# Workflow Index

This repository includes governance and quality workflows under `.github/workflows/`.

## Core Quality and Release

- `09-code-quality.yml`: lint and test jobs
- `11-security-checks.yml`: secret/dependency scanning
- `18-regression-gates.yml`: strict regression gates for contracts, tests, and golden threshold
- `10-release-automation.yml`: tag-driven GitHub release

## Governance

- `01-enforce-state-machine.yml`
- `02-enforce-artifact-linking.yml`
- `03-enforce-approval-gates.yml`
- `04-audit-logger.yml`
- `05-security-gate.yml`
- `06-pr-validation.yml`
- `07-issue-validation.yml`
- `08-branch-protection.yml`
- `12-epic-story-tracking.yml`
- `13-definition-of-ready.yml`
- `14-definition-of-done.yml`
- `15-labeling-standard.yml`
- `16-commit-lint.yml`
- `17-file-organization.yml`

## Phase 5 Regression Gate Details

The `18-regression-gates.yml` workflow enforces:

1. `python scripts/validate_data_contracts.py --strict-files`
2. `pytest tests -q`
3. `python scripts/run_regression_gates.py --doc-id rockwell_powerflex_40 --limit 5 --top-n 6 --min-pass-rate 80`

The workflow uploads `.context/reports/regression_gate_ci.json` as an artifact.
