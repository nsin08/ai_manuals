from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class PlanStep:
    step_id: str
    tool_name: str
    objective: str


class PlannerPort(ABC):
    @abstractmethod
    def create_plan(
        self,
        *,
        query: str,
        intent: str,
        doc_id: str | None,
        max_steps: int,
    ) -> list[PlanStep]:
        raise NotImplementedError
