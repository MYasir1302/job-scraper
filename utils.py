"""
utils.py — Shared utilities: logging, retry decorator, URL helpers.
"""

import logging
import random
import time
import functools
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


# ── Logging setup ─────────────────────────────────────────────────────────────

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

_log_file = LOG_DIR / "scraper.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),                          # console
        logging.FileHandler(_log_file, encoding="utf-8") # file
    ],
)

log = logging.getLogger("linkedin_scraper")


# ── Retry decorator ───────────────────────────────────────────────────────────

def retry(max_attempts: int = 3, delay: float = 4.0, exceptions=(Exception,)):
    """
    Decorator that retries a function up to *max_attempts* times on failure.

    Usage:
        @retry(max_attempts=3, delay=2.0)
        def flaky_function(): ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    wait = delay * attempt + random.uniform(0.5, 1.5)
                    log.warning(
                        f"Attempt {attempt}/{max_attempts} failed for "
                        f"{func.__name__!r}: {exc}. Retrying in {wait:.1f}s…"
                    )
                    time.sleep(wait)
            log.error(f"All {max_attempts} attempts failed for {func.__name__!r}.")
            raise last_exc
        return wrapper
    return decorator


# ── URL helpers ───────────────────────────────────────────────────────────────

def clean_linkedin_url(url: str) -> str:
    """
    Strip LinkedIn tracking parameters and normalise the job URL so that
    deduplication works correctly regardless of how the link was obtained.

    Keeps only the core job path + `currentJobId` query param when present.
    """
    if not url:
        return url
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        # Extract the stable job ID if available
        job_id = params.get("currentJobId", [""])[0]
        clean_query = urlencode({"currentJobId": job_id}) if job_id else ""
        clean = urlunparse((
            parsed.scheme, parsed.netloc, parsed.path,
            "", clean_query, ""
        ))
        return clean
    except Exception:
        return url


def extract_job_id(url: str) -> str:
    """
    Extract the numeric LinkedIn job ID from a URL.
    Used as the deduplication key — more stable than the full URL.

    Examples:
        https://www.linkedin.com/jobs/view/1234567890/  → "1234567890"
        https://www.linkedin.com/jobs/search/?currentJobId=9876543210 → "9876543210"
    """
    if not url:
        return url
    try:
        parsed = urlparse(url)
        # Pattern 1: /jobs/view/<id>/
        parts = [p for p in parsed.path.split("/") if p.isdigit()]
        if parts:
            return parts[-1]
        # Pattern 2: ?currentJobId=<id>
        params = parse_qs(parsed.query)
        job_id = params.get("currentJobId", [""])[0]
        if job_id:
            return job_id
    except Exception:
        pass
    return clean_linkedin_url(url)   # fallback to cleaned URL


# ── Human-like delay ──────────────────────────────────────────────────────────

def human_delay(min_sec: float = 1.5, max_sec: float = 4.0) -> None:
    """Sleep for a random duration to mimic human browsing behaviour."""
    time.sleep(random.uniform(min_sec, max_sec))
