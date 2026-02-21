from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from packages.application.agentic.state import AgenticAnswerState
from packages.application.use_cases.search_evidence import (
    EvidenceHit,
    SearchEvidenceInput,
    search_evidence_use_case,
)
from packages.domain.citation_formatter import format_citation
from packages.domain.models import Answer, Citation
from packages.domain.policies import has_minimum_citation_fields, is_answer_grounded
from packages.ports.agent_trace_port import AgentTracePort
from packages.ports.chunk_query_port import ChunkQueryPort
from packages.ports.keyword_search_port import KeywordSearchPort
from packages.ports.llm_port import LlmEvidence, LlmPort
from packages.ports.planner_port import PlannerPort
from packages.ports.reranker_port import RerankerPort
from packages.ports.state_graph_runner_port import GraphRunLimits, StateGraphRunnerPort
from packages.ports.tool_executor_port import ToolExecutorPort
from packages.ports.vector_search_port import VectorSearchPort

_TOKEN_RE = re.compile(r'[a-z0-9]+')
_ALIASES = {
    'analog': 'analogue',
    'analogue': 'analogue',
    'mean': 'description',
    'meaning': 'description',
    'descriptions': 'description',
    'parameters': 'parameter',
    'signals': 'signal',
}
_NOT_FOUND_TEXT = 'Not found in provided manuals based on retrieved evidence.'
_STOPWORDS = {
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'do', 'does', 'for', 'from',
    'how', 'i', 'in', 'is', 'it', 'mean', 'of', 'on', 'or', 'recommended', 'should',
    'that', 'the', 'to', 'what', 'when', 'where', 'which', 'why', 'with',
}
_AMBIGUOUS_HINTS = (
    'my equipment',
    'my unit',
    'my machine',
    'this equipment',
    'this unit',
    'it trips',
    'it fails',
    'it alarms',
    'it will not',
    "it won't",
)
_COMPARISON_HINTS = (' compare ', ' vs ', ' versus ', ' difference ')
_ALLOWED_STATUSES = {'ok', 'not_found', 'needs_follow_up', 'partial'}
_DIRECT_ANSWER_HEADER = 'Direct answer:'
_KEY_DETAILS_HEADER = 'Key details:'
_MISSING_DATA_HEADER = 'If missing data:'


class TraceLoggerPort(Protocol):
    def log(self, payload: dict[str, Any]) -> None:
        ...


@dataclass(frozen=True)
class AnswerQuestionInput:
    query: str
    doc_id: str | None = None
    top_n: int = 6
    top_k_keyword: int = 20
    top_k_vector: int = 20
    rerank_pool_size: int = 24


@dataclass(frozen=True)
class AnswerCitationOutput:
    doc_id: str
    page: int
    section_path: str | None
    figure_id: str | None
    table_id: str | None
    label: str


@dataclass(frozen=True)
class AnswerQuestionOutput:
    query: str
    intent: str
    status: str
    confidence: str
    answer: str
    follow_up_question: str | None
    warnings: list[str]
    total_chunks_scanned: int
    retrieved_chunk_ids: list[str]
    citations: list[AnswerCitationOutput]
    reasoning_summary: str | None = None


def _tokens(text: str) -> set[str]:
    out: set[str] = set()
    for raw in _TOKEN_RE.findall((text or '').lower()):
        token = raw
        if len(token) > 3 and token.endswith('s'):
            token = token[:-1]
        token = _ALIASES.get(token, token)
        if token not in _STOPWORDS and len(token) > 1:
            out.add(token)
    return out


def _query_overlap(query: str, hits: list[EvidenceHit], top_n: int = 3) -> float:
    q_tokens = _tokens(query)
    if not q_tokens or not hits:
        return 0.0

    best = 0.0
    for hit in hits[:top_n]:
        overlap = len(q_tokens.intersection(_tokens(hit.snippet))) / max(len(q_tokens), 1)
        best = max(best, overlap)
    return best


