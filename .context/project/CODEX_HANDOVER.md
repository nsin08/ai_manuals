# Equipment Manuals Chatbot - MVP Codex Handover

Document Version: 1.1
Date: 2026-02-17
Status: Active Development
Framework: space_framework v1.0.0

## 0) Context and Goal

Build a local-first chatbot that answers engineering questions across 5-10 equipment manuals (PDFs), including scanned PDFs, supporting:
- troubleshooting queries (alarms and symptoms)
- SOP and procedures (commission, decommission, maintenance)
- specs from tables
- answers requiring diagrams (dimension callouts, wiring labels)
- grounded answers with citations (doc + page + figure/table where possible)

The app must be:
- fully containerized (`docker compose`)
- local-first (no API keys required for MVP)
- optionally able to use cloud API keys later for better quality
- engineered using Hexagonal Architecture, SOLID, and 12-Factor

## 1) Hard Requirements

### 1.1 Functional Requirements (MVP)

FR-1 Ingest PDFs
- Upload and ingest 5-10 PDFs (mix of digital and scanned).
- Extract and index text blocks, tables, figures/diagrams, OCR text.

FR-2 Ask questions
- Provide a chat interface for troubleshooting, SOP, spec, and wiring/dimension questions.

FR-3 Evidence-grounded answers
- Every answer must be grounded in retrieved evidence.
- Every answer must include citations:
  - doc title or doc id
  - page number
  - section path when available
  - figure/table id when available

FR-4 Diagram and table interpretation
- Tables must be answerable.
- Diagrams supported via OCR on figure crops and captions.
- Optional MVP+: targeted vision read when OCR is insufficient.

FR-5 Follow-up questions
- If ambiguous (model/variant/revision unclear), ask one short follow-up.

FR-6 Local-first mode
- Works offline after ingestion.

### 1.2 Non-functional Requirements

NFR-1 Containerized
- Entire system runs with `docker compose up`.

NFR-2 Architecture constraints
- Hexagonal architecture with clear boundaries.
- SOLID and 12-Factor practices.

NFR-3 Auditability
- Log question -> retrieved chunks -> citations used.
- Store traces for debugging (configurable).

NFR-4 Security
- No manual content leaves local environment in local-first mode.
- Cloud usage must be explicit and configurable.

NFR-5 Performance
- MVP scale: 5-10 PDFs, up to a few thousand pages.
- Ingestion can be async; query-time must feel interactive.

## 2) System Overview

### 2.1 High-level Components

1. Ingestion Service
- Parse PDF, extract text/tables/figures, OCR, and store artifacts + metadata.

2. Indexing/Retrieval Service
- Hybrid search: keyword + vector retrieval, optional reranking.

3. Chat API
- Orchestrates retrieval, answer generation, and citations.

4. UI
- Chat UI + document upload + source panel.

5. Storage
- Relational DB for metadata/chunks.
- Vector index (local).
- Object store/filesystem for page images and figure crops.

## 3) Tech Stack (MVP Local-first)

### 3.1 Runtime and Core Libraries
- Python 3.11
- FastAPI
- Celery + Redis
- Streamlit

### 3.2 PDF and Extraction
- PyMuPDF (fitz)
- pdfplumber fallback
- Camelot for digital table extraction
- Pillow/OpenCV for image processing

### 3.3 OCR
- PaddleOCR primary
- Tesseract fallback

### 3.4 Storage and Retrieval
- PostgreSQL 16
- pgvector
- Postgres FTS
- Filesystem asset storage for MVP (optional MinIO)

### 3.5 Models
- Embeddings: `BAAI/bge-large-en-v1.5` (or `bge-m3` if needed)
- Local LLM via Ollama (`llama3` or `qwen2.5` class)
- Optional cloud toggle for LLM + vision providers

## 4) Hexagonal Architecture

### 4.1 Layers

Domain (core)
- Entities: `Document`, `Chunk`, `Citation`, `Query`, `Answer`
- Policies: grounding rule, citation formatting, safety guardrails

Application (use-cases)
- `IngestDocumentUseCase`
- `SearchEvidenceUseCase`
- `AnswerQuestionUseCase`
- `ExplainSourcesUseCase`

Ports (interfaces)
- `DocumentRepositoryPort`
- `ChunkRepositoryPort`
- `VectorSearchPort`
- `KeywordSearchPort`
- `OcrPort`
- `PdfParserPort`
- `LlmPort`
- `VisionPort` (optional)
- `ObjectStorePort`

