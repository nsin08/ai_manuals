from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExtractedTableRow:
    """Structured representation of a single table row."""

    table_id: str
    page_number: int
    row_index: int
    headers: list[str]       # empty list when no header detected
    row_cells: list[str]
    units: list[str]         # "" per cell when absent; same length as row_cells
    raw_text: str            # original unparsed row text (fallback)


@dataclass(frozen=True)
class ExtractedTable:
    table_id: str
    page_number: int
    rows: list[ExtractedTableRow] = field(default_factory=list)
    raw_text: str = ''       # whole-table fallback (never stored as a chunk)


class TableExtractorPort(ABC):
    @abstractmethod
    def extract(self, page_text: str, page_number: int, doc_id: str = '') -> list[ExtractedTable]:
        raise NotImplementedError
