# Q1 2026 Implementation Plan — Phases 1-4

**Version:** 1.0  
**Date:** 2026-02-21  
**Role:** Project Owner + Architect  
**Status:** Approved  

---

> **Purpose:** This document is the authoritative implementation checklist for all phases.
> Each phase section is structured to satisfy:
> - **Workflow 12** (Epic/Story Tracking): `type:epic` with `Parent:` link and story issue list
> - **Workflow 13** (Definition of Ready): contains `Success Criteria`, `Non-Goals`, `Acceptance Criteria`
> - **Workflow 14** (Definition of Done): each PR must contain `Evidence Mapping`, `Tests`, `Documentation`
>
> Copy the relevant section into GitHub issue bodies when creating/updating Epic and Story issues.

---

## Phase 1 — Table and Diagram Fidelity

**GitHub Issue:** #3  
**Branch:** `feature/3-table-diagram-fidelity`  
**PR Target:** `develop`  
**Role:** Implementer + Architect  
**Labels:** `type:epic`, `state:ready`, `priority:high`  

### Epic Issue Body (copy to #3)

```
# 🎯 Epic: Phase 1 — Table and Diagram Fidelity

Parent: #3

## Overview
Deliver structured table extraction (row-level chunks), region-based figure OCR with
bounding box coordinates, and table/figure identifiers in citations.

## Architecture Notes

### Components Affected
- [ ] packages/adapters/tables/simple_table_extractor_adapter.py
- [ ] packages/ports/table_extractor_port.py
- [ ] packages/application/use_cases/ingest_document.py
- [ ] packages/adapters/data_contracts/visual_artifact_generation.py
- [ ] packages/adapters/data_contracts/contracts.py

### Technical Approach
1. Update TableExtractorPort.extract() to return structured rows (not flat text)
2. Update SimpleTableExtractorAdapter to parse headers, row_cells, units per row
3. Update _process_single_page() to emit table_row chunks per row with row_index metadata
4. Add PyMuPDF region detection to extract bbox for figures and tables
5. Assign figure_id to OCR output with region bbox coordinates
6. Regenerate visual artifacts to include bbox and figure_id

### Dependencies
- PyMuPDF (fitz) already in requirements
- OCR adapters already support page-level; region-level needs coordinate injection

## Stories
- [ ] #TBD — Story 1: Update TableExtractorPort contract
- [ ] #TBD — Story 2: Emit table_row chunks in ingestion
- [ ] #TBD — Story 3: Region-based OCR and bbox extraction
- [ ] #TBD — Story 4: Contract validation for table_row and figure artifacts

## Success Criteria
1. Golden table questions pass rate >= 80%
2. Table recall-at-5 >= 0.80
3. All table_row chunks include headers, row_index, units in metadata
4. All figure chunks include figure_id and bbox coordinates in metadata

## Acceptance Criteria
- [ ] TableExtractorPort.extract() returns list of ExtractedTableRow with headers field
- [ ] Ingestion emits content_type='table_row' (one per row) instead of 'table'
- [ ] table_id and row_index present on all table_row chunks
- [ ] figure_id and bbox (list of 4 floats) present on all figure chunks
- [ ] validate_data_contracts.py passes for table_row and figure artifact contracts
- [ ] Golden evaluation run on siemens_g120 shows table recall improvement

## Non-Goals
- No changes to text chunking strategy (covered in Phase 3)
- No graph store or connector entity extraction (Phase 4)
- No reranker model changes (Phase 2)
- No catalog revision tracking (Phase 3)

## Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Heuristic table detection fails on unusual layouts | Medium | Golden test gates catch regressions |
| PyMuPDF layout API differences across PDF types | Medium | Fallback to page-level OCR if region fails |
| table_row migration breaks existing chunk queries | High | Legacy content_type=table supported during migration |

## Migration Notes
- Existing table chunks must be regenerated into table_row chunks
- Legacy content_type=table accepted during Phase 1 window only
- All docs must be reingested after Phase 1 merges

## Timeline
- Start: Week 1
- Target completion: End of Week 3
```

---

### Story Breakdown (create as separate issues)

#### Story 1: Update TableExtractorPort contract

**Labels:** `type:story`, `state:ready`, `priority:high`, `role:implementer`