Adapters (infrastructure)
- Postgres metadata/chunk adapter
- pgvector adapter
- Postgres FTS adapter
- PyMuPDF/pdfplumber parser adapter
- PaddleOCR adapter
- Ollama adapter
- Optional cloud LLM/Vision adapter
- Filesystem/MinIO adapter

### 4.2 Dependency Rule
- Domain and application do not import infrastructure.
- Infrastructure implements ports.

## 5) Data Model (MVP)

### 5.1 Tables (Postgres)

`documents`
- `id (uuid)`
- `title`
- `source_filename`
- `revision` (nullable)
- `equipment_tags` (`text[]`)
- `created_at`

`chunks`
- `id (uuid)`
- `document_id (fk)`
- `content_type` enum: `text | table | figure_ocr | figure_caption`
- `section_path` (nullable)
- `page_start`, `page_end` (int)
- `figure_id` / `table_id` (nullable)
- `caption` (nullable)
- `content_text` (text)
- `asset_ref` (nullable)
- `metadata` (`jsonb`)

`embeddings`
- `chunk_id (fk)`
- `embedding vector(<dim>)`

`runs` / `traces` (optional)
- `id`, `question`, `retrieved_chunk_ids`, `citations`, `answer`, `created_at`

### 5.2 Assets Layout
- `/data/assets/{doc_id}/pages/{page}.png`
- `/data/assets/{doc_id}/figures/{figure_id}.png`
- `/data/assets/{doc_id}/tables/{table_id}.md`

## 6) Retrieval and Answering Logic

### 6.1 Hybrid Retrieval
1. Keyword retrieval (FTS) top K1
2. Vector retrieval (pgvector) top K2
3. Merge and normalize scores
4. Optional rerank (cross-encoder)
5. Return top N chunks with metadata

### 6.2 Table-first Rule
If the query contains spec-like terms (gap, clearance, torque, tolerance, dimension, mm, Nm), prioritize table and figure OCR chunks.

### 6.3 Diagram Handling
Base MVP:
- Retrieve figure chunks using caption + OCR text.
- Answer from OCR when possible.

MVP+ (optional):
- If OCR finds likely figure but not confident values, call `VisionPort` with constrained prompt.

### 6.4 Grounding Policy
- The answer generator uses only retrieved evidence.
- If evidence is insufficient:
  - respond not found in provided manuals
  - show closest citations
  - ask one follow-up (model/revision/section)

### 6.5 Answer Output Format
- direct answer
- numbered steps
- warnings
- citations (doc/page/figure/table)

## 7) Containerization

### 7.1 Services (`docker compose`)
- `api` (FastAPI)
- `worker` (Celery)
- `postgres` (pgvector)
- `redis` (queue)
- `ui` (Streamlit)
- optional `minio`

### 7.2 Environment Variables (12-Factor)
- `APP_ENV=local|prod`
- `DATABASE_URL=...`
- `ASSET_STORE=filesystem|minio`
- `LLM_PROVIDER=local|cloud`
- `LOCAL_LLM_BASE_URL=http://ollama:11434`
- `CLOUD_API_KEY=...` (if cloud enabled)
- `OCR_ENGINE=paddle|tesseract`
- `INGEST_CONCURRENCY=...`

### 7.3 Logging
- JSON logs to stdout
- Include request id and run id
- Persist traces in DB only when enabled

## 8) Hardware Fit

Available hardware:
- Ryzen 9 8940HX (16C/32T)
- RTX 5060 8GB
- 24GB RAM

Good fit for OCR/PDF processing, local embeddings, and local 7B/8B LLMs.

## 9) MVP Acceptance Criteria (Demo Checklist)

1. Ingest completes and shows doc list + page counts.
2. Query returns answer with citations (doc + page).
3. At least one table-based question answered correctly.
4. At least one scanned PDF question answered correctly (OCR-based).
5. At least one diagram-based question answered (OCR-based at minimum).
6. Ambiguous query triggers one concise follow-up.

## 10) Recommended Repo Skeleton

```text
/apps
  /api
  /ui
/packages
  /domain
  /application
  /adapters
  /ports
/infra
  docker-compose.yml
  /postgres
  /minio (optional)
/data
  /assets
/tests
  /unit
  /integration
/docs
  ARCHITECTURE.md
  ADR/
```

## 11) ADRs to Record Early

- ADR-001: pgvector in Postgres for MVP
- ADR-002: PaddleOCR as OCR engine
- ADR-003: Evidence-grounded answering and citation format
- ADR-004: Diagram strategy (OCR-first, vision fallback)
- ADR-005: Local-first default with explicit cloud toggle

Navigation: [Project README](README.md) | [Architecture](ARCHITECTURE.md)
