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
| Phase 1 - Ingestion Pipeline | in progress |  | Parser/table/worker and chunk persistence implemented; OCR adapters added, phase exit criteria still open |
| Phase 2 - Retrieval | in progress |  | Hybrid retrieval + trace logging implemented with local adapters; pgvector/FTS backend integration pending |
| Phase 3 - Answering and Citations | done | 2026-02-18 | Grounded answer use-case, citation formatter, answer trace logging, and behavior/contract tests passing |
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
| OCR adapter implemented (primary + fallback behavior) | Codex | done | 2026-02-17 | `packages/adapters/ocr/paddle_ocr_adapter.py`, `packages/adapters/ocr/tesseract_ocr_adapter.py`, `packages/adapters/ocr/factory.py` |
| Table extraction adapter implemented with fallback | Codex | done | 2026-02-17 | `packages/adapters/tables/simple_table_extractor_adapter.py` (enhanced heuristics) |
| Ingestion worker job implemented and runnable | Codex | done | 2026-02-17 | `apps/worker/main.py`, `docker ps` shows `infra-worker-1` up |
| Chunk persistence includes `text`, `table`, `figure_ocr`, `figure_caption` | Codex | done | 2026-02-17 | `packages/application/use_cases/ingest_document.py`; API ingest result includes typed chunk counts |
| Asset storage references persisted correctly | Codex | done | 2026-02-17 | `packages/adapters/storage/filesystem_chunk_store_adapter.py`, output `data/assets/rockwell_powerflex_40/chunks.jsonl` |
| Integration tests for ingestion adapters pass | Codex | done | 2026-02-17 | `pytest tests -q` -> `12 passed`; `tests/integration/test_ingest_pipeline.py`, `tests/unit/test_ocr_and_tables.py` |
| Ingestion run summary attached as evidence | Codex | done | 2026-02-17 | `scripts/run_ingestion.py --doc-id rockwell_powerflex_40` -> `total_chunks: 510` (`text:156`, `table:328`, `figure_caption:26`) |
| Sample citations attached as evidence | Codex | done | 2026-02-18 | `.context/reports/phase3_answer_ok.json` includes doc/page and figure/table citation labels |
| Phase 1 commits recorded | Codex | done | 2026-02-17 | `f6e53c0` (ingestion scaffold), `fb78e16` (OCR + table improvements) |

Phase 1 exit criteria:
- At least 3 PDFs ingested successfully (digital + scanned mix).
- Ingestion run summary and sample citations attached as evidence.

## Phase 2 - Retrieval

| Item | Owner | Status | Date | Evidence |
|------|-------|--------|------|----------|
| FTS retrieval implemented | Codex | in progress | 2026-02-17 | `packages/adapters/retrieval/simple_keyword_search_adapter.py` (BM25-like local lexical scoring) |
| Vector retrieval implemented (pgvector) | Codex | in progress | 2026-02-17 | `packages/adapters/retrieval/hash_vector_search_adapter.py` (local vector fallback; pgvector adapter pending) |
| Hybrid merge and scoring implemented | Codex | done | 2026-02-17 | `packages/application/use_cases/search_evidence.py` (keyword + vector normalization and merge) |
| Query-intent weighting for table/diagram intents implemented | Codex | done | 2026-02-17 | `packages/application/use_cases/search_evidence.py` intent detection + content-type weighting |
| Retrieval trace logging enabled | Codex | done | 2026-02-17 | `.context/reports/retrieval_traces.jsonl`, `packages/adapters/retrieval/retrieval_trace_logger.py` |
| Retrieval tests pass (FTS/vector/hybrid) | Codex | done | 2026-02-17 | `pytest tests -q` -> `17 passed`; `tests/unit/test_retrieval.py`, `tests/integration/test_retrieval_pipeline.py` |
| Retrieval API endpoint available | Codex | done | 2026-02-17 | `GET /search` in `apps/api/main.py`; verified with `q=fault code corrective action` |

Phase 2 exit criteria:
- Golden subset retrieval check (top-k relevance) captured with evidence.

## Phase 3 - Answering and Citations

| Item | Owner | Status | Date | Evidence |
|------|-------|--------|------|----------|
| Evidence-only answer composition implemented | Codex | done | 2026-02-18 | `packages/application/use_cases/answer_question.py` (`answer_question_use_case`) |
| Citation schema enforced (`doc`, `page`, optional figure/table) | Codex | done | 2026-02-18 | `packages/domain/citation_formatter.py`, `tests/unit/test_citation_formatter.py` |
| Insufficient evidence path implemented (`not found` + closest citations) | Codex | done | 2026-02-18 | `.context/reports/phase3_answer_not_found.json` |
| Ambiguity follow-up behavior implemented (single concise question) | Codex | done | 2026-02-18 | `.context/reports/phase3_answer_follow_up.json`, `tests/unit/test_answer_question.py` |
| Contract tests for answer payload pass | Codex | done | 2026-02-18 | `tests/unit/test_answer_question.py`, `pytest tests -q` -> `23 passed` |
| Grounding policy behavior tests pass | Codex | done | 2026-02-18 | `tests/unit/test_grounding_policy.py`, `.context/reports/phase3_pytest.txt` |

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
