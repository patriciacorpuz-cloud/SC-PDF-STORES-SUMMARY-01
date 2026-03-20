"""All constants: sheet IDs, column widths, design tokens, prefix maps."""

from pathlib import Path
import base64

# ─── DESIGN TOKENS ─────────────────────────────────────────────────────────────
GOLD   = "#C9A96E"
DARK   = "#0D0D0D"
CARD   = "#141414"
BORDER = "#2A2A2A"
TEXT   = "#F0EDE8"
MUTED  = "#888880"
GREEN  = "#4CAF50"
RED    = "#E53935"

# ─── CHART LAYOUT ──────────────────────────────────────────────────────────────
CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Jost, sans-serif", color=TEXT, size=11),
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
