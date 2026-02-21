from __future__ import annotations

from abc import ABC, abstractmethod

from packages.domain.models import Chunk


class ChunkStorePort(ABC):
    @abstractmethod
    def persist(self, doc_id: str, chunks: list[Chunk]) -> str:
        """Persist chunks and return an asset reference path."""
        raise NotImplementedError
