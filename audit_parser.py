#!/usr/bin/env python3
"""Diagnostic script: audit PDF parser against real sample PDFs.
Self-contained — copies parser logic to avoid Python 3.9 type hint issues with app.py.
"""

import pdfplumber
import io
import re
import pandas as pd
from pathlib import Path
from collections import Counter
from typing import Optional

PDF_DIR = Path("/Users/patriciacorpuz/Downloads")
PDF_PATTERN = "ABC-*.pdf"

# ─── Copied parser functions (from app.py, adapted for Python 3.9) ───────────

def clean_store_name(raw_name: str) -> str:
    n = raw_name.strip()
    if n.upper().startswith('SYS_OPS_'):
        n = n[8:]
        m = re.match(r'([A-Za-z0-9\-]+?)_\d{4}_', n)
        store_part = m.group(1) if m else n.split('_')[0]
        upper = n.upper()
        if 'ADDITIONAL ORDER' in upper:
            return f"{store_part}-ADDITIONAL ORDER"
        elif 'PICK LIST-KITCHEN' in upper or 'PICKLIST-KITCHEN' in upper:
            return f"{store_part}-KITCHEN"
        elif 'PICK LIST-BAR' in upper or 'PICKLIST-BAR' in upper:
            return f"{store_part}-BAR"
        else:
            return store_part
    n = re.sub(r'\s*-\s*\d{2}_\d{2}_\d{2,4}.*$', '', n).strip()
    n = re.sub(r'\s*\((?:CS\s*\d*|FS|F|B|\d+)\)\s*$', '', n, flags=re.IGNORECASE).strip()
    n = re.sub(r'\s*\((?:CS\s*\d*|FS|F|B|\d+)\)\s*$', '', n, flags=re.IGNORECASE).strip()
    return n

_STORE_ALIAS_MAP = {
    "TCS-MAHI": "ABC-MAHI",
    "TCS-MANDANI": "ABC-MANDANI",
    "TCS MAHI": "ABC-MAHI",
    "TCS MANDANI": "ABC-MANDANI",
}

def _normalize_store(name: str) -> str:
    n = name.upper().strip()
    n = re.sub(r'\s*-\s*\d{2}_\d{2}_\d{2,4}.*$', '', n).strip()
    n = re.sub(r'\s*\((?:CS\s*\d*|FS|F|B|\d+)\)\s*$', '', n).strip()
    n = re.sub(r'\s*\((?:CS\s*\d*|FS|F|B|\d+)\)\s*$', '', n).strip()
    n = re.sub(r'-\([A-Z]+\)\s*', '-', n)
    n = re.sub(r'\s+(?:FS|CS)\s*$', '', n).strip()
    n = re.sub(r'-{2,}', '-', n)
    n = re.sub(r'\s+', ' ', n).strip()
    suffix = ''
    for suf in ('-BAR', '-KITCHEN', ' BAR', ' KITCHEN', '-ADDITIONAL ORDER'):
        if n.endswith(suf):
            suffix = suf
            n = n[:-len(suf)]
            break
    if n in _STORE_ALIAS_MAP:
        n = _STORE_ALIAS_MAP[n]
    n = n + suffix
    return n

def extract_header_total(text: str) -> Optional[float]:
    match = re.search(r'TOTAL\s+AMOUNT[:\s]*([\d,]+\.?\d*)', text, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1).replace(',', ''))
        except ValueError:
            return None
    return None

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

def fix_merged_uom_amount(uom_val, amt_val, days_val):
    m = re.match(r'^([A-Za-z]{2,})\s*(\d[\d,]*\.?\d*)$', uom_val.strip())
    if m:
        return m.group(1), m.group(2), amt_val if amt_val else days_val
    if amt_val:
        m2 = re.match(r'^([A-Za-z]+)(\d[\d,]*\.?\d*)$', amt_val.strip())
        if m2:
            return uom_val + m2.group(1), m2.group(2), days_val
    return uom_val, amt_val, days_val

def _join_fragmented_cells(row):
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

