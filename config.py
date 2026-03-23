"""All constants: sheet IDs, column widths, design tokens, prefix maps."""

from pathlib import Path
import base64

# ─── DESIGN TOKENS ─────────────────────────────────────────────────────────────
ACCENT = "#C9A96E"     # Gold accent — nav bar brand, subtle highlights
DARK   = "#FAF8F5"     # Page background — warm off-white
CARD   = "#FFFFFF"     # Card backgrounds — white
BORDER = "#E5E0DA"     # Borders — warm grey
TEXT   = "#1A1A1A"     # Main text — dark
MUTED  = "#888880"     # Secondary text
GREEN  = "#4CAF50"     # Success
RED    = "#E53935"     # Error
GOLD   = TEXT          # Alias — accent references in CSS now resolve to dark

# ─── CHART LAYOUT ──────────────────────────────────────────────────────────────
CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Jost, sans-serif", color=MUTED, size=11),
    margin=dict(l=0, r=10, t=10, b=10),
)
GRID_STYLE = dict(gridcolor=BORDER, zerolinecolor=BORDER)

# ─── LOGO ──────────────────────────────────────────────────────────────────────
_LOGO_PATH = Path(__file__).parent / "assets" / "tag_logo.png"
try:
    with open(_LOGO_PATH, "rb") as _f:
        LOGO_B64 = base64.b64encode(_f.read()).decode()
except Exception:
    LOGO_B64 = ""

# ─── GOOGLE SHEET IDS ──────────────────────────────────────────────────────────
MASTER_SHEET_ID = "1eNFzPEpMnxi2GQupi_Ed9_owJMJllrpTzg0kVuyZtDU"
MASTER_SHEET_NAME = "STORE LIST"

# ─── STORE PREFIX GROUPS ───────────────────────────────────────────────────────
# Prefixes are checked in order; first match wins. Longer prefixes first.
PREFIX_GROUP_MAP = [
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

# ─── STORE ALIAS MAP ──────────────────────────────────────────────────────────
STORE_ALIAS_MAP = {
    "TCS-MAHI": "ABC-MAHI",
    "TCS-MANDANI": "ABC-MANDANI",
    "TCS MAHI": "ABC-MAHI",
    "TCS MANDANI": "ABC-MANDANI",
}
