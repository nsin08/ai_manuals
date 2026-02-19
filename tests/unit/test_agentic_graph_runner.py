from __future__ import annotations

import time

from packages.adapters.agentic.langgraph_runner_adapter import LangGraphRunnerAdapter
from packages.ports.llm_port import LlmEvidence, LlmPort
from packages.ports.planner_port import PlanStep, PlannerPort
from packages.ports.state_graph_runner_port import GraphRunLimits
from packages.ports.tool_executor_port import ToolExecutionResult, ToolExecutorPort


class FakePlanner(PlannerPort):
    def create_plan(
        self,
        *,
        query: str,
        intent: str,
        doc_id: str | None,
        max_steps: int,
    ) -> list[PlanStep]:
        _ = query, intent, doc_id, max_steps
        return [
            PlanStep(step_id='s1', tool_name='search_evidence', objective='search'),
            PlanStep(step_id='s2', tool_name='draft_answer', objective='draft'),
        ]


class FakeToolExecutor(ToolExecutorPort):
    def available_tools(self) -> list[str]:
        return ['search_evidence', 'draft_answer']

    def execute(
        self,
        *,
        tool_name: str,
        arguments: dict[str, object],
    ) -> ToolExecutionResult:
        if tool_name == 'search_evidence':
            return ToolExecutionResult(
                tool_name=tool_name,
                success=True,
                payload={
                    'query': arguments.get('query'),
                    'intent': 'general',
                    'total_chunks_scanned': 4,
                    'hits': [
                        {
                            'chunk_id': 'c1',
                            'doc_id': 'd1',
                            'content_type': 'text',
                            'page_start': 2,
                            'page_end': 2,
                            'section_path': None,
                            'figure_id': None,
                            'table_id': None,
                            'score': 0.7,
                            'keyword_score': 0.6,
                            'vector_score': 0.8,
                            'rerank_score': 0.0,
                            'snippet': 'Fault F005 indicates overcurrent.',
                        }
                    ],
                },
            )
        return ToolExecutionResult(tool_name=tool_name, success=True, payload={})


class FailingToolExecutor(ToolExecutorPort):
    def available_tools(self) -> list[str]:
        return ['search_evidence']

    def execute(
        self,
        *,
        tool_name: str,
        arguments: dict[str, object],
    ) -> ToolExecutionResult:
        _ = arguments
        return ToolExecutionResult(tool_name=tool_name, success=False, error='boom')


class FakeLlm(LlmPort):
    def generate_answer(
        self,
        *,
        query: str,
        intent: str,
        evidence: list[LlmEvidence],
    ) -> str:
        _ = query, intent, evidence
        return 'LLM synthesized answer.'


class DraftOnlySlowPlanner(PlannerPort):
    def create_plan(
        self,
        *,
        query: str,
        intent: str,
        doc_id: str | None,
        max_steps: int,
    ) -> list[PlanStep]:
        _ = query, intent, doc_id, max_steps
        time.sleep(0.05)
        return [PlanStep(step_id='s1', tool_name='draft_answer', objective='draft')]


def test_langgraph_runner_produces_answer_draft_and_hits() -> None:
    runner = LangGraphRunnerAdapter()
    output = runner.run(
        initial_state={'query': 'What does F005 mean?', 'doc_id': 'd1', 'top_n': 4},
        limits=GraphRunLimits(max_iterations=4, max_tool_calls=4, timeout_seconds=10),
        planner=FakePlanner(),
        tool_executor=FakeToolExecutor(),
        llm=FakeLlm(),
        trace_logger=None,
    )

    assert output.iterations >= 1
    assert output.tool_calls >= 1
    assert output.state['answer_draft']
    assert output.state['status'] == 'ok'
    assert output.state['evidence_hits']
    assert output.state['retrieved_chunk_ids']


def test_langgraph_runner_handles_tool_failures_without_crashing() -> None:
    runner = LangGraphRunnerAdapter()
    output = runner.run(
        initial_state={'query': 'What does F005 mean?', 'doc_id': 'd1', 'top_n': 4},
        limits=GraphRunLimits(max_iterations=2, max_tool_calls=2, timeout_seconds=10),
        planner=FakePlanner(),
        tool_executor=FailingToolExecutor(),
        llm=None,
        trace_logger=None,
    )

    assert output.state['errors']
    assert output.state['status'] in {'ok', 'not_found'}


def test_langgraph_runner_executes_after_slow_planner_and_auto_inserts_retrieval() -> None:
    runner = LangGraphRunnerAdapter()
    output = runner.run(
        initial_state={'query': 'What does F005 mean?', 'doc_id': 'd1', 'top_n': 4},
        limits=GraphRunLimits(max_iterations=3, max_tool_calls=3, timeout_seconds=0.01),
        planner=DraftOnlySlowPlanner(),
        tool_executor=FakeToolExecutor(),
        llm=None,
        trace_logger=None,
    )

    assert output.tool_calls >= 1
    assert output.iterations >= 1
    assert output.terminated_reason != 'timeout'
    assert output.state['evidence_hits']
