from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from packages.adapters.data_contracts.contracts import ValidationResult, validate_contracts


@dataclass(frozen=True)
class ValidateDataContractsInput:
    catalog_path: Path
    golden_questions_path: Path
    strict_files: bool = False



def validate_data_contracts_use_case(input_data: ValidateDataContractsInput) -> ValidationResult:
    return validate_contracts(
        catalog_path=input_data.catalog_path,
        golden_path=input_data.golden_questions_path,
        strict_files=input_data.strict_files,
    )
