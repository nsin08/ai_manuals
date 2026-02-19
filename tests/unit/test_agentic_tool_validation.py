from __future__ import annotations

from packages.adapters.agentic.langchain_tool_executor_adapter import (
    LangChainToolDefinition,
    LangChainToolExecutorAdapter,
)


def test_tool_executor_rejects_unknown_tool() -> None:
    executor = LangChainToolExecutorAdapter(tools=[])
    result = executor.execute(tool_name='missing', arguments={})
    assert result.success is False
    assert 'Unknown tool' in (result.error or '')


def test_tool_executor_validates_required_args() -> None:
    executor = LangChainToolExecutorAdapter(
        tools=[
            LangChainToolDefinition(
                name='search_evidence',
                description='Search',
                handler=lambda _: {},
                required_args=('query',),
            )
        ]
    )
    result = executor.execute(tool_name='search_evidence', arguments={})
    assert result.success is False
    assert 'Missing required args' in (result.error or '')


def test_tool_executor_runs_successful_tool() -> None:
    executor = LangChainToolExecutorAdapter(
        tools=[
            LangChainToolDefinition(
                name='search_evidence',
                description='Search',
                handler=lambda arguments: {'query': arguments['query'], 'hits': []},
                required_args=('query',),
            )
        ]
    )
    result = executor.execute(tool_name='search_evidence', arguments={'query': 'q1'})
    assert result.success is True
    assert result.payload['query'] == 'q1'


def test_tool_executor_maps_input_to_query_when_needed() -> None:
    executor = LangChainToolExecutorAdapter(
        tools=[
            LangChainToolDefinition(
                name='search_evidence',
                description='Search',
                handler=lambda arguments: {'query': arguments['query']},
                required_args=('query',),
            )
        ]
    )
    result = executor.execute(tool_name='search_evidence', arguments={'input': 'q2'})
    assert result.success is True
    assert result.payload['query'] == 'q2'
