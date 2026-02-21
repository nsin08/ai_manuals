from __future__ import annotations

import json
from pathlib import Path

from packages.adapters.data_contracts.visual_artifacts import (
    validate_visual_artifacts,
    validate_visual_artifacts_for_doc,
)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')


def test_visual_artifact_contract_passes_for_valid_doc(tmp_path: Path) -> None:
    doc_dir = tmp_path / 'doc_a'
    doc_dir.mkdir(parents=True)

    _write_jsonl(
        doc_dir / 'visual_chunks.jsonl',
        [
            {
                'chunk_id': 'doc_a:visual:1',
                'doc_id': 'doc_a',
                'page': 2,
                'region_id': 'r1',
                'bbox': [0, 0, 100, 100],
                'modality': 'figure',
                'asset_relpath': 'images/p2_r1.png',
                'linked_text_chunk_ids': ['doc_a:text:1'],
                'vision_confidence': 0.91,
                'fallback_used': False,
            },
            {
                'chunk_id': 'doc_a:visual:2',
                'doc_id': 'doc_a',
                'page': 3,
                'region_id': 'r2',
                'bbox': [10, 10, 120, 140],
                'modality': 'table',
                'asset_relpath': 'images/p3_r2.png',
            },
        ],
    )
    _write_jsonl(
        doc_dir / 'visual_embeddings.jsonl',
        [
            {
                'chunk_id': 'doc_a:visual:1',
                'doc_id': 'doc_a',
                'provider': 'ollama',
                'model': 'vision-embed',
                'dim': 3,
                'embedding': [0.1, 0.2, 0.3],
            },
            {
                'chunk_id': 'doc_a:visual:2',
                'doc_id': 'doc_a',
                'provider': 'ollama',
                'model': 'vision-embed',
                'dim': 3,
                'embedding': [0.4, 0.5, 0.6],
            },
        ],
    )
    (doc_dir / 'visual_manifest.json').write_text(
        json.dumps(
            {
                'contract_version': 'visual-v1',
                'doc_id': 'doc_a',
                'visual_chunk_count': 2,
                'embedding_count': 2,
                'embedding_dim': 3,
                'provider': 'ollama',
                'model': 'vision-embed',
            }
        ),
        encoding='utf-8',
    )

    result = validate_visual_artifacts_for_doc(doc_dir, strict=True)
    assert result.errors == []
    assert result.warnings == []


def test_visual_artifact_contract_missing_files_warns_when_non_strict(tmp_path: Path) -> None:
    doc_dir = tmp_path / 'doc_b'
    doc_dir.mkdir(parents=True)

    result = validate_visual_artifacts_for_doc(doc_dir, strict=False)
    assert result.errors == []
    assert len(result.warnings) == 3

    strict_result = validate_visual_artifacts_for_doc(doc_dir, strict=True)
    assert len(strict_result.errors) == 3


def test_visual_artifact_contract_detects_mapping_dim_and_fallback_issues(tmp_path: Path) -> None:
    doc_dir = tmp_path / 'doc_c'
    doc_dir.mkdir(parents=True)

    _write_jsonl(
        doc_dir / 'visual_chunks.jsonl',
        [
            {
                'chunk_id': 'doc_c:visual:1',
                'doc_id': 'doc_c',
                'page': 1,
                'region_id': 'r1',
                'bbox': [0, 0, 10, 10],
                'modality': 'image',
                'asset_relpath': 'images/p1_r1.png',
                'vision_confidence': 0.1,
                'fallback_used': False,
            }
        ],
    )
    _write_jsonl(
        doc_dir / 'visual_embeddings.jsonl',
        [
            {
                'chunk_id': 'doc_c:visual:not_found',
                'doc_id': 'doc_c',
                'provider': 'ollama',
                'model': 'vision-embed',
                'dim': 3,
                'embedding': [0.1, 0.2],
            }
        ],
    )
    (doc_dir / 'visual_manifest.json').write_text(
        json.dumps(
            {
                'contract_version': 'visual-v0',
                'doc_id': 'doc_c',
                'visual_chunk_count': 2,
                'embedding_count': 1,
                'embedding_dim': 7,
                'provider': 'ollama',
                'model': 'vision-embed',
            }
        ),
        encoding='utf-8',
    )

    result = validate_visual_artifacts_for_doc(doc_dir, strict=True)
    assert any('not present in visual_chunks.jsonl' in error for error in result.errors)
    assert any('embedding length' in error for error in result.errors)
    assert any('visual_chunk_count' in error for error in result.errors)
    assert any('embedding_dim' in error for error in result.errors)
    assert any('low vision_confidence' in warning for warning in result.warnings)
    assert any('contract_version should be `visual-v1`' in warning for warning in result.warnings)


def test_validate_visual_artifacts_handles_missing_assets_dir() -> None:
    results = validate_visual_artifacts(Path('missing-assets-dir-for-test'), strict=False)
    result = results['<all>']
    assert result.errors == []
    assert result.warnings
