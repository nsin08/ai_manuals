# Copilot Instructions: Equipment Manuals Chatbot

**Project:** Equipment Manuals Chatbot - Local-first AI chatbot for engineering documentation  
**Repository:** https://github.com/nsin08/ai_manuals  
**Framework:** space_framework (enforced governance)  
**Framework Repository:** https://github.com/nsin08/space_framework  
**Last Updated:** 2026-02-17

---

## 1. Load Framework Context (REQUIRED)

All agents must load framework rules first:

```
@space_framework Load: 10-roles/00-shared-context.md
```

This provides:
- Mandatory state machine (Idea → Approved → Ready → In Progress → In Review → Done → Released)
- AI agent boundaries (cannot merge, approve, or skip states)
- Enforced rules (DoR, DoD, artifact linking, approval gates)

---

## 1.1 Environment Awareness (Reduce Retries)

Agents MUST adapt to the user's environment and avoid guessing.

### Preflight (run once before GitHub/Git operations)

- Detect which shell you are in and output commands for that shell only.
- Confirm `git` exists (`git --version`).
- Confirm `gh` exists (`gh --version`).
- If you will create/update Issues/PRs/labels: confirm auth (`gh auth status`).
  - If not authenticated: STOP and ask the user to authenticate. Do not attempt alternate methods.

### GitHub tooling policy

- Prefer `gh` first for GitHub operations (issues/PRs/labels).
- Use GitHub MCP only if the user explicitly asks to use it (and only after checking it is available).
- Do not try multiple approaches for the same action; fail fast with the exact error and missing prerequisite.

### Branch safety

- Do not push directly to protected branches (`main`, `develop`, `release/*`) unless the user explicitly requests it.
- Use PR-based flow for merges; branch protection enforces policy server-side.

---

## 2. Project Identity

| Item | Value |
|------|-------|
| **Primary Language** | Python 3.11 |
| **Repository** | https://github.com/nsin08/ai_manuals |
| **CODEOWNER** | @nsin08 |
| **Tech Lead** | @nsin08 |
| **PM** | @nsin08 |

**Governance:**
- All work flows through the state machine (per Rule 01)
- Only CODEOWNER merges PRs (per Rule 06)

---

## 3. Quick Start: Setup & Development

### Clone and Install

```bash
git clone https://github.com/nsin08/ai_manuals
cd ai_manuals

# Set up Python environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Run Tests

```bash
pytest tests/
```

### Run Locally

```bash
# Start services
docker compose up -d

# Run the application
python -m apps.api.main
```

### Linting & Formatting

```bash
# Format code
black .
isort .

# Lint
pylint apps/ packages/
mypy apps/ packages/
```

---

## 4. Project Structure

```
/apps
  /api              # FastAPI application
  /ui               # Streamlit UI
/packages
  /domain           # Core domain entities
  /application      # Use cases
  /adapters         # Infrastructure adapters
  /ports            # Interface definitions
/infra
  docker-compose.yml
  /postgres
/data
  /assets           # PDF assets (bind mount)
/docs
  CODEX_HANDOVER.md
  ARCHITECTURE.md
  ADR/
/tests
  /unit
  /integration
.context/
  project/          # Project docs (architecture, ADRs, meetings) - committed
  sprint/           # Sprint artifacts (plans, retros) - committed
  temp/             # Agent scratch/drafts - git-ignored
  issues/           # Issue workspaces - git-ignored
  reports/          # Generated reports - git-ignored
```

---

## 5. File Organization Rules (Rule 11)

**Enforcement:** GitHub Actions (70-enforcement/17-file-organization.yml) - currently manual review

### Classification: Committed vs. Git-Ignored

| Category | Location | Committed? | What goes here |
|----------|----------|------------|----------------|
| **Temp (default for agent-created)** | `.context/temp/` | ❌ No (git-ignored) | Scratch work, one-offs, drafts, local logs |
| **Issue workspaces** | `.context/issues/{repo}-{issue}-{slug}__gh/` | ❌ No (git-ignored) | PR bodies, issue snapshots, per-issue notes/drafts |
| **Sprint** | `.context/sprint/` | ✅ Yes | Sprint plans, retros, sprint notes |
| **Project** | `.context/project/` | ✅ Yes | Architecture, ADRs, meeting notes, runbooks |
| **Reports** | `.context/reports/` | ❌ No (git-ignored) | Generated outputs (coverage, scans, metrics) |

### Required `.gitignore` entries

```gitignore
# Context: Local-only temp, issue workspaces, and reports (Rule 11)
.context/temp/
.context/issues/
.context/tasks-*/   # legacy (deprecated)
.context/reports/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
ENV/
env/

# Docker
.env

# IDE
.vscode/
.idea/
```

### File Placement Rules

**Tests:**
- ✅ All tests in `tests/` directory
- ❌ Tests outside `tests/`

**Temp/Debug scripts:**
- ✅ `.context/temp/debug_*.py`, `.context/issues/{...}__gh/check_*.py`
- ❌ `debug_*.py`, `check_*.py`, `temp_*.py` in project root

---

## 6. Code Standards

### Before Opening a PR

- [ ] Tests written for each acceptance criterion (per Rule 03 DoD)
- [ ] Tests passing locally
- [ ] Lint/format checks passing locally
- [ ] No debug statements committed (print/logging.debug)
- [ ] No secrets committed

### Branch Naming (Rule 07)

**Pattern:** `<type>/<issue-id>-<slug>`

**Types:** `feature/`, `fix/`, `docs/`, `chore/`, `refactor/`, `test/`, `perf/`

**Examples:**
- `feature/42-pdf-ingestion`
- `fix/99-ocr-timeout`
- `docs/55-architecture-decision`

### Commit Message Format (recommended)

**Pattern:** `<type>(<scope>): <subject>`

**Types:** feat, fix, docs, refactor, test, chore, perf

**Example:**
```
feat(ingestion): add PDF table extraction with Camelot

