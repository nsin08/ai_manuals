from __future__ import annotations

from pathlib import Path

from packages.adapters.data_contracts.yaml_catalog_adapter import YamlDocumentCatalogAdapter
from packages.adapters.ocr.factory import create_ocr_adapter
from packages.adapters.pdf.pypdf_parser_adapter import PypdfParserAdapter
from packages.adapters.retrieval.filesystem_chunk_query_adapter import FilesystemChunkQueryAdapter
from packages.adapters.retrieval.hash_vector_search_adapter import HashVectorSearchAdapter
from packages.adapters.retrieval.simple_keyword_search_adapter import SimpleKeywordSearchAdapter
from packages.adapters.storage.filesystem_chunk_store_adapter import FilesystemChunkStoreAdapter
from packages.adapters.tables.simple_table_extractor_adapter import SimpleTableExtractorAdapter
from packages.application.use_cases.ingest_document import IngestDocumentInput, ingest_document_use_case
from packages.application.use_cases.search_evidence import SearchEvidenceInput, search_evidence_use_case



def test_search_after_ingestion_returns_hits(tmp_path: Path) -> None:
    catalog_path = Path('.context/project/data/document_catalog.yaml')
    catalog = YamlDocumentCatalogAdapter(catalog_path)
    doc = catalog.get('rockwell_powerflex_40')

    assert doc is not None
    pdf_path = catalog_path.parent / (doc.filename or '')
    assert pdf_path.exists()

    ingest_document_use_case(
        IngestDocumentInput(doc_id=doc.doc_id, pdf_path=pdf_path),
        pdf_parser=PypdfParserAdapter(),
        ocr_adapter=create_ocr_adapter('noop', 'noop'),
        table_extractor=SimpleTableExtractorAdapter(),
        chunk_store=FilesystemChunkStoreAdapter(tmp_path),
    )

    output = search_evidence_use_case(
        SearchEvidenceInput(query='fault code table corrective action', doc_id=doc.doc_id, top_n=5),
        chunk_query=FilesystemChunkQueryAdapter(tmp_path),
        keyword_search=SimpleKeywordSearchAdapter(),
        vector_search=HashVectorSearchAdapter(),
        trace_logger=None,
    )

    assert output.total_chunks_scanned > 0
    assert output.hits
    assert any(hit.content_type in {'table_row', 'text'} for hit in output.hits)