**Issue body template:**
```
# 📖 Story: Update TableExtractorPort contract

Parent: #3

## Description
Change TableExtractorPort.extract() to return structured row data with headers, row_cells,
units, and row_index instead of a flat text string. Update SimpleTableExtractorAdapter
to implement the new contract.

## Acceptance Criteria
- [ ] ExtractedTableRow dataclass has fields: table_id, page_number, headers, row_cells, units, row_index, row_text
- [ ] TableExtractorPort.extract() signature returns list[ExtractedTableRow]
- [ ] SimpleTableExtractorAdapter implements header detection from first row
- [ ] Unit tests cover header parsing, key-value rows, pipe-delimited rows
- [ ] Existing golden evaluation does not regress

## Success Criteria
1. ExtractedTableRow contract matches DATA_CONTRACTS.md §3
2. Adapter correctly parses at least 3 different table formats (pipe, key-value, multi-column)
3. All unit tests pass with >80% coverage on new adapter code

## Non-Goals
- No ingestion changes (Story 2 handles this)
- No UI changes
- No performance optimizations

## Technical Notes
- See DATA_CONTRACTS.md §3 (Table Row Contract) for required fields
- See packages/ports/table_extractor_port.py for current signature
- Current ExtractedTable only has table_id, page_number, text — upgrade it

## Dependencies
- None (first story in phase)

## Test Approach
- Unit tests: test_table_extractor_adapter.py (new file)
- Test cases: pipe-delimited, key-value, multi-column, empty input, single row
- Integration tests: run ingest on one manual, check for table_row chunks

## Estimate
Points: 2
```

#### Story 2: Emit table_row chunks in ingestion

**Labels:** `type:story`, `state:ready`, `priority:high`, `role:implementer`

**Issue body template:**
```
# 📖 Story: Emit table_row chunks in ingestion

Parent: #3

## Description
Update _process_single_page() in ingest_document.py to emit one chunk per table row
with content_type='table_row', and include headers, row_index, units in metadata.

## Acceptance Criteria
- [ ] ingest_document.py emits content_type='table_row' for each row (not 'table')
- [ ] Each chunk has metadata.row_index (int), metadata.headers (list), metadata.units (list)
- [ ] table_id set on every table_row chunk
- [ ] IngestDocumentOutput.by_type reports 'table_row' key
- [ ] Integration test: ingest siemens_g120 manual and verify table_row chunks present

## Success Criteria
1. Ingestion output contains table_row chunks with all metadata fields populated
2. No regression in text or figure chunk counts
3. Integration test validates metadata schema against DATA_CONTRACTS.md §2

## Non-Goals
- No changes to TableExtractorPort after Story 1 is merged
- No changes to figure/vision_summary chunk logic
- No cache implementation (Phase 3)

## Technical Notes
- Depends on Story 1: ExtractedTableRow with headers field
- _process_single_page() in packages/application/use_cases/ingest_document.py
- Each ExtractedTableRow → one Chunk with content_type='table_row'
- Store headers/units/row_index in metadata dict

## Dependencies
- [ ] #TBD Story 1 merged (ExtractedTableRow available)

## Test Approach
- Integration tests: tests/integration/test_ingest_pipeline.py
- Assert chunk type distribution includes 'table_row'
- Assert metadata fields present on sampled table_row chunks

## Estimate
Points: 2
```

#### Story 3: Region-based OCR and bbox extraction

**Labels:** `type:story`, `state:ready`, `priority:high`, `role:implementer`

**Issue body template:**
```
# 📖 Story: Region-based OCR and bbox extraction

Parent: #3

## Description
Use PyMuPDF layout analysis to extract bounding boxes (bbox) for figure and table regions
on each page. Assign figure_id to OCR text from detected regions. Store bbox in
metadata.bbox on figure_ocr chunks.

## Acceptance Criteria
- [ ] PDF pages are analysed for layout blocks with bbox coordinates
- [ ] Figure regions identified by image block type or figure/caption proximity
- [ ] figure_id assigned per region (format: fig-p{page:04d}-{idx:03d})
- [ ] bbox (list of 4 floats [x0, y0, x1, y1]) stored in metadata.bbox
- [ ] OCR adapter called with bbox region crop, not entire page, when region detected
- [ ] Unit tests cover bbox extraction logic with mocked PyMuPDF output

## Success Criteria
1. figure_id and bbox present on all figure_ocr chunks (verified via data contract validator)
2. OCR quality improves compared to page-level OCR baseline
3. No regression in ingest throughput > 20%

## Non-Goals
- No changes to table extraction logic (Stories 1-2)
- No vision_summary changes
- No connector entity extraction (Phase 4)

## Technical Notes
- PyMuPDF (fitz) is already a dependency
- Use page.get_text('dict') to get blocks with bbox
- Block type 1 = image, type 0 = text; detect image blocks near figure captions
- See ARCHITECTURE.md §4.1 for chunking strategy

## Dependencies
- [ ] Stories 1 and 2 merged

## Test Approach
- Unit tests: test_ingest_region_ocr.py
- Mock PyMuPDF page.get_text('dict') output
- Integration test: verify figure_ocr chunks have bbox metadata on sample PDF

## Estimate
Points: 3
```

