from __future__ import annotations

from pathlib import Path

from packages.adapters.data_contracts.yaml_catalog_adapter import YamlDocumentCatalogAdapter
from packages.adapters.ocr.factory import create_ocr_adapter
from packages.adapters.pdf.pypdf_parser_adapter import PypdfParserAdapter
from packages.adapters.storage.filesystem_chunk_store_adapter import FilesystemChunkStoreAdapter
from packages.adapters.tables.simple_table_extractor_adapter import SimpleTableExtractorAdapter
from packages.application.use_cases.ingest_document import (
    IngestDocumentInput,
    ingest_document_use_case,
)



def test_ingest_real_catalog_document_to_filesystem(tmp_path: Path) -> None:
    catalog_path = Path('.context/project/data/document_catalog.yaml')
    catalog = YamlDocumentCatalogAdapter(catalog_path)

    doc = catalog.get('rockwell_powerflex_40')
    assert doc is not None
    assert doc.status == 'present'
    assert doc.filename

    pdf_path = catalog_path.parent / doc.filename
    assert pdf_path.exists()

    out = ingest_document_use_case(
        IngestDocumentInput(doc_id=doc.doc_id, pdf_path=pdf_path),
        pdf_parser=PypdfParserAdapter(),
        ocr_adapter=create_ocr_adapter('noop', 'noop'),
        table_extractor=SimpleTableExtractorAdapter(),
        chunk_store=FilesystemChunkStoreAdapter(tmp_path),
    )

    assert out.total_chunks > 0
    chunks_path = Path(out.asset_ref)
    assert chunks_path.exists()

    with chunks_path.open('r', encoding='utf-8') as fh:
        lines = [line for line in fh if line.strip()]

    assert lines
