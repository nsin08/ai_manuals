# Implementation Roadmap

Version: 1.2
Date: 2026-02-17
Status: Draft (Agile + Verifiable Deliverables)

## Sprint Model

- 1 phase = 1 sprint target (except Phase 5 can span 1-2 sprints)
- Each sprint ends with a demo and evidence pack
- Advancement rule: phase exit criteria must be satisfied

## Phase 0 - Foundation and Data Contracts (Sprint 1)

Goals:
- Create project skeleton and dependency management
- Define shared config and logging conventions
- Stand up `docker compose` baseline
- Validate document catalog and golden question schema

Deliverables:
- `apps/api`, `apps/ui`
- `packages/domain`, `packages/application`, `packages/ports`, `packages/adapters`
- `infra/docker-compose.yml`
- Base `.env.example`
- Data contracts validated (`document_catalog.yaml`, `golden_questions.yaml`)

Verification:
- `docker compose` health checks green
- Contract-validation tests passing
- PR evidence mapping completed

## Phase 1 - Ingestion Pipeline (Sprint 2)

Goals:
- Ingest digital and scanned PDFs
- Produce text/table/figure artifacts and metadata chunks

Deliverables:
- PDF parser adapter
- OCR adapter
- Table extraction adapter
- Asset storage adapter
- Background worker job for ingestion

Verification:
- Ingestion integration tests passing
- Ingestion report with chunk counts by content type
- Sample citations generated from ingested artifacts

## Phase 2 - Retrieval (Sprint 3)

Goals:
- Implement robust evidence retrieval

Deliverables:
- Keyword (FTS) retrieval
- Vector (pgvector) retrieval
- Hybrid merge/scoring module
- Query-intent heuristic (table and diagram aware)

Verification:
- Retrieval test suite passing
- Golden subset retrieval quality report (top-k hit checks)
- Trace logs for retrieval path available

## Phase 3 - Answering and Citations (Sprint 4)

Goals:
- Generate answers from evidence only

Deliverables:
- Answer composition service
- Citation formatter
- Ambiguity follow-up logic
- Trace logging for retrieval and citations

Verification:
- Contract tests for answer payload and citation schema
- Behavior tests for ambiguity follow-up
- Grounding guardrail tests passing

## Phase 4 - Evaluation and UI/E2E (Sprint 5)

Goals:
- Provide demo-ready user flow
- Produce repeatable benchmark metrics

Deliverables:
- Streamlit upload + chat screens
- Sources panel with citations
- Golden-question runner + score summary report

Verification:
- E2E tests passing (`upload -> query -> answer`)
- Golden benchmark run captured with pass/fail per question
- Demo checklist signed for sprint review

## Phase 5 - Hardening (Sprint 6)

Goals:
- Stabilize for MVP release

Deliverables:
- Unit/integration/e2e test coverage baseline
- Performance baseline metrics
- Security and local-first checks
- Golden benchmark regression gate in CI
- Runbook validation

Verification:
- CI green with regression thresholds
- Performance report stored
- Release checklist complete

## Backlog Buckets

- Core: must-have for MVP acceptance
- Nice-to-have: reranker, advanced diagram read
- Post-MVP: cloud vision enhancements, additional UI workflows

## Global Exit Criteria

- Each phase exits only after acceptance checks are green and linked to tests
- MVP exit also requires passing golden must-have checks
- Any missing document mapping blocks benchmark pass