def _aggregate_overlap(query: str, hits: list[EvidenceHit], top_n: int = 6) -> float:
    q_tokens = _tokens(query)
    if not q_tokens or not hits:
        return 0.0

    aggregate_tokens: set[str] = set()
    for hit in hits[:top_n]:
        aggregate_tokens.update(_tokens(hit.snippet))
    return len(q_tokens.intersection(aggregate_tokens)) / max(len(q_tokens), 1)


def _best_overlap_count(query: str, hits: list[EvidenceHit], top_n: int = 3) -> tuple[int, int]:
    q_tokens = _tokens(query)
    if not q_tokens or not hits:
        return 0, len(q_tokens)

    best = 0
    for hit in hits[:top_n]:
        overlap_count = len(q_tokens.intersection(_tokens(hit.snippet)))
        best = max(best, overlap_count)
    return best, len(q_tokens)


def _is_comparison_query(query: str) -> bool:
    q = f' {query.lower()} '
    return any(hint in q for hint in _COMPARISON_HINTS)


def _is_insufficient_evidence(query: str, hits: list[EvidenceHit]) -> bool:
    if not hits:
        return True

    best_score = hits[0].score
    best_keyword = max((h.keyword_score for h in hits), default=0.0)
    best_vector = max((h.vector_score for h in hits), default=0.0)
    overlap = _query_overlap(query, hits)
    agg_overlap = _aggregate_overlap(query, hits)
    overlap_count, query_token_count = _best_overlap_count(query, hits)
    is_compare = _is_comparison_query(query)
    if best_score < 0.22 and best_keyword < 0.35 and best_vector < 0.60:
        return True

    if is_compare:
        if agg_overlap < 0.22 and overlap < 0.10 and best_vector < 0.70 and best_keyword < 0.45:
            return True
    else:
        if overlap < 0.15 and agg_overlap < 0.25 and best_vector < 0.75 and best_keyword < 0.55:
            return True

    if query_token_count >= 6 and overlap_count < 2 and agg_overlap < 0.30:
        return True
    return False


def _build_follow_up_question(query: str, hits: list[EvidenceHit], doc_id: str | None) -> str | None:
    if doc_id:
        return None

    q = query.lower()
    has_hint = any(hint in q for hint in _AMBIGUOUS_HINTS)
    unique_docs = sorted({h.doc_id for h in hits[:5]})
    multi_doc = len(unique_docs) > 1

    if not has_hint and not multi_doc:
        return None

    if multi_doc:
        docs_preview = ', '.join(unique_docs[:3])
        return f'Which manual/model should I use ({docs_preview})?'

    return 'Which exact model/manual should I use for this issue?'


def _compose_answer_text(hits: list[EvidenceHit]) -> str:
    points: list[str] = []
    for hit in hits[:3]:
        snippet = hit.snippet.strip()
        if snippet:
            points.append(snippet)

    if not points:
        return _NOT_FOUND_TEXT
    if len(points) == 1:
        return points[0]

    return '\n'.join(f'{idx + 1}. {value}' for idx, value in enumerate(points))


def _compose_related_evidence_text(hits: list[EvidenceHit]) -> str:
    if not hits:
        return _NOT_FOUND_TEXT

    lines = ['Direct answer is not explicitly stated. Closest grounded evidence:']
    for hit in hits[:3]:
        snippet = hit.snippet.strip()
        if not snippet:
            continue
        page = hit.page_start if hit.page_start > 0 else hit.page_end
        lines.append(f'- p.{page}: {snippet}')
    return '\n'.join(lines)


def _compose_llm_answer_text(
    *,
    query: str,
    intent: str,
    hits: list[EvidenceHit],
    llm: LlmPort,
) -> str:
    evidence = [
        LlmEvidence(
            doc_id=hit.doc_id,
            page_start=hit.page_start,
            page_end=hit.page_end,
            content_type=hit.content_type,
            text=hit.snippet,
        )
        for hit in hits[:12]
    ]
    return llm.generate_answer(query=query, intent=intent, evidence=evidence).strip()


