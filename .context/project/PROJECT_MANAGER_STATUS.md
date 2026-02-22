# AI Manuals Project Manager Status Report
**Date:** February 22, 2026  
**Report Type:** Issue Audit + Implementation Planning  
**Author:** Copilot Agent (PM Mode)

---

## 1. ISSUE STATUS AUDIT

### Summary
| Total Open | state:ready | state:in-progress | state:idea | state:approved |
|-----------|------------|------------------|-----------|---|
| 6 | 4 | 1 | 1 | 0 |

### Issue Breakdown

#### ✅ READY FOR IMPLEMENTATION (4 issues)

| # | Title | Type | Priority | Milestone | Parent |
|---|-------|------|----------|-----------|--------|
| **3** | Phase 1: Table and Diagram Fidelity | story | high | Phase 1 | #11 |
| **4** | Phase 2: Retrieval Reliability | story | high | Phase 2 | #11 |
| **5** | Phase 3: Industrial Scale | story | medium | Phase 3 | #11 |
| **12** | Expose Retrieval as MCP Server Tool | story | medium | Phase 5 | #11 |

**Status:** All have DoR (Success Criteria, Acceptance Criteria, Non-Goals) + DoD (Test Strategy, Evidence Mapping, Full Spec)

---

#### 🔄 IN PROGRESS (1 issue)

| # | Title | Type | Priority | Milestone | Notes |
|---|-------|------|----------|-----------|-------|
| **11** | AI Manuals Q1 2026 — Engineering Programme | epic | high | *None* | Root programme epic; no milestone needed |

**Status:** Tracking all phase stories; all children linked via `Parent: #11`

---

#### ⏸️ BLOCKED / DEFERRED (1 issue)

| # | Title | Type | Priority | Milestone | Blocker | Target |
|---|-------|------|----------|-----------|---------|--------|
| **6** | Phase 4: Advanced Connectivity (Future) | story | low | Phase 4 | ADR-006 (entity schema design) | Q2 2026 |

**Status:** Waiting for approval of entity schema (connector/pin/signal design) before moving to `state:approved`

---

### Label Health Check

**State Label Violations:**  
✅ All issues have exactly ONE state label (No violations detected)

**Type Label Status:**  
✅ All issues properly typed (5× `type:story`, 1× `type:epic`)

**Missing Labels:**  
⚠️ None critical; all required governance labels present

**Milestone Status:**  
⚠️ #11 (programme epic) missing milestone assignment (optional—root issue)  
✅ #3, #4, #5, #6 all have phase milestones  
✅ #12 assigned to Phase 5

---

## 2. IMPLEMENTATION PLAN

### Phase Delivery Sequence

```
DEPENDENCY GRAPH:
│
├─ Phase 1: Table & Diagram Fidelity    [#3] ──────────────┐
│  └─ Row-level table chunks            Ready             │
│  └─ Figure bbox normalization          Ready             ├──> Phase 2+3 can parallelize
│  └─ Visual artifact metadata           Ready             │
│                                                          │
├─ Phase 2: Retrieval Reliability       [#4] ─────────────┤
│  └─ Procedure intent detection         Ready             │ (Depends on Phase 1)
│  └─ Coverage scoring (float 0..1)      Ready             │
│  └─ Modality diversity post-rerank     Ready             │
│  └─ Abstain enforcement (cov < 0.50)   Ready             │
│                                                          │
├─ Phase 3: Industrial Scale            [#5] ─────────────┤
│  └─ QC metrics (0.60/0.50 gates)       Ready             │ (Parallel with Phase 2)
│  └─ Catalog versioning & tags          Ready             │
│  └─ Cache with invalidation rules      Ready             │
│  └─ YAML-only adapter (scope)          Ready             │
│                                                          │
├─ Phase 5: MCP Server                 [#12] ─────────────┘
│  └─ Stdio/SSE transport options        Ready
│  └─ 3 tools: search, answer, list      Ready
│  └─ Claude Desktop integration         Ready
│  └─ Zero domain changes (hex arch)     Ready
│  └─ Depends on: Phase 1, 2 stable
│
└─ Phase 4: Advanced Connectivity       [#6]  🔴 BLOCKED
   └─ Requires ADR-006 approval (entity schema)
   └─ Target: Q2 2026 (after Phase 1-3 complete)
   └─ Graph store decision (Neo4j vs adjacency table)
```

