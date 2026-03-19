import streamlit as st
import pdfplumber
import pandas as pd
import re
import io
import json
import base64
import os
from pathlib import Path
from collections import Counter
import plotly.graph_objects as go

# ─── LOGO (embedded for print reports) ─────────────────────────────────────────
_LOGO_PATH = Path(__file__).parent / "assets" / "tag_logo.png"
try:
    with open(_LOGO_PATH, "rb") as _f:
        LOGO_B64 = base64.b64encode(_f.read()).decode()
except Exception:
    LOGO_B64 = ""

# ─── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SC_PDF STORES SUMMARY_01",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── DESIGN TOKENS ─────────────────────────────────────────────────────────────
GOLD   = "#C9A96E"
DARK   = "#0D0D0D"
CARD   = "#141414"
BORDER = "#2A2A2A"
TEXT   = "#F0EDE8"
MUTED  = "#888880"
GREEN  = "#4CAF50"
RED    = "#E53935"


st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Jost:wght@300;400;500;600;700&family=Manrope:wght@300;400;500;600;700&display=swap');

  html, body, [class*="css"] {{
    font-family: 'Jost', sans-serif !important;
    background-color: {DARK};
    color: {TEXT};
  }}
  section[data-testid="stSidebar"] {{
    background-color: #0A0A0A !important;
    border-right: 1px solid {BORDER};
  }}
  section[data-testid="stSidebar"] * {{ font-family: 'Jost', sans-serif !important; }}

  .abaca-header {{
    display: flex; align-items: center; gap: 16px;
    border-bottom: 1px solid {BORDER};
    padding-bottom: 20px; margin-bottom: 24px;
  }}
  .abaca-wordmark {{
    font-family: 'Manrope', sans-serif;
    font-size: 0.65rem; font-weight: 600;
    letter-spacing: 0.25em; text-transform: uppercase;
    color: {MUTED}; margin-top: 2px;
  }}
  .abaca-title {{
    font-family: 'Jost', sans-serif;
    font-size: 1.6rem; font-weight: 600;
    color: {TEXT}; letter-spacing: 0.03em; margin: 0;
  }}
  .gold-line {{ width: 36px; height: 2px; background: {GOLD}; margin: 6px 0; }}

  .kpi-row {{ display: flex; gap: 16px; margin-bottom: 28px; }}
  .kpi-card {{
    flex: 1; background: {CARD};
    border: 1px solid {BORDER}; border-left: 3px solid {GOLD};
    border-radius: 4px; padding: 16px 20px;
  }}
  .kpi-label {{
    font-size: 0.65rem; font-weight: 600;
    letter-spacing: 0.15em; text-transform: uppercase;
    color: {MUTED}; margin-bottom: 6px;
  }}
  .kpi-value {{
    font-family: 'Manrope', sans-serif;
    font-size: 1.75rem; font-weight: 700; color: {TEXT};
  }}
  .kpi-sub {{ font-size: 0.72rem; color: {MUTED}; margin-top: 3px; }}

  .section-label {{
    font-size: 0.65rem; font-weight: 600;
    letter-spacing: 0.2em; text-transform: uppercase;
    color: {GOLD}; margin-bottom: 12px;
  }}

  .stDataFrame {{ border: 1px solid {BORDER} !important; border-radius: 4px; }}
  .stDataFrame th {{
    background: #1A1A1A !important; color: {MUTED} !important;
    font-size: 0.65rem !important; letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    font-family: 'Jost', sans-serif !important;
    border-bottom: 1px solid {BORDER} !important;
  }}
  .stDataFrame td {{
    font-size: 0.82rem !important;
    font-family: 'Jost', sans-serif !important;
    border-bottom: 1px solid #1E1E1E !important;
  }}

  .stTabs [data-baseweb="tab-list"] {{
    border-bottom: 1px solid {BORDER} !important;
    gap: 0 !important; background: transparent !important;
  }}
  .stTabs [data-baseweb="tab"] {{
    font-family: 'Jost', sans-serif !important;
    font-size: 0.7rem !important; font-weight: 600 !important;
    letter-spacing: 0.12em !important; text-transform: uppercase !important;
    color: {MUTED} !important; padding: 10px 24px !important;
    border: none !important; border-bottom: 2px solid transparent !important;
    background: transparent !important;
  }}
  .stTabs [aria-selected="true"] {{
    color: {GOLD} !important; border-bottom: 2px solid {GOLD} !important;
  }}

  div[data-testid="stFileUploader"] {{
    border: 1px solid {BORDER} !important;
    border-radius: 4px !important; padding: 8px !important;
    background: {CARD} !important;
  }}

  .stRadio label {{ font-size: 0.78rem !important; }}
  .stMultiSelect [data-baseweb="tag"] {{
    background: rgba(201,169,110,0.15) !important;
    border: 1px solid {GOLD} !important; border-radius: 2px !important;
  }}

  .stButton button, .stDownloadButton button {{
    font-family: 'Jost', sans-serif !important;
    letter-spacing: 0.1em !important; text-transform: uppercase !important;
    font-size: 0.72rem !important; font-weight: 600 !important;
    background: transparent !important;
    border: 1px solid {GOLD} !important;
    color: {GOLD} !important; border-radius: 2px !important;
  }}
  .stButton button:hover, .stDownloadButton button:hover {{
    background: rgba(201,169,110,0.1) !important;
  }}

  /* Print button — stands out */
  .print-btn button {{
    background: rgba(201,169,110,0.15) !important;
    border: 1px solid {GOLD} !important;
    color: {GOLD} !important;
  }}

  /* P2-H: Out-of-stock badge */
  .out-badge {{
    display: inline-block;
    background: rgba(229,57,53,0.15);
    border: 1px solid {RED};
    border-radius: 3px;
    padding: 1px 6px;
    font-size: 0.65rem;
    font-weight: 700;
    color: {RED};
    letter-spacing: 0.08em;
  }}

  hr {{ border-color: {BORDER} !important; margin: 24px 0 !important; }}
  ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
  ::-webkit-scrollbar-track {{ background: {DARK}; }}
  ::-webkit-scrollbar-thumb {{ background: {BORDER}; border-radius: 3px; }}
  ::-webkit-scrollbar-thumb:hover {{ background: {GOLD}; }}

  .info-pill {{
    display: inline-block;
    background: rgba(201,169,110,0.12);
    border: 1px solid rgba(201,169,110,0.3);
    border-radius: 3px;
    padding: 3px 10px;
    font-size: 0.72rem;
    color: {GOLD};
    letter-spacing: 0.08em;
    margin-right: 6px;
    margin-bottom: 4px;
  }}
