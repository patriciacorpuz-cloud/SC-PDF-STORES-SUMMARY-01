"""SC_PDF STORES SUMMARY_01 — Streamlit app for store order PDF parsing and reporting.

UI only: sidebar, tabs, session state, filters.
All logic lives in dedicated modules.
"""

import streamlit as st
import pandas as pd
import re
import json
from pathlib import Path
import plotly.graph_objects as go

from config import (
    GOLD, DARK, CARD, BORDER, TEXT, MUTED, GREEN, RED, ACCENT, LOGO_B64,
    CHART_LAYOUT, GRID_STYLE,
)
from pdf_parser import parse_pdf, resolve_empty_locations, clean_numeric
from store_matching import (
    clean_store_name, normalize_store,
    auto_group_stores, check_bar_kitchen, is_rn1_store,
    check_rn1_submitted, compute_checklist_summary, all_expected_pdf_names,
)
from print_reports import make_picklist_html, make_allocation_html, make_undelivered_html
from pdf_generator import _generate_combined_pdf, _generate_multi_allocation_pdf
from drive_loader import _download_from_drive
from sheets_loader import _fetch_master_stores


# ─── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SC_PDF STORES SUMMARY_01",
    page_icon="\U0001F4E6",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ─── GLOBAL STYLES ─────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Jost:wght@300;400;500;600;700&family=Manrope:wght@300;400;500;600;700&display=swap');

  html, body, [class*="css"]:not(.material-symbols-rounded) {{
    font-family: 'Jost', sans-serif !important;
    background-color: {DARK};
    color: {TEXT};
  }}

  /* ── Sidebar ── */
  section[data-testid="stSidebar"] {{
    background-color: #F5F2ED !important;
    border-right: 1px solid {BORDER};
  }}
  section[data-testid="stSidebar"] *:not(.material-symbols-rounded):not([data-testid="stIconMaterial"]) {{ font-family: 'Jost', sans-serif !important; }}
  section[data-testid="stSidebar"] hr {{
    margin: 16px 0 !important;
    border-color: {BORDER} !important;
  }}
  /* ── Restore Material Symbols font on icon elements ── */
  .material-symbols-rounded,
  [data-testid="stIconMaterial"],
  [data-testid="stExpanderToggleIcon"] {{
    font-family: 'Material Symbols Rounded' !important;
  }}
  /* ── Expander styling ── */
  [data-testid="stExpander"] summary {{
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.04em !important;
    color: {TEXT} !important;
    padding: 10px 14px !important;
  }}
  [data-testid="stExpander"] summary p {{
    font-size: 0.78rem !important;
    font-weight: 600 !important;
  }}
  [data-testid="stExpander"] {{
    border: 1px solid {BORDER} !important;
    border-radius: 4px !important;
    background: {CARD} !important;
    margin-bottom: 6px !important;
  }}
  [data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
    padding: 0 14px 10px 14px !important;
  }}
  section[data-testid="stSidebar"] [data-testid="stAlert"] {{
    font-size: 0.72rem !important;
    padding: 8px 12px !important;
    border-radius: 3px !important;
  }}

  /* ── Top Nav Bar ── */
  .abaca-nav {{
    background: #1A1A1A;
    margin: -1rem -1rem 28px -1rem;
    padding: 14px 28px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .abaca-nav-brand {{
    font-family: 'Manrope', sans-serif;
    font-size: 0.72rem; font-weight: 700;
    letter-spacing: 0.25em; text-transform: uppercase;
    color: {ACCENT};
  }}
  .abaca-nav-title {{
    font-family: 'Jost', sans-serif;
    font-size: 0.8rem; font-weight: 400;
    color: #F0EDE8; letter-spacing: 0.08em;
  }}

  /* ── Legacy header (hidden, replaced by nav) ── */
  .abaca-header {{ display: none; }}

  /* ── KPI Cards ── */
  .kpi-row {{ display: flex; gap: 12px; margin-bottom: 24px; }}
  .kpi-card {{
    flex: 1; background: {CARD};
    border: 1px solid {BORDER}; border-top: 2px solid {TEXT};
    border-radius: 3px; padding: 14px 16px;
    transition: border-color 0.2s;
  }}
  .kpi-card:hover {{ border-color: {MUTED}; }}
  .kpi-label {{
    font-size: 0.58rem; font-weight: 700;
    letter-spacing: 0.18em; text-transform: uppercase;
    color: {MUTED}; margin-bottom: 4px;
  }}
  .kpi-value {{
    font-family: 'Manrope', sans-serif;
    font-size: 1.6rem; font-weight: 700; color: {TEXT};
    line-height: 1.2;
  }}
  .kpi-sub {{
    font-size: 0.65rem; color: {MUTED}; margin-top: 2px;
    letter-spacing: 0.02em;
  }}

  /* ── Section Labels ── */
  .section-label {{
    font-size: 0.6rem; font-weight: 700;
    letter-spacing: 0.22em; text-transform: uppercase;
    color: {TEXT}; margin-bottom: 12px;
    position: relative; padding-left: 12px;
  }}
  .section-label::before {{
    content: '';
    position: absolute; left: 0; top: 1px;
    width: 3px; height: 100%;
    background: {TEXT}; border-radius: 1px;
  }}

  /* ── Data Tables ── */
  .stDataFrame {{ border: 1px solid {BORDER} !important; border-radius: 3px; }}
  .stDataFrame th {{
    background: #F5F2ED !important; color: {MUTED} !important;
    font-size: 0.6rem !important; letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    font-family: 'Jost', sans-serif !important;
    border-bottom: 1px solid {BORDER} !important;
    padding: 8px 10px !important;
  }}
  .stDataFrame td {{
    font-size: 0.78rem !important;
    font-family: 'Jost', sans-serif !important;
    border-bottom: 1px solid {BORDER} !important;
    padding: 6px 10px !important;
  }}

  /* ── Tabs ── */
  .stTabs [data-baseweb="tab-list"] {{
    border-bottom: 1px solid {BORDER} !important;
    gap: 0 !important; background: transparent !important;
  }}
  .stTabs [data-baseweb="tab"] {{
    font-family: 'Jost', sans-serif !important;
    font-size: 0.65rem !important; font-weight: 600 !important;
    letter-spacing: 0.14em !important; text-transform: uppercase !important;
    color: {MUTED} !important; padding: 10px 20px !important;
    border: none !important; border-bottom: 2px solid transparent !important;
    background: transparent !important;
    transition: color 0.15s, border-color 0.15s;
  }}
  .stTabs [data-baseweb="tab"]:hover {{
    color: {TEXT} !important;
  }}
  .stTabs [aria-selected="true"] {{
    color: {TEXT} !important; border-bottom: 2px solid {TEXT} !important;
  }}

  /* ── Form Inputs ── */
  div[data-testid="stFileUploader"] {{
    border: 1px solid {BORDER} !important;
    border-radius: 3px !important; padding: 8px !important;
    background: {CARD} !important;
  }}
  .stRadio label {{ font-size: 0.78rem !important; }}
  .stMultiSelect [data-baseweb="tag"] {{
    background: rgba(26,26,26,0.06) !important;
    border: 1px solid rgba(26,26,26,0.15) !important; border-radius: 2px !important;
  }}

  /* ── Buttons ── */
  .stButton button, .stDownloadButton button {{
    font-family: 'Jost', sans-serif !important;
    letter-spacing: 0.12em !important; text-transform: uppercase !important;
    font-size: 0.68rem !important; font-weight: 600 !important;
    background: transparent !important;
    border: 1px solid {TEXT} !important;
    color: {TEXT} !important; border-radius: 2px !important;
    transition: all 0.15s;
  }}
  .stButton button:hover, .stDownloadButton button:hover {{
    background: rgba(26,26,26,0.06) !important;
  }}

  /* ── Badges ── */
  .out-badge {{
    display: inline-block;
    background: rgba(229,57,53,0.08);
    border: 1px solid rgba(229,57,53,0.3);
    border-radius: 2px;
    padding: 1px 6px;
    font-size: 0.6rem;
    font-weight: 700;
    color: {RED};
    letter-spacing: 0.1em;
  }}

  /* ── Info Pills ── */
  .info-pill {{
    display: inline-block;
    background: rgba(26,26,26,0.04);
    border: 1px solid rgba(26,26,26,0.12);
    border-radius: 2px;
    padding: 3px 10px;
    font-size: 0.68rem;
    color: {TEXT};
    letter-spacing: 0.06em;
    margin-right: 6px;
    margin-bottom: 4px;
  }}

  /* ── Misc ── */
  hr {{ border-color: {BORDER} !important; margin: 20px 0 !important; }}
  ::-webkit-scrollbar {{ width: 5px; height: 5px; }}
  ::-webkit-scrollbar-track {{ background: transparent; }}
  ::-webkit-scrollbar-thumb {{ background: {BORDER}; border-radius: 3px; }}
  ::-webkit-scrollbar-thumb:hover {{ background: {MUTED}; }}

  /* ── Reconciliation Panel ── */
  .recon-row {{
    display: flex; justify-content: space-between; align-items: center;
    font-size: 0.7rem; padding: 4px 0;
    border-bottom: 1px solid {BORDER};
  }}
  .recon-ok {{ color: {TEXT}; }}
  .recon-warn {{ color: {RED}; }}
  .recon-meta {{ color: {MUTED}; font-size: 0.65rem; }}

  /* ── Warning list ── */
  .warn-item {{
    font-size: 0.7rem; padding: 3px 0;
    border-bottom: 1px solid {BORDER};
    color: {TEXT};
  }}
</style>
""", unsafe_allow_html=True)


# ─── SESSION STATE ───────────────────────────────────────────────────────────────
if 'df' not in st.session_state:
    st.session_state.df              = pd.DataFrame()
    st.session_state.file_names      = set()
if 'undelivered_rows' not in st.session_state:
    st.session_state.undelivered_rows = []
if 'parse_warnings' not in st.session_state:
    st.session_state.parse_warnings  = []
if 'unavailable_items' not in st.session_state:
    st.session_state.unavailable_items = []
if 'manual_orders' not in st.session_state:
    st.session_state.manual_orders = []
if 'pdf_reconciliation' not in st.session_state:
    st.session_state.pdf_reconciliation = []


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
      <div style="width:28px; height:2px; background:{ACCENT}; margin-top:8px;"></div>
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
    load_drive = st.button("\U0001F4E5  Load from Drive", use_container_width=True, key="load_drive_btn")

    pdf_file_list = []

    if drive_link and load_drive:
        pdf_file_list = _download_from_drive(drive_link)

    if pdf_file_list:
        new_names = {n for n, _ in pdf_file_list}

        if new_names != st.session_state.file_names:
            progress = st.progress(0, text="Reading PDFs\u2026")
            dfs = []
            all_warnings = []
            reconciliation = []
            for i, (name, data) in enumerate(pdf_file_list):
                df_i, file_warnings, header_total = parse_pdf(data, name)
                all_warnings.extend(file_warnings)

                # Build reconciliation data
                if not df_i.empty:
                    amounts = pd.to_numeric(
                        df_i['Total Amount'].astype(str).str.replace(',', '').str.strip(),
                        errors='coerce'
                    )
                    parsed_total = amounts.sum()
                else:
                    parsed_total = 0.0

                reconciliation.append({
                    'pdf': clean_store_name(Path(name).stem),
                    'rows': len(df_i),
                    'header_total': header_total,
                    'parsed_total': parsed_total,
                    'variance': (
                        abs(parsed_total - header_total) / header_total * 100
                        if header_total and header_total > 0
                        else 0.0
                    ),
                    'status': (
                        'match'
                        if header_total is None or (header_total > 0 and abs(parsed_total - header_total) / header_total * 100 < 0.5)
                        else 'mismatch'
                    ),
                })

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
                combined = resolve_empty_locations(combined, all_warnings)

                st.session_state.df              = combined
                st.session_state.file_names      = new_names
                st.session_state.parse_warnings  = all_warnings
                st.session_state.pdf_reconciliation = reconciliation
            else:
                st.error("No data extracted from PDFs.")

        # Status badge
        n = len(pdf_file_list)
        df_loaded = st.session_state.df
        del_dates = df_loaded['Delivery Date'].dropna().unique().tolist() if not df_loaded.empty else []
        del_label = del_dates[0] if len(del_dates) == 1 else (f"{len(del_dates)} dates" if del_dates else "\u2014")

        st.markdown(f"""
        <div style="margin-top:12px; padding:12px 14px; background:{CARD};
                    border:1px solid {BORDER}; border-left:3px solid {GOLD}; border-radius:3px;">
          <div style="font-size:0.6rem; letter-spacing:0.15em; color:{MUTED};
                      text-transform:uppercase; font-weight:600; margin-bottom:6px;">Loaded</div>
          <div style="font-size:1.2rem; font-weight:700; color:{TEXT};">{n} PDF{'s' if n != 1 else ''}</div>
          <div style="font-size:0.72rem; color:{MUTED}; margin-top:6px;">
            {df_loaded['Store'].nunique() if not df_loaded.empty else 0} stores
            &nbsp;\u00b7&nbsp; Delivery: {del_label}
          </div>
        </div>
        """, unsafe_allow_html=True)

    if not st.session_state.df.empty:
        st.markdown("---")

        # ── Per-PDF Reconciliation Panel ─────────────────────────────────────
        recon = st.session_state.pdf_reconciliation
        if recon:
            mismatches = sum(1 for r in recon if r['status'] == 'mismatch')
            if mismatches:
                label = f"PDF Reconciliation \u2014 {mismatches} issue{'s' if mismatches != 1 else ''}"
            else:
                label = f"PDF Reconciliation \u2014 {len(recon)} PDFs verified"
            with st.expander(label, expanded=mismatches > 0):
                st.markdown(
                    f'<div style="font-size:0.65rem; color:{MUTED}; margin-bottom:8px;">'
                    f'Compares parsed totals against PDF header amounts to catch missing rows</div>',
                    unsafe_allow_html=True
                )
                # Show mismatches first, then matches
                sorted_recon = sorted(recon, key=lambda r: (r['status'] == 'match', r['pdf']))
                for r in sorted_recon:
                    is_ok = r['status'] == 'match'
                    css_class = 'recon-ok' if is_ok else 'recon-warn'
                    dot = '\u25cf' if is_ok else '\u25b2'
                    dot_color = '#4CAF50' if is_ok else RED
                    ht = f"\u20b1{r['header_total']:,.2f}" if r['header_total'] else "\u2014"
                    pt = f"\u20b1{r['parsed_total']:,.2f}"
                    var_text = f"{r['variance']:.1f}%" if r['header_total'] else "\u2014"
                    st.markdown(
                        f'<div class="recon-row {css_class}">'
                        f'<span><span style="color:{dot_color};font-size:0.55rem;">{dot}</span> '
                        f'{r["pdf"]}</span>'
                        f'<span class="recon-meta">{r["rows"]}r '
                        f'\u00b7 {pt} \u00b7 {var_text}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

        # ── Parsing Notes Panel ────────────────────────────────────────────
        warn_list = st.session_state.parse_warnings
        filtered_warnings = [
            w for w in warn_list
            if 'DO NOT TOUCH' not in w.upper()
            and 'row skipped' not in w.lower()
        ]
        if filtered_warnings:
            blank_amt = [w for w in filtered_warnings if 'Blank amount' in w]
            unknown_loc = [w for w in filtered_warnings if 'Unknown location' in w]
            other = [w for w in filtered_warnings
                     if 'Blank amount' not in w and 'Unknown location' not in w]

            with st.expander(
                f"Parsing Notes ({len(filtered_warnings)})",
                expanded=False
            ):
                st.markdown(
                    f'<div style="font-size:0.65rem; color:{MUTED}; margin-bottom:8px;">'
                    f'Items with missing data from the PDFs \u2014 '
                    f'most are zero-cost supplies or first-row items without a location</div>',
                    unsafe_allow_html=True
                )
                if other:
                    for w in other:
                        st.markdown(
                            f'<div class="warn-item" style="color:{RED};">{w}</div>',
                            unsafe_allow_html=True
                        )

                if blank_amt:
                    # Extract unique item names from warnings
                    blank_items = set()
                    for w in blank_amt:
                        # "Blank amount: STORE -> ITEM (UOM: X)"
                        parts = w.replace('Blank amount: ', '').split(' -> ')
                        if len(parts) == 2:
                            item_part = parts[1].split(' (UOM:')[0]
                            blank_items.add(item_part)
                    st.markdown(
                        f'<div style="font-size:0.65rem; color:{MUTED}; '
                        f'margin:6px 0 4px 0;">'
                        f'<strong style="color:{TEXT};">Blank Amounts</strong> '
                        f'\u00b7 {len(blank_amt)} rows across {len(blank_items)} items'
                        f'<br>Zero-cost supplies (bags, paper, boxes) \u2014 '
                        f'included in data with amount = 0</div>',
                        unsafe_allow_html=True
                    )

                if unknown_loc:
                    unknown_items = set()
                    for w in unknown_loc:
                        parts = w.replace('Unknown location: ', '').replace(' \u2014 set to UNKNOWN', '').split(' -> ')
                        if len(parts) == 2:
                            unknown_items.add(parts[1])
                    st.markdown(
                        f'<div style="font-size:0.65rem; color:{MUTED}; '
                        f'margin:6px 0 4px 0;">'
                        f'<strong style="color:{TEXT};">Unknown Locations</strong> '
                        f'\u00b7 {len(unknown_loc)} rows across {len(unknown_items)} items'
                        f'<br>Items that appear first on page before any location header \u2014 '
                        f'listed under "UNKNOWN" in Pick List</div>',
                        unsafe_allow_html=True
                    )
                    for item in sorted(unknown_items):
                        st.markdown(
                            f'<div style="font-size:0.68rem; color:{TEXT}; '
                            f'padding:2px 0 2px 8px; '
                            f'border-left:2px solid {BORDER};">'
                            f'{item}</div>',
                            unsafe_allow_html=True
                        )

        # ── Store Roster Check ───────────────────────────────────────────────
        df_check = st.session_state.df
        store_counts = df_check.groupby('Store').agg(
            Files=('Store', 'count'),
        ).reset_index()

        store_del_combos = df_check.groupby(['Store', 'Delivery Date']).size().reset_index(name='count')
        dup_stores = set()
        for _, combo in store_del_combos.iterrows():
            store_name_val = combo['Store']
            matching_files = [
                fn for fn in st.session_state.file_names
                if clean_store_name(Path(fn).stem) == store_name_val
            ]
            if len(matching_files) > 1:
                dup_stores.add(store_name_val)

        store_counts['Flag'] = store_counts['Store'].apply(
            lambda x: '\u26a0\ufe0f Possible duplicate' if x in dup_stores else '\u2705'
        )

        with st.expander(f"Store Roster ({len(store_counts)} stores)", expanded=False):
            st.markdown(
                f'<div style="font-size:0.65rem; color:{MUTED}; margin-bottom:8px;">'
                f'All stores parsed from uploaded PDFs \u2014 '
                f'check for missing or duplicate uploads</div>',
                unsafe_allow_html=True
            )
            for _, row in store_counts.sort_values('Store').iterrows():
                flag_color = "#E8A020" if "\u26a0\ufe0f" in row['Flag'] else "#4CAF50"
                st.markdown(
                    f'<div style="font-size:0.75rem; padding:3px 0; '
                    f'border-bottom:1px solid {BORDER}; display:flex; '
                    f'justify-content:space-between;">'
                    f'<span style="color:{TEXT};">{row["Store"]}</span>'
                    f'<span style="color:{flag_color}; font-size:0.68rem;">{row["Flag"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            st.markdown(
                f'<div style="font-size:0.65rem; color:{MUTED}; margin-top:10px; '
                f'letter-spacing:0.08em; text-transform:uppercase; font-weight:600;">'
                f'{len(st.session_state.file_names)} files uploaded</div>',
                unsafe_allow_html=True
            )
            for fname in sorted(st.session_state.file_names):
                st.markdown(
                    f'<div style="font-size:0.68rem; color:{MUTED}; padding:2px 0;">'
                    f'\u00b7 {fname}</div>',
                    unsafe_allow_html=True
                )

        st.markdown("---")

        # ── Save Session ─────────────────────────────────────────────────────
        session_data = {
            'df': st.session_state.df.to_dict('records'),
            'file_names': list(st.session_state.file_names),
            'undelivered_rows': st.session_state.undelivered_rows,
            'parse_warnings': st.session_state.parse_warnings,
            'unavailable_items': st.session_state.unavailable_items,
            'manual_orders': st.session_state.manual_orders,
            'pdf_reconciliation': st.session_state.pdf_reconciliation,
        }
        session_json = json.dumps(session_data, default=str)
        st.download_button(
            "\U0001F4BE  Save Session",
            data=session_json,
            file_name="orders_session.json",
            mime="application/json",
            use_container_width=True,
            help="Download a snapshot you can reload later \u2014 even after restart"
        )

        st.markdown("---")
        if st.button("\U0001F5D1  Clear & Reset"):
            st.session_state.df               = pd.DataFrame()
            st.session_state.file_names       = set()
            st.session_state.undelivered_rows = []
            st.session_state.parse_warnings   = []
            st.session_state.unavailable_items = []
            st.session_state.manual_orders    = []
            st.session_state.pdf_reconciliation = []
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
            if not isinstance(data, dict):
                st.error("**Invalid session file** — expected a JSON object.")
            elif 'df' not in data:
                st.error("**Invalid session file** — missing order data. Is this a session file from this app?")
            else:
                EXPECTED_COLS = {
                    'Store', 'Order Date', 'Delivery Date', 'Location',
                    'PLU Code', 'Item Description', 'Order Qty', 'UOM',
                    'Total Amount', 'Days to Last', 'Ordered By',
                }
                df_restored = pd.DataFrame(data['df'])
                if not df_restored.empty:
                    missing = EXPECTED_COLS - set(df_restored.columns)
                    if missing:
                        st.error(f"**Invalid session file** — missing columns: {', '.join(sorted(missing))}")
                    else:
                        for col_name in ['Order Qty', 'Total Amount', 'Days to Last']:
                            if col_name in df_restored.columns:
                                df_restored[col_name] = clean_numeric(df_restored[col_name])
                        st.session_state.df               = df_restored
                        st.session_state.file_names       = set(data.get('file_names', []))
                        st.session_state.undelivered_rows  = data.get('undelivered_rows', [])
                        st.session_state.parse_warnings    = data.get('parse_warnings', [])
                        st.session_state.unavailable_items = data.get('unavailable_items', [])
                        st.session_state.manual_orders     = data.get('manual_orders', [])
                        st.session_state.pdf_reconciliation = data.get('pdf_reconciliation', [])
                        st.session_state.session_loaded_key = loaded_session.name
                        st.success("\u2705 Session restored!")
                        st.rerun()
                else:
                    st.warning("Session file loaded but contains no order data.")
        except json.JSONDecodeError:
            st.error("**Invalid file** — not valid JSON.")
        except Exception as e:
            st.error(f"Could not load session: {e}")


# ─── HEADER ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="abaca-nav">
  <div class="abaca-nav-brand">ABACA &nbsp;\u00b7&nbsp; Supply Chain</div>
  <div class="abaca-nav-title">SC_PDF STORES SUMMARY_01</div>
</div>
""", unsafe_allow_html=True)

df = st.session_state.df

if df.empty:
    st.markdown(f"""
    <div style="padding:56px 0; text-align:center; color:{MUTED};">
      <div style="font-size:2.5rem; margin-bottom:16px;">\U0001F4C2</div>
      <div style="font-size:0.8rem; letter-spacing:0.15em; text-transform:uppercase;
                  font-weight:600; color:{TEXT};">
        Upload PDF store orders from the sidebar to begin
      </div>
      <div style="margin-top:16px; font-size:0.8rem; line-height:2.2; color:#555;">
        Drag all store PDFs into the uploader &nbsp;\u00b7&nbsp; Supports 100+ files at once<br>
        Pick List by Location &nbsp;\u00b7&nbsp; Item Allocation sheets &nbsp;\u00b7&nbsp; Store \u00d7 Item Matrix
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
    search_item = st.text_input("Search Item", placeholder="e.g. CHICKEN, BEEF\u2026")

with f4:
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
nan_amount_count = int(filtered['Total Amount'].isna().sum()) if 'Total Amount' in filtered.columns else 0
total_amount = filtered['Total Amount'].sum()
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
    <div class="kpi-value">\u20b1{total_amount:,.0f}</div>
    <div class="kpi-sub">filtered total</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-label">Out of Stock</div>
    <div class="kpi-value" style="color:{RED if oos_count > 0 else TEXT};">{oos_count}</div>
    <div class="kpi-sub">Days to Last = 0</div>
  </div>
</div>
""", unsafe_allow_html=True)

if nan_amount_count > 0:
    st.caption(f"\u26a0\ufe0f {nan_amount_count} item(s) have missing amounts and are excluded from the total.")


# ─── DELIVERY DATE PILLS ─────────────────────────────────────────────────────────
del_dates = sorted(d for d in filtered['Delivery Date'].dropna().unique() if str(d).strip())
if del_dates:
    pills = "".join(f'<span class="info-pill">Delivery: {d}</span>' for d in del_dates)
    st.markdown(pills, unsafe_allow_html=True)

st.markdown("---")


# ─── TABS ────────────────────────────────────────────────────────────────────────
tab1, tab2, tab5, tab6, tab7 = st.tabs([
    "  \U0001F4CB  PICK LIST  ",
    "  \U0001F4E6  ITEM ALLOCATION  ",
    "  \U0001F6AB  UNDELIVERED REPORT  ",
    "  \U0001F4DD  MANUAL ORDERS  ",
    "  \u2705  STORE CHECKLIST  ",
])


# ══════════════════════════════════════════════════════════════════════════════════
# TAB 1 — PICK LIST (by Location, for Pickers)
# ══════════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown(f"""
    <div style="margin-bottom:12px;">
      <div style="font-size:0.65rem; letter-spacing:0.15em; color:{MUTED};
                  text-transform:uppercase; font-weight:600;">
        Select a location \u2192 get a ready-to-print pick list for your pickers
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
            loc_del_dates = df_loc['Delivery Date'].dropna().unique()
            loc_del = loc_del_dates[0] if len(loc_del_dates) > 0 else "\u2014"
            loc_ordered_by = df_loc['Ordered By'].dropna().unique() if 'Ordered By' in df_loc.columns else []
            loc_ordered_by_str = ", ".join(sorted(set(loc_ordered_by))) if len(loc_ordered_by) > 0 else ""
            loc_stores = df_loc['Store'].nunique()
            loc_items  = df_loc['Item Description'].nunique()
            loc_total  = df_loc['Order Qty'].sum()

            st.markdown(f"""
            <div style="display:flex; gap:16px; margin-bottom:16px; flex-wrap:wrap;">
              <span class="info-pill">\U0001F4CD {sel_loc}</span>
              <span class="info-pill">\U0001F3EA {loc_stores} stores</span>
              <span class="info-pill">\U0001F4E6 {loc_items} items</span>
              <span class="info-pill">\U0001F522 {int(loc_total) if pd.notna(loc_total) else 0} total units</span>
              <span class="info-pill">\U0001F4C5 Delivery: {loc_del}</span>
              {f'<span class="info-pill">\U0001F464 {loc_ordered_by_str}</span>' if loc_ordered_by_str else ''}
            </div>
            """, unsafe_allow_html=True)

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

            st.markdown(f'<div class="section-label">Summary Qty \u2014 {sel_loc}</div>', unsafe_allow_html=True)
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

            st.markdown("<br>", unsafe_allow_html=True)
            html_picklist = make_picklist_html(df_loc, sel_loc, loc_del, loc_ordered_by_str)
            st.download_button(
                label=f"\U0001F5A8  Download {sel_loc} Pick List (Print-Ready HTML)",
                data=html_picklist.encode('utf-8'),
                file_name=f"PICKLIST_{sel_loc.replace(' ', '_')}_{loc_del}.html",
                mime="text/html",
                key=f"dl_picklist_{sel_loc}"
            )
            st.markdown(
                f'<div style="font-size:0.7rem; color:{MUTED}; margin-top:6px;">'
                '\u2b06 Download \u2192 open in browser \u2192 Ctrl+P to print</div>',
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
        Select an item \u2192 see total qty + store breakdown \u2014 for production make-to-order
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Multi-Item Allocation ────────────────────────────────────────────────
    st.markdown(f'<div class="section-label">Multi-Item Allocation \u2014 Combined Report</div>',
                unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:0.7rem; color:{MUTED}; margin-bottom:10px;">'
        f'Select multiple items \u2192 review store breakdowns \u2192 download one combined PDF</div>',
        unsafe_allow_html=True,
    )

    all_items = sorted(filtered['Item Description'].dropna().unique())

    ma_c1, ma_c2 = st.columns([5, 1])
    with ma_c1:
        sel_multi_items = st.multiselect(
            "Select items for combined report",
            all_items,
            key="multi_alloc_items",
            placeholder="Click to select items\u2026",
        )
    with ma_c2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Clear", key="multi_alloc_clear", use_container_width=True):
            st.session_state.multi_alloc_items = []
            st.rerun()

    if sel_multi_items:
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

        total_items = len(sel_multi_items)
        grand_total = sum(d["total_qty"] for d in multi_items_data)
        st.markdown(f"""
        <div style="display:flex; gap:12px; margin:8px 0 12px 0; flex-wrap:wrap;">
          <span class="info-pill">\U0001F4E6 {total_items} item(s) selected</span>
          <span class="info-pill">\U0001F522 {grand_total:,} total units</span>
        </div>
        """, unsafe_allow_html=True)

        for d in multi_items_data:
            with st.expander(
                f"**{d['item']}** \u2014 {len(d['stores'])} stores, {d['total_qty']} {d['uom']}",
                expanded=False,
            ):
                disp = pd.DataFrame(d["stores"]).rename(columns={"store": "Store", "qty": "Qty"})
                total_row = pd.DataFrame([{"Store": "\u2500\u2500 TOTAL", "Qty": d["total_qty"]}])
                disp = pd.concat([disp, total_row], ignore_index=True)
                st.dataframe(
                    disp, use_container_width=True, hide_index=True,
                    height=min(300, 40 + len(disp) * 36),
                )

        del_dates_multi = filtered['Delivery Date'].dropna().unique()
        del_multi = del_dates_multi[0] if len(del_dates_multi) > 0 else ""

        combined_alloc_pdf = _generate_multi_allocation_pdf(multi_items_data, del_multi)
        st.download_button(
            label=f"\U0001F4C4  Download Combined Allocation Report ({total_items} items)",
            data=combined_alloc_pdf,
            file_name=f"COMBINED_ALLOCATION_{del_multi}.pdf",
            mime="application/pdf",
            key="dl_multi_alloc",
        )


# ══════════════════════════════════════════════════════════════════════════════════
# TAB 5 — UNDELIVERED REPORT
# ══════════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown(f"""
    <div style="margin-bottom:16px;">
      <div style="font-size:0.65rem; letter-spacing:0.15em; color:{MUTED};
                  text-transform:uppercase; font-weight:600;">
        Flag undelivered items \u00b7 system auto-fills which stores ordered it \u00b7 add remarks \u00b7 generate report
      </div>
    </div>
    """, unsafe_allow_html=True)

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

    # ── Section 1: Undelivered Item Form (row-by-row) ────────────────────────
    st.markdown(f'<div class="section-label">Add Undelivered Item (row-by-row)</div>', unsafe_allow_html=True)

    fa1, fa2 = st.columns([2, 3])

    with fa1:
        all_items_ud = sorted(filtered['Item Description'].dropna().unique()) if not filtered.empty else []
        sel_ud_item = st.selectbox(
            "Item Not Available",
            ["\u2014 select item \u2014"] + all_items_ud,
            key="ud_item_sel"
        )

    with fa2:
        if sel_ud_item and sel_ud_item != "\u2014 select item \u2014":
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
            help="Pre-selected stores that ordered this item \u2014 deselect any that DID receive it"
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
        add_clicked = st.button("\u2795  Add", key="ud_add_btn", use_container_width=True)

    if add_clicked:
        if sel_ud_item == "\u2014 select item \u2014":
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

    # ── Current Undelivered List ─────────────────────────────────────────────
    if not st.session_state.undelivered_rows:
        st.markdown(f"""
        <div style="padding:24px; text-align:center; color:{MUTED};
                    border:1px dashed {BORDER}; border-radius:4px;">
          <div style="font-size:0.75rem; letter-spacing:0.1em; text-transform:uppercase;">
            No undelivered items added yet
          </div>
          <div style="font-size:0.72rem; margin-top:6px;">
            Select an item above and click \u2795 Add to Report
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="section-label">Undelivered Items \u2014 {len(st.session_state.undelivered_rows)} rows</div>',
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
            if st.button("\U0001F5D1  Clear All Rows", key="ud_clear"):
                st.session_state.undelivered_rows = []
                st.rerun()

        with bc2:
            if st.session_state.undelivered_rows:
                html_ud = make_undelivered_html(
                    rows          = st.session_state.undelivered_rows,
                    report_title  = report_title_input or "UNDELIVERED REPORT",
                    order_date    = ud_order_date,
                    delivery_date = ud_del_date,
                    prepared_by   = ud_prepared_by or "\u2014",
                )
                title_safe = re.sub(r'[^\w\s-]', '', report_title_input or "UNDELIVERED").replace(' ', '_')
                st.download_button(
                    label="\U0001F5A8  Download Report (HTML)",
                    data=html_ud.encode('utf-8'),
                    file_name=f"{title_safe}_{ud_del_date}.html",
                    mime="text/html",
                    key="ud_download"
                )

        with bc3:
            st.markdown(
                f'<div style="font-size:0.7rem; color:{MUTED}; margin-top:8px;">'
                'Download \u2192 open in browser \u2192 Ctrl+P to print</div>',
                unsafe_allow_html=True
            )

    st.markdown("---")

    # ── Section 2: ITEMS NOT AVAILABLE TODAY ─────────────────────────────────
    st.markdown(f'<div class="section-label">Items Not Available Today</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="font-size:0.7rem; color:{MUTED}; margin-bottom:12px;">'
        f'Select items one by one \u2014 they are instantly added to the list below. '
        f'Add remarks inline after adding. Generate the Allocation Guide PDF when ready.</div>',
        unsafe_allow_html=True,
    )

    existing_na_items = {e["item"] for e in st.session_state.unavailable_items}
    all_items_na = sorted(filtered['Item Description'].dropna().unique()) if not filtered.empty else []
    available_na_options = [it for it in all_items_na if it not in existing_na_items]

    sel_na_item = st.selectbox(
        "Select unavailable item (instant add)",
        [""] + available_na_options,
        format_func=lambda x: "\u2014 click to select an item \u2014" if x == "" else x,
        key="na_item_sel",
    )

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
                f"**{item_name}** \u2014 {len(stores)} stores, {total_qty} units"
                + (f"  \u00b7  _{remarks}_" if remarks else ""),
                expanded=False,
            ):
                if stores:
                    st.dataframe(
                        pd.DataFrame(stores).rename(columns={"store": "Store", "qty": "Qty", "uom": "UOM"}),
                        use_container_width=True,
                        hide_index=True,
                        height=min(250, 40 + len(stores) * 36),
                    )
                new_remark = st.text_input(
                    "Remarks",
                    value=remarks,
                    placeholder="e.g. AVAILABLE TOMORROW, OUT OF STOCK",
                    key=f"na_remark_{idx}",
                )
                if new_remark != remarks:
                    st.session_state.unavailable_items[idx]["remarks"] = new_remark.strip().upper()

                if st.button("\U0001F5D1 Remove", key=f"na_remove_{idx}"):
                    st.session_state.unavailable_items.pop(idx)
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        na_bc1, na_bc2 = st.columns([2, 3])
        with na_bc1:
            if st.button("\U0001F5D1  Clear All Unavailable Items", key="na_clear_all"):
                st.session_state.unavailable_items = []
                st.rerun()
        with na_bc2:
            pdf_bytes = _generate_combined_pdf(
                unavailable_items=st.session_state.unavailable_items,
                manual_orders=[],
                report_title=report_title_input or "ALLOCATION GUIDE",
                order_date=ud_order_date,
                delivery_date=ud_del_date,
                prepared_by=ud_prepared_by or "\u2014",
            )
            title_safe = re.sub(r'[^\w\s-]', '', report_title_input or "ALLOCATION_GUIDE").replace(' ', '_')
            st.download_button(
                label="\U0001F4C4  Download Allocation Guide (PDF)",
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
            No unavailable items added yet \u2014 select items above
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
        Add orders that came in verbally or by hand \u2014 not in any uploaded PDF
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f'<div class="section-label">Add Manual Order</div>', unsafe_allow_html=True)

    mo_c1, mo_c2, mo_c3, mo_c4 = st.columns([2, 3, 1, 1])
    with mo_c1:
        all_stores_mo = sorted(df['Store'].dropna().unique()) if not df.empty else []
        mo_store = st.selectbox(
            "Store",
            ["\u2014 select store \u2014"] + all_stores_mo,
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
        mo_add = st.button("\u2795  Add Order", key="mo_add_btn", use_container_width=True)

    if mo_add:
        if mo_store == "\u2014 select store \u2014":
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
            st.success(f"Added **{mo_item.strip().upper()}** \u00d7 {int(mo_qty)} for **{mo_store}**.")
            st.rerun()

    st.markdown("---")

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
            f'<div class="section-label">Manual Orders \u2014 {len(st.session_state.manual_orders)} entries</div>',
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
            if st.button("\U0001F5D1  Clear All Manual Orders", key="mo_clear"):
                st.session_state.manual_orders = []
                st.rerun()

    st.markdown("---")

    # ── Generate Combined Report PDF ─────────────────────────────────────────
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
            f'No data to generate report \u2014 add undelivered items in the Undelivered Report tab '
            f'and/or add manual orders above.</div>',
            unsafe_allow_html=True,
        )
    else:
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

        r_title = st.session_state.get("ud_title", "COMBINED REPORT")
        r_order = st.session_state.get("ud_order_date", "")
        r_del = st.session_state.get("ud_del_date", "")
        r_prep = st.session_state.get("ud_prep_by", "\u2014")

        combined_pdf = _generate_combined_pdf(
            unavailable_items=[],
            manual_orders=st.session_state.manual_orders,
            report_title=r_title or "COMBINED REPORT",
            order_date=r_order,
            delivery_date=r_del,
            prepared_by=r_prep or "\u2014",
            undelivered_rows=st.session_state.undelivered_rows,
        )
        title_safe = re.sub(r'[^\w\s-]', '', r_title or "COMBINED_REPORT").replace(' ', '_')
        st.download_button(
            label="\U0001F4C4  Download Combined Report (PDF)",
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
# TAB 7 — STORE CHECKLIST
# ══════════════════════════════════════════════════════════════════════════════════
with tab7:
    st.markdown(f"""
    <div style="margin-bottom:12px;">
      <div style="font-size:0.65rem; letter-spacing:0.15em; color:{MUTED};
                  text-transform:uppercase; font-weight:600;">
        Master store list from Google Sheet \u2192 compare against parsed PDFs \u2192 see who's missing
      </div>
    </div>
    """, unsafe_allow_html=True)

    if 'checklist_groups' not in st.session_state:
        st.session_state.checklist_groups = {}
    if 'checklist_loaded' not in st.session_state:
        st.session_state.checklist_loaded = False

    if not st.session_state.checklist_loaded:
        with st.spinner("Loading master store list from Google Sheet\u2026"):
            groups = _fetch_master_stores()
        if groups:
            st.session_state.checklist_groups = groups
            st.session_state.checklist_loaded = True
            total = sum(len(v) for v in groups.values())
            st.success(f"\u2713 Loaded **{total}** stores from Google Sheet")

    if st.button("\U0001F504  Refresh from Sheet", key="refresh_master_sheet"):
        with st.spinner("Refreshing master store list\u2026"):
            groups = _fetch_master_stores()
        if groups:
            st.session_state.checklist_groups = groups
            st.session_state.checklist_loaded = True
            total = sum(len(v) for v in groups.values())
            st.success(f"\u2713 Loaded **{total}** stores from Google Sheet")

    st.markdown("---")

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
        complete_count, total_expected = compute_checklist_summary(groups, loaded_stores)

        st.markdown(
            f'<div style="font-size:0.85rem; font-weight:600; color:{TEXT}; '
            f'margin-bottom:16px;">DATE: {today_str}</div>',
            unsafe_allow_html=True,
        )

        summary_color = GREEN if complete_count == total_expected else GOLD
        st.markdown(f"""
        <div style="display:flex; gap:16px; margin-bottom:16px; flex-wrap:wrap;">
          <span class="info-pill" style="color:{summary_color};">
            \u2705 {complete_count} of {total_expected} stores fully complete
            (both BAR and KITCHEN received)
          </span>
          <span class="info-pill" style="color:{RED}; border-color:{RED};">
            \u274c {total_expected - complete_count} incomplete
          </span>
        </div>
        """, unsafe_allow_html=True)

        # ── Helper to render a store group ───────────────────────────────────
        def _render_store_group(title, stores, loaded_stores_set):
            is_rn1_group = all(is_rn1_store(s) for s in stores) if stores else False

            if is_rn1_group:
                col_header = (
                    f'<div style="display:flex; align-items:center; gap:0; '
                    f'background:rgba(26,26,26,0.04); border:1px solid {BORDER}; '
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
                    f'background:rgba(26,26,26,0.04); border:1px solid {BORDER}; '
                    f'border-radius:3px; padding:6px 12px; margin-bottom:2px; '
                    f'font-size:0.68rem; font-weight:700; letter-spacing:0.1em; '
                    f'text-transform:uppercase; color:{GOLD};">'
                    f'<span style="flex:3;">{title}</span>'
                    f'<span style="flex:1; text-align:center;">BAR</span>'
                    f'<span style="flex:1; text-align:center;">KITCHEN</span>'
                    f'</div>'
                )
            st.markdown(col_header, unsafe_allow_html=True)

            for store in stores:
                if is_rn1_store(store):
                    submitted = check_rn1_submitted(store, loaded_stores_set)
                    icon = "\u2705" if submitted else "\u274c"
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
                    bar_ok, kit_ok = check_bar_kitchen(store, loaded_stores_set)
                    bar_icon = "\u2705" if bar_ok else "\u274c"
                    kit_icon = "\u2705" if kit_ok else "\u274c"
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

        # ── Unrecognized Stores ──────────────────────────────────────────────
        expected_names = all_expected_pdf_names(groups)
        unrecognized = sorted(
            s for s in loaded_stores
            if normalize_store(s) not in expected_names
        )
        if unrecognized:
            st.markdown("---")
            st.markdown(
                f'<div class="section-label">Unrecognized Stores \u2014 '
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
                    'Amount': f"\u20b1{df[df['Store'] == s]['Total Amount'].sum():,.2f}",
                }
                for s in unrecognized
            ])
            st.dataframe(unrec_df, use_container_width=True, hide_index=True)
