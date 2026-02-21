from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from packages.adapters.data_contracts.contracts import ValidationResult

_CHUNK_FILE = 'visual_chunks.jsonl'
_EMBED_FILE = 'visual_embeddings.jsonl'
_MANIFEST_FILE = 'visual_manifest.json'
_LOW_CONFIDENCE_THRESHOLD = 0.45


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _as_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _load_json_lines(path: Path, result: ValidationResult, label: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        for line_no, raw in enumerate(path.read_text(encoding='utf-8').splitlines(), start=1):
            text = raw.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as exc:
                result.errors.append(f'{label}:{line_no} invalid JSON: {exc.msg}')
                continue
            if not isinstance(payload, dict):
                result.errors.append(f'{label}:{line_no} must be a JSON object')
                continue
            rows.append(payload)
    except FileNotFoundError:
        result.errors.append(f'{label} missing: {path}')
    return rows


def _load_manifest(path: Path, result: ValidationResult) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        result.errors.append(f'manifest missing: {path}')
        return {}
    except json.JSONDecodeError as exc:
        result.errors.append(f'manifest invalid JSON: {exc.msg}')
        return {}

    if not isinstance(payload, dict):
        result.errors.append('manifest must be a JSON object')
        return {}
    return payload


def validate_visual_artifacts_for_doc(doc_assets_dir: Path, strict: bool = False) -> ValidationResult:
    result = ValidationResult()
    doc_id = doc_assets_dir.name

    chunk_path = doc_assets_dir / _CHUNK_FILE
    embed_path = doc_assets_dir / _EMBED_FILE
    manifest_path = doc_assets_dir / _MANIFEST_FILE

    required_files = (
        (_CHUNK_FILE, chunk_path),
        (_EMBED_FILE, embed_path),
        (_MANIFEST_FILE, manifest_path),
    )

    missing_paths = [name for name, path in required_files if not path.exists()]
    for name in missing_paths:
        message = f'{doc_id}: missing required artifact file `{name}`'
        if strict:
            result.errors.append(message)
        else:
            result.warnings.append(message)

    if missing_paths:
        return result

    chunk_rows = _load_json_lines(chunk_path, result, f'{doc_id}:{_CHUNK_FILE}')
    embed_rows = _load_json_lines(embed_path, result, f'{doc_id}:{_EMBED_FILE}')
    manifest = _load_manifest(manifest_path, result)

    chunk_ids: set[str] = set()
    for idx, row in enumerate(chunk_rows, start=1):
        prefix = f'{doc_id}:{_CHUNK_FILE}:{idx}'
        chunk_id = str(row.get('chunk_id') or '').strip()
        if not chunk_id:
            result.errors.append(f'{prefix} missing chunk_id')
        elif chunk_id in chunk_ids:
            result.errors.append(f'{prefix} duplicate chunk_id `{chunk_id}`')
        else:
            chunk_ids.add(chunk_id)

        row_doc_id = str(row.get('doc_id') or '').strip()
        if row_doc_id != doc_id:
            result.errors.append(f'{prefix} doc_id mismatch `{row_doc_id}` != `{doc_id}`')

        page = _as_int(row.get('page'))
        if page is None or page < 1:
            result.errors.append(f'{prefix} page must be integer >= 1')

        region_id = str(row.get('region_id') or '').strip()
        if not region_id:
            result.errors.append(f'{prefix} missing region_id')

        bbox = row.get('bbox')
        if not isinstance(bbox, list) or len(bbox) != 4 or any(not _is_number(item) for item in bbox):
            result.errors.append(f'{prefix} bbox must be [x1, y1, x2, y2] numeric')

        modality = str(row.get('modality') or '').strip().lower()
        if modality not in {'figure', 'table', 'image'}:
            result.errors.append(f'{prefix} modality must be one of figure|table|image')

        asset_relpath = str(row.get('asset_relpath') or '').strip()
        if not asset_relpath:
            result.errors.append(f'{prefix} missing asset_relpath')

        linked_text_chunk_ids = row.get('linked_text_chunk_ids')
        if linked_text_chunk_ids is not None:
            if not isinstance(linked_text_chunk_ids, list) or any(
                not str(item).strip() for item in linked_text_chunk_ids
            ):
                result.errors.append(f'{prefix} linked_text_chunk_ids must be a non-empty string list')

        confidence = _as_float(row.get('vision_confidence'))
        fallback_used = bool(row.get('fallback_used'))
        if confidence is not None and confidence < _LOW_CONFIDENCE_THRESHOLD and not fallback_used:
            result.warnings.append(
                f'{prefix} low vision_confidence={confidence:.3f} without fallback_used=true'
            )

    embed_ids: set[str] = set()
    embed_dims: set[int] = set()
    for idx, row in enumerate(embed_rows, start=1):
        prefix = f'{doc_id}:{_EMBED_FILE}:{idx}'
        chunk_id = str(row.get('chunk_id') or '').strip()
        if not chunk_id:
            result.errors.append(f'{prefix} missing chunk_id')
        elif chunk_id in embed_ids:
            result.errors.append(f'{prefix} duplicate chunk_id `{chunk_id}`')
        else:
            embed_ids.add(chunk_id)

        row_doc_id = str(row.get('doc_id') or '').strip()
        if row_doc_id != doc_id:
            result.errors.append(f'{prefix} doc_id mismatch `{row_doc_id}` != `{doc_id}`')

        provider = str(row.get('provider') or '').strip()
        model = str(row.get('model') or '').strip()
        if not provider:
            result.errors.append(f'{prefix} missing provider')
        if not model:
            result.errors.append(f'{prefix} missing model')

        dim = _as_int(row.get('dim'))
        if dim is None or dim <= 0:
            result.errors.append(f'{prefix} dim must be integer > 0')
            dim = None

        embedding = row.get('embedding')
        if not isinstance(embedding, list) or not embedding:
            result.errors.append(f'{prefix} embedding must be non-empty list')
        elif any(not _is_number(item) for item in embedding):
            result.errors.append(f'{prefix} embedding values must be numeric')

        if dim is not None and isinstance(embedding, list) and len(embedding) != dim:
            result.errors.append(f'{prefix} embedding length {len(embedding)} != dim {dim}')
        if dim is not None:
            embed_dims.add(dim)

        if chunk_id and chunk_ids and chunk_id not in chunk_ids:
            result.errors.append(f'{prefix} chunk_id `{chunk_id}` not present in {_CHUNK_FILE}')

    if len(embed_dims) > 1:
        result.errors.append(
            f'{doc_id}:{_EMBED_FILE} has inconsistent dimensions: {sorted(embed_dims)}'
        )

    manifest_doc = str(manifest.get('doc_id') or '').strip()
    if manifest_doc and manifest_doc != doc_id:
        result.errors.append(f'{doc_id}:{_MANIFEST_FILE} doc_id mismatch `{manifest_doc}` != `{doc_id}`')

    contract_version = str(manifest.get('contract_version') or '').strip()
    if contract_version and contract_version != 'visual-v1':
        result.warnings.append(f'{doc_id}:{_MANIFEST_FILE} contract_version should be `visual-v1`')

    manifest_chunk_count = _as_int(manifest.get('visual_chunk_count'))
    if manifest_chunk_count is None:
        result.errors.append(f'{doc_id}:{_MANIFEST_FILE} visual_chunk_count must be integer >= 0')
    elif manifest_chunk_count != len(chunk_rows):
        result.errors.append(
            f'{doc_id}:{_MANIFEST_FILE} visual_chunk_count {manifest_chunk_count} != actual {len(chunk_rows)}'
        )

    manifest_embed_count = _as_int(manifest.get('embedding_count'))
    if manifest_embed_count is None:
        result.errors.append(f'{doc_id}:{_MANIFEST_FILE} embedding_count must be integer >= 0')
    elif manifest_embed_count != len(embed_rows):
        result.errors.append(
            f'{doc_id}:{_MANIFEST_FILE} embedding_count {manifest_embed_count} != actual {len(embed_rows)}'
        )

    manifest_embed_dim = _as_int(manifest.get('embedding_dim'))
    if len(embed_rows) > 0:
        if manifest_embed_dim is None or manifest_embed_dim <= 0:
            result.errors.append(f'{doc_id}:{_MANIFEST_FILE} embedding_dim must be integer > 0')
        elif embed_dims and manifest_embed_dim not in embed_dims:
            result.errors.append(
                f'{doc_id}:{_MANIFEST_FILE} embedding_dim {manifest_embed_dim} != actual {sorted(embed_dims)}'
            )

    provider = str(manifest.get('provider') or '').strip()
    model = str(manifest.get('model') or '').strip()
    if len(embed_rows) > 0 and not provider:
        result.errors.append(f'{doc_id}:{_MANIFEST_FILE} provider is required when embeddings exist')
    if len(embed_rows) > 0 and not model:
        result.errors.append(f'{doc_id}:{_MANIFEST_FILE} model is required when embeddings exist')

    return result


def validate_visual_artifacts(
    assets_dir: Path,
    doc_ids: list[str] | None = None,
    strict: bool = False,
) -> dict[str, ValidationResult]:
    if not assets_dir.exists():
        result = ValidationResult(
            errors=[f'assets_dir does not exist: {assets_dir}'] if strict else [],
            warnings=[f'assets_dir does not exist: {assets_dir}'] if not strict else [],
        )
        return {'<all>': result}

    selected: list[str]
    if doc_ids:
        selected = sorted({str(doc_id).strip() for doc_id in doc_ids if str(doc_id).strip()})
    else:
        selected = sorted(
            path.name
            for path in assets_dir.iterdir()
            if path.is_dir() and (path / 'chunks.jsonl').exists()
        )

    return {
        doc_id: validate_visual_artifacts_for_doc(assets_dir / doc_id, strict=strict)
        for doc_id in selected
    }
