# Q1 2026 Sprint Plan: Phases 1-4 Implementation

**Version:** 1.0  
**Date:** 2026-02-21  
**Status:** In Planning  
**Tracking Branch:** `chore/2026-q1-sprint-phases-1-4`

---

## Overview

Multi-phase delivery of table/diagram fidelity, retrieval reliability, industrial scaling, and advanced connectivity for the Equipment Manuals Chatbot.

**Success Definition:** All Phase 1-3 acceptance criteria met; Phase 4 design finalized or deferred.

---

## Phase 1: Table and Diagram Fidelity — **HIGH PRIORITY**

**GitHub Issue:** #3  
**Target Duration:** 3 weeks  
**Branch Pattern:** `feature/3-table-diagram-fidelity`  
**PR Target:** `develop`

### Acceptance Criteria
- ✅ Golden table questions >= 80% pass rate
- ✅ Table recall-at-5 >= 0.80
- ✅ All table_row chunks have headers, row_index, units metadata
- ✅ All figures have figure_id and bbox coordinates

### Stories (in order)
1. **Update TableExtractorPort contract** (1-2 days)
   - Change return type to structured rows with headers
   - Add row_index, units, headers fields

2. **Implement table_row chunk emission** (3-4 days)
   - Update `_process_single_page()` in ingest_document.py
   - Emit one table_row chunk per table row, not per table
   - Preserve table_id, figure_id linking

3. **Region-based OCR and bbox** (4-5 days)
   - Add `PyMuPDF` bbox extraction from page layout
   - OCR figures with region coordinates
   - Generate visual artifacts with bbox

4. **Contract validation** (1-2 days)
   - Add tests for table_row contract in `validate_data_contracts.py`
   - Test figure artifact generation

### Dependencies
- `ExtractedTable` dataclass compatible with header extraction
- `SimpleTableExtractorAdapter` enhanced or replaced
- PDF layout engine (PyMuPDF already in stack)

### Risks
- Table extraction heuristics may not work for all manual types
- OCR region accuracy depends on PDF layout structure
- Mitigation: Golden evaluation gates catch regressions early

---

## Phase 2: Retrieval Reliability — **HIGH PRIORITY** (depends on Phase 1)

**GitHub Issue:** #4  
**Target Duration:** 2-3 weeks  
**Branch Pattern:** `feature/4-retrieval-reliability`  
**PR Target:** `develop`

### Acceptance Criteria
- ✅ Golden overall pass rate >= 85%
- ✅ Incorrect answers reduced by 50% on previous failures
- ✅ Evidence coverage threshold enforced at 0.50
- ✅ Procedure intent recall-at-5 >= 0.75
- ✅ Modality diversity: ≥2 modalities in top-5 per intent

### Stories (in order)
1. **Add procedure intent detection** (1-2 days)
   - Extend `_detect_intent()` in search_evidence.py
   - Add keywords: "step", "procedure", "instruction", "how to"

2. **Compute numeric coverage score** (2-3 days)
   - Implement `_compute_evidence_coverage(query, hits)` 
   - Use token overlap, modality diversity, chunk relevance
   - Return 0.0–1.0 score

3. **Enforce abstain at 0.50** (1-2 days)
   - Update answer_question.py to check coverage < 0.50
   - Set abstain=True, answer_text to placeholder
   - Test against golden questions

4. **Add modality_hit_counts to traces** (1-2 days)
   - Update retrieval trace logger
   - Populate {text, table, figure, visual} counts
   - Validate in `validate_data_contracts.py`

5. **Enforce modality diversity** (1-2 days)
   - Add diversity check in reranker pool
   - Ensure top-5 includes ≥2 modalities when multimodal
   - Document weighting strategy

### Dependencies
- Phase 1 table_row chunks available
- Reranker already integrated; weights may need tuning

### Risks
- Coverage score model brittleness (query domain-specific)
- Modality diversity may conflict with relevance ranking
- Mitigation: Tuning parameters tracked in OPERATIONS.md

---

## Phase 3: Industrial Scale — **MEDIUM PRIORITY** (depends on Phase 1-2)

**GitHub Issue:** #5  
**Target Duration:** 2 weeks  
**Branch Pattern:** `feature/5-industrial-scale`  
**PR Target:** `develop`

### Acceptance Criteria
- ✅ Ingestion >= 200 pages/min on baseline hardware
- ✅ Median answer latency <= 5 seconds
- ✅ All catalog entries include revision, source_hash
- ✅ QC metrics (text_coverage, ocr_coverage, table_yield) recorded

### Stories (in order)
1. **Add ingestion timing metrics** (1-2 days)
   - Instrument IngestDocumentOutput with timing
   - Log pages/second in ingestion traces
   - Validate against 200 ppm baseline

