# Sprint 2026-W08

**Dates:** 2026-02-16 to 2026-02-22  
**Document Type:** Product Owner + Architect Implementation Plan  
**Program Horizon:** 4 sprints (W08-W11)

## Goals
- Deliver an execution-ready plan to evolve the manuals assistant into a full agentic multimodal RAG system.
- Lock P0 architecture and acceptance gates for multimodal retrieval, grounded synthesis, and reliability.
- Raise golden benchmark performance from current baseline to production-ready targets.

## Product Outcomes (Engineering)
| Outcome | Current State | Target by W11 |
|---|---|---|
| Overall golden pass rate | 50% | >= 70% |
| Multi-turn completion | 100% completion, low quality | >= 98% completion and >= 65% pass |
| Multimodal quality | Text-centric retrieval with caption support | True multimodal retrieval with >= 60% multimodal pass |
| Grounding quality | High citation presence | >= 98% grounded finalization rate |
| Agent diagnostics | JSONL traces only | Trace quality dashboards and failure taxonomy workflow |

## Scope
### P0 In Scope (W08-W11)
- True multimodal retrieval (text, table, figure/image evidence).
- Agentic multimodal planning and tool orchestration.
- Structured grounded answer policy enforcement.
- Golden v3 evaluation hardening and regression gates.
- Observability for plan/tool/finalization decisions.

### P1 Deferred
- Multi-agent collaboration/swarm behavior.
- External document systems and enterprise integrations.
- Advanced model routing and cost-aware orchestration.

## Architecture Strategy
### System Boundaries
- Keep current architecture:
  - API: FastAPI (`apps/api`)
  - UI: Streamlit (`apps/ui`)
  - Application core: `packages/application`
  - Domain core: `packages/domain`
  - Adapters and providers: `packages/adapters`
  - Contracts and reports: `.context/project`, `.context/reports`
- Preserve hexagonal boundaries: framework-specific imports remain in adapters only.

### Target Modules
| Module | Responsibility | Primary Surfaces |
|---|---|---|
| Multimodal Ingestion | Extract text/table/figure assets and metadata | `ingest_document` use case, `data/assets/*` |
| Visual Retrieval | Image embedding/index and retrieval | `packages/adapters/embeddings`, retrieval adapters |
| Multimodal Fusion | Merge text and visual evidence, rerank | `search_evidence` pipeline |
| Agentic Orchestration | Plan, tool loop, state transitions, fallback | `packages/adapters/agentic`, `answer_question` |
| Structured Answering | Enforce answer sections and grounding policy | `answer_question` output contract |
| Evaluation and Gates | Golden runs, reliability checks, CI thresholds | `/evaluate/golden`, `scripts/run_*` |
| Trace and Audit | Agent/tool traces and failure taxonomies | `.context/reports/*traces*.jsonl` |

### Data Artifact Additions (Proposed)
| Artifact | Purpose | Key Fields |
|---|---|---|
| `visual_chunks.jsonl` | Region-level figure/table visual units | `doc_id`, `page`, `bbox`, `figure_id`, `caption` |
| `visual_embedding_index` | Visual retrieval vectors | `chunk_id`, `embedding`, `provider`, `model` |
| `multimodal_hit_links` | Tie visual hits to text/table context | `chunk_id`, `linked_chunk_ids`, `link_type` |
| `agent_run_events` | Structured execution telemetry | `trace_id`, `step`, `tool`, `status`, `latency_ms` |

## Implementation Work Packages
### WP-01 Multimodal Asset and Index Foundation (P0)
**User Stories**
- As the system, I can index visual regions so retrieval is not limited to OCR/captions.
- As an operator, I can get answers backed by figure/table evidence when relevant.

**Acceptance Criteria**
- Ingestion produces visual chunks with page and region metadata.
- Visual index build step is repeatable and deterministic.
- Visual artifacts are mapped back to citation metadata.

**Technical Tasks**
- Add visual chunk extraction artifacts under `data/assets/<doc_id>/`.
- Add visual index generation adapter and config.
- Add integrity checks for visual chunk to citation mappings.

### WP-01A Ingestion Validation UX (P0)
**User Stories**
- As an operator, I can visually inspect vision extraction and embedding outputs before publish.
- As an engineer, I can see deterministic validation failures immediately and re-run with the same config.

**Acceptance Criteria**
- Ingestion page shows pipeline stages:
  - `Upload PDF`
  - `Parse + OCR`
  - `Vision extraction`
  - `Embedding generation`
  - `Contract validation`
  - `Finalize + publish`
