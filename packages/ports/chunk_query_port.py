from __future__ import annotations

from abc import ABC, abstractmethod

from packages.domain.models import Chunk


class ChunkQueryPort(ABC):
    @abstractmethod
    def list_chunks(self, doc_id: str | None = None) -> list[Chunk]:
        raise NotImplementedError