Closes #42
```

### PR Requirements (Rule 08 + Rule 04)

- Must link to a single Story/Issue: `Closes #<id>` or `Resolves #<id>`
- Must include evidence mapping (each acceptance criterion → test + location)
- Must be reviewable (avoid unrelated changes)

**Evidence Mapping Table (required in PR body):**

| Criterion | Test | Location | Status |
|-----------|------|----------|--------|
| [criterion] | [test name] | [path:line] | ✅/❌ |

---

## 7. Role-Based Entry Points

When assigned work, load your role context:

| I am a... | Load | Then |
|-----------|------|------|
| **Implementer** | `@space_framework 10-roles/05-implementer.md` | Implement Story in `state:ready` |
| **Reviewer** | `@space_framework 10-roles/06-reviewer.md` | Review PR against DoD + evidence |
| **DevOps** | `@space_framework 10-roles/07-devops.md` | Release/deploy per governance |
| **Architect** | `@space_framework 10-roles/04-architect.md` | Validate feasibility + design |

---

## 8. Hard Boundaries (Cannot Override)

You CANNOT:
- Merge PRs (CODEOWNER only)
- Approve PRs (human reviewers only)
- Skip workflow states
- Modify security-sensitive governance without approval (e.g., CODEOWNERS, CI/CD) per Rule 10
- Access secrets or credentials

You CAN:
- Implement within assigned Story scope
- Open PRs with evidence mapping
- Request reviews and respond to feedback
- Document discoveries per Rule 11

---

## 9. Essential Workflows

### Discovery Workflow (Agents)

**Draft first:** put exploratory notes in `.context/temp/` (git-ignored).  
**Promote later:** move stable, durable information into:
- `.context/project/` (architecture, ADRs, meetings, runbooks)
- `.context/sprint/` (sprint plans, retros)

### Starting Work on a Story

1. Story must be labeled `state:ready`
2. Create branch per Rule 07: `<type>/<issue-id>-<slug>`
3. Implement acceptance criteria + tests
4. Keep drafts in `.context/temp/` (promote durable notes to `.context/project/` or `.context/sprint/`)

### Opening a PR

1. Link issue: `Closes #123` / `Resolves #123`
2. Fill evidence mapping table
3. Request reviews (tag CODEOWNER + relevant reviewers)
4. Ensure CI is green

---

## 10. Enforcement Status

**Current Implementation:**
- ✅ Branch protection: Active (requires 1 approval + CODEOWNER review)
- ✅ Labels: Created (24 labels for state/type/priority/role)
- ✅ CODEOWNERS: Active (@nsin08)
- ⚠️ Workflows: Basic CI only (lint, tests, PR validation) - **framework workflows are reference implementations, need adaptation**

**Framework Workflows (70-enforcement/ - 17 files documented, need implementation):**
1. State Machine Enforcement
2. Artifact Linking
3. Approval Gates
4. Audit Logger
5. Security Gate
6. PR Validation
7. Issue Validation
8. Branch Protection Validation
9. Code Quality
10. Release Automation
11. Security Checks
12. Epic/Story Tracking
13. Definition of Ready
14. Definition of Done
15. Labeling Standard
16. Commit Linting
17. File Organization (Rule 11)

**Note:** Framework is enforcement-first by design; workflows are documented patterns that must be implemented per project needs.

---

## 11. Key References

- Framework roles: `10-roles/`
- Framework rules: `20-rules/` (especially Rule 01, 03, 04, 06, 07, 08, 10, 11)
- Templates: `50-templates/`
- Enforcement workflows (reference): `70-enforcement/` at https://github.com/nsin08/space_framework
- Framework adoption guide: https://github.com/nsin08/space_framework/blob/main/90-guides/01-framework-adoption.md
- Project CODEX: `.context/project/CODEX_HANDOVER.md`

---

## 12. Project-Specific Context

### Architecture

This project uses **Hexagonal Architecture** with:
- **Domain** layer: Pure business logic (entities, policies)
- **Application** layer: Use cases
- **Ports** layer: Interfaces
- **Adapters** layer: Infrastructure implementations

### Key Technologies

- **Backend:** Python 3.11 + FastAPI
- **Storage:** PostgreSQL 16 with pgvector extension
- **OCR:** PaddleOCR (primary), Tesseract (fallback)
- **PDF Processing:** PyMuPDF, pdfplumber, Camelot
- **LLM (local):** Ollama (llama3/qwen2.5)
- **LLM (cloud, optional):** OpenAI API
- **Embeddings:** BAAI/bge-large-en-v1.5
- **UI:** Streamlit (MVP)
- **Containers:** Docker + docker-compose

### Testing Strategy

- **Unit tests:** Domain logic, use cases
- **Integration tests:** Adapter implementations, database
- **E2E tests:** Full pipeline (PDF → query → answer)
- **Coverage target:** >80%

---

## Initialization Checklist (Human, One-Time)

- [x] Copy this file to `.github/copilot-instructions.md`
- [x] Fill Sections 2–6 with project-specific details
- [x] Ensure `.gitignore` has Rule 11 entries
- [x] Add CODEOWNERS file in `.github/CODEOWNERS`
- [ ] Configure branch protection rules for `main`
- [ ] Commit and push
