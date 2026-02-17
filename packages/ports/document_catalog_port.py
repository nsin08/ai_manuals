from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentCatalogRecord:
    doc_id: str
    title: str
    filename: str
    status: str


class DocumentCatalogPort(ABC):
    @abstractmethod
    def list_documents(self) -> list[DocumentCatalogRecord]:
        raise NotImplementedError

    @abstractmethod
    def get(self, doc_id: str) -> DocumentCatalogRecord | None:
        raise NotImplementedError
