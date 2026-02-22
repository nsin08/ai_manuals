from __future__ import annotations

from pathlib import Path

from packages.adapters.reranker.noop_reranker_adapter import NoopRerankerAdapter
from packages.application.use_cases.ingest_document import (
    IngestDocumentInput,
    ingest_document_use_case,
)
from packages.domain.models import Chunk
from packages.ports.chunk_store_port import ChunkStorePort
from packages.ports.ocr_port import OcrPort
from packages.ports.pdf_parser_port import ParsedPdfPage, PdfParserPort
from packages.ports.reranker_port import RerankCandidate
from packages.ports.table_extractor_port import ExtractedTable, ExtractedTableRow, TableExtractorPort
from packages.ports.vision_port import VisionPort


class FakePdfParser(PdfParserPort):
    def parse(self, pdf_path: str) -> list[ParsedPdfPage]:
        _ = pdf_path
        return [ParsedPdfPage(page_number=1, text='Fig. 1'), ParsedPdfPage(page_number=2, text='')]


class FakeOcr(OcrPort):
    def extract_text(self, source_path: str, page_number: int) -> str:
        _ = source_path
        return 'motor label data' if page_number == 1 else ''


class FakeTables(TableExtractorPort):
    def extract(self, page_text: str, page_number: int, doc_id: str = '') -> list[ExtractedTable]:
        _ = page_text
        if page_number == 1:
            row = ExtractedTableRow(
                table_id='t1', page_number=1, row_index=0,
                headers=[], row_cells=['fault', 'cause', 'remedy'],
                units=['', '', ''], raw_text='fault cause remedy'
            )
            return [ExtractedTable(table_id='t1', page_number=1, rows=[row], raw_text='fault cause remedy')]
        return []


class FakeVision(VisionPort):
    def extract_page_insights(self, *, pdf_path: str, page_number: int) -> str:
        _ = pdf_path
        return f'vision summary page {page_number}'


class InMemoryChunkStore(ChunkStorePort):
    def __init__(self) -> None:
        self.saved: list[Chunk] = []

    def persist(self, doc_id: str, chunks: list[Chunk]) -> str:
        _ = doc_id
        self.saved = list(chunks)
        return 'memory://chunks'


def test_noop_reranker_keeps_base_order() -> None:
    candidates = [
        RerankCandidate(
            chunk_id='c1',
            doc_id='d',
            page_start=1,
            content_type='text',
            text='low',
            base_score=0.2,
        ),
        RerankCandidate(
            chunk_id='c2',
            doc_id='d',
            page_start=2,
            content_type='text',
            text='high',
            base_score=0.8,
        ),
    ]
    ranked = NoopRerankerAdapter().rerank(query='q', candidates=candidates, top_k=2)
    assert [row.chunk_id for row in ranked] == ['c2', 'c1']


def test_ingest_document_adds_vision_summary_chunks_when_enabled() -> None:
    store = InMemoryChunkStore()

    result = ingest_document_use_case(
        IngestDocumentInput(doc_id='doc-vision', pdf_path=Path('ignored.pdf')),
        pdf_parser=FakePdfParser(),
        ocr_adapter=FakeOcr(),
        table_extractor=FakeTables(),
        chunk_store=store,
        vision_adapter=FakeVision(),
        vision_max_pages=5,
    )

    assert result.by_type.get('vision_summary', 0) >= 1
    assert any(chunk.content_type == 'vision_summary' for chunk in store.saved)
