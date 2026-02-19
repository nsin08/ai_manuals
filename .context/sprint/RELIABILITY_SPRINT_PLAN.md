# Reliability Sprint Plan

Date: 2026-02-19
Branch: feature/reliability-sprint
Goal: Move from demo behavior to dependable manual assistant with measurable answer quality.

## Definition of Done

- Golden evaluation pass rate >= 70% overall.
- Zero missing-citation answers when status is `ok`.
- False `not_found` rate reduced on known-answer questions.
- Query trace includes retrieval/rerank/answer diagnostics for every request.
- UI exposes reliability controls and confidence cues without overwhelming users.

## Scope (Sprint)

1. Retrieval Reliability
- Add reranking stage after hybrid retrieval (top 30 -> rerank -> top 8).
- Add intent-specific retrieval profiles:
  - `procedure`: prefer sequential text chunks.
  - `troubleshooting`: prefer fault/cause/remedy tables + warning sections.
  - `comparison`: force coverage of both compared concepts.
- Add anchor-term hard constraints for operational queries.
- Add dynamic top-k widening when early hits are low-confidence.

Deliverables:
- `packages/application/use_cases/search_evidence.py` upgraded pipeline.
- `packages/adapters/retrieval/*` reranker adapter.
- Retrieval diagnostics in `.context/reports/retrieval_traces.jsonl`.

Acceptance checks:
- Unit tests for reranking and anchor constraints.
- Integration test proving better hit@k on curated cases.

2. Ingestion Reliability
- Section-aware chunking (heading + body cohesion).
- Procedure step extraction (`Step 1`, `1.`, warnings/cautions).
- Table row normalization for troubleshooting mappings.
- Optional vision pass for diagram/table-heavy pages to generate structured text metadata.

Deliverables:
- Improved chunk schema metadata: `section_title`, `step_index`, `table_row_type`, `confidence`.
- Ingestion QA report per doc: pages parsed, OCR pages, table rows extracted.

Acceptance checks:
- Ingestion report generated under `.context/reports/ingestion_qc_<doc_id>.json`.
- Regression tests for chunk type coverage.

3. Answer Reliability
- Intent-aware answer templates:
  - Procedure: prerequisites -> ordered steps -> verification.
  - Troubleshooting: symptom -> checks in order -> corrective action.
  - Comparison: side-by-side table.
- Add answer consistency checks:
  - reject if no direct evidence support for key claim.
  - downgrade to `partial` instead of generic `not_found` when nearby evidence exists.

Deliverables:
- `packages/application/use_cases/answer_question.py` with template dispatcher.
- Optional `status=partial` API response path.

Acceptance checks:
- Unit tests for each template behavior.
- No freeform unstructured response for procedure/comparison intents.

4. Evaluation and Gates
- Expand golden set with per-doc query classes:
  - reference, procedure, troubleshooting, comparison, wiring/diagram.
- Add metrics script:
  - citation precision
  - groundedness pass rate
  - not_found false-positive rate
  - per-doc pass rate
- CI gate for reliability threshold.

Deliverables:
- `scripts/run_reliability_eval.py`
- `.context/reports/reliability_eval_summary.json`
- workflow update in `.github/workflows/*`

Acceptance checks:
- CI fails below threshold.
- report attached per PR.

5. UX for Dependability
- Add response confidence indicator (`high/medium/low`) based on retrieval quality.
- Add "Why this answer" panel: top evidence rationale + selected manual scope.
- Preserve concise main response while giving operators details on demand.

Deliverables:
- UI updates in `apps/ui/main.py`.

Acceptance checks:
- Sources remain clickable and page-anchored.
- Confidence aligns with retrieval diagnostics.

## Local Vision Model Recommendation

Primary (best quality for technical page understanding on local Ollama):
- `qwen2.5vl:7b` (or latest qwen2.5-vl variant)

Fallback (lighter):
- `llava:7b`

Usage pattern:
- Run vision only on pages flagged low-text/high-figure.
- Store extracted structured text; embed that text for retrieval.

## Task Breakdown (Execution Order)

Phase A: Retrieval + Rerank
- Implement reranker adapter and anchor constraints.
- Add tests + benchmark before/after.

Phase B: Ingestion QC + Structured Extraction
- Add section/step/table-row metadata.
- Add ingestion QC report.

Phase C: Answer Templates + Partial Status
- Implement template dispatcher and strict grounded checks.

Phase D: Evaluation Gate + UI Confidence
- Add reliability eval script and CI thresholds.
- Add confidence + rationale panel in UI.

## Risks

- Overfitting to golden questions.
Mitigation: keep unseen validation set.

- Vision extraction latency.
Mitigation: selective page routing and caching.

- Too strict grounding causing excessive `partial`.
Mitigation: tune thresholds from traces and per-intent calibration.

## Evidence to Capture

- `pytest tests -q` results
- `scripts/run_reliability_eval.py` output JSON
- Example answer traces showing template + citation grounding
- Before/after metrics table in PR description
