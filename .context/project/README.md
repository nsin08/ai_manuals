# Project Context

**Purpose:** Durable project documentation (architecture, ADRs, meetings, runbooks)  
**Location:** `.context/project/` (committed to version control)

---

## Quick Links

| Document | Purpose |
|----------|---------|
| [CODEX_HANDOVER.md](CODEX_HANDOVER.md) | MVP requirements and system overview |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Hexagonal architecture design |
| [ADR/](ADR/) | Architecture Decision Records |

---

## Directory Structure

```
.context/project/
├── README.md                    # This file
├── CODEX_HANDOVER.md            # MVP requirements
├── ARCHITECTURE.md              # System architecture
├── ADR/                         # Architecture decisions
│   ├── 001-pgvector-for-mvp.md
│   ├── 002-paddleocr-engine.md
│   ├── 003-grounded-answering.md
│   ├── 004-diagram-strategy.md
│   └── 005-local-first-default.md
├── Tech_Stack/                  # Technology guides
│   ├── Backend/
│   ├── Frontend/
│   └── Infrastructure/
└── Runbooks/                    # Operational procedures
    ├── Local_Development.md
    ├── Build_and_Test.md
    ├── Deployment.md
    └── Troubleshooting.md
```

---

## Usage Guidelines

### When to Add Documents Here

- **Architecture decisions** that affect multiple components
- **ADRs** (why we chose X over Y)
- **Runbooks** for common tasks
- **Meeting notes** with lasting decisions
- **Tech stack guides** for onboarding

### When NOT to Add Here

- **Temporary notes** → use `.context/temp/`
- **Issue-specific work** → use `.context/issues/`
- **Sprint-specific artifacts** → use `.context/sprint/`

---

## Contributing

1. Create new documents in appropriate subdirectories
2. Update this README with links
3. Use clear, descriptive filenames
4. Include frontmatter with date/author when appropriate
5. Link related documents

---

**Framework:** space_framework  
**Last Updated:** 2026-02-17
