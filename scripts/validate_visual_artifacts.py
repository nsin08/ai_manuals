from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.adapters.data_contracts.visual_artifacts import validate_visual_artifacts


def _parse_doc_ids(value: str | None) -> list[str] | None:
    if not value:
        return None
    out = [item.strip() for item in value.split(',')]
    parsed = [item for item in out if item]
    return parsed or None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Validate visual chunk/embedding artifact contract')
    parser.add_argument('--assets-dir', type=Path, default=Path('data/assets'))
    parser.add_argument('--doc-id', default=None, help='Optional comma-separated doc ids')
    parser.add_argument('--strict', action='store_true')
    parser.add_argument('--output', type=Path, default=None, help='Optional JSON report path')
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    doc_ids = _parse_doc_ids(args.doc_id)
    results = validate_visual_artifacts(args.assets_dir, doc_ids=doc_ids, strict=args.strict)

    payload: dict[str, object] = {
        'assets_dir': str(args.assets_dir),
        'strict': bool(args.strict),
        'doc_count': len(results),
        'error_count': 0,
        'warning_count': 0,
        'docs': {},
    }

    docs_payload: dict[str, object] = {}
    for doc_id, result in results.items():
        payload['error_count'] = int(payload['error_count']) + len(result.errors)
        payload['warning_count'] = int(payload['warning_count']) + len(result.warnings)
        docs_payload[doc_id] = {
            'valid': result.is_valid(),
            'errors': result.errors,
            'warnings': result.warnings,
        }
    payload['docs'] = docs_payload

    text = json.dumps(payload, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding='utf-8')

    print(text)
    return 1 if int(payload['error_count']) > 0 else 0


if __name__ == '__main__':
    raise SystemExit(main())
