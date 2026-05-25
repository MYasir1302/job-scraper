import sys
sys.stdout.reconfigure(encoding='utf-8')

import time
import gspread
from google.oauth2.service_account import Credentials
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime

# ============================================
#         YOUR SETTINGS — EDIT THESE
# ============================================
CREDENTIALS_FILE = "Paste_Your_.JSON"
SHEET_ID         = "Paste_Your_Sheet_ID"
# ============================================


def get_user_input():
    print("=" * 50)
    print("   🤖 LinkedIn Job Scraper Bot")
    print("=" * 50)

    print("\n📌 Select Job Location:")
    print("  1. Pakistan")
    print("  2. United States")
    print("  3. United Kingdom")
    print("  4. Canada")
    print("  5. Australia")
    print("  6. Remote")
    print("  7. Custom (type your own)")

    location_choice = input("\nEnter number (1-7): ").strip()
    locations = {
        "1": "Pakistan", "2": "United States", "3": "United Kingdom",
        "4": "Canada",   "5": "Australia",     "6": "Remote",
    }
    if location_choice in locations:
        location = locations[location_choice]
    elif location_choice == "7":
        location = input("Enter your custom location: ").strip()
    else:
        print("⚠️ Invalid choice, defaulting to Pakistan")
        location = "Pakistan"

    print("\n💼 Select Job Type:")
    print("  1. Python Developer")
    print("  2. Web Developer")
    print("  3. Data Scientist")
    print("  4. Machine Learning Engineer")
    print("  5. Frontend Developer")
    print("  6. Backend Developer")
    print("  7. Full Stack Developer")
    print("  8. DevOps Engineer")
    print("  9. Custom (type your own)")

    job_choice = input("\nEnter number (1-9): ").strip()
    job_types = {
        "1": "Python Developer",       "2": "Web Developer",
        "3": "Data Scientist",         "4": "Machine Learning Engineer",
        "5": "Frontend Developer",     "6": "Backend Developer",
        "7": "Full Stack Developer",   "8": "DevOps Engineer",
    }
    if job_choice in job_types:
        keyword = job_types[job_choice]
    elif job_choice == "9":
        keyword = input("Enter your custom job type: ").strip()
    else:
        print("⚠️ Invalid choice, defaulting to Python Developer")
        keyword = "Python Developer"

    print("\n⏰ Select Time Filter:")
    print("  1. Last 24 hours")
    print("  2. Last 48 hours")
    print("  3. Last week")

    time_choice = input("\nEnter number (1-3): ").strip()
    time_filters = {"1": "r86400", "2": "r172800", "3": "r604800"}
    time_filter  = time_filters.get(time_choice, "r86400")

    print(f"\n✅ Searching for: {keyword} in {location}")
    print("=" * 50)
    return keyword, location, time_filter


def get_google_sheets():
    print("📊 Connecting to Google Sheets...")
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds  = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    sheet  = client.open_by_key(SHEET_ID)

    # ── Sheet 1: Complete Jobs ──
    worksheet1 = sheet.get_worksheet(0)
    worksheet1.update_title("✅ Complete Jobs")
    existing1 = worksheet1.get_all_values()
    if not existing1:
        worksheet1.append_row(["Title", "Company", "Location", "Link", "Scraped At"])

    # ── Sheet 2: Incomplete Jobs ──
    try:
        worksheet2 = sheet.get_worksheet(1)
        worksheet2.update_title("⚠️ Incomplete Jobs")
    except:
        worksheet2 = sheet.add_worksheet(title="⚠️ Incomplete Jobs", rows="1000", cols="10")

    existing2 = worksheet2.get_all_values()
    if not existing2:
        worksheet2.append_row(["Title", "Company", "Location", "Link", "Scraped At"])

    print("✅ Connected to both sheets!")
    print(f"🔗 Link: https://docs.google.com/spreadsheets/d/{SHEET_ID}")
    return worksheet1, worksheet2