def _dedupe_lines(lines: list[str], limit: int) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for line in lines:
        cleaned = ' '.join((line or '').split()).strip(' -')
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
        if len(out) >= limit:
            break
    return out


def _parse_structured_sections(text: str) -> tuple[str | None, list[str], list[str]]:
    direct_lines: list[str] = []
    key_details: list[str] = []
    missing_data: list[str] = []
    section: str | None = None

    for raw_line in (text or '').splitlines():
        line = raw_line.strip()
        if not line:
            continue

        lower = line.lower()
        if lower.startswith(_DIRECT_ANSWER_HEADER.lower()):
            section = 'direct'
            value = line.split(':', 1)[1].strip()
            if value:
                direct_lines.append(value)
            continue
        if lower.startswith(_KEY_DETAILS_HEADER.lower()):
            section = 'details'
            value = line.split(':', 1)[1].strip()
            if value:
                key_details.append(value)
            continue
        if lower.startswith(_MISSING_DATA_HEADER.lower()):
            section = 'missing'
            value = line.split(':', 1)[1].strip()
            if value:
                missing_data.append(value)
            continue

        cleaned = re.sub(r'^\d+\.\s*', '', re.sub(r'^[-*]\s*', '', line)).strip()
        if not cleaned:
            continue

        if section == 'direct':
            direct_lines.append(cleaned)
        elif section == 'details':
            key_details.append(cleaned)
        elif section == 'missing':
            missing_data.append(cleaned)

    direct_answer = ' '.join(direct_lines).strip() if direct_lines else None
    return direct_answer, _dedupe_lines(key_details, limit=4), _dedupe_lines(missing_data, limit=4)


def _extract_direct_answer_text(answer_text: str) -> str:
    direct_answer, _, _ = _parse_structured_sections(answer_text)
    if direct_answer:
        return direct_answer

    lines = [line.strip() for line in (answer_text or '').splitlines() if line.strip()]
    if not lines:
        return _NOT_FOUND_TEXT

    first = re.sub(r'^\d+\.\s*', '', re.sub(r'^[-*]\s*', '', lines[0])).strip()
    if first.lower().startswith(_DIRECT_ANSWER_HEADER.lower()):
        first = first.split(':', 1)[1].strip()
    return first or _NOT_FOUND_TEXT


def _build_key_details(answer_text: str, hits: list[EvidenceHit]) -> list[str]:
    _, parsed_details, _ = _parse_structured_sections(answer_text)
    if parsed_details:
        return parsed_details

    details: list[str] = []
    for hit in hits[:3]:
        snippet = hit.snippet.strip()
        if snippet:
            details.append(snippet)
    if not details:
        details.append('No additional grounded details beyond the direct answer.')
    return _dedupe_lines(details, limit=3)


def _build_missing_data_lines(
    *,
    status: str,
    follow_up: str | None,
    warnings: list[str],
    answer_text: str,
) -> list[str]:
    _, _, parsed_missing = _parse_structured_sections(answer_text)
    if parsed_missing:
        return parsed_missing

    if status == 'ok':
        return ['None identified in retrieved evidence.']

    items: list[str] = []
    if status == 'needs_follow_up':
        items.append(follow_up or 'Manual/model context is required to finalize the answer.')
    if status in {'not_found', 'partial'}:
        items.append('Direct answer is not explicitly stated in the retrieved evidence.')

    for warning in warnings:
        lowered = warning.lower()
        if 'insufficient evidence' in lowered:
            items.append('Evidence is insufficient for a fully grounded direct answer.')
        if 'no citations available' in lowered:
            items.append('Grounding check blocked an ungrounded ok response.')

    if not items:
        items.append('No additional missing-data notes.')

    return _dedupe_lines(items, limit=3)


