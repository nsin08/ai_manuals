# Dataset and Benchmark Inputs

This folder contains source manuals and benchmark questions used to validate MVP quality.

## Files

- `golden_questions.yaml`: canonical benchmark question set.
- `document_catalog.yaml`: mapping from canonical `doc_id` values to local files.
- PDF manuals used for ingestion and evaluation.

## Why This Matters

Golden questions reference canonical document IDs (for example `rockwell_powerflex_40`).
The application must resolve those IDs to local filenames before ingestion and evaluation.

## Preflight Rules

1. Validate every `doc_id` in `golden_questions.yaml` has a catalog entry.
2. Validate each catalog entry points to an existing file.
3. Mark missing files explicitly and fail evaluation preflight when missing.

## Expected Outputs from Evaluation

- Per-question pass/fail status
- Citation presence check (doc + page)
- Grounding check against retrieved evidence
- Aggregate score summary