def scrape_linkedin_jobs(keyword, location, time_filter):
    print("🚀 Starting browser...")
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    url = f"https://www.linkedin.com/jobs/search/?keywords={keyword}&location={location}&f_TPR={time_filter}&sortBy=DD"
    print(f"🔍 Searching: {keyword} in {location}")
    driver.get(url)
    time.sleep(5)

    for _ in range(3):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    complete_jobs   = []
    incomplete_jobs = []

    try:
        job_cards = driver.find_elements(By.CSS_SELECTOR, "div.base-card")
        print(f"📋 Total cards found: {len(job_cards)}")

        for card in job_cards:
            try:
                # Get title
                try:
                    title = card.find_element(By.CSS_SELECTOR, "h3.base-search-card__title").text.strip()
                except:
                    try:
                        title = card.find_element(By.CSS_SELECTOR, "h3").text.strip()
                    except:
                        title = ""

                # Get company
                try:
                    company = card.find_element(By.CSS_SELECTOR, "h4.base-search-card__subtitle").text.strip()
                except:
                    try:
                        company = card.find_element(By.CSS_SELECTOR, "a.hidden-nested-link").text.strip()
                    except:
                        company = ""

                # Get location
                try:
                    loc = card.find_element(By.CSS_SELECTOR, "span.job-search-card__location").text.strip()
                except:
                    try:
                        loc = card.find_element(By.CSS_SELECTOR, "[class*='location']").text.strip()
                    except:
                        loc = ""

                # Get link
                try:
                    link = card.find_element(By.CSS_SELECTOR, "a.base-card__full-link").get_attribute("href")
                except:
                    try:
                        link = card.find_element(By.TAG_NAME, "a").get_attribute("href")
                    except:
                        link = ""

                scraped_at = datetime.now().strftime("%Y-%m-%d %H:%M")

                # ✅ Complete — all fields present
                if title and company and loc and link:
                    complete_jobs.append([title, company, loc, link, scraped_at])

                # ⚠️ Incomplete — at least has a link
                elif link:
                    incomplete_jobs.append([
                        title   or "N/A",
                        company or "N/A",
                        loc     or "N/A",
                        link,
                        scraped_at
                    ])

            except:
                continue

    except Exception as e:
        print(f"❌ Error scraping: {e}")
    finally:
        driver.quit()

    print(f"✅ Complete jobs:   {len(complete_jobs)}")
    print(f"⚠️ Incomplete jobs: {len(incomplete_jobs)}")
    return complete_jobs, incomplete_jobs


def save_to_sheet(worksheet, jobs, sheet_name="Sheet"):
    if not jobs:
        print(f"⚠️ No jobs to save in {sheet_name}.")
        return

    print(f"💾 Saving {len(jobs)} jobs to {sheet_name}...")
    existing_data  = worksheet.get_all_values()
    existing_links = [row[3] for row in existing_data[1:] if len(row) > 3]

    new_jobs = 0
    skipped  = 0
    for job in jobs:
        if job[3] not in existing_links:
            worksheet.append_row(job)
            existing_links.append(job[3])
            new_jobs += 1
            time.sleep(0.5)
        else:
            skipped += 1

    print(f"✅ {new_jobs} new jobs saved in {sheet_name}! ({skipped} duplicates skipped)")


# ── Run it ──
if __name__ == "__main__":
    keyword, location, time_filter    = get_user_input()
    worksheet1, worksheet2            = get_google_sheets()
    complete_jobs, incomplete_jobs    = scrape_linkedin_jobs(keyword, location, time_filter)
    save_to_sheet(worksheet1, complete_jobs,   "✅ Complete Jobs")
    save_to_sheet(worksheet2, incomplete_jobs, "⚠️ Incomplete Jobs")

    print("\n" + "=" * 50)
    print("🎉 Done! Check your Google Sheet:")
    print(f"🔗 https://docs.google.com/spreadsheets/d/{SHEET_ID}")
    print("=" * 50)