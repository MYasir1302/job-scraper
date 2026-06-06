"""
scraper.py — LinkedIn job scraper using Selenium.

Features:
  - Headless Chrome with anti-detection headers
  - Multi-page pagination (scrapes all available pages)
  - Scroll until card count stabilises (loads all lazy cards)
  - Bot / CAPTCHA detection with early exit
  - Retry logic via @retry decorator
  - Random human-like delays
  - Extracts extra fields: date posted, work type, seniority
"""

import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from webdriver_manager.chrome import ChromeDriverManager

import config
from utils import log, retry, human_delay, extract_job_id, clean_linkedin_url


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class JobListing:
    title:       str = ""
    company:     str = ""
    location:    str = ""
    link:        str = ""
    date_posted: str = ""
    work_type:   str = ""   # Remote / Hybrid / On-site
    seniority:   str = ""
    scraped_at:  str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))

    @property
    def is_complete(self) -> bool:
        return bool(self.title and self.company and self.location and self.link)

    @property
    def job_id(self) -> str:
        return extract_job_id(self.link)

    def to_row(self) -> list:
        return [
            self.title,
            self.company,
            self.location,
            clean_linkedin_url(self.link),
            self.date_posted,
            self.work_type,
            self.seniority,
            self.scraped_at,
        ]


# ── Driver factory ────────────────────────────────────────────────────────────

