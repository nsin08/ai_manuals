# Implementation Plan

Version: 1.0
Date: 2026-02-21
Status: Draft

## Phase 1: Table and Diagram Fidelity
Objectives:
- Structured table extraction with row-level chunks.
- Region-based figure OCR and caption handling.
- Table and figure identifiers in citations.

Deliverables:
- Table extractor adapter with header-aware output.
- New chunk types: table_row, figure_ocr, vision_summary.
- Updated retrieval intent routing for tables and diagrams.

Acceptance Criteria:
- Golden table questions pass rate >= 80 percent.
- Table recall-at-5 >= 0.80.

## Phase 2: Retrieval Reliability
Objectives:
- Modality-specific candidate pools.
- Always-on reranking for top-k.
- Evidence coverage checks and abstain rules.
- Procedure intent detection and routing.
- Modality diversity enforcement across evidence sets.

Deliverables:
- Retrieval orchestrator with intent routing.
- Reranker integration and coverage gating.
- Answer abstain when evidence is weak.
 - Retrieval traces with modality hit counts.

Acceptance Criteria:
- Golden overall pass rate >= 85 percent.
- Incorrect answers reduced by 50 percent on previous failure set.
 - Evidence coverage threshold enforced at 0.50.

## Phase 3: Industrial Scale
Objectives:
- Parallel ingestion pipeline.
- Incremental updates and versioning.
- Partitioned retrieval per doc and domain.
 - Ingestion throughput instrumentation.
 - Retrieval caching for repeated queries.

Deliverables:
- Background ingestion workers.
- Document catalog with revision tracking.
- Retrieval filters and caching.
 - Ingestion QC metrics stored and queryable.

Acceptance Criteria:
- Ingestion throughput >= 200 pages per minute.
- Median answer latency <= 5 seconds.
 - Catalog entries include revision and source hash for all manuals.

## Phase 4: Advanced Connectivity
Objectives:
- Connector and pin entity extraction.
- Optional graph store for multi-hop reasoning.

Deliverables:
- Connector/pin schema extraction.
- Optional graph index and query adapter.

Acceptance Criteria:
- Diagram-related pass rate >= 80 percent.
- Multi-hop pinout queries answered with correct citations.

## Dependencies
- OCR engine support for region-based extraction.
- Embedding provider with stable latency.
- Storage capacity for large manual catalogs.
