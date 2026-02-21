from __future__ import annotations

from packages.ports.reranker_port import RankedCandidate, RerankCandidate, RerankerPort


class NoopRerankerAdapter(RerankerPort):
    def rerank(
        self,
        *,
        query: str,
        candidates: list[RerankCandidate],
        top_k: int,
    ) -> list[RankedCandidate]:
        _ = query
        rows = sorted(candidates, key=lambda row: row.base_score, reverse=True)
        return [RankedCandidate(chunk_id=row.chunk_id, score=row.base_score) for row in rows[:top_k]]
