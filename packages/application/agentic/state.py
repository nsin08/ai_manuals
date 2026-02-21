from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgenticAnswerState:
    query: str
    doc_id: str | None = None
    intent: str = 'general'
    top_n: int = 6
    top_k_keyword: int = 20
    top_k_vector: int = 20
    rerank_pool_size: int = 24
    plan_steps: list[dict[str, str]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    evidence_hits: list[dict[str, Any]] = field(default_factory=list)
    answer_draft: str = ''
    status: str = 'ok'
    follow_up_question: str | None = None
    warnings: list[str] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    retrieved_chunk_ids: list[str] = field(default_factory=list)
    total_chunks_scanned: int = 0
    confidence: str = 'low'
    reasoning_summary: str | None = None
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            'query': self.query,
            'doc_id': self.doc_id,
            'intent': self.intent,
            'top_n': self.top_n,
            'top_k_keyword': self.top_k_keyword,
            'top_k_vector': self.top_k_vector,
            'rerank_pool_size': self.rerank_pool_size,
            'plan_steps': list(self.plan_steps),
            'tool_calls': list(self.tool_calls),
            'evidence_hits': list(self.evidence_hits),
            'answer_draft': self.answer_draft,
            'status': self.status,
            'follow_up_question': self.follow_up_question,
            'warnings': list(self.warnings),
            'citations': list(self.citations),
            'retrieved_chunk_ids': list(self.retrieved_chunk_ids),
            'total_chunks_scanned': self.total_chunks_scanned,
            'confidence': self.confidence,
            'reasoning_summary': self.reasoning_summary,
            'errors': list(self.errors),
            'metadata': dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> 'AgenticAnswerState':
        return cls(
            query=str(payload.get('query') or ''),
            doc_id=payload.get('doc_id'),
            intent=str(payload.get('intent') or 'general'),
            top_n=int(payload.get('top_n') or 6),
            top_k_keyword=int(payload.get('top_k_keyword') or 20),
            top_k_vector=int(payload.get('top_k_vector') or 20),
            rerank_pool_size=int(payload.get('rerank_pool_size') or 24),
            plan_steps=list(payload.get('plan_steps') or []),
            tool_calls=list(payload.get('tool_calls') or []),
            evidence_hits=list(payload.get('evidence_hits') or []),
            answer_draft=str(payload.get('answer_draft') or ''),
            status=str(payload.get('status') or 'ok'),
            follow_up_question=payload.get('follow_up_question'),
            warnings=[str(item) for item in payload.get('warnings') or []],
            citations=list(payload.get('citations') or []),
            retrieved_chunk_ids=[str(item) for item in payload.get('retrieved_chunk_ids') or []],
            total_chunks_scanned=int(payload.get('total_chunks_scanned') or 0),
            confidence=str(payload.get('confidence') or 'low'),
            reasoning_summary=payload.get('reasoning_summary'),
            errors=[str(item) for item in payload.get('errors') or []],
            metadata=dict(payload.get('metadata') or {}),
        )
