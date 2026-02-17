# Project Context

Purpose: durable project documentation for architecture, decisions, planning, and operations.
Location: `.context/project/` (committed to version control).

## Quick Links

| Document | Purpose |
|----------|---------|
| [CODEX_HANDOVER.md](CODEX_HANDOVER.md) | MVP requirements and constraints |
| [PROJECT_PLAN.md](PROJECT_PLAN.md) | Comprehensive delivery plan and milestones |
| [PROGRESS_CHECKLIST.md](PROGRESS_CHECKLIST.md) | Phase-by-phase progress and evidence tracking |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Hexagonal architecture, modules, and data flow |
| [IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md) | Phased implementation sequence |
| [ADR/](ADR/) | Architecture Decision Records |
| [Tech_Stack/](Tech_Stack/) | Backend, frontend, and infrastructure guides |
| [Runbooks/](Runbooks/) | Development and operations runbooks |
| [Runbooks/Release_Checklist.md](Runbooks/Release_Checklist.md) | Release readiness checklist and sign-off |
| [data/README.md](data/README.md) | Dataset and golden-question contracts |

## Directory Structure

```text
.context/project/
|-- README.md
|-- CODEX_HANDOVER.md
|-- PROJECT_PLAN.md
|-- PROGRESS_CHECKLIST.md
|-- IMPLEMENTATION_ROADMAP.md
|-- ARCHITECTURE.md
|-- ADR/
|   |-- 001-pgvector-for-mvp.md
|   |-- 002-paddleocr-engine.md
|   |-- 003-grounded-answering.md
|   |-- 004-diagram-strategy.md
|   `-- 005-local-first-default.md
|-- Tech_Stack/
|   |-- Backend/
|   |   `-- README.md
|   |-- Frontend/
|   |   `-- README.md
|   `-- Infrastructure/
|       `-- README.md
|-- Runbooks/
|   |-- Local_Development.md
|   |-- Build_and_Test.md
|   |-- Deployment.md
|   |-- Troubleshooting.md
|   `-- Release_Checklist.md
`-- data/
    |-- README.md
    |-- golden_questions.yaml
    `-- document_catalog.yaml
```

## Usage Guidelines

When to add documents here:
- Architecture decisions affecting multiple components
- ADRs that capture tradeoffs and rationale
- Durable runbooks for repeatable procedures
- Technology guides for onboarding and standardization
- Medium to long horizon plans and milestones
- Stable benchmark and dataset contracts

When not to add documents here:
- Temporary exploration notes: use `.context/temp/`
- Issue-specific drafts and working notes: use `.context/issues/`
- Sprint-only artifacts: use `.context/sprint/`

## Contributing

1. Place docs in the appropriate subdirectory.
2. Update this `README.md` with new links.
3. Use descriptive filenames and stable headings.
4. Include date/version metadata when useful.
5. Link related docs (handover, architecture, ADRs, runbooks, data contracts).

Framework: `space_framework`
Last Updated: `2026-02-17`
