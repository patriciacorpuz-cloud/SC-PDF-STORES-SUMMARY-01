"""HTML print report generators for pick lists, allocation sheets, and undelivered reports."""

import html
from typing import List, Tuple

import pandas as pd
from config import LOGO_B64


def _esc(val) -> str:
    """Escape a value for safe HTML interpolation."""
    return html.escape(str(val)) if val is not None else ""


def _print_header_html(report_label: str, meta_rows: List[Tuple]) -> str:
    """Shared branded header for all print reports.
    meta_rows: list of (label, value, highlight) tuples.
    """
    logo_tag = (
        f'<img src="data:image/png;base64,{LOGO_B64}" class="logo" alt="The Abaca Group">'
        if LOGO_B64 else
        '<div class="logo-text">THE ABACA GROUP</div>'
    )
    meta_html = "".join(
        f'<tr><td class="ml">{lbl}</td>'
        f'<td class="mv{"h" if hi else ""}">{val}</td></tr>'
        for lbl, val, hi in meta_rows
    )
    return f"""
<div class="brand-header">
  <div class="brand-left">
    {logo_tag}
    <div class="brand-sub">Supply Chain · Commissary</div>
  </div>
  <div class="brand-right">
    <div class="report-label">{report_label}</div>
    <table class="meta-table">{meta_html}</table>
  </div>
</div>
<div class="gold-rule"></div>
"""


def _print_base_css() -> str:
    return """
  * { box-sizing: border-box; }
  body {
    font-family: 'Arial', sans-serif;
    font-size: 10pt;
    color: #1a1a1a;
    background: #ffffff;
    margin: 18mm 16mm 14mm 16mm;
  }
  /* ── Branded header ── */
  .brand-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding-bottom: 8px;
  }
  .brand-left { display: flex; flex-direction: column; justify-content: center; }
  .logo {
    height: 38px;
    width: auto;
    filter: invert(1) brightness(0);   /* white PNG → solid black */
  }
  .logo-text {
    font-size: 13pt;
    font-weight: 700;
    letter-spacing: 0.12em;
    color: #1a1a1a;
  }
  .brand-sub {
    font-size: 7.5pt;
    color: #777;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-top: 3px;
  }
  .brand-right { text-align: right; }
  .report-label {
    font-size: 15pt;
    font-weight: 700;
    letter-spacing: 0.06em;
    color: #1a1a1a;
    text-transform: uppercase;
  }
  .meta-table { margin-top: 4px; border-collapse: collapse; margin-left: auto; }
  .meta-table td { padding: 1px 6px; font-size: 8.5pt; }
  .ml { font-weight: 600; color: #555; text-align: right; }
  .mv { font-weight: 500; color: #1a1a1a; }
  .mvh { font-weight: 700; color: #b5821a; }   /* highlight = gold-ish */
  /* ── Gold rule ── */
  .gold-rule {
    height: 2.5px;
    background: #C9A96E;
    margin-bottom: 10px;
  }
  /* ── Data tables ── */
  table.data {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 14px;
    font-size: 9pt;
  }
  table.data th {
    background: #1a1a1a;
    color: #ffffff;
    border: 1px solid #1a1a1a;
    padding: 5px 8px;
    text-align: left;
    font-size: 8.5pt;
    letter-spacing: 0.04em;
  }
  table.data td {
    border: 1px solid #d0d0d0;
    padding: 4px 8px;
    vertical-align: middle;
  }
  table.data tbody tr:nth-child(even) td { background: #f7f5f2; }
  /* ── Summary / totals ── */
  .summary-section-header td {
    background: #f0ebe2;
    border: 1px solid #C9A96E;
    font-weight: 700;
    font-size: 8.5pt;
    padding: 5px 8px;
    letter-spacing: 0.04em;
    color: #7a5c1e;
  }
  .total-row td {
    background: #f0ebe2;
    border: 1px solid #C9A96E;
    font-weight: 700;
    color: #7a5c1e;
  }
  /* ── Footer ── */
  .print-footer {
    margin-top: 12px;
    padding-top: 5px;
    border-top: 1px solid #ddd;
    font-size: 7.5pt;
    color: #aaa;
    display: flex;
    justify-content: space-between;
  }
  /* ── Print button (screen only) ── */
  .print-btn {
    display: inline-block;
    margin-top: 14px;
    padding: 8px 24px;
    font-size: 10.5pt;
    cursor: pointer;
    background: #1a1a1a;
    color: #C9A96E;
    border: 1.5px solid #C9A96E;
    border-radius: 4px;
    font-weight: 600;
    letter-spacing: 0.04em;
  }
  @media print {
    body { margin: 10mm 12mm; }
    .print-btn { display: none; }
  }
"""


