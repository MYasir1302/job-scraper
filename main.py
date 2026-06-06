"""
main.py — Entry point for the LinkedIn Job Scraper.

Orchestrates: CLI → Scrape → Save → Log → Notify

Usage:
    python main.py                                          # interactive
    python main.py -k "Data Scientist" -l "Remote" -t 1   # CLI flags
"""

import sys

# Ensure stdout handles unicode on all platforms (Windows fix)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from utils import log
import config   # validates .env on import — exits early with clear message if broken


def main() -> None:
    from cli      import get_search_params
    from scraper  import scrape_linkedin_jobs
    from sheets   import get_worksheets, save_jobs, log_run
    from notifier import notify_all

    # ── 1. Parse search parameters ────────────────────────────────────────────
    keyword, location, time_filter, listing_type = get_search_params()

    # ── 2. Connect to Google Sheets ───────────────────────────────────────────
    ws_complete, ws_incomplete, ws_runlog = get_worksheets()

    # ── 3. Scrape LinkedIn ────────────────────────────────────────────────────
    complete_jobs, incomplete_jobs = scrape_linkedin_jobs(
        keyword, location, time_filter, listing_type
    )

    # ── 4. Save to Sheets (batch writes) ─────────────────────────────────────
    new_complete   = save_jobs(ws_complete,   complete_jobs,   "✅ Complete Jobs")
    new_incomplete = save_jobs(ws_incomplete, incomplete_jobs, "⚠️  Incomplete Jobs")
    new_total      = new_complete + new_incomplete

    # ── 5. Log this run ───────────────────────────────────────────────────────
    time_label    = config.TIME_FILTER_LABELS.get(time_filter, time_filter)
    listing_label = listing_type.get("label", "Any")
    log_run(
        ws_runlog,
        keyword           = keyword,
        location          = location,
        time_filter_label = f"{time_label} | {listing_label}",
        complete_count    = len(complete_jobs),
        incomplete_count  = len(incomplete_jobs),
        new_total         = new_total,
    )

    # ── 6. Optional notifications ─────────────────────────────────────────────
    notify_all(
        keyword    = keyword,
        location   = location,
        complete   = len(complete_jobs),
        incomplete = len(incomplete_jobs),
        new_total  = new_total,
    )

    # ── 7. Summary ────────────────────────────────────────────────────────────
    log.info("=" * 52)
    log.info("🎉  Done!")
    log.info(f"    Listing type:          {listing_label}")
    log.info(f"    Complete jobs found:   {len(complete_jobs)}")
    log.info(f"    Incomplete jobs found: {len(incomplete_jobs)}")
    log.info(f"    New rows saved:        {new_total}")
    log.info(f"    🔗  https://docs.google.com/spreadsheets/d/{config.SHEET_ID}")
    log.info("=" * 52)


if __name__ == "__main__":
    main()