def parse_pdf(pdf_bytes, filename):
    rows = []
    warnings = []
    raw_store_name = Path(filename).stem
    store_name = clean_store_name(raw_store_name)
    order_date = ""
    delivery_date = ""
    ordered_by = ""
    header_total = None
    known_col_count = None
    last_location = ""

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
                    order_date = ""
                    delivery_date = ""
                    header_total = extract_header_total(text)

                tables = page.extract_tables({
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines"
                })
                for table in tables:
                    if not table or len(table) < 1:
                        continue

                    header_idx = None
                    for i, row in enumerate(table):
                        if row and any('LOCATION' in str(cell or '').upper() for cell in row):
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

                        idx_loc = col('LOCATION')
                        idx_plu = col('PLU')
                        idx_order = col('ORDER')
                        idx_item = col('ITEM') or col('DESCRIPTION')
                        idx_uom = col('UOM')
                        idx_amt = col('TOTAL AMOUNT') or col('AMOUNT')
                        idx_days = col('DAYS')
                        data_rows = table[header_idx + 1:]
                    else:
                        if known_col_count is None:
                            warnings.append(f"Page {page_num+1}: skipped - no header row and no prior column layout")
                            continue
                        data_rows = table

                    for row in data_rows:
                        if not row:
                            continue
                        row = _join_fragmented_cells(row)

                        def get(idx):
                            if idx is None or idx >= len(row):
                                return ''
                            return ' '.join(str(row[idx] or '').split()).strip()

                        location = get(idx_loc)
                        item = get(idx_item)

                        if not item or item.upper() in ('ITEM DESCRIPTION', 'DESCRIPTION'):
                            continue

                        if location and location.upper() != 'LOCATION':
                            last_location = location

                        raw_uom = get(idx_uom)
                        raw_amt = get(idx_amt)
                        raw_days = get(idx_days)
                        fixed_uom, fixed_amt, fixed_days = fix_merged_uom_amount(raw_uom, raw_amt, raw_days)

                        if not fixed_amt or fixed_amt.strip() == '':
                            warnings.append(f"Blank amount: {store_name} -> {item} (UOM: {fixed_uom})")

                        rows.append({
                            'Store': store_name,
                            'Order Date': order_date,
                            'Delivery Date': delivery_date,
                            'Ordered By': ordered_by,
                            'Location': location if (location and location.upper() != 'LOCATION') else '',
                            'PLU Code': get(idx_plu),
                            'Order Qty': get(idx_order),
                            'Item Description': item,
                            'UOM': fixed_uom,
                            'Total Amount': fixed_amt,
                            'Days to Last': fixed_days,
                        })

    except Exception as e:
        warnings.append(f"Could not parse {filename}: {e}")

    df = pd.DataFrame(rows)
    return df, warnings, header_total


# ─── Audit logic ─────────────────────────────────────────────────────────────

def audit_single_pdf(filepath):
    with open(filepath, "rb") as f:
        pdf_bytes = f.read()

    filename = filepath.name
    df, warnings, header_total = parse_pdf(pdf_bytes, filename)

    # Get page count
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        num_pages = len(pdf.pages)

    # Calculate parsed total
    if not df.empty:
        amounts = pd.to_numeric(
            df['Total Amount'].astype(str).str.replace(',', '').str.strip(),
            errors='coerce'
        )
        parsed_total = amounts.sum()
    else:
        parsed_total = 0.0

    # Flag problematic rows
    bad_rows = []
    if not df.empty:
        for idx, row in df.iterrows():
            issues = []
            if not row.get('Location') or str(row['Location']).strip() == '':
                issues.append('empty_location')
            plu = str(row.get('PLU Code', '')).strip()
            if plu and not plu.replace(' ', '').isdigit():
                issues.append(f'non_numeric_plu={plu}')
            amt = str(row.get('Total Amount', '')).strip()
            if not amt or amt == '' or amt == 'nan':
                issues.append('empty_amount')
            qty = str(row.get('Order Qty', '')).strip()
            if not qty or qty == '' or qty == 'nan':
                issues.append('empty_qty')
            if issues:
                bad_rows.append({
                    'row_idx': idx,
                    'item': row.get('Item Description', ''),
                    'location': row.get('Location', ''),
                    'plu': plu,
                    'amount': amt,
                    'qty': qty,
                    'issues': issues,
                })

    variance = None
    variance_pct = None
    if header_total and header_total > 0:
        variance = parsed_total - header_total
        variance_pct = (variance / header_total) * 100

    return {
        'filename': filename,
        'store_name': clean_store_name(Path(filename).stem),
        'normalized': _normalize_store(clean_store_name(Path(filename).stem)),
        'rows_extracted': len(df),
        'header_total': header_total,
        'parsed_total': parsed_total,
        'variance': variance,
        'variance_pct': variance_pct,
        'warnings': warnings,
        'bad_rows': bad_rows,
        'df': df,
        'num_pages': num_pages,
    }


