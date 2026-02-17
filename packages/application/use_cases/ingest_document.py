from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from packages.domain.models import Chunk
from packages.ports.chunk_store_port import ChunkStorePort
from packages.ports.ocr_port import OcrPort
from packages.ports.pdf_parser_port import PdfParserPort
from packages.ports.table_extractor_port import TableExtractorPort


@dataclass(frozen=True)
class IngestDocumentInput:
    doc_id: str
    pdf_path: Path


@dataclass(frozen=True)
class IngestDocumentOutput:
    doc_id: str
    asset_ref: str
    total_chunks: int
    by_type: dict[str, int]



def _new_chunk_id() -> str:
    return str(uuid.uuid4())



def _extract_figure_captions(page_text: str) -> list[str]:
    captions: list[str] = []
    for line in page_text.splitlines():
        s = line.strip()
        if not s:
            continue
        if re.match(r'^(figure|fig\.)\s*\d+', s, flags=re.IGNORECASE):
            captions.append(s)
    return captions



def ingest_document_use_case(
    input_data: IngestDocumentInput,
    pdf_parser: PdfParserPort,
    ocr_adapter: OcrPort,
    table_extractor: TableExtractorPort,
    chunk_store: ChunkStorePort,
) -> IngestDocumentOutput:
    pages = pdf_parser.parse(str(input_data.pdf_path))
    chunks: list[Chunk] = []
    by_type: dict[str, int] = {}

    def add_chunk(chunk: Chunk) -> None:
        chunks.append(chunk)
        by_type[chunk.content_type] = by_type.get(chunk.content_type, 0) + 1

    for page in pages:
        page_text = page.text.strip()

        if page_text:
            add_chunk(
                Chunk(
                    chunk_id=_new_chunk_id(),
                    doc_id=input_data.doc_id,
                    content_type='text',
                    page_start=page.page_number,
                    page_end=page.page_number,
                    content_text=page_text,
                )
            )
        else:
            ocr_text = ocr_adapter.extract_text(str(input_data.pdf_path), page.page_number).strip()
            if ocr_text:
                add_chunk(
                    Chunk(
                        chunk_id=_new_chunk_id(),
                        doc_id=input_data.doc_id,
                        content_type='figure_ocr',
                        page_start=page.page_number,
                        page_end=page.page_number,
                        content_text=ocr_text,
                    )
                )

        for table in table_extractor.extract(page_text, page.page_number):
            add_chunk(
                Chunk(
                    chunk_id=_new_chunk_id(),
                    doc_id=input_data.doc_id,
                    content_type='table',
                    page_start=page.page_number,
                    page_end=page.page_number,
                    content_text=table.text,
                    table_id=table.table_id,
                )
            )

        captions = _extract_figure_captions(page_text)
        for idx, caption in enumerate(captions, start=1):
            fig_id = f'fig-p{page.page_number:04d}-{idx:03d}'
            add_chunk(
                Chunk(
                    chunk_id=_new_chunk_id(),
                    doc_id=input_data.doc_id,
                    content_type='figure_caption',
                    page_start=page.page_number,
                    page_end=page.page_number,
                    content_text=caption,
                    figure_id=fig_id,
                    caption=caption,
                )
            )

            ocr_text = ocr_adapter.extract_text(str(input_data.pdf_path), page.page_number).strip()
            if ocr_text:
                add_chunk(
                    Chunk(
                        chunk_id=_new_chunk_id(),
                        doc_id=input_data.doc_id,
                        content_type='figure_ocr',
                        page_start=page.page_number,
                        page_end=page.page_number,
                        content_text=ocr_text,
                        figure_id=fig_id,
                    )
                )

    asset_ref = chunk_store.persist(input_data.doc_id, chunks)

    return IngestDocumentOutput(
        doc_id=input_data.doc_id,
        asset_ref=asset_ref,
        total_chunks=len(chunks),
        by_type=by_type,
    )
