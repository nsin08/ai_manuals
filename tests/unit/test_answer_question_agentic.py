from __future__ import annotations

from packages.adapters.retrieval.hash_vector_search_adapter import HashVectorSearchAdapter
from packages.adapters.retrieval.simple_keyword_search_adapter import SimpleKeywordSearchAdapter
from packages.application.use_cases.answer_question import (
    AnswerQuestionInput,
    answer_question_use_case,
)
from packages.domain.models import Chunk
from packages.ports.chunk_query_port import ChunkQueryPort
from packages.ports.planner_port import PlanStep, PlannerPort
from packages.ports.state_graph_runner_port import GraphRunLimits, GraphRunOutput, StateGraphRunnerPort
from packages.ports.tool_executor_port import ToolExecutionResult, ToolExecutorPort


class InMemoryChunkQuery(ChunkQueryPort):
    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks

    def list_chunks(self, doc_id: str | None = None) -> list[Chunk]:
        if doc_id is None:
            return list(self._chunks)
        return [chunk for chunk in self._chunks if chunk.doc_id == doc_id]


class StubPlanner(PlannerPort):
    def create_plan(
        self,
        *,
        query: str,
        intent: str,
        doc_id: str | None,
        max_steps: int,
    ) -> list[PlanStep]:
        _ = query, intent, doc_id, max_steps
        return [PlanStep(step_id='s1', tool_name='search_evidence', objective='search')]


class StubToolExecutor(ToolExecutorPort):
    def available_tools(self) -> list[str]:
        return ['search_evidence']

    def execute(
        self,
        *,
        tool_name: str,
        arguments: dict[str, object],
    ) -> ToolExecutionResult:
        _ = tool_name, arguments
        return ToolExecutionResult(tool_name='search_evidence', success=True, payload={})


class StubGraphRunner(StateGraphRunnerPort):
    def run(
        self,
        *,
        initial_state: dict[str, object],
        limits: GraphRunLimits,
        planner: PlannerPort,
        tool_executor: ToolExecutorPort,
        llm,
        trace_logger=None,
    ) -> GraphRunOutput:
        _ = initial_state, limits, planner, tool_executor, llm, trace_logger
        return GraphRunOutput(
            state={
                'query': 'What does F005 mean?',
                'doc_id': 'd1',
                'intent': 'general',
                'answer_draft': 'Agentic draft response',
                'evidence_hits': [
                    {
                        'chunk_id': 'c1',
                        'doc_id': 'd1',
                        'content_type': 'text',
                        'page_start': 4,
                        'page_end': 4,
                        'section_path': None,
                        'figure_id': None,
                        'table_id': None,
                        'score': 0.8,
                        'keyword_score': 0.7,
                        'vector_score': 0.8,
                        'rerank_score': 0.0,
                        'snippet': 'Fault F005 indicates overcurrent condition.',
                    }
                ],
                'retrieved_chunk_ids': ['c1'],
                'total_chunks_scanned': 2,
                'warnings': [],
                'status': 'ok',
                'reasoning_summary': 'Plan executed with tools: search_evidence',
            },
            iterations=1,
            tool_calls=1,
            terminated_reason='completed',
        )


class FailingGraphRunner(StateGraphRunnerPort):
    def run(
        self,
        *,
        initial_state: dict[str, object],
        limits: GraphRunLimits,
        planner: PlannerPort,
        tool_executor: ToolExecutorPort,
        llm,
        trace_logger=None,
    ) -> GraphRunOutput:
        _ = initial_state, limits, planner, tool_executor, llm, trace_logger
        raise RuntimeError('graph failed')


def test_answer_question_agentic_mode_returns_graph_output() -> None:
    output = answer_question_use_case(
        AnswerQuestionInput(query='What does F005 mean?', doc_id='d1'),
        chunk_query=InMemoryChunkQuery([]),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
        use_agentic_mode=True,
        planner=StubPlanner(),
        tool_executor=StubToolExecutor(),
        state_graph_runner=StubGraphRunner(),
        trace_logger=None,
    )

    assert output.status == 'ok'
    assert output.answer == 'Agentic draft response'
    assert output.citations
    assert output.reasoning_summary is not None


def test_answer_question_agentic_fallback_uses_deterministic_path() -> None:
    chunks = [
        Chunk(
            chunk_id='c1',
            doc_id='d1',
            content_type='text',
            page_start=3,
            page_end=3,
            content_text='Fault F005 indicates overcurrent and check output wiring.',
        )
    ]
    output = answer_question_use_case(
        AnswerQuestionInput(query='What does F005 mean?', doc_id='d1'),
        chunk_query=InMemoryChunkQuery(chunks),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
        use_agentic_mode=True,
        planner=StubPlanner(),
        tool_executor=StubToolExecutor(),
        state_graph_runner=FailingGraphRunner(),
        trace_logger=None,
    )

    assert output.answer
    assert any('Agentic mode fallback triggered' in warning for warning in output.warnings)
