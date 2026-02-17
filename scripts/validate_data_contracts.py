from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.application.use_cases.validate_data_contracts import (
    ValidateDataContractsInput,
    validate_data_contracts_use_case,
)



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Validate project data contracts')
    parser.add_argument(
        '--catalog',
        type=Path,
        default=Path('.context/project/data/document_catalog.yaml'),
        help='Path to document catalog YAML',
    )
    parser.add_argument(
        '--golden',
        type=Path,
        default=Path('.context/project/data/golden_questions.yaml'),
        help='Path to golden questions YAML',
    )
    parser.add_argument(
        '--strict-files',
        action='store_true',
        help='Treat missing catalog documents as errors',
    )
    return parser.parse_args()



def main() -> int:
    args = parse_args()
    result = validate_data_contracts_use_case(
        ValidateDataContractsInput(
            catalog_path=args.catalog,
            golden_questions_path=args.golden,
            strict_files=args.strict_files,
        )
    )

    print('Data contract validation summary')
    print(f'  Errors: {len(result.errors)}')
    print(f'  Warnings: {len(result.warnings)}')

    for error in result.errors:
        print(f'ERROR: {error}')
    for warning in result.warnings:
        print(f'WARNING: {warning}')

    return 1 if result.errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
