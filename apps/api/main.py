from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from packages.application.config import load_config
from packages.application.use_cases.validate_data_contracts import (
    ValidateDataContractsInput,
    validate_data_contracts_use_case,
)


DATA_DIR = Path('.context/project/data')
CATALOG_PATH = DATA_DIR / 'document_catalog.yaml'
GOLDEN_PATH = DATA_DIR / 'golden_questions.yaml'

app = FastAPI(title='Equipment Manuals Chatbot API', version='0.1.0')


@app.get('/health')
def health() -> dict[str, object]:
    cfg = load_config()
    validation = validate_data_contracts_use_case(
        ValidateDataContractsInput(
            catalog_path=CATALOG_PATH,
            golden_questions_path=GOLDEN_PATH,
            strict_files=False,
        )
    )

    return {
        'status': 'ok' if validation.is_valid() else 'degraded',
        'app_env': cfg.app_env,
        'llm_provider': cfg.llm_provider,
        'contract_errors': len(validation.errors),
        'contract_warnings': len(validation.warnings),
    }


@app.get('/health/contracts')
def contract_health() -> dict[str, object]:
    validation = validate_data_contracts_use_case(
        ValidateDataContractsInput(
            catalog_path=CATALOG_PATH,
            golden_questions_path=GOLDEN_PATH,
            strict_files=False,
        )
    )

    return {
        'valid': validation.is_valid(),
        'errors': validation.errors,
        'warnings': validation.warnings,
    }
