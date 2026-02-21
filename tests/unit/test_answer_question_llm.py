from __future__ import annotations

from packages.adapters.retrieval.hash_vector_search_adapter import HashVectorSearchAdapter
from packages.adapters.retrieval.simple_keyword_search_adapter import SimpleKeywordSearchAdapter
from packages.application.use_cases.answer_question import (
    AnswerQuestionInput,
    answer_question_use_case,
)
from packages.domain.models import Chunk
from packages.ports.chunk_query_port import ChunkQueryPort
from packages.ports.llm_port import LlmEvidence, LlmPort


class InMemoryChunkQuery(ChunkQueryPort):
    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks

    def list_chunks(self, doc_id: str | None = None) -> list[Chunk]:
        if doc_id is None:
            return list(self._chunks)
        return [chunk for chunk in self._chunks if chunk.doc_id == doc_id]


class FakeLlm(LlmPort):
    def __init__(self, text: str) -> None:
        self._text = text

    def generate_answer(
        self,
        *,
        query: str,
        intent: str,
        evidence: list[LlmEvidence],
    ) -> str:
        _ = query, intent, evidence
        return self._text


def _chunks() -> list[Chunk]:
    return [
        Chunk(
            chunk_id='c1',
            doc_id='d1',
            content_type='text',
            page_start=5,
            page_end=5,
            content_text='Fault F005 indicates overcurrent and check output wiring.',
        )
    ]


def test_answer_question_uses_llm_text_when_available() -> None:
    output = answer_question_use_case(
        AnswerQuestionInput(query='What does F005 mean?', doc_id='d1'),
        chunk_query=InMemoryChunkQuery(_chunks()),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
        llm=FakeLlm('LLM grounded response'),
        trace_logger=None,
    )

    assert output.status == 'ok'
    assert output.answer == 'LLM grounded response'
    assert output.citations


def test_answer_question_falls_back_when_llm_returns_empty() -> None:
    output = answer_question_use_case(
        AnswerQuestionInput(query='What does F005 mean?', doc_id='d1'),
        chunk_query=InMemoryChunkQuery(_chunks()),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
        llm=FakeLlm(''),
        trace_logger=None,
    )

    assert output.status == 'ok'
    assert output.answer
    assert output.answer != 'LLM grounded response'
