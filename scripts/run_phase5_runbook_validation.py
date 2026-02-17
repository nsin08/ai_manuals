from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Validate runbook commands and capture report')
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('.context/reports/phase5_runbook_validation.md'),
    )
    return parser.parse_args()


def _run(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    combined = '\n'.join(part for part in [result.stdout.strip(), result.stderr.strip()] if part)
    return result.returncode, combined


def main() -> int:
    args = parse_args()
    commands = [
        [sys.executable, 'scripts/validate_data_contracts.py', '--strict-files'],
        [sys.executable, '-m', 'pytest', 'tests', '-q'],
        [sys.executable, 'scripts/run_regression_gates.py', '--doc-id', 'rockwell_powerflex_40', '--limit', '5', '--min-pass-rate', '80', '--output', '.context/reports/phase5_regression_gate.json'],
        [sys.executable, 'scripts/check_local_first_security.py', '--output', '.context/reports/phase5_security_local_first.json'],
    ]

    rows: list[tuple[str, int, str]] = []
    overall_ok = True
    for command in commands:
        rc, output = _run(command)
        text = output if output else '(no output)'
        rows.append((' '.join(command), rc, text))
        if rc != 0:
            overall_ok = False

    lines = [
        '# Phase 5 Runbook Validation',
        '',
        f'- Generated at: {datetime.now(UTC).isoformat()}',
        f'- Overall status: {"PASS" if overall_ok else "FAIL"}',
        '',
    ]

    for command, rc, output in rows:
        lines.append(f'## Command: `{command}`')
        lines.append(f'- Exit code: `{rc}`')
        lines.append('```text')
        lines.append(output)
        lines.append('```')
        lines.append('')

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text('\n'.join(lines), encoding='utf-8')
    print('\n'.join(lines))
    return 0 if overall_ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
