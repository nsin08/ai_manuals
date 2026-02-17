from __future__ import annotations

from abc import ABC, abstractmethod

from packages.domain.models import Chunk
from packages.ports.keyword_search_port import ScoredChunk


class VectorSearchPort(ABC):
    @abstractmethod
    def search(self, query: str, chunks: list[Chunk], top_k: int) -> list[ScoredChunk]:
        raise NotImplementedError