</style>
""", unsafe_allow_html=True)


# ─── CHART LAYOUT ───────────────────────────────────────────────────────────────
CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Jost, sans-serif", color=TEXT, size=11),
    margin=dict(l=0, r=10, t=10, b=10),
)
GRID_STYLE = dict(gridcolor=BORDER, zerolinecolor=BORDER)


# ─── PDF PARSING ────────────────────────────────────────────────────────────────

def clean_store_name(raw_name: str) -> str:
    """P1-E/I: Strip date suffix and OS duplicate markers from filename-based store names.
    Handles: ' - 03_15_26', ' - 03_21_26 (1)', ' - 03_21_26 (1) (1)', trailing ' (CS 2)', ' (FS)'.
    """
    n = raw_name.strip()
    # Strip date suffix and everything after it: ' - MM_DD_YY...'
    n = re.sub(r'\s*-\s*\d{2}_\d{2}_\d{2,4}.*$', '', n).strip()
    # Strip trailing parenthetical suffixes like (CS 2), (CS 1), (FS), (F), (1)
    # These come from OS duplicate markers or PDF naming conventions
    n = re.sub(r'\s*\((?:CS\s*\d*|FS|F|B|\d+)\)\s*$', '', n, flags=re.IGNORECASE).strip()
    # Run again in case there were nested suffixes like "(1) (1)" or "(CS 2)" after date strip
    n = re.sub(r'\s*\((?:CS\s*\d*|FS|F|B|\d+)\)\s*$', '', n, flags=re.IGNORECASE).strip()
    return n


def extract_store_name(text: str) -> str:
    match = re.search(
        r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(.+?)\s+LATEST TIME EDITED',
        text, re.IGNORECASE
    )
    if match:
        name = match.group(1).strip()
        if name:
            return name
    for line in text.split('\n')[:6]:
        cleaned = re.sub(
            r'(ORDER DATE|DELIVERY DATE|ORDERED BY|LATEST TIME EDITED|PICKED BY|TOTAL AMOUNT).*',
            '', line, flags=re.IGNORECASE
        ).strip()
        cleaned = re.sub(r'\d{1,2}[/-]\w+[/-]\d{2,4}', '', cleaned).strip()
        cleaned = re.sub(r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun)', '', cleaned, flags=re.IGNORECASE).strip()
        if cleaned and re.match(r'^[A-Z][A-Z0-9\-\s]+$', cleaned) and len(cleaned) > 3:
            return cleaned.strip()
    return "UNKNOWN"


def extract_date(text: str, label: str) -> str:
    match = re.search(rf'{label}\s+(\d{{1,2}}-\w+-\d{{2,4}})', text, re.IGNORECASE)
    return match.group(1) if match else ""


def extract_header_total(text: str) -> float | None:
    """P1-F: Extract TOTAL AMOUNT from PDF header for validation."""
    match = re.search(r'TOTAL\s+AMOUNT[:\s]*([\d,]+\.?\d*)', text, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1).replace(',', ''))
        except ValueError:
            return None
    return None


def extract_ordered_by(text: str) -> str:
    """P2-L: Extract ORDERED BY from PDF header."""
    match = re.search(r'ORDERED\s+BY\s+(.+?)(?:\s+TOTAL|\s+PICKED|\n)', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def fix_merged_uom_amount(uom_val: str, amt_val: str, days_val: str) -> tuple[str, str, str]:
    """P1-C: Split merged UOM+Amount like 'SHEET50.00' or 'ROLLS102.00'.
    Also handles 'SHEET 50.00' (space-separated due to PDF line breaks).
    When UOM has a merged number, the real amount is inside the UOM
    and whatever was in the Amount column is actually Days to Last (shifted left).
    Returns (fixed_uom, fixed_amount, fixed_days).
    """
    # Case 1: UOM has a number merged in (e.g. 'SHEET50.00' or 'ROLLS102.00')
    m = re.match(r'^([A-Za-z]{2,})\s*(\d[\d,]*\.?\d*)$', uom_val.strip())
    if m:
        real_uom = m.group(1)
        real_amt = m.group(2)
        real_days = amt_val if amt_val else days_val
        return real_uom, real_amt, real_days

    # Case 2: Amount cell starts with letters (split across columns by pdfplumber).
    # e.g. UOM='SHEE', Amount='T50.00' → real UOM='SHEET', real Amount='50.00'
    if amt_val:
        m2 = re.match(r'^([A-Za-z]+)(\d[\d,]*\.?\d*)$', amt_val.strip())
        if m2:
            real_uom = uom_val + m2.group(1)
            real_amt = m2.group(2)
            real_days = days_val
            return real_uom, real_amt, real_days

    return uom_val, amt_val, days_val


def _join_fragmented_cells(row: list) -> list:
    """P0-A: Rejoin cells that got split across columns due to PDF line breaks.
    e.g. ['SECOND FLOO', 'R 20196', '1', ...] → ['SECOND FLOOR', '20196', '1', ...]
    """
    if not row or len(row) < 2:
        return row
    joined = list(row)
    loc_val = str(joined[0] or '').strip()
    next_val = str(joined[1] or '').strip()
    # Detect: location is a partial word AND next cell starts with the continuation + a number
    # e.g. loc="SECOND FLOO" next="R 20196"
    if loc_val and next_val and re.match(r'^[A-Z]{1,3}\s+\d+', next_val):
        parts = next_val.split(None, 1)
        joined[0] = loc_val + parts[0]  # "SECOND FLOO" + "R" = "SECOND FLOOR"
        joined[1] = parts[1] if len(parts) > 1 else ''  # "20196"
    return joined


def parse_pdf(pdf_bytes: bytes, filename: str) -> tuple[pd.DataFrame, list[str]]:
    """Parse a single PDF file. Returns (DataFrame, list_of_warnings)."""
    rows = []
    warnings = []
    raw_store_name = Path(filename).stem
    # P1-E/I: Strip date suffix from filename
    store_name = clean_store_name(raw_store_name)
    order_date    = ""
    delivery_date = ""
    ordered_by    = ""  # P2-L
    header_total  = None  # P1-F

    # Track column layout from page 1 header for continuation pages (P0-A)
    known_col_count = None
    last_location = ""  # Track last seen location for context

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if page_num == 0:
                    if not re.match(r'^\d+$', raw_store_name):
                        pass  # keep filename (cleaned) as store name
                    else:
                        extracted = extract_store_name(text)
                        if extracted and extracted != "UNKNOWN":
                            store_name = extracted
                    order_date    = extract_date(text, "ORDER DATE")
                    delivery_date = extract_date(text, "DELIVERY DATE")
                    ordered_by    = extract_ordered_by(text)
                    header_total  = extract_header_total(text)

                tables = page.extract_tables({
                    "vertical_strategy":   "lines",
                    "horizontal_strategy": "lines"
                })
                for table in tables:
                    if not table or len(table) < 1:
                        continue

                    # Look for header row with "LOCATION"
                    header_idx = None
                    for i, row in enumerate(table):
                        if row and any('LOCATION' in str(cell or '').upper() for cell in row):
                            header_idx = i
                            break

                    if header_idx is not None:
                        # Standard page with header — extract column indices
                        def flat(cell):
                            return ' '.join(str(cell or '').split()).upper()

                        header = [flat(h) for h in table[header_idx]]
                        known_col_count = len(header)

                        def col(keyword):
                            for ci, h in enumerate(header):
                                if keyword in h:
                                    return ci
                            return None

                        idx_loc   = col('LOCATION')
                        idx_plu   = col('PLU')
                        idx_order = col('ORDER')
                        idx_item  = col('ITEM') or col('DESCRIPTION')
                        idx_uom   = col('UOM')
                        idx_amt   = col('TOTAL AMOUNT') or col('AMOUNT')
                        idx_days  = col('DAYS')

                        data_rows = table[header_idx + 1:]
                    else:
                        # P0-A: Continuation page — no header row.
                        # Reuse column layout from page 1.
                        if known_col_count is None:
                            warnings.append(f"Page {page_num+1}: skipped — no header row and no prior column layout")
                            continue
                        data_rows = table  # all rows are data

                    for row in data_rows:
                        if not row:
                            continue

                        # P0-A: Fix fragmented cells before extracting values
                        row = _join_fragmented_cells(row)

                        def get(idx):
                            if idx is None or idx >= len(row):
                                return ''
                            return ' '.join(str(row[idx] or '').split()).strip()

                        location = get(idx_loc)
                        item     = get(idx_item)

                        if not item or item.upper() in ('ITEM DESCRIPTION', 'DESCRIPTION'):
                            continue

                        # P0-B: Allow empty location — we'll resolve it later via cross-reference.
                        # Track last seen location for context.
                        if location and location.upper() != 'LOCATION':
                            last_location = location

                        raw_uom  = get(idx_uom)
                        raw_amt  = get(idx_amt)
                        raw_days = get(idx_days)
                        # P1-C: Fix merged UOM+Amount (also shifts Days when merge detected)
                        fixed_uom, fixed_amt, fixed_days = fix_merged_uom_amount(
                            raw_uom, raw_amt, raw_days
                        )

                        # P3-D: Flag blank amounts
                        if not fixed_amt or fixed_amt.strip() == '':
                            warnings.append(
                                f"Blank amount: {store_name} → {item} (UOM: {fixed_uom})"
                            )

                        rows.append({
                            'Store':            store_name,
                            'Order Date':       order_date,
                            'Delivery Date':    delivery_date,
                            'Ordered By':       ordered_by,
                            'Location':         location if (location and location.upper() != 'LOCATION') else '',
                            'PLU Code':         get(idx_plu),
                            'Order Qty':        get(idx_order),
                            'Item Description': item,
                            'UOM':              fixed_uom,
                            'Total Amount':     fixed_amt,
                            'Days to Last':     fixed_days,
                        })

    except Exception as e:
        warnings.append(f"Could not parse {filename}: {e}")

    df = pd.DataFrame(rows)

    # P1-F: Validate parsed total vs PDF header total
    if not df.empty and header_total is not None:
        df['Total Amount'] = pd.to_numeric(
            df['Total Amount'].astype(str).str.replace(',', '').str.strip(),
            errors='coerce'
        )
        parsed_total = df['Total Amount'].sum()
        if header_total > 0:
            pct_diff = abs(parsed_total - header_total) / header_total * 100
            if pct_diff > 1:
                warnings.append(
                    f"Total mismatch: parsed ₱{parsed_total:,.2f} vs PDF header ₱{header_total:,.2f} "
                    f"(diff {pct_diff:.1f}%) — some rows may have been lost"
                )
        # Reset to string so clean_numeric runs uniformly later
        df['Total Amount'] = df['Total Amount'].astype(str)

    return df, warnings


def resolve_empty_locations(df: pd.DataFrame, warnings: list[str]) -> pd.DataFrame:
    """P0-B: Fill empty Location cells by cross-referencing item names.
    1. If the same item appears elsewhere in the same store with a location, use that.
    2. If the item appears across stores, use the most common location.
    3. Otherwise fill 'UNKNOWN' and log a warning.
    """
    if df.empty:
        return df

    empty_mask = df['Location'].str.strip().eq('') | df['Location'].isna()
    if not empty_mask.any():
        return df

    # Build lookup: item → list of known locations
    known = df[~empty_mask].groupby('Item Description')['Location'].apply(list).to_dict()

    for idx in df[empty_mask].index:
        item = df.at[idx, 'Item Description']
        store = df.at[idx, 'Store']
        resolved = ''

        if item in known:
            locs = known[item]
            # Prefer locations from the same store
            same_store_locs = [
                df.at[i, 'Location']
                for i in df[(df['Item Description'] == item) & (df['Store'] == store) & (~empty_mask)].index
            ]
            if same_store_locs:
                resolved = Counter(same_store_locs).most_common(1)[0][0]
            else:
                resolved = Counter(locs).most_common(1)[0][0]

        if not resolved:
            resolved = 'UNKNOWN'
            warnings.append(f"Unknown location: {store} → {item} — set to UNKNOWN")

        df.at[idx, 'Location'] = resolved

    return df


def clean_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(',', '').str.strip(),
        errors='coerce'
    )



# ─── PRINT HTML GENERATORS ──────────────────────────────────────────────────────

def _print_header_html(report_label: str, meta_rows: list[tuple]) -> str:
    """Shared branded header for all print reports.
    meta_rows: list of (label, value, highlight) tuples.
    """
    logo_tag = (
        f'<img src="data:image/png;base64,{LOGO_B64}" class="logo" alt="The Abaca Group">'
        if LOGO_B64 else
        '<div class="logo-text">THE ABACÁ GROUP</div>'
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
          <td>{r['Store']}</td>
          <td style="font-size:8pt; color:#888;">{r.get('PLU Code', '')}</td>
          <td>{r['Item Description']}</td>
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
          <td>{r['Item Description']}</td>
          <td></td>
          <td></td>
          <td style="text-align:center;">{int(r['Order Qty']) if pd.notna(r['Order Qty']) else '-'}</td>
        </tr>"""

    meta_rows = [
        ("Delivery Date:", delivery_date, True),
        ("Location:", location, False),
        ("Total Lines:", str(len(df_sorted)), False),
    ]
    if ordered_by:
        meta_rows.append(("Ordered By:", ordered_by, False))

    header = _print_header_html(f"{location} — PICK LIST", meta_rows)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{location} PICKLIST</title>
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
  <span>Pick List · {location}</span>
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
          <td>{r['Store']}</td>
          <td style="text-align:center;">{int(r['Order Qty']) if pd.notna(r['Order Qty']) else '-'}</td>
        </tr>"""

    uom_vals = df_item['UOM'].dropna().unique()
    uom = uom_vals[0] if len(uom_vals) > 0 else ""

    header = _print_header_html(
        f"{item_name} — ORDER",
        [
            ("Delivery Date:", delivery_date, True),
            ("UOM:", uom, False),
            ("Total Stores:", str(len(store_summary)), False),
            ("Total Qty:", str(total_qty), False),
        ]
    )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{item_name} — ORDER</title>
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
  <span>Item Allocation · {item_name}</span>
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
            remarks_cell = f'<td{rs_attr}{cls}>{remark_val}</td>'
            # Mark subsequent rows in this group to skip the remarks cell
            for k in range(idx + 1, idx + span):
                skip_remarks.add(k)

        tr_html += f"""
        <tr>
          <td>{delivery_date}</td>
          <td>{r['store']}</td>
          <td>{r['item']}</td>
          <td style="text-align:center;">{r['qty']}</td>
          {remarks_cell}
        </tr>"""

    header = _print_header_html(
        report_title,
        [
            ("Order Date:", order_date, False),
            ("Delivery Date:", delivery_date, True),
            ("Prepared by:", prepared_by.upper(), False),
            ("Total Items:", str(len(sorted_rows)), False),
        ]
    )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{report_title}</title>
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
  <span>Undelivered Report · {delivery_date}</span>
</div>

<button class="print-btn" onclick="window.print()">🖨&nbsp; Print</button>
</body>
</html>"""


# ─── GOOGLE DRIVE DOWNLOAD ────────────────────────────────────────────────────
import tempfile

def _parse_drive_link(url: str) -> tuple[str, str]:
    """Parse a Google Drive URL and return (link_type, id).
    link_type is 'folder', 'file', or 'unknown'.
    """
    url = url.strip()
    # Folder link: https://drive.google.com/drive/folders/FOLDER_ID...
    m = re.search(r'drive\.google\.com/drive/folders/([A-Za-z0-9_-]+)', url)
    if m:
        return 'folder', m.group(1)
    # File link: https://drive.google.com/file/d/FILE_ID/...
    m = re.search(r'drive\.google\.com/file/d/([A-Za-z0-9_-]+)', url)
    if m:
        return 'file', m.group(1)
    # Open link: https://drive.google.com/open?id=FILE_ID
    m = re.search(r'drive\.google\.com/open\?id=([A-Za-z0-9_-]+)', url)
    if m:
        return 'file', m.group(1)
    # Fallback: try to extract any long alphanumeric ID
    m = re.search(r'/d/([A-Za-z0-9_-]{20,})/', url)
    if m:
        return 'file', m.group(1)
    return 'unknown', ''


