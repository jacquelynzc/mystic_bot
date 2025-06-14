import os
import sqlite3
import time
from dotenv import load_dotenv
from openai import OpenAI
from playwright.sync_api import sync_playwright

# Load environment variables
load_dotenv()

# Constants
db_path = os.path.join(os.path.dirname(__file__), "trends.db")
openai_api_key = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=openai_api_key)

def ensure_db_schema(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            summary TEXT,
            score INTEGER,
            stage TEXT,
            examples TEXT,
            url TEXT
        )
    """)
    # Ensure new columns exist
    for column in ["examples", "url"]:
        try:
            cursor.execute(f"ALTER TABLE trends ADD COLUMN {column} TEXT")
        except sqlite3.OperationalError:
            pass  # Already exists

def scrape_tiktok_discover(headless=True):
    print(f"\U0001F310 Scraping TikTok Discover... (headless={headless})")
    trends = []
    seen = set()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()
            page.goto("https://www.tiktok.com/discover", timeout=15000)
            print("⌛ Waiting for page to load...")
            page.wait_for_timeout(5000)

            scrolls = 5
            for _ in range(scrolls):
                page.mouse.wheel(0, 1000)
                page.wait_for_timeout(2000)

            items = page.query_selector_all("a[href*='/tag/']")
            print(f"🔍 Found {len(items)} tag links.")

            for item in items:
                name = item.inner_text().strip().replace("#", "")
                url = item.get_attribute("href")
                if name and name not in seen:
                    trends.append({"name": name, "url": url})
                    seen.add(name)
                if len(trends) >= 50:
                    break

            browser.close()
    except Exception as e:
        print(f"❌ Browser scraping error: {e}")
    print(f"✅ Scraped {len(trends)} trend(s).")
    return trends

def generate_summary_and_examples(trend_name):
    prompt = (
        f"Give a detailed analysis of the trending TikTok hashtag #{trend_name}. "
        f"Describe what it’s about, why it’s trending, who’s using it, and include 2–3 example video concepts someone could make to participate."
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a social media analyst and trend forecaster."},
                {"role": "user", "content": prompt},
            ]
        )
        full_text = response.choices[0].message.content.strip()
        parts = full_text.split("\n")
        summary = parts[0]
        examples = [line.strip("-• ") for line in parts[1:] if line.strip()]
        return summary, examples[:3]
    except Exception as e:
        print(f"⚠️ OpenAI API error: {e}")
        return "Summary unavailable.", []

def score_trend(trend_name):
    return len(trend_name) * 7 % 100

def determine_stage(score):
    if score > 75:
        return "Exploding"
    elif score > 50:
        return "Rising"
    elif score > 25:
        return "Early"
    else:
        return "Niche"

def save_trends_to_db(trends, cursor, conn):
    ensure_db_schema(cursor)
    for trend in trends:
        summary, examples = generate_summary_and_examples(trend["name"])
        score = score_trend(trend["name"])
        stage = determine_stage(score)

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO trends (name, summary, score, stage, examples, url)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (trend["name"], summary, score, stage, str(examples), trend.get("url")))
            print(f"✅ Saved trend: {trend['name']}")
        except sqlite3.OperationalError as e:
            print(f"❌ DB Error for trend '{trend['name']}': {e}")

    conn.commit()

def run_bot():
    trends = scrape_tiktok_discover(headless=False)
    if not trends:
        print("⚠️ No trends found. Exiting.")
        return

    print("💾 Saving to local database...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    save_trends_to_db(trends, cursor, conn)
    conn.close()
    print("✅ All done!")

if __name__ == "__main__":
    run_bot()

