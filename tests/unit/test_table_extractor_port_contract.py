"""Tests for ExtractedTableRow / ExtractedTable dataclass contracts (Phase 1 #3)."""
from __future__ import annotations

import pytest

from packages.ports.table_extractor_port import ExtractedTable, ExtractedTableRow


class TestExtractedTableRowContract:
    def test_all_required_fields_present(self) -> None:
        row = ExtractedTableRow(
            table_id='tbl_doc1_1_000',
            page_number=1,
            row_index=0,
            headers=['Parameter', 'Value', 'Unit'],
            row_cells=['Speed', '1450', 'rpm'],
            units=['', '', 'rpm'],
            raw_text='Speed  1450  rpm',
        )
        assert row.table_id == 'tbl_doc1_1_000'
        assert row.page_number == 1
        assert row.row_index == 0
        assert row.headers == ['Parameter', 'Value', 'Unit']
        assert row.row_cells == ['Speed', '1450', 'rpm']
        assert row.units == ['', '', 'rpm']
        assert row.raw_text == 'Speed  1450  rpm'

    def test_units_length_equals_row_cells_length(self) -> None:
        row = ExtractedTableRow(
            table_id='tbl_x',
            page_number=2,
            row_index=1,
            headers=[],
            row_cells=['A', 'B', 'C', 'D'],
            units=['', 'Hz', '', 'V'],
            raw_text='A  B  C  D',
        )
        assert len(row.units) == len(row.row_cells)

    def test_immutability(self) -> None:
        row = ExtractedTableRow(
            table_id='t', page_number=1, row_index=0,
            headers=[], row_cells=['x'], units=[''], raw_text='x',
        )
        with pytest.raises(AttributeError):
            row.row_index = 99  # type: ignore[misc]

    def test_empty_headers_allowed(self) -> None:
        row = ExtractedTableRow(
            table_id='t', page_number=1, row_index=0,
            headers=[], row_cells=['data'], units=[''],
            raw_text='data',
        )
        assert row.headers == []


class TestExtractedTableContract:
    def test_table_holds_rows(self) -> None:
        row = ExtractedTableRow(
            table_id='tbl_d_1_000', page_number=1, row_index=0,
            headers=[], row_cells=['x'], units=[''], raw_text='x',
        )
        table = ExtractedTable(table_id='tbl_d_1_000', page_number=1, rows=[row])
        assert len(table.rows) == 1
        assert table.rows[0] is row

    def test_default_rows_is_empty_list(self) -> None:
        table = ExtractedTable(table_id='t', page_number=1)
        assert table.rows == []

    def test_raw_text_defaults_empty(self) -> None:
        table = ExtractedTable(table_id='t', page_number=1)
        assert table.raw_text == ''