def _format_eval_answer(
    *,
    answer_text: str,
    status: str,
    hits: list[EvidenceHit],
    follow_up: str | None,
    warnings: list[str],
) -> str:
    direct_answer = _extract_direct_answer_text(answer_text)
    key_details = _build_key_details(answer_text, hits)
    missing_data = _build_missing_data_lines(
        status=status,
        follow_up=follow_up,
        warnings=warnings,
        answer_text=answer_text,
    )

    lines = [f'{_DIRECT_ANSWER_HEADER} {direct_answer}', _KEY_DETAILS_HEADER]
    for detail in key_details:
        lines.append(f'- {detail}')
    lines.append(_MISSING_DATA_HEADER)
    for item in missing_data:
        lines.append(f'- {item}')
    return '\n'.join(lines).strip()


def _build_citations(hits: list[EvidenceHit], limit: int | None = None) -> list[Citation]:
    seen: set[tuple[str, int, str | None, str | None, str | None]] = set()
    citations: list[Citation] = []
    if not hits:
        return citations

    top_score = max(h.score for h in hits)
    min_relevance = max(0.18, top_score * 0.35)

    for hit in hits:
        if hit.score < min_relevance:
            continue
        page = hit.page_start if hit.page_start > 0 else max(hit.page_end, 1)
        citation = Citation(
            doc_id=hit.doc_id,
            page=page,
            section_path=hit.section_path,
            figure_id=hit.figure_id,
            table_id=hit.table_id,
        )
        key = (
            citation.doc_id,
            citation.page,
            citation.section_path,
            citation.figure_id,
            citation.table_id,
        )
        if key in seen:
            continue
        seen.add(key)
        citations.append(citation)
        if limit is not None and len(citations) >= limit:
            break

    if not citations and hits:
        first = hits[0]
        page = first.page_start if first.page_start > 0 else max(first.page_end, 1)
        citations.append(
            Citation(
                doc_id=first.doc_id,
                page=page,
                section_path=first.section_path,
                figure_id=first.figure_id,
                table_id=first.table_id,
            )
        )

    return citations


def _confidence_from_hits(query: str, hits: list[EvidenceHit], status: str) -> str:
    if status != 'ok' or not hits:
        return 'low'

    best_score = hits[0].score
    overlap = _aggregate_overlap(query, hits)
    rerank = max((h.rerank_score for h in hits), default=0.0)

    if best_score >= 0.60 and overlap >= 0.35:
        return 'high'
    if best_score >= 0.40 and overlap >= 0.22:
        return 'medium'
    if rerank >= 0.60 and overlap >= 0.20:
        return 'medium'
    return 'low'


def _coerce_evidence_hits(rows: list[dict[str, Any]]) -> list[EvidenceHit]:
    hits: list[EvidenceHit] = []
    for row in rows:
        try:
            chunk_id = str(row.get('chunk_id') or '').strip()
            doc_id = str(row.get('doc_id') or '').strip()
            if not chunk_id or not doc_id:
                continue
            hits.append(
                EvidenceHit(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    content_type=str(row.get('content_type') or 'text'),
                    page_start=int(row.get('page_start') or 0),
                    page_end=int(row.get('page_end') or 0),
                    section_path=row.get('section_path'),
                    figure_id=row.get('figure_id'),
                    table_id=row.get('table_id'),
                    score=float(row.get('score') or 0.0),
                    keyword_score=float(row.get('keyword_score') or 0.0),
                    vector_score=float(row.get('vector_score') or 0.0),
                    snippet=str(row.get('snippet') or ''),
                    rerank_score=float(row.get('rerank_score') or 0.0),
                )
            )
        except Exception:
            continue
    hits.sort(key=lambda row: row.score, reverse=True)
    return hits


