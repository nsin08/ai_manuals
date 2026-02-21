from __future__ import annotations

from pathlib import Path

from packages.adapters.data_contracts.visual_artifact_generation import (
    build_visual_artifacts_from_chunks,
    write_visual_artifacts,
)


def test_build_visual_artifacts_from_chunks_extracts_visual_rows() -> None:
    rows = [
        {
            'chunk_id': 'text-1',
            'doc_id': 'doc_x',
            'content_type': 'text',
            'page_start': 1,
            'page_end': 1,
            'content_text': 'Page text',
            'metadata': {},
        },
        {
            'chunk_id': 'fig-1',
            'doc_id': 'doc_x',
            'content_type': 'figure_caption',
            'page_start': 1,
            'page_end': 1,
            'content_text': 'Figure 1: test',
            'figure_id': 'fig-1',
            'metadata': {},
        },
        {
            'chunk_id': 'tab-1',
            'doc_id': 'doc_x',
            'content_type': 'table',
            'page_start': 2,
            'page_end': 2,
            'content_text': 'A|B',
            'table_id': 'tab-1',
            'metadata': {},
        },
    ]

    visual_rows, embedding_rows, manifest = build_visual_artifacts_from_chunks('doc_x', rows)
    assert len(visual_rows) == 2
    assert embedding_rows == []
    assert manifest['visual_chunk_count'] == 2
    assert manifest['embedding_count'] == 0
    assert any(row['modality'] == 'figure' for row in visual_rows)
    assert any(row['modality'] == 'table' for row in visual_rows)


def test_write_visual_artifacts_creates_contract_files(tmp_path: Path) -> None:
    doc_dir = tmp_path / 'doc_y'
    visual_rows = [
        {
            'chunk_id': 'doc_y:visual:00001',
            'doc_id': 'doc_y',
            'page': 1,
            'region_id': 'r1',
            'bbox': [0, 0, 1, 1],
            'modality': 'image',
            'asset_relpath': 'generated/p1_r1.png',
        }
    ]
    embedding_rows: list[dict[str, object]] = []
    manifest = {
        'contract_version': 'visual-v1',
        'doc_id': 'doc_y',
        'visual_chunk_count': 1,
        'embedding_count': 0,
        'embedding_dim': 0,
        'provider': 'derived',
        'model': 'chunk-metadata',
    }

    write_visual_artifacts(doc_dir, visual_rows, embedding_rows, manifest)
    assert (doc_dir / 'visual_chunks.jsonl').exists()
    assert (doc_dir / 'visual_embeddings.jsonl').exists()
    assert (doc_dir / 'visual_manifest.json').exists()
