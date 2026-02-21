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
- content_text: string
- metadata: object
 - metadata.row_index: int | null
 - metadata.headers: list[string] | null
 - metadata.row_cells: list[string] | null
 - metadata.units: list[string] | null

## 3. Table Row Contract
Fields:
- table_id: string
- page: int
- headers: list[string]
- row_cells: list[string]
- units: list[string]
- row_text: string
- source_chunk_id: string

## 4. Figure Artifact Contract
Fields:
- figure_id: string
- page: int
- caption_text: string
- ocr_text: string
- bbox: list[float] (x0, y0, x1, y1)
- asset_ref: string

## 5. Visual Artifact Contract
Fields:
- visual_id: string
- doc_id: string
- page: int
- modality: figure | table | image
- region_id: string
- bbox: list[float]
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
