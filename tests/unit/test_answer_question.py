from __future__ import annotations

from pathlib import Path

from packages.adapters.answering.answer_trace_logger import AnswerTraceLogger
from packages.adapters.retrieval.hash_vector_search_adapter import HashVectorSearchAdapter
from packages.adapters.retrieval.simple_keyword_search_adapter import SimpleKeywordSearchAdapter
from packages.application.use_cases.answer_question import (
    AnswerQuestionInput,
    answer_question_use_case,
)
from packages.domain.models import Chunk
from packages.ports.chunk_query_port import ChunkQueryPort


class InMemoryChunkQuery(ChunkQueryPort):
    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks

    def list_chunks(self, doc_id: str | None = None) -> list[Chunk]:
        if doc_id is None:
            return list(self._chunks)
        return [chunk for chunk in self._chunks if chunk.doc_id == doc_id]


def _sample_chunks() -> list[Chunk]:
    return [
        Chunk(
            chunk_id='c1',
            doc_id='d1',
            content_type='table',
            page_start=10,
            page_end=10,
            content_text='Torque specification table: motor torque is 45 Nm at rated load.',
            table_id='tbl-1',
        ),
        Chunk(
            chunk_id='c2',
            doc_id='d1',
            content_type='text',
            page_start=12,
            page_end=12,
            content_text='If drive trips after start, check overload and acceleration time settings.',
        ),
        Chunk(
            chunk_id='c3',
            doc_id='d1',
            content_type='text',
            page_start=15,
            page_end=15,
            content_text='Calibration baseline for encoder scaling values.',
        ),
        Chunk(
            chunk_id='c4',
            doc_id='d2',
            content_type='figure_ocr',
            page_start=7,
            page_end=7,
            content_text='Pump startup trip guidance: verify phase wiring and terminal map.',
            figure_id='fig-3',
        ),
    ]


def test_answer_question_returns_grounded_answer_with_citations(tmp_path: Path) -> None:
    trace_file = tmp_path / 'answer_traces.jsonl'
    output = answer_question_use_case(
        AnswerQuestionInput(query='What is the torque specification in Nm?', doc_id='d1'),
        chunk_query=InMemoryChunkQuery(_sample_chunks()),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
        trace_logger=AnswerTraceLogger(trace_file),
    )

    assert output.status == 'ok'
    assert output.answer
    assert output.citations
    assert all(c.doc_id for c in output.citations)
    assert all(c.page > 0 for c in output.citations)
    assert any(c.table_id == 'tbl-1' for c in output.citations)
    assert output.follow_up_question is None
    assert trace_file.exists()


def test_answer_question_returns_not_found_with_closest_citations() -> None:
    output = answer_question_use_case(
        AnswerQuestionInput(
            query='What is the quantum flux capacitor calibration constant for arc control?',
            doc_id='d1',
        ),
        chunk_query=InMemoryChunkQuery(_sample_chunks()),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
        trace_logger=None,
    )

    assert output.status == 'not_found'
    assert 'Closest grounded evidence' in output.answer
    assert output.citations


def test_answer_question_triggers_single_follow_up_for_ambiguous_prompt() -> None:
    output = answer_question_use_case(
        AnswerQuestionInput(
            query='My equipment trips immediately after start. What should I check first?'
        ),
        chunk_query=InMemoryChunkQuery(_sample_chunks()),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
        trace_logger=None,
    )

    assert output.status == 'needs_follow_up'
    assert output.follow_up_question is not None
    assert output.follow_up_question.endswith('?')
    assert output.follow_up_question.count('?') == 1
