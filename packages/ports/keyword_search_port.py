from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from packages.domain.models import Chunk


@dataclass(frozen=True)
class ScoredChunk:
    chunk: Chunk
    score: float
    source: str


class KeywordSearchPort(ABC):
    @abstractmethod
    def search(self, query: str, chunks: list[Chunk], top_k: int) -> list[ScoredChunk]:
        raise NotImplementedError
