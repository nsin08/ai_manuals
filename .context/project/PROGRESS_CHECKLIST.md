# Progress Checklist and Evidence Log

Version: 1.0  
Date: 2026-02-17  
Status: Active Tracking

## How to Use

- Update `Status` as work progresses: `not started`, `in progress`, `done`, `blocked`.
- Add concrete proof in `Evidence` (file path, command output location, CI run URL, commit SHA).
- A phase is complete only when all required rows are `done` and evidence is present.

## Status Summary

| Phase | Status | Completion Date | Evidence Summary |
|------|--------|-----------------|------------------|
| Phase 0 - Foundation and Data Contracts | done | 2026-02-17 | Skeleton, config, compose runtime, and contract-validation verified in Docker |
| Phase 1 - Ingestion Pipeline | in progress |  | Parser/table/worker and chunk persistence scaffold implemented; OCR is placeholder |
| Phase 2 - Retrieval | not started |  |  |
| Phase 3 - Answering and Citations | not started |  |  |
| Phase 4 - UI and Evaluation | not started |  |  |
| Phase 5 - Hardening | not started |  |  |

## Phase 0 - Foundation and Data Contracts

| Item | Owner | Status | Date | Evidence |
|------|-------|--------|------|----------|
| Project skeleton created: `apps/`, `packages/`, `infra/`, `tests/` | Codex | done | 2026-02-17 | `apps/`, `packages/`, `infra/`, `tests/` |
| Baseline compose stack starts cleanly (`postgres`, `redis`, `api`, `worker`, `ui`) | Codex | done | 2026-02-17 | `docker compose -f infra/docker-compose.yml up -d --build`, `docker ps` shows all services running |
| `.env.example` created with required variables | Codex | done | 2026-02-17 | `.env.example` |
| Catalog and golden schema validation tests added | Codex | done | 2026-02-17 | `tests/unit/test_data_contracts.py`, `pytest tests/unit -q` |
| `document_catalog.yaml` validated against actual files | Codex | done | 2026-02-17 | `scripts/validate_data_contracts.py` (`Errors: 0`, `Warnings: 1`) |
| PR evidence mapping prepared for Phase 0 story | Codex | done | 2026-02-17 | Phase-0 commit + tag on `develop` with checklist evidence |

Phase 0 exit criteria:
- All rows above are `done`.
- Evidence includes compose status output and validation test results.

## Phase 1 - Ingestion Pipeline

| Item | Owner | Status | Date | Evidence |
|------|-------|--------|------|----------|
| PDF parser adapter implemented | Codex | done | 2026-02-17 | `packages/adapters/pdf/pypdf_parser_adapter.py` |
| OCR adapter implemented (primary + fallback behavior) | Codex | in progress | 2026-02-17 | `packages/adapters/ocr/noop_ocr_adapter.py` (placeholder until Paddle/Tesseract adapters) |
| Table extraction adapter implemented with fallback | Codex | done | 2026-02-17 | `packages/adapters/tables/simple_table_extractor_adapter.py` |
| Ingestion worker job implemented and runnable | Codex | done | 2026-02-17 | `apps/worker/main.py`, `docker ps` shows `infra-worker-1` up |
| Chunk persistence includes `text`, `table`, `figure_ocr`, `figure_caption` | Codex | in progress | 2026-02-17 | `packages/application/use_cases/ingest_document.py` |
| Asset storage references persisted correctly | Codex | done | 2026-02-17 | `packages/adapters/storage/filesystem_chunk_store_adapter.py`, output `data/assets/rockwell_powerflex_40/chunks.jsonl` |
| Integration tests for ingestion adapters pass | Codex | done | 2026-02-17 | `pytest tests -q` -> `8 passed`; `tests/integration/test_ingest_pipeline.py` |

Phase 1 exit criteria:
- At least 3 PDFs ingested successfully (digital + scanned mix).
- Ingestion run summary and sample citations attached as evidence.

## Phase 2 - Retrieval

| Item | Owner | Status | Date | Evidence |
|------|-------|--------|------|----------|
| FTS retrieval implemented |  | not started |  |  |
| Vector retrieval implemented (pgvector) |  | not started |  |  |
| Hybrid merge and scoring implemented |  | not started |  |  |
| Query-intent weighting for table/diagram intents implemented |  | not started |  |  |
| Retrieval trace logging enabled |  | not started |  |  |
| Retrieval tests pass (FTS/vector/hybrid) |  | not started |  |  |

Phase 2 exit criteria:
- Golden subset retrieval check (top-k relevance) captured with evidence.

## Phase 3 - Answering and Citations

| Item | Owner | Status | Date | Evidence |
|------|-------|--------|------|----------|
| Evidence-only answer composition implemented |  | not started |  |  |
| Citation schema enforced (`doc`, `page`, optional figure/table) |  | not started |  |  |
| Insufficient evidence path implemented (`not found` + closest citations) |  | not started |  |  |
| Ambiguity follow-up behavior implemented (single concise question) |  | not started |  |  |
| Contract tests for answer payload pass |  | not started |  |  |
| Grounding policy behavior tests pass |  | not started |  |  |

Phase 3 exit criteria:
- Sample Q/A outputs demonstrate citation and ambiguity behavior.

## Phase 4 - UI and Evaluation

| Item | Owner | Status | Date | Evidence |
|------|-------|--------|------|----------|
| Streamlit upload flow implemented |  | not started |  |  |
| Chat flow implemented with source panel |  | not started |  |  |
| Golden-question runner implemented |  | not started |  |  |
| Per-question evaluation output generated |  | not started |  |  |
| Aggregate benchmark summary generated (pass/fail + reasons) |  | not started |  |  |
| E2E tests for upload -> query -> answer pass |  | not started |  |  |

Phase 4 exit criteria:
- Demo checklist and benchmark report attached.

## Phase 5 - Hardening

| Item | Owner | Status | Date | Evidence |
|------|-------|--------|------|----------|
| Regression gates configured in CI |  | not started |  |  |
| Performance baseline report captured |  | not started |  |  |
| Security/local-first checks completed |  | not started |  |  |
| Runbooks validated against real execution |  | not started |  |  |
| Release checklist completed and signed |  | not started |  |  |

Phase 5 exit criteria:
- CI green on release candidate commit.
- Golden must-have checks pass at configured threshold.

## Evidence Conventions

- Test evidence: `tests/...` path + command used.
- CI evidence: workflow URL + commit SHA.
- Runtime evidence: log/report path (for example `.context/reports/...`).
- Documentation evidence: updated path reference (ADR/runbook/spec).
