from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractedTable:
    table_id: str
    page_number: int
    text: str


class TableExtractorPort(ABC):
    @abstractmethod
    def extract(self, page_text: str, page_number: int) -> list[ExtractedTable]:
        raise NotImplementedError