def make_picklist_html(df_loc: pd.DataFrame, location: str, delivery_date: str,
                       ordered_by: str = "") -> str:
    """Generates a branded print-ready Picklist. P2-K: Now includes PLU Code."""

    df_sorted = df_loc.sort_values(['Item Description', 'Store'])

    detail_rows_html = ""
    for _, r in df_sorted.iterrows():
        detail_rows_html += f"""
        <tr>
          <td>{_esc(r['Store'])}</td>
          <td style="font-size:8pt; color:#888;">{_esc(r.get('PLU Code', ''))}</td>
          <td>{_esc(r['Item Description'])}</td>
          <td style="text-align:center;">{int(r['Order Qty']) if pd.notna(r['Order Qty']) else '-'}</td>
        </tr>"""

    summary = (
        df_loc.groupby('Item Description')['Order Qty']
        .sum().reset_index()
        .sort_values('Item Description')
    )
    summary_rows_html = ""
    for _, r in summary.iterrows():
        summary_rows_html += f"""
        <tr>
          <td>{_esc(r['Item Description'])}</td>
          <td></td>
          <td></td>
          <td style="text-align:center;">{int(r['Order Qty']) if pd.notna(r['Order Qty']) else '-'}</td>
        </tr>"""

    meta_rows = [
        ("Delivery Date:", _esc(delivery_date), True),
        ("Location:", _esc(location), False),
        ("Total Lines:", str(len(df_sorted)), False),
    ]
    if ordered_by:
        meta_rows.append(("Ordered By:", _esc(ordered_by), False))

    header = _print_header_html(f"{_esc(location)} — PICK LIST", meta_rows)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{_esc(location)} PICKLIST</title>
<style>{_print_base_css()}</style>
</head>
<body>
{header}
<table class="data">
  <thead>
    <tr>
      <th>STORE NAME</th>
      <th style="width:60px;">PLU</th>
      <th>ITEM DESCRIPTION</th>
      <th style="text-align:center; width:70px;">QTY</th>
    </tr>
  </thead>
  <tbody>
    {detail_rows_html}
  </tbody>
</table>

<table class="data">
  <thead>
    <tr class="summary-section-header">
      <td colspan="4">SUMMARY QTY</td>
    </tr>
    <tr>
      <th>ITEM DESCRIPTION</th>
      <th></th>
      <th></th>
      <th style="text-align:center; width:70px;">TOTAL QTY</th>
    </tr>
  </thead>
  <tbody>
    {summary_rows_html}
  </tbody>
</table>

<div class="print-footer">
  <span>SC_PDF STORES SUMMARY_01 · The Abaca Group</span>
  <span>Pick List · {_esc(location)}</span>
</div>
<button class="print-btn" onclick="window.print()">🖨&nbsp; Print</button>
</body>
</html>"""


def make_allocation_html(df_item: pd.DataFrame, item_name: str, delivery_date: str) -> str:
    """Generates a branded print-ready Item Allocation sheet."""

    store_summary = (
        df_item.groupby('Store')['Order Qty']
        .sum().reset_index()
        .sort_values('Store')
    )
    total_qty = int(store_summary['Order Qty'].sum()) if not store_summary.empty else 0

    rows_html = ""
    for _, r in store_summary.iterrows():
        rows_html += f"""
        <tr>
          <td>{_esc(r['Store'])}</td>
          <td style="text-align:center;">{int(r['Order Qty']) if pd.notna(r['Order Qty']) else '-'}</td>
        </tr>"""

    uom_vals = df_item['UOM'].dropna().unique()
    uom = uom_vals[0] if len(uom_vals) > 0 else ""

    header = _print_header_html(
        f"{_esc(item_name)} — ORDER",
        [
            ("Delivery Date:", _esc(delivery_date), True),
            ("UOM:", _esc(uom), False),
            ("Total Stores:", str(len(store_summary)), False),
            ("Total Qty:", str(total_qty), False),
        ]
    )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{_esc(item_name)} — ORDER</title>
<style>
{_print_base_css()}
  body {{ max-width: 520px; }}
</style>
</head>
<body>
{header}
<table class="data">
  <thead>
    <tr>
      <th>STORE NAME</th>
      <th style="text-align:center; width:90px;">QTY</th>
    </tr>
  </thead>
  <tbody>
    {rows_html}
    <tr class="total-row">
      <td><b>TOTAL</b></td>
      <td style="text-align:center;"><b>{total_qty}</b></td>
    </tr>
  </tbody>
</table>

<div class="print-footer">
  <span>SC_PDF STORES SUMMARY_01 · The Abaca Group</span>
  <span>Item Allocation · {_esc(item_name)}</span>
</div>
<button class="print-btn" onclick="window.print()">🖨&nbsp; Print</button>
</body>
</html>"""