2. **Extend document catalog** (1-2 days)
   - Add revision, source_hash, tags, contract_version
   - Update YAML adapter to load/persist
   - Backfill existing catalog entries

3. **Implement retrieval cache** (2-3 days)
   - Add cache layer in search_evidence_use_case
   - Key: (doc_id, query) scope
   - TTL and size limits configurable

4. **Add QC metrics output** (1-2 days)
   - Compute text_coverage, ocr_coverage, table_yield
   - Store in IngestDocumentOutput
   - Match DATA_CONTRACTS.md §8 spec

### Dependencies
- Phase 1-2 complete and stable
- Redis (already in stack) for cache backend

### Risks
- Cache invalidation on catalog updates
- QC metrics accuracy depends on ingestion completeness
- Mitigation: Metrics gated independently; cache can be disabled

---

## Phase 4: Advanced Connectivity — **LOW PRIORITY, DEFERRED**

**GitHub Issue:** #6  
**Status:** Design phase — entity schema not yet defined  
**Target:** Q2 2026 or later (if Phase 1-3 ship first)

### Blockers
- ❌ Connector/pin/signal entity schema undefined (open question in PRODUCT_SPEC §10)
- ❌ No engineering review on graph store performance impact  
- ❌ Scope may be too large for Phase 4 MVP

### Recommendation
- Complete Phase 1-3 first (3-4 weeks total)
- Defer graph store to Phase 4 or future quarter
- Document entity schema design as separate ADR

---

## Sprint Timeline

| Phase | Weeks | Start | End | Blocker |
|-------|-------|-------|-----|---------|
| 1 | 3 | Week 1 | Week 3 | – |
| 2 | 3 | Week 2* | Week 4 | Phase 1 complete |
| 3 | 2 | Week 4 | Week 5 | Phase 1-2 complete |
| 4 | TBD | Q2 | Q2 | Schema design |

*Phase 2 starts during Phase 1 (parallel work on different stories)

**Total MVP Target:** 5-6 weeks (Phases 1-3 only)

---

## Definition of Ready (per Framework Rule 03)

Each phase issue must have:
- ✅ Acceptance criteria linked to DATA_CONTRACTS.md
- ✅ Story breakdown with estimated effort
- ✅ Interface/port changes clearly documented
- ✅ Migration notes (if breaking changes)
- ✅ Blocked-by relationships to other phases

---

## Definition of Done (per Framework Rule 03)

Each story/PR must include:
- ✅ Unit tests for business logic (>80% coverage)
- ✅ Integration tests for end-to-end flows
- ✅ Golden evaluation pass rate meets/exceeds criterion
- ✅ Retrieval traces logged with all fields present
- ✅ Documentation updated (ARCHITECTURE, OPERATIONS)
- ✅ No debug prints/logging.debug in committed code
- ✅ All contracts validated (validate_data_contracts.py passes)

---

## Quality Gates (per QUALITY_GATES.md)

### Per Phase
- **Phase 1:** Table pass >= 80%, recall >= 0.80
- **Phase 2:** Overall pass >= 85%, procedure recall >= 0.75
- **Phase 3:** QC metrics recorded, cache validation passing
- **Phase 4:** Graph queries validated (if implemented)

### Per Release (MVP)
- ✅ Regression tests pass on all phases
- ✅ Golden evaluation pass rate >= threshold
- ✅ No new warnings in QC metrics
- ✅ Ingestion throughput >= 200 ppm (Phase 3 gate)

---

## Rollout Strategy

1. **Phase 1:** 3-week development, internal testing
2. **Phase 2:** Parallel dev, then merge to develop once Phase 1 stable
3. **Phase 3:** Final integration and performance tuning
4. **Release:** All phases merged to main, tagged as v0.2.0

---

## Notes & Open Questions

- **Phase 4 graph store:** Deferred pending schema design. Document as ADR-006.
- **Chunking strategy:** 800-1200 chars per chunk (documented in ARCHITECTURE.md §4.1)
- **Embedding model:** Stable across all phases; no changes planned
- **Cache backend:** Redis (already running in docker-compose)

---

## Branch Protection & Merge Strategy

- All feature branches require 1 approval + CODEOWNER review (per framework Rule 06)
- PR description must reference issue (`Closes #N`)
- Evidence mapping table required (per Rule 04)
- Squash merge to develop; merge commit to main (per Rule 08)

---

## Next Steps

1. ✅ Create Phase 1-4 GitHub issues
2. ⏳ Start Phase 1 story 1 (TableExtractorPort update)
3. ⏳ Open PR for Phase 1 story 1 to develop
4. ⏳ Reference this sprint plan in each PR description

---

**Prepared by:** GitHub Copilot  
**Approved by:** @nsin08 (CODEOWNER)  
**Last Updated:** 2026-02-21
