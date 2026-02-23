from __future__ import annotations

from pathlib import Path

import pytest

from packages.application.use_cases.ingest_document import (
    IngestDocumentInput,
    ingest_document_use_case,
)
from packages.domain.models import Chunk
from packages.ports.chunk_store_port import ChunkStorePort
from packages.ports.embedding_port import EmbeddingPort
from packages.ports.ocr_port import OcrPort
from packages.ports.pdf_parser_port import ParsedPdfPage, PdfParserPort
from packages.ports.table_extractor_port import ExtractedTable, ExtractedTableRow, TableExtractorPort


class FakePdfParser(PdfParserPort):
    def parse(self, pdf_path: str) -> list[ParsedPdfPage]:
        _ = pdf_path
        return [
            ParsedPdfPage(page_number=1, text='Figure 1 Motor layout\\nA  B  C\\n10 20 30'),
            ParsedPdfPage(page_number=2, text='General notes and warnings'),
        ]


class FakeOcr(OcrPort):
    def extract_text(self, source_path: str, page_number: int) -> str:
        _ = source_path
        return 'OCR labels text' if page_number == 1 else ''


class FakeTables(TableExtractorPort):
    def extract(self, page_text: str, page_number: int, doc_id: str = '') -> list[ExtractedTable]:
        if page_number != 1:
            return []
        row = ExtractedTableRow(
            table_id='table-1', page_number=1, row_index=0,
            headers=['A', 'B', 'C'], row_cells=['10', '20', '30'],
            units=['', '', ''], raw_text='A B C\\n10 20 30'
        )
        return [ExtractedTable(table_id='table-1', page_number=1, rows=[row], raw_text='A B C\\n10 20 30')]


class InMemoryChunkStore(ChunkStorePort):
    def __init__(self) -> None:
        self.saved: list[Chunk] = []

    def persist(self, doc_id: str, chunks: list[Chunk]) -> str:
        _ = doc_id
        self.saved = list(chunks)
        return 'memory://chunks'


class FakeEmbedding(EmbeddingPort):
    def embed_text(self, text: str) -> list[float]:
        return [float(len(text or '')), 1.0]


class FlakyEmbedding(EmbeddingPort):
    def __init__(self) -> None:
        self._seen: dict[str, int] = {}

    def embed_text(self, text: str) -> list[float]:
        value = (text or '').lower()
        self._seen[value] = self._seen.get(value, 0) + 1
        if ('acro-set' in value or 'figure' in value) and self._seen[value] == 1:
            return []
        return [float(len(text or '')), 1.0]


class AlwaysFailEmbedding(EmbeddingPort):
    @property
    def last_error(self) -> str:
        return 'simulated-embedding-failure'

    def embed_text(self, text: str) -> list[float]:
        _ = text
        return []



def test_ingest_document_produces_expected_chunk_types() -> None:
    store = InMemoryChunkStore()

    result = ingest_document_use_case(
        IngestDocumentInput(doc_id='doc-x', pdf_path=Path('ignored.pdf')),
        pdf_parser=FakePdfParser(),
        ocr_adapter=FakeOcr(),
        table_extractor=FakeTables(),
        chunk_store=store,
    )

    assert result.total_chunks == len(store.saved)
    assert result.by_type.get('text', 0) >= 2
    assert result.by_type.get('table_row', 0) >= 1
    assert result.by_type.get('figure_caption', 0) >= 1
    assert result.by_type.get('figure_ocr', 0) >= 1


def test_ingest_document_attaches_embeddings_when_adapter_provided() -> None:
    store = InMemoryChunkStore()
    ingest_document_use_case(
        IngestDocumentInput(doc_id='doc-embed', pdf_path=Path('ignored.pdf')),
        pdf_parser=FakePdfParser(),
        ocr_adapter=FakeOcr(),
        table_extractor=FakeTables(),
        chunk_store=store,
        embedding_adapter=FakeEmbedding(),
    )

    assert store.saved
    assert any(isinstance(chunk.metadata.get('embedding'), list) for chunk in store.saved)


def test_ingest_document_reports_embedding_coverage_and_warnings() -> None:
    store = InMemoryChunkStore()
    result = ingest_document_use_case(
        IngestDocumentInput(doc_id='doc-embed-warn', pdf_path=Path('ignored.pdf')),
        pdf_parser=FakePdfParser(),
        ocr_adapter=FakeOcr(),
        table_extractor=FakeTables(),
        chunk_store=store,
        embedding_adapter=FlakyEmbedding(),
    )

    assert result.embedding_attempted
    assert result.embedding_second_pass_attempted
    assert result.embedding_second_pass_recovered > 0
    assert result.embedding_failed_count == 0
    assert result.embedding_coverage == 1.0
    assert result.warnings
    assert any('Second-pass embedding recovered' in warning for warning in result.warnings)


def test_ingest_document_can_fail_fast_on_low_embedding_coverage() -> None:
    store = InMemoryChunkStore()
    with pytest.raises(ValueError):
        ingest_document_use_case(
            IngestDocumentInput(doc_id='doc-embed-fail-fast', pdf_path=Path('ignored.pdf')),
            pdf_parser=FakePdfParser(),
            ocr_adapter=FakeOcr(),
            table_extractor=FakeTables(),
            chunk_store=store,
            embedding_adapter=AlwaysFailEmbedding(),
            embedding_min_coverage=0.95,
            embedding_fail_fast=True,
        )


def test_ingest_document_reports_failure_reasons_when_embedding_still_fails() -> None:
    store = InMemoryChunkStore()
    result = ingest_document_use_case(
        IngestDocumentInput(doc_id='doc-embed-reasons', pdf_path=Path('ignored.pdf')),
        pdf_parser=FakePdfParser(),
        ocr_adapter=FakeOcr(),
        table_extractor=FakeTables(),
        chunk_store=store,
        embedding_adapter=AlwaysFailEmbedding(),
    )

    assert result.embedding_attempted
    assert result.embedding_second_pass_attempted
    assert result.embedding_failed_count > 0
    assert result.embedding_failure_reasons
    assert all(
        reason == 'simulated-embedding-failure'
        for reason in result.embedding_failure_reasons.values()
    )
