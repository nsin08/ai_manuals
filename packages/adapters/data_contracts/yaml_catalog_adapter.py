from __future__ import annotations

from pathlib import Path

from packages.adapters.data_contracts.contracts import load_catalog
from packages.ports.document_catalog_port import DocumentCatalogPort, DocumentCatalogRecord


class YamlDocumentCatalogAdapter(DocumentCatalogPort):
    def __init__(self, catalog_path: Path) -> None:
        self._catalog_path = catalog_path

    def list_documents(self) -> list[DocumentCatalogRecord]:
        rows = load_catalog(self._catalog_path)
        return [
            DocumentCatalogRecord(
                doc_id=row.doc_id,
                title=row.title,
                filename=row.filename,
                status=row.status,
            )
            for row in rows
        ]

    def get(self, doc_id: str) -> DocumentCatalogRecord | None:
        for row in self.list_documents():
            if row.doc_id == doc_id:
                return row
        return None
