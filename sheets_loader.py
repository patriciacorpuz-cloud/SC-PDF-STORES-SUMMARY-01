"""Google Sheets master list fetch."""
import streamlit as st
from typing import Dict, List

from config import MASTER_SHEET_ID, MASTER_SHEET_NAME
from store_matching import auto_group_stores


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


def _fetch_master_stores() -> Dict[str, List[str]]:
    """Fetch the master store list from the private Google Sheet.
    Auto-groups stores by prefix since the sheet is a flat list.
    Returns dict like {"ABC STORES": ["ABC-AYALA-BAR", ...], ...}.
    """
    try:
        gc = _get_gspread_client()
        sh = gc.open_by_key(MASTER_SHEET_ID)
        ws = sh.worksheet(MASTER_SHEET_NAME)
        all_values = ws.col_values(1)  # read first column (A)

        # Filter empty rows and strip whitespace
        stores = [v.strip() for v in all_values if v and v.strip()]

        if not stores:
            st.warning("Master store list sheet is empty.")
            return {}

        return auto_group_stores(stores)
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
