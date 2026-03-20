#!/usr/bin/env python3
"""Automated tests for PDF parser and store name normalization."""

import sys
import os
from pathlib import Path

# Ensure imports work
sys.path.insert(0, str(Path(__file__).parent))

import pytest
import pandas as pd

from store_matching import clean_store_name, normalize_store
from pdf_parser import (
    parse_pdf, extract_header_total, fix_merged_uom_amount,
    _join_fragmented_cells, resolve_empty_locations, _is_total_row,
)

PDF_DIR = Path("/Users/patriciacorpuz/Downloads")


# ─── Store Name Normalization Tests ──────────────────────────────────────────

class TestNormalizeStore:
    def test_standard_filename(self):
        assert normalize_store("ABC-CYBER-BAR") == "ABC-CYBER-BAR"

    def test_type_code_f(self):
        assert normalize_store("ABC-(F) NUSTAR-BAR") == "ABC-NUSTAR-BAR"

    def test_type_code_cs(self):
        assert normalize_store("ABC-(CS) AYALA-BAR") == "ABC-AYALA-BAR"

    def test_tcs_alias(self):
        assert normalize_store("TCS-MAHI-KITCHEN") == "ABC-MAHI-KITCHEN"

    def test_tcs_alias_bar(self):
        assert normalize_store("TCS-MANDANI-BAR") == "ABC-MANDANI-BAR"

    def test_trailing_fs(self):
        assert normalize_store("TCS MAHI FS") == "ABC-MAHI"

    def test_parenthetical_suffix(self):
        result = normalize_store("ABC-(CS) AYALA-BAR (CS 2)")
        assert "CS 2" not in result
        assert result == "ABC-AYALA-BAR"

    def test_date_suffix_stripped(self):
        result = normalize_store("ABC-ZONE-BAR - 03_15_26")
        assert result == "ABC-ZONE-BAR"


class TestCleanStoreName:
    def test_standard_date_strip(self):
        assert clean_store_name("ABC-CYBER-BAR - 03_15_26") == "ABC-CYBER-BAR"

    def test_type_code_preserved(self):
        # clean_store_name preserves type codes (only strips dates)
        assert clean_store_name("ABC-(F) NUSTAR-BAR - 03_15_26") == "ABC-(F) NUSTAR-BAR"

    def test_sys_ops_prefix_bar(self):
        result = clean_store_name("SYS_OPS_ABC-BLOC_2025_03_2.26 - PICK LIST-BAR - 2026-03-19T013558.224")
        assert result == "ABC-BLOC-BAR"

    def test_sys_ops_prefix_kitchen(self):
        result = clean_store_name("SYS_OPS_ABC-BLOC_2025_03_2.26 - PICK LIST-KITCHEN")
        assert result == "ABC-BLOC-KITCHEN"

    def test_duplicate_marker(self):
        result = clean_store_name("ABC-ZONE-BAR - 03_15_26 (1)")
        assert result == "ABC-ZONE-BAR"

    def test_cs_suffix_stripped(self):
        result = clean_store_name("ABC-AYALA-BAR (CS 2)")
        assert result == "ABC-AYALA-BAR"


# ─── Parser Function Tests ──────────────────────────────────────────────────

class TestFixMergedUomAmount:
    def test_merged_sheet_amount(self):
        uom, amt, days = fix_merged_uom_amount("SHEET50.00", "3", "")
        assert uom == "SHEET"
        assert amt == "50.00"
        assert days == "3"

    def test_merged_rolls_amount(self):
        uom, amt, days = fix_merged_uom_amount("ROLLS102.00", "5", "")
        assert uom == "ROLLS"
        assert amt == "102.00"

    def test_split_across_columns(self):
        uom, amt, days = fix_merged_uom_amount("SHEE", "T50.00", "3")
        assert uom == "SHEET"
        assert amt == "50.00"

    def test_normal_no_merge(self):
        uom, amt, days = fix_merged_uom_amount("KG", "100.00", "5")
        assert uom == "KG"
        assert amt == "100.00"
        assert days == "5"


class TestJoinFragmentedCells:
    def test_second_floor_split(self):
        row = ['SECOND FLOO', 'R 20196', '1', 'ITEM', 'KG', '100.00', '5']
        result = _join_fragmented_cells(row)
        assert result[0] == 'SECOND FLOOR'
        assert result[1] == '20196'

    def test_no_fragmentation(self):
        row = ['CHILLER', '20014', '1', 'ITEM', 'KG', '100.00', '5']
        result = _join_fragmented_cells(row)
        assert result == row


class TestIsTotalRow:
    def test_total_item(self):
        assert _is_total_row({'item': 'TOTAL', 'location': ''}) is True

    def test_subtotal_location(self):
        assert _is_total_row({'item': 'BEEF', 'location': 'SUBTOTAL'}) is True

    def test_normal_row(self):
        assert _is_total_row({'item': 'CHICKEN BREAST', 'location': 'CHILLER'}) is False