---

### Implementation Roadmap (Q1 2026)

#### Week 1-3: Phase 1 — Table & Diagram Fidelity
**Owner:** Feature branch `feature/3-table-diagram-fidelity`  
**PR Target:** Merge to develop → main  
**Success Gate:** Golden eval table recall-at-5 >= 0.80

**Deliverables:**
- ✅ ExtractedTableRow dataclass with headers/units metadata
- ✅ Row-level chunk emission (one chunk per table row)
- ✅ PyMuPDF bbox extraction (normalized to [0,1])
- ✅ Figure region detection with figure_id
- ✅ Unit tests: `test_table_extractor_adapter.py`, `test_visual_artifact_bbox.py`
- ✅ Integration tests: siemens_g120 golden eval
- ✅ Data contract validation passing

**Dependencies:** None (non-blocking start)

---

#### Week 2-4: Phase 2 — Retrieval Reliability (parallel or sequential)
**Owner:** Feature branch `feature/4-retrieval-reliability`  
**PR Target:** Merge to develop → main  
**Success Gate:** Golden eval pass rate >= 85%

**Deliverables:**
- ✅ PROCEDURE_TERMS classification for evidence filtering
- ✅ `_compute_evidence_coverage()` in policies.py
- ✅ `has_sufficient_evidence(coverage: float) -> bool` enforcement
- ✅ `modality_hit_counts` in retrieval output
- ✅ Post-rerank modality diversity (stable promotion algorithm)
- ✅ Abstain when coverage < 0.50
- ✅ Unit tests: `test_procedure_intent.py`, `test_confidence_.*` (4 callers)
- ✅ Integration tests: full pipeline golden eval
- ✅ Evidence mapping for 8 acceptance criteria

**Dependencies:** Phase 1 stable; can run in parallel once Phase 1 fixtures available

---

#### Week 3-5: Phase 3 — Industrial Scale (parallel with Phase 2)
**Owner:** Feature branch `feature/5-industrial-scale`  
**PR Target:** Merge to develop → main  
**Success Gate:** Ingestion QC metrics emitted per run

**Deliverables:**
- ✅ QC metric gates: 0.60 (yellow), 0.50 (red) thresholds
- ✅ `total_pages` field in IngestDocumentOutput
- ✅ `tags` parameter for table-heavy gating (adaptive downgrade)
- ✅ Cache adapter with invalidation on doc_id/version change
- ✅ Catalog versioning (increment on reingestion)
- ✅ YAML-only storage adapter (scope: config layer only)
- ✅ Unit tests: `test_qc_metrics.py`, `test_catalog_versioning.py`
- ✅ Integration tests: full-scale benchmark (1000+ pages)
- ✅ Contract validation: QC metric records, cache miss rates

**Dependencies:** Phase 1 stable; Phase 2 recommended but not blocking

---

#### Week 5-6: Phase 5 — MCP Server (after Phase 1-2 stable)
**Owner:** Feature branch `feature/12-mcp-server`  
**PR Target:** Merge to develop → main  
**Success Gate:** Tools visible and usable in Claude Desktop

**Deliverables:**
- ✅ `apps/mcp/server.py` (~100 lines, zero domain changes)
- ✅ 3 tools: `search_manuals`, `answer_question`, `list_manuals`
- ✅ Stdio transport (local mode for Claude Desktop)
- ✅ SSE transport option (hosted mode)
- ✅ `claude_desktop_config.json` snippet in docs
- ✅ Unit tests: `test_mcp_tool_contracts.py`, `test_mcp_*_tool.py`
- ✅ Integration tests: stdio round-trip
- ✅ Evidence mapping: 5 acceptance criteria

**Dependencies:** Phase 1 & 2 merged and stable

---

#### Q2 2026: Phase 4 — Advanced Connectivity (Deferred)
**Blocker:** ADR-006 (entity schema design) approval required  
**Owner:** TBD (pending ADR resolution)  
**Target:** Week 1-4 Q2 2026, IF ADR-006 approved in Q1

