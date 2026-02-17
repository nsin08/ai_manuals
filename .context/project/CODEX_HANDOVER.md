# Equipment Manuals Chatbot — MVP Codex Handover

**Document Version:** 1.0  
**Date:** 2026-02-17  
**Status:** Active Development  
**Framework:** space_framework v1.0.0

---

## 0) Context and Goal

Build a **local-first** chatbot that answers engineering questions across **5–10 equipment manuals (PDFs)**, including **scanned PDFs**, supporting:

* troubleshooting queries (alarms/symptoms)
* SOP/procedures (commission/decommission/maintenance)
* specs from **tables**
* answers requiring **diagrams** (dimension callouts, wiring labels)
* **grounded answers with citations** (doc + page + figure/table where possible)

The app must be:

* **fully containerized** (docker-compose)
* **local-first** (no API keys required for MVP)
* optionally able to use **cloud API keys** later (OpenAI/others) for improved quality
* engineered using **Hexagonal Architecture**, **SOLID**, and **12-Factor**

---

## 1) Hard Requirements

### 1.1 Functional requirements (MVP)

**FR-1 Ingest PDFs**

* Upload/ingest 5–10 PDFs initially (mix of digital + scanned).
* Extract and index:
  * text blocks
  * tables (preserve structure)
  * figures/diagrams (crop/store)
  * OCR text for scanned pages and for figure callouts

**FR-2 Ask questions**

* Provide a chat interface where engineers can ask:
  * "Alarm X meaning and recovery steps"
  * "Commissioning steps for subsystem Y"
  * "Torque/clearance/gap for part Z"
  * "What does CN1 pin 3 connect to?" / "gap between A and B"

**FR-3 Evidence-grounded answers**

* Every answer must be **grounded in retrieved evidence**.
* Must include **citations**:
  * doc title / doc id
  * page number
  * section path when available
  * figure/table id when available

**FR-4 Diagram & table interpretation**

* Tables must be answerable (row/parameter retrieval).
* Diagrams must be supported at least via:
  * OCR on figure crops + captions for retrieval
  * *Optional MVP+*: targeted "diagram read" step when OCR alone isn't enough

**FR-5 Follow-up questions**

* If the user's question is ambiguous (wrong/unknown model, multiple manuals match), the bot should ask **one short follow-up** (e.g., model/variant/revision).

**FR-6 Local-first mode**

* Works offline after ingestion (no external APIs required).

---

### 1.2 Non-functional requirements

**NFR-1 Containerized**

* Entire system runs via `docker compose up` (including DB + services).

**NFR-2 Architecture constraints**

* Hexagonal architecture: domain core + ports + adapters
* SOLID: clear boundaries, testable components
* 12-Factor: config in env vars, stateless services, logs to stdout, etc.

**NFR-3 Auditability**

* Log: question → retrieved chunks → citations used.
* Store conversation traces for debugging (configurable).

**NFR-4 Security**

* No manual content leaves local environment in local-first mode.
* When cloud is enabled, must be explicit and configurable.

**NFR-5 Performance**

* MVP scale: 5–10 PDFs, up to a few thousand pages.
* Ingestion can be async/background job; query-time must feel interactive.

---

## 2) System Overview

### 2.1 High-level components

1. **Ingestion Service**
   * Parses PDF, extracts text/tables/figures, runs OCR, stores artifacts + metadata
2. **Indexing/Retrieval Service**
   * Hybrid search: keyword + vector retrieval, optional reranking
3. **Chat API**
   * Orchestrates retrieval + answer generation + citations
4. **UI**
   * Chat UI + document upload + "show sources" panel
5. **Storage**
   * Relational DB for metadata/chunks
   * Vector index (local)
   * Object store for page images and figure crops

---

## 3) Tech Stack (MVP Local-First)

### 3.1 Runtime and core libs

* Language: **Python 3.11**
* API: **FastAPI**
* Workers/Jobs: **Celery + Redis**
* UI: **Streamlit** (fastest MVP)

### 3.2 PDF + extraction

* PDF render & extraction: **PyMuPDF (fitz)**
* Text extraction fallback: **pdfplumber**
* Table extraction:
  * digital PDFs: **Camelot** (lattice/stream modes)
  * fallback: parse via pdfplumber tables when Camelot fails
* Image processing: **Pillow / OpenCV**

### 3.3 OCR (must for scanned + diagrams)

* **PaddleOCR** (recommended for best label accuracy)
* fallback: **Tesseract** if needed

### 3.4 Storage & retrieval (local-first, minimal ops)

**Primary DB + vector**

* **PostgreSQL 16**
* **pgvector** extension for embeddings
* **Postgres FTS** for keyword search

**Objects**

* MVP: local filesystem mounted into container (e.g., `/data/assets`)
* optional: **MinIO** (S3-compatible) if you want an object-store boundary now

### 3.5 Models (local-first baseline + optional cloud)

**Local-first baseline**

* Embeddings: `BAAI/bge-large-en-v1.5` (or `bge-m3` if multilingual needed)
* LLM (local): `llama3.x` / `qwen2.5` class models via **Ollama**

**Cloud (optional toggle)**

* LLM + vision: OpenAI / other provider
* Use only when `LLM_PROVIDER=cloud` and API key set.

---

## 4) Hexagonal Architecture

### 4.1 Layers

**Domain (core)**

* Entities: `Document`, `Chunk`, `Citation`, `Query`, `Answer`
* Policies:
  * grounding rule: "no evidence, no claim"
  * citation formatting
  * safety gate for dangerous SOP actions

**Application (use-cases)**

* `IngestDocumentUseCase`
* `SearchEvidenceUseCase`
* `AnswerQuestionUseCase`
* `ExplainSourcesUseCase`

