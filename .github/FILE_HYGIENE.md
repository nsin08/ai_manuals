# File Hygiene Guide

## Overview

This project follows **Rule 11 (File Organization)** from the space_framework. All files in this repository are classified into two categories based on their lifecycle and audience.

---

## Classification: Committed vs. Git-Ignored

### 🔵 Committed Files (Track in Git)

These files are **essential for project understanding** and should be tracked in version control.

#### `.context/project/` — Project-Wide Documentation
- **Purpose:** Durable, long-term documentation shared across all contributors
- **Lifecycle:** Added once, updated infrequently
- **Audience:** Entire team, future contributors
- **Examples:**
  - `CODEX_HANDOVER.md` — Complete MVP requirements and architecture
  - `ARCHITECTURE.md` — System design decisions
  - `ADR/` — Architecture Decision Records (one file per decision)
  - `RUNBOOKS.md` — Operational procedures
  - Meeting notes (aggregated quarterly or as major milestones)

**When to add files:**
- Decisions that affect the entire project
- Architectural changes (should also create ADR)
- Long-term operational procedures
- Team agreements (coding standards, deployment processes)

---

#### `.context/sprint/` — Sprint Planning & Retrospectives
- **Purpose:** Sprint-specific planning artifacts and retrospective analysis
- **Lifecycle:** Created at sprint start, finalized at sprint end, kept for historical reference
- **Audience:** Entire team
- **Structure:**
  ```
  .context/sprint/
  ├── README.md                    # Sprint cadence and structure
  ├── sprint-01/
  │   ├── plan.md                  # Sprint goals, story breakdown, capacity
  │   ├── retro.md                 # Retrospective notes
  │   └── metrics.md               # Burndown, velocity, lead time
  ├── sprint-02/
  └── ...
  ```

**When to add files:**
- Start of each sprint: `sprint-NN/plan.md`
- End of sprint: `sprint-NN/retro.md` and `sprint-NN/metrics.md`
- Historical reference: Archive old sprints in year directories if needed

---

### 🔴 Git-Ignored Files (NOT Tracked)

These files are **local, temporary, or environment-specific** and should NOT be committed.

#### `.context/temp/` — Agent Drafts & Scratch Work
- **Purpose:** Temporary working space for AI agents and developers during exploration
- **Lifecycle:** Created during work, deleted after findings are consolidated
- **Audience:** Individual contributor or AI agent
- **Examples:**
  - Draft design documents before finalizing in `project/`
  - Research notes and investigation logs
  - Local data files and test outputs
  - Temporary scripts and debugging logs

**Usage:**
- Exploratory work goes here first
- Once findings are validated, promote durable content to `.context/project/` or `.context/sprint/`
- Safe to delete without affecting the project

**Example workflow:**
```
1. Agent explores: `.context/temp/research-notes.md`
2. Findings proven: Create `.context/project/ADR/0005-new-approach.md`
3. Delete temp file (optional, but recommended)
```

---

#### `.context/issues/` — Issue-Specific Workspaces
- **Purpose:** Isolated workspace for investigating and resolving individual GitHub issues
- **Lifecycle:** Created when starting work on an issue, cleaned up after PR is merged
- **Audience:** Individual contributor or AI agent working on that issue
- **Structure:**
  ```
  .context/issues/
  ├── ai_manuals-42-pdf-ingestion__gh/
  │   ├── investigation.md
  │   ├── analysis.md
  │   └── solution-sketch.md
  ├── ai_manuals-99-ocr-timeout__gh/
  └── ...
  ```

**Naming Convention:**
- Format: `<repo>-<issue-id>-<slug>__gh/`
- Example: `ai_manuals-42-pdf-ingestion__gh/`
- Suffix `__gh/` indicates GitHub-based issue

**Usage:**
- Create folder when starting work on the issue
- Organize investigation notes, prototypes, and solution sketches inside
- Link findings back to the PR or issue comments
- Safe to delete after PR is closed/merged

---

#### `.context/reports/` — Generated Reports & Outputs
- **Purpose:** Automated or manual reports that are generated from project data
- **Lifecycle:** Generated on-demand, regenerated as needed, never manually edited for long-term storage
- **Audience:** Specific context (metrics review, security audit, etc.)
- **Examples:**
  - Code quality reports (coverage, complexity)
  - Security audit results
  - Performance benchmarks
  - CI/CD logs and build artifacts
  - Generated API documentation
  - Test result summaries

