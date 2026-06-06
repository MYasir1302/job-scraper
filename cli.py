"""
cli.py — Command-line interface for the LinkedIn Job Scraper.

Supports both:
  1. Interactive mode  (run with no --keyword / --location flags)
  2. Direct CLI mode   (pass flags for scripting / cron / automation)

Examples:
  python main.py
  python main.py --keyword "Data Scientist" --location "Remote" --time 1
  python main.py -k "Backend Developer" -l "United States" -t 3
"""

import argparse
import sys

import config
from utils import log


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="linkedin-scraper",
        description="Scrape LinkedIn job listings into Google Sheets.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Time filter options:
  1  →  Last 24 hours  (default)
  2  →  Last 48 hours
  3  →  Last week

Location presets:
  Pakistan, United States, United Kingdom, Canada, Australia, Remote
  (or any free-text location)

Examples:
  python main.py
  python main.py -k "Python Developer" -l "Pakistan" -t 1
  python main.py -k "ML Engineer"      -l "Remote"   -t 3
        """,
    )
    parser.add_argument(
        "-k", "--keyword",
        help="Job title / keyword to search for.",
    )
    parser.add_argument(
        "-l", "--location",
        help="Location to search in (preset name or custom text).",
    )
    parser.add_argument(
        "-t", "--time",
        choices=["1", "2", "3"],
        default=None,
        help="Time filter: 1=24h (default), 2=48h, 3=1week.",
    )
    return parser


# ── Interactive fallback helpers ──────────────────────────────────────────────

def _prompt_keyword() -> str:
    print("\n💼 Select Job Type:")
    for k, v in config.JOB_TYPE_PRESETS.items():
        print(f"  {k}. {v}")
    print(f"  {len(config.JOB_TYPE_PRESETS) + 1}. Custom (type your own)")

    choice = input("\nEnter number: ").strip()
    if choice in config.JOB_TYPE_PRESETS:
        return config.JOB_TYPE_PRESETS[choice]
    if choice == str(len(config.JOB_TYPE_PRESETS) + 1):
        return input("Enter your custom job type: ").strip()
    log.warning("Invalid choice — defaulting to 'Python Developer'")
    return "Python Developer"


def _prompt_location() -> str:
    print("\n📌 Select Job Location:")
    for k, v in config.LOCATION_PRESETS.items():
        print(f"  {k}. {v}")
    print(f"  {len(config.LOCATION_PRESETS) + 1}. Custom (type your own)")

    choice = input("\nEnter number: ").strip()
    if choice in config.LOCATION_PRESETS:
        return config.LOCATION_PRESETS[choice]
    if choice == str(len(config.LOCATION_PRESETS) + 1):
        return input("Enter your custom location: ").strip()
    log.warning("Invalid choice — defaulting to 'Pakistan'")
    return "Pakistan"


def _prompt_time_filter() -> str:
    print("\n⏰ Select Time Filter:")
    labels = {
        "1": "Last 24 hours",
        "2": "Last 48 hours",
        "3": "Last week",
    }
    for k, v in labels.items():
        print(f"  {k}. {v}")

    choice = input("\nEnter number (1-3): ").strip()
    if choice in config.TIME_FILTER_PRESETS:
        return config.TIME_FILTER_PRESETS[choice]
    log.warning("Invalid choice — defaulting to last 24 hours")
    return "r86400"


def _prompt_listing_type() -> dict:
    print("\n🎓 Select Listing Type:")
    for k, v in config.LISTING_TYPE_PRESETS.items():
        print(f"  {k}. {v['label']}")

    choice = input("\nEnter number: ").strip()
    if choice in config.LISTING_TYPE_PRESETS:
        return config.LISTING_TYPE_PRESETS[choice]
    log.warning("Invalid choice — defaulting to 'Any'")
    return config.LISTING_TYPE_PRESETS["1"]


# ── Public entry point ────────────────────────────────────────────────────────

def get_search_params() -> tuple[str, str, str, dict]:
    """
    Parse CLI args; fall back to interactive prompts for any missing value.

    Returns:
        (keyword, location, time_filter_code, listing_type_dict)
    """
    parser = build_parser()
    args   = parser.parse_args()

    # ── keyword ───────────────────────────────────────────────────────────────
    if args.keyword:
        keyword = args.keyword.strip()
    else:
        print("=" * 52)
        print("   🤖  LinkedIn Job Scraper")
        print("=" * 52)
        keyword = _prompt_keyword()

    # ── location ─────────────────────────────────────────────────────────────
    if args.location:
        location = args.location.strip()
    else:
        location = _prompt_location()

    # ── time filter ───────────────────────────────────────────────────────────
    if args.time:
        time_filter = config.TIME_FILTER_PRESETS[args.time]
    else:
        time_filter = _prompt_time_filter()

    # ── listing type (internship / full-time / etc.) ──────────────────────────
    listing_type = _prompt_listing_type()

    label = config.TIME_FILTER_LABELS.get(time_filter, time_filter)
    log.info(
        f"🔎 Search: '{keyword}'  |  📍 {location}  |  "
        f"⏰ {label}  |  🎓 {listing_type['label']}"
    )
    print("=" * 52)

    return keyword, location, time_filter, listing_type
