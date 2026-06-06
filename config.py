"""
config.py — Centralized configuration loader.

Reads from .env file (or environment variables) and validates
required settings before the app starts.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root
load_dotenv(Path(__file__).parent / ".env")


def _require(key: str) -> str:
    """Return env var or exit with a clear message."""
    value = os.getenv(key, "").strip()
    if not value:
        print(f"❌  Missing required config: {key}")
        print(f"    Add it to your .env file.  See .env.example for reference.")
        sys.exit(1)
    return value


# ── Google Sheets ────────────────────────────────────────────────────────────
CREDENTIALS_FILE: str = _require("CREDENTIALS_FILE")
SHEET_ID: str         = _require("SHEET_ID")

# Validate credentials file actually exists
if not Path(CREDENTIALS_FILE).exists():
    print(f"❌  Credentials file not found: {CREDENTIALS_FILE}")
    print(f"    Make sure the path in your .env is correct.")
    sys.exit(1)

# Validate Sheet ID looks plausible (basic sanity check)
if len(SHEET_ID) < 20 or " " in SHEET_ID:
    print(f"❌  SHEET_ID looks invalid: '{SHEET_ID}'")
    print(f"    Copy the long ID from your Google Sheets URL.")
    sys.exit(1)

# ── Scraper behaviour ────────────────────────────────────────────────────────
SCROLL_CYCLES: int   = int(os.getenv("SCROLL_CYCLES", "6"))
SCROLL_PAUSE: float  = float(os.getenv("SCROLL_PAUSE", "2.0"))
PAGE_LOAD_WAIT: float = float(os.getenv("PAGE_LOAD_WAIT", "5.0"))
MAX_RETRIES: int     = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY: float   = float(os.getenv("RETRY_DELAY", "4.0"))

# ── Notifications (optional) ─────────────────────────────────────────────────
SLACK_WEBHOOK_URL: str = os.getenv("SLACK_WEBHOOK_URL", "")
NOTIFY_EMAIL: str      = os.getenv("NOTIFY_EMAIL", "")

# ── Location presets ─────────────────────────────────────────────────────────
LOCATION_PRESETS: dict[str, str] = {
    "1": "Pakistan",
    "2": "United States",
    "3": "United Kingdom",
    "4": "Canada",
    "5": "Australia",
    "6": "Remote",
}

# ── Job type presets ─────────────────────────────────────────────────────────
JOB_TYPE_PRESETS: dict[str, str] = {
    "1": "Python Developer",
    "2": "Web Developer",
    "3": "Data Scientist",
    "4": "Machine Learning Engineer",
    "5": "Frontend Developer",
    "6": "Backend Developer",
    "7": "Full Stack Developer",
    "8": "DevOps Engineer",
}

# ── Time filter presets ──────────────────────────────────────────────────────
TIME_FILTER_PRESETS: dict[str, str] = {
    "1": "r86400",   # Last 24 hours
    "2": "r172800",  # Last 48 hours
    "3": "r604800",  # Last week
}

TIME_FILTER_LABELS: dict[str, str] = {
    "r86400":  "Last 24 hours",
    "r172800": "Last 48 hours",
    "r604800": "Last week",
}

# ── Job experience / listing type filter ─────────────────────────────────────
# LinkedIn URL param: f_E  (experience level)  &  f_JT  (job type)
#
# f_E values:  1=Internship  2=Entry level  3=Associate
#              4=Mid-Senior  5=Director     6=Executive
#
# f_JT values: F=Full-time  P=Part-time  C=Contract
#              T=Temporary  I=Internship  V=Volunteer  O=Other
#
# We expose a single "listing type" menu that sets the right param.

LISTING_TYPE_PRESETS: dict[str, dict] = {
    "1": {"label": "Any (all types)",      "f_E": "",   "f_JT": ""},
    "2": {"label": "Internship",           "f_E": "1",  "f_JT": "I"},
    "3": {"label": "Entry Level",          "f_E": "2",  "f_JT": "F"},
    "4": {"label": "Full-time",            "f_E": "",   "f_JT": "F"},
    "5": {"label": "Part-time",            "f_E": "",   "f_JT": "P"},
    "6": {"label": "Contract",             "f_E": "",   "f_JT": "C"},
    "7": {"label": "Mid-Senior Level",     "f_E": "4",  "f_JT": "F"},
}
