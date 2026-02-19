from __future__ import annotations

from packages.adapters.agentic.factory import create_planner_adapter
from packages.adapters.agentic.langchain_planner_adapter import LangChainPlannerAdapter
from packages.adapters.agentic.noop_planner_adapter import NoopPlannerAdapter


def test_langgraph_provider_uses_deterministic_noop_planner() -> None:
    planner = create_planner_adapter(
        provider='langgraph',
        base_url='http://localhost:11434',
        model='deepseek-r1:8b',
    )
    assert isinstance(planner, NoopPlannerAdapter)


def test_langchain_provider_uses_llm_planner_adapter() -> None:
    planner = create_planner_adapter(
        provider='langchain',
        base_url='http://localhost:11434',
        model='deepseek-r1:8b',
    )
    assert isinstance(planner, LangChainPlannerAdapter)
