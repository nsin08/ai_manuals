# System Architecture

Version: 1.2
Date: 2026-02-21
Status: Rearchitecture Draft (Ingestion, Checking, Retrieval)

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

- Ingestion pipeline service (layout + OCR + table/figure extraction)
- Quality and checking service (ingestion QC, contracts, golden eval)
- Retrieval service (multi-stage, multi-modality)
- Answer orchestration service (grounded, citation-first)
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
  - `run_ingestion_checks` (new)
  - `run_retrieval_checks` (new)

`packages/ports`
- Repositories:
  - document/chunk repositories
  - evaluation run/result repositories
  - quality metrics repository (new)
- Providers:
  - keyword/vector search
  - table extraction and normalization (new)
  - layout/region extraction (new)
  - pdf parser
  - OCR
  - object store
  - LLM and optional vision provider
  - document catalog resolver (`doc_id` -> source file)
  - optional graph store (new)

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

### 4.1 Ingestion Flow (v2)

1. User uploads manual via UI/API.
2. API enqueues ingestion job with document metadata.
3. Worker extracts per-page text and layout regions.
4. OCR runs on low-text pages and figure/table regions.
5. Tables are extracted with structure when possible, else fallback heuristics.
6. Figures are cropped, captioned, and OCR summarized as needed.
7. Chunks are produced by modality: text, table rows, figure OCR, vision summary.
8. Embeddings computed per chunk and persisted.
9. Ingestion QC computes coverage metrics and flags low-quality pages.

### 4.2 Retrieval + Answering Flow (v2)

1. User asks a question.
2. Query intent detection (table, diagram, procedure, general).
3. Candidate retrieval per modality (keyword + vector on text chunks).
4. Table row retrieval and header-aware search.
5. Figure and vision chunks retrieval for diagram queries.
6. Reranker blends candidates and enforces evidence diversity.
7. Answer composer generates grounded response with citations.
8. Confidence and evidence coverage are returned with the answer.

### 4.3 Checking Flow (v2)

1. Ingestion QC runs on each document (coverage, OCR ratio, table yield).
2. Contract checks validate chunk, visual artifact, and metadata schemas.
3. Golden questions are executed with retrieval traces stored.
4. Retrieval checks compute recall-at-k and modality hit rates.
5. Failures are recorded and can gate releases.

## 5. Data Architecture

Operational datastore:
- PostgreSQL for `documents`, `chunks`, `embeddings`, `runs`, `quality_metrics`

Evaluation datastore:
- `evaluation_runs` (run metadata)
- `evaluation_results` (per question metrics + pass/fail)
- `retrieval_traces` (query -> chunk ids, modality hits)

Search datastore:
- pgvector for embeddings
- Postgres FTS for keyword search
- optional graph store for connector/pin or cross-artifact relations

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
 - Do we need a graph store for connector/pin mappings, or can we derive edges on the fly?
 - What ingestion QC thresholds should block a document from being searchable?
