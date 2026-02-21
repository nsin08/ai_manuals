from __future__ import annotations

from abc import ABC, abstractmethod


class VisionPort(ABC):
    @abstractmethod
    def extract_page_insights(self, *, pdf_path: str, page_number: int) -> str:
        raise NotImplementedError
