from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

from packages.domain.models import Chunk
from packages.ports.chunk_query_port import ChunkQueryPort


class FilesystemChunkQueryAdapter(ChunkQueryPort):
    def __init__(self, assets_dir: Path) -> None:
        self._assets_dir = assets_dir

    def list_chunks(self, doc_id: str | None = None) -> list[Chunk]:
        if not self._assets_dir.exists():
            return []

        docs: list[Path]
        if doc_id:
            docs = [self._assets_dir / doc_id]
        else:
            docs = [p for p in self._assets_dir.iterdir() if p.is_dir()]

        chunks: list[Chunk] = []
        valid_keys = {f.name for f in fields(Chunk)}

        for doc_path in docs:
            chunks.extend(self._load_text_chunks(doc_path, valid_keys))
            chunks.extend(self._load_visual_chunks(doc_path))

        return chunks

    def _load_text_chunks(self, doc_path: Path, valid_keys: set[str]) -> list[Chunk]:
        out: list[Chunk] = []
        jsonl_path = doc_path / 'chunks.jsonl'
        if not jsonl_path.exists():
            return out

        with jsonl_path.open('r', encoding='utf-8') as fh:
            for line in fh:
                if not line.strip():
                    continue
                row = json.loads(line)
                payload = {k: row.get(k) for k in valid_keys}
                out.append(Chunk(**payload))
        return out

    def _load_visual_chunks(self, doc_path: Path) -> list[Chunk]:
        visual_path = doc_path / 'visual_chunks.jsonl'
        if not visual_path.exists():
            return []

        embedding_path = doc_path / 'visual_embeddings.jsonl'
        embeddings: dict[str, list[float]] = {}
        if embedding_path.exists():
            with embedding_path.open('r', encoding='utf-8') as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    chunk_id = str(row.get('chunk_id') or '').strip()
                    vector = row.get('embedding')
                    if chunk_id and isinstance(vector, list):
                        embeddings[chunk_id] = vector

        out: list[Chunk] = []
        with visual_path.open('r', encoding='utf-8') as fh:
            for line in fh:
                if not line.strip():
                    continue
                row = json.loads(line)
                chunk_id = str(row.get('chunk_id') or '').strip()
                row_doc_id = str(row.get('doc_id') or '').strip() or doc_path.name
                page = int(row.get('page') or 0)
                if not chunk_id or page <= 0:
                    continue

                caption_text = str(row.get('caption_text') or '').strip()
                ocr_text = str(row.get('ocr_text') or '').strip()
                modality = str(row.get('modality') or 'image').strip().lower()
                summary_parts = [part for part in [caption_text, ocr_text] if part]
                content_text = ' '.join(summary_parts) if summary_parts else f'{modality} visual evidence'
                metadata = {
                    'modality': modality,
                    'region_id': row.get('region_id'),
                    'bbox': row.get('bbox'),
                    'asset_relpath': row.get('asset_relpath'),
                    'source_chunk_id': row.get('source_chunk_id'),
                }
                embedding = embeddings.get(chunk_id)
                if embedding:
                    metadata['embedding'] = embedding

                out.append(
                    Chunk(
                        chunk_id=chunk_id,
                        doc_id=row_doc_id,
                        content_type=f'visual_{modality}',
                        page_start=page,
                        page_end=page,
                        content_text=content_text,
                        figure_id=row.get('figure_id'),
                        table_id=row.get('table_id'),
                        caption=caption_text or None,
                        metadata=metadata,
                    )
                )

        return out
