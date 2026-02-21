from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.adapters.data_contracts.visual_artifact_generation import (
    build_visual_artifacts_from_chunks,
    load_chunk_rows,
    write_visual_artifacts,
)


def _parse_doc_ids(value: str | None) -> list[str] | None:
    if not value:
        return None
    rows = [item.strip() for item in value.split(',')]
    out = [item for item in rows if item]
    return out or None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Generate visual artifact files from existing chunks.jsonl')
    parser.add_argument('--assets-dir', type=Path, default=Path('data/assets'))
    parser.add_argument('--doc-id', default=None, help='Optional comma-separated doc ids')
    parser.add_argument('--output', type=Path, default=None, help='Optional JSON summary path')
    return parser.parse_args()


def _discover_doc_ids(assets_dir: Path) -> list[str]:
    if not assets_dir.exists():
        return []
    return sorted(
        row.name
        for row in assets_dir.iterdir()
        if row.is_dir() and (row / 'chunks.jsonl').exists()
    )


def main() -> int:
    args = parse_args()
    selected = _parse_doc_ids(args.doc_id) or _discover_doc_ids(args.assets_dir)
    if not selected:
        raise SystemExit('No doc ids found for generation')

    payload: dict[str, object] = {'assets_dir': str(args.assets_dir), 'docs': {}, 'total_docs': 0}
    docs_payload: dict[str, object] = {}

    for doc_id in selected:
        doc_dir = args.assets_dir / doc_id
        chunk_rows = load_chunk_rows(doc_dir / 'chunks.jsonl')
        visual_rows, embedding_rows, manifest = build_visual_artifacts_from_chunks(doc_id, chunk_rows)
        write_visual_artifacts(doc_dir, visual_rows, embedding_rows, manifest)
        docs_payload[doc_id] = {
            'source_chunks': len(chunk_rows),
            'visual_chunk_count': len(visual_rows),
            'embedding_count': len(embedding_rows),
        }

    payload['docs'] = docs_payload
    payload['total_docs'] = len(docs_payload)

    text = json.dumps(payload, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding='utf-8')
    print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
