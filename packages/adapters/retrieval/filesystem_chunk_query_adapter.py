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
            jsonl_path = doc_path / 'chunks.jsonl'
            if not jsonl_path.exists():
                continue

            with jsonl_path.open('r', encoding='utf-8') as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    payload = {k: row.get(k) for k in valid_keys}
                    chunks.append(Chunk(**payload))

        return chunks
