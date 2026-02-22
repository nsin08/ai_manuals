from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import fitz  # PyMuPDF — optional; only needed for live PDF bbox extraction
    _FITZ_AVAILABLE = True
except ImportError:  # pragma: no cover
    fitz = None  # type: ignore[assignment]
    _FITZ_AVAILABLE = False


def _extract_figure_regions(page: 'fitz.Page', doc_id: str, page_num: int) -> list[dict[str, Any]]:
    """Extract raster-image regions (type==1 blocks) with normalized bbox.

    Normalizes raw PyMuPDF point coordinates to [0, 1] range relative to page
    dimensions so coordinates are device-independent and portable to the UI layer.

    Args:
        page: fitz.Page object for the PDF page.
        doc_id: Document identifier used to build the figure_id.
        page_num: 1-based page number.

    Returns:
        List of dicts with keys: figure_id, bbox (4 floats [0,1]), page_number.
    """
    if not _FITZ_AVAILABLE:
        return []
    w, h = page.rect.width, page.rect.height
    if w <= 0 or h <= 0:
        return []
    regions: list[dict[str, Any]] = []
    for idx, block in enumerate(page.get_text('dict')['blocks']):
        if block.get('type') != 1:  # 1 == raster image block
            continue
        x0, y0, x1, y1 = block['bbox']
        norm_bbox = [
            round(x0 / w, 4),
            round(y0 / h, 4),
            round(x1 / w, 4),
            round(y1 / h, 4),
        ]
        figure_id = f'fig_{doc_id}_p{page_num:04d}_{idx:03d}'
        regions.append({'figure_id': figure_id, 'bbox': norm_bbox, 'page_number': page_num})
    return regions


def _bbox_from_text_block(block: dict[str, Any], page: 'fitz.Page') -> list[float]:
    """Normalize a text-block bbox (for table region metadata injection into chunks).

    Raw PyMuPDF bbox is in points (x0, y0, x1, y1).  Normalizes to [0, 1]
    using page.rect.width / height so they are device-independent.

    Args:
        block: A single block dict from page.get_text('dict')['blocks'].
        page: The fitz.Page the block belongs to.

    Returns:
        4-element list of floats, each in [0, 1].
    """
    w, h = page.rect.width, page.rect.height
    x0, y0, x1, y1 = block['bbox']
    return [
        round(x0 / w, 4),
        round(y0 / h, 4),
        round(x1 / w, 4),
        round(y1 / h, 4),
    ]


def _is_numeric_list(value: object) -> bool:
    if not isinstance(value, list) or not value:
        return False
    return all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value)


def load_chunk_rows(chunks_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not chunks_path.exists():
        return rows

    for raw in chunks_path.read_text(encoding='utf-8').splitlines():
        text = raw.strip()
        if not text:
            continue
        payload = json.loads(text)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def build_visual_artifacts_from_chunks(
    doc_id: str,
    chunk_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    text_chunk_ids_by_page: dict[int, list[str]] = {}
    for row in chunk_rows:
        if str(row.get('content_type') or '').strip() != 'text':
            continue
        page = int(row.get('page_start') or 0)
        chunk_id = str(row.get('chunk_id') or '').strip()
        if page <= 0 or not chunk_id:
            continue
        text_chunk_ids_by_page.setdefault(page, []).append(chunk_id)

    visual_rows: list[dict[str, Any]] = []
    embedding_rows: list[dict[str, Any]] = []
    visual_index = 0
    for row in chunk_rows:
        content_type = str(row.get('content_type') or '').strip().lower()
        if content_type not in {'figure_caption', 'figure_ocr', 'vision_summary', 'table', 'table_row'}:
            continue

        original_chunk_id = str(row.get('chunk_id') or '').strip()
        if not original_chunk_id:
            continue

        visual_index += 1
        page = int(row.get('page_start') or 0)
        if page <= 0:
            page = max(int(row.get('page_end') or 0), 1)
        figure_id = row.get('figure_id')
        table_id = row.get('table_id')

        modality = 'table' if content_type in {'table', 'table_row'} else ('figure' if 'figure' in content_type else 'image')
        region_id = (
            str(figure_id).strip()
            if figure_id
            else (str(table_id).strip() if table_id else f'r{visual_index:04d}')
        )
        visual_chunk_id = f'{doc_id}:visual:{visual_index:05d}'

        snippet = str(row.get('content_text') or '').strip()
        caption_text = str(row.get('caption') or '').strip()
        if not caption_text and modality == 'figure':
            caption_text = snippet[:240]

        visual_rows.append(
            {
                'chunk_id': visual_chunk_id,
                'doc_id': doc_id,
                'page': page,
                'region_id': region_id,
                'bbox': (row.get('metadata') or {}).get('bbox') or [0, 0, 1, 1],
                'modality': modality,
                'figure_id': figure_id,
                'table_id': table_id,
                'caption_text': caption_text,
                'ocr_text': snippet if content_type in {'figure_ocr', 'vision_summary'} else '',
                'linked_text_chunk_ids': text_chunk_ids_by_page.get(page, [])[:3],
                'asset_relpath': f'generated/page_{page:04d}_{region_id}.png',
                'vision_confidence': 0.5,
                'fallback_used': False,
                'source_chunk_id': original_chunk_id,
            }
        )

        metadata = row.get('metadata') or {}
        embedding = metadata.get('embedding') if isinstance(metadata, dict) else None
        if _is_numeric_list(embedding):
            embedding_rows.append(
                {
                    'chunk_id': visual_chunk_id,
                    'doc_id': doc_id,
                    'provider': str(metadata.get('embedding_provider') or 'derived'),
                    'model': str(metadata.get('embedding_model') or 'chunk-metadata'),
                    'dim': len(embedding),
                    'embedding': embedding,
                }
            )

    dims = sorted({int(row['dim']) for row in embedding_rows})
    manifest: dict[str, Any] = {
        'contract_version': 'visual-v1',
        'doc_id': doc_id,
        'visual_chunk_count': len(visual_rows),
        'embedding_count': len(embedding_rows),
        'provider': 'derived',
        'model': 'chunk-metadata',
    }
    if len(embedding_rows) > 0 and len(dims) == 1:
        manifest['embedding_dim'] = dims[0]
        manifest['provider'] = str(embedding_rows[0].get('provider') or 'derived')
        manifest['model'] = str(embedding_rows[0].get('model') or 'chunk-metadata')
    else:
        manifest['embedding_dim'] = 0
        if len(dims) > 1:
            manifest['warnings'] = ['inconsistent embedding dimensions in source metadata']

    return visual_rows, embedding_rows, manifest


def write_visual_artifacts(
    doc_assets_dir: Path,
    visual_rows: list[dict[str, Any]],
    embedding_rows: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> None:
    doc_assets_dir.mkdir(parents=True, exist_ok=True)

    chunks_path = doc_assets_dir / 'visual_chunks.jsonl'
    with chunks_path.open('w', encoding='utf-8') as fh:
        for row in visual_rows:
            fh.write(json.dumps(row, ensure_ascii=True))
            fh.write('\n')

    embed_path = doc_assets_dir / 'visual_embeddings.jsonl'
    with embed_path.open('w', encoding='utf-8') as fh:
        for row in embedding_rows:
            fh.write(json.dumps(row, ensure_ascii=True))
            fh.write('\n')

    manifest_path = doc_assets_dir / 'visual_manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
