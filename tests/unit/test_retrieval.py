from __future__ import annotations

import json
from pathlib import Path

from packages.adapters.retrieval.filesystem_chunk_query_adapter import FilesystemChunkQueryAdapter
from packages.adapters.retrieval.hash_vector_search_adapter import HashVectorSearchAdapter
from packages.adapters.retrieval.retrieval_trace_logger import RetrievalTraceLogger
from packages.adapters.retrieval.simple_keyword_search_adapter import SimpleKeywordSearchAdapter
from packages.application.use_cases.search_evidence import SearchEvidenceInput, search_evidence_use_case
from packages.domain.models import Chunk
from packages.ports.chunk_query_port import ChunkQueryPort


class InMemoryChunkQuery(ChunkQueryPort):
    def __init__(self, chunks: list[Chunk]) -> None:
        self._chunks = chunks

    def list_chunks(self, doc_id: str | None = None) -> list[Chunk]:
        if doc_id is None:
            return list(self._chunks)
        return [c for c in self._chunks if c.doc_id == doc_id]



def _sample_chunks() -> list[Chunk]:
    return [
        Chunk(
            chunk_id='c1',
            doc_id='d1',
            content_type='table',
            page_start=10,
            page_end=10,
            content_text='Torque | 45 Nm\\nClearance | 0.2 mm',
        ),
        Chunk(
            chunk_id='c2',
            doc_id='d1',
            content_type='text',
            page_start=11,
            page_end=11,
            content_text='General installation and setup notes',
        ),
        Chunk(
            chunk_id='c3',
            doc_id='d2',
            content_type='figure_ocr',
            page_start=4,
            page_end=4,
            content_text='Terminal X1 pin 3 connects to enable input',
        ),
    ]



def test_keyword_search_prefers_relevant_chunk() -> None:
    chunks = _sample_chunks()
    results = SimpleKeywordSearchAdapter().search('torque clearance', chunks, top_k=3)

    assert results
    assert results[0].chunk.chunk_id == 'c1'



def test_vector_search_returns_non_empty_results() -> None:
    chunks = _sample_chunks()
    results = HashVectorSearchAdapter().search('enable input terminal', chunks, top_k=3)

    assert results
    assert any(item.chunk.chunk_id == 'c3' for item in results)



def test_search_evidence_applies_table_intent_weighting(tmp_path: Path) -> None:
    chunks = _sample_chunks()
    trace_file = tmp_path / 'traces.jsonl'

    output = search_evidence_use_case(
        SearchEvidenceInput(query='What is the torque spec in Nm?', top_n=3),
        chunk_query=InMemoryChunkQuery(chunks),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
        trace_logger=RetrievalTraceLogger(trace_file),
    )

    assert output.intent == 'table'
    assert output.hits
    assert output.hits[0].content_type in {'table', 'figure_ocr'}
    assert trace_file.exists()



def test_filesystem_chunk_query_reads_jsonl(tmp_path: Path) -> None:
    doc_dir = tmp_path / 'd1'
    doc_dir.mkdir(parents=True)
    (doc_dir / 'chunks.jsonl').write_text(
        '{"chunk_id":"a","doc_id":"d1","content_type":"text","page_start":1,"page_end":1,"content_text":"hello","section_path":null,"figure_id":null,"table_id":null,"caption":null,"asset_ref":null,"metadata":{}}\n',
        encoding='utf-8',
    )

    adapter = FilesystemChunkQueryAdapter(tmp_path)
    chunks = adapter.list_chunks('d1')

    assert len(chunks) == 1
    assert chunks[0].chunk_id == 'a'


def test_filesystem_chunk_query_reads_visual_chunks(tmp_path: Path) -> None:
    doc_dir = tmp_path / 'd1'
    doc_dir.mkdir(parents=True)
    (doc_dir / 'chunks.jsonl').write_text(
        '{"chunk_id":"a","doc_id":"d1","content_type":"text","page_start":1,"page_end":1,"content_text":"hello","section_path":null,"figure_id":null,"table_id":null,"caption":null,"asset_ref":null,"metadata":{}}\n',
        encoding='utf-8',
    )
    (doc_dir / 'visual_chunks.jsonl').write_text(
        '{"chunk_id":"v1","doc_id":"d1","page":2,"region_id":"r1","bbox":[0,0,1,1],"modality":"figure","figure_id":"f1","table_id":null,"caption_text":"motor block","ocr_text":"x1 terminal","linked_text_chunk_ids":["a"],"asset_relpath":"generated/p2_r1.png"}\n',
        encoding='utf-8',
    )
    (doc_dir / 'visual_embeddings.jsonl').write_text(
        '{"chunk_id":"v1","doc_id":"d1","provider":"derived","model":"chunk","dim":3,"embedding":[0.1,0.2,0.3]}\n',
        encoding='utf-8',
    )

    adapter = FilesystemChunkQueryAdapter(tmp_path)
    chunks = adapter.list_chunks('d1')
    ids = {chunk.chunk_id for chunk in chunks}
    assert ids == {'a', 'v1'}
    visual = next(chunk for chunk in chunks if chunk.chunk_id == 'v1')
    assert visual.content_type == 'visual_figure'
    assert visual.page_start == 2
    assert isinstance(visual.metadata.get('embedding'), list)


def test_search_evidence_trace_includes_modality_counts(tmp_path: Path) -> None:
    chunks = [
        Chunk(
            chunk_id='v1',
            doc_id='d1',
            content_type='visual_image',
            page_start=1,
            page_end=1,
            content_text='terminal wiring image',
            metadata={'embedding': [0.2, 0.3, 0.4]},
        ),
        Chunk(
            chunk_id='t1',
            doc_id='d1',
            content_type='text',
            page_start=2,
            page_end=2,
            content_text='terminal wiring notes',
            metadata={'embedding': [0.2, 0.3, 0.4]},
        ),
    ]
    trace_file = tmp_path / 'trace.jsonl'
    output = search_evidence_use_case(
        SearchEvidenceInput(query='terminal wiring', top_n=2),
        chunk_query=InMemoryChunkQuery(chunks),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
        trace_logger=RetrievalTraceLogger(trace_file),
    )
    assert output.hits
    lines = [row for row in trace_file.read_text(encoding='utf-8').splitlines() if row.strip()]
    assert lines
    payload = json.loads(lines[-1])
    assert 'scanned_modality_counts' in payload
    assert 'top_hit_modality_counts' in payload


def test_keyword_search_matches_hyphenated_compound_terms() -> None:
    chunks = [
        Chunk(
            chunk_id='c1',
            doc_id='d1',
            content_type='text',
            page_start=11,
            page_end=11,
            content_text='ACRO-SET is based on Hooke law and system spring rate.',
        ),
        Chunk(
            chunk_id='c2',
            doc_id='d1',
            content_type='text',
            page_start=2,
            page_end=2,
            content_text='What is this and what is that and it is general background text.',
        ),
    ]
    results = SimpleKeywordSearchAdapter().search('what is acroset', chunks, top_k=2)
    assert results
    assert results[0].chunk.chunk_id == 'c1'
