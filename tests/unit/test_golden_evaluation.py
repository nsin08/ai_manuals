from __future__ import annotations

from pathlib import Path

import packages.application.use_cases.run_golden_evaluation as run_golden_module
from packages.adapters.retrieval.hash_vector_search_adapter import HashVectorSearchAdapter
from packages.adapters.retrieval.simple_keyword_search_adapter import SimpleKeywordSearchAdapter
from packages.application.use_cases.answer_question import AnswerQuestionOutput
from packages.application.use_cases.run_golden_evaluation import (
    RunGoldenEvaluationInput,
    run_golden_evaluation_use_case,
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


def _write_contracts(tmp_path: Path) -> tuple[Path, Path]:
    catalog_path = tmp_path / 'catalog.yaml'
    golden_path = tmp_path / 'golden.yaml'

    catalog_path.write_text(
        '\n'.join(
            [
                'version: "1.0"',
                'documents:',
                '  - doc_id: d1',
                '    title: "Doc 1"',
                '    filename: "doc1.pdf"',
                '    status: present',
                '  - doc_id: d_missing',
                '    title: "Missing Doc"',
                '    filename: ""',
                '    status: missing',
            ]
        ),
        encoding='utf-8',
    )

    golden_path.write_text(
        '\n'.join(
            [
                'meta:',
                '  docs:',
                '    d1: "Doc 1"',
                '    d_missing: "Missing Doc"',
                'questions:',
                '  - id: Q1',
                '    doc: d1',
                '    intent: reference',
                '    evidence: text',
                '    question: "What is the torque value?"',
                '  - id: Q2',
                '    doc: d_missing',
                '    intent: troubleshooting',
                '    evidence: text',
                '    question: "Any fault guidance?"',
            ]
        ),
        encoding='utf-8',
    )

    return catalog_path, golden_path


def test_run_golden_evaluation_reports_summary_and_missing_docs(tmp_path: Path) -> None:
    catalog_path, golden_path = _write_contracts(tmp_path)
    chunks = [
        Chunk(
            chunk_id='c1',
            doc_id='d1',
            content_type='text',
            page_start=3,
            page_end=3,
            content_text='Torque value is 45 Nm and should be verified during startup.',
        )
    ]

    output = run_golden_evaluation_use_case(
        RunGoldenEvaluationInput(
            catalog_path=catalog_path,
            golden_questions_path=golden_path,
            top_n=3,
        ),
        chunk_query=InMemoryChunkQuery(chunks),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
        trace_logger=None,
    )

    assert output.total_questions == 2
    assert output.passed_questions == 1
    assert output.failed_questions == 1
    assert output.missing_docs == ['d_missing']
    assert any(row.question_id == 'Q1' and row.pass_result for row in output.results)
    assert any(row.question_id == 'Q2' and row.answer_status == 'missing_doc' for row in output.results)


def test_run_golden_evaluation_uses_structured_output_mode(monkeypatch, tmp_path: Path) -> None:
    catalog_path, golden_path = _write_contracts(tmp_path)
    enforce_flags: list[bool] = []

    def _stub_answer_question_use_case(*args, **kwargs):
        _ = args
        enforce_flags.append(bool(kwargs.get('enforce_structured_output')))
        return AnswerQuestionOutput(
            query='What is the torque value?',
            intent='general',
            status='ok',
            confidence='medium',
            answer=(
                'Direct answer: Torque value is 45 Nm.\n'
                'Key details:\n'
                '- Sourced from table evidence.\n'
                'If missing data:\n'
                '- None identified in retrieved evidence.'
            ),
            follow_up_question=None,
            warnings=[],
            total_chunks_scanned=1,
            retrieved_chunk_ids=['c1'],
            citations=[],
            reasoning_summary=None,
        )

    monkeypatch.setattr(run_golden_module, 'answer_question_use_case', _stub_answer_question_use_case)

    output = run_golden_evaluation_use_case(
        RunGoldenEvaluationInput(
            catalog_path=catalog_path,
            golden_questions_path=golden_path,
            top_n=3,
        ),
        chunk_query=InMemoryChunkQuery([]),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
        trace_logger=None,
    )

    assert output.total_questions == 2
    assert enforce_flags == [True]