class TestExtractHeaderTotal:
    def test_standard_total(self):
        text = "TOTAL AMOUNT 9,726.35"
        assert extract_header_total(text) == 9726.35

    def test_no_total(self):
        assert extract_header_total("no total here") is None


# ─── Integration Tests (require sample PDFs) ────────────────────────────────

def _load_pdf(filename):
    path = PDF_DIR / filename
    if not path.exists():
        pytest.skip(f"Sample PDF not found: {path}")
    with open(path, "rb") as f:
        return f.read()


class TestMultiPagePDF:
    """NUSTAR-BAR is a 2-page PDF with ~46 items."""

    def test_row_count(self):
        data = _load_pdf("ABC-(F) NUSTAR-BAR - 03_15_26.pdf")
        df, warnings, header_total = parse_pdf(data, "ABC-(F) NUSTAR-BAR - 03_15_26.pdf")
        assert len(df) >= 44, f"Expected >= 44 rows, got {len(df)}"

    def test_total_matches_header(self):
        data = _load_pdf("ABC-(F) NUSTAR-BAR - 03_15_26.pdf")
        df, warnings, header_total = parse_pdf(data, "ABC-(F) NUSTAR-BAR - 03_15_26.pdf")
        assert header_total is not None
        amounts = pd.to_numeric(
            df['Total Amount'].astype(str).str.replace(',', '').str.strip(),
            errors='coerce'
        )
        parsed_total = amounts.sum()
        assert abs(parsed_total - header_total) < 1.0, (
            f"Total mismatch: parsed {parsed_total} vs header {header_total}"
        )

    def test_second_floor_rows_intact(self):
        """SECOND FLOOR rows should have intact location + numeric PLU."""
        data = _load_pdf("ABC-(F) NUSTAR-BAR - 03_15_26.pdf")
        df, _, _ = parse_pdf(data, "ABC-(F) NUSTAR-BAR - 03_15_26.pdf")
        second_floor = df[df['Location'] == 'SECOND FLOOR']
        assert len(second_floor) >= 2, "Should have SECOND FLOOR rows"
        for _, row in second_floor.iterrows():
            plu = str(row['PLU Code']).strip()
            assert plu.isdigit(), f"Non-numeric PLU in SECOND FLOOR row: {plu}"


class TestSinglePagePDF:
    """NUSTAR-KITCHEN is a single-page PDF."""

    def test_all_rows_extracted(self):
        data = _load_pdf("ABC-(F) NUSTAR-KITCHEN - 03_15_26.pdf")
        df, _, header_total = parse_pdf(data, "ABC-(F) NUSTAR-KITCHEN - 03_15_26.pdf")
        assert len(df) >= 25
        assert header_total is not None

    def test_total_matches(self):
        data = _load_pdf("ABC-(F) NUSTAR-KITCHEN - 03_15_26.pdf")
        df, _, header_total = parse_pdf(data, "ABC-(F) NUSTAR-KITCHEN - 03_15_26.pdf")
        amounts = pd.to_numeric(
            df['Total Amount'].astype(str).str.replace(',', '').str.strip(),
            errors='coerce'
        )
        assert abs(amounts.sum() - header_total) < 1.0


class TestAllSamplePDFs:
    """Run against all available sample PDFs."""

    @pytest.fixture
    def all_pdfs(self):
        pdfs = sorted(PDF_DIR.glob("ABC-*.pdf"))
        if not pdfs:
            pytest.skip("No sample PDFs found")
        return pdfs

    def test_all_totals_match(self, all_pdfs):
        for pdf_path in all_pdfs:
            with open(pdf_path, "rb") as f:
                data = f.read()
            df, warnings, header_total = parse_pdf(data, pdf_path.name)
            if header_total is not None and not df.empty:
                amounts = pd.to_numeric(
                    df['Total Amount'].astype(str).str.replace(',', '').str.strip(),
                    errors='coerce'
                )
                parsed = amounts.sum()
                pct_diff = abs(parsed - header_total) / header_total * 100 if header_total > 0 else 0
                assert pct_diff < 0.5, (
                    f"{pdf_path.name}: {pct_diff:.2f}% variance "
                    f"(parsed {parsed:.2f} vs header {header_total:.2f})"
                )

    def test_no_mismatch_warnings(self, all_pdfs):
        for pdf_path in all_pdfs:
            with open(pdf_path, "rb") as f:
                data = f.read()
            _, warnings, _ = parse_pdf(data, pdf_path.name)
            mismatch_warnings = [w for w in warnings if 'mismatch' in w.lower()]
            assert not mismatch_warnings, (
                f"{pdf_path.name} has mismatch warnings: {mismatch_warnings}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