def _build_answer_output(
    *,
    query: str,
    intent: str,
    doc_id: str | None,
    hits: list[EvidenceHit],
    total_chunks_scanned: int,
    retrieved_chunk_ids: list[str],
    answer_text_override: str | None,
    follow_up_override: str | None,
    warnings_seed: list[str],
    llm: LlmPort | None,
    reasoning_summary: str | None,
    enforce_structured_output: bool,
) -> AnswerQuestionOutput:
    follow_up = follow_up_override
    if follow_up is None:
        follow_up = _build_follow_up_question(query, hits, doc_id)

    citations = _build_citations(hits, limit=None)
    warnings = list(warnings_seed)
    status = 'ok'
    answer_text = (answer_text_override or '').strip()
    if not answer_text:
        answer_text = _compose_answer_text(hits)

    if _is_insufficient_evidence(query, hits):
        status = 'not_found'
        answer_text = _compose_related_evidence_text(hits)
        warnings.append('Insufficient evidence to provide a grounded direct answer.')

    if follow_up is not None:
        status = 'needs_follow_up'
        warnings.append('Query appears ambiguous across manuals or equipment variants.')

    if status == 'ok' and llm is not None and not (answer_text_override or '').strip():
        llm_text = _compose_llm_answer_text(
            query=query,
            intent=intent,
            hits=hits,
            llm=llm,
        )
        if llm_text:
            answer_text = llm_text

    answer_model = Answer(
        text=answer_text,
        citations=citations,
        warnings=list(warnings),
        metadata={'status': status, 'intent': intent},
    )

    if citations and not has_minimum_citation_fields(answer_model):
        filtered = [c for c in citations if c.doc_id and c.page > 0]
        filtered_warnings = list(warnings) + ['Dropped invalid citations failing minimum schema checks.']
        answer_model = Answer(
            text=answer_text,
            citations=filtered,
            warnings=filtered_warnings,
            metadata=answer_model.metadata,
        )

    if status == 'ok' and not is_answer_grounded(answer_model):
        status = 'not_found'
        answer_text = _NOT_FOUND_TEXT
        blocked_warnings = list(answer_model.warnings) + ['No citations available for grounded answer.']
        answer_model = Answer(
            text=answer_text,
            citations=answer_model.citations,
            warnings=blocked_warnings,
            metadata=answer_model.metadata,
        )

    if enforce_structured_output:
        answer_text = _format_eval_answer(
            answer_text=answer_text,
            status=status,
            hits=hits,
            follow_up=follow_up,
            warnings=list(answer_model.warnings),
        )
        answer_model = Answer(
            text=answer_text,
            citations=answer_model.citations,
            warnings=list(answer_model.warnings),
            metadata=answer_model.metadata,
        )

    confidence = _confidence_from_hits(query, hits, status)

    citation_payload = [
        AnswerCitationOutput(
            doc_id=c.doc_id,
            page=c.page,
            section_path=c.section_path,
            figure_id=c.figure_id,
            table_id=c.table_id,
            label=format_citation(c),
        )
        for c in answer_model.citations
    ]

    return AnswerQuestionOutput(
        query=query,
        intent=intent,
        status=status,
        confidence=confidence,
        answer=answer_text,
        follow_up_question=follow_up,
        warnings=list(answer_model.warnings),
        total_chunks_scanned=total_chunks_scanned,
        retrieved_chunk_ids=retrieved_chunk_ids,
        citations=citation_payload,
        reasoning_summary=reasoning_summary,
    )


def _log_answer_trace(
    *,
    trace_logger: TraceLoggerPort | None,
    input_data: AnswerQuestionInput,
    output: AnswerQuestionOutput,
    agentic: dict[str, Any] | None = None,
) -> None:
    if trace_logger is None:
        return

    payload: dict[str, Any] = {
        'ts': datetime.now(UTC).isoformat(),
        'query': output.query,
        'intent': output.intent,
        'status': output.status,
        'confidence': output.confidence,
        'doc_id': input_data.doc_id,
        'retrieved_chunk_ids': output.retrieved_chunk_ids,
        'citations': [
            {
                'doc_id': citation.doc_id,
                'page': citation.page,
                'section_path': citation.section_path,
                'figure_id': citation.figure_id,
                'table_id': citation.table_id,
            }
            for citation in output.citations
        ],
        'follow_up_question': output.follow_up_question,
    }
    if output.reasoning_summary:
        payload['reasoning_summary'] = output.reasoning_summary
    if agentic:
        payload['agentic'] = agentic
    trace_logger.log(payload)


