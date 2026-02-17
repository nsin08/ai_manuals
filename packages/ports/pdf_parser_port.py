from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedPdfPage:
    page_number: int
    text: str


class PdfParserPort(ABC):
    @abstractmethod
    def parse(self, pdf_path: str) -> list[ParsedPdfPage]:
        raise NotImplementedError
