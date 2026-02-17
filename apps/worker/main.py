from __future__ import annotations

import time
from pathlib import Path

from packages.application.use_cases.validate_data_contracts import (
    ValidateDataContractsInput,
    validate_data_contracts_use_case,
)



def main() -> int:
    data_dir = Path('.context/project/data')
    result = validate_data_contracts_use_case(
        ValidateDataContractsInput(
            catalog_path=data_dir / 'document_catalog.yaml',
            golden_questions_path=data_dir / 'golden_questions.yaml',
            strict_files=False,
        )
    )

    print('Worker scaffold ready')
    print(f'Contract errors: {len(result.errors)}')
    print(f'Contract warnings: {len(result.warnings)}')

    if result.errors:
        for err in result.errors:
            print(f'ERROR: {err}')
        return 1

    # Keep worker process alive in Phase 0 so compose service health is stable.
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print('Worker stopping')
        return 0


if __name__ == '__main__':
    raise SystemExit(main())