#### Story 4: Contract validation for table_row and figure artifacts

**Labels:** `type:story`, `state:ready`, `priority:high`, `role:implementer`

**Issue body template:**
```
# 📖 Story: Contract validation for table_row and figure artifacts

Parent: #3

## Description
Add contract validation rules for table_row and figure artifact chunks to
validate_data_contracts.py and run existing golden evaluation to confirm Phase 1
acceptance criteria are met.

## Acceptance Criteria
- [ ] validate_data_contracts.py validates all table_row chunk metadata fields
- [ ] validate_data_contracts.py validates figure_id and bbox on figure_ocr chunks
- [ ] Golden evaluation run on siemens_g120 basic positioner shows table recall >= 0.80
- [ ] Unit and integration tests pass with >80% coverage
- [ ] Ingestion QC produces no errors for manuals in /data/assets

## Success Criteria
1. Contract validator reports 0 errors on freshly ingested manuals
2. Golden table pass rate >= 80% (measured via run_golden_evaluation.py)
3. Overall golden pass rate does not regress from pre-Phase-1 baseline

## Non-Goals
- No retrieval changes (Phase 2)
- No QC reporting pipeline (Phase 3)

## Technical Notes
- See DATA_CONTRACTS.md §2, §3, §4 for field requirements
- packages/application/use_cases/validate_data_contracts.py
- Run scripts/run_golden_evaluation.py to get pass rate

## Dependencies
- [ ] Stories 1, 2, 3 merged

## Test Approach
- Unit tests: test_validate_data_contracts.py additions
- Integration tests: test_ingest_pipeline.py — validate full run on sample manual
- Golden evaluation: run_golden_evaluation.py on siemens_g120

## Estimate
Points: 2
```

---

### Phase 1 DoR Checklist (for each story issue before labeling `state:ready`)

- [ ] Issue body contains `Success Criteria` section
- [ ] Issue body contains `Non-Goals` section
- [ ] Issue body contains `Acceptance Criteria` section
- [ ] `Parent: #3` linked in body
- [ ] Dependencies identified and linked
- [ ] Estimated story points assigned
- [ ] Architect reviewed (structural change to port)
- [ ] Interface change documented (TableExtractorPort signature)

### Phase 1 DoD Checklist (for each PR)

PR body **must** contain all three:

- [ ] `Evidence Mapping` table: each criterion → test file → line range → status
- [ ] `Tests` section or mention of test additions and pass status
- [ ] `Documentation` section: updated ARCHITECTURE.md / DATA_CONTRACTS.md if needed

---

---

## Phase 2 — Retrieval Reliability

**GitHub Issue:** #4  
**Branch:** `feature/4-retrieval-reliability`  
**PR Target:** `develop`  
**Labels:** `type:epic`, `state:ready`, `priority:high`  
**Depends on:** Phase 1 complete

### Epic Issue Body (copy to #4)