def _get_drive_service():
    """Build a Google Drive API service using the same service account from Streamlit secrets."""
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes,
    )
    return build("drive", "v3", credentials=creds)


def _download_from_drive(url: str) -> list[tuple[str, bytes]]:
    """Download PDFs from a Google Drive link (folder or single file).
    Uses the Google Drive API via the same service account used for the Store Checklist.
    The Drive folder/file must be shared with the service account email.
    Returns list of (filename, bytes) tuples.
    """
    link_type, drive_id = _parse_drive_link(url)

    if link_type == 'unknown' or not drive_id:
        st.error(
            "**Could not parse Drive link.** "
            "Make sure you paste the full URL from Google Drive "
            "(folder or file share link)."
        )
        return []

    try:
        service = _get_drive_service()
    except KeyError:
        st.error(
            "**Service account credentials not found.** "
            "Add `[gcp_service_account]` to Streamlit secrets."
        )
        return []
    except Exception as e:
        st.error(f"**Could not connect to Google Drive API:** {e}")
        return []

    results = []  # (name, bytes)

    if link_type == 'folder':
        status = st.empty()
        status.info("Scanning Google Drive folder for PDF files…")

        try:
            # List all PDF files in the folder using Drive API
            query = f"'{drive_id}' in parents and mimeType='application/pdf' and trashed=false"
            file_list = []
            page_token = None
            while True:
                resp = service.files().list(
                    q=query,
                    fields="nextPageToken, files(id, name, size)",
                    pageSize=100,
                    pageToken=page_token,
                ).execute()
                file_list.extend(resp.get("files", []))
                page_token = resp.get("nextPageToken")
                if not page_token:
                    break
        except Exception as e:
            status.empty()
            err_msg = str(e)
            if "404" in err_msg:
                st.error("**Folder not found.** Check the link is correct.")
            elif "403" in err_msg or "access" in err_msg.lower():
                # Show the service account email so user can share with it
                sa_email = st.secrets.get("gcp_service_account", {}).get("client_email", "")
                st.error(
                    f"**Access denied.** Share the Drive folder with the service account:\n\n"
                    f"`{sa_email}`\n\n"
                    f"Set permission to **Viewer**."
                )
            else:
                st.error(f"**Drive API error:** {e}")
            return []

        status.empty()

        if not file_list:
            sa_email = st.secrets.get("gcp_service_account", {}).get("client_email", "")
            st.error(
                f"**No PDF files found in folder.** Possible causes:\n"
                f"- Folder is empty or has no PDFs\n"
                f"- Folder is not shared with the service account\n\n"
                f"Share the folder with:\n`{sa_email}`"
            )
            return []

        st.info(f"Found **{len(file_list)} PDF(s)** in folder — downloading…")
        progress = st.progress(0, text=f"Downloading 0 of {len(file_list)} files…")

        for i, f_info in enumerate(file_list):
            fname = f_info.get("name", f"file_{i}.pdf")
            progress.progress(
                (i + 1) / len(file_list),
                text=f"Downloading {i + 1} of {len(file_list)} files… ({fname})"
            )
            try:
                content = service.files().get_media(fileId=f_info["id"]).execute()
                if content and content[:5].startswith(b'%PDF'):
                    results.append((fname, content))
                else:
                    st.warning(f"Skipped **{fname}** — not a valid PDF")
            except Exception as e:
                st.warning(f"Failed to download **{fname}**: {e}")

        progress.empty()

        if results:
            st.success(f"✓ Downloaded **{len(results)} PDF(s)** — parsing now…")
        else:
            st.error("**No PDFs could be downloaded** from the folder.")

    else:
        # Single file download via Drive API
        status = st.empty()
        status.info("Downloading file from Google Drive…")

        try:
            # Get file metadata (name)
            meta = service.files().get(fileId=drive_id, fields="name, mimeType").execute()
            fname = meta.get("name", f"drive_{drive_id[:8]}.pdf")

            # Download content
            content = service.files().get_media(fileId=drive_id).execute()
        except Exception as e:
            status.empty()
            err_msg = str(e)
            if "404" in err_msg:
                st.error("**File not found.** Check the link is correct.")
            elif "403" in err_msg or "access" in err_msg.lower():
                sa_email = st.secrets.get("gcp_service_account", {}).get("client_email", "")
                st.error(
                    f"**Access denied.** Share the file with the service account:\n\n"
                    f"`{sa_email}`\n\n"
                    f"Set permission to **Viewer**."
                )
            else:
                st.error(f"**Download failed:** {e}")
            return []
        status.empty()

        if not content or not content[:5].startswith(b'%PDF'):
            st.error("**Downloaded file is not a valid PDF.**")
            return []

        if not fname.lower().endswith('.pdf'):
            fname += '.pdf'
        results.append((fname, content))
        st.success(f"✓ Downloaded **1 PDF** ({fname}) — parsing now…")

    return results


# ─── PDF REPORT GENERATION (fpdf2) ────────────────────────────────────────────

