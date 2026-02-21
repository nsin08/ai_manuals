from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class LlmEvidence:
    doc_id: str
    page_start: int
    page_end: int
    content_type: str
    text: str


class LlmPort(ABC):
    @abstractmethod
    def generate_answer(
        self,
        *,
        query: str,
        intent: str,
        evidence: list[LlmEvidence],
    ) -> str:
        raise NotImplementedError