- Deterministic gates are displayed with pass/fail details:
  - schema validation
  - ID uniqueness and mapping integrity
  - embedding count and dimension consistency
  - fallback trigger rules for noisy vision output
- Review workspace supports page-level region inspection with metadata:
  - `chunk_id`, caption, OCR text, linked text chunks, embedding status
- Re-run controls preserve reproducibility:
  - pinned model/version config
  - source PDF fingerprint/hash
  - run history and rerun with same config

**Technical Tasks**
- Extend ingestion UI with stage timeline and per-stage status.
- Add validation summary pane with field-level errors.
- Add page/region inspector for visual chunks and link integrity.
- Add run metadata capture (`pdf_hash`, model versions, config snapshot) and rerun action.

### WP-02 Visual and Hybrid Retrieval (P0)
**User Stories**
- As an operator, multimodal questions retrieve image evidence when text alone is weak.
- As evaluator, I can see modality distribution in retrieved evidence.

**Acceptance Criteria**
- Visual search endpoint/adapter returns ranked visual hits.
- Hybrid retrieval merges text, table, and visual hits.
- Retrieval traces include per-modality hit counts and scores.

**Technical Tasks**
- Implement `search_evidence_visual` path and adapter.
- Add hybrid merge logic and rerank feature flags.
- Extend retrieval tracing payload for modality diagnostics.

### WP-03 Agentic Multimodal Planning and Tooling (P0)
**User Stories**
- As the agent, I can choose tools by modality and question complexity.
- As developer, I can inspect plan and tool call outcomes clearly.

**Acceptance Criteria**
- Planner emits multimodal-aware plans.
- Tool executor validates and runs text/visual/fusion tools safely.
- Graph runner enforces budgets and fallback with no contract break.

**Technical Tasks**
- Add multimodal tool definitions in agentic adapter.
- Add modality routing policies in graph nodes.
- Add per-step trace events with tool args/status.

### WP-04 Structured Answer and Grounding Policy (P0)
**User Stories**
- As user, I receive consistent answer structure with explicit evidence gaps.
- As evaluator, grounded answers are clearly distinguishable from partial/not_found.

**Acceptance Criteria**
- Answer sections include `Direct answer`, `Key details`, and `If missing data`.
- `ok` status requires grounded citation checks to pass.
- Multimodal citations include visual/table references when used.

**Technical Tasks**
- Define strict output template policy for eval mode.
- Add grounding gate checks before finalization.
- Extend citation formatting for multimodal references.

### WP-05 Golden v3 and Reliability Gates (P0)
**User Stories**
- As QA, I can measure progress by question type, modality, and turn depth.
- As team, regressions fail fast in CI.

**Acceptance Criteria**
- Golden v3 taxonomy validated with no schema drift.
- Reliability runs report modality-level and turn-level KPIs.
- CI gates enforce minimum thresholds.

**Technical Tasks**
- Finalize `golden_questions_v3.yaml` and validation checks.
- Extend reporting with failure taxonomy outputs.
- Add gate thresholds to regression scripts.

### WP-06 Observability and Debug Surface (P0)
**User Stories**
- As developer, I can quickly identify whether failures are retrieval, planning, or answer formatting.
- As reviewer, I can compare runs across configs and sprints.

**Acceptance Criteria**
- Reports include per-run trace summary and top failure classes.
- Agent traces can be correlated to question IDs and doc IDs.
- Run folders follow strict naming conventions.

**Technical Tasks**
- Standardize run metadata in reports.
- Add trace-to-question linkage in evaluation outputs.
- Add dashboard-ready summary JSON artifacts.

## Sprint-by-Sprint Delivery Plan
| Sprint | Focus | Exit Criteria |
|---|---|---|
| W08 | Foundation plus baseline hardening | Golden v3 schema locked, multimodal artifact design frozen, ingestion validation UX spec finalized, baseline reports for current ingestion |
| W09 | Visual retrieval plus hybrid fusion MVP | Visual/hybrid retrieval active, modality traces present, targeted multimodal pass improvement |
| W10 | Agentic multimodal toolchain plus structured finalization | Planner/tool routing by modality stable, answer structure policy enforced, fallback rate controlled |
| W11 | Reliability gates plus stabilization | CI thresholds active, full six-manual evaluation run complete, demo-ready evidence pack |

