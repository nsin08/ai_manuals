from __future__ import annotations

import ast
from pathlib import Path


FORBIDDEN_IMPORT_PREFIXES = (
    'langchain',
    'langgraph',
    'packages.adapters.agentic',
)


def _collect_imports(py_path: Path) -> list[str]:
    tree = ast.parse(py_path.read_text(encoding='utf-8-sig'))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.append(node.module)
    return modules


def test_application_and_domain_do_not_import_agentic_framework_modules() -> None:
    roots = [Path('packages/application'), Path('packages/domain')]
    offenders: list[str] = []

    for root in roots:
        for py_path in root.rglob('*.py'):
            for module in _collect_imports(py_path):
                if module.startswith(FORBIDDEN_IMPORT_PREFIXES):
                    offenders.append(f'{py_path}:{module}')

    assert offenders == []