```
# 🎯 Epic: Phase 2 — Retrieval Reliability

Parent: #4

## Overview
Add procedure intent detection, compute evidence coverage score, enforce abstain when
coverage < 0.50, add modality_hit_counts to retrieval traces, and enforce modality
diversity in retrieval results.

## Architecture Notes

### Components Affected
- [ ] packages/application/use_cases/search_evidence.py (_detect_intent, trace logger)
- [ ] packages/application/use_cases/answer_question.py (_is_insufficient_evidence)
- [ ] packages/domain/policies.py (evidence coverage policy)
- [ ] packages/adapters/retrieval/retrieval_trace_logger.py

### Technical Approach
1. Add 'procedure' to _detect_intent() in search_evidence.py
2. Implement _compute_evidence_coverage() returning float 0..1
3. Update answer_question.py to use coverage score for abstain decision
4. Add modality_hit_counts field to SearchEvidenceOutput and trace log
5. Add modality diversity enforcement in rerank pool

### Dependencies
- Phase 1 table_row chunks must be ingested and available
- Reranker adapter already integrated

## Stories
- [ ] #TBD — Story 1: Add procedure intent detection
- [ ] #TBD — Story 2: Evidence coverage scoring and abstain enforcement
- [ ] #TBD — Story 3: Modality hit counts in retrieval traces
- [ ] #TBD — Story 4: Modality diversity enforcement in reranker pool

## Success Criteria
1. Golden overall pass rate >= 85%
2. Incorrect answers reduced by 50% on known failure set
3. Evidence coverage threshold enforced at 0.50
4. Procedure intent recall-at-5 >= 0.75
5. Modality diversity: top-5 results include >= 2 modalities for multimodal intent

## Acceptance Criteria
- [ ] _detect_intent() returns 'procedure' for step/instruction queries
- [ ] _compute_evidence_coverage() returns float 0..1 and is covered by unit tests
- [ ] answer_question.py sets abstain=True and confidence<0.50 when coverage < 0.50
- [ ] SearchEvidenceOutput.hits traces include modality_hit_counts dict
- [ ] Reranker pool enforces at least 2 modality types in top-5 when available
- [ ] Golden evaluation pass rate >= 85% on combined golden set

## Non-Goals
- No changes to embedding model
- No catalog revision tracking (Phase 3)
- No graph store (Phase 4)
- No connector entity extraction (Phase 4)

## Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Coverage score too strict, over-abstains | High | Tune threshold with golden set; default 0.50 per spec |
| Modality diversity conflicts with relevance | Medium | Soft constraint via score weighting not hard filter |
| Procedure intent false positives | Low | Verified with golden procedure questions |

## Timeline
- Start: Week 2 (parallel with Phase 1 stories 3-4)
- Target completion: End of Week 4
```

---

### Story Breakdown (create as separate issues)

#### Story 1: Procedure intent detection

**Labels:** `type:story`, `state:ready`, `priority:high`, `role:implementer`

**Issue body template:**
```
# 📖 Story: Add procedure intent detection

Parent: #4

## Description
Extend _detect_intent() in search_evidence.py to return 'procedure' for queries about
steps, instructions, sequences, and how-to content.

## Acceptance Criteria
- [ ] _detect_intent() returns 'procedure' for step/instruction/how-to queries
- [ ] Procedure intent terms defined: 'step', 'procedure', 'instruction', 'sequence',
      'how to', 'how do', 'replace', 'install', 'commissioning', 'startup', 'shutdown'
- [ ] Procedure-type content_type_weight applied: 1.30 boost for text chunks
- [ ] Unit tests cover procedure detection and non-procedure rejection
- [ ] Existing table and diagram intent detection not regressed

## Success Criteria
1. Procedure recall-at-5 >= 0.75 on golden procedure questions
2. Intent detection adds 'procedure' without reducing table/diagram accuracy
3. Unit test coverage >80% on modified _detect_intent()

## Non-Goals
- No changes to coverage scoring (Story 2)
- No changes to modality diversity (Story 4)

## Technical Notes
- packages/application/use_cases/search_evidence.py: _detect_intent()
- PROCEDURE_TERMS set similar to TABLE_TERMS and DIAGRAM_TERMS patterns
- If procedure_hits > table_hits and > diagram_hits: return 'procedure'

## Dependencies
- No blocking stories

## Test Approach
- Unit tests: tests/unit/test_search_evidence.py additions
- Test with real procedure-type golden questions

## Estimate
Points: 2
```

#### Story 2: Evidence coverage scoring and abstain enforcement

**Labels:** `type:story`, `state:ready`, `priority:high`, `role:implementer`

