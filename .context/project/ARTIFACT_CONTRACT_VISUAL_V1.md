# Visual Artifact Contract v1

Version: `visual-v1`  
Purpose: define deterministic ingestion outputs for multimodal visual chunks and embeddings.

## Output Files (Per `doc_id`)

Required under `data/assets/<doc_id>/`:

- `visual_chunks.jsonl`
- `visual_embeddings.jsonl`
- `visual_manifest.json`

## `visual_chunks.jsonl` Contract

One JSON object per line.

Required fields:
- `chunk_id` (string, unique within document)
- `doc_id` (string, must match folder `doc_id`)
- `page` (int, >= 1)
- `region_id` (string, non-empty)
- `bbox` (array of 4 numeric values `[x1, y1, x2, y2]`)
- `modality` (string, one of: `figure`, `table`, `image`)
- `asset_relpath` (string, non-empty)

Optional but recommended:
- `figure_id` (string or null)
- `table_id` (string or null)
- `caption_text` (string)
- `ocr_text` (string)
- `linked_text_chunk_ids` (array of strings)
- `vision_confidence` (float, 0.0-1.0)
- `fallback_used` (boolean)

Noise fallback rule:
- If `vision_confidence` exists and is `< 0.45`, then `fallback_used` should be `true`.

## `visual_embeddings.jsonl` Contract

One JSON object per line.

Required fields:
- `chunk_id` (string, unique within document, must exist in `visual_chunks.jsonl`)
- `doc_id` (string, must match folder `doc_id`)
- `provider` (string, non-empty)
- `model` (string, non-empty)
- `dim` (int, > 0)
- `embedding` (array of numeric values, length must equal `dim`)

Optional:
- `created_at` (ISO timestamp)

## `visual_manifest.json` Contract

Required fields:
- `contract_version` (string, must be `visual-v1`)
- `doc_id` (string, must match folder `doc_id`)
- `visual_chunk_count` (int, >= 0)
- `embedding_count` (int, >= 0)
- `embedding_dim` (int, > 0 when `embedding_count > 0`)
- `provider` (string, non-empty)
- `model` (string, non-empty)

Consistency rules:
- `visual_chunk_count` equals actual number of rows in `visual_chunks.jsonl`.
- `embedding_count` equals actual number of rows in `visual_embeddings.jsonl`.
- All embedding rows have the same `dim`.
- Embedding row `dim` equals manifest `embedding_dim` when embeddings exist.

## Validation Modes

- Non-strict mode:
  - Missing files and weak fallback behavior are warnings.
- Strict mode:
  - Missing files and contract breaks are errors.

## Canonical Validation Commands

```bash
python scripts/validate_visual_artifacts.py --assets-dir data/assets
python scripts/validate_visual_artifacts.py --assets-dir data/assets --strict
python scripts/validate_visual_artifacts.py --assets-dir data/assets --doc-id timken_bearing_setting --strict
```
