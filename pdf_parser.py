"""PDF parsing: parse_pdf(), column repair, metadata extraction, location resolution."""

import re
import io
import pdfplumber
import pandas as pd
from pathlib import Path
from collections import Counter
from typing import Optional, List, Tuple

from store_matching import clean_store_name


def extract_store_name(text: str) -> str:
    """Extract store name from PDF header text."""
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
    """Extract a date value (ORDER DATE or DELIVERY DATE) from PDF header."""
    match = re.search(rf'{label}\s+(\d{{1,2}}-\w+-\d{{2,4}})', text, re.IGNORECASE)
    return match.group(1) if match else ""


def extract_header_total(text: str) -> Optional[float]:
    """Extract TOTAL AMOUNT from PDF header for validation."""
    match = re.search(r'TOTAL\s+AMOUNT[:\s]*([\d,]+\.?\d*)', text, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1).replace(',', ''))
        except ValueError:
            return None
    return None


def extract_ordered_by(text: str) -> str:
    """Extract ORDERED BY from PDF header."""
    match = re.search(r'ORDERED\s+BY\s+(.+?)(?:\s+TOTAL|\s+PICKED|\n)', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ""


def fix_merged_uom_amount(
    uom_val: str, amt_val: str, days_val: str
) -> Tuple[str, str, str]:
    """Split merged UOM+Amount like 'SHEET50.00' or 'ROLLS102.00'.
    Returns (fixed_uom, fixed_amount, fixed_days).
    """
    # Case 1: UOM has a number merged in (e.g. 'SHEET50.00')
    m = re.match(r'^([A-Za-z]{2,})\s*(\d[\d,]*\.?\d*)$', uom_val.strip())
    if m:
        real_uom = m.group(1)
        real_amt = m.group(2)
        real_days = amt_val if amt_val else days_val
        return real_uom, real_amt, real_days

    # Case 2: Amount cell starts with letters (split across columns by pdfplumber)
    if amt_val:
        m2 = re.match(r'^([A-Za-z]+)(\d[\d,]*\.?\d*)$', amt_val.strip())
        if m2:
            real_uom = uom_val + m2.group(1)
            real_amt = m2.group(2)
            real_days = days_val
            return real_uom, real_amt, real_days

    return uom_val, amt_val, days_val


def _join_fragmented_cells(row: list) -> list:
    """Rejoin cells that got split across columns due to PDF line breaks.
    e.g. ['SECOND FLOO', 'R 20196', '1', ...] -> ['SECOND FLOOR', '20196', '1', ...]
    """
    if not row or len(row) < 2:
        return row
    joined = list(row)
    loc_val = str(joined[0] or '').strip()
    next_val = str(joined[1] or '').strip()
    if loc_val and next_val and re.match(r'^[A-Z]{1,3}\s+\d+', next_val):
        parts = next_val.split(None, 1)
        joined[0] = loc_val + parts[0]
        joined[1] = parts[1] if len(parts) > 1 else ''
    return joined


def _is_total_row(row_data: dict) -> bool:
    """Check if a row is a subtotal/total row that should be excluded."""
    item = str(row_data.get('item', '')).upper().strip()
    location = str(row_data.get('location', '')).upper().strip()
    if any(kw in item for kw in ('TOTAL', 'SUBTOTAL', 'GRAND TOTAL')):
        return True
    if any(kw in location for kw in ('TOTAL', 'SUBTOTAL')):
        return True
    return False


def parse_pdf(
    pdf_bytes: bytes, filename: str
) -> Tuple[pd.DataFrame, List[str], Optional[float]]:
    """Parse a single PDF file.
    Returns (DataFrame, list_of_warnings, header_total).
    """
    rows = []
    warnings = []
    raw_store_name = Path(filename).stem
    store_name = clean_store_name(raw_store_name)
    order_date    = ""
    delivery_date = ""
    ordered_by    = ""
    header_total  = None

    known_col_count = None
    last_location = ""

    # Column indices — persist across pages for continuation pages
    idx_loc = idx_plu = idx_order = idx_item = idx_uom = idx_amt = idx_days = None

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if page_num == 0:
                    if not re.match(r'^\d+$', raw_store_name):
                        pass
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

                # Fallback: if no tables found with lines strategy, try text strategy
                if not tables:
                    tables = page.extract_tables({
                        "vertical_strategy":   "text",
                        "horizontal_strategy": "text"
                    })
                    if tables:
                        warnings.append(
                            f"Page {page_num+1}: used text-based table extraction "
                            f"(no line borders detected)"
                        )

                for table in tables:
                    if not table or len(table) < 1:
                        continue

                    header_idx = None
                    for i, row in enumerate(table):
                        if not row:
                            continue
                        row_text = [str(cell or '').upper() for cell in row]
                        row_joined = ' '.join(row_text)
                        # Primary: look for LOCATION header
                        if any('LOCATION' in cell for cell in row_text):
                            header_idx = i
                            break
                        # Fallback: look for PLU + ITEM/DESCRIPTION combo
                        if ('PLU' in row_joined and
                                ('ITEM' in row_joined or 'DESCRIPTION' in row_joined)):
                            header_idx = i
                            break

                    if header_idx is not None:
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
                        idx_days  = col('DAYS') or col('MAXIMUM')

                        # Fallback: if ITEM/DESCRIPTION column not found by keyword,
                        # infer it positionally — it's typically between ORDER and UOM
                        if idx_item is None and idx_uom is not None:
                            # Item description is the column just before UOM
                            candidate = idx_uom - 1
                            # Make sure it's not already claimed by another column
                            used = {idx_loc, idx_plu, idx_order, idx_uom, idx_amt, idx_days}
                            if candidate >= 0 and candidate not in used:
                                idx_item = candidate

                        data_rows = table[header_idx + 1:]
                    else:
                        if known_col_count is None:
                            warnings.append(
                                f"Page {page_num+1}: skipped — no header row and no prior column layout"
                            )
                            continue
                        # Continuation page: validate column count, skip empty rows
                        data_rows = []
                        for row in table:
                            if not row:
                                continue
                            # Skip rows with wrong column count (different table structure)
                            if len(row) != known_col_count:
                                # Only warn if the row has actual content
                                has_content = any(
                                    str(c or '').strip() for c in row
                                )
                                if has_content:
                                    warnings.append(
                                        f"Page {page_num+1}: row skipped — "
                                        f"{len(row)} cols (expected {known_col_count})"
                                    )
                                continue
                            data_rows.append(row)

                    for row in data_rows:
                        if not row:
                            continue

                        row = _join_fragmented_cells(row)

                        def get(idx):
                            if idx is None or idx >= len(row):
                                return ''
                            return ' '.join(str(row[idx] or '').split()).strip()

                        location = get(idx_loc)
                        item     = get(idx_item)

                        if not item or item.upper() in ('ITEM DESCRIPTION', 'DESCRIPTION'):
                            continue

                        # Skip placeholder/instruction rows
                        if 'DO NOT TOUCH' in item.upper():
                            continue

                        # Track last seen location for forward-fill
                        if location and location.upper() != 'LOCATION':
                            last_location = location

                        raw_uom  = get(idx_uom)
                        raw_amt  = get(idx_amt)
                        raw_days = get(idx_days)
                        fixed_uom, fixed_amt, fixed_days = fix_merged_uom_amount(
                            raw_uom, raw_amt, raw_days
                        )

                        effective_location = (
                            location
                            if (location and location.upper() != 'LOCATION')
                            else ''
                        )

                        row_data = {
                            'Store':            store_name,
                            'Order Date':       order_date,
                            'Delivery Date':    delivery_date,
                            'Ordered By':       ordered_by,
                            'Location':         effective_location,
                            'PLU Code':         get(idx_plu),
                            'Order Qty':        get(idx_order),
                            'Item Description': item,
                            'UOM':              fixed_uom,
                            'Total Amount':     fixed_amt,
                            'Days to Last':     fixed_days,
                        }

                        # Filter total/subtotal rows
                        if _is_total_row({'item': item, 'location': effective_location}):
                            continue

                        # Forward-fill empty location from last seen
                        if not effective_location and last_location:
                            row_data['Location'] = last_location

                        if not fixed_amt or fixed_amt.strip() == '':
                            warnings.append(
                                f"Blank amount: {store_name} -> {item} (UOM: {fixed_uom})"
                            )

                        rows.append(row_data)

    except Exception as e:
        warnings.append(f"Could not parse {filename}: {e}")

    df = pd.DataFrame(rows)

    # Validate parsed total vs PDF header total
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
                    f"Total mismatch: parsed P{parsed_total:,.2f} vs PDF header P{header_total:,.2f} "
                    f"(diff {pct_diff:.1f}%) — some rows may have been lost"
                )
        # Reset to string so clean_numeric runs uniformly later
        df['Total Amount'] = df['Total Amount'].astype(str)

    return df, warnings, header_total