def main():
    pdfs = sorted(PDF_DIR.glob(PDF_PATTERN))
    if not pdfs:
        print(f"No PDFs found matching {PDF_DIR / PDF_PATTERN}")
        return

    print(f"\n{'='*80}")
    print(f"  PDF PARSER AUDIT REPORT")
    print(f"  {len(pdfs)} PDFs found in {PDF_DIR}")
    print(f"{'='*80}\n")

    all_results = []
    total_issues = 0

    for pdf_path in pdfs:
        result = audit_single_pdf(pdf_path)
        all_results.append(result)

        status = "OK" if (result['variance_pct'] is None or abs(result['variance_pct']) < 0.1) else "MISMATCH"
        icon = "+" if status == "OK" else "!!!"

        print(f"[{icon}] {result['filename']}")
        print(f"    Store: {result['store_name']}  ->  Normalized: {result['normalized']}")
        print(f"    Pages: {result['num_pages']}, Rows extracted: {result['rows_extracted']}")

        if result['header_total'] is not None:
            print(f"    Header total: P{result['header_total']:,.2f}")
            print(f"    Parsed total: P{result['parsed_total']:,.2f}")
            if result['variance'] is not None:
                print(f"    Variance: P{result['variance']:,.2f} ({result['variance_pct']:+.2f}%)")
        else:
            print(f"    Header total: NOT FOUND")
            print(f"    Parsed total: P{result['parsed_total']:,.2f}")

        if result['warnings']:
            print(f"    Warnings ({len(result['warnings'])}):")
            for w in result['warnings']:
                print(f"      - {w}")

        if result['bad_rows']:
            print(f"    Bad rows ({len(result['bad_rows'])}):")
            for br in result['bad_rows']:
                print(f"      Row {br['row_idx']}: {br['item'][:40]:40s} | issues: {', '.join(br['issues'])}")
            total_issues += len(result['bad_rows'])

        print()

    # Summary
    print(f"{'='*80}")
    print(f"  SUMMARY")
    print(f"{'='*80}")
    print(f"  PDFs parsed: {len(all_results)}")
    print(f"  Total rows extracted: {sum(r['rows_extracted'] for r in all_results)}")
    print(f"  Total bad rows: {total_issues}")

    mismatches = [r for r in all_results if r['variance_pct'] is not None and abs(r['variance_pct']) > 0.1]
    if mismatches:
        print(f"\n  TOTAL MISMATCHES: {len(mismatches)}")
        for m in mismatches:
            print(f"    {m['filename']}: {m['variance_pct']:+.2f}% (P{m['variance']:,.2f})")
    else:
        print(f"\n  All totals match within 0.1% tolerance!")

    no_header = [r for r in all_results if r['header_total'] is None]
    if no_header:
        print(f"\n  PDFs without header total: {len(no_header)}")
        for r in no_header:
            print(f"    {r['filename']}")

    # Store name normalization
    print(f"\n  STORE NAME NORMALIZATION:")
    for r in all_results:
        print(f"    {r['filename'][:50]:50s} -> {r['normalized']}")

    # Detailed rows
    print(f"\n{'='*80}")
    print(f"  DETAILED ROW DATA (first 5 + last 3 rows per PDF)")
    print(f"{'='*80}")
    for r in all_results:
        print(f"\n  [{r['filename']}] ({r['rows_extracted']} rows)")
        if not r['df'].empty:
            show_df = r['df'][['Location', 'PLU Code', 'Item Description', 'Order Qty', 'UOM', 'Total Amount']]
            for idx, row in show_df.head(5).iterrows():
                print(f"    {idx:3d}: Loc={str(row['Location']):15s} PLU={str(row['PLU Code']):8s} "
                      f"Item={str(row['Item Description'])[:30]:30s} Qty={str(row['Order Qty']):5s} "
                      f"UOM={str(row['UOM']):8s} Amt={str(row['Total Amount']):10s}")
            if len(r['df']) > 8:
                print(f"    ... ({len(r['df']) - 8} rows omitted) ...")
            if len(r['df']) > 5:
                for idx, row in show_df.tail(3).iterrows():
                    print(f"    {idx:3d}: Loc={str(row['Location']):15s} PLU={str(row['PLU Code']):8s} "
                          f"Item={str(row['Item Description'])[:30]:30s} Qty={str(row['Order Qty']):5s} "
                          f"UOM={str(row['UOM']):8s} Amt={str(row['Total Amount']):10s}")
        else:
            print(f"    (no data)")


if __name__ == "__main__":
    main()
