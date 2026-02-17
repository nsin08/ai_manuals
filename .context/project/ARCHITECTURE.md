# System Architecture

Version: 1.1
Date: 2026-02-17
Status: Draft Baseline (Revised for Dataset + Golden Questions)

## 1. Architecture Style

The system uses Hexagonal Architecture (Ports and Adapters):
- Domain contains business entities and policies.
- Application contains use-case orchestration.
- Ports define external capabilities required by use-cases.
- Adapters implement ports with concrete technologies.

Dependency rule:
- `domain` and `application` never import `adapters`.
- `adapters` implement `ports`.

## 2. Logical Components

- Ingestion service
- Retrieval service
- Answer orchestration service
- Evaluation service (golden questions)
- API service
- UI service
- Persistence and asset storage

## 3. Package Boundaries

`packages/domain`
- Entities: `Document`, `Chunk`, `Citation`, `Query`, `Answer`
- Evaluation entities: `GoldenQuestion`, `EvaluationRun`, `EvaluationResult`
- Policies: grounding, citation formatting, safety checks

`packages/application`
- Use-cases:
  - `ingest_document`
  - `search_evidence`
  - `answer_question`
  - `explain_sources`
  - `run_golden_evaluation`

`packages/ports`
- Repositories:
  - document/chunk repositories
  - evaluation run/result repositories
- Providers:
  - keyword/vector search
  - pdf parser
  - OCR
  - object store
  - LLM and optional vision provider
  - document catalog resolver (`doc_id` -> source file)

`packages/adapters`
- Implementations:
  - Postgres + pgvector + FTS
  - PyMuPDF/pdfplumber/Camelot
  - PaddleOCR/Tesseract
  - Ollama provider
  - optional cloud provider
  - filesystem/minio object store
  - YAML document catalog adapter

`apps/api`
- FastAPI entrypoint
- API endpoints and request/response models
- dependency wiring

`apps/ui`
- Streamlit app
- upload, query, sources panel, follow-up prompt

## 4. Runtime Flows

### 4.1 Ingestion + Query Flow

1. User uploads manual via UI/API.
2. API enqueues ingestion job.
3. Worker parses pages, extracts tables/figures, runs OCR.
4. Worker stores chunks and assets; computes embeddings.
5. User asks a question.
6. API retrieves evidence via keyword + vector hybrid.
7. Application composes grounded answer with citations.
8. UI shows answer and linked evidence.

### 4.2 Golden Evaluation Flow

1. Load `golden_questions.yaml` and document catalog.
2. Resolve each `doc` alias to one or more ingested docs.
3. Run Q/A pipeline for each golden question.
4. Score must-have checks (grounding + citation presence).
5. Store per-question results and summary metrics.

## 5. Data Architecture

Operational datastore:
- PostgreSQL for `documents`, `chunks`, `embeddings`, `runs`

Evaluation datastore:
- `evaluation_runs` (run metadata)
- `evaluation_results` (per question metrics + pass/fail)

Search datastore:
- pgvector for embeddings
- Postgres FTS for keyword search

Asset storage:
- Filesystem in MVP
- Optional MinIO abstraction for portability

## 6. Document Identity and Catalog

The benchmark file references canonical `doc` ids (for example `rockwell_powerflex_40`).
A catalog layer is required to map these IDs to concrete filenames and revisions.

Required behavior:
- Explicit mapping (`doc_id` -> filename/path/source hash)
- Missing-doc detection before evaluation
- Alias support for filename variations

## 7. Cross-cutting Concerns

Configuration:
- Environment variables only

Logging and tracing:
- Structured logs with request/run ids
- Optional trace persistence for debugging

Security:
- local-first default
- explicit cloud toggle and provider keys

Testing:
- unit tests for domain/application
- integration tests for adapters
- e2e tests for ingestion/retrieval/answering
- golden evaluation regression tests

## 8. Open Architecture Questions

- Should reranking be required in MVP or post-MVP?
- When to introduce MinIO boundary?
- What confidence threshold should trigger follow-up questions?
- Should golden evaluation run on every PR or nightly only?
