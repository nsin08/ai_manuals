# Workflow Files Placeholder

**Status:** TO BE COPIED FROM FRAMEWORK  
**Source:** https://github.com/nsin08/space_framework/tree/main/70-enforcement

---

## Required Workflows (17 total)

The following workflow files need to be copied from the space_framework repository:

1. `01-enforce-state-machine.yml` - Enforces state transitions
2. `02-enforce-artifact-linking.yml` - Validates Epic→Story→PR chain
3. `03-enforce-approval-gates.yml` - Role-based approval requirements
4. `04-audit-logger.yml` - Logs all governance events
5. `05-security-gate.yml` - Security validation
6. `06-pr-validation.yml` - PR hygiene checks
7. `07-issue-validation.yml` - Issue quality checks
8. `08-branch-protection.yml` - Merge requirements
9. `09-code-quality.yml` - Linting and testing
10. `10-release-automation.yml` - Release workflow
11. `11-security-checks.yml` - Vulnerability scanning
12. `12-epic-story-tracking.yml` - Issue hierarchy validation
13. `13-definition-of-ready.yml` - DoR checklist validation
14. `14-definition-of-done.yml` - DoD checklist validation
15. `15-labeling-standard.yml` - Label consistency
16. `16-commit-lint.yml` - Conventional commits
17. `17-file-organization.yml` - Rule 11 file placement

---

## How to Install

### Option 1: Manual Copy (Recommended for now)

Clone the space_framework repository and copy the workflows:

```bash
# Clone framework repo
git clone https://github.com/nsin08/space_framework /tmp/space_framework

# Copy workflows
cp /tmp/space_framework/70-enforcement/*.yml .github/workflows/

# Review and customize for your project
```

### Option 2: Using Framework Script

```bash
# Clone framework locally
git clone https://github.com/nsin08/space_framework

# Run install script
python space_framework/scripts/install_framework.py \
  --source-root space_framework \
  --repo-root .
```

---

## Project-Specific Customization

After copying, update these in workflows:

- Python version (`3.11`)
- Test commands (`pytest tests/`)
- Lint commands (`black .`, `pylint apps/ packages/`)
- Build commands (if any)

---

## Initial Setup (Minimal CI)

For MVP, create a basic CI workflow first:

**`.github/workflows/ci.yml`:**

```yaml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Lint
        run: |
          pip install black pylint mypy
          black --check .
          pylint apps/ packages/
      
      - name: Test
        run: |
          pytest tests/ --cov=apps --cov=packages
```

---

**Next Step:** Copy workflows from framework or create minimal CI first