**Issue body template:**
```
# 📖 Story: Evidence coverage scoring and abstain enforcement

Parent: #4

## Description
Implement a numeric evidence coverage score (0..1) and enforce abstain=True in
answer generation when score < 0.50. Replace the existing token overlap heuristic
with an explicit coverage computation used in both retrieval and answering.

## Acceptance Criteria
- [ ] _compute_evidence_coverage(query, hits) returns float in [0, 1]
- [ ] Coverage incorporates: anchor term overlap, best retrieval score, modality match
- [ ] answer_question.py checks coverage and sets abstain=True when < 0.50
- [ ] AnswerQuestionOutput.confidence is a float (0..1), not string
- [ ] Unit tests for _compute_evidence_coverage with multiple scenarios
- [ ] Golden evaluation: abstain rate on known-bad questions >= 70%

## Success Criteria
1. AnswerQuestionOutput.confidence type is float 0..1 matching DATA_CONTRACTS.md §7
2. All incorrect answers in known 'hallucination' set trigger abstain
3. Abstain threshold 0.50 configurable (defaults from PRODUCT_SPEC.md §7.2)

## Non-Goals
- No changes to retrieval scoring weights
- No LLM judge integration
- No UI changes for abstain display

## Technical Notes
- PRODUCT_SPEC.md §7.2: abstain when coverage < 0.50 or best score < 0.22
- AnswerQuestionOutput.confidence currently is str — change to float
- _is_insufficient_evidence() in answer_question.py can be refactored
- Confidence bands: 0.70-1.0 high, 0.40-0.69 medium, 0.00-0.39 low

## Dependencies
- No blocking stories (can parallel with Story 1)

## Test Approach
- Unit tests: tests/unit/test_answer_question.py additions
- Test coverage scenarios: empty hits, low scores, partial match, strong match
- Integration: run golden eval and check abstain behavior on weak evidence queries

## Estimate
Points: 3
```

#### Story 3: Modality hit counts in retrieval traces

**Labels:** `type:story`, `state:ready`, `priority:medium`, `role:implementer`

**Issue body template:**
```
# 📖 Story: Modality hit counts in retrieval traces

Parent: #4

## Description
Add modality_hit_counts (dict with keys: text, table, figure, visual) to retrieval
trace output and to SearchEvidenceOutput so callers can inspect modality distribution.

## Acceptance Criteria
- [ ] SearchEvidenceOutput has modality_hit_counts: dict[str, int]
- [ ] Trace log payload includes modality_hit_counts at top level
- [ ] Hit counts computed for top_hits using _modality_bucket() function
- [ ] Keys: 'text', 'table', 'figure', 'visual' (no other keys)
- [ ] validate_data_contracts.py validates modality_hit_counts in trace files
- [ ] Unit tests cover bucket aggregation logic

## Success Criteria
1. Retrieval trace files contain modality_hit_counts matching DATA_CONTRACTS.md §6
2. Contract validator passes on all generated trace files
3. Trace count accurately reflects hitlist modality distribution

## Non-Goals
- No changes to scoring logic
- No UI trace visualization

## Technical Notes
- search_evidence.py: already computes hit_modality_counts but doesn't expose it
- Update SearchEvidenceOutput dataclass to include modality_hit_counts
- Update search_evidence_use_case return statement

## Dependencies
- [ ] Story 1 (procedure intent adds new modality bucket path)

## Test Approach
- Unit tests: test_search_evidence.py additions for output field
- Contract test: validate trace JSONL output against DATA_CONTRACTS.md §6

## Estimate
Points: 1
```

#### Story 4: Modality diversity in reranker pool

**Labels:** `type:story`, `state:ready`, `priority:medium`, `role:implementer`

**Issue body template:**
```
# 📖 Story: Modality diversity enforcement in reranker pool

Parent: #4

## Description
Add a soft modality diversity constraint to the reranker pool so that the top-5
evidence hits include at least 2 distinct modalities when the intent is multimodal
(table or diagram).

## Acceptance Criteria
- [ ] _apply_reranker() or post-rerank step enforces diversity when intent is 'table' or 'diagram'
- [ ] At least 2 distinct modality buckets in top-5 when available in pool
- [ ] Diversity enforcement is soft: does not replace a top hit unless score difference < 0.10
- [ ] Unit tests cover diversity logic with various pool compositions

## Success Criteria
1. Multimodal queries show >=2 modalities in top-5 evidence (verified in golden traces)
2. Retrieval quality (recall-at-5) does not regress > 0.02

## Non-Goals
- No hard diversity filter
- No changes to scoring weights outside diversity logic

## Technical Notes
- After reranking, check modality diversity in top_n slice
- If only 1 modality and pool has alternative, swap last hit for diverse hit
- ARCHITECTURE.md §3.2: diversity documented as soft constraint

## Dependencies
- [ ] Stories 1-3 merged

## Test Approach
- Unit tests: test_search_evidence_diversity.py
- Test: homogeneous pool → diversity unchanged; mixed pool → diversity enforced

## Estimate
Points: 2
```

