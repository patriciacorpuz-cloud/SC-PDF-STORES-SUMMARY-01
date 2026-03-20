"""PDF generation functions extracted from app.py.

Uses fpdf2 to generate print-ready PDF reports for:
- Combined report (undelivered + unavailable + manual orders)
- Multi-item allocation report
"""

from typing import Optional, List, Dict
from collections import defaultdict

from config import _LOGO_PATH


def _safe(text: str) -> str:
    """Sanitize text for fpdf2's built-in fonts (latin-1 only).
    Replace common Unicode chars with ASCII equivalents.
    """
    replacements = {
        '\u2014': '-', '\u2013': '-',  # em/en dash
        '\u2018': "'", '\u2019': "'",  # smart quotes
        '\u201c': '"', '\u201d': '"',
        '\u2026': '...', '\u00a0': ' ',
        '\u2022': '*', '\u00b7': '*',
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    # Drop any remaining non-latin1 chars
    return text.encode('latin-1', errors='replace').decode('latin-1')


def _generate_combined_pdf(
    unavailable_items: List[Dict],
    manual_orders: List[Dict],
    report_title: str,
    order_date: str,
    delivery_date: str,
    prepared_by: str,
    undelivered_rows: Optional[List[Dict]] = None,
) -> bytes:
    """Generate a print-ready PDF combining undelivered items, unavailable items, and manual orders.
    Uses fpdf2. Returns PDF bytes.
    """
    from fpdf import FPDF

    class ReportPDF(FPDF):
        def header(self):
            # Logo if available
            if _LOGO_PATH.exists():
                try:
                    self.image(str(_LOGO_PATH), 10, 8, 25)
                except Exception:
                    pass
            self.set_font("Helvetica", "B", 14)
            self.cell(0, 8, _safe(report_title), new_x="LMARGIN", new_y="NEXT", align="R")
            self.set_font("Helvetica", "", 8)
            self.set_text_color(100, 100, 100)
            meta = f"Order Date: {order_date}   |   Delivery Date: {delivery_date}   |   Prepared By: {prepared_by.upper()}"
            self.cell(0, 5, _safe(meta), new_x="LMARGIN", new_y="NEXT", align="R")
            self.set_text_color(0, 0, 0)
            # Gold rule
            self.set_draw_color(201, 169, 110)
            self.set_line_width(0.8)
            self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
            self.ln(6)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 7)
            self.set_text_color(160, 160, 160)
            self.cell(0, 10, f"SC_PDF STORES SUMMARY \u00b7 The Abaca Group \u00b7 Page {self.page_no()}/{{nb}}", align="C")

    pdf = ReportPDF(orientation="P", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # ── Section 0: Undelivered Rows (row-by-row from Undelivered Report) ─────
    if undelivered_rows:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(26, 26, 26)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, "  UNDELIVERED ITEMS", new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(3)

        # Group by item, then show stores per item
        ud_grouped = defaultdict(list)
        ud_remarks_map = {}
        for row in undelivered_rows:
            item = row.get("item", "")
            ud_grouped[item].append(row)
            if row.get("remarks"):
                ud_remarks_map[item] = row["remarks"]

        col_w = [90, 30, 40]
        headers = ["STORE", "QTY", "REMARKS"]

        for item_name, rows in ud_grouped.items():
            if pdf.get_y() > 250:
                pdf.add_page()

            pdf.set_font("Helvetica", "B", 10)
            pdf.set_fill_color(240, 235, 226)
            pdf.set_draw_color(201, 169, 110)
            pdf.cell(0, 7, _safe(f"  {item_name}"), new_x="LMARGIN", new_y="NEXT", fill=True, border="L")
            pdf.set_draw_color(0, 0, 0)

            if item_name in ud_remarks_map:
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(122, 92, 30)
                pdf.cell(0, 5, _safe(f"  Remarks: {ud_remarks_map[item_name]}"), new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(0, 0, 0)

            # Table header
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_fill_color(240, 240, 240)
            for i, h in enumerate(headers):
                pdf.cell(col_w[i], 6, h, border=1, fill=True, align="C")
            pdf.ln()

            pdf.set_font("Helvetica", "", 8)
            for r in rows:
                if pdf.get_y() > 270:
                    pdf.add_page()
                pdf.cell(col_w[0], 5.5, _safe(f"  {r.get('store', '')}"), border=1)
                pdf.cell(col_w[1], 5.5, str(r.get("qty", "")), border=1, align="C")
                pdf.cell(col_w[2], 5.5, _safe(r.get("remarks", "")), border=1, align="C")
                pdf.ln()

            pdf.ln(4)

    # ── Section 1: Unavailable Items ──────────────────────────────────────────
    if unavailable_items:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(26, 26, 26)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, "  ITEMS NOT AVAILABLE TODAY", new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(3)

        for entry in unavailable_items:
            item_name = entry.get("item", "")
            remarks = entry.get("remarks", "")
            stores = entry.get("stores", [])

            # Check if we need a new page (at least 30mm needed for item header + a few rows)
            if pdf.get_y() > 250:
                pdf.add_page()

            # Item name header
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_fill_color(240, 235, 226)
            pdf.set_draw_color(201, 169, 110)
            pdf.cell(0, 7, _safe(f"  {item_name}"), new_x="LMARGIN", new_y="NEXT", fill=True, border="L")
            pdf.set_draw_color(0, 0, 0)

            if remarks:
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(122, 92, 30)
                pdf.cell(0, 5, _safe(f"  Remarks: {remarks}"), new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(0, 0, 0)

            # Table header
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_fill_color(240, 240, 240)
            col_w = [90, 30, 40]
            headers = ["STORE", "QTY", "UOM"]
            for i, h in enumerate(headers):
                pdf.cell(col_w[i], 6, h, border=1, fill=True, align="C")
            pdf.ln()

            # Table rows
            pdf.set_font("Helvetica", "", 8)
            for s in stores:
                if pdf.get_y() > 270:
                    pdf.add_page()
                    # Re-draw item context on new page
                    pdf.set_font("Helvetica", "B", 9)
                    pdf.cell(0, 6, _safe(f"  {item_name} (continued)"), new_x="LMARGIN", new_y="NEXT")
                    pdf.set_font("Helvetica", "B", 8)
                    pdf.set_fill_color(240, 240, 240)
                    for i, h in enumerate(headers):
                        pdf.cell(col_w[i], 6, h, border=1, fill=True, align="C")
                    pdf.ln()
                    pdf.set_font("Helvetica", "", 8)

                pdf.cell(col_w[0], 5.5, _safe(f"  {s.get('store', '')}"), border=1)
                pdf.cell(col_w[1], 5.5, str(s.get("qty", "")), border=1, align="C")
                pdf.cell(col_w[2], 5.5, _safe(s.get("uom", "")), border=1, align="C")
                pdf.ln()

            pdf.ln(4)

    # ── Section 2: Manual Orders ──────────────────────────────────────────────
    if manual_orders:
        if pdf.get_y() > 240:
            pdf.add_page()

        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(26, 26, 26)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 8, "  MANUAL ORDERS", new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(3)

        # Group manual orders by item
        mo_grouped = defaultdict(list)
        mo_remarks = {}
        for mo in manual_orders:
            mo_grouped[mo["item"]].append(mo)
            if mo.get("remarks"):
                mo_remarks[mo["item"]] = mo["remarks"]

        for item_name, entries in mo_grouped.items():
            if pdf.get_y() > 250:
                pdf.add_page()

            pdf.set_font("Helvetica", "B", 10)
            pdf.set_fill_color(240, 235, 226)
            pdf.set_draw_color(201, 169, 110)
            pdf.cell(0, 7, _safe(f"  {item_name}"), new_x="LMARGIN", new_y="NEXT", fill=True, border="L")
            pdf.set_draw_color(0, 0, 0)

            if item_name in mo_remarks:
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(122, 92, 30)
                pdf.cell(0, 5, _safe(f"  Remarks: {mo_remarks[item_name]}"), new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(0, 0, 0)

            # Table
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_fill_color(240, 240, 240)
            col_w = [90, 30, 40]
            headers = ["STORE", "QTY", "UOM"]
            for i, h in enumerate(headers):
                pdf.cell(col_w[i], 6, h, border=1, fill=True, align="C")
            pdf.ln()

            pdf.set_font("Helvetica", "", 8)
            for e in entries:
                if pdf.get_y() > 270:
                    pdf.add_page()
                pdf.cell(col_w[0], 5.5, _safe(f"  {e.get('store', '')}"), border=1)
                pdf.cell(col_w[1], 5.5, str(e.get("qty", "")), border=1, align="C")
                pdf.cell(col_w[2], 5.5, _safe(e.get("uom", "")), border=1, align="C")
                pdf.ln()

            pdf.ln(4)

    # If all empty, show a message
    if not undelivered_rows and not unavailable_items and not manual_orders:
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 10, "No items to report.", new_x="LMARGIN", new_y="NEXT", align="C")

    return bytes(pdf.output())


def _generate_multi_allocation_pdf(
    items_data: List[Dict],
    delivery_date: str,
) -> bytes:
    """Generate a combined allocation PDF for multiple items.
    items_data: list of {item, uom, total_qty, stores: [{store, qty}]}
    Each item gets its own section with a page break between items.
    """
    from fpdf import FPDF

    class AllocPDF(FPDF):
        def header(self):
            if _LOGO_PATH.exists():
                try:
                    self.image(str(_LOGO_PATH), 10, 8, 25)
                except Exception:
                    pass
            self.set_font("Helvetica", "B", 13)
            self.cell(0, 8, "COMBINED ALLOCATION REPORT", new_x="LMARGIN", new_y="NEXT", align="R")
            self.set_font("Helvetica", "", 8)
            self.set_text_color(100, 100, 100)
            self.cell(0, 5, _safe(f"Delivery Date: {delivery_date}   |   Items: {len(items_data)}"),
                      new_x="LMARGIN", new_y="NEXT", align="R")
            self.set_text_color(0, 0, 0)
            self.set_draw_color(201, 169, 110)
            self.set_line_width(0.8)
            self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
            self.ln(6)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 7)
            self.set_text_color(160, 160, 160)
            self.cell(0, 10, f"SC_PDF STORES SUMMARY - The Abaca Group - Page {self.page_no()}/{{nb}}", align="C")

    pdf = AllocPDF(orientation="P", unit="mm", format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    for idx, item in enumerate(items_data):
        pdf.add_page()

        item_name = item["item"]
        uom = item.get("uom", "")
        total_qty = item.get("total_qty", 0)
        stores = item.get("stores", [])

        # Item title bar
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_fill_color(240, 235, 226)
        pdf.set_draw_color(201, 169, 110)
        pdf.cell(0, 9, _safe(f"  {item_name}"), new_x="LMARGIN", new_y="NEXT", fill=True, border="L")
        pdf.set_draw_color(0, 0, 0)

        # Meta line
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 5, _safe(f"  UOM: {uom}   |   Total Qty: {total_qty}   |   Stores: {len(stores)}"),
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

        # Table header
        col_w = [120, 40]
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(26, 26, 26)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(col_w[0], 7, "  STORE", border=1, fill=True)
        pdf.cell(col_w[1], 7, "QTY", border=1, fill=True, align="C")
        pdf.ln()
        pdf.set_text_color(0, 0, 0)

        # Table rows
        pdf.set_font("Helvetica", "", 9)
        for i, s in enumerate(stores):
            if i % 2 == 0:
                pdf.set_fill_color(247, 245, 242)
            else:
                pdf.set_fill_color(255, 255, 255)
            pdf.cell(col_w[0], 6, _safe(f"  {s['store']}"), border=1, fill=True)
            pdf.cell(col_w[1], 6, str(s["qty"]), border=1, fill=True, align="C")
            pdf.ln()

        # Total row
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(240, 235, 226)
        pdf.cell(col_w[0], 7, "  TOTAL", border=1, fill=True)
        pdf.cell(col_w[1], 7, str(total_qty), border=1, fill=True, align="C")
        pdf.ln()

    return bytes(pdf.output())
