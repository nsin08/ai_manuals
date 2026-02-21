from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolExecutionResult:
    tool_name: str
    success: bool
    payload: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class ToolExecutorPort(ABC):
    @abstractmethod
    def available_tools(self) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def execute(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ToolExecutionResult:
        raise NotImplementedError
