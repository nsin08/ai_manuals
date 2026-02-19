from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Callable

from packages.domain.models import Chunk
from packages.ports.chunk_store_port import ChunkStorePort
from packages.ports.embedding_port import EmbeddingPort
from packages.ports.ocr_port import OcrPort
from packages.ports.pdf_parser_port import ParsedPdfPage, PdfParserPort
from packages.ports.table_extractor_port import TableExtractorPort
from packages.ports.vision_port import VisionPort


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


@dataclass(frozen=True)
class _PageProcessingOutput:
    page_number: int
    chunks: list[Chunk]
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


def _should_attempt_ocr(page_text: str) -> bool:
    compact = re.sub(r'\s+', ' ', page_text or '').strip()
    return len(compact) < 80


def _should_attempt_vision(*, page_text: str, page_ocr_text: str, captions: list[str]) -> bool:
    compact_text = re.sub(r'\s+', ' ', page_text or '').strip()
    compact_ocr = re.sub(r'\s+', ' ', page_ocr_text or '').strip()
    if captions:
        return True
    if len(compact_text) < 220 and len(compact_ocr) < 220:
        return True
    return False


def _process_single_page(
    *,
    doc_id: str,
    pdf_path: Path,
    page: ParsedPdfPage,
    ocr_adapter: OcrPort,
    table_extractor: TableExtractorPort,
    vision_adapter: VisionPort | None,
    vision_budget: dict[str, int],
    vision_budget_lock: Lock,
) -> _PageProcessingOutput:
    page_chunks: list[Chunk] = []
    page_by_type: dict[str, int] = {}

    def add_chunk(chunk: Chunk) -> None:
        page_chunks.append(chunk)
        page_by_type[chunk.content_type] = page_by_type.get(chunk.content_type, 0) + 1

    page_text = page.text.strip()
    page_ocr_text = ''

    if _should_attempt_ocr(page_text):
        page_ocr_text = ocr_adapter.extract_text(str(pdf_path), page.page_number).strip()

    if page_text:
        add_chunk(
            Chunk(
                chunk_id=_new_chunk_id(),
                doc_id=doc_id,
                content_type='text',
                page_start=page.page_number,
                page_end=page.page_number,
                content_text=page_text,
            )
        )

    if page_ocr_text:
        add_chunk(
            Chunk(
                chunk_id=_new_chunk_id(),
                doc_id=doc_id,
                content_type='figure_ocr',
                page_start=page.page_number,
                page_end=page.page_number,
                content_text=page_ocr_text,
            )
        )

    table_source_text = page_text if page_text else page_ocr_text
    for table in table_extractor.extract(table_source_text, page.page_number):
        add_chunk(
            Chunk(
                chunk_id=_new_chunk_id(),
                doc_id=doc_id,
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
                doc_id=doc_id,
                content_type='figure_caption',
                page_start=page.page_number,
                page_end=page.page_number,
                content_text=caption,
                figure_id=fig_id,
                caption=caption,
            )
        )

        figure_ocr_text = page_ocr_text or ocr_adapter.extract_text(str(pdf_path), page.page_number).strip()
        if figure_ocr_text:
            add_chunk(
                Chunk(
                    chunk_id=_new_chunk_id(),
                    doc_id=doc_id,
                    content_type='figure_ocr',
                    page_start=page.page_number,
                    page_end=page.page_number,
                    content_text=figure_ocr_text,
                    figure_id=fig_id,
                )
            )

    should_call_vision = (
        vision_adapter is not None
        and _should_attempt_vision(
            page_text=page_text,
            page_ocr_text=page_ocr_text,
            captions=captions,
        )
    )

    reserved_slot = False
    if should_call_vision:
        with vision_budget_lock:
            if vision_budget['remaining'] > 0:
                vision_budget['remaining'] -= 1
                reserved_slot = True

    if should_call_vision and reserved_slot and vision_adapter is not None:
        vision_text = vision_adapter.extract_page_insights(
            pdf_path=str(pdf_path),
            page_number=page.page_number,
        ).strip()
        if vision_text:
            add_chunk(
                Chunk(
                    chunk_id=_new_chunk_id(),
                    doc_id=doc_id,
                    content_type='vision_summary',
                    page_start=page.page_number,
                    page_end=page.page_number,
                    content_text=vision_text,
                )
            )
        else:
            with vision_budget_lock:
                vision_budget['remaining'] += 1

    return _PageProcessingOutput(
        page_number=page.page_number,
        chunks=page_chunks,
        by_type=page_by_type,
    )