**Scope (TBD pending ADR):**
- Connector/pin/signal entity extraction
- Graph store adapter (Neo4j vs adjacency table TBD)
- Multi-hop reasoning queries
- Feature flag: `USE_GRAPH_STORE` (default off)

**Status:** `state:idea` (not `state:approved` until ADR approved)

---

## 3. RISK & MITIGATION MATRIX

| Phase | Risk | Impact | Mitigation |
|-------|------|--------|-----------|
| **1** | PyMuPDF layout API differences | Medium | Fallback to page-level OCR; golden gates catch regressions |
| **1** | Table heuristic fails on unusual layouts | Medium | Golden test gates; manual annotation for edge cases |
| **1** | Document re-ingestion required | High | Plan re-ingestion window; notify users; phase-in new chunks |
| **2** | Procedure term coverage scoring complexity | Medium | Start conservative (threshold 0.70); tune downward per golden |
| **2** | Modality diversity post-rerank stability | Medium | Test on diverse doc sets; A/B test old vs new reranker |
| **3** | QC threshold tuning (0.60/0.50 too aggressive) | Medium | Start at 0.70/0.60; tune downward; monitor ingestion metrics |
| **3** | Cache invalidation false positives | Low | Validate cache miss rates in test suite | **5** | MCP SDK API instability (early ecosystem) | Medium | Pin exact version in `requirements.txt`; CI test against pinned version |
| **5** | Stdio process lifecycle edge cases | Low | Stateless handlers; no persistent state; client manages lifecycle |
| **4 (BLOCKED)** | ADR-006 scope creep delays approval | High | Scope ADR narrowly: only schema; defer graph tech to implementation |

---

## 4. RESOURCE & TIMELINE PROJECTION

### Estimated Effort (Developer Weeks)

| Phase | Impl | Tests | Review | Total | Parallel? |
|-------|------|-------|--------|-------|-----------|
| **1** | 2.5 | 1.5 | 0.5 | **4.5** | — (blocks 2,3,5) |
| **2** | 2.0 | 1.5 | 0.5 | **4.0** | ✅ After Phase 1 starts |
| **3** | 2.0 | 1.5 | 0.5 | **4.0** | ✅ After Phase 1 starts |
| **5** | 1.0 | 1.0 | 0.5 | **2.5** | After Phases 1+2 merge |
| **4** | TBD | TBD | TBD | **TBD** | ⏸️ Q2 2026 (blocked) |

**Total Q1 2026:** ~15 dev-weeks (non-parallel), ~8 weeks (3-way parallel)  
**Recommended Schedule:** 6 weeks (Feb 22 - Apr 4, serial then parallel)

