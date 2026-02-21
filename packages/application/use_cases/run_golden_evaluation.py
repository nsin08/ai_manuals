from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Protocol

from packages.adapters.data_contracts.contracts import GoldenQuestion, load_catalog, load_golden_questions
from packages.application.use_cases.answer_question import (
    AnswerQuestionInput,
    AnswerQuestionOutput,
    answer_question_use_case,
)
from packages.ports.agent_trace_port import AgentTracePort
from packages.ports.chunk_query_port import ChunkQueryPort
from packages.ports.keyword_search_port import KeywordSearchPort
from packages.ports.llm_port import LlmPort
from packages.ports.planner_port import PlannerPort
from packages.ports.reranker_port import RerankerPort
from packages.ports.state_graph_runner_port import StateGraphRunnerPort
from packages.ports.tool_executor_port import ToolExecutorPort
from packages.ports.vector_search_port import VectorSearchPort


class TraceLoggerPort(Protocol):
    def log(self, payload: dict[str, object]) -> None:
        ...


@dataclass(frozen=True)
class RunGoldenEvaluationInput:
    catalog_path: Path
    golden_questions_path: Path
    top_n: int = 6
    doc_id_filter: str | None = None
    limit: int | None = None


@dataclass(frozen=True)
class GoldenQuestionEvaluation:
    question_id: str
    doc: str
    intent: str
    question_type: str
    difficulty: str
    rag_mode: str
    turn_count: int
    question: str
    answer_status: str
    has_citation_doc_page: bool
    grounded: bool
    follow_up_expected: bool
    follow_up_ok: bool
    expected_keyword_hits: int
    expected_keyword_total: int
    expected_match: bool
    missing_expected_keywords: list[str]
    citation_count: int
    pass_result: bool
    reasons: list[str]
    follow_up_question: str | None
    planned_turns: int
    executed_turns: int
    turn_prompts: list[str]
    turn_statuses: list[str]


@dataclass(frozen=True)
class RunGoldenEvaluationOutput:
    total_questions: int
    passed_questions: int
    failed_questions: int
    pass_rate: float
    missing_docs: list[str]
    results: list[GoldenQuestionEvaluation]


def _extract_turn_prompts(question: GoldenQuestion) -> list[str]:
    planned_turns = max(1, int(question.turn_count))
    base = (question.question or '').strip()
    if not base:
        return ['']
    if planned_turns == 1:
        return [base]

    # Prefer explicit "Step N:" decomposition when present.
    step_parts = [part.strip(' .;') for part in re.split(r'(?i)\bstep\s*\d+\s*:\s*', base) if part.strip()]
    candidates = step_parts

    if len(candidates) < 2 and '->' in base:
        arrow_parts = [part.strip(' .;') for part in base.split('->') if part.strip()]
        if len(arrow_parts) >= 2:
            candidates = arrow_parts

    if len(candidates) < 2:
        then_parts = [part.strip(' .;') for part in re.split(r'(?i)\bthen\b', base) if part.strip()]
        if len(then_parts) >= 2:
            candidates = then_parts

    if len(candidates) < 2:
        sentence_parts = [part.strip(' .;') for part in re.split(r'(?<=[.?!])\s+', base) if part.strip()]
        if len(sentence_parts) >= 2:
            candidates = sentence_parts

    if len(candidates) < 2:
        candidates = [base]

    prompts = [re.sub(r'\s+', ' ', part).strip() for part in candidates if part.strip()]
    if not prompts:
        prompts = [base]

    if len(prompts) > planned_turns:
        prompts = prompts[: planned_turns - 1] + ['; '.join(prompts[planned_turns - 1 :])]
    while len(prompts) < planned_turns:
        idx = len(prompts) + 1
        prompts.append(f'Continue the same task with step {idx}. Base task: {base}')
    return prompts


def _compose_turn_query(*, prompt: str, history: list[tuple[str, str]], turn_index: int) -> str:
    if turn_index <= 0 or not history:
        return prompt

    lines: list[str] = ['Conversation context from earlier turns:']
    for idx, (prior_prompt, prior_answer) in enumerate(history[-2:], start=max(1, len(history) - 1)):
        lines.append(f'Prior turn {idx} user: {prior_prompt}')
        lines.append(f'Prior turn {idx} assistant: {prior_answer[:800]}')
    lines.append(f'Current turn user: {prompt}')
    return '\n'.join(lines)


