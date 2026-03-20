"""Store name normalization, alias mapping, and prefix grouping."""

import re
from collections import OrderedDict
from typing import Dict, List, Set, Tuple

from config import STORE_ALIAS_MAP, PREFIX_GROUP_MAP


def clean_store_name(raw_name: str) -> str:
    """Strip date suffix, OS duplicate markers, and SYS_OPS prefix from filenames.
    Handles: ' - 03_15_26', ' - 03_21_26 (1)', trailing ' (CS 2)', ' (FS)', SYS_OPS_ prefix.
    """
    n = raw_name.strip()

    # Handle SYS_OPS_ filenames
    if n.upper().startswith('SYS_OPS_'):
        n = n[8:]
        m = re.match(r'([A-Za-z0-9\-]+?)_\d{4}_', n)
        if m:
            store_part = m.group(1)
        else:
            store_part = n.split('_')[0]
        upper = n.upper()
        if 'ADDITIONAL ORDER' in upper:
            return f"{store_part}-ADDITIONAL ORDER"
        elif 'PICK LIST-KITCHEN' in upper or 'PICKLIST-KITCHEN' in upper:
            return f"{store_part}-KITCHEN"
        elif 'PICK LIST-BAR' in upper or 'PICKLIST-BAR' in upper:
            return f"{store_part}-BAR"
        else:
            return store_part

    # Standard filenames
    n = re.sub(r'\s*-\s*\d{2}_\d{2}_\d{2,4}.*$', '', n).strip()
    n = re.sub(r'\s*\((?:CS\s*\d*|FS|F|B|\d+)\)\s*$', '', n, flags=re.IGNORECASE).strip()
    n = re.sub(r'\s*\((?:CS\s*\d*|FS|F|B|\d+)\)\s*$', '', n, flags=re.IGNORECASE).strip()
    return n


def normalize_store(name: str) -> str:
    """Normalize a store name for matching between master list and parsed PDFs.
    Strips: type codes -(CS)/(F), trailing suffixes (CS 2)/(FS)/(1), date remnants,
    trailing FS/CS labels from master list names. Applies alias mapping.
    """
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
    if n in STORE_ALIAS_MAP:
        n = STORE_ALIAS_MAP[n]
    n = n + suffix

    return n


def auto_group_stores(store_names: List[str]) -> Dict[str, List[str]]:
    """Group a flat list of store names by prefix into an ordered dict."""
    grouped = OrderedDict()
    for name in store_names:
        upper = name.upper()
        matched_group = "OTHER"
        for prefix, group_name in PREFIX_GROUP_MAP:
            if upper.startswith(prefix.upper()):
                matched_group = group_name
                break
        grouped.setdefault(matched_group, []).append(name)
    return grouped


def check_bar_kitchen(store: str, loaded_stores: Set[str]) -> Tuple[bool, bool]:
    """Check if BAR and KITCHEN PDFs exist for a given master store name."""
    norm = normalize_store(store)
    bar_found = False
    kitchen_found = False
    for ls in loaded_stores:
        ls_norm = normalize_store(ls)
        if ls_norm == f"{norm}-BAR" or ls_norm == f"{norm} BAR":
            bar_found = True
        if ls_norm == f"{norm}-KITCHEN" or ls_norm == f"{norm} KITCHEN":
            kitchen_found = True
        if bar_found and kitchen_found:
            break
    return bar_found, kitchen_found


def is_rn1_store(store: str) -> bool:
    """RN1 stores only submit one PDF (no BAR/KITCHEN split)."""
    return store.upper().startswith("RN1")


def check_rn1_submitted(store: str, loaded_stores: Set[str]) -> bool:
    """For RN1 stores, check if any PDF matching the store name was parsed."""
    norm = normalize_store(store)
    for ls in loaded_stores:
        ls_norm = normalize_store(ls)
        if ls_norm == norm or ls_norm.startswith(norm):
            return True
    return False


def compute_checklist_summary(
    groups: Dict[str, List[str]], loaded_stores: Set[str]
) -> Tuple[int, int]:
    """Return (fully_complete_count, total_stores) across all groups."""
    complete = 0
    total = 0
    for stores in groups.values():
        for store in stores:
            total += 1
            if is_rn1_store(store):
                if check_rn1_submitted(store, loaded_stores):
                    complete += 1
            else:
                bar_ok, kit_ok = check_bar_kitchen(store, loaded_stores)
                if bar_ok and kit_ok:
                    complete += 1
    return complete, total


def all_expected_pdf_names(groups: Dict[str, List[str]]) -> Set[str]:
    """Build a set of all expected normalized store names for unrecognized-store detection."""
    expected = set()
    for stores in groups.values():
        for store in stores:
            norm = normalize_store(store)
            if is_rn1_store(store):
                expected.add(norm)
            else:
                expected.add(f"{norm}-BAR")
                expected.add(f"{norm} BAR")
                expected.add(f"{norm}-KITCHEN")
                expected.add(f"{norm} KITCHEN")
    return expected
