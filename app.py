import streamlit as st
import pdfplumber
import pandas as pd
import re
import io
from pathlib import Path
import plotly.graph_objects as go

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


def parse_pdf(pdf_bytes: bytes, filename: str) -> pd.DataFrame:
    rows = []
    store_name    = Path(filename).stem
    order_date    = ""
    delivery_date = ""

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if page_num == 0:
                    extracted = extract_store_name(text)
                    if extracted and extracted != "UNKNOWN":
                        store_name = extracted
                    order_date    = extract_date(text, "ORDER DATE")
                    delivery_date = extract_date(text, "DELIVERY DATE")

                tables = page.extract_tables({
                    "vertical_strategy":   "lines",
                    "horizontal_strategy": "lines"
                })
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    header_idx = None
                    for i, row in enumerate(table):
                        if row and any('LOCATION' in str(cell or '').upper() for cell in row):
                            header_idx = i
                            break
                    if header_idx is None:
                        continue

                    def flat(cell):
                        return ' '.join(str(cell or '').split()).upper()

                    header = [flat(h) for h in table[header_idx]]

                    def col(keyword):
                        for i, h in enumerate(header):
                            if keyword in h:
                                return i
                        return None

                    idx_loc   = col('LOCATION')
                    idx_plu   = col('PLU')
                    idx_order = col('ORDER')
                    idx_item  = col('ITEM') or col('DESCRIPTION')
                    idx_uom   = col('UOM')
                    idx_amt   = col('TOTAL AMOUNT') or col('AMOUNT')
                    idx_days  = col('DAYS')

                    for row in table[header_idx + 1:]:
                        if not row:
                            continue

                        def get(idx):
                            if idx is None or idx >= len(row):
                                return ''
                            return ' '.join(str(row[idx] or '').split()).strip()

                        location = get(idx_loc)
                        item     = get(idx_item)

                        if not location or location.upper() == 'LOCATION':
                            continue
                        if not item or item.upper() in ('ITEM DESCRIPTION', 'DESCRIPTION'):
                            continue

                        rows.append({
                            'Store':            store_name,
                            'Order Date':       order_date,
                            'Delivery Date':    delivery_date,
                            'Location':         location,
                            'PLU Code':         get(idx_plu),
                            'Order Qty':        get(idx_order),
                            'Item Description': item,
                            'UOM':              get(idx_uom),
                            'Total Amount':     get(idx_amt),
                            'Days to Last':     get(idx_days),
                        })
    except Exception as e:
        st.warning(f"Could not parse **{filename}**: {e}")

    return pd.DataFrame(rows)


def clean_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(',', '').str.strip(),
        errors='coerce'
    )


# ─── PRINT HTML GENERATORS ──────────────────────────────────────────────────────

def make_picklist_html(df_loc: pd.DataFrame, location: str, delivery_date: str) -> str:
    """Generates a print-ready Outside/Location Picklist (matches manual format)."""

    # Sort by item, then store
    df_sorted = df_loc.sort_values(['Item Description', 'Store'])

    # Build rows
    detail_rows_html = ""
    for _, r in df_sorted.iterrows():
        detail_rows_html += f"""
        <tr>
          <td>{r['Store']}</td>
          <td>{r['Item Description']}</td>
          <td style="text-align:center;">{int(r['Order Qty']) if pd.notna(r['Order Qty']) else '-'}</td>
        </tr>"""

    # Build summary
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
          <td style="text-align:center; font-weight:bold;">{int(r['Order Qty']) if pd.notna(r['Order Qty']) else '-'}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{location} PICKLIST</title>