**Usage:**
- Do NOT manually edit reports for long-term storage
- Regenerate via tooling when needed
- Reference in sprint retrospectives or project analysis
- Safe to delete and regenerate without data loss

---

## Workflow Examples

### Example 1: Architecture Decision

**Scenario:** You need to decide between PostgreSQL and MongoDB for the vector store.

1. **Explore** in `.context/temp/`:
   ```
   .context/temp/db-comparison.md
   ```
   - List pros/cons
   - Draft trade-off analysis
   - Share for feedback

2. **Validate** with team feedback, then **promote**:
   ```
   .context/project/ADR/0003-postgresql-pgvector-selection.md
   ```
   - Final decision documented
   - Committed to repository
   - Permanent reference

3. **Cleanup**:
   - Delete `.context/temp/db-comparison.md`
   - Keep ADR in `.context/project/ADR/`

---

### Example 2: Issue Investigation

**Scenario:** You're assigned to fix OCR timeout issues (#99).

1. **Start work**, create workspace:
   ```
   .context/issues/ai_manuals-99-ocr-timeout__gh/
   ```

2. **Investigate and document**:
   ```
   .context/issues/ai_manuals-99-ocr-timeout__gh/investigation.md
   - Test results from different PDF sizes
   - PaddleOCR performance profiling
   - Timeout threshold findings
   ```

3. **Implement fix** in `packages/adapters/ocr/`, link PR to investigation

4. **After PR merged**, cleanup:
   - Delete `.context/issues/ai_manuals-99-ocr-timeout__gh/`
   - Keep PR comments/links as historical record

---

### Example 3: Sprint Planning

**Scenario:** Sprint 5 kicks off with 3 stories.

1. **Create sprint artifacts**:
   ```
   .context/sprint/sprint-05/plan.md
   - Goals: OCR module, API hardening, docs
   - Stories: #100, #101, #102
   - Capacity: 30 story points
   ```

2. **During sprint**: Update as needed for mid-sprint adjustments

3. **Sprint end**, finalize:
   ```
   .context/sprint/sprint-05/retro.md
   - What went well
   - What didn't
   - Improvements for sprint-06
   
   .context/sprint/sprint-05/metrics.md
   - Velocity: 28 points
   - Lead time average: 4.2 days
   - Bug escape rate: 0%
   ```

4. **Keep in repository** — these become historical reference

---

## Git Configuration

Ensure `.gitignore` includes Rule 11 ignores:

```gitignore
# Context: Local-only temp, issue workspaces, and reports (Rule 11)
.context/temp/
.context/issues/
.context/reports/

# Python, Docker, IDE
__pycache__/
*.py[cod]
venv/
.env
.vscode/
.idea/
```

---

## Quick Reference: Where Should This Go?

| Content | Location | Committed? |
|---------|----------|-----------|
| MVP requirements | `.context/project/CODEX_HANDOVER.md` | ✅ Yes |
| Architecture decision | `.context/project/ADR/` | ✅ Yes |
| Operational runbook | `.context/project/RUNBOOKS.md` | ✅ Yes |
| Sprint 5 plan | `.context/sprint/sprint-05/plan.md` | ✅ Yes |
| Sprint 5 retro | `.context/sprint/sprint-05/retro.md` | ✅ Yes |
| Design brainstorm (early stage) | `.context/temp/` | ❌ No |
| Issue #99 investigation | `.context/issues/ai_manuals-99-*/` | ❌ No |
| Test coverage report | `.context/reports/` | ❌ No |
| Generated API docs | `.context/reports/` | ❌ No |

---

## Enforcement

This hygiene policy is enforced by:

1. **Pre-commit hooks** (future): Block commits of files in git-ignored directories
2. **CI/CD validation** (future): Verify no reports or temp files committed
3. **Manual review** in PRs: Reviewer checks for policy violations
4. **Agent guidelines** in `.github/copilot-instructions.md`: AI agents follow Rule 11 by default

---

## Summary

- **Keep in Git:** Project decisions (ADRs), sprint artifacts (plans, retros), durable documentation
- **Ignore in Git:** Drafts, investigations, generated reports, local environment files
- **Goal:** Clean repository that captures team knowledge without noise from temporary work

For more details, see `space_framework` [Rule 11: File Organization](https://github.com/nsin08/space_framework/blob/main/20-rules/11-file-organization.md).
