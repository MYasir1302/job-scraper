"""
sheets.py — Google Sheets integration.

Features:
  - Connects via service-account credentials
  - Sheet 1: ✅ Complete Jobs
  - Sheet 2: ⚠️  Incomplete Jobs
  - Sheet 3: 📈 Run Log  (one row per scraper run)
  - Batch writes (one API call per sheet, not one per row)
  - Deduplicates by job ID extracted from the URL
  - Retry wrapper around gspread calls
"""

import time
from datetime import datetime
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

import config
from scraper import JobListing
from utils import log, retry, extract_job_id


# ── Sheet column headers ──────────────────────────────────────────────────────

COMPLETE_HEADERS   = ["Title", "Company", "Location", "Link", "Date Posted", "Work Type", "Seniority", "Scraped At"]
INCOMPLETE_HEADERS = ["Title", "Company", "Location", "Link", "Date Posted", "Work Type", "Seniority", "Scraped At"]
RUN_LOG_HEADERS    = ["Run At", "Keyword", "Location", "Time Filter", "Complete", "Incomplete", "Total New", "Sheet URL"]


# ── Connection ────────────────────────────────────────────────────────────────

@retry(max_attempts=3, delay=3.0)
def get_worksheets() -> tuple[gspread.Worksheet, gspread.Worksheet, gspread.Worksheet]:
    """
    Open the Google Spreadsheet and return (complete_ws, incomplete_ws, runlog_ws).
    Creates missing sheets and writes headers on first use.
    """
    log.info("📊 Connecting to Google Sheets…")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds  = Credentials.from_service_account_file(config.CREDENTIALS_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    sheet  = client.open_by_key(config.SHEET_ID)

    # ── Helper ────────────────────────────────────────────────────────────────
    def _get_or_create(index: int, title: str, headers: list[str]) -> gspread.Worksheet:
        try:
            ws = sheet.get_worksheet(index)
            ws.update_title(title)
        except Exception:
            ws = sheet.add_worksheet(title=title, rows="5000", cols=str(len(headers)))
        # Write headers if the sheet is empty
        if not ws.get_all_values():
            ws.append_row(headers, value_input_option="USER_ENTERED")
        return ws

    ws_complete   = _get_or_create(0, "✅ Complete Jobs",   COMPLETE_HEADERS)
    ws_incomplete = _get_or_create(1, "⚠️ Incomplete Jobs", INCOMPLETE_HEADERS)
    ws_runlog     = _get_or_create(2, "📈 Run Log",         RUN_LOG_HEADERS)

    log.info(f"✅ Connected! 🔗 https://docs.google.com/spreadsheets/d/{config.SHEET_ID}")
    return ws_complete, ws_incomplete, ws_runlog


# ── Save helpers ──────────────────────────────────────────────────────────────

def _existing_job_ids(worksheet: gspread.Worksheet) -> set[str]:
    """
    Return a set of job IDs already present in the sheet.
    Uses the Link column (index 3, zero-based) for extraction.
    """
    all_rows = worksheet.get_all_values()
    ids: set[str] = set()
    for row in all_rows[1:]:   # skip header
        if len(row) > 3 and row[3]:
            ids.add(extract_job_id(row[3]))
    return ids


@retry(max_attempts=3, delay=3.0)
def save_jobs(
    worksheet: gspread.Worksheet,
    jobs: list[JobListing],
    sheet_label: str = "Sheet",
) -> int:
    """
    Batch-append new (non-duplicate) jobs to *worksheet*.

    Returns the count of rows actually written.
    """
    if not jobs:
        log.info(f"  No jobs to save in {sheet_label}.")
        return 0

    log.info(f"💾 Saving up to {len(jobs)} jobs to {sheet_label}…")

    existing_ids = _existing_job_ids(worksheet)
    new_rows = [
        job.to_row()
        for job in jobs
        if job.job_id not in existing_ids
    ]

    skipped = len(jobs) - len(new_rows)

    if new_rows:
        # Single batch API call — much faster than looping append_row
        worksheet.append_rows(new_rows, value_input_option="USER_ENTERED")

    log.info(f"  ✅ {len(new_rows)} new rows written, {skipped} duplicates skipped — {sheet_label}")
    return len(new_rows)


@retry(max_attempts=3, delay=3.0)
def log_run(
    worksheet: gspread.Worksheet,
    keyword: str,
    location: str,
    time_filter_label: str,
    complete_count: int,
    incomplete_count: int,
    new_total: int,
) -> None:
    """Append a summary row to the Run Log sheet."""
    row = [
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        keyword,
        location,
        time_filter_label,
        complete_count,
        incomplete_count,
        new_total,
        f"https://docs.google.com/spreadsheets/d/{config.SHEET_ID}",
    ]
    worksheet.append_row(row, value_input_option="USER_ENTERED")
    log.info("📈 Run logged to Run Log sheet.")