---

### Phase 2 DoR Checklist

- [ ] Issue body contains `Success Criteria`
- [ ] Issue body contains `Non-Goals`
- [ ] Issue body contains `Acceptance Criteria`
- [ ] `Parent: #4` linked in body
- [ ] Phase 1 acceptance criteria verified before Phase 2 starts
- [ ] Coverage threshold (0.50) confirmed in PRODUCT_SPEC.md §7.2
- [ ] confidence type change (str→float) reviewed by architect

### Phase 2 DoD Checklist (for each PR)

- [ ] `Evidence Mapping` table: criterion → test → location → status
- [ ] `Tests` section: unit and integration tests added and passing
- [ ] `Documentation` section: ARCHITECTURE.md §3.2 updated if needed

---

---

## Phase 3 — Industrial Scale

**GitHub Issue:** #5  
**Branch:** `feature/5-industrial-scale`  
**PR Target:** `develop`  
**Labels:** `type:epic`, `state:ready`, `priority:medium`  
**Depends on:** Phase 1 and 2 complete

### Epic Issue Body (copy to #5)

```
# 🎯 Epic: Phase 3 — Industrial Scale

Parent: #5

## Overview
Add ingestion timing metrics, document catalog revision/source_hash tracking, retrieval
caching, and ingestion QC metrics to deliver production-ready operational observability
and throughput management.

## Architecture Notes

### Components Affected
- [ ] packages/application/use_cases/ingest_document.py (timing, QC metrics)
- [ ] packages/ports/document_catalog_port.py (revision, source_hash, tags)
- [ ] packages/adapters/data_contracts/yaml_catalog_adapter.py (new fields)
- [ ] packages/adapters/data_contracts/contracts.py (CatalogEntry new fields)
- [ ] packages/application/use_cases/search_evidence.py (cache layer)

### Technical Approach
1. Add timing instrumentation to ingest_document_use_case
2. Compute text_coverage, ocr_coverage, table_yield, embedding_coverage, status
3. Extend DocumentCatalogRecord with revision, source_hash, tags, contract_version
4. Implement simple dict-based retrieval cache keyed by (doc_id, query)
5. Store QC metrics in IngestDocumentOutput matching DATA_CONTRACTS §8

### Dependencies
- Redis already available in docker-compose for future cache backend
- Phase 1-2 must be stable (chunks available for QC measurement)

## Stories
- [ ] #TBD — Story 1: Ingestion timing metrics
- [ ] #TBD — Story 2: Document catalog revision and source_hash
- [ ] #TBD — Story 3: Ingestion QC metrics output
- [ ] #TBD — Story 4: Retrieval caching

## Success Criteria
1. Ingestion throughput >= 200 pages/minute on baseline hardware
2. Median answer latency <= 5 seconds for single-manual queries
3. All catalog entries include revision and source_hash
4. QC status (pass/warn/fail) emitted per ingestion run

## Acceptance Criteria
- [ ] IngestDocumentOutput includes pages_per_minute (float)
- [ ] IngestDocumentOutput includes text_coverage, ocr_coverage, table_yield, qc_status
- [ ] DocumentCatalogRecord has revision, source_hash, tags, contract_version fields
- [ ] YAML catalog adapter loads and persists new fields
- [ ] Retrieval cache hit avoids redundant keyword+vector search
- [ ] validate_data_contracts.py validates qc_status values (pass/warn/fail)

## Non-Goals
- No graph store (Phase 4)
- No full PostgreSQL migration (filesystem adapter sufficient for MVP)
- No connector entity extraction (Phase 4)

## Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Cache invalidation race conditions | Medium | Simple TTL + doc-scoped keys |
| QC threshold calibration | Low | Thresholds in QUALITY_GATES.md; configurable |

## Timeline
- Start: Week 4 (after Phase 1-2 stable)
- Target completion: End of Week 5
```

---

### Phase 3 DoR Checklist

