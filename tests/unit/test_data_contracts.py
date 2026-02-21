from __future__ import annotations

from pathlib import Path

from packages.adapters.data_contracts.contracts import validate_contracts
from packages.adapters.data_contracts.yaml_catalog_adapter import YamlDocumentCatalogAdapter


DATA_DIR = Path('.context/project/data')
CATALOG = DATA_DIR / 'document_catalog.yaml'
GOLDEN = DATA_DIR / 'golden_questions.yaml'



def test_validate_contracts_non_strict_has_no_errors() -> None:
    result = validate_contracts(CATALOG, GOLDEN, strict_files=False)
    assert result.errors == []



def test_validate_contracts_strict_has_no_errors_when_all_docs_present() -> None:
    result = validate_contracts(CATALOG, GOLDEN, strict_files=True)
    assert result.errors == []



def test_yaml_catalog_adapter_lookup() -> None:
    adapter = YamlDocumentCatalogAdapter(CATALOG)
    rockwell = adapter.get('rockwell_powerflex_40')

    assert rockwell is not None
    assert rockwell.filename == '22b-um001_-en-e.pdf'
