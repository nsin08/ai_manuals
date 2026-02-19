from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class RerankCandidate:
    chunk_id: str
    doc_id: str
    page_start: int
    content_type: str
    text: str
    base_score: float


@dataclass(frozen=True)
class RankedCandidate:
    chunk_id: str
    score: float


class RerankerPort(ABC):
    @abstractmethod
    def rerank(
        self,
        *,
        query: str,
        candidates: list[RerankCandidate],
        top_k: int,
    ) -> list[RankedCandidate]:
        raise NotImplementedError