- [ ] Issue body contains `Success Criteria`
- [ ] Issue body contains `Non-Goals`
- [ ] Issue body contains `Acceptance Criteria`
- [ ] `Parent: #5` linked
- [ ] Phase 1 and 2 acceptance criteria verified
- [ ] DATA_CONTRACTS.md §8 (QC) reviewed

### Phase 3 DoD Checklist (for each PR)

- [ ] `Evidence Mapping` table: criterion → test → location → status
- [ ] `Tests` section: performance tests, integration tests listed
- [ ] `Documentation` section: OPERATIONS.md and DATA_CONTRACTS.md updated

---

---

## Phase 4 — Advanced Connectivity (Deferred)

**GitHub Issue:** #6  
**Status:** BLOCKED — entity schema not yet designed  
**Labels:** `type:epic`, `state:idea`, `priority:low`  

### Blocker Resolution Required

Before Phase 4 can be `state:approved`:

- [ ] Connector/pin/signal entity schema designed (ADR-006 required)
- [ ] Multi-hop query planner design reviewed by architect
- [ ] Graph store technology selected (Neo4j vs adjacency table)
- [ ] Phase 1-3 complete and stable

### Epic Issue Body (copy to #6 when unblocked)

```
# 🎯 Epic: Phase 4 — Advanced Connectivity

Parent: #6

## Overview
Define and implement connector/pin entity extraction from diagrams and tables,
with an optional graph store for multi-hop reasoning queries.

## Success Criteria
1. Diagram-related pass rate >= 80%
2. Multi-hop pinout queries answered with correct citations
3. Graph store implemented behind USE_GRAPH_STORE feature flag

## Acceptance Criteria
- [ ] Connector/pin/signal entity schema defined and documented in ADR-006
- [ ] Entity extraction runs during ingestion for diagram-heavy PDFs
- [ ] Graph adapter implemented behind feature flag (default: off)
- [ ] Multi-hop query resolves connector A → signal B → destination C with citations

## Non-Goals
- No changes to text or table chunk pipeline
- No mandatory graph store (always optional)

## Architecture Notes
### Components Affected
- TBD pending entity schema design

### Technical Approach
- TBD pending ADR-006
```

---

---

## Workflow Compliance Summary

### Workflow 12 — Epic/Story Tracking
Each phase issue must have:
- [ ] Label `type:epic`
- [ ] `Parent: #<id>` line in body
- [ ] Story list with `- [ ] #<id> — Description` format

Each story issue must have:
- [ ] Label `type:story`
- [ ] `Parent: #<epic-id>` line in body

### Workflow 13 — Definition of Ready
Each issue body must contain ALL of:
- [ ] `## Success Criteria` (or `Success Criteria` anywhere in body)
- [ ] `## Non-Goals` (or `Non-Goals` anywhere in body)
- [ ] `## Acceptance Criteria` or `# Acceptance Criteria`

### Workflow 14 — Definition of Done
Each PR body must contain ALL of:
- [ ] `Evidence Mapping` (table mapping criteria to tests)
- [ ] `Tests` (explicit mention of test additions/results)
- [ ] `Documentation` (confirmation of doc updates)

> The PR template at `.github/pull_request_template.md` already satisfies these.
> Do NOT delete the Evidence Mapping table or Documentation section from PRs.

---

## Issue Status Tracker

| Issue | Title | Type | DoR Ready | Branch |
|-------|-------|------|-----------|--------|
| #3 | Phase 1: Table and Diagram Fidelity | epic | ❌ needs Success Criteria, Non-Goals | feature/3-... |
| #4 | Phase 2: Retrieval Reliability | epic | ❌ needs Success Criteria, Non-Goals | feature/4-... |
| #5 | Phase 3: Industrial Scale | epic | ❌ needs Success Criteria, Non-Goals | feature/5-... |
| #6 | Phase 4: Advanced Connectivity | epic | ❌ blocked, state:idea | – |

---

## Next Actions

1. ✅ This plan created
2. ⏳ Update GitHub issues #3, #4, #5 body text to include Success Criteria and Non-Goals
3. ⏳ Update ISSUE_TEMPLATE files to always include required DoR sections
4. ⏳ Create story-level child issues for Phase 1 (Stories 1-4 above)
5. ⏳ Start Phase 1 Story 1 implementation
