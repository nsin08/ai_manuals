# Space Framework Adoption — Setup Complete ✅

## Summary

The `ai_manuals` repository has been successfully configured with the **space_framework** governance model. All automated setup is complete and ready for team collaboration.

---

## What Was Configured

### 1. **Labels (24 created)**
All labels follow space_framework taxonomy for workflow state machine and artifact classification:

- **State Labels** (7): `state:idea`, `state:approved`, `state:ready`, `state:in-progress`, `state:in-review`, `state:done`, `state:released`
- **Type Labels** (8): `type:feature`, `type:epic`, `type:story`, `type:task`, `type:bug`, `type:chore`, `type:refactor`, `type:docs`, `type:test`
- **Priority Labels** (4): `priority:critical`, `priority:high`, `priority:medium`, `priority:low`
- **Role Labels** (4): `role:implementer`, `role:reviewer`, `role:architect`, `role:devops`

**Usage:** Label issues as they move through the workflow. AI agents and humans tag items with state and role labels to track progress and enforce the state machine.

---

### 2. **Branch Protection (Lightweight)**
Main branch (`main`) is protected with:
- ✅ Requires 1 approval on PRs
- ✅ Requires CODEOWNER (@nsin08) review
- ✅ Non-strict: Allows force pushes and deletions (no linear history requirement)
- ✅ No status checks enforced (allows full automation flexibility)

**Why non-strict?** Per user requirement: "dont add strict branch protection rules" — this allows fast iteration while maintaining code review quality.

---

### 3. **Governance Documentation**

#### `.github/copilot-instructions.md`
- Mandatory context loading: `@space_framework Load: 10-roles/00-shared-context.md`
- Detailed role entry points for Implementer, Reviewer, DevOps, Architect
- Hard boundaries (cannot merge, approve, or skip states)
- Code standards, branch naming, commit format requirements
- Quick start setup for Python 3.11, FastAPI, Docker

#### `.github/FILE_HYGIENE.md` (NEW)
- Complete Rule 11 classification guide: **Committed vs. Git-Ignored**
- Explains each context directory:
  - `.context/project/` — Durable, long-term documentation ✅ **Tracked in Git**
  - `.context/sprint/` — Sprint plans and retrospectives ✅ **Tracked in Git**
  - `.context/temp/` — Agent drafts and scratch work ❌ **Git-ignored**
  - `.context/issues/` — Issue-specific investigation ❌ **Git-ignored**
  - `.context/reports/` — Generated outputs ❌ **Git-ignored**
- Workflow examples and quick reference table
- Enforcement policy

#### Issue Templates (7 files)
- **01-idea.md** — Feature requests with business value
- **02-epic.md** — Technical epics with components/dependencies
- **03-story.md** — User stories with DoR checklist
- **04-task.md** — Technical tasks (chores, refactor, docs)
- **05-dor-checklist.md** — Definition of Ready validation
- **06-dod-checklist.md** — Definition of Done validation
- **07-feature-request.md** — User-submitted requests

#### PR Template
- Evidence mapping table (criterion → test → location) per Rule 04
- Comprehensive DoD checklist
- Links to CODEX_HANDOVER and relevant standards

---

### 4. **Enforcement Workflows (3 core)**

#### 01-lint.yml
- Runs on PRs and pushes to `main`/`develop`
- Checks: black (format), isort (imports), pylint (linting), mypy (types)
- Non-blocking (warnings only) to support fast iteration

#### 02-tests.yml
- Unit tests with coverage reporting
- Integration tests with PostgreSQL service
- Uploads coverage to Codecov
- Runs on PRs and `main`/`develop` branch

#### 03-validate-pr.yml
- Validates PR links an issue (requires "Closes #123" or "Resolves #456")
- Warns if evidence mapping table is missing
- Enforces Rule 04 (artifact linking)

---

### 5. **Directory Structure**

