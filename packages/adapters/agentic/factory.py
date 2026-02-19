from __future__ import annotations

from pathlib import Path

from packages.adapters.agentic.jsonl_agent_trace_logger_adapter import JsonlAgentTraceLoggerAdapter
from packages.adapters.agentic.langchain_planner_adapter import LangChainPlannerAdapter
from packages.adapters.agentic.langchain_tool_executor_adapter import (
    LangChainToolDefinition,
    LangChainToolExecutorAdapter,
)
from packages.adapters.agentic.langgraph_runner_adapter import LangGraphRunnerAdapter
from packages.adapters.agentic.noop_planner_adapter import NoopPlannerAdapter
from packages.ports.agent_trace_port import AgentTracePort
from packages.ports.planner_port import PlannerPort
from packages.ports.state_graph_runner_port import StateGraphRunnerPort
from packages.ports.tool_executor_port import ToolExecutorPort


def create_planner_adapter(
    *,
    provider: str,
    base_url: str,
    model: str,
) -> PlannerPort:
    normalized = provider.strip().lower()
    # Keep planning deterministic for langgraph by default.
    # LLM-driven planning is opt-in via AGENTIC_PROVIDER=langchain.
    if normalized in {'langchain', 'local', 'ollama'}:
        return LangChainPlannerAdapter(base_url=base_url, model=model)
    return NoopPlannerAdapter()


def create_tool_executor_adapter(
    *,
    provider: str,
    tools: list[LangChainToolDefinition],
) -> ToolExecutorPort:
    _ = provider
    return LangChainToolExecutorAdapter(tools=tools)


def create_state_graph_runner_adapter(
    *,
    provider: str,
) -> StateGraphRunnerPort:
    _ = provider
    return LangGraphRunnerAdapter()


def create_agent_trace_logger(trace_file: Path) -> AgentTracePort:
    return JsonlAgentTraceLoggerAdapter(trace_file=trace_file)
