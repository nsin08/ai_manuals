# Equipment Manuals Chatbot - Comprehensive Project Plan

Version: 1.2
Date: 2026-02-17
Status: Planning Baseline (Agile + Verifiable Deliverables)

## 1. Mission

Deliver a local-first engineering assistant that answers manual-based questions with auditable citations across digital and scanned PDFs.

## 2. Objectives

- Build a usable MVP for 5-10 equipment manuals.
- Guarantee evidence-grounded responses with citations.
- Keep default operation fully local and offline post-ingestion.
- Add repeatable benchmark evaluation using golden questions.
- Preserve extensibility for optional cloud LLM/vision providers.

## 3. Scope

In scope:
- Ingestion pipeline (text, table, figure, OCR)
- Document catalog mapping (`doc_id` -> source file)
- Hybrid retrieval (keyword + vector)
- Chat API with grounding policy
- Streamlit MVP UI
- Golden question evaluator and scoring report
- Containerized local deployment
- Core runbooks and architecture docs

Out of scope for MVP:
- Multi-tenant auth model
- Enterprise SSO and RBAC
- Horizontal scaling beyond single host

## 4. Principles

- Local-first by default
- No evidence, no claim
- Hexagonal architecture boundaries are enforced
- Config-driven behavior (12-Factor)
- Reproducible deployments via Docker Compose
- Benchmark-driven quality checks before release
- End-of-phase deliverables must be demoable and test-verifiable

## 5. Requirements Traceability

- FR-1 (ingestion): ingestion pipeline and metadata persistence
- FR-2 (question answering): API and UI chat interface
- FR-3 (grounding/citations): answer composer and citation formatter
- FR-4 (diagram/table): OCR + table extraction + retrieval weighting
- FR-5 (follow-up): ambiguity detector and clarifier
- FR-6 (offline): local providers and local storage

- NFR-1 (containerized): compose stack and runbooks
- NFR-2 (architecture): package boundaries and dependency rules
- NFR-3 (auditability): trace logs and run records
- NFR-4 (security): explicit provider toggle and no silent exfiltration
- NFR-5 (performance): async ingestion and bounded retrieval

## 6. Agile Delivery Phases

Phase 0: Foundations and Data Contracts
- Build code skeleton, local stack, and data contract loaders
- Validate catalog and golden question schema

Phase 1: Ingestion
- Parse PDFs, OCR scanned pages/figures, extract tables
- Persist chunks, metadata, and assets

Phase 2: Retrieval
- Implement FTS + vector retrieval and hybrid merge
- Add query-intent weighting (table/diagram aware)

Phase 3: Answering
- Enforce evidence-only answer generation
- Add citation formatter and ambiguity follow-up

Phase 4: UI and Evaluation
- Deliver upload + chat + citations panel
- Execute golden-question benchmark run

Phase 5: Hardening
- Enforce regression gates and performance baselines
- Finalize runbooks and release checklist

## 7. Phase-End Verifiable Deliverables

### Phase 0 Deliverables
- Code directories and service entrypoints present
- `docker compose up` starts baseline services
- `document_catalog.yaml` and `golden_questions.yaml` pass schema validation

Verification artifacts:
- Compose service status output
- Schema validation test report
- PR evidence map linking AC -> tests

### Phase 1 Deliverables
- At least 3 sample PDFs ingested successfully (digital + scanned mix)
- Chunks written to DB with content types (`text`, `table`, `figure_ocr`, `figure_caption`)
- Assets persisted and referenced

Verification artifacts:
- Ingestion run summary with counts per content type
- Integration tests for parser/OCR/table adapters
- Sample citations from ingested docs

### Phase 2 Deliverables
- Hybrid retrieval endpoint returns ranked evidence
- Query-intent weighting active for table/diagram questions

Verification artifacts:
- Retrieval test suite (FTS, vector, merge)
- Benchmark of top-k relevance on selected golden IDs
- Logged retrieval traces (question -> chunk ids)

### Phase 3 Deliverables
- Answers contain citations (doc + page minimum)
- Insufficient evidence path returns explicit "not found" + closest citations
- Ambiguous prompts trigger one short follow-up

Verification artifacts:
- Contract tests for answer schema + citations
- Behavioral tests for ambiguity handling
- Grounding policy test cases

### Phase 4 Deliverables
- Streamlit flow supports upload, ask, and source inspection
- Golden benchmark run produces per-question report

Verification artifacts:
- E2E tests for upload->query->answer path
- Golden evaluation summary (`pass_rate`, failures, missing docs)
- Demo script with expected outputs

### Phase 5 Deliverables
- Regression gates enabled (tests + golden minimum threshold)
- Performance and reliability baseline recorded
- Release checklist completed

Verification artifacts:
- CI run links
- Baseline latency/throughput report
- Signed-off release checklist

## 8. Work Breakdown Structure

WBS-1 Platform and Infrastructure
WBS-2 Domain/Application contracts
WBS-3 Ingestion adapters
WBS-4 Retrieval adapters
WBS-5 Answer orchestration
WBS-6 UI integration
WBS-7 Evaluation and QA
WBS-8 Documentation and governance

## 9. Milestones

M0: Dataset catalog and golden questions validated
M1: Repo and container baseline complete
M2: Ingestion of sample manuals complete
M3: Hybrid retrieval working with citations
M4: Chat + source panel demo-ready
M5: MVP acceptance checklist passed + golden benchmark baseline captured

## 10. Risks and Mitigations

R1 OCR misses labels in noisy scans
- Mitigation: preprocessing, fallback OCR, confidence thresholds

R2 Diagram answers are low confidence
- Mitigation: OCR-first + optional vision fallback

R3 Retrieval returns mixed-manual noise
- Mitigation: stronger metadata filters and follow-up clarifier

R4 Latency spikes on larger manuals
- Mitigation: async ingestion, capped retrieval, caching

R5 Architecture drift under delivery pressure
- Mitigation: ADR discipline + boundary tests

R6 Dataset mismatch between canonical `doc` ids and filenames
- Mitigation: explicit document catalog + preflight validation

## 11. Quality Strategy

- Unit tests for domain and use cases
- Integration tests for adapters (db/ocr/pdf/retrieval)
- E2E tests for ingest-to-answer flow
- Golden benchmark checks:
  - must-have citation present
  - grounded answer behavior
- Phase-end demo checklist must pass before moving phase

## 12. Governance Alignment

- Follow issue state machine and PR evidence mapping
- Keep temporary artifacts in `.context/temp/` or `.context/issues/`
- Keep durable decisions in `.context/project/`

## 13. Immediate Next Steps

1. Confirm this revised plan as baseline.
2. Complete missing doc mapping in `document_catalog.yaml`.
3. Scaffold code directories (`apps`, `packages`, `infra`, `tests`).
4. Implement Phase 0 story with verification artifacts.
