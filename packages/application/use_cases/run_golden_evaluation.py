from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from packages.adapters.data_contracts.contracts import load_catalog, load_golden_questions
from packages.application.use_cases.answer_question import (
    AnswerQuestionInput,
    AnswerQuestionOutput,
    answer_question_use_case,
)
from packages.ports.chunk_query_port import ChunkQueryPort
from packages.ports.keyword_search_port import KeywordSearchPort
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
    question: str
    answer_status: str
    has_citation_doc_page: bool
    grounded: bool
    follow_up_expected: bool
    follow_up_ok: bool
    citation_count: int
    pass_result: bool
    reasons: list[str]
    follow_up_question: str | None


@dataclass(frozen=True)
class RunGoldenEvaluationOutput:
    total_questions: int
    passed_questions: int
    failed_questions: int
    pass_rate: float
    missing_docs: list[str]
    results: list[GoldenQuestionEvaluation]


def _evaluate_question(
    answer: AnswerQuestionOutput,
    question_intent: str,
) -> tuple[bool, bool, bool, bool, list[str]]:
    has_citation_doc_page = bool(answer.citations) and all(
        c.doc_id and c.page > 0 for c in answer.citations
    )
    grounded = has_citation_doc_page and answer.status in {'ok', 'not_found', 'needs_follow_up'}
    follow_up_expected = question_intent == 'follow_up_required'
    follow_up_ok = (answer.status == 'needs_follow_up') if follow_up_expected else True

    reasons: list[str] = []
    if not has_citation_doc_page:
        reasons.append('missing doc/page citation')
    if not grounded:
        reasons.append('answer not grounded')
    if follow_up_expected and not follow_up_ok:
        reasons.append('follow-up expected but not returned')

    return has_citation_doc_page, grounded, follow_up_expected, follow_up_ok, reasons


def run_golden_evaluation_use_case(
    input_data: RunGoldenEvaluationInput,
    chunk_query: ChunkQueryPort,
    keyword_search: KeywordSearchPort,
    vector_search: VectorSearchPort,
    trace_logger: TraceLoggerPort | None = None,
) -> RunGoldenEvaluationOutput:
    catalog_rows = load_catalog(input_data.catalog_path)
    _, questions = load_golden_questions(input_data.golden_questions_path)
    catalog_by_doc = {row.doc_id: row for row in catalog_rows}

    selected_questions = questions
    if input_data.doc_id_filter:
        selected_questions = [q for q in selected_questions if q.doc == input_data.doc_id_filter]

    if input_data.limit is not None and input_data.limit > 0:
        selected_questions = selected_questions[: input_data.limit]

    missing_docs: set[str] = set()
    results: list[GoldenQuestionEvaluation] = []

    for question in selected_questions:
        if question.doc != 'multiple':
            row = catalog_by_doc.get(question.doc)
            if row is None or row.status != 'present':
                missing_docs.add(question.doc)
                results.append(
                    GoldenQuestionEvaluation(
                        question_id=question.question_id,
                        doc=question.doc,
                        intent=question.intent,
                        question=question.question,
                        answer_status='missing_doc',
                        has_citation_doc_page=False,
                        grounded=False,
                        follow_up_expected=question.intent == 'follow_up_required',
                        follow_up_ok=False,
                        citation_count=0,
                        pass_result=False,
                        reasons=['document not available in catalog'],
                        follow_up_question=None,
                    )
                )
                continue

        doc_id = None if question.doc == 'multiple' else question.doc
        answer = answer_question_use_case(
            AnswerQuestionInput(
                query=question.question,
                doc_id=doc_id,
                top_n=input_data.top_n,
            ),
            chunk_query=chunk_query,
            keyword_search=keyword_search,
            vector_search=vector_search,
            trace_logger=trace_logger,
        )

        has_citation_doc_page, grounded, follow_up_expected, follow_up_ok, reasons = _evaluate_question(
            answer,
            question.intent,
        )

        results.append(
            GoldenQuestionEvaluation(
                question_id=question.question_id,
                doc=question.doc,
                intent=question.intent,
                question=question.question,
                answer_status=answer.status,
                has_citation_doc_page=has_citation_doc_page,
                grounded=grounded,
                follow_up_expected=follow_up_expected,
                follow_up_ok=follow_up_ok,
                citation_count=len(answer.citations),
                pass_result=not reasons,
                reasons=reasons,
                follow_up_question=answer.follow_up_question,
            )
        )

    passed = sum(1 for row in results if row.pass_result)
    total = len(results)
    failed = total - passed
    pass_rate = round((passed / total) * 100.0, 2) if total else 0.0

    return RunGoldenEvaluationOutput(
        total_questions=total,
        passed_questions=passed,
        failed_questions=failed,
        pass_rate=pass_rate,
        missing_docs=sorted(missing_docs),
        results=results,
    )
