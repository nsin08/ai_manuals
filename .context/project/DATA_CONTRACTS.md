# Data Contracts

Version: 1.0
Date: 2026-02-21
Status: Draft

## 1. Document Catalog Entry
Fields:
- doc_id: string (unique)
- title: string
- filename: string
- revision: string
- source_hash: string
- tags: list[string]

## 2. Chunk Contract
Fields:
- chunk_id: string
- doc_id: string
- content_type: text | table_row | figure_ocr | vision_summary
- page_start: int
- page_end: int
- section_path: string | null
- table_id: string | null
- figure_id: string | null
- caption: string | null
- content_text: string (for table_row: format is `headers || row_cells` when headers present, else just `row_cells` joined by ` | `)
- metadata: object
 - metadata.row_index: int | null (for table_row chunks: 0-indexed row position within table)
 - metadata.headers: list[string] | null (for table_row: column header names, empty list if no header detected)
 - metadata.row_cells: list[string] | null (for table_row: cell values, one per column)
 - metadata.units: list[string] | null (for table_row: extracted units per cell, same length as row_cells)
 - metadata.bbox: list[float] | null (normalized bbox [x0, y0, x1, x1] in [0,1] range; null for text/table_row without explicit extraction)

## 3. Table Row Extraction Contract (Port: TableExtractorPort)

ExtractedTableRow structure:
- table_id: string (format: `tbl_{doc_id}_{page}_{table_idx:03d}` when doc_id provided, else `table-p{page:04d}-{idx:03d}`)
- page_number: int
- row_index: int (0-indexed within table rows, after header)
- headers: list[string] (empty list if no header detected; threshold: >= 50% of first row must be non-numeric strings < 30 chars)
- row_cells: list[str] (parsed cell values, split on `|` or 2+ spaces or `:` for key-value pairs)
- units: list[str] (extracted from `(unit)` patterns; same length as row_cells, empty string when absent)
- raw_text: string (original unparsed row text for fallback)

## 4. Figure Artifact Contract
Fields:
- figure_id: string
- page: int
- caption_text: string
- ocr_text: string
- bbox: list[float] (x0, y0, x1, y1)
- asset_ref: string

## 5. Visual Artifact Contract (from Chunk metadata)
Fields:
- visual_id: string (format: `fig-p{page:04d}-{idx:03d}` for figures, `tbl_{...}` for tables)
- doc_id: string
- page: int
- modality: figure | table | image (detected from content_type: figure_ocr → figure, table_row → table, etc.)
- region_id: string
- bbox: list[float] (normalized to [0,1] range: [x0, y0, x1, y1]; extracted from PyMuPDF image blocks or from chunk metadata)
  - For figures: extracted via _extract_figure_regions from PyMuPDF page.get_images() blocks
  - For table_row chunks: defaults to [0, 0, 1, 1] (full page) unless specific bbox provided in metadata
- caption_text: string
- ocr_text: string
- linked_text_chunk_ids: list[string]
- asset_ref: string

## 6. Retrieval Trace Contract
Fields:
- query: string
- intent: string
- doc_id: string | null
- top_hits: list[{chunk_id, content_type, score, table_id, figure_id}]
- total_chunks_scanned: int
- modality_hit_counts: object with keys {text, table, figure, visual}
- timestamp_utc: string

## 7. Answer Contract
Fields:
- answer_text: string
- citations: list[{doc_id, page, chunk_id, table_id, figure_id}]
- confidence: float (0..1)
- abstain: bool
- follow_up_question: string | null

## 8. Ingestion QC Contract
Fields:
- doc_id: string
- total_pages: int
- text_coverage: float
- ocr_coverage: float
- table_yield: float
- embedding_coverage: float
- status: pass | warn | fail

## 9. Example Answer Payload
{
  "answer_text": "Set parameter p2596 to 2 for reference cam with zero mark.",
  "citations": [
    {"doc_id": "siemens_g120_basic_positioner", "page": 128, "chunk_id": "...", "table_id": "table-p0128-001", "figure_id": null}
  ],
  "confidence": 0.84,
  "abstain": false,
  "follow_up_question": null
}