```
.github/
├── CODEOWNERS                      # Enforces @nsin08 as sole merger
├── copilot-instructions.md         # AI agent workflow (12 sections)
├── FILE_HYGIENE.md                 # Rule 11 classification guide (NEW)
├── SETUP_COMMANDS.md               # Label + protection setup (reference)
├── branch-protection.json          # Branch protection config (reference)
├── pull_request_template.md        # PR evidence mapping (Rule 04)
├── workflows/
│   ├── 01-lint.yml                # Format/type checking
│   ├── 02-tests.yml               # Unit + integration tests
│   └── 03-validate-pr.yml         # PR validation (links, evidence)
└── [7 issue templates]

.context/
├── project/
│   ├── README.md                  # Project documentation index
│   ├── CODEX_HANDOVER.md          # Complete MVP requirements
│   └── [ADRs to be added]         # Architecture decisions
├── sprint/
│   ├── README.md                  # Sprint cadence definition
│   └── [sprint-NN/ folders]       # Sprint plans, retros, metrics
├── temp/                          # ❌ Git-ignored (drafts)
├── issues/                        # ❌ Git-ignored (issue workspaces)
└── reports/                       # ❌ Git-ignored (generated outputs)

README.md                          # Project overview
VERIFICATION.md                    # Setup checklist
.gitignore                         # Rule 11 ignores + Python
```

---

## Key Files to Review

| File | Purpose | Link |
|------|---------|------|
| **FILE_HYGIENE.md** | Rule 11 classification (Committed vs. Git-ignored) | [.github/FILE_HYGIENE.md](.github/FILE_HYGIENE.md) |
| **CODEX_HANDOVER.md** | Complete MVP requirements (11 sections) | [.context/project/CODEX_HANDOVER.md](.context/project/CODEX_HANDOVER.md) |
| **copilot-instructions.md** | AI agent workflow and boundaries | [.github/copilot-instructions.md](.github/copilot-instructions.md) |
| **pull_request_template.md** | PR evidence mapping requirements | [.github/pull_request_template.md](.github/pull_request_template.md) |

---

## Next Steps for Team

### For all contributors:
1. **Read FILE_HYGIENE.md** — Understand where files go
2. **Read copilot-instructions.md** — Know the governance rules
3. **Review CODEX_HANDOVER.md** — Understand MVP requirements
4. **Label first issues** — Test the workflow with `state:ready` + `type:story` labels

### For first implementation work:
1. Ensure issue is labeled `state:ready` before starting
2. Create branch: `feature/<issue-id>-<slug>` (e.g., `feature/42-pdf-ingestion`)
3. Link PR: Include "Closes #42" or "Resolves #42" in PR body
4. Add evidence mapping table showing criterion → test → location
5. Request review (CODEOWNER @nsin08 will review automatically)

### For infrastructure:
1. **Workflows** activate automatically on PRs to `main`
2. **Labels** are ready to use immediately
3. **Branch protection** enforces 1 approval + CODEOWNER review (non-strict)
4. **Template prompts** appear when creating new issues/PRs in GitHub UI

---

## Verification Checklist ✅

- [x] Repository created: `nsin08/ai_manuals`
- [x] All governance files committed
- [x] 24 labels created
- [x] Branch protection configured (lightweight, non-strict)
- [x] Core workflows installed (lint, tests, PR validation)
- [x] FILE_HYGIENE.md guide created
- [x] Context directories created (project, sprint, temp, issues, reports)
- [x] Initial commits pushed to GitHub
- [x] PR template with evidence mapping ready
- [x] Issue templates ready (7 types)

---

## Repository Links

- **Repository:** https://github.com/nsin08/ai_manuals
- **Space Framework:** https://github.com/nsin08/space_framework
- **Settings:** https://github.com/nsin08/ai_manuals/settings

---

## Governance Model

This repository enforces the **space_framework** state machine:

```
Idea → Approved → Ready → In Progress → In Review → Done → Released
```

**Key Rules Enforced:**
- Rule 01: State machine (cannot skip states)
- Rule 03: Tests required for all acceptance criteria
- Rule 04: PRs must link issues with evidence mapping
- Rule 06: CODEOWNER (@nsin08) merges all PRs
- Rule 07: Branch naming convention (`<type>/<id>-<slug>`)
- Rule 08: PR requirements (link + evidence + reviewable)
- Rule 11: File hygiene (committed vs. git-ignored classification)

For full framework details, see: https://github.com/nsin08/space_framework/tree/main/20-rules

---

## Support

For questions about:
- **Governance:** Read `.github/copilot-instructions.md` Section 8 (Hard Boundaries)
- **File organization:** Read `.github/FILE_HYGIENE.md`
- **MVP requirements:** Read `.context/project/CODEX_HANDOVER.md`
- **Workflow state machine:** Load `@space_framework` and read `10-roles/00-shared-context.md`

