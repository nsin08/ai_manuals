from __future__ import annotations

from packages.adapters.ocr.factory import create_ocr_adapter
from packages.adapters.ocr.noop_ocr_adapter import NoopOcrAdapter
from packages.adapters.ocr.tesseract_ocr_adapter import TesseractOcrAdapter
from packages.adapters.tables.simple_table_extractor_adapter import SimpleTableExtractorAdapter



def test_ocr_factory_falls_back_for_unknown_primary() -> None:
    adapter = create_ocr_adapter('unknown', 'noop')
    assert isinstance(adapter, NoopOcrAdapter)



def test_ocr_factory_selects_tesseract() -> None:
    adapter = create_ocr_adapter('tesseract', 'noop')
    # Wrapped in fallback adapter; check concrete class via type name when needed.
    assert adapter.__class__.__name__ in {'FallbackOcrAdapter', 'TesseractOcrAdapter'}



def test_table_extractor_detects_key_value_rows() -> None:
    page_text = '\n'.join(
        [
            'Torque: 45 Nm',
            'Clearance: 0.2 mm',
            'Gap: 1.5 mm',
            'Notes: verify alignment',
        ]
    )

    tables = SimpleTableExtractorAdapter().extract(page_text, page_number=1)
    assert tables
    assert 'Torque | 45 Nm' in tables[0].raw_text



def test_table_extractor_detects_multicolumn_rows() -> None:
    page_text = '\n'.join(
        [
            'Parameter    Value    Unit',
            'Torque       45       Nm',
            'Clearance    0.2      mm',
        ]
    )

    tables = SimpleTableExtractorAdapter().extract(page_text, page_number=2)
    assert tables
    assert 'Parameter | Value | Unit' in tables[0].raw_text
