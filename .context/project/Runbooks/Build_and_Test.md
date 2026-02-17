# Runbook: Build and Test

Version: 1.1
Date: 2026-02-17

## Local Build

1. `docker compose -f infra/docker-compose.yml up --build -d`
2. `python -m pip install -r requirements.txt`

## Test Commands

- Full tests: `pytest tests -q`
- Strict contract check: `python scripts/validate_data_contracts.py --strict-files`
- Regression gates (Phase 5): `python scripts/run_regression_gates.py --doc-id rockwell_powerflex_40 --limit 5 --min-pass-rate 80`
- Security/local-first checks: `python scripts/check_local_first_security.py`

## CI Gate Definition

- Workflow: `.github/workflows/18-regression-gates.yml`
- Required checks:
  - strict contract validation
  - full `pytest`
  - golden-threshold regression gate (minimum pass rate: 80 on `rockwell_powerflex_40` subset)

## Evidence

- `.context/reports/phase5_pytest.txt`
- `.context/reports/phase5_regression_gate.json`
- `.context/reports/phase5_runbook_validation.md`