def make_undelivered_html(rows: list, report_title: str, order_date: str,
                          delivery_date: str, prepared_by: str) -> str:
    """Generates a print-ready Undelivered Report with merged remarks cells (rowspan)."""

    # Sort rows by remarks so same-remark rows are grouped together
    sorted_rows = sorted(rows, key=lambda r: (r.get('remarks', '') or ''))

    # Pre-compute rowspans for the REMARKS column
    rowspan_map = {}   # index → rowspan count (only set for first row of a group)
    i = 0
    while i < len(sorted_rows):
        remark = sorted_rows[i].get('remarks', '') or ''
        span = 1
        j = i + 1
        while j < len(sorted_rows) and (sorted_rows[j].get('remarks', '') or '') == remark:
            span += 1
            j += 1
        rowspan_map[i] = span
        i = j

    # Build HTML rows
    tr_html = ""
    skip_remarks = set()   # indices where we suppress the remarks cell (already merged)
    for idx, r in enumerate(sorted_rows):
        remarks_cell = ""
        if idx not in skip_remarks:
            span = rowspan_map.get(idx, 1)
            remark_val = r.get('remarks', '') or ''
            rs_attr = f' rowspan="{span}"' if span > 1 else ''
            cls = ' class="remarks-cell"' if remark_val else ''
            remarks_cell = f'<td{rs_attr}{cls}>{_esc(remark_val)}</td>'
            # Mark subsequent rows in this group to skip the remarks cell
            for k in range(idx + 1, idx + span):
                skip_remarks.add(k)

        tr_html += f"""
        <tr>
          <td>{_esc(delivery_date)}</td>
          <td>{_esc(r['store'])}</td>
          <td>{_esc(r['item'])}</td>
          <td style="text-align:center;">{_esc(r['qty'])}</td>
          {remarks_cell}
        </tr>"""

    header = _print_header_html(
        _esc(report_title),
        [
            ("Order Date:", _esc(order_date), False),
            ("Delivery Date:", _esc(delivery_date), True),
            ("Prepared by:", _esc(prepared_by.upper()), False),
            ("Total Items:", str(len(sorted_rows)), False),
        ]
    )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{_esc(report_title)}</title>
<style>
{_print_base_css()}
  /* Remarks cell styling */
  table.data td.remarks-cell {{
    background: #fdf8ee;
    border-left: 3px solid #C9A96E;
    font-weight: 600;
    font-style: italic;
    color: #7a5c1e;
    vertical-align: middle;
  }}
</style>
</head>
<body>
{header}

<table class="data">
  <thead>
    <tr>
      <th style="width:90px;">DATE</th>
      <th>STORE NAME</th>
      <th>ITEM DESCRIPTION</th>
      <th style="text-align:center; width:55px;">QTY</th>
      <th style="width:200px;">REMARKS</th>
    </tr>
  </thead>
  <tbody>
    {tr_html}
  </tbody>
</table>

<div class="print-footer">
  <span>SC_PDF STORES SUMMARY_01 · The Abaca Group Supply Chain</span>
  <span>Undelivered Report · {_esc(delivery_date)}</span>
</div>

<button class="print-btn" onclick="window.print()">🖨&nbsp; Print</button>
</body>
</html>"""
