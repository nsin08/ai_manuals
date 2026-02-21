# System Architecture

Version: 1.0
Date: 2026-02-21
Status: Draft

## 1. Architecture Principles
- Evidence-only answers with citations.
- Multi-modality: text, tables, figures, and diagrams.
- Local-first default with optional external providers.
- Deterministic evaluation and regression gates.
- Scalability to thousands of manuals.

## 2. Logical Components
- Ingestion pipeline service
- Retrieval service
- Answer orchestration service
- Evaluation and checking service
- API service
- UI service
- Storage and asset management

## 3. Runtime Flows

### 3.1 Ingestion Flow
1. Receive manual upload or catalog reference.
2. Parse PDF pages and extract layout regions.
3. OCR low-text pages and figure/table regions with bbox coordinates.
4. Extract tables with structure when available; fallback to heuristics.
5. Extract figures and captions; generate OCR summaries per region.
6. Create chunks by modality: text, table_row, figure_ocr, vision_summary.
7. Compute embeddings for all chunks.
8. Persist chunks, embeddings, and assets.
9. Compute ingestion QC metrics and store results.

### 3.2 Retrieval Flow
1. Detect intent (table, diagram, procedure, general).
2. Run modality-specific retrieval:
   - Text: keyword plus vector
   - Tables: header-aware lexical plus vector using table_row chunks
   - Diagrams: figure OCR and vision summaries with figure_id
3. Rerank candidates and enforce evidence diversity across modalities.
4. Validate evidence coverage with a numeric score and threshold.
5. Return top evidence with scores and citations.

### 3.3 Answering Flow
1. Receive top evidence and query intent.
2. Generate answer only from evidence.
3. Attach citations (doc_id, page, table_id, figure_id).
4. Emit confidence as a float, abstain flag, and follow-up prompts if needed.

### 3.4 Evaluation Flow
1. Run golden questions with retrieval traces.
2. Compute recall-at-k and pass rates.
3. Enforce regression gates in CI.

## 4. Storage
- PostgreSQL for documents, chunks, metadata, evaluations.
- pgvector for embeddings.
- Filesystem or object storage for visual artifacts.
- Optional graph store for connector and pin relationships.
 - Optional cache for repeated retrieval queries.

## 5. Observability
- Ingestion logs with QC metrics.
- Ingestion throughput metrics (pages per minute).
- Retrieval traces with intent, modality hit counts, and scores.
- Answer traces with citations and confidence.

## 6. Failure Handling
- If embedding fails, mark coverage and retry with shorter text.
- If evidence coverage is low, abstain or ask follow-up.
- If OCR fails, mark document as degraded in QC.
