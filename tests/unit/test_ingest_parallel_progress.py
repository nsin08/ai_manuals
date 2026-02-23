from __future__ import annotations

from pathlib import Path

from packages.application.use_cases.ingest_document import (
    IngestDocumentInput,
    ingest_document_use_case,
)
from packages.domain.models import Chunk
from packages.ports.chunk_store_port import ChunkStorePort
from packages.ports.ocr_port import OcrPort
from packages.ports.pdf_parser_port import ParsedPdfPage, PdfParserPort
from packages.ports.table_extractor_port import ExtractedTable, ExtractedTableRow, TableExtractorPort


class FakePdfParser(PdfParserPort):
    def parse(self, pdf_path: str) -> list[ParsedPdfPage]:
        _ = pdf_path
        return [
            ParsedPdfPage(page_number=1, text='Figure 1 Motor'),
            ParsedPdfPage(page_number=2, text='Routine maintenance steps'),
            ParsedPdfPage(page_number=3, text='Figure 2 Control block'),
        ]


class FakeOcr(OcrPort):
    def extract_text(self, source_path: str, page_number: int) -> str:
        _ = source_path
        if page_number in {1, 3}:
            return 'ocr labels'
        return ''


class FakeTables(TableExtractorPort):
    def extract(self, page_text: str, page_number: int, doc_id: str = '') -> list[ExtractedTable]:
        _ = page_text
        if page_number == 2:
            row = ExtractedTableRow(
                table_id='table-2', page_number=2, row_index=0,
                headers=[], row_cells=['fault', 'cause', 'remedy'],
                units=['', '', ''], raw_text='fault cause remedy'
            )
            return [ExtractedTable(table_id='table-2', page_number=2, rows=[row], raw_text='fault cause remedy')]
        return []


class InMemoryChunkStore(ChunkStorePort):
    def __init__(self) -> None:
        self.saved: list[Chunk] = []

    def persist(self, doc_id: str, chunks: list[Chunk]) -> str:
        _ = doc_id
        self.saved = list(chunks)
        return 'memory://chunks'


def test_ingest_reports_page_progress_with_parallel_workers() -> None:
    store = InMemoryChunkStore()
    events: list[dict[str, object]] = []

    result = ingest_document_use_case(
        IngestDocumentInput(doc_id='doc-progress', pdf_path=Path('ignored.pdf')),
        pdf_parser=FakePdfParser(),
        ocr_adapter=FakeOcr(),
        table_extractor=FakeTables(),
        chunk_store=store,
        page_workers=3,
        progress_callback=lambda payload: events.append(dict(payload)),
    )

    assert result.total_chunks == len(store.saved)
    assert any(row.get('stage') == 'extracting' for row in events)
    assert events[-1].get('stage') == 'persisted'
    assert events[-1].get('processed_pages') == 3
    assert events[-1].get('total_pages') == 3
