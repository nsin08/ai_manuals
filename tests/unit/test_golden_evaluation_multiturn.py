from __future__ import annotations

from pathlib import Path

from packages.adapters.retrieval.hash_vector_search_adapter import HashVectorSearchAdapter
from packages.adapters.retrieval.simple_keyword_search_adapter import SimpleKeywordSearchAdapter
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
                'questions:',
                '  - id: MT1',
                '    doc: d1',
                '    intent: procedure',
                '    evidence: text',
                '    question_type: multi_turn',
                '    turn_count: 3',
                '    question: "Step 1: torque setup prerequisites. Step 2: torque setup sequence. Step 3: torque verification."',
            ]
        ),
        encoding='utf-8',
    )

    return catalog_path, golden_path


def test_run_golden_evaluation_executes_multi_turn_sequence(tmp_path: Path) -> None:
    catalog_path, golden_path = _write_contracts(tmp_path)
    chunks = [
        Chunk(
            chunk_id='c1',
            doc_id='d1',
            content_type='text',
            page_start=3,
            page_end=3,
            content_text='Torque setup prerequisites include preload checks. Torque setup sequence and verification steps are documented.',
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

    assert output.total_questions == 1
    row = output.results[0]
    assert row.question_id == 'MT1'
    assert row.planned_turns == 3
    assert row.executed_turns == 3
    assert len(row.turn_prompts) == 3
    assert len(row.turn_statuses) == 3