def _generate_combined_pdf(
    unavailable_items: list[dict],
    manual_orders: list[dict],
    report_title: str,
    order_date: str,
    delivery_date: str,
    prepared_by: str,
    undelivered_rows: list[dict] | None = None,
) -> bytes:
    """Generate a print-ready PDF combining undelivered items, unavailable items, and manual orders.
    Uses fpdf2. Returns PDF bytes.
    """
    from fpdf import FPDF

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
            '\u2019': "'",
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        # Drop any remaining non-latin1 chars
        return text.encode('latin-1', errors='replace').decode('latin-1')

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
            self.cell(0, 10, f"SC_PDF STORES SUMMARY · The Abaca Group · Page {self.page_no()}/{{nb}}", align="C")

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
        from collections import defaultdict
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
        from collections import defaultdict
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
    items_data: list[dict],
    delivery_date: str,
) -> bytes:
    """Generate a combined allocation PDF for multiple items.
    items_data: list of {item, uom, total_qty, stores: [{store, qty}]}
    Each item gets its own section with a page break between items.
    """
    from fpdf import FPDF

    def _safe(text: str) -> str:
        replacements = {
            '\u2014': '-', '\u2013': '-', '\u2018': "'", '\u2019': "'",
            '\u201c': '"', '\u201d': '"', '\u2026': '...', '\u00a0': ' ',
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        return text.encode('latin-1', errors='replace').decode('latin-1')

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


# ─── SESSION STATE ───────────────────────────────────────────────────────────────
if 'df' not in st.session_state:
    st.session_state.df              = pd.DataFrame()
    st.session_state.file_names      = set()
if 'undelivered_rows' not in st.session_state:
    st.session_state.undelivered_rows = []   # list of dicts
if 'parse_warnings' not in st.session_state:
    st.session_state.parse_warnings  = []    # P2-J: Parsing warning log
if 'unavailable_items' not in st.session_state:
    st.session_state.unavailable_items = []  # list of dicts: {item, remarks, stores: [{store, qty, uom}]}
if 'manual_orders' not in st.session_state:
    st.session_state.manual_orders = []      # list of dicts: {store, item, qty, uom, remarks}


# ─── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="padding:8px 0 20px 0;">
      <div style="font-family:'Manrope',sans-serif; font-size:0.6rem; font-weight:700;
                  letter-spacing:0.25em; color:{MUTED}; text-transform:uppercase;">
        The Abaca Group
      </div>
      <div style="font-size:0.95rem; font-weight:600; color:{TEXT}; margin-top:4px;">
        Supply Chain
      </div>
      <div style="width:28px; height:2px; background:{GOLD}; margin-top:8px;"></div>
    </div>
    """, unsafe_allow_html=True)

    # ── PDF Input — Google Drive Link ────────────────────────────────────────
    st.markdown(
        f'<div style="font-size:0.62rem; font-weight:600; letter-spacing:0.15em; '
        f'text-transform:uppercase; color:{GOLD}; margin-bottom:8px;">'
        f'Load PDFs from Google Drive</div>',
        unsafe_allow_html=True
    )
    drive_link = st.text_input(
        "Google Drive link",
        placeholder="https://drive.google.com/drive/folders/...",
        help="Paste a Google Drive folder or single file link",
        label_visibility="collapsed",
        key="drive_link_input",
    )
    st.markdown(
        f'<div style="font-size:0.62rem; color:{MUTED}; margin-top:-8px; margin-bottom:8px;">'
        f'Share the Drive folder with the service account email (see Store Checklist tab for details)</div>',
        unsafe_allow_html=True,
    )
    load_drive = st.button("📥  Load from Drive", use_container_width=True, key="load_drive_btn")

    pdf_file_list = []  # list of (name, bytes)

    if drive_link and load_drive:
        pdf_file_list = _download_from_drive(drive_link)

    if pdf_file_list:
        new_names = {n for n, _ in pdf_file_list}

        if new_names != st.session_state.file_names:
            progress = st.progress(0, text="Reading PDFs…")
            dfs = []
            all_warnings = []
            for i, (name, data) in enumerate(pdf_file_list):
                df_i, file_warnings = parse_pdf(data, name)
                all_warnings.extend(file_warnings)
                if not df_i.empty:
                    dfs.append(df_i)
                progress.progress((i + 1) / len(pdf_file_list), text=f"{i+1}/{len(pdf_file_list)}: {name}")
            progress.empty()

            if dfs:
                combined = pd.concat(dfs, ignore_index=True)
                combined['Order Qty']    = clean_numeric(combined['Order Qty'])
                combined['Total Amount'] = clean_numeric(combined['Total Amount'])
                combined['Days to Last'] = clean_numeric(combined['Days to Last'])
                combined = combined[combined['Item Description'].str.strip().str.len() > 0]
                # P0-B: Resolve empty locations via cross-reference instead of dropping rows
                combined = resolve_empty_locations(combined, all_warnings)
                # Deduplicate stores that resolve to the same clean name (e.g. OS duplicate files)
                if not combined.empty:
                    combined['_clean_store'] = combined['Store'].apply(
                        lambda s: _normalize_store(s) if pd.notna(s) else ''
                    )
                    dup_groups = combined.groupby('_clean_store')['Store'].apply(
                        lambda x: list(x.unique())
                    )
                    for clean_name, store_variants in dup_groups.items():
                        if len(store_variants) > 1:
                            # Keep the variant with more rows, drop the rest
                            counts = {
                                sv: len(combined[combined['Store'] == sv])
                                for sv in store_variants
                            }
                            keep = max(counts, key=counts.get)
                            drop_variants = [sv for sv in store_variants if sv != keep]
                            for dv in drop_variants:
                                all_warnings.append(
                                    f"Duplicate store: '{dv}' merged into '{keep}' "
                                    f"({counts[dv]} rows dropped, {counts[keep]} kept)"
                                )
                                combined = combined[combined['Store'] != dv]
                    combined.drop(columns=['_clean_store'], inplace=True)

                st.session_state.df              = combined
                st.session_state.file_names      = new_names
                st.session_state.parse_warnings  = all_warnings
            else:
                st.error("No data extracted from PDFs.")

        # Status badge
        n = len(pdf_file_list)
        df_loaded = st.session_state.df
        del_dates = df_loaded['Delivery Date'].dropna().unique().tolist() if not df_loaded.empty else []
        del_label = del_dates[0] if len(del_dates) == 1 else (f"{len(del_dates)} dates" if del_dates else "—")

        st.markdown(f"""
        <div style="margin-top:12px; padding:12px 14px; background:{CARD};
                    border:1px solid {BORDER}; border-left:3px solid {GOLD}; border-radius:3px;">
          <div style="font-size:0.6rem; letter-spacing:0.15em; color:{MUTED};
                      text-transform:uppercase; font-weight:600; margin-bottom:6px;">Loaded</div>
          <div style="font-size:1.2rem; font-weight:700; color:{TEXT};">{n} PDF{'s' if n != 1 else ''}</div>
          <div style="font-size:0.72rem; color:{MUTED}; margin-top:6px;">
            {df_loaded['Store'].nunique() if not df_loaded.empty else 0} stores
            &nbsp;·&nbsp; Delivery: {del_label}
          </div>
        </div>
        """, unsafe_allow_html=True)

    if not st.session_state.df.empty:
        st.markdown("---")

        # ── P2-J: Parsing Warnings Panel ──────────────────────────────────────
        warn_list = st.session_state.parse_warnings
        if warn_list:
            with st.expander(f"⚠ Parsing Warnings ({len(warn_list)})", expanded=False):
                for w in warn_list:
                    icon = "🔴" if "mismatch" in w.lower() or "lost" in w.lower() else "🟡"
                    st.markdown(
                        f'<div style="font-size:0.72rem; padding:3px 0; '
                        f'border-bottom:1px solid {BORDER}; color:{TEXT};">'
                        f'{icon} {w}</div>',
                        unsafe_allow_html=True
                    )

        # ── Store Roster Check ──────────────────────────────────────────────
        df_check = st.session_state.df
        store_counts = df_check.groupby('Store').agg(
            Files=('Store', 'count'),
        ).reset_index()

        # P3-G: Duplicate detection — check for same store + delivery date in multiple files
        store_del_combos = df_check.groupby(['Store', 'Delivery Date']).size().reset_index(name='count')
        # A store should only appear once per delivery date; flag if file count > expected items
        dup_stores = set()
        for _, combo in store_del_combos.iterrows():
            store_name_val = combo['Store']
            # Check if multiple filenames map to the same cleaned store name
            matching_files = [
                fn for fn in st.session_state.file_names
                if clean_store_name(Path(fn).stem) == store_name_val
            ]
            if len(matching_files) > 1:
                dup_stores.add(store_name_val)

        store_counts['Flag'] = store_counts['Store'].apply(
            lambda x: '⚠️ Possible duplicate' if x in dup_stores else '✅'
        )

        with st.expander(f"📋 Store Roster ({len(store_counts)} stores)", expanded=False):
            st.markdown(
                f'<div style="font-size:0.65rem; color:{MUTED}; '
                f'letter-spacing:0.1em; text-transform:uppercase; '
                f'font-weight:600; margin-bottom:8px;">'
                f'Loaded stores — check for missing or duplicate uploads</div>',
                unsafe_allow_html=True
            )
            for _, row in store_counts.sort_values('Store').iterrows():
                flag_color = "#E8A020" if "⚠️" in row['Flag'] else "#4CAF50"
                st.markdown(
                    f'<div style="font-size:0.75rem; padding:3px 0; '
                    f'border-bottom:1px solid {BORDER}; display:flex; '
                    f'justify-content:space-between;">'
                    f'<span style="color:{TEXT};">{row["Store"]}</span>'
                    f'<span style="color:{flag_color}; font-size:0.68rem;">{row["Flag"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            # List file names uploaded
            st.markdown(
                f'<div style="font-size:0.65rem; color:{MUTED}; margin-top:10px; '
                f'letter-spacing:0.08em; text-transform:uppercase; font-weight:600;">'
                f'{len(st.session_state.file_names)} files uploaded</div>',
                unsafe_allow_html=True
            )
            for fname in sorted(st.session_state.file_names):
                st.markdown(
                    f'<div style="font-size:0.68rem; color:{MUTED}; padding:2px 0;">'
                    f'· {fname}</div>',
                    unsafe_allow_html=True
                )

        st.markdown("---")

        # ── Save Session ────────────────────────────────────────────────────
        session_data = {
            'df': st.session_state.df.to_dict('records'),
            'file_names': list(st.session_state.file_names),
            'undelivered_rows': st.session_state.undelivered_rows,
            'parse_warnings': st.session_state.parse_warnings,
            'unavailable_items': st.session_state.unavailable_items,
            'manual_orders': st.session_state.manual_orders,
        }
        session_json = json.dumps(session_data, default=str)
        st.download_button(
            "💾  Save Session",
            data=session_json,
            file_name="orders_session.json",
            mime="application/json",
            use_container_width=True,
            help="Download a snapshot you can reload later — even after restart"
        )

        st.markdown("---")
        if st.button("🗑  Clear & Reset"):
            st.session_state.df               = pd.DataFrame()
            st.session_state.file_names       = set()
            st.session_state.undelivered_rows = []
            st.session_state.parse_warnings   = []
            st.session_state.unavailable_items = []
            st.session_state.manual_orders    = []
            st.rerun()

    # ── Load Saved Session ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        f'<div style="font-size:0.62rem; font-weight:600; letter-spacing:0.15em; '
        f'text-transform:uppercase; color:{MUTED}; margin-bottom:6px;">Restore session</div>',
        unsafe_allow_html=True
    )
    if 'session_loaded_key' not in st.session_state:
        st.session_state.session_loaded_key = None
    loaded_session = st.file_uploader(
        "Load saved session (.json)",
        type="json",
        key="session_loader",
        label_visibility="collapsed"
    )
    if loaded_session and loaded_session.name != st.session_state.session_loaded_key:
        try:
            data = json.loads(loaded_session.read())
            df_restored = pd.DataFrame(data.get('df', []))
            if not df_restored.empty:
                for col_name in ['Order Qty', 'Total Amount', 'Days to Last']:
                    if col_name in df_restored.columns:
                        df_restored[col_name] = clean_numeric(df_restored[col_name])
            st.session_state.df               = df_restored
            st.session_state.file_names       = set(data.get('file_names', []))
            st.session_state.undelivered_rows  = data.get('undelivered_rows', [])
            st.session_state.parse_warnings    = data.get('parse_warnings', [])
            st.session_state.unavailable_items = data.get('unavailable_items', [])
            st.session_state.manual_orders     = data.get('manual_orders', [])
            st.session_state.session_loaded_key = loaded_session.name
            st.success("✅ Session restored!")
            st.rerun()
        except Exception as e:
            st.error(f"Could not load session: {e}")


# ─── HEADER ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="abaca-header">
  <div>
    <div class="abaca-wordmark">The Abaca Group &nbsp;·&nbsp; Supply Chain</div>
    <h1 class="abaca-title">SC_PDF STORES SUMMARY_01</h1>
    <div class="gold-line"></div>
  </div>
</div>
""", unsafe_allow_html=True)

df = st.session_state.df