<style>
  body {{ font-family: Arial, sans-serif; font-size: 10pt; margin: 20px; }}
  .title {{ font-size: 14pt; font-weight: bold; text-align: center;
            background: #d0d0f0; padding: 8px; border: 1px solid #999; margin-bottom: 0; }}
  .header-table {{ width: 100%; border-collapse: collapse; margin-bottom: 12px; }}
  .header-table td {{ padding: 4px 8px; border: 1px solid #999; font-size: 10pt; }}
  .date-red {{ color: red; font-weight: bold; }}
  table.data {{ width: 100%; border-collapse: collapse; margin-bottom: 14px; }}
  table.data th {{
    background: #cccccc; border: 1px solid #666;
    padding: 5px 8px; font-size: 9pt; text-align: left;
  }}
  table.data td {{ border: 1px solid #aaa; padding: 4px 8px; font-size: 9pt; }}
  .summary-header td {{
    background: #FFFF00; font-weight: bold; border: 1px solid #666;
    padding: 5px 8px; font-size: 9pt;
  }}
  .summary-row td {{ background: #FFFACD; border: 1px solid #aaa; padding: 4px 8px; font-size: 9pt; }}
  @media print {{
    body {{ margin: 10mm; }}
    button {{ display: none; }}
  }}
</style>
</head>
<body>
<div class="title">{location} PICKLIST</div>
<table class="header-table">
  <tr>
    <td><b>DELIVERY DATE:</b></td>
    <td class="date-red">{delivery_date}</td>
    <td><b>LOCATION:</b></td>
    <td>{location}</td>
  </tr>
</table>

<table class="data">
  <thead>
    <tr>
      <th>STORE NAME</th>
      <th>ITEM DESCRIPTION</th>
      <th>QTY</th>
    </tr>
  </thead>
  <tbody>
    {detail_rows_html}
  </tbody>
</table>

<table class="data">
  <thead>
    <tr class="summary-header">
      <td colspan="3"><b>SUMMARY QTY</b></td>
    </tr>
  </thead>
  <tbody>
    {summary_rows_html}
  </tbody>
</table>

<button onclick="window.print()" style="margin-top:12px; padding:8px 20px;
  font-size:11pt; cursor:pointer; background:#444; color:white; border:none; border-radius:4px;">
  🖨 Print
</button>
</body>
</html>"""


def make_allocation_html(df_item: pd.DataFrame, item_name: str, delivery_date: str) -> str:
    """Generates a print-ready Item Allocation sheet (matches Eggs / Milk format)."""

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

    # UOM
    uom_vals = df_item['UOM'].dropna().unique()
    uom = uom_vals[0] if len(uom_vals) > 0 else ""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{item_name} — ORDER</title>
<style>
  body {{ font-family: Arial, sans-serif; font-size: 10pt; margin: 20px; max-width: 500px; }}
  .title {{
    font-size: 13pt; font-weight: bold; text-align: center;
    background: #d0d0f0; padding: 8px; border: 1px solid #999; margin-bottom: 0;
  }}
  table.data {{ width: 100%; border-collapse: collapse; }}
  table.data th {{
    background: #cccccc; border: 1px solid #666;
    padding: 5px 10px; font-size: 10pt;
  }}
  table.data td {{ border: 1px solid #aaa; padding: 5px 10px; font-size: 10pt; }}
  .header-row td {{ border: 1px solid #999; padding: 5px 10px; }}
  .label-col {{ font-weight: bold; }}
  .date-red {{ color: red; font-weight: bold; }}
  .total-row td {{ background: #FFFF00; font-weight: bold; border: 1px solid #666; padding: 5px 10px; }}
  @media print {{
    body {{ margin: 10mm; }}
    button {{ display: none; }}
  }}
</style>
</head>
<body>
<div class="title">{item_name}</div>
<table class="data" style="margin-bottom:12px;">
  <tr class="header-row">
    <td class="label-col">DELIVERY DATE:</td>
    <td class="date-red">{delivery_date}</td>
  </tr>
  <tr class="header-row">
    <td class="label-col">UOM:</td>
    <td>{uom}</td>
  </tr>
</table>

<table class="data">
  <thead>
    <tr>
      <th>STORE NAME</th>
      <th>QTY</th>
    </tr>
  </thead>
  <tbody>
    {rows_html}
    <tr class="total-row">
      <td>TOTAL</td>
      <td style="text-align:center;">{total_qty}</td>
    </tr>
  </tbody>
</table>

<button onclick="window.print()" style="margin-top:12px; padding:8px 20px;
  font-size:11pt; cursor:pointer; background:#444; color:white; border:none; border-radius:4px;">
  🖨 Print
</button>
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
            bg = ' style="background:#fff8dc; vertical-align:middle; font-weight:bold;"' if span > 1 else ''
            remarks_cell = f'<td{rs_attr}{bg}>{remark_val}</td>'
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

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{report_title}</title>
<style>
  body {{ font-family: Arial, sans-serif; font-size: 10pt; margin: 20px; }}
  .outer-table {{ width:100%; border-collapse:collapse; margin-bottom:0; }}
  .outer-table td {{ border:1px solid #999; vertical-align:middle; padding:6px 10px; }}
  .title-cell {{
    font-size:16pt; font-weight:bold; text-align:center;
    background:#e8e8f0; letter-spacing:0.05em;
  }}
  .meta-label {{ font-size:9pt; font-weight:bold; color:#444; }}
  .meta-value {{ font-size:10pt; font-weight:bold; }}
  table.data {{ width:100%; border-collapse:collapse; margin-top:10px; }}
  table.data th {{
    background:#cccccc; border:1px solid #666;
    padding:6px 8px; font-size:9pt; text-align:left;
  }}
  table.data td {{ border:1px solid #aaa; padding:5px 8px; font-size:9pt; }}
  table.data tr:nth-child(even) td {{ background:#f9f9f9; }}
  .footer {{
    margin-top:14px; font-size:8pt; color:#666;
    border-top:1px solid #ccc; padding-top:6px;
  }}
  @media print {{
    body {{ margin:10mm; }}
    button {{ display:none; }}
  }}
</style>
</head>
<body>

<table class="outer-table">
  <tr>
    <td rowspan="3" style="width:50%;"> </td>
    <td class="title-cell" colspan="2">{report_title}</td>
  </tr>
  <tr>
    <td class="meta-label">ORDER DATE:</td>
    <td class="meta-value">{order_date}</td>
  </tr>
  <tr>
    <td class="meta-label">DELIVERY DATE:</td>
    <td class="meta-value" style="color:#cc0000; font-weight:bold;">{delivery_date}</td>
  </tr>
  <tr>
    <td></td>
    <td class="meta-label">PREPARED BY:</td>
    <td class="meta-value">{prepared_by.upper()}</td>
  </tr>
</table>

<table class="data">
  <thead>
    <tr>
      <th>DATE</th>
      <th>STORE NAME</th>
      <th>ITEM DESCRIPTION</th>
      <th>QTY</th>
      <th>REMARKS</th>
    </tr>
  </thead>
  <tbody>
    {tr_html}
  </tbody>
</table>

<div class="footer">
  Generated by SC_PDF STORES SUMMARY_01 &nbsp;·&nbsp; The Abaca Group Supply Chain
</div>

<button onclick="window.print()" style="margin-top:14px; padding:8px 20px;
  font-size:11pt; cursor:pointer; background:#444; color:white; border:none; border-radius:4px;">
  🖨 Print
</button>

</body>
</html>"""


# ─── SESSION STATE ───────────────────────────────────────────────────────────────
if 'df' not in st.session_state:
    st.session_state.df              = pd.DataFrame()
    st.session_state.file_names      = set()
if 'undelivered_rows' not in st.session_state:
    st.session_state.undelivered_rows = []   # list of dicts


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

    uploaded_files = st.file_uploader(
        "Upload PDF Orders",
        type="pdf",
        accept_multiple_files=True,
        help="Drop all store PDFs here — supports 100+ at once"
    )

    if uploaded_files:
        new_files = [(f.name, f.read()) for f in uploaded_files]
        new_names = {n for n, _ in new_files}

        if new_names != st.session_state.file_names:
            progress = st.progress(0, text="Reading PDFs…")
            dfs = []
            for i, (name, data) in enumerate(new_files):
                df_i = parse_pdf(data, name)
                if not df_i.empty:
                    dfs.append(df_i)
                progress.progress((i + 1) / len(new_files), text=f"{i+1}/{len(new_files)}: {name}")
            progress.empty()

            if dfs:
                combined = pd.concat(dfs, ignore_index=True)
                combined['Order Qty']    = clean_numeric(combined['Order Qty'])
                combined['Total Amount'] = clean_numeric(combined['Total Amount'])
                combined['Days to Last'] = clean_numeric(combined['Days to Last'])
                combined = combined[combined['Item Description'].str.strip().str.len() > 0]
                combined = combined[combined['Location'].str.strip().str.len() > 0]
                st.session_state.df         = combined
                st.session_state.file_names = new_names
            else:
                st.error("No data extracted from PDFs.")

        # Status badge
        n = len(uploaded_files)
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

        # ── Store Roster Check ──────────────────────────────────────────────
        df_check = st.session_state.df
        store_counts = df_check.groupby('Store').agg(
            Files=('Store', 'count'),
        ).reset_index()

        # Detect duplicates: same store name appearing from >1 file
        # (rough proxy: if a store appears with >1 distinct delivery date it may be a dupe upload)
        store_file_map = {}
        for fname in st.session_state.file_names:
            # Re-check store name per file via the stored data
            pass
        # Simpler: flag stores whose row count seems doubled vs median
        median_lines = store_counts['Files'].median()
        store_counts['Flag'] = store_counts['Files'].apply(
            lambda x: '⚠️ Possible duplicate' if x > median_lines * 1.8 else '✅'
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
        if st.button("🗑  Clear & Reset"):
            st.session_state.df         = pd.DataFrame()
            st.session_state.file_names = set()
            st.rerun()


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
f1, f2, f3 = st.columns(3)

with f1:
    all_stores = sorted(df['Store'].dropna().unique())
    sel_stores = st.multiselect("Store / Branch", all_stores, placeholder="All stores")

with f2:
    all_locs = sorted(df['Location'].dropna().unique())
    sel_locs = st.multiselect("Location / Area", all_locs, placeholder="All areas")

with f3:
    search_item = st.text_input("Search Item", placeholder="e.g. CHICKEN, BEEF…")

filtered = df.copy()
if sel_stores:
    filtered = filtered[filtered['Store'].isin(sel_stores)]
if sel_locs:
    filtered = filtered[filtered['Location'].isin(sel_locs)]
if search_item:
    filtered = filtered[filtered['Item Description'].str.contains(search_item, case=False, na=False)]


# ─── KPIs ────────────────────────────────────────────────────────────────────────
total_stores = filtered['Store'].nunique()
unique_items = filtered['Item Description'].nunique()
total_lines  = len(filtered)
total_amount = filtered['Total Amount'].sum()

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
</div>
""", unsafe_allow_html=True)


# ─── DELIVERY DATE PILLS ─────────────────────────────────────────────────────────
del_dates = sorted(filtered['Delivery Date'].dropna().unique())
if del_dates:
    pills = "".join(f'<span class="info-pill">📅 Delivery: {d}</span>' for d in del_dates)
    st.markdown(pills, unsafe_allow_html=True)

st.markdown("---")


# ─── TABS ────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "  📋  PICK LIST  ",
    "  📦  ITEM ALLOCATION  ",
    "  🏪  STORE MATRIX  ",
    "  📊  ALL ORDERS  ",
    "  🚫  UNDELIVERED REPORT  ",
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

            # Header info
            loc_stores = df_loc['Store'].nunique()
            loc_items  = df_loc['Item Description'].nunique()
            loc_total  = df_loc['Order Qty'].sum()

            st.markdown(f"""
            <div style="display:flex; gap:16px; margin-bottom:16px;">
              <span class="info-pill">📍 {sel_loc}</span>
              <span class="info-pill">🏪 {loc_stores} stores</span>
              <span class="info-pill">📦 {loc_items} items</span>
              <span class="info-pill">🔢 {int(loc_total) if pd.notna(loc_total) else 0} total units</span>
              <span class="info-pill">📅 Delivery: {loc_del}</span>
            </div>
            """, unsafe_allow_html=True)

            # ── Detail table ──
            if show_store_breakdown:
                display = (
                    df_loc.groupby(['Store', 'Item Description', 'PLU Code', 'UOM'])
                    .agg(Qty=('Order Qty', 'sum'))
                    .reset_index()
                    .sort_values(['Item Description', 'Store'])
                )
                display.columns = ['Store', 'Item Description', 'PLU Code', 'UOM', 'Qty']
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
            html_picklist = make_picklist_html(df_loc, sel_loc, loc_del)
            st.download_button(
                label=f"🖨  Download {sel_loc} Pick List (Print-Ready HTML)",
                data=html_picklist.encode('utf-8'),
                file_name=f"PICKLIST_{sel_loc.replace(' ', '_')}_{loc_del}.html",
                mime="text/html",
                key="dl_picklist"
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

    # ── Single Item Drill-Down (Allocation Sheet) ──
    st.markdown(f'<div class="section-label">Item Allocation — Store Breakdown</div>',
                unsafe_allow_html=True)

    all_items = sorted(filtered['Item Description'].dropna().unique())
    sel_item  = st.selectbox("Select Item", all_items, key="alloc_item",
                              placeholder="Choose an item…")

    if sel_item:
        df_item = filtered[filtered['Item Description'] == sel_item].copy()
        store_alloc = (
            df_item.groupby('Store')['Order Qty']
            .sum().reset_index()
            .sort_values('Store')
        )
        total_qty = int(store_alloc['Order Qty'].sum()) if not store_alloc.empty else 0
        store_alloc.columns = ['Store', 'Qty']
        store_alloc['Qty'] = store_alloc['Qty'].apply(
            lambda x: int(x) if pd.notna(x) else 0)

        # Add TOTAL row
        total_row = pd.DataFrame([{'Store': '── TOTAL', 'Qty': total_qty}])
        display_alloc = pd.concat([store_alloc, total_row], ignore_index=True)

        ia2_c1, ia2_c2 = st.columns([2, 2])
        with ia2_c1:
            # UOM & location info
            uom_vals = df_item['UOM'].dropna().unique()
            uom_label = uom_vals[0] if len(uom_vals) > 0 else "—"
            locs = df_item['Location'].dropna().unique()
            loc_label = ", ".join(sorted(locs))
            del_dates_item = df_item['Delivery Date'].dropna().unique()
            del_item = del_dates_item[0] if len(del_dates_item) > 0 else "—"

            st.markdown(f"""
            <div style="margin-bottom:10px;">
              <span class="info-pill">📦 {sel_item}</span>
              <span class="info-pill">UOM: {uom_label}</span>
              <span class="info-pill">📍 {loc_label}</span>
              <span class="info-pill">🔢 Total: {total_qty}</span>
              <span class="info-pill">📅 Delivery: {del_item}</span>
            </div>
            """, unsafe_allow_html=True)

            st.dataframe(
                display_alloc,
                use_container_width=True, hide_index=True,
                height=min(500, 56 + len(display_alloc) * 36)
            )

            # Download allocation sheet
            st.markdown("<br>", unsafe_allow_html=True)
            html_alloc = make_allocation_html(df_item, sel_item, del_item)
            item_safe = re.sub(r'[^\w\s-]', '', sel_item).strip().replace(' ', '_')
            st.download_button(
                label=f"🖨  Download {sel_item} Allocation Sheet",
                data=html_alloc.encode('utf-8'),
                file_name=f"ALLOCATION_{item_safe}_{del_item}.html",
                mime="text/html",
                key="dl_alloc"
            )
            st.markdown(
                f'<div style="font-size:0.7rem; color:{MUTED}; margin-top:6px;">'
                '⬆ Download → open in browser → Ctrl+P to print</div>',
                unsafe_allow_html=True
            )

        with ia2_c2:
            # Store allocation bar chart
            if not store_alloc.empty:
                fig2 = go.Figure(go.Bar(
                    x=store_alloc['Qty'],
                    y=store_alloc['Store'],
                    orientation='h',
                    marker=dict(color=GOLD, line=dict(width=0)),
                    hovertemplate='<b>%{y}</b><br>Qty: %{x}<extra></extra>'
                ))
                fig2.update_layout(
                    **CHART_LAYOUT,
                    height=max(300, len(store_alloc) * 28),
                    xaxis=dict(title="Qty", **GRID_STYLE),
                    yaxis=dict(title="", tickfont=dict(size=9), autorange="reversed"),
                )
                st.plotly_chart(fig2, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════════
# TAB 3 — STORE × ITEM MATRIX
# ══════════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown(f"""
    <div style="font-size:0.72rem; color:{MUTED}; margin-bottom:14px;">
      Rows = Items &nbsp;·&nbsp; Columns = Stores &nbsp;·&nbsp; Values = Qty Ordered
    </div>
    """, unsafe_allow_html=True)

    mx_c1, mx_c2 = st.columns([2, 1])
    with mx_c1:
        matrix_loc = st.selectbox(
            "Filter by Location",
            ["All Locations"] + sorted(filtered['Location'].dropna().unique().tolist()),
            key="matrix_loc"
        )
    matrix_df = filtered if matrix_loc == "All Locations" else filtered[filtered['Location'] == matrix_loc]

    if not matrix_df.empty:
        pivot = (
            matrix_df.groupby(['Item Description', 'Store'])['Order Qty']
            .sum().reset_index()
            .pivot(index='Item Description', columns='Store', values='Order Qty')
            .fillna(0).astype(int)
        )
        pivot['TOTAL'] = pivot.sum(axis=1)
        pivot = pivot.sort_values('TOTAL', ascending=False)
        st.dataframe(pivot, use_container_width=True, height=500)

        # CSV export of matrix
        csv_matrix = pivot.to_csv().encode('utf-8')
        st.download_button(
            "⬇ Export Matrix (CSV)",
            data=csv_matrix,
            file_name=f"STORE_MATRIX_{matrix_loc.replace(' ', '_')}.csv",
            mime="text/csv"
        )

        # Heatmap
        if len(pivot.columns) <= 60:
            st.markdown(f'<div class="section-label" style="margin-top:20px;">Order Intensity Heatmap</div>',
                        unsafe_allow_html=True)
            stores_cols = [c for c in pivot.columns if c != 'TOTAL']
            fig = go.Figure(go.Heatmap(
                z=pivot[stores_cols].values,
                x=stores_cols,
                y=pivot.index.tolist(),
                colorscale=[[0, DARK], [0.3, "#3A2A10"], [1, GOLD]],
                hovertemplate='Item: %{y}<br>Store: %{x}<br>Qty: %{z}<extra></extra>',
                showscale=True
            ))
            fig.update_layout(
                **CHART_LAYOUT,
                height=max(400, len(pivot) * 22),
                xaxis=dict(tickangle=-45, tickfont=dict(size=9)),
                yaxis=dict(tickfont=dict(size=9), autorange="reversed"),
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data for this selection.")


# ══════════════════════════════════════════════════════════════════════════════════
# TAB 4 — ALL ORDERS (Full Detail)
# ══════════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown(f"""
    <div style="font-size:0.72rem; color:{MUTED}; margin-bottom:14px;">
      Complete extracted data from all uploaded PDFs
    </div>
    """, unsafe_allow_html=True)

    st.dataframe(
        filtered[[
            'Store', 'Order Date', 'Delivery Date',
            'Location', 'PLU Code', 'Item Description',
            'Order Qty', 'UOM', 'Total Amount', 'Days to Last'
        ]].sort_values(['Store', 'Location', 'Item Description']),
        use_container_width=True, hide_index=True, height=550
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
        # Auto-fill from data if available
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

    # ── Add Undelivered Item Form ────────────────────────────────────────────────
    st.markdown(f'<div class="section-label">Add Undelivered Item</div>', unsafe_allow_html=True)

    fa1, fa2 = st.columns([2, 3])

    with fa1:
        all_items_ud = sorted(filtered['Item Description'].dropna().unique()) if not filtered.empty else []
        sel_ud_item = st.selectbox(
            "Item Not Available",
            ["— select item —"] + all_items_ud,
            key="ud_item_sel"
        )

    with fa2:
        # Auto-load stores that ordered this item
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
            default=stores_ordered,   # pre-select ALL stores that ordered this item
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
            # Look up qty per store from order data
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

        # Editable preview table
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

        # Sync edits back to session state
        if edited_df is not None:
            st.session_state.undelivered_rows = edited_df.rename(columns={
                'Item': 'item', 'Store': 'store', 'Qty': 'qty', 'Remarks': 'remarks'
            }).to_dict('records')

        # Action buttons
        bc1, bc2, bc3 = st.columns([2, 2, 3])
        with bc1:
            if st.button("🗑  Clear All Rows", key="ud_clear"):
                st.session_state.undelivered_rows = []
                st.rerun()

        with bc2:
            # Generate + download report
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
                    label="🖨  Download Report (Print-Ready)",
                    data=html_ud.encode('utf-8'),
                    file_name=f"{title_safe}_{ud_del_date}.html",
                    mime="text/html",
                    key="ud_download"
                )

        with bc3:
            st.markdown(
                f'<div style="font-size:0.7rem; color:{MUTED}; margin-top:8px;">'
                'Download → open in browser → Ctrl+P to print &nbsp;·&nbsp; '
                'You can also edit cells directly in the table above</div>',
                unsafe_allow_html=True
            )
