from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from packages.ports.agent_trace_port import AgentTracePort
from packages.ports.llm_port import LlmPort
from packages.ports.planner_port import PlannerPort
from packages.ports.tool_executor_port import ToolExecutorPort


@dataclass(frozen=True)
class GraphRunLimits:
    max_iterations: int = 4
    max_tool_calls: int = 6
    timeout_seconds: float = 20.0


@dataclass(frozen=True)
class GraphRunOutput:
    state: dict[str, Any]
    iterations: int
    tool_calls: int
    terminated_reason: str


class StateGraphRunnerPort(ABC):
    @abstractmethod
    def run(
        self,
        *,
        initial_state: dict[str, Any],
        limits: GraphRunLimits,
        planner: PlannerPort,
        tool_executor: ToolExecutorPort,
        llm: LlmPort | None,
        trace_logger: AgentTracePort | None = None,
    ) -> GraphRunOutput:
        raise NotImplementedError