def _normalize(text: str) -> str:
    return ' '.join((text or '').lower().split())


def _evaluate_expected_keywords(
    answer_text: str,
    question: GoldenQuestion,
) -> tuple[int, int, bool, list[str]]:
    expected = [keyword for keyword in question.expected_keywords if keyword]
    if not expected:
        return 0, 0, True, []

    normalized_answer = _normalize(answer_text)
    matched: list[str] = []
    for keyword in expected:
        if _normalize(keyword) in normalized_answer:
            matched.append(keyword)

    required_hits = min(max(question.min_keyword_hits, 1), len(expected))
    expected_match = len(matched) >= required_hits
    missing_keywords = [keyword for keyword in expected if keyword not in matched]
    return len(matched), len(expected), expected_match, missing_keywords


def _evaluate_question(
    *,
    answer: AnswerQuestionOutput,
    question: GoldenQuestion,
) -> tuple[bool, bool, bool, bool, int, int, bool, list[str], list[str]]:
    has_citation_doc_page = bool(answer.citations) and all(
        citation.doc_id and citation.page > 0 for citation in answer.citations
    )
    grounded = has_citation_doc_page and answer.status in {'ok', 'not_found', 'needs_follow_up'}
    follow_up_expected = question.intent == 'follow_up_required'
    follow_up_ok = (answer.status == 'needs_follow_up') if follow_up_expected else True

    expected_hits, expected_total, expected_match, missing_keywords = _evaluate_expected_keywords(
        answer.answer,
        question,
    )

    reasons: list[str] = []
    if not has_citation_doc_page:
        reasons.append('missing doc/page citation')
    if not grounded:
        reasons.append('answer not grounded')
    if follow_up_expected and not follow_up_ok:
        reasons.append('follow-up expected but not returned')
    if not expected_match:
        reasons.append('expected answer keywords not matched')

    return (
        has_citation_doc_page,
        grounded,
        follow_up_expected,
        follow_up_ok,
        expected_hits,
        expected_total,
        expected_match,
        missing_keywords,
        reasons,
    )


