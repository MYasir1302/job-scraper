# 🤖 LinkedIn Job Scraper

Scrapes LinkedIn job listings and saves them to Google Sheets — automatically, with deduplication, pagination, and optional notifications.

---

## 📁 Project Structure

```
linkedin_scraper/
├── main.py          ← Entry point (run this)
├── cli.py           ← Argument parsing + interactive prompts
├── scraper.py       ← Selenium scraping logic
├── sheets.py        ← Google Sheets read/write
├── notifier.py      ← Slack / email notifications (optional)
├── config.py        ← Config loader (reads .env)
├── utils.py         ← Logging, retry decorator, URL helpers
├── requirements.txt
├── .env.example     ← Copy to .env and fill in your values
└── .gitignore
```

---

## ⚡ Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up Google Sheets API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable **Google Sheets API** and **Google Drive API**
3. Create a **Service Account** → download the JSON key file
4. Open your Google Sheet → Share it with the service account email (`...@...iam.gserviceaccount.com`) as **Editor**

### 3. Configure `.env`

```bash
cp .env.example .env
```

Edit `.env`:

```env
CREDENTIALS_FILE=credentials.json   # path to your downloaded JSON key
SHEET_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms   # from your Sheet URL
```

### 4. Run it

```bash
# Interactive mode (menu-driven)
python main.py

# CLI mode (scriptable / cron-friendly)
python main.py -k "Data Scientist" -l "Remote" -t 1
```

---

## 🖥️ CLI Options

| Flag | Short | Description |
|------|-------|-------------|
| `--keyword` | `-k` | Job title to search |
| `--location` | `-l` | Location (preset name or custom) |
| `--time` | `-t` | `1`=24h · `2`=48h · `3`=1week |

**Location presets:** Pakistan, United States, United Kingdom, Canada, Australia, Remote

---

## 📊 Google Sheets Output

| Sheet | Contents |
|-------|----------|
| ✅ Complete Jobs | All fields present: title, company, location, link, date posted, work type, seniority |
| ⚠️ Incomplete Jobs | Have a link but missing one or more fields |
| 📈 Run Log | One row per run: timestamp, keyword, location, counts |

---

## 🔔 Optional Notifications

Add to your `.env`:

```env
# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz

# Email (Gmail)
NOTIFY_EMAIL=you@example.com
GMAIL_SENDER=yourbot@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

---

## ⏰ Scheduling (Cron)

Run automatically every day at 8 AM:

```bash
# crontab -e
0 8 * * * cd /path/to/linkedin_scraper && python main.py -k "Python Developer" -l "Pakistan" -t 1 >> logs/cron.log 2>&1
```

---

## ⚙️ Advanced Config (`.env`)

```env
SCROLL_CYCLES=6        # max scroll rounds per page
SCROLL_PAUSE=2.0       # seconds between scrolls
PAGE_LOAD_WAIT=5.0     # seconds to wait for first card
MAX_RETRIES=3          # retry attempts on failure
RETRY_DELAY=4.0        # base delay between retries (seconds)
```

---

## 🛡️ Security

- **Never commit `.env` or `credentials.json`** — both are in `.gitignore`
- Use a dedicated Google service account with minimum required permissions
- Rotate your service account key periodically

---

## 📝 Logs

All runs are logged to `logs/scraper.log` (rotated automatically) and printed to the console.