**Ports (interfaces)**

* `DocumentRepositoryPort`
* `ChunkRepositoryPort`
* `VectorSearchPort`
* `KeywordSearchPort`
* `OcrPort`
* `PdfParserPort`
* `LlmPort`
* `VisionPort` (optional)
* `ObjectStorePort`

**Adapters (infrastructure)**

* Postgres adapter (metadata + chunks)
* pgvector adapter (vector similarity)
* Postgres FTS adapter (keyword)
* PyMuPDF/pdfplumber adapter (PDF parsing)
* PaddleOCR adapter (OCR)
* Ollama adapter (local LLM)
* OpenAI adapter (cloud LLM + vision, later)
* Filesystem/MinIO adapter (assets)

### 4.2 Dependency rule

Domain and application **do not import** infrastructure.
Infrastructure depends on ports; ports depend on domain.

---

## 5) Data Model (MVP)

### 5.1 Tables (Postgres)

**documents**

* `id (uuid)`
* `title`
* `source_filename`
* `revision` (nullable)
* `equipment_tags` (text[])
* `created_at`

**chunks**

* `id (uuid)`
* `document_id (fk)`
* `content_type` enum: `text | table | figure_ocr | figure_caption`
* `section_path` (text, nullable)
* `page_start`, `page_end` (int)
* `figure_id` / `table_id` (nullable)
* `caption` (nullable)
* `content_text` (text)
* `asset_ref` (nullable) → points to stored image/table artifact
* `metadata` jsonb (bbox, columns, units hints, etc.)

**embeddings**

* `chunk_id (fk)`
* `embedding vector(<dim>)`

**runs / traces** (optional but recommended)

* `id`, `question`, `retrieved_chunk_ids`, `citations`, `answer`, `created_at`

### 5.2 Assets layout (filesystem or object store)

* `/data/assets/{doc_id}/pages/{page}.png`
* `/data/assets/{doc_id}/figures/{figure_id}.png`
* `/data/assets/{doc_id}/tables/{table_id}.md`

---

## 6) Retrieval & Answering Logic

### 6.1 Hybrid retrieval (required)

1. Keyword retrieval (FTS) top K1
2. Vector retrieval (pgvector) top K2
3. Merge + score normalization
4. Optional rerank (cross-encoder) *(nice-to-have)*
5. Return top N evidence chunks with metadata

### 6.2 Table-first rule

If query includes spec-like terms (gap, clearance, torque, tolerance, dimension, mm, Nm):

* prioritize table chunks and figure OCR chunks in scoring.

### 6.3 Diagram handling (MVP)

**Base MVP**

* Retrieve figure chunks using caption + OCR text.
* Answer from OCR if possible.

**MVP+ (recommended if you want a "wow" demo)**

* If OCR retrieval finds the right figure but value isn't confidently extracted:
  * call `VisionPort` on the figure crop/page image with a constrained prompt:
    * "Extract the dimension between labels A and B; return value+unit and where it appears."
* This can be local (hard) or cloud (easy) behind a toggle.

### 6.4 Grounding policy (hard rule)

* The answer generator must ONLY use retrieved evidence.
* If evidence is insufficient:
  * say "not found in provided manuals"
  * show closest citations
  * ask one follow-up (model/revision/section)

### 6.5 Output format (engineer-friendly)

* direct answer
* steps (numbered)
* warnings
* citations list (doc/page/figure/table)

---

## 7) Containerization

### 7.1 Services (docker-compose)

* `api` (FastAPI)
* `worker` (Celery/RQ)
* `postgres` (with pgvector)
* `redis` (job queue)
* `ui` (Streamlit)
* *(optional)* `minio`

### 7.2 Environment variables (12-factor)

* `APP_ENV=local|prod`
* `DATABASE_URL=...`
* `ASSET_STORE=filesystem|minio`
* `LLM_PROVIDER=local|cloud`
* `LOCAL_LLM_BASE_URL=http://ollama:11434`
* `CLOUD_API_KEY=...` (only if cloud enabled)
* `OCR_ENGINE=paddle|tesseract`
* `INGEST_CONCURRENCY=...`

### 7.3 Logging

* JSON logs to stdout (API + worker)
* include request id and run id
* store traces in DB only if enabled

---

## 8) Hardware Fit

**Available Hardware:**

* Ryzen 9 8940HX (16C/32T), RTX 5060 8GB, 24GB RAM

This is suitable for:

* OCR + PDF rendering (CPU heavy)
* embeddings locally
* local 7B/8B LLM via Ollama (good enough for grounded answers)
* if you want best diagram reading, cloud vision can be toggled later.

---

## 9) MVP Acceptance Criteria (demo checklist)

For a demo with 5–10 PDFs:

1. Ingest completes and shows doc list + page counts.
2. Query returns answer with **citations** (doc + page).
3. At least **one table-based** question answered correctly (shows exact row/parameter).
4. At least **one scanned PDF** question answered correctly (OCR-based).
5. At least **one diagram-based** question answered (via figure OCR; vision step optional).
6. If query is ambiguous, bot asks a short follow-up.

---

## 10) Repo Skeleton (recommended)

```
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
  /assets (bind mount)
/docs
  CODEX_HANDOVER.md
  ARCHITECTURE.md
  ADR/
```

---

## 11) ADRs to record early (short list)

* ADR-001: pgvector in Postgres for MVP (vs separate vector DB)
* ADR-002: PaddleOCR as OCR engine
* ADR-003: Evidence-grounded answering and citation format
* ADR-004: Diagram strategy (OCR-first, optional vision fallback)
* ADR-005: Local-first default, cloud toggle via env vars

---

**Navigation:** [← Project README](README.md) | [Architecture →](ARCHITECTURE.md)
