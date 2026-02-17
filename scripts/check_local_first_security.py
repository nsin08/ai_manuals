from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run local-first and security sanity checks')
    parser.add_argument(
        '--env-example',
        type=Path,
        default=Path('.env.example'),
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('.context/reports/phase5_security_local_first.json'),
    )
    return parser.parse_args()


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or '=' not in stripped:
            continue
        key, value = stripped.split('=', 1)
        values[key.strip()] = value.strip()
    return values


def _scan_external_urls() -> list[str]:
    allow_hosts = {'localhost', '127.0.0.1', 'api', 'ollama', 'redis', 'postgres'}
    pattern = re.compile(r'https?://([a-zA-Z0-9._-]+)')
    hits: list[str] = []

    for path in Path('.').rglob('*.py'):
        if '.venv' in path.parts:
            continue
        if '__pycache__' in path.parts:
            continue
        text = path.read_text(encoding='utf-8', errors='ignore')
        for match in pattern.findall(text):
            host = match.lower()
            if host in allow_hosts:
                continue
            hits.append(f'{path}: {host}')

    return sorted(set(hits))


def main() -> int:
    args = parse_args()
    checks: list[dict[str, object]] = []

    if not args.env_example.exists():
        checks.append({'name': 'env_example_exists', 'passed': False, 'details': str(args.env_example)})
    else:
        env_values = _parse_env_file(args.env_example)
        checks.append({'name': 'env_example_exists', 'passed': True})
        checks.append(
            {
                'name': 'default_llm_provider_local',
                'passed': env_values.get('LLM_PROVIDER') == 'local',
                'actual': env_values.get('LLM_PROVIDER'),
            }
        )
        checks.append(
            {
                'name': 'default_asset_store_filesystem',
                'passed': env_values.get('ASSET_STORE') == 'filesystem',
                'actual': env_values.get('ASSET_STORE'),
            }
        )
        checks.append(
            {
                'name': 'cloud_api_key_not_required_by_default',
                'passed': 'CLOUD_API_KEY' not in env_values,
            }
        )

    external_urls = _scan_external_urls()
    checks.append(
        {
            'name': 'no_external_http_calls_in_runtime_python',
            'passed': len(external_urls) == 0,
            'external_calls': external_urls,
        }
    )

    pip_check = subprocess.run(
        [sys.executable, '-m', 'pip', 'check'],
        capture_output=True,
        text=True,
        check=False,
    )
    checks.append(
        {
            'name': 'pip_dependency_integrity',
            'passed': pip_check.returncode == 0,
            'stdout': pip_check.stdout.strip(),
            'stderr': pip_check.stderr.strip(),
        }
    )

    overall_passed = all(bool(row.get('passed')) for row in checks)
    payload = {'overall_passed': overall_passed, 'checks': checks}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(json.dumps(payload, indent=2))
    return 0 if overall_passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
