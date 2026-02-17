# Runbook: Build and Test

Version: 1.0
Date: 2026-02-17

## Build Process

1. Build/update service images via Docker Compose.
2. Install Python dependencies in virtual environment.
3. Run formatting and lint checks.

## Test Levels

- Unit tests: domain/application logic
- Integration tests: adapters and persistence
- E2E tests: ingest to answer flow

## Quality Gates

- All tests pass
- Lint and type checks pass
- No boundary violations across architecture layers

## Troubleshooting Failing CI

1. Reproduce locally with same commands.
2. Check environment variable differences.
3. Validate DB and Redis service availability.
4. Re-run targeted failed tests with verbose output.