### Branch Ownership
- **Phase 1 (#3):** `feature/3-table-diagram-fidelity` ← base: develop
- **Phase 2 (#4):** `feature/4-retrieval-reliability` ← base: develop (after #3 merged)
- **Phase 3 (#5):** `feature/5-industrial-scale` ← base: develop (after #3 merged)
- **Phase 5 (#12):** `feature/12-mcp-server` ← base: develop (after #4 merged)
- **Phase 4 (#6):** `feature/6-advanced-connectivity` ← base: develop (blocked until Q2 + ADR-006)

---

## 5. CRITICAL PATH GATES

### PR Merge Gates (Enforced by WF-14 DoD)

For any Phase PR to merge:

✅ **All acceptance criteria tests passing**  
✅ **Evidence mapping table populated** (criterion → test file → method → expected result)  
✅ **Code review from CODEOWNER + 1 peer**  
✅ **Coverage >= 80% on new code**  
✅ **Golden evaluation gate met** (phase-specific pass rate)  
✅ **Data contracts validated** (schema, metadata fields)  
✅ **No debug code (print/logging.debug) committed**  

### State Transitions (WF-01)

```
state:ready [#3,#4,#5,#12]
    ↓
(developer picks up)
    ↓
state:in-progress
    ↓
(push branch, open PR)
    ↓
state:in-review
    ↓
(CODEOWNER approves, CI green, evidence mapping verified)
    ↓
MERGE to develop
    ↓
(QA gates pass, all phases stable)
    ↓
MERGE to main → state:done
```

---

## 6. NEXT ACTIONS (This Week)

### Immediate (Today)
- [ ] Confirm Phase 5 milestone created and #12 assigned
- [ ] Add #12 to sprint backlog (assigned to: TBD dev)
- [ ] Slack notification: phases #3-#12 ready for implementation pickup

### This Week
- [ ] **Dev assigned to #3:** Create `feature/3-table-diagram-fidelity` branch from develop
- [ ] **Dev assigned to #4:** Prepare local test fixtures for Phase 2 (depends on Phase 1 output)
- [ ] **Devops:** Ensure docker-compose setup stable for CI/CD pipeline

### Next Sprint
- [ ] Monitor Phase 1 PR; unblock Phase 2/3 branches when #3 merged
- [ ] Weekly standups: phase lead reports blockers, test status, timeline confidence
- [ ] Golden evaluation tracking: table recall-at-5, coverage scoring accuracy, QC metric correctness

---

## 7. STAKEHOLDER COMMUNICATION

### For Engineering Leads
- **Phase 1:** High priority; unblocks subsequent phases. Start now.
- **Phase 2 & 3:** Can parallelize after Phase 1 ships; prepare fixtures in parallel.
- **Phase 5 (MCP):** Medium priority; valuable for external tool integration; no core changes.
- **Phase 4 (ADR-006):** Deferred to Q2 2026; unblock by finalizing entity schema design.

### For Product/PM
- **Go-live target:** Phase 1 + 2 by end of March 2026 (golden eval pass rate >= 85%)
- **Phase 3 (scale):** Early April optional; main value in production observability
- **Phase 5 (MCP):** Late April; enables Claude Desktop + IDE integrations
- **Phase 4 (connectivity):** Q2 2026 pending architecture review

### For QA/Testing
- **Phase 1 gate:** siemens_g120 golden eval table recall-at-5 >= 0.80
- **Phase 2 gate:** overall golden eval >= 85% pass rate
- **Phase 3 gate:** QC metrics emitted and validated per ingestion run
- **Phase 5 gate:** Manual test—Claude Desktop tools visible and functional

---

## 8. DOCUMENT INVENTORY

| Document | Location | Status | Next Review |
|----------|----------|--------|-------------|
| IMPLEMENTATION_PLAN_PHASES.md | `.context/sprint/IMPLEMENTATION_PLAN_PHASES.md` | ✅ Complete (4 phases, all specs) | After Phase 1 merge |
| ARCHITECTURE.md | `.context/project/ARCHITECTURE.md` | ✅ Current (hexagonal overview) | Q2 2026 (Phase 4) |
| CODEX_HANDOVER.md | `.context/project/CODEX_HANDOVER.md` | ✅ Current | Quarterly review |
| Q1_2026_SPRINT_PLAN.md | `.context/sprint/Q1_2026_SPRINT_PLAN.md` | ✅ Current | After each phase merge |
| **PROJECT_MANAGER_STATUS.md** | `.context/project/PROJECT_MANAGER_STATUS.md` | ✅ **NEW (this doc)** | Weekly updates |

---

## 9. SUMMARY TABLE

| Issue | Title | State | Type | Priority | Est. Effort | Timeline | Status |
|-------|-------|-------|------|----------|------------|----------|--------|
| #3 | Table & Diagram Fidelity | ready | story | HIGH | 4.5 wks | Week 1-3 | 🟢 Ready to start |
| #4 | Retrieval Reliability | ready | story | HIGH | 4.0 wks | Week 2-4 | 🟡 Start after #3 |
| #5 | Industrial Scale | ready | story | MEDIUM | 4.0 wks | Week 2-4 | 🟡 Parallel with #4 |
| #12 | MCP Server | ready | story | MEDIUM | 2.5 wks | Week 5-6 | 🟡 After #3+#4 merge |
| #11 | Programme Epic | in-progress | epic | HIGH | — | — | 🟢 Tracking all phases |
| #6 | Advanced Connectivity | idea | story | LOW | TBD | Q2 2026 | 🔴 Blocked (ADR-006) |

---

**Report Generated:** February 22, 2026 · 10:45 AM  
**Next Update:** After Phase 1 branch created (EOW Feb 29)  
**Prepared by:** Copilot PM Agent (Framework Role: Project Manager)
