from __future__ import annotations

from abc import ABC, abstractmethod


class OcrPort(ABC):
    @abstractmethod
    def extract_text(self, source_path: str, page_number: int) -> str:
        raise NotImplementedError
