from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from packages.adapters.retrieval.retrieval_trace_logger import RetrievalTraceLogger
from packages.ports.chunk_query_port import ChunkQueryPort
from packages.ports.keyword_search_port import KeywordSearchPort, ScoredChunk
from packages.ports.vector_search_port import VectorSearchPort


@dataclass(frozen=True)
class SearchEvidenceInput:
    query: str
    doc_id: str | None = None
    top_k_keyword: int = 20
    top_k_vector: int = 20
    top_n: int = 8


@dataclass(frozen=True)
class EvidenceHit:
    chunk_id: str
    doc_id: str
    content_type: str
    page_start: int
    page_end: int
    section_path: str | None
    figure_id: str | None
    table_id: str | None
    score: float
    keyword_score: float
    vector_score: float
    snippet: str


@dataclass(frozen=True)
class SearchEvidenceOutput:
    query: str
    intent: str
    total_chunks_scanned: int
    hits: list[EvidenceHit]


TABLE_TERMS = {
    'table', 'parameter', 'spec', 'specification', 'torque', 'clearance', 'gap',
    'tolerance', 'dimension', 'mm', 'nm', 'schedule', 'interval', 'fault code'
}
DIAGRAM_TERMS = {
    'diagram', 'schematic', 'wiring', 'terminal', 'pin', 'connector', 'figure',
    'signal', 'block diagram', 'connection'
}



def _detect_intent(query: str) -> str:
    q = query.lower()
    if any(term in q for term in DIAGRAM_TERMS):
        return 'diagram'
    if any(term in q for term in TABLE_TERMS):
        return 'table'
    return 'general'



def _normalize_scores(results: list[ScoredChunk]) -> dict[str, float]:
    if not results:
        return {}

    raw = [item.score for item in results]
    lo = min(raw)
    hi = max(raw)

    if hi <= lo:
        return {item.chunk.chunk_id: 1.0 for item in results}

    return {
        item.chunk.chunk_id: (item.score - lo) / (hi - lo)
        for item in results
    }



def _content_type_weight(content_type: str, intent: str) -> float:
    if intent == 'table':
        if content_type == 'table':
            return 1.35
        if content_type in {'figure_ocr', 'figure_caption'}:
            return 1.10
    if intent == 'diagram':
        if content_type in {'figure_ocr', 'figure_caption'}:
            return 1.40
        if content_type == 'table':
            return 1.10
    return 1.0



def _snippet(text: str, max_len: int = 240) -> str:
    compact = ' '.join((text or '').split())
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 3] + '...'



def search_evidence_use_case(
    input_data: SearchEvidenceInput,
    chunk_query: ChunkQueryPort,
    keyword_search: KeywordSearchPort,
    vector_search: VectorSearchPort,
    trace_logger: RetrievalTraceLogger | None = None,
) -> SearchEvidenceOutput:
    query = input_data.query.strip()
    if not query:
        return SearchEvidenceOutput(
            query=input_data.query,
            intent='general',
            total_chunks_scanned=0,
            hits=[],
        )

    chunks = chunk_query.list_chunks(doc_id=input_data.doc_id)
    intent = _detect_intent(query)

    keyword_hits = keyword_search.search(query, chunks, input_data.top_k_keyword)
    vector_hits = vector_search.search(query, chunks, input_data.top_k_vector)

    keyword_norm = _normalize_scores(keyword_hits)
    vector_norm = _normalize_scores(vector_hits)

    by_chunk: dict[str, dict[str, Any]] = {}

    for item in keyword_hits:
        key = item.chunk.chunk_id
        by_chunk.setdefault(
            key,
            {
                'chunk': item.chunk,
                'keyword_score': 0.0,
                'vector_score': 0.0,
            },
        )
        by_chunk[key]['keyword_score'] = keyword_norm.get(key, 0.0)

    for item in vector_hits:
        key = item.chunk.chunk_id
        by_chunk.setdefault(
            key,
            {
                'chunk': item.chunk,
                'keyword_score': 0.0,
                'vector_score': 0.0,
            },
        )
        by_chunk[key]['vector_score'] = vector_norm.get(key, 0.0)

    hits: list[EvidenceHit] = []
    for row in by_chunk.values():
        chunk = row['chunk']
        base = 0.5 * row['keyword_score'] + 0.5 * row['vector_score']
        weighted = base * _content_type_weight(chunk.content_type, intent)

        hits.append(
            EvidenceHit(
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                content_type=chunk.content_type,
                page_start=chunk.page_start,
                page_end=chunk.page_end,
                section_path=chunk.section_path,
                figure_id=chunk.figure_id,
                table_id=chunk.table_id,
                score=round(weighted, 6),
                keyword_score=round(row['keyword_score'], 6),
                vector_score=round(row['vector_score'], 6),
                snippet=_snippet(chunk.content_text),
            )
        )

    hits.sort(key=lambda x: x.score, reverse=True)
    top_hits = hits[: input_data.top_n]

    if trace_logger is not None:
        trace_logger.log(
            {
                'ts': datetime.now(UTC).isoformat(),
                'query': query,
                'intent': intent,
                'doc_id': input_data.doc_id,
                'total_chunks_scanned': len(chunks),
                'top_hits': [
                    {
                        'chunk_id': h.chunk_id,
                        'doc_id': h.doc_id,
                        'content_type': h.content_type,
                        'page_start': h.page_start,
                        'section_path': h.section_path,
                        'figure_id': h.figure_id,
                        'table_id': h.table_id,
                        'score': h.score,
                    }
                    for h in top_hits
                ],
            }
        )

    return SearchEvidenceOutput(
        query=query,
        intent=intent,
        total_chunks_scanned=len(chunks),
        hits=top_hits,
    )