def answer_question_use_case(
    input_data: AnswerQuestionInput,
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
    enforce_structured_output: bool = False,
) -> AnswerQuestionOutput:
    fallback_warnings: list[str] = []

    if use_agentic_mode and planner and tool_executor and state_graph_runner:
        initial_state = AgenticAnswerState(
            query=input_data.query,
            doc_id=input_data.doc_id,
            top_n=input_data.top_n,
            top_k_keyword=input_data.top_k_keyword,
            top_k_vector=input_data.top_k_vector,
            rerank_pool_size=input_data.rerank_pool_size,
        ).to_dict()
        try:
            graph_output = state_graph_runner.run(
                initial_state=initial_state,
                limits=GraphRunLimits(
                    max_iterations=max(1, agent_max_iterations),
                    max_tool_calls=max(1, agent_max_tool_calls),
                    timeout_seconds=max(1.0, float(agent_timeout_seconds)),
                ),
                planner=planner,
                tool_executor=tool_executor,
                llm=llm,
                trace_logger=agent_trace_logger,
            )
            state = AgenticAnswerState.from_dict(graph_output.state)
            hits = _coerce_evidence_hits(state.evidence_hits)

            status = state.status if state.status in _ALLOWED_STATUSES else 'ok'
            warnings_seed = list(state.warnings)
            if status != 'ok':
                warnings_seed.append(f'Agentic status hint: {status}')
            if graph_output.terminated_reason != 'completed':
                warnings_seed.append(f'Agentic run terminated: {graph_output.terminated_reason}')

            output = _build_answer_output(
                query=input_data.query.strip(),
                intent=state.intent or 'general',
                doc_id=input_data.doc_id,
                hits=hits,
                total_chunks_scanned=state.total_chunks_scanned,
                retrieved_chunk_ids=state.retrieved_chunk_ids or [h.chunk_id for h in hits],
                answer_text_override=state.answer_draft,
                follow_up_override=state.follow_up_question,
                warnings_seed=warnings_seed,
                llm=None,
                reasoning_summary=state.reasoning_summary,
                enforce_structured_output=enforce_structured_output,
            )
            _log_answer_trace(
                trace_logger=trace_logger,
                input_data=input_data,
                output=output,
                agentic={
                    'enabled': True,
                    'iterations': graph_output.iterations,
                    'tool_calls': graph_output.tool_calls,
                    'terminated_reason': graph_output.terminated_reason,
                },
            )
            return output
        except Exception as exc:
            fallback_warnings.append(
                f'Agentic mode fallback triggered: {type(exc).__name__}. Using deterministic path.'
            )
            if agent_trace_logger is not None:
                agent_trace_logger.log(
                    {
                        'ts': datetime.now(UTC).isoformat(),
                        'event': 'agentic_fallback',
                        'query': input_data.query,
                        'doc_id': input_data.doc_id,
                        'error': f'{type(exc).__name__}: {exc}',
                    }
                )

    evidence = search_evidence_use_case(
        SearchEvidenceInput(
            query=input_data.query,
            doc_id=input_data.doc_id,
            top_n=input_data.top_n,
            top_k_keyword=input_data.top_k_keyword,
            top_k_vector=input_data.top_k_vector,
            rerank_pool_size=input_data.rerank_pool_size,
        ),
        chunk_query=chunk_query,
        keyword_search=keyword_search,
        vector_search=vector_search,
        trace_logger=None,
        reranker=reranker,
    )

    output = _build_answer_output(
        query=evidence.query,
        intent=evidence.intent,
        doc_id=input_data.doc_id,
        hits=evidence.hits,
        total_chunks_scanned=evidence.total_chunks_scanned,
        retrieved_chunk_ids=[h.chunk_id for h in evidence.hits],
        answer_text_override=None,
        follow_up_override=None,
        warnings_seed=fallback_warnings,
        llm=llm,
        reasoning_summary=None,
        enforce_structured_output=enforce_structured_output,
    )

    _log_answer_trace(
        trace_logger=trace_logger,
        input_data=input_data,
        output=output,
        agentic={'enabled': False} if use_agentic_mode else None,
    )
    return output