def _build_driver() -> webdriver.Chrome:
    """Build a headless Chrome driver with anti-detection options."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )
    # Hide the webdriver flag via JS
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    return driver


# ── Bot / block detection ─────────────────────────────────────────────────────

_BLOCK_SIGNALS = [
    "authwall",
    "checkpoint",
    "login",
    "sign in to continue",
    "join now",
    "verify you are human",
    "captcha",
]

def _is_blocked(driver: webdriver.Chrome) -> bool:
    """Return True if LinkedIn has redirected us to an auth / bot wall."""
    url   = driver.current_url.lower()
    title = driver.title.lower()
    body  = driver.find_element(By.TAG_NAME, "body").text[:500].lower()
    return any(sig in url or sig in title or sig in body for sig in _BLOCK_SIGNALS)


# ── Card parser ───────────────────────────────────────────────────────────────

def _text(element, selector: str, fallback_selectors: list[str] = ()) -> str:
    """Try CSS selectors in order, return first non-empty text found."""
    for sel in (selector, *fallback_selectors):
        try:
            return element.find_element(By.CSS_SELECTOR, sel).text.strip()
        except NoSuchElementException:
            continue
    return ""


def _attr(element, selector: str, attribute: str, fallback_selectors: list[str] = ()) -> str:
    for sel in (selector, *fallback_selectors):
        try:
            value = element.find_element(By.CSS_SELECTOR, sel).get_attribute(attribute)
            return (value or "").strip()
        except NoSuchElementException:
            continue
    return ""


def _parse_card(card) -> Optional[JobListing]:
    """Extract a JobListing from a single base-card element."""
    try:
        job = JobListing()

        job.title = _text(
            card,
            "h3.base-search-card__title",
            ["h3.job-search-card__title", "h3"],
        )
        job.company = _text(
            card,
            "h4.base-search-card__subtitle",
            ["a.hidden-nested-link", "h4"],
        )
        job.location = _text(
            card,
            "span.job-search-card__location",
            ["[class*='location']"],
        )
        job.link = _attr(
            card,
            "a.base-card__full-link",
            "href",
            ["a[href*='/jobs/view/']", "a"],
        )
        job.date_posted = _attr(
            card,
            "time.job-search-card__listdate",
            "datetime",
            ["time[datetime]"],
        )
        job.work_type = _text(
            card,
            "li.job-search-card__benefits",
            ["[class*='workplace-type']", "[class*='remote']"],
        )
        job.seniority = _text(
            card,
            "[class*='seniority']",
            ["[class*='level']"],
        )

        return job if job.link else None   # must at least have a link

    except Exception as exc:
        log.debug(f"Card parse error: {exc}")
        return None


# ── Scroll until stable ───────────────────────────────────────────────────────

def _scroll_to_load_all(driver: webdriver.Chrome) -> None:
    """
    Scroll the page in a loop until the number of loaded job cards stops
    growing (or we hit a hard cap to avoid infinite loops).
    """
    MAX_SCROLL_ROUNDS = 15
    prev_count = 0

    for _ in range(MAX_SCROLL_ROUNDS):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(config.SCROLL_PAUSE)

        # Try clicking "Show more jobs" button if present
        try:
            btn = driver.find_element(By.CSS_SELECTOR, "button.infinite-scroller__show-more-button")
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(config.SCROLL_PAUSE)
        except NoSuchElementException:
            pass

        cards = driver.find_elements(By.CSS_SELECTOR, "div.base-card")
        current_count = len(cards)
        log.debug(f"  Scroll round: {current_count} cards loaded")

        if current_count == prev_count:
            break   # Nothing new — we've loaded everything
        prev_count = current_count


# ── Main scrape function ──────────────────────────────────────────────────────

@retry(max_attempts=config.MAX_RETRIES, delay=config.RETRY_DELAY)
def scrape_linkedin_jobs(
    keyword: str,
    location: str,
    time_filter: str,
    listing_type: dict | None = None,
) -> tuple[list[JobListing], list[JobListing]]:
    """
    Scrape LinkedIn job listings for the given search parameters.

    Args:
        keyword:      Job title / keyword
        location:     Location string
        time_filter:  LinkedIn f_TPR value (e.g. 'r86400')
        listing_type: Dict with keys 'f_E' and 'f_JT' from config.LISTING_TYPE_PRESETS

    Returns:
        (complete_jobs, incomplete_jobs)
        complete   — all four core fields present
        incomplete — have a link but missing one or more fields
    """
    listing_type = listing_type or {"f_E": "", "f_JT": ""}

    log.info(f"🚀 Starting Chrome driver…")
    driver = _build_driver()

    complete_jobs:   list[JobListing] = []
    incomplete_jobs: list[JobListing] = []
    seen_ids: set[str] = set()

    try:
        page = 0
        while True:
            start = page * 25

            # Build URL — only add f_E / f_JT params when they have a value
            url = (
                f"https://www.linkedin.com/jobs/search/"
                f"?keywords={keyword}"
                f"&location={location}"
                f"&f_TPR={time_filter}"
                f"&sortBy=DD"
                f"&start={start}"
            )
            if listing_type.get("f_JT"):
                url += f"&f_JT={listing_type['f_JT']}"
            if listing_type.get("f_E"):
                url += f"&f_E={listing_type['f_E']}"
            log.info(f"🔍 Page {page + 1} — {keyword} in {location}  ({start} offset)")
            driver.get(url)

            # Wait for at least one card to appear
            try:
                WebDriverWait(driver, config.PAGE_LOAD_WAIT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.base-card"))
                )
            except TimeoutException:
                log.warning("  No job cards found on this page — stopping pagination.")
                break

            # Bot / auth wall detection
            if _is_blocked(driver):
                log.error(
                    "🚫 LinkedIn has blocked this session (auth wall / CAPTCHA). "
                    "Try again later or reduce scroll speed."
                )
                break

            # Scroll to load all lazy cards on this page
            _scroll_to_load_all(driver)

            cards = driver.find_elements(By.CSS_SELECTOR, "div.base-card")
            log.info(f"📋 {len(cards)} cards on page {page + 1}")

            page_new = 0
            for card in cards:
                job = _parse_card(card)
                if job is None:
                    continue

                # Deduplicate by job ID
                jid = job.job_id
                if jid in seen_ids:
                    continue
                seen_ids.add(jid)

                if job.is_complete:
                    complete_jobs.append(job)
                else:
                    incomplete_jobs.append(job)
                page_new += 1

            log.info(f"  ✅ {page_new} new unique jobs from page {page + 1}")

            # Stop if this page had no new jobs (end of results)
            if page_new == 0:
                log.info("  No new jobs found — end of results.")
                break

            page += 1
            human_delay(2.0, 5.0)   # polite pause between pages

    except WebDriverException as exc:
        log.error(f"❌ WebDriver error: {exc}")
    finally:
        driver.quit()
        log.info("🔒 Browser closed.")

    log.info(f"✅ Complete jobs:    {len(complete_jobs)}")
    log.info(f"⚠️  Incomplete jobs:  {len(incomplete_jobs)}")
    return complete_jobs, incomplete_jobs