def run_golden_evaluation_use_case(
    input_data: RunGoldenEvaluationInput,
    chunk_query: ChunkQueryPort,
    keyword_search: KeywordSearchPort,
    vector_search: VectorSearchPort,
    trace_logger: TraceLoggerPort | None = None,
    llm: LlmPort | None = None,
    reranker: RerankerPort | None = None,
    use_agentic_mode: bool = False,
    planner: PlannerPort | None = None,
    tool_executor: ToolExecutorPort | None = None,
    state_graph_runner: StateGraphRunnerPort | None = None,
    agent_trace_logger: AgentTracePort | None = None,
    agent_max_iterations: int = 4,
    agent_max_tool_calls: int = 6,
    agent_timeout_seconds: float = 20.0,
) -> RunGoldenEvaluationOutput:
    catalog_rows = load_catalog(input_data.catalog_path)
    _, questions = load_golden_questions(input_data.golden_questions_path)
    catalog_by_doc = {row.doc_id: row for row in catalog_rows}

    selected_questions = questions
    if input_data.doc_id_filter:
        selected_questions = [question for question in selected_questions if question.doc == input_data.doc_id_filter]

    if input_data.limit is not None and input_data.limit > 0:
        selected_questions = selected_questions[: input_data.limit]

    missing_docs: set[str] = set()
    results: list[GoldenQuestionEvaluation] = []

    def _run_answer(question_text: str, doc_id: str | None) -> AnswerQuestionOutput:
        return answer_question_use_case(
            AnswerQuestionInput(
                query=question_text,
                doc_id=doc_id,
                top_n=input_data.top_n,
            ),
            chunk_query=chunk_query,
            keyword_search=keyword_search,
            vector_search=vector_search,
            trace_logger=trace_logger,
            llm=llm,
            reranker=reranker,
            use_agentic_mode=use_agentic_mode,
            planner=planner,
            tool_executor=tool_executor,
            state_graph_runner=state_graph_runner,
            agent_trace_logger=agent_trace_logger,
            agent_max_iterations=agent_max_iterations,
            agent_max_tool_calls=agent_max_tool_calls,
            agent_timeout_seconds=agent_timeout_seconds,
            enforce_structured_output=True,
        )

    for question in selected_questions:
        if question.doc != 'multiple':
            catalog_row = catalog_by_doc.get(question.doc)
            if catalog_row is None or catalog_row.status != 'present':
                missing_docs.add(question.doc)
                results.append(
                    GoldenQuestionEvaluation(
                        question_id=question.question_id,
                        doc=question.doc,
                        intent=question.intent,
                        question_type=question.question_type,
                        difficulty=question.difficulty,
                        rag_mode=question.rag_mode,
                        turn_count=question.turn_count,
                        question=question.question,
                        answer_status='missing_doc',
                        has_citation_doc_page=False,
                        grounded=False,
                        follow_up_expected=question.intent == 'follow_up_required',
                        follow_up_ok=False,
                        expected_keyword_hits=0,
                        expected_keyword_total=len(question.expected_keywords),
                        expected_match=False if question.expected_keywords else True,
                        missing_expected_keywords=list(question.expected_keywords),
                        citation_count=0,
                        pass_result=False,
                        reasons=['document not available in catalog'],
                        follow_up_question=None,
                        planned_turns=max(1, int(question.turn_count)),
                        executed_turns=0,
                        turn_prompts=[],
                        turn_statuses=[],
                    )
                )
                continue

        doc_id = None if question.doc == 'multiple' else question.doc

        turn_prompts = _extract_turn_prompts(question)
        history: list[tuple[str, str]] = []
        turn_outputs: list[AnswerQuestionOutput] = []
        turn_statuses: list[str] = []
        for idx, turn_prompt in enumerate(turn_prompts):
            turn_query = _compose_turn_query(prompt=turn_prompt, history=history, turn_index=idx)
            turn_answer = _run_answer(turn_query, doc_id)
            turn_outputs.append(turn_answer)
            turn_statuses.append(turn_answer.status)
            history.append((turn_prompt, turn_answer.answer))

        answer = turn_outputs[-1]
        if len(turn_outputs) > 1:
            combined_answer_text = '\n'.join(
                f'Turn {idx + 1} answer: {turn_output.answer}'
                for idx, turn_output in enumerate(turn_outputs)
                if turn_output.answer.strip()
            )
            if combined_answer_text.strip():
                answer = AnswerQuestionOutput(
                    query=answer.query,
                    intent=answer.intent,
                    status=answer.status,
                    confidence=answer.confidence,
                    answer=combined_answer_text,
                    follow_up_question=answer.follow_up_question,
                    warnings=answer.warnings,
                    total_chunks_scanned=answer.total_chunks_scanned,
                    retrieved_chunk_ids=answer.retrieved_chunk_ids,
                    citations=answer.citations,
                    reasoning_summary=answer.reasoning_summary,
                )

        (
            has_citation_doc_page,
            grounded,
            follow_up_expected,
            follow_up_ok,
            expected_hits,
            expected_total,
            expected_match,
            missing_expected_keywords,
            reasons,
        ) = _evaluate_question(answer=answer, question=question)
        if len(turn_outputs) < max(1, int(question.turn_count)):
            reasons.append('insufficient turns executed for multi-turn scenario')

        results.append(
            GoldenQuestionEvaluation(
                question_id=question.question_id,
                doc=question.doc,
                intent=question.intent,
                question_type=question.question_type,
                difficulty=question.difficulty,
                rag_mode=question.rag_mode,
                turn_count=question.turn_count,
                question=question.question,
                answer_status=answer.status,
                has_citation_doc_page=has_citation_doc_page,
                grounded=grounded,
                follow_up_expected=follow_up_expected,
                follow_up_ok=follow_up_ok,
                expected_keyword_hits=expected_hits,
                expected_keyword_total=expected_total,
                expected_match=expected_match,
                missing_expected_keywords=missing_expected_keywords,
                citation_count=len(answer.citations),
                pass_result=not reasons,
                reasons=reasons,
                follow_up_question=answer.follow_up_question,
                planned_turns=max(1, int(question.turn_count)),
                executed_turns=len(turn_outputs),
                turn_prompts=turn_prompts,
                turn_statuses=turn_statuses,
            )
        )

    passed_questions = sum(1 for row in results if row.pass_result)
    total_questions = len(results)
    failed_questions = total_questions - passed_questions
    pass_rate = round((passed_questions / total_questions) * 100.0, 2) if total_questions else 0.0

    return RunGoldenEvaluationOutput(
        total_questions=total_questions,
        passed_questions=passed_questions,
        failed_questions=failed_questions,
        pass_rate=pass_rate,
        missing_docs=sorted(missing_docs),
        results=results,
    )