if df.empty:
    st.markdown(f"""
    <div style="padding:56px 0; text-align:center; color:{MUTED};">
      <div style="font-size:2.5rem; margin-bottom:16px;">📂</div>
      <div style="font-size:0.8rem; letter-spacing:0.15em; text-transform:uppercase;
                  font-weight:600; color:{TEXT};">
        Upload PDF store orders from the sidebar to begin
      </div>
      <div style="margin-top:16px; font-size:0.8rem; line-height:2.2; color:#555;">
        Drag all store PDFs into the uploader &nbsp;·&nbsp; Supports 100+ files at once<br>
        Pick List by Location &nbsp;·&nbsp; Item Allocation sheets &nbsp;·&nbsp; Store × Item Matrix
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ─── GLOBAL FILTERS ─────────────────────────────────────────────────────────────
st.markdown(f'<div class="section-label">Filters</div>', unsafe_allow_html=True)
f1, f2, f3, f4 = st.columns([2, 2, 2, 1])

with f1:
    all_stores = sorted(df['Store'].dropna().unique())
    sel_stores = st.multiselect("Store / Branch", all_stores, placeholder="All stores")

with f2:
    all_locs = sorted(df['Location'].dropna().unique())
    sel_locs = st.multiselect("Location / Area", all_locs, placeholder="All areas")

with f3:
    search_item = st.text_input("Search Item", placeholder="e.g. CHICKEN, BEEF…")

with f4:
    # P2-H: Out-of-stock filter toggle
    show_oos_only = st.toggle("Out of Stock only", value=False, key="oos_filter",
                               help="Show only items where Days to Last = 0")

filtered = df.copy()
if sel_stores:
    filtered = filtered[filtered['Store'].isin(sel_stores)]
if sel_locs:
    filtered = filtered[filtered['Location'].isin(sel_locs)]
if search_item:
    filtered = filtered[filtered['Item Description'].str.contains(search_item, case=False, na=False)]
if show_oos_only:
    filtered = filtered[filtered['Days to Last'] == 0]


# ─── KPIs ────────────────────────────────────────────────────────────────────────
total_stores = filtered['Store'].nunique()
unique_items = filtered['Item Description'].nunique()
total_lines  = len(filtered)
total_amount = filtered['Total Amount'].sum()
# P2-H: Count out-of-stock items
oos_count = int((filtered['Days to Last'] == 0).sum())

st.markdown(f"""
<div class="kpi-row">
  <div class="kpi-card">
    <div class="kpi-label">Stores</div>
    <div class="kpi-value">{total_stores}</div>
    <div class="kpi-sub">branches with orders</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Unique Items</div>
    <div class="kpi-value">{unique_items}</div>
    <div class="kpi-sub">distinct SKUs ordered</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Order Lines</div>
    <div class="kpi-value">{total_lines:,}</div>
    <div class="kpi-sub">total line items</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Total Amount</div>
    <div class="kpi-value">₱{total_amount:,.0f}</div>
    <div class="kpi-sub">filtered total</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Out of Stock</div>
    <div class="kpi-value" style="color:{RED if oos_count > 0 else TEXT};">{oos_count}</div>
    <div class="kpi-sub">Days to Last = 0</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ─── DELIVERY DATE PILLS ─────────────────────────────────────────────────────────
del_dates = sorted(filtered['Delivery Date'].dropna().unique())
if del_dates:
    pills = "".join(f'<span class="info-pill">📅 Delivery: {d}</span>' for d in del_dates)
    st.markdown(pills, unsafe_allow_html=True)

st.markdown("---")


# ─── TABS ────────────────────────────────────────────────────────────────────────
tab1, tab2, tab4, tab5, tab6, tab7 = st.tabs([
    "  📋  PICK LIST  ",
    "  📦  ITEM ALLOCATION  ",
    "  📊  ALL ORDERS  ",
    "  🚫  UNDELIVERED REPORT  ",
    "  📝  MANUAL ORDERS  ",
    "  ✅  STORE CHECKLIST  ",
])


# ══════════════════════════════════════════════════════════════════════════════════
# TAB 1 — PICK LIST (by Location, for Pickers)
# ══════════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown(f"""
    <div style="margin-bottom:12px;">
      <div style="font-size:0.65rem; letter-spacing:0.15em; color:{MUTED};
                  text-transform:uppercase; font-weight:600;">
        Select a location → get a ready-to-print pick list for your pickers
      </div>
    </div>
    """, unsafe_allow_html=True)

    locations = sorted(filtered['Location'].dropna().unique())

    if not locations:
        st.info("No locations found. Upload PDF orders first.")
    else:
        pl_col1, pl_col2, pl_col3 = st.columns([2, 1, 1])
        with pl_col1:
            sel_loc = st.selectbox("Select Location / Area", locations, key="picklist_loc")
        with pl_col2:
            show_store_breakdown = st.toggle("Show store column", value=True, key="pl_breakdown")

        df_loc = filtered[filtered['Location'] == sel_loc].copy()

        if df_loc.empty:
            st.warning(f"No orders found for **{sel_loc}**.")
        else:
            # Get delivery date for this location
            loc_del_dates = df_loc['Delivery Date'].dropna().unique()
            loc_del = loc_del_dates[0] if len(loc_del_dates) > 0 else "—"

            # P2-L: Get ordered_by for header
            loc_ordered_by = df_loc['Ordered By'].dropna().unique() if 'Ordered By' in df_loc.columns else []
            loc_ordered_by_str = ", ".join(sorted(set(loc_ordered_by))) if len(loc_ordered_by) > 0 else ""

            # Header info
            loc_stores = df_loc['Store'].nunique()
            loc_items  = df_loc['Item Description'].nunique()
            loc_total  = df_loc['Order Qty'].sum()

            st.markdown(f"""
            <div style="display:flex; gap:16px; margin-bottom:16px; flex-wrap:wrap;">
              <span class="info-pill">📍 {sel_loc}</span>
              <span class="info-pill">🏪 {loc_stores} stores</span>
              <span class="info-pill">📦 {loc_items} items</span>
              <span class="info-pill">🔢 {int(loc_total) if pd.notna(loc_total) else 0} total units</span>
              <span class="info-pill">📅 Delivery: {loc_del}</span>
              {f'<span class="info-pill">👤 {loc_ordered_by_str}</span>' if loc_ordered_by_str else ''}
            </div>
            """, unsafe_allow_html=True)

            # ── Detail table ──
            if show_store_breakdown:
                display = (
                    df_loc.groupby(['Store', 'Item Description', 'PLU Code', 'UOM'])
                    .agg(Qty=('Order Qty', 'sum'), DaysToLast=('Days to Last', 'min'))
                    .reset_index()
                    .sort_values(['Item Description', 'Store'])
                )
                display.columns = ['Store', 'Item Description', 'PLU Code', 'UOM', 'Qty', 'Days to Last']
                st.dataframe(display, use_container_width=True, hide_index=True, height=420)
            else:
                display = (
                    df_loc.groupby(['Item Description', 'PLU Code', 'UOM'])
                    .agg(Total_Qty=('Order Qty', 'sum'), Stores=('Store', 'nunique'))
                    .reset_index()
                    .sort_values('Item Description')
                )
                display.columns = ['Item Description', 'PLU Code', 'UOM', 'Total Qty', 'Stores Ordering']
                st.dataframe(display, use_container_width=True, hide_index=True, height=420)

            st.markdown("---")

            # ── SUMMARY QTY (like yellow section in manual picklist) ──
            st.markdown(f'<div class="section-label">Summary Qty — {sel_loc}</div>', unsafe_allow_html=True)
            summary_loc = (
                df_loc.groupby(['Item Description', 'UOM'])['Order Qty']
                .sum().reset_index()
                .sort_values('Item Description')
            )
            summary_loc.columns = ['Item Description', 'UOM', 'Total Qty']
            summary_loc['Total Qty'] = summary_loc['Total Qty'].apply(
                lambda x: int(x) if pd.notna(x) else 0)

            st.dataframe(
                summary_loc,
                use_container_width=True, hide_index=True,
                height=min(300, 40 + len(summary_loc) * 36)
            )

            # ── Print / Download ──
            st.markdown("<br>", unsafe_allow_html=True)
            html_picklist = make_picklist_html(df_loc, sel_loc, loc_del, loc_ordered_by_str)
            st.download_button(
                label=f"🖨  Download {sel_loc} Pick List (Print-Ready HTML)",
                data=html_picklist.encode('utf-8'),
                file_name=f"PICKLIST_{sel_loc.replace(' ', '_')}_{loc_del}.html",
                mime="text/html",
                key=f"dl_picklist_{sel_loc}"  # P3-M: Dynamic key
            )
            st.markdown(
                f'<div style="font-size:0.7rem; color:{MUTED}; margin-top:6px;">'
                '⬆ Download → open in browser → Ctrl+P to print</div>',
                unsafe_allow_html=True
            )


# ══════════════════════════════════════════════════════════════════════════════════
# TAB 2 — ITEM ALLOCATION (by Item, for Production)
# ══════════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown(f"""
    <div style="margin-bottom:12px;">
      <div style="font-size:0.65rem; letter-spacing:0.15em; color:{MUTED};
                  text-transform:uppercase; font-weight:600;">
        Select an item → see total qty + store breakdown — for production make-to-order
      </div>
    </div>
    """, unsafe_allow_html=True)

    ia_c1, ia_c2 = st.columns([3, 1])

    with ia_c1:
        # Item summary table (all items) — default view
        st.markdown(f'<div class="section-label">All Items — Total Qty Across All Stores</div>',
                    unsafe_allow_html=True)
        item_summary = (
            filtered.groupby(['Item Description', 'UOM', 'Location'])
            .agg(
                Total_Qty       = ('Order Qty',    'sum'),
                Stores_Ordering = ('Store',        'nunique'),
                Total_Amount    = ('Total Amount', 'sum'),
            )
            .reset_index()
            .sort_values('Total_Qty', ascending=False)
        )
        item_summary.columns = ['Item', 'UOM', 'Location', 'Total Qty', 'Stores Ordering', 'Total Amount (₱)']
        item_summary['Total Qty'] = item_summary['Total Qty'].apply(
            lambda x: int(x) if pd.notna(x) else 0)
        item_summary['Total Amount (₱)'] = item_summary['Total Amount (₱)'].map(
            lambda x: f'{x:,.2f}' if pd.notna(x) else '—')
        st.dataframe(item_summary, use_container_width=True, hide_index=True, height=400)

    with ia_c2:
        # Quick totals chart
        top10 = item_summary.nlargest(10, 'Total Qty')
        if not top10.empty:
            fig = go.Figure(go.Bar(
                x=top10['Total Qty'],
                y=top10['Item'],
                orientation='h',
                marker=dict(
                    color=top10['Total Qty'],
                    colorscale=[[0, "#2A2A2A"], [1, GOLD]],
                    line=dict(width=0)
                ),
                hovertemplate='<b>%{y}</b><br>Qty: %{x}<extra></extra>'
            ))
            fig.update_layout(
                **CHART_LAYOUT, height=400,
                xaxis=dict(title="", **GRID_STYLE),
                yaxis=dict(title="", tickfont=dict(size=9), autorange="reversed"),
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════════
    # Multi-Item Allocation — select multiple items for a combined report
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown(f'<div class="section-label">Multi-Item Allocation — Combined Report</div>',
                unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:0.7rem; color:{MUTED}; margin-bottom:10px;">'
        f'Select multiple items → review store breakdowns → download one combined PDF</div>',
        unsafe_allow_html=True,
    )

    all_items = sorted(filtered['Item Description'].dropna().unique())

    ma_c1, ma_c2 = st.columns([5, 1])
    with ma_c1:
        sel_multi_items = st.multiselect(
            "Select items for combined report",
            all_items,
            key="multi_alloc_items",
            placeholder="Click to select items…",
        )
    with ma_c2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Clear", key="multi_alloc_clear", use_container_width=True):
            st.session_state.multi_alloc_items = []
            st.rerun()

    if sel_multi_items:
        # Build data for each selected item
        multi_items_data = []
        for item_name in sel_multi_items:
            df_mi = filtered[filtered['Item Description'] == item_name]
            store_agg = (
                df_mi.groupby('Store')['Order Qty'].sum().reset_index().sort_values('Store')
            )
            total = int(store_agg['Order Qty'].sum()) if not store_agg.empty else 0
            uom_vals = df_mi['UOM'].dropna().unique()
            uom = uom_vals[0] if len(uom_vals) > 0 else ""

            stores_list = [
                {"store": r['Store'], "qty": int(r['Order Qty']) if pd.notna(r['Order Qty']) else 0}
                for _, r in store_agg.iterrows()
            ]
            multi_items_data.append({
                "item": item_name, "uom": uom, "total_qty": total, "stores": stores_list,
            })

        # Summary pills
        total_items = len(sel_multi_items)
        grand_total = sum(d["total_qty"] for d in multi_items_data)
        st.markdown(f"""
        <div style="display:flex; gap:12px; margin:8px 0 12px 0; flex-wrap:wrap;">
          <span class="info-pill">📦 {total_items} item(s) selected</span>
          <span class="info-pill">🔢 {grand_total:,} total units</span>
        </div>
        """, unsafe_allow_html=True)

        # Collapsible detail per item
        for d in multi_items_data:
            with st.expander(
                f"**{d['item']}** — {len(d['stores'])} stores, {d['total_qty']} {d['uom']}",
                expanded=False,
            ):
                disp = pd.DataFrame(d["stores"]).rename(columns={"store": "Store", "qty": "Qty"})
                total_row = pd.DataFrame([{"Store": "── TOTAL", "Qty": d["total_qty"]}])
                disp = pd.concat([disp, total_row], ignore_index=True)
                st.dataframe(
                    disp, use_container_width=True, hide_index=True,
                    height=min(300, 40 + len(disp) * 36),
                )

        # Download combined PDF
        del_dates_multi = filtered['Delivery Date'].dropna().unique()
        del_multi = del_dates_multi[0] if len(del_dates_multi) > 0 else ""

        combined_alloc_pdf = _generate_multi_allocation_pdf(multi_items_data, del_multi)
        st.download_button(
            label=f"📄  Download Combined Allocation Report ({total_items} items)",
            data=combined_alloc_pdf,
            file_name=f"COMBINED_ALLOCATION_{del_multi}.pdf",
            mime="application/pdf",
            key="dl_multi_alloc",
        )




# ══════════════════════════════════════════════════════════════════════════════════
# TAB 4 — ALL ORDERS (Full Detail) + P2-H: Out-of-stock highlighting
# ══════════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown(f"""
    <div style="font-size:0.72rem; color:{MUTED}; margin-bottom:14px;">
      Complete extracted data from all uploaded PDFs
      {f' &nbsp;·&nbsp; <span class="out-badge">OUT</span> = Days to Last is 0 (out of stock)' if oos_count > 0 else ''}
    </div>
    """, unsafe_allow_html=True)

    display_cols = [
        'Store', 'Ordered By', 'Order Date', 'Delivery Date',
        'Location', 'PLU Code', 'Item Description',
        'Order Qty', 'UOM', 'Total Amount', 'Days to Last'
    ]
    # Only show columns that exist
    display_cols = [c for c in display_cols if c in filtered.columns]

    all_orders_display = filtered[display_cols].sort_values(
        ['Store', 'Location', 'Item Description']
    ).copy()

    st.dataframe(
        all_orders_display,
        use_container_width=True, hide_index=True, height=550,
        column_config={
            "Days to Last": st.column_config.NumberColumn(
                "Days to Last",
                help="0 = OUT OF STOCK",
                format="%.2f",
            ),
        }
    )

    st.markdown("<br>", unsafe_allow_html=True)
    e1, e2 = st.columns(2)
    with e1:
        csv = filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            "⬇ Export Filtered (CSV)",
            data=csv,
            file_name="SC_PDF_STORES_SUMMARY_01_filtered.csv",
            mime="text/csv"
        )
    with e2:
        csv_all = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "⬇ Export All Orders (CSV)",
            data=csv_all,
            file_name="SC_PDF_STORES_SUMMARY_01_all.csv",
            mime="text/csv"
        )


# ══════════════════════════════════════════════════════════════════════════════════
# TAB 5 — UNDELIVERED REPORT
# ══════════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown(f"""
    <div style="margin-bottom:16px;">
      <div style="font-size:0.65rem; letter-spacing:0.15em; color:{MUTED};
                  text-transform:uppercase; font-weight:600;">
        Flag undelivered items · system auto-fills which stores ordered it · add remarks · generate report
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Report Header Settings ───────────────────────────────────────────────────
    st.markdown(f'<div class="section-label">Report Settings</div>', unsafe_allow_html=True)
    rh1, rh2, rh3, rh4 = st.columns([2, 2, 2, 2])

    with rh1:
        report_title_input = st.text_input(
            "Report Title",
            value="DRY UNDELIVERED",
            placeholder="e.g. DRY UNDELIVERED, CHILLER UNDELIVERED",
            key="ud_title"
        )
    with rh2:
        auto_order_dates = sorted(filtered['Order Date'].dropna().unique()) if not filtered.empty else []
        auto_del_dates   = sorted(filtered['Delivery Date'].dropna().unique()) if not filtered.empty else []
        ud_order_date = st.text_input(
            "Order Date",
            value=auto_order_dates[0] if auto_order_dates else "",
            key="ud_order_date"
        )
    with rh3:
        ud_del_date = st.text_input(
            "Delivery Date",
            value=auto_del_dates[0] if auto_del_dates else "",
            key="ud_del_date"
        )
    with rh4:
        ud_prepared_by = st.text_input("Prepared By", placeholder="e.g. MICHAEL", key="ud_prep_by")

    st.markdown("---")

    # ── Section 1: Original Undelivered Item Form (row-by-row) ────────────────
    st.markdown(f'<div class="section-label">Add Undelivered Item (row-by-row)</div>', unsafe_allow_html=True)

    fa1, fa2 = st.columns([2, 3])

    with fa1:
        all_items_ud = sorted(filtered['Item Description'].dropna().unique()) if not filtered.empty else []
        sel_ud_item = st.selectbox(
            "Item Not Available",
            ["— select item —"] + all_items_ud,
            key="ud_item_sel"
        )

    with fa2:
        if sel_ud_item and sel_ud_item != "— select item —":
            stores_ordered = sorted(
                filtered[filtered['Item Description'] == sel_ud_item]['Store']
                .dropna().unique().tolist()
            )
        else:
            stores_ordered = sorted(filtered['Store'].dropna().unique().tolist()) if not filtered.empty else []

        sel_ud_stores = st.multiselect(
            "Affected Stores",
            stores_ordered,
            default=stores_ordered,
            key="ud_stores_sel",
            help="Pre-selected stores that ordered this item — deselect any that DID receive it"
        )

    fb1, fb2 = st.columns([4, 1])
    with fb1:
        ud_remarks = st.text_input(
            "Remarks",
            placeholder="e.g. AVAILABLE TOMORROW, AVAILABLE ON MONDAY, OUT OF STOCK",
            key="ud_remarks"
        )
    with fb2:
        st.markdown("<br>", unsafe_allow_html=True)
        add_clicked = st.button("➕  Add", key="ud_add_btn", use_container_width=True)

    if add_clicked:
        if sel_ud_item == "— select item —":
            st.warning("Please select an item first.")
        elif not sel_ud_stores:
            st.warning("Please select at least one store.")
        else:
            for store in sel_ud_stores:
                mask = (
                    (filtered['Item Description'] == sel_ud_item) &
                    (filtered['Store'] == store)
                )
                qty_val = filtered.loc[mask, 'Order Qty'].sum()
                qty_val = int(qty_val) if pd.notna(qty_val) and qty_val > 0 else 1

                st.session_state.undelivered_rows.append({
                    'item':    sel_ud_item,
                    'store':   store,
                    'qty':     qty_val,
                    'remarks': ud_remarks.strip().upper() if ud_remarks else "",
                })
            st.success(f"Added **{sel_ud_item}** for {len(sel_ud_stores)} store(s).")
            st.rerun()

    st.markdown("---")

    # ── Current Undelivered List ─────────────────────────────────────────────────
    if not st.session_state.undelivered_rows:
        st.markdown(f"""
        <div style="padding:24px; text-align:center; color:{MUTED};
                    border:1px dashed {BORDER}; border-radius:4px;">
          <div style="font-size:0.75rem; letter-spacing:0.1em; text-transform:uppercase;">
            No undelivered items added yet
          </div>
          <div style="font-size:0.72rem; margin-top:6px;">
            Select an item above and click ➕ Add to Report
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="section-label">Undelivered Items — {len(st.session_state.undelivered_rows)} rows</div>',
                    unsafe_allow_html=True)

        ud_df = pd.DataFrame(st.session_state.undelivered_rows)
        ud_df.columns = ['Item', 'Store', 'Qty', 'Remarks']

        edited_df = st.data_editor(
            ud_df,
            use_container_width=True,
            hide_index=False,
            num_rows="dynamic",
            column_config={
                "Item":    st.column_config.TextColumn("Item Description", width="large"),
                "Store":   st.column_config.TextColumn("Store", width="medium"),
                "Qty":     st.column_config.NumberColumn("Qty", min_value=0, width="small"),
                "Remarks": st.column_config.TextColumn("Remarks", width="large"),
            },
            key="ud_editor"
        )

        if edited_df is not None:
            st.session_state.undelivered_rows = edited_df.rename(columns={
                'Item': 'item', 'Store': 'store', 'Qty': 'qty', 'Remarks': 'remarks'
            }).to_dict('records')

        bc1, bc2, bc3 = st.columns([2, 2, 3])
        with bc1:
            if st.button("🗑  Clear All Rows", key="ud_clear"):
                st.session_state.undelivered_rows = []
                st.rerun()

        with bc2:
            if st.session_state.undelivered_rows:
                html_ud = make_undelivered_html(
                    rows          = st.session_state.undelivered_rows,
                    report_title  = report_title_input or "UNDELIVERED REPORT",
                    order_date    = ud_order_date,
                    delivery_date = ud_del_date,
                    prepared_by   = ud_prepared_by or "—",
                )
                title_safe = re.sub(r'[^\w\s-]', '', report_title_input or "UNDELIVERED").replace(' ', '_')
                st.download_button(
                    label="🖨  Download Report (HTML)",
                    data=html_ud.encode('utf-8'),
                    file_name=f"{title_safe}_{ud_del_date}.html",
                    mime="text/html",
                    key="ud_download"
                )

        with bc3:
            st.markdown(
                f'<div style="font-size:0.7rem; color:{MUTED}; margin-top:8px;">'
                'Download → open in browser → Ctrl+P to print</div>',
                unsafe_allow_html=True
            )

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════════════
    # Section 2: ITEMS NOT AVAILABLE TODAY (instant-add, grouped by item)
    # ══════════════════════════════════════════════════════════════════════════════
    st.markdown(f'<div class="section-label">Items Not Available Today</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:0.7rem; color:{MUTED}; margin-bottom:12px;">'
        f'Select items one by one — they are instantly added to the list below. '
        f'Add remarks inline after adding. Generate the Allocation Guide PDF when ready.</div>',
        unsafe_allow_html=True,
    )

    # Build the options list excluding already-added items
    existing_na_items = {e["item"] for e in st.session_state.unavailable_items}
    all_items_na = sorted(filtered['Item Description'].dropna().unique()) if not filtered.empty else []
    available_na_options = [it for it in all_items_na if it not in existing_na_items]

    # Instant-add selectbox: selecting any item immediately adds it
    sel_na_item = st.selectbox(
        "Select unavailable item (instant add)",
        [""] + available_na_options,
        format_func=lambda x: "— click to select an item —" if x == "" else x,
        key="na_item_sel",
    )

    # When a non-empty item is selected, instantly add it and rerun
    if sel_na_item and sel_na_item != "":
        item_data = filtered[filtered['Item Description'] == sel_na_item]
        store_rows = []
        for store_name in sorted(item_data['Store'].dropna().unique()):
            store_mask = item_data['Store'] == store_name
            qty = item_data.loc[store_mask, 'Order Qty'].sum()
            qty = int(qty) if pd.notna(qty) and qty > 0 else 1
            uom_vals = item_data.loc[store_mask, 'UOM'].dropna().unique()
            uom = uom_vals[0] if len(uom_vals) > 0 else ""
            store_rows.append({"store": store_name, "qty": qty, "uom": uom})

        st.session_state.unavailable_items.append({
            "item": sel_na_item,
            "remarks": "",
            "stores": store_rows,
        })
        st.rerun()

    # Display current unavailable items list
    if st.session_state.unavailable_items:
        st.markdown(
            f'<div class="section-label" style="margin-top:12px;">'
            f'{len(st.session_state.unavailable_items)} item(s) marked unavailable</div>',
            unsafe_allow_html=True,
        )

        for idx, entry in enumerate(st.session_state.unavailable_items):
            item_name = entry["item"]
            remarks = entry.get("remarks", "")
            stores = entry.get("stores", [])
            total_qty = sum(s.get("qty", 0) for s in stores)

            with st.expander(
                f"**{item_name}** — {len(stores)} stores, {total_qty} units"
                + (f"  ·  _{remarks}_" if remarks else ""),
                expanded=False,
            ):
                if stores:
                    st.dataframe(
                        pd.DataFrame(stores).rename(columns={"store": "Store", "qty": "Qty", "uom": "UOM"}),
                        use_container_width=True,
                        hide_index=True,
                        height=min(250, 40 + len(stores) * 36),
                    )
                # Inline remark field — editable per item
                new_remark = st.text_input(
                    "Remarks",
                    value=remarks,
                    placeholder="e.g. AVAILABLE TOMORROW, OUT OF STOCK",
                    key=f"na_remark_{idx}",
                )
                if new_remark != remarks:
                    st.session_state.unavailable_items[idx]["remarks"] = new_remark.strip().upper()

                if st.button("🗑 Remove", key=f"na_remove_{idx}"):
                    st.session_state.unavailable_items.pop(idx)
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # Generate Allocation Guide PDF
        na_bc1, na_bc2 = st.columns([2, 3])
        with na_bc1:
            if st.button("🗑  Clear All Unavailable Items", key="na_clear_all"):
                st.session_state.unavailable_items = []
                st.rerun()
        with na_bc2:
            pdf_bytes = _generate_combined_pdf(
                unavailable_items=st.session_state.unavailable_items,
                manual_orders=[],
                report_title=report_title_input or "ALLOCATION GUIDE",
                order_date=ud_order_date,
                delivery_date=ud_del_date,
                prepared_by=ud_prepared_by or "—",
            )
            title_safe = re.sub(r'[^\w\s-]', '', report_title_input or "ALLOCATION_GUIDE").replace(' ', '_')
            st.download_button(
                label="📄  Download Allocation Guide (PDF)",
                data=pdf_bytes,
                file_name=f"{title_safe}_ALLOCATION_{ud_del_date}.pdf",
                mime="application/pdf",
                key="na_download_pdf",
            )
    else:
        st.markdown(f"""
        <div style="padding:18px; text-align:center; color:{MUTED};
                    border:1px dashed {BORDER}; border-radius:4px; margin-top:8px;">
          <div style="font-size:0.72rem; letter-spacing:0.08em; text-transform:uppercase;">
            No unavailable items added yet — select items above
          </div>
        </div>
        """, unsafe_allow_html=True)



# ══════════════════════════════════════════════════════════════════════════════════
# TAB 6 — MANUAL ORDERS
# ══════════════════════════════════════════════════════════════════════════════════
with tab6:
    st.markdown(f"""
    <div style="margin-bottom:16px;">
      <div style="font-size:0.65rem; letter-spacing:0.15em; color:{MUTED};
                  text-transform:uppercase; font-weight:600;">
        Add orders that came in verbally or by hand — not in any uploaded PDF
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Add Manual Order Form ─────────────────────────────────────────────────
    st.markdown(f'<div class="section-label">Add Manual Order</div>', unsafe_allow_html=True)

    mo_c1, mo_c2, mo_c3, mo_c4 = st.columns([2, 3, 1, 1])
    with mo_c1:
        # Store dropdown from master list or parsed data
        all_stores_mo = sorted(df['Store'].dropna().unique()) if not df.empty else []
        mo_store = st.selectbox(
            "Store",
            ["— select store —"] + all_stores_mo,
            key="mo_store_sel",
        )
    with mo_c2:
        mo_item = st.text_input("Item Name", placeholder="e.g. CHICKEN BREAST", key="mo_item")
    with mo_c3:
        mo_qty = st.number_input("Qty", min_value=0, value=1, step=1, key="mo_qty")
    with mo_c4:
        mo_uom = st.text_input("UOM", placeholder="e.g. KG, PCS", key="mo_uom")

    mo_r1, mo_r2 = st.columns([4, 1])
    with mo_r1:
        mo_remarks = st.text_input(
            "Remarks",
            placeholder="e.g. VERBAL ORDER FROM MANAGER, PHONE ORDER",
            key="mo_remarks",
        )
    with mo_r2:
        st.markdown("<br>", unsafe_allow_html=True)
        mo_add = st.button("➕  Add Order", key="mo_add_btn", use_container_width=True)

    if mo_add:
        if mo_store == "— select store —":
            st.warning("Please select a store.")
        elif not mo_item or not mo_item.strip():
            st.warning("Please enter an item name.")
        elif mo_qty <= 0:
            st.warning("Qty must be greater than 0.")
        else:
            st.session_state.manual_orders.append({
                "store": mo_store,
                "item": mo_item.strip().upper(),
                "qty": int(mo_qty),
                "uom": mo_uom.strip().upper() if mo_uom else "",
                "remarks": mo_remarks.strip().upper() if mo_remarks else "",
            })
            st.success(f"Added **{mo_item.strip().upper()}** × {int(mo_qty)} for **{mo_store}**.")
            st.rerun()

    st.markdown("---")

    # ── Current Manual Orders List ────────────────────────────────────────────
    if not st.session_state.manual_orders:
        st.markdown(f"""
        <div style="padding:24px; text-align:center; color:{MUTED};
                    border:1px dashed {BORDER}; border-radius:4px;">
          <div style="font-size:0.75rem; letter-spacing:0.1em; text-transform:uppercase;">
            No manual orders added yet
          </div>
          <div style="font-size:0.72rem; margin-top:6px;">
            Use the form above to add verbal or hand-written orders
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="section-label">Manual Orders — {len(st.session_state.manual_orders)} entries</div>',
            unsafe_allow_html=True,
        )

        mo_df = pd.DataFrame(st.session_state.manual_orders)
        mo_df.columns = ['Store', 'Item', 'Qty', 'UOM', 'Remarks']

        edited_mo = st.data_editor(
            mo_df,
            use_container_width=True,
            hide_index=False,
            num_rows="dynamic",
            column_config={
                "Store":   st.column_config.TextColumn("Store", width="medium"),
                "Item":    st.column_config.TextColumn("Item", width="large"),
                "Qty":     st.column_config.NumberColumn("Qty", min_value=0, width="small"),
                "UOM":     st.column_config.TextColumn("UOM", width="small"),
                "Remarks": st.column_config.TextColumn("Remarks", width="medium"),
            },
            key="mo_editor",
        )

        if edited_mo is not None:
            st.session_state.manual_orders = edited_mo.rename(columns={
                'Store': 'store', 'Item': 'item', 'Qty': 'qty', 'UOM': 'uom', 'Remarks': 'remarks'
            }).to_dict('records')

        mo_bc1, mo_bc2 = st.columns([2, 3])
        with mo_bc1:
            if st.button("🗑  Clear All Manual Orders", key="mo_clear"):
                st.session_state.manual_orders = []
                st.rerun()

    st.markdown("---")

    # ── Generate Combined Report PDF ──────────────────────────────────────────
    st.markdown(f'<div class="section-label">Generate Combined Report</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:0.7rem; color:{MUTED}; margin-bottom:12px;">'
        f'Combines unavailable items from the Undelivered Report tab + manual orders from this tab into one PDF.</div>',
        unsafe_allow_html=True,
    )

    has_undelivered = bool(st.session_state.undelivered_rows)
    has_manual = bool(st.session_state.manual_orders)

    if not has_undelivered and not has_manual:
        st.markdown(
            f'<div style="font-size:0.72rem; color:{MUTED}; padding:12px; '
            f'border:1px dashed {BORDER}; border-radius:4px; text-align:center;">'
            f'No data to generate report — add undelivered items in the Undelivered Report tab '
            f'and/or add manual orders above.</div>',
            unsafe_allow_html=True,
        )
    else:
        # Summary of what will be included
        summary_parts = []
        if has_undelivered:
            summary_parts.append(f"{len(st.session_state.undelivered_rows)} undelivered row(s)")
        if has_manual:
            summary_parts.append(f"{len(st.session_state.manual_orders)} manual order(s)")
        st.markdown(
            f'<div style="font-size:0.72rem; color:{TEXT}; margin-bottom:8px;">'
            f'Report will include: {" + ".join(summary_parts)}</div>',
            unsafe_allow_html=True,
        )

        # Use the same report settings from the Undelivered Report tab
        r_title = st.session_state.get("ud_title", "COMBINED REPORT")
        r_order = st.session_state.get("ud_order_date", "")
        r_del = st.session_state.get("ud_del_date", "")
        r_prep = st.session_state.get("ud_prep_by", "—")

        combined_pdf = _generate_combined_pdf(
            unavailable_items=[],
            manual_orders=st.session_state.manual_orders,
            report_title=r_title or "COMBINED REPORT",
            order_date=r_order,
            delivery_date=r_del,
            prepared_by=r_prep or "—",
            undelivered_rows=st.session_state.undelivered_rows,
        )
        title_safe = re.sub(r'[^\w\s-]', '', r_title or "COMBINED_REPORT").replace(' ', '_')
        st.download_button(
            label="📄  Download Combined Report (PDF)",
            data=combined_pdf,
            file_name=f"{title_safe}_COMBINED_{r_del}.pdf",
            mime="application/pdf",
            key="mo_combined_pdf",
        )
        st.markdown(
            f'<div style="font-size:0.7rem; color:{MUTED}; margin-top:6px;">'
            f'Uses Report Settings from the Undelivered Report tab (title, dates, prepared by)</div>',
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════════
# TAB 7 — STORE CHECKLIST (private Google Sheet via service account)
# ══════════════════════════════════════════════════════════════════════════════════

_MASTER_SHEET_ID = "1eNFzPEpMnxi2GQupi_Ed9_owJMJllrpTzg0kVuyZtDU"
_MASTER_SHEET_NAME = "STORE LIST"

# Prefix → display name mapping for auto-grouping stores from the flat sheet list.
# Prefixes are checked in order; first match wins. Longer prefixes first to avoid
# "ABC-" catching "ABC-(CS)" or "ABC-(F)" before their specific rules.
_PREFIX_GROUP_MAP = [
    ("ABC-(CS)",   "ABC COFFEE SHOPS"),
    ("ABC-(F)",    "ABC FULL SERVICE"),
    ("ABC-",       "ABC STORES"),
    ("TCS-",       "TAG CONCESSIONS"),
    ("PHT-",       "PHAT PHO"),
    ("TAV-",       "TAVERNA"),
    ("AE-",        "ABACA EATS"),
    ("REEF-",      "REEF"),
    ("RN1-",       "RN1 COMMISSARY"),
    ("RN1 -",      "RN1 COMMISSARY"),
    ("RNO-",       "RNO"),
    ("MAYA-",      "MAYA"),
    ("TCS ",       "TAG CONCESSIONS"),
    ("REEF ",      "REEF"),
    ("ADMIN",      "ADMIN / SUPPORT"),
    ("COMMISSARY", "ADMIN / SUPPORT"),
    ("DAVE",       "ADMIN / SUPPORT"),
    ("RESEARCH",   "ADMIN / SUPPORT"),
]


def _get_gspread_client():
    """Build a gspread client from Streamlit secrets (service account JSON)."""
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes,
    )
    return gspread.authorize(creds)


def _auto_group_stores(store_names: list[str]) -> dict[str, list[str]]:
    """Group a flat list of store names by prefix into an ordered dict."""
    from collections import OrderedDict
    grouped: dict[str, list[str]] = OrderedDict()
    for name in store_names:
        upper = name.upper()
        matched_group = "OTHER"
        for prefix, group_name in _PREFIX_GROUP_MAP:
            if upper.startswith(prefix.upper()):
                matched_group = group_name
                break
        grouped.setdefault(matched_group, []).append(name)
    return grouped


def _fetch_master_stores() -> dict[str, list[str]]:
    """Fetch the master store list from the private Google Sheet.
    Auto-groups stores by prefix since the sheet is a flat list.
    Returns dict like {"ABC STORES": ["ABC-AYALA-BAR", ...], ...}.
    """
    try:
        gc = _get_gspread_client()
        sh = gc.open_by_key(_MASTER_SHEET_ID)
        ws = sh.worksheet(_MASTER_SHEET_NAME)
        all_values = ws.col_values(1)  # read first column (A)

        # Filter empty rows and strip whitespace
        stores = [v.strip() for v in all_values if v and v.strip()]

        if not stores:
            st.warning("Master store list sheet is empty.")
            return {}

        return _auto_group_stores(stores)
    except KeyError:
        st.error(
            "**Service account credentials not found.** "
            "Add `[gcp_service_account]` to `.streamlit/secrets.toml` "
            "with your service account JSON keys."
        )
        return {}
    except Exception as e:
        st.error(f"**Failed to fetch master store list:** {e}")
        return {}


def _normalize_store(name: str) -> str:
    """Normalize a store name for matching between master list and parsed PDFs.
    Strips: type codes -(CS)/(F), trailing suffixes (CS 2)/(FS)/(1), date remnants.
    'ABC-(CS) CYBER' → 'ABC-CYBER', 'ABC-(F) TGU-BAR (FS)' → 'ABC-TGU-BAR'.
    """
    n = name.upper().strip()
    # Strip date suffix and everything after: ' - MM_DD_YY...'
    n = re.sub(r'\s*-\s*\d{2}_\d{2}_\d{2,4}.*$', '', n).strip()
    # Strip trailing parenthetical suffixes: (CS 2), (CS 1), (FS), (F), (1), etc.
    n = re.sub(r'\s*\((?:CS\s*\d*|FS|F|B|\d+)\)\s*$', '', n).strip()
    n = re.sub(r'\s*\((?:CS\s*\d*|FS|F|B|\d+)\)\s*$', '', n).strip()
    # Remove -(XX) type codes from master list names: "-(CS) " or "-(F) "
    n = re.sub(r'-\([A-Z]+\)\s*', '-', n)
    # Collapse double dashes and normalize whitespace
    n = re.sub(r'-{2,}', '-', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def _check_bar_kitchen(store: str, loaded_stores: set[str]) -> tuple[bool, bool]:
    """Check if BAR and KITCHEN PDFs exist for a given master store name.
    Normalizes both sides (strips type codes) before comparing.
    """
    norm = _normalize_store(store)
    bar_found = False
    kitchen_found = False
    for ls in loaded_stores:
        ls_norm = _normalize_store(ls)
        if ls_norm == f"{norm}-BAR" or ls_norm == f"{norm} BAR":
            bar_found = True
        if ls_norm == f"{norm}-KITCHEN" or ls_norm == f"{norm} KITCHEN":
            kitchen_found = True
        if bar_found and kitchen_found:
            break
    return bar_found, kitchen_found


def _is_rn1_store(store: str) -> bool:
    """RN1 stores only submit one PDF (no BAR/KITCHEN split)."""
    return store.upper().startswith("RN1")


def _check_rn1_submitted(store: str, loaded_stores: set[str]) -> bool:
    """For RN1 stores, check if any PDF matching the store name was parsed."""
    norm = _normalize_store(store)
    for ls in loaded_stores:
        ls_norm = _normalize_store(ls)
        if ls_norm == norm or ls_norm.startswith(norm):
            return True
    return False


def _render_store_group(title: str, stores: list[str], loaded_stores: set[str]):
    """Render a category block with BAR / KITCHEN status columns."""
    # Category header — columns: Name | BAR | KITCHEN (or SUBMITTED for RN1)
    is_rn1_group = all(_is_rn1_store(s) for s in stores) if stores else False

    if is_rn1_group:
        col_header = (
            f'<div style="display:flex; align-items:center; gap:0; '
            f'background:rgba(201,169,110,0.18); border:1px solid {GOLD}; '
            f'border-radius:3px; padding:6px 12px; margin-bottom:2px; '
            f'font-size:0.68rem; font-weight:700; letter-spacing:0.1em; '
            f'text-transform:uppercase; color:{GOLD};">'
            f'<span style="flex:3;">{title}</span>'
            f'<span style="flex:1; text-align:center;">SUBMITTED</span>'
            f'</div>'
        )
    else:
        col_header = (
            f'<div style="display:flex; align-items:center; gap:0; '
            f'background:rgba(201,169,110,0.18); border:1px solid {GOLD}; '
            f'border-radius:3px; padding:6px 12px; margin-bottom:2px; '
            f'font-size:0.68rem; font-weight:700; letter-spacing:0.1em; '
            f'text-transform:uppercase; color:{GOLD};">'
            f'<span style="flex:3;">{title}</span>'
            f'<span style="flex:1; text-align:center;">BAR</span>'
            f'<span style="flex:1; text-align:center;">KITCHEN</span>'
            f'</div>'
        )
    st.markdown(col_header, unsafe_allow_html=True)

    # Store rows
    for store in stores:
        if _is_rn1_store(store):
            submitted = _check_rn1_submitted(store, loaded_stores)
            icon = "✅" if submitted else "❌"
            name_color = TEXT if submitted else MUTED
            st.markdown(
                f'<div style="display:flex; align-items:center; gap:0; '
                f'padding:4px 12px; border-bottom:1px solid {BORDER}; '
                f'font-size:0.78rem; color:{name_color};">'
                f'<span style="flex:3;">{store}</span>'
                f'<span style="flex:1; text-align:center; font-size:0.85rem;">{icon}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            bar_ok, kit_ok = _check_bar_kitchen(store, loaded_stores)
            bar_icon = "✅" if bar_ok else "❌"
            kit_icon = "✅" if kit_ok else "❌"
            both_ok = bar_ok and kit_ok
            name_color = TEXT if both_ok else MUTED
            st.markdown(
                f'<div style="display:flex; align-items:center; gap:0; '
                f'padding:4px 12px; border-bottom:1px solid {BORDER}; '
                f'font-size:0.78rem; color:{name_color};">'
                f'<span style="flex:3;">{store}</span>'
                f'<span style="flex:1; text-align:center; font-size:0.85rem;">{bar_icon}</span>'
                f'<span style="flex:1; text-align:center; font-size:0.85rem;">{kit_icon}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


def _compute_checklist_summary(groups: dict[str, list[str]], loaded_stores: set[str]) -> tuple[int, int]:
    """Return (fully_complete_count, total_stores) across all groups.
    A non-RN1 store is 'complete' when both BAR and KITCHEN are received.
    An RN1 store is 'complete' when its single PDF is received.
    """
    complete = 0
    total = 0
    for stores in groups.values():
        for store in stores:
            total += 1
            if _is_rn1_store(store):
                if _check_rn1_submitted(store, loaded_stores):
                    complete += 1
            else:
                bar_ok, kit_ok = _check_bar_kitchen(store, loaded_stores)
                if bar_ok and kit_ok:
                    complete += 1
    return complete, total


def _all_expected_pdf_names(groups: dict[str, list[str]]) -> set[str]:
    """Build a set of all expected *normalized* store names for unrecognized-store detection.
    Non-RN1 stores expect STORE-BAR and STORE-KITCHEN; RN1 stores expect the store name itself.
    Uses normalized names (type codes stripped) so parsed PDF names match.
    """
    expected = set()
    for stores in groups.values():
        for store in stores:
            norm = _normalize_store(store)
            if _is_rn1_store(store):
                expected.add(norm)
            else:
                expected.add(f"{norm}-BAR")
                expected.add(f"{norm} BAR")
                expected.add(f"{norm}-KITCHEN")
                expected.add(f"{norm} KITCHEN")
    return expected


with tab7:
    st.markdown(f"""
    <div style="margin-bottom:12px;">
      <div style="font-size:0.65rem; letter-spacing:0.15em; color:{MUTED};
                  text-transform:uppercase; font-weight:600;">
        Master store list from Google Sheet → compare against parsed PDFs → see who's missing
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Session state for grouped master list ──────────────────────────────────
    if 'checklist_groups' not in st.session_state:
        st.session_state.checklist_groups = {}   # {category: [store, ...]}
    if 'checklist_loaded' not in st.session_state:
        st.session_state.checklist_loaded = False

    # Auto-fetch on first visit
    if not st.session_state.checklist_loaded:
        with st.spinner("Loading master store list from Google Sheet…"):
            groups = _fetch_master_stores()
        if groups:
            st.session_state.checklist_groups = groups
            st.session_state.checklist_loaded = True
            total = sum(len(v) for v in groups.values())
            st.success(f"✓ Loaded **{total}** stores from Google Sheet")

    # Manual refresh button
    if st.button("🔄  Refresh from Sheet", key="refresh_master_sheet"):
        with st.spinner("Refreshing master store list…"):
            groups = _fetch_master_stores()
        if groups:
            st.session_state.checklist_groups = groups
            st.session_state.checklist_loaded = True
            total = sum(len(v) for v in groups.values())
            st.success(f"✓ Loaded **{total}** stores from Google Sheet")

    st.markdown("---")

    # ── Checklist display ──────────────────────────────────────────────────────
    groups = st.session_state.checklist_groups
    loaded_stores = set(df['Store'].dropna().unique()) if not df.empty else set()
    today_str = pd.Timestamp.now().strftime("%B %d, %Y")

    if not groups:
        st.markdown(f"""
        <div style="padding:36px; text-align:center; color:{MUTED};
                    border:1px dashed {BORDER}; border-radius:4px;">
          <div style="font-size:0.8rem; letter-spacing:0.1em; text-transform:uppercase;">
            No master store list loaded
          </div>
          <div style="font-size:0.72rem; margin-top:8px;">
            Check that <code>[gcp_service_account]</code> is configured in Streamlit secrets
            and the service account has access to the Sheet.
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        all_master = [s for stores in groups.values() for s in stores]
        master_set = set(all_master)
        complete_count, total_expected = _compute_checklist_summary(groups, loaded_stores)

        # Date header
        st.markdown(
            f'<div style="font-size:0.85rem; font-weight:600; color:{TEXT}; '
            f'margin-bottom:16px;">DATE: {today_str}</div>',
            unsafe_allow_html=True,
        )

        # Summary pills
        summary_color = GREEN if complete_count == total_expected else GOLD
        st.markdown(f"""
        <div style="display:flex; gap:16px; margin-bottom:16px; flex-wrap:wrap;">
          <span class="info-pill" style="color:{summary_color};">
            ✅ {complete_count} of {total_expected} stores fully complete
            (both BAR and KITCHEN received)
          </span>
          <span class="info-pill" style="color:{RED}; border-color:{RED};">
            ❌ {total_expected - complete_count} incomplete
          </span>
        </div>
        """, unsafe_allow_html=True)

        # ── 2-column grid grouped by prefix ───────────────────────────────────
        cat_list = list(groups.keys())
        pairs = []
        for i in range(0, len(cat_list), 2):
            left = cat_list[i] if i < len(cat_list) else None
            right = cat_list[i + 1] if i + 1 < len(cat_list) else None
            pairs.append((left, right))

        for left_cat, right_cat in pairs:
            col_left, col_right = st.columns(2)
            with col_left:
                if left_cat and left_cat in groups:
                    _render_store_group(left_cat, groups[left_cat], loaded_stores)
            with col_right:
                if right_cat and right_cat in groups:
                    _render_store_group(right_cat, groups[right_cat], loaded_stores)
            st.markdown("<br>", unsafe_allow_html=True)

        # ── Unrecognized Stores ───────────────────────────────────────────────
        # A loaded store is "unrecognized" if it doesn't match any expected PDF name
        expected_names = _all_expected_pdf_names(groups)
        unrecognized = sorted(
            s for s in loaded_stores
            if _normalize_store(s) not in expected_names
        )
        if unrecognized:
            st.markdown("---")
            st.markdown(
                f'<div class="section-label">Unrecognized Stores — '
                f'not in master list ({len(unrecognized)})</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div style="font-size:0.7rem; color:{MUTED}; margin-bottom:8px;">'
                f'These stores appeared in parsed PDFs but do not match any name in the '
                f'master list. Check for renamed stores or typos.</div>',
                unsafe_allow_html=True,
            )
            unrec_df = pd.DataFrame([
                {
                    'Store': s,
                    'Lines': int(df[df['Store'] == s].shape[0]),
                    'Amount': f"₱{df[df['Store'] == s]['Total Amount'].sum():,.2f}",
                }
                for s in unrecognized
            ])
            st.dataframe(unrec_df, use_container_width=True, hide_index=True)
