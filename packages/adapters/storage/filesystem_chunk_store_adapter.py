from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from packages.domain.models import Chunk
from packages.ports.chunk_store_port import ChunkStorePort


class FilesystemChunkStoreAdapter(ChunkStorePort):
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    def persist(self, doc_id: str, chunks: list[Chunk]) -> str:
        out_dir = self._base_dir / doc_id
        out_dir.mkdir(parents=True, exist_ok=True)

        out_path = out_dir / 'chunks.jsonl'
        with out_path.open('w', encoding='utf-8') as fh:
            for chunk in chunks:
                fh.write(json.dumps(asdict(chunk), ensure_ascii=True))
                fh.write('\n')

        return str(out_path)
