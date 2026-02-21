# Product Specification

Version: 1.0
Date: 2026-02-21
Status: Draft

## 1. Problem Statement
Engineers must frequently consult large PDF manuals for operations, maintenance,
commissioning, troubleshooting, and safety requirements. This is slow, error-prone,
and difficult to scale across large equipment fleets. The product must provide a
reliable, self-sufficient assistant that returns accurate, citation-backed answers
from manuals without requiring users to open the PDFs.

## 2. Goals
- Provide accurate, evidence-only answers with citations.
- Strong handling of tables, parameters, fault codes, and diagrams.
- Scale to thousands of manuals with acceptable latency.
- Deterministic evaluation with golden tests and regression gates.
- Local-first operation by default with optional external models.
 - Explicit, numeric confidence on answers with abstain behavior when evidence is weak.

## 3. Non-Goals
- Web search or external knowledge beyond ingested manuals.
- Engineering design or safety certification.
- Guaranteed answers for missing or ambiguous information.

## 4. Target Users
- Field engineers and technicians
- Maintenance and commissioning teams
- Reliability and operations engineers

## 5. User Journeys
1. Upload or register manuals in the catalog.
2. Ask a question about a specific manual or equipment family.
3. Receive a concise answer with citations to the manual pages.
4. If evidence is weak, receive a clear abstain or follow-up question.

## 6. Query Types
- Procedures and ordered steps
- Parameter tables, fault codes, and specifications
- Wiring diagrams and connector pinouts
- Troubleshooting and corrective actions
 - Procedure intent is a first-class query type in intent detection.

## 7. UX and Answer Format
- Answers must include citations with `doc_id` and page numbers.
- When possible, include table or figure identifiers.
- Provide confidence and abstain behavior explicitly.
- Offer follow-up questions when intent is unclear.
 - Confidence is a float in the range 0 to 1.
 - Abstain must be returned when evidence coverage is below the threshold.

## 8. Success Metrics
- Golden test pass rate >= 85 percent.
- Retrieval recall-at-5 on golden questions >= 80 percent.
- Median answer latency <= 5 seconds for single manual queries.
- Ingestion throughput >= 200 pages per minute on baseline hardware.
 - Table intent pass rate >= 80 percent.
 - Diagram intent pass rate >= 80 percent.

## 9. Constraints
- Local-first by default. External providers are optional.
- Evidence-only answers are mandatory.
- Manual revisions must be tracked as separate versions.
 - Catalog entries must include revision and source hash for traceability.
 - Evidence coverage threshold defaults to 0.50 for abstain enforcement.

## 10. Open Questions
- Do we introduce a graph store for connector and pin relationships now or later?
- What confidence threshold should trigger abstain vs follow-up?
