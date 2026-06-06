"""
notifier.py — Optional run-complete notifications.

Supports:
  - Slack  (via incoming webhook URL)
  - Email  (via smtplib / Gmail app password)

Both are opt-in; if the relevant config values are empty the
notifier silently does nothing.
"""

import json
import smtplib
import urllib.request
from email.mime.text import MIMEText

import config
from utils import log


# ── Slack ─────────────────────────────────────────────────────────────────────

def notify_slack(
    keyword: str,
    location: str,
    complete: int,
    incomplete: int,
    new_total: int,
) -> None:
    """Send a Slack notification if SLACK_WEBHOOK_URL is configured."""
    if not config.SLACK_WEBHOOK_URL:
        return

    text = (
        f"*LinkedIn Job Scraper — Run Complete* ✅\n"
        f">*Search:*  {keyword} in {location}\n"
        f">*Complete jobs:*   {complete}\n"
        f">*Incomplete jobs:* {incomplete}\n"
        f">*New rows saved:*  {new_total}\n"
        f">🔗 <https://docs.google.com/spreadsheets/d/{config.SHEET_ID}|Open Sheet>"
    )

    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        config.SLACK_WEBHOOK_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                log.info("📣 Slack notification sent.")
            else:
                log.warning(f"Slack notification returned status {resp.status}")
    except Exception as exc:
        log.warning(f"Slack notification failed: {exc}")


# ── Email (Gmail) ─────────────────────────────────────────────────────────────

def notify_email(
    keyword: str,
    location: str,
    complete: int,
    incomplete: int,
    new_total: int,
) -> None:
    """
    Send an email summary if NOTIFY_EMAIL + GMAIL_APP_PASSWORD are set.

    Required extra env vars (add to .env):
        GMAIL_SENDER=your_address@gmail.com
        GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx   # Google App Password
    """
    import os
    sender   = os.getenv("GMAIL_SENDER", "").strip()
    password = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    recipient = config.NOTIFY_EMAIL

    if not (sender and password and recipient):
        return

    subject = f"[LinkedIn Scraper] {new_total} new jobs — {keyword} in {location}"
    body = (
        f"LinkedIn Job Scraper run complete.\n\n"
        f"Search:          {keyword} in {location}\n"
        f"Complete jobs:   {complete}\n"
        f"Incomplete jobs: {incomplete}\n"
        f"New rows saved:  {new_total}\n\n"
        f"View your sheet:\n"
        f"https://docs.google.com/spreadsheets/d/{config.SHEET_ID}\n"
    )

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = recipient

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender, password)
            smtp.sendmail(sender, recipient, msg.as_string())
        log.info(f"📧 Email notification sent to {recipient}.")
    except Exception as exc:
        log.warning(f"Email notification failed: {exc}")


# ── Unified notify ────────────────────────────────────────────────────────────

def notify_all(
    keyword: str,
    location: str,
    complete: int,
    incomplete: int,
    new_total: int,
) -> None:
    """Fire all configured notification channels."""
    notify_slack(keyword, location, complete, incomplete, new_total)
    notify_email(keyword, location, complete, incomplete, new_total)