def resolve_empty_locations(df: pd.DataFrame, warnings: List[str]) -> pd.DataFrame:
    """Fill empty Location cells by cross-referencing item names.
    1. If the same item appears elsewhere in the same store with a location, use that.
    2. If the item appears across stores, use the most common location.
    3. Otherwise fill 'UNKNOWN' and log a warning.
    """
    if df.empty:
        return df

    empty_mask = df['Location'].str.strip().eq('') | df['Location'].isna()
    if not empty_mask.any():
        return df

    known = df[~empty_mask].groupby('Item Description')['Location'].apply(list).to_dict()

    for idx in df[empty_mask].index:
        item = df.at[idx, 'Item Description']
        store = df.at[idx, 'Store']
        resolved = ''

        if item in known:
            locs = known[item]
            same_store_locs = [
                df.at[i, 'Location']
                for i in df[
                    (df['Item Description'] == item) &
                    (df['Store'] == store) &
                    (~empty_mask)
                ].index
            ]
            if same_store_locs:
                resolved = Counter(same_store_locs).most_common(1)[0][0]
            else:
                resolved = Counter(locs).most_common(1)[0][0]

        if not resolved:
            resolved = 'UNKNOWN'
            warnings.append(f"Unknown location: {store} -> {item} — set to UNKNOWN")

        df.at[idx, 'Location'] = resolved

    return df


def clean_numeric(series: pd.Series) -> pd.Series:
    """Convert string amounts with commas to numeric."""
    return pd.to_numeric(
        series.astype(str).str.replace(',', '').str.strip(),
        errors='coerce'
    )
