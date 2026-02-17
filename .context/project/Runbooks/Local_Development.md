# Runbook: Local Development

Version: 1.0
Date: 2026-02-17

## Prerequisites

- Python 3.11
- Docker and Docker Compose
- Git

## Steps

1. Clone repository and enter project directory.
2. Create and activate virtual environment.
3. Install dependencies.
4. Start containers with `docker compose up -d`.
5. Start API and UI processes.

## Verification

- API health endpoint responds.
- UI loads in browser.
- Postgres and Redis containers are healthy.

## Common Local Commands

- `pytest tests/`
- `black .`
- `isort .`
- `pylint apps/ packages/`
- `mypy apps/ packages/`
