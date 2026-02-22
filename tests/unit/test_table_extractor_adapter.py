"""Tests for SimpleTableExtractorAdapter (Phase 1 #3)."""
from __future__ import annotations

import pytest

from packages.adapters.tables.simple_table_extractor_adapter import SimpleTableExtractorAdapter
from packages.ports.table_extractor_port import ExtractedTable, ExtractedTableRow


@pytest.fixture()
def adapter() -> SimpleTableExtractorAdapter:
    return SimpleTableExtractorAdapter()


class TestExtractReturnsStructuredRows:
    def test_returns_list_of_extracted_tables(self, adapter: SimpleTableExtractorAdapter) -> None:
        text = "Parameter  Value  Unit\nSpeed      1450   rpm\nVoltage    400    V"
        result = adapter.extract(text, page_number=1, doc_id='doc1')
        assert isinstance(result, list)
        assert len(result) >= 1
        assert isinstance(result[0], ExtractedTable)

    def test_extract_returns_rows_with_headers(self, adapter: SimpleTableExtractorAdapter) -> None:
        """Header row detected when >= 50% cells are non-numeric short strings."""
        text = "Parameter  Value  Unit\nSpeed      1450   rpm\nVoltage    400    V"
        tables = adapter.extract(text, page_number=1, doc_id='doc1')
        assert tables, "Expected at least one table"
        rows = tables[0].rows
        assert len(rows) >= 1
        # Headers should come from the first row
        assert rows[0].headers == ['Parameter', 'Value', 'Unit']

    def test_row_cells_populated(self, adapter: SimpleTableExtractorAdapter) -> None:
        text = "Parameter  Value  Unit\nSpeed      1450   rpm"
        tables = adapter.extract(text, page_number=1, doc_id='doc1')
        rows = tables[0].rows
        assert rows[0].row_cells == ['Speed', '1450', 'rpm']

    def test_pipe_delimited_table(self, adapter: SimpleTableExtractorAdapter) -> None:
        text = "| Name     | Value | Unit |\n| Speed    | 1450  | rpm  |\n| Voltage  | 400   | V    |"
        tables = adapter.extract(text, page_number=2, doc_id='doc1')
        assert tables
        # All rows should have cells
        for row in tables[0].rows:
            assert len(row.row_cells) >= 1

    def test_units_extracted_from_parentheses(self, adapter: SimpleTableExtractorAdapter) -> None:
        """Units like (rpm) or (V) extracted from row_cells."""
        text = "Param        Nominal  Max\nShaft speed  1450 (rpm)  1800 (rpm)\nPower        5.5 (kW)    7.5 (kW)"
        tables = adapter.extract(text, page_number=1, doc_id='doc1')
        assert tables
        rows = tables[0].rows
        # At least one row should have a non-empty unit
        all_units = [u for row in rows for u in row.units]
        assert any(u != '' for u in all_units), "Expected at least one unit extracted"

    def test_units_length_equals_row_cells_length(self, adapter: SimpleTableExtractorAdapter) -> None:
        text = "Param  Value  Unit\nSpeed  1450   rpm\nPower  5.5    kW"
        tables = adapter.extract(text, page_number=1, doc_id='doc1')
        for table in tables:
            for row in table.rows:
                assert len(row.units) == len(row.row_cells), \
                    f"units length {len(row.units)} != row_cells length {len(row.row_cells)}"

    def test_table_id_includes_doc_id(self, adapter: SimpleTableExtractorAdapter) -> None:
        text = "A  B  C\n1  2  3\n4  5  6"
        tables = adapter.extract(text, page_number=5, doc_id='siemens_g120')
        assert tables
        assert 'siemens_g120' in tables[0].table_id

    def test_row_index_sequential_from_zero(self, adapter: SimpleTableExtractorAdapter) -> None:
        text = "Header1  Header2\nRow1A    Row1B\nRow2A    Row2B\nRow3A    Row3B"
        tables = adapter.extract(text, page_number=1, doc_id='doc1')
        assert tables
        for expected_idx, row in enumerate(tables[0].rows):
            assert row.row_index == expected_idx

    def test_empty_page_returns_empty_list(self, adapter: SimpleTableExtractorAdapter) -> None:
        assert adapter.extract('', page_number=1, doc_id='doc1') == []
        assert adapter.extract('   \n  ', page_number=1, doc_id='doc1') == []

    def test_fallback_single_row_on_unparseable_input(self, adapter: SimpleTableExtractorAdapter) -> None:
        """When row parsing yields no data rows, emit one fallback row."""
        # Two identical lines that trigger group detection but parse to empty cells
        text = "abc\nabc"
        tables = adapter.extract(text, page_number=1, doc_id='doc1')
        if tables:
            # If a table was detected, must have at least one row
            assert len(tables[0].rows) >= 1

    def test_raw_text_preserved_on_table(self, adapter: SimpleTableExtractorAdapter) -> None:
        text = "H1  H2  H3\nA   B   C\nD   E   F"
        tables = adapter.extract(text, page_number=1, doc_id='doc1')
        assert tables
        assert tables[0].raw_text != ''

    def test_no_doc_id_uses_legacy_table_id_format(self, adapter: SimpleTableExtractorAdapter) -> None:
        text = "A  B  C\n1  2  3\n4  5  6"
        tables = adapter.extract(text, page_number=3)
        assert tables
        assert tables[0].table_id.startswith('table-p')