## Engineering Breakdown (Execution Ready)
### Backend and Application
- Add adapter implementations for visual retrieval and multimodal fusion.
- Extend use-cases with modality-aware scoring and trace context.
- Keep ports stable and prevent framework leakage into core layers.

### Evaluation and Tooling
- Extend golden and reliability scripts for modality KPIs.
- Add threshold enforcement and run metadata normalization.
- Maintain reproducible report naming and artifact layout.

### UI and Developer Experience
- Surface optional debugging context (`reasoning_summary`, trace hints) in developer/admin views.
- Keep user-facing chat concise while retaining full traceability in reports.
- Add ingestion validation UX with visual chunk review and deterministic gate status.

### Quality and Verification
- Unit coverage for adapter and use-case logic.
- Integration coverage for ingestion plus evaluation pipeline.
- Live golden runs on ingested docs each sprint with report artifacts.

## Definition of Done (Per Work Package)
- Acceptance criteria met.
- Tests added and passing.
- Trace and report outputs verified.
- Documentation updated in `.context/sprint` and `.context/reports`.
- No architecture boundary violation.

## Risks and Mitigations
| Risk | Impact | Mitigation |
|---|---|---|
| Latency increase from multimodal retrieval | High | Modality routing and strict iteration/tool budgets |
| False failures from brittle expected keywords | Medium | Per-doc terminology packs and normalized expected matching |
| Framework leakage into core layers | High | Boundary tests and adapter-only framework imports |
| Overfitting to two ingested manuals | High | Force periodic full-six-manual ingestion/eval cycles |
| Low multimodal signal quality | Medium | Region-level visual indexing and cross-modal fusion tuning |

## Metrics
- Overall golden pass rate (target >= 70% by W11).
- Multi-turn pass rate (target >= 65% by W11).
- Multimodal pass rate (target >= 60% by W11).
- Grounded finalization rate (target >= 98%).
- Turn execution rate (target >= 98%).
- Agent fallback rate and tool failure rate.

## Immediate Next Actions (W08 Start)
- [x] Freeze golden v3 schema and acceptance criteria from `.context/project/data/golden_questions_v3.yaml`. (Evidence: `.context/reports/contract_checks/golden_v3_contract_check_20260220.json`)
- [x] Define visual chunk and embedding artifact contract for ingestion output. (Evidence: `.context/project/ARTIFACT_CONTRACT_VISUAL_V1.md`, `packages/adapters/data_contracts/visual_artifacts.py`, `scripts/validate_visual_artifacts.py`)
- [x] Run and archive baseline report for current ingested docs with failure taxonomy. (Evidence: `.context/reports/golden_live/20260220_011050/run_summary.json`, `.context/reports/golden_live/20260220_011050/failed_cases.csv`)

## Success Criteria Checklist (Update After Every Step)
**Instructions**
- Update this checklist immediately after completing each step.
- Mark completed items with `[x]`.
- Add evidence links (PR, commit, report path, test output) inline next to the item.
- Do not progress to next work package until gate checks are complete.

### Global Delivery Gates (Apply to Every Work Package)
- [ ] Product acceptance walkthrough completed.
- [x] Golden/reliability tests passing for targeted scope. (Evidence: `pytest tests/unit -q` -> 55 passed, `pytest tests/integration/test_api_e2e.py -q` -> 3 passed)
- [x] Live run report generated under `.context/reports/golden_live/<run_id>/`. (Evidence: `.context/reports/golden_live/20260220_115243/`)
- [x] Architecture boundaries verified by tests. (Evidence: `pytest tests/unit -q` includes `tests/unit/test_architecture_boundaries.py`)
- [x] Documentation and runbook updated. (Evidence: `.context/sprint/Sprint-multipodal-rag.md`, `.context/project/ARTIFACT_CONTRACT_VISUAL_V1.md`)

### WP-01 Multimodal Asset and Index Foundation
- [x] Visual chunk artifact schema finalized. (Evidence: `.context/project/ARTIFACT_CONTRACT_VISUAL_V1.md`)
- [x] Visual chunk generation verified on at least 2 manuals. (Evidence: `.context/reports/contract_checks/visual_artifact_generation_20260220.json`)
- [x] Visual citation link integrity check passing. (Evidence: `.context/reports/contract_checks/visual_artifact_contract_check_strict_20260220.json`)

