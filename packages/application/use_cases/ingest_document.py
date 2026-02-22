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
    embedding_attempted: bool = False
    embedding_success_count: int = 0
    embedding_failed_count: int = 0
    embedding_coverage: float = 0.0
    embedding_failed_chunk_ids: list[str] | None = None
    embedding_failure_reasons: dict[str, str] | None = None
    embedding_second_pass_attempted: bool = False
    embedding_second_pass_recovered: int = 0
    warnings: list[str] | None = None


@dataclass(frozen=True)
class _PageProcessingOutput:
    page_number: int
    chunks: list[Chunk]
    by_type: dict[str, int]


def _new_chunk_id() -> str:
    return str(uuid.uuid4())


def _copy_chunk_with_metadata(chunk: Chunk, metadata: dict[str, Any]) -> Chunk:
    return Chunk(
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
    # Dimension-annotation pages: many isolated numeric callouts (e.g. CAD
    # drawings), very few prose words.  PyPDF extracts dimension numbers as
    # disconnected tokens — a vision model sees the full drawing and can
    # answer dimension queries that raw text extraction misses.
    numeric_tokens = re.findall(r'\b\d+(?:\.\d+)?\b', compact_text)
    prose_words = re.findall(r'[A-Za-z]{4,}', compact_text)
    if len(numeric_tokens) >= 5 and len(prose_words) <= 8:
        return True
    # General low-content pages (raised threshold from 220 to 400 chars).
    if len(compact_text) < 400 and len(compact_ocr) < 400:
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
    figure_regions: list[dict[str, Any]] | None = None,
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
    for table in table_extractor.extract(table_source_text, page.page_number, doc_id):
        for row in table.rows:
            row_text = (
                ' | '.join(row.headers) + ' || ' + ' | '.join(row.row_cells)
                if row.headers
                else ' | '.join(row.row_cells)
            )
            add_chunk(
                Chunk(
                    chunk_id=_new_chunk_id(),
                    doc_id=doc_id,
                    content_type='table_row',
                    page_start=page.page_number,
                    page_end=page.page_number,
                    content_text=row_text,
                    table_id=row.table_id,
                    metadata={
                        'table_id': row.table_id,
                        'row_index': row.row_index,
                        'headers': row.headers,
                        'units': row.units,
                    },
                )
            )

    captions = _extract_figure_captions(page_text)
    for idx, caption in enumerate(captions, start=1):
        fig_id = f'fig-p{page.page_number:04d}-{idx:03d}'
        fig_bbox = (
            figure_regions[idx - 1].get('bbox')
            if figure_regions and idx <= len(figure_regions)
            else None
        )
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
                metadata={'bbox': fig_bbox} if fig_bbox is not None else None,
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
                    metadata={'bbox': fig_bbox} if fig_bbox is not None else None,
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
    embedding_min_coverage: float = 0.0,
    embedding_fail_fast: bool = False,
    embedding_second_pass_max_chars: int = 2048,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> IngestDocumentOutput:
    pages = pdf_parser.parse(str(input_data.pdf_path))
    chunks: list[Chunk] = []
    by_type: dict[str, int] = {}
    total_pages = len(pages)

    # Pre-extract figure bounding boxes using fitz when available.
    page_figure_regions: dict[int, list[dict[str, Any]]] = {}
    try:
        from packages.adapters.data_contracts.visual_artifact_generation import (  # noqa: PLC0415
            _extract_figure_regions as _efr,
        )
        import fitz as _fitz  # noqa: PLC0415

        with _fitz.open(str(input_data.pdf_path)) as _doc:
            for _fp in _doc:
                _pn = _fp.number + 1
                page_figure_regions[_pn] = _efr(_fp, input_data.doc_id, _pn)
    except Exception:  # fitz/import not available or any parse error
        pass

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
                figure_regions=page_figure_regions.get(page.page_number),
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
                    figure_regions=page_figure_regions.get(page.page_number),
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

    embedding_attempted = False
    embedding_success_count = 0
    embedding_failed_count = 0
    embedding_failed_chunk_ids: list[str] = []
    embedding_failure_reasons: dict[str, str] = {}
    embedding_second_pass_attempted = False
    embedding_second_pass_recovered = 0
    warnings: list[str] = []

    if embedding_adapter is not None:
        embedding_attempted = True
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
        failed_positions: list[int] = []

        for idx, chunk in enumerate(chunks):
            embedding = embedding_adapter.embed_text(chunk.content_text)
            metadata = dict(chunk.metadata or {})
            if embedding:
                metadata['embedding'] = embedding
                embedding_success_count += 1
            else:
                embedding_failed_count += 1
                embedding_failed_chunk_ids.append(chunk.chunk_id)
                adapter_error = getattr(embedding_adapter, 'last_error', None)
                if isinstance(adapter_error, str) and adapter_error.strip():
                    embedding_failure_reasons[chunk.chunk_id] = adapter_error.strip()
                else:
                    embedding_failure_reasons[chunk.chunk_id] = 'embedding-returned-empty-vector'
                failed_positions.append(idx)

            enriched.append(_copy_chunk_with_metadata(chunk, metadata))

        if failed_positions:
            embedding_second_pass_attempted = True
            if progress_callback is not None:
                progress_callback(
                    {
                        'stage': 'embedding',
                        'processed_pages': total_pages,
                        'total_pages': total_pages,
                        'message': (
                            f'Second-pass embedding retry for {len(failed_positions)} failed chunks'
                        ),
                    }
                )

            normalized_retry_chars = max(0, int(embedding_second_pass_max_chars or 0))
            for position in failed_positions:
                failed_chunk = enriched[position]
                retry_candidates: list[str] = []
                if normalized_retry_chars > 0:
                    candidate_lengths = [normalized_retry_chars, 1536, 1024, 768]
                    seen_lengths: set[int] = set()
                    for length in candidate_lengths:
                        normalized_length = max(1, min(length, len(failed_chunk.content_text)))
                        if normalized_length in seen_lengths:
                            continue
                        seen_lengths.add(normalized_length)
                        retry_candidates.append(failed_chunk.content_text[:normalized_length])
                else:
                    retry_candidates.append(failed_chunk.content_text)

                retried_embedding: list[float] = []
                for retry_text in retry_candidates:
                    retried_embedding = embedding_adapter.embed_text(retry_text)
                    if retried_embedding:
                        break
                    adapter_error = getattr(embedding_adapter, 'last_error', None)
                    if isinstance(adapter_error, str) and adapter_error.strip():
                        embedding_failure_reasons[failed_chunk.chunk_id] = adapter_error.strip()

                if not retried_embedding:
                    continue

                retry_metadata = dict(failed_chunk.metadata or {})
                retry_metadata['embedding'] = retried_embedding
                enriched[position] = _copy_chunk_with_metadata(failed_chunk, retry_metadata)
                embedding_second_pass_recovered += 1
                embedding_success_count += 1
                embedding_failed_count -= 1
                if failed_chunk.chunk_id in embedding_failed_chunk_ids:
                    embedding_failed_chunk_ids.remove(failed_chunk.chunk_id)
                embedding_failure_reasons.pop(failed_chunk.chunk_id, None)
        chunks = enriched

        total_embedding_targets = max(len(chunks), 1)
        embedding_coverage = embedding_success_count / total_embedding_targets
        if embedding_second_pass_recovered > 0:
            warnings.append(
                f'Second-pass embedding recovered {embedding_second_pass_recovered} chunks.'
            )
        if embedding_failed_count > 0:
            warnings.append(
                f'Embedding unavailable for {embedding_failed_count}/{len(chunks)} chunks '
                f'({embedding_coverage:.2%} coverage).'
            )
        min_coverage = max(0.0, min(float(embedding_min_coverage or 0.0), 1.0))
        if embedding_fail_fast and embedding_coverage < min_coverage:
            raise ValueError(
                'Embedding coverage below threshold: '
                f'{embedding_coverage:.2%} < {min_coverage:.2%}. '
                f'Failed chunks: {len(embedding_failed_chunk_ids)}'
            )
    else:
        embedding_coverage = 0.0

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
        embedding_attempted=embedding_attempted,
        embedding_success_count=embedding_success_count,
        embedding_failed_count=embedding_failed_count,
        embedding_coverage=round(embedding_coverage, 6) if embedding_attempted else 0.0,
        embedding_failed_chunk_ids=embedding_failed_chunk_ids if embedding_attempted else [],
        embedding_failure_reasons=embedding_failure_reasons if embedding_attempted else {},
        embedding_second_pass_attempted=embedding_second_pass_attempted,
        embedding_second_pass_recovered=embedding_second_pass_recovered,
        warnings=warnings,
    )

