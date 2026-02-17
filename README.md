# Equipment Manuals Chatbot

**Local-first AI chatbot for engineering documentation**

[![Framework](https://img.shields.io/badge/framework-space__framework-blue)](https://github.com/nsin08/space_framework)
[![Python](https://img.shields.io/badge/python-3.11-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Overview

A **local-first** chatbot that answers engineering questions from equipment manuals (PDFs), including scanned documents. Supports:

- 🔍 **Troubleshooting** queries (alarms, symptoms, recovery steps)
- 📋 **SOP/procedures** (commissioning, decommissioning, maintenance)
- 📊 **Specs from tables** (torque, clearance, dimensions)
- 🖼️ **Diagram interpretation** (wiring labels, dimension callouts)
- 📝 **Grounded answers with citations** (doc + page + figure/table)

Built with **Hexagonal Architecture**, **SOLID principles**, and **12-Factor methodology**.

---

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- 16GB+ RAM recommended
- GPU optional (for local LLM)

### Installation

```bash
# Clone repository
git clone https://github.com/nsin08/ai_manuals
cd ai_manuals

# Set up Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start services
docker compose up -d
```

### Run

```bash
# Run API
python -m apps.api.main

# Run UI (separate terminal)
streamlit run apps/ui/main.py
```

Visit: http://localhost:8501

---

## Features

### MVP Scope

- ✅ Ingest 5-10 PDFs (digital + scanned)
- ✅ Extract text, tables, and figures
- ✅ OCR for scanned pages and diagrams
- ✅ Hybrid search (keyword + vector)
- ✅ Evidence-grounded answers with citations
- ✅ Local-first (works offline)
- ✅ Optional cloud API toggle

### Architecture

```
/apps
  /api              # FastAPI application
  /ui               # Streamlit UI
/packages
  /domain           # Core business logic
  /application      # Use cases
  /adapters         # Infrastructure
  /ports            # Interfaces
```

See [CODEX_HANDOVER.md](.context/project/CODEX_HANDOVER.md) for complete system design.

---

## Tech Stack

- **Backend:** Python 3.11 + FastAPI
- **Storage:** PostgreSQL 16 + pgvector
- **OCR:** PaddleOCR (primary), Tesseract (fallback)
- **PDF:** PyMuPDF, pdfplumber, Camelot
- **LLM (local):** Ollama (llama3/qwen2.5)
- **Embeddings:** BAAI/bge-large-en-v1.5
- **UI:** Streamlit
- **Containers:** Docker Compose

---

## Development

### Run Tests

```bash
pytest tests/
```

### Lint & Format

```bash
black .
isort .
pylint apps/ packages/
mypy apps/ packages/
```

### Governance

This project follows [space_framework](https://github.com/nsin08/space_framework) governance:

- **State machine:** Idea → Approved → Ready → In Progress → In Review → Done → Released
- **Issue templates:** See [.github/ISSUE_TEMPLATE/](.github/ISSUE_TEMPLATE/)
- **PR template:** Evidence mapping required
- **CODEOWNER:** @nsin08 (merge authority)

See [.github/copilot-instructions.md](.github/copilot-instructions.md) for complete workflow.

---

## Documentation

| Document | Purpose |
|----------|---------|
| [CODEX_HANDOVER](.context/project/CODEX_HANDOVER.md) | MVP requirements & system design |
| [VERIFICATION](VERIFICATION.md) | Setup verification checklist |
| [SETUP_COMMANDS](.github/SETUP_COMMANDS.md) | GitHub configuration |
| [Copilot Instructions](.github/copilot-instructions.md) | Agent guidelines |

---

## Contributing

1. Pick a Story in `state:ready`
2. Create branch: `feature/<issue-id>-<slug>`
3. Implement with tests
4. Open PR with evidence mapping
5. Request review

See [Contributing Guidelines](.github/copilot-instructions.md#9-essential-workflows) for details.

---

## License

MIT License - See [LICENSE](LICENSE) for details

---

## Acknowledgments

- **Framework:** [space_framework](https://github.com/nsin08/space_framework)
- **Architecture:** Hexagonal Architecture + SOLID + 12-Factor
- **Governance:** CODEOWNER-enforced PR workflow

---

**Project Status:** Active Development  
**Last Updated:** 2026-02-17