### WP-01A Ingestion Validation UX
- [x] Ingestion stage timeline visible and accurate. (Evidence: `apps/ui/admin_main.py` `_render_stage_timeline`, job stages include `visual_artifacts` and `contract_validation`)
- [x] Deterministic validation gate panel implemented and verified. (Evidence: `GET /ingested/{doc_id}/validation`, `apps/ui/admin_main.py` gate panel, `tests/integration/test_api_e2e.py::test_ingested_validation_and_reingest_flow`)
- [x] Visual region inspector wired to chunk metadata and embedding status. (Evidence: `GET /ingested/{doc_id}/visual-chunks`, `apps/ui/admin_main.py` visual inspector)
- [x] Re-run with identical config works and stores run history metadata. (Evidence: `POST /jobs/reingest/{doc_id}`, `data/assets/<doc_id>/ingestion_runs.jsonl`, `POST /ingested/{doc_id}/visual-artifacts/generate`)

### WP-02 Visual and Hybrid Retrieval
- [x] Visual retrieval adapter implemented and validated. (Evidence: `packages/adapters/retrieval/filesystem_chunk_query_adapter.py`, `tests/unit/test_retrieval.py::test_filesystem_chunk_query_reads_visual_chunks`)
- [x] Hybrid retrieval returns mixed-modality hits on multimodal questions. (Evidence: `.context/reports/contract_checks/wp02_retrieval_mixed_modality_20260220.json`)
- [x] Retrieval trace includes modality-level diagnostics. (Evidence: `packages/application/use_cases/search_evidence.py`, `.context/reports/contract_checks/wp02_retrieval_trace_sample_20260220.jsonl`)

### WP-03 Agentic Multimodal Planning and Tooling
- [x] Planner emits modality-aware steps. (Evidence: `packages/adapters/agentic/noop_planner_adapter.py`, `tests/unit/test_noop_planner_multimodal.py`)
- [x] Tool argument validation and failures handled without crashes. (Evidence: `tests/unit/test_agentic_tool_validation.py`)
- [x] Graph execution budgets and fallback verified. (Evidence: `tests/unit/test_agentic_graph_runner.py`, `tests/unit/test_answer_question_agentic.py`)

### WP-04 Structured Answer and Grounding Policy
- [x] Structured answer sections consistently present in eval mode. (Evidence: `packages/application/use_cases/answer_question.py` `_format_eval_answer`, `packages/application/use_cases/run_golden_evaluation.py` passes `enforce_structured_output=True`, `tests/unit/test_answer_question.py::test_answer_question_enforces_structured_sections_in_eval_mode`, `tests/unit/test_golden_evaluation.py::test_run_golden_evaluation_uses_structured_output_mode`)
- [x] Grounding gate blocks ungrounded `ok` responses. (Evidence: `packages/application/use_cases/answer_question.py` grounding fallback in `_build_answer_output`, `tests/unit/test_answer_question.py::test_answer_question_grounding_gate_demotes_ungrounded_ok`)
- [x] Multimodal citation rendering validated. (Evidence: `packages/domain/citation_formatter.py`, `tests/unit/test_answer_question.py::test_answer_question_citation_labels_include_multimodal_refs`)

### WP-05 Golden v3 and Reliability Gates
- [x] Golden v3 data contracts validated. (Evidence: `.context/reports/contract_checks/golden_v3_contract_check_20260220.json`)
- [x] KPI breakdown by question type/modality available in summary. (Evidence: `.context/reports/golden_live/20260220_011050/run_summary.json`)
- [x] CI regression gate thresholds enforced. (Evidence: `scripts/run_regression_gates.py` (`--min-pass-rate`, `--min-grounded-rate`, `--min-turn-execution-rate`, v3 default path), `.github/workflows/18-regression-gates.yml` gate invocation)

### WP-06 Observability and Debug Surface
- [x] Agent trace summary artifact generated per run. (Evidence: `.context/reports/golden_live/20260220_011050/agent_trace_summary.json`)
- [x] Failure taxonomy report produced and reviewed. (Evidence: `.context/reports/golden_live/20260220_011050/failed_cases.json`)
- [x] Run-to-run comparison report template established. (Evidence: `scripts/run_baseline_golden_archive.py`, `.context/reports/golden_live/20260220_005645/`, `.context/reports/golden_live/20260220_011050/`)

### Sprint Exit Checklist (W08-W11)
- [ ] W08 exit criteria met and signed off.
- [ ] W09 exit criteria met and signed off.
- [ ] W10 exit criteria met and signed off.
- [ ] W11 exit criteria met and signed off.
- [ ] Final reliability review completed.
- [ ] Production readiness review completed.
