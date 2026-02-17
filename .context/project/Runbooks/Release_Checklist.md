# Runbook: Release Checklist

Version: 1.0
Date: 2026-02-17
Status: Signed

## Candidate

- Branch: `develop`
- Target: MVP hardening baseline (Phase 5)

## Required Checks

- [x] Strict data contracts pass
- [x] Full automated tests pass
- [x] Regression gate pass rate meets threshold
- [x] Security/local-first checks pass
- [x] Performance baseline captured
- [x] Runbook validation completed

## Evidence

- `.context/reports/phase5_pytest.txt`
- `.context/reports/phase5_regression_gate.json`
- `.context/reports/phase5_security_local_first.json`
- `.context/reports/phase5_performance_baseline.json`
- `.context/reports/phase5_runbook_validation.md`
- `.github/workflows/18-regression-gates.yml`

## Sign-off

- Signed by: Codex
- Signed at: 2026-02-17 UTC
