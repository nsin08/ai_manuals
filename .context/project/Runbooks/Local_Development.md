# Runbook: Local Development

Version: 1.1
Date: 2026-02-17

## Prerequisites

- Python 3.11
- Docker and Docker Compose
- Git

## Setup

1. Clone repo and `cd` to project root.
2. Install dependencies: `python -m pip install -r requirements.txt`
3. Start services: `docker compose -f infra/docker-compose.yml up --build -d`
4. Open UI: `http://localhost:8501`
5. Verify API: `http://localhost:8000/health`

## Daily Verification

- `python scripts/validate_data_contracts.py --strict-files`
- `pytest tests -q`
- `python scripts/run_regression_gates.py --doc-id rockwell_powerflex_40 --limit 5 --min-pass-rate 80`

## Evidence

- `.context/reports/phase5_runbook_validation.md`