def ingest_document_use_case(
    input_data: IngestDocumentInput,
    pdf_parser: PdfParserPort,
    ocr_adapter: OcrPort,
    table_extractor: TableExtractorPort,
    chunk_store: ChunkStorePort,
    embedding_adapter: EmbeddingPort | None = None,
    vision_adapter: VisionPort | None = None,
    vision_max_pages: int = 40,
    page_workers: int = 1,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> IngestDocumentOutput:
    pages = pdf_parser.parse(str(input_data.pdf_path))
    chunks: list[Chunk] = []
    by_type: dict[str, int] = {}
    total_pages = len(pages)

    if progress_callback is not None:
        progress_callback(
            {
                'stage': 'extracting',
                'processed_pages': 0,
                'total_pages': total_pages,
                'message': 'Starting page extraction',
            }
        )

    vision_budget = {'remaining': max(vision_max_pages, 0)}
    vision_budget_lock = Lock()

    page_outputs: list[_PageProcessingOutput] = []
    normalized_workers = max(int(page_workers or 1), 1)

    if normalized_workers <= 1 or total_pages <= 1:
        for idx, page in enumerate(pages, start=1):
            page_output = _process_single_page(
                doc_id=input_data.doc_id,
                pdf_path=input_data.pdf_path,
                page=page,
                ocr_adapter=ocr_adapter,
                table_extractor=table_extractor,
                vision_adapter=vision_adapter,
                vision_budget=vision_budget,
                vision_budget_lock=vision_budget_lock,
            )
            page_outputs.append(page_output)
            if progress_callback is not None:
                progress_callback(
                    {
                        'stage': 'extracting',
                        'processed_pages': idx,
                        'total_pages': total_pages,
                        'message': f'Processed page {idx}/{total_pages}',
                    }
                )
    else:
        processed = 0
        with ThreadPoolExecutor(max_workers=normalized_workers) as executor:
            futures = [
                executor.submit(
                    _process_single_page,
                    doc_id=input_data.doc_id,
                    pdf_path=input_data.pdf_path,
                    page=page,
                    ocr_adapter=ocr_adapter,
                    table_extractor=table_extractor,
                    vision_adapter=vision_adapter,
                    vision_budget=vision_budget,
                    vision_budget_lock=vision_budget_lock,
                )
                for page in pages
            ]
            for future in as_completed(futures):
                page_outputs.append(future.result())
                processed += 1
                if progress_callback is not None:
                    progress_callback(
                        {
                            'stage': 'extracting',
                            'processed_pages': processed,
                            'total_pages': total_pages,
                            'message': f'Processed page {processed}/{total_pages}',
                        }
                    )

    page_outputs.sort(key=lambda row: row.page_number)
    for page_output in page_outputs:
        chunks.extend(page_output.chunks)
        for chunk_type, count in page_output.by_type.items():
            by_type[chunk_type] = by_type.get(chunk_type, 0) + count

    if embedding_adapter is not None:
        if progress_callback is not None:
            progress_callback(
                {
                    'stage': 'embedding',
                    'processed_pages': total_pages,
                    'total_pages': total_pages,
                    'message': f'Computing embeddings for {len(chunks)} chunks',
                }
            )

        enriched: list[Chunk] = []
        for chunk in chunks:
            embedding = embedding_adapter.embed_text(chunk.content_text)
            metadata = dict(chunk.metadata or {})
            if embedding:
                metadata['embedding'] = embedding
            enriched.append(
                Chunk(
                    chunk_id=chunk.chunk_id,
                    doc_id=chunk.doc_id,
                    content_type=chunk.content_type,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    content_text=chunk.content_text,
                    section_path=chunk.section_path,
                    figure_id=chunk.figure_id,
                    table_id=chunk.table_id,
                    caption=chunk.caption,
                    asset_ref=chunk.asset_ref,
                    metadata=metadata,
                )
            )
        chunks = enriched

    asset_ref = chunk_store.persist(input_data.doc_id, chunks)

    if progress_callback is not None:
        progress_callback(
            {
                'stage': 'persisted',
                'processed_pages': total_pages,
                'total_pages': total_pages,
                'message': f'Persisted {len(chunks)} chunks',
            }
        )

    return IngestDocumentOutput(
        doc_id=input_data.doc_id,
        asset_ref=asset_ref,
        total_chunks=len(chunks),
        by_type=by_type,
    )

