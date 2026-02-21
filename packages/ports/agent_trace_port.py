from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AgentTracePort(ABC):
    @abstractmethod
    def log(self, payload: dict[str, Any]) -> None:
        raise NotImplementedError
