from __future__ import annotations

from pathlib import Path

from packages.application.use_cases.ingest_document import (
    IngestDocumentInput,
    ingest_document_use_case,
)
from packages.domain.models import Chunk
from packages.ports.chunk_store_port import ChunkStorePort
from packages.ports.embedding_port import EmbeddingPort
from packages.ports.ocr_port import OcrPort
from packages.ports.pdf_parser_port import ParsedPdfPage, PdfParserPort
from packages.ports.table_extractor_port import ExtractedTable, TableExtractorPort


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
    def extract(self, page_text: str, page_number: int) -> list[ExtractedTable]:
        if page_number != 1:
            return []
        return [ExtractedTable(table_id='table-1', page_number=1, text='A B C\\n10 20 30')]


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
    assert result.by_type.get('table', 0) >= 1
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
