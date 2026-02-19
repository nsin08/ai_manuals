from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol

from packages.application.use_cases.search_evidence import (
    EvidenceHit,
    SearchEvidenceInput,
    search_evidence_use_case,
)
from packages.domain.citation_formatter import format_citation
from packages.domain.models import Answer, Citation
from packages.domain.policies import has_minimum_citation_fields, is_answer_grounded
from packages.ports.chunk_query_port import ChunkQueryPort
from packages.ports.keyword_search_port import KeywordSearchPort
from packages.ports.llm_port import LlmEvidence, LlmPort
from packages.ports.reranker_port import RerankerPort
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


def answer_question_use_case(
    input_data: AnswerQuestionInput,
    chunk_query: ChunkQueryPort,
    keyword_search: KeywordSearchPort,
    vector_search: VectorSearchPort,
    trace_logger: TraceLoggerPort | None = None,
    llm: LlmPort | None = None,
    reranker: RerankerPort | None = None,
) -> AnswerQuestionOutput:
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

    follow_up = _build_follow_up_question(input_data.query, evidence.hits, input_data.doc_id)
    citations = _build_citations(evidence.hits, limit=None)
    warnings: list[str] = []
    status = 'ok'
    answer_text = _compose_answer_text(evidence.hits)

    if _is_insufficient_evidence(input_data.query, evidence.hits):
        status = 'not_found'
        answer_text = _compose_related_evidence_text(evidence.hits)
        warnings.append('Insufficient evidence to provide a grounded direct answer.')

    if follow_up is not None:
        status = 'needs_follow_up'
        warnings.append('Query appears ambiguous across manuals or equipment variants.')

    if status == 'ok' and llm is not None:
        llm_text = _compose_llm_answer_text(
            query=input_data.query,
            intent=evidence.intent,
            hits=evidence.hits,
            llm=llm,
        )
        if llm_text:
            answer_text = llm_text

    answer_model = Answer(
        text=answer_text,
        citations=citations,
        warnings=list(warnings),
        metadata={'status': status, 'intent': evidence.intent},
    )

    if citations and not has_minimum_citation_fields(answer_model):
        filtered = [c for c in citations if c.doc_id and c.page > 0]
        answer_model = Answer(
            text=answer_text,
            citations=filtered,
            warnings=warnings + ['Dropped invalid citations failing minimum schema checks.'],
            metadata=answer_model.metadata,
        )

    if status == 'ok' and not is_answer_grounded(answer_model):
        status = 'not_found'
        answer_text = _NOT_FOUND_TEXT
        warnings.append('No citations available for grounded answer.')

    confidence = _confidence_from_hits(input_data.query, evidence.hits, status)

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

    output = AnswerQuestionOutput(
        query=evidence.query,
        intent=evidence.intent,
        status=status,
        confidence=confidence,
        answer=answer_text,
        follow_up_question=follow_up,
        warnings=list(answer_model.warnings),
        total_chunks_scanned=evidence.total_chunks_scanned,
        retrieved_chunk_ids=[h.chunk_id for h in evidence.hits],
        citations=citation_payload,
    )

    if trace_logger is not None:
        trace_logger.log(
            {
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
        )

    return output
