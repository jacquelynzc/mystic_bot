import os
import sqlite3
import time
from dotenv import load_dotenv
from openai import OpenAI
from playwright.sync_api import sync_playwright
from apscheduler.schedulers.blocking import BlockingScheduler
import requests

# Load environment variables
load_dotenv()

# Constants
db_path = os.path.join(os.path.dirname(__file__), "trends.db")
openai_api_key = os.getenv("OPENAI_API_KEY")
notion_token = os.getenv("NOTION_API_KEY")
notion_db_id = os.getenv("NOTION_DATABASE_ID")

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
    for column in ["examples", "url"]:
        try:
            cursor.execute(f"ALTER TABLE trends ADD COLUMN {column} TEXT")
        except sqlite3.OperationalError:
            pass

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

            for _ in range(5):
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
        f"You are an elite-level trend forecaster with an it-girl edge. Analyze the TikTok hashtag #{trend_name} in your signature voice: casual but razor-sharp, zillennial sarcasm meets grounded taste. Keep it real, mock trends when deserved (never cruel), and explain why it's gaining traction. Highlight if it's a flash-in-the-pan or has real staying power. Give 2–3 creative video ideas for creators to hop on in a way that feels relevant and fresh."
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a cultural critic and social media trend forecaster with a grounded, witty, effortlessly cool voice."},
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

def post_to_notion(trend):
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    data = {
        "parent": {"database_id": notion_db_id},
        "properties": {
            "Name": {"title": [{"text": {"content": trend['name']}}]},
            "Summary": {"rich_text": [{"text": {"content": trend['summary']}}]},
            "Score": {"number": trend['score']},
            "Stage": {"select": {"name": trend['stage']}}
        }
    }
    try:
        response = requests.post("https://api.notion.com/v1/pages", headers=headers, json=data)
        response.raise_for_status()
        print(f"✅ Posted to Notion: {trend['name']}")
    except Exception as e:
        print(f"❌ Notion post failed: {e}")

def save_trends_to_db(trends, cursor, conn):
    ensure_db_schema(cursor)
    for trend in trends:
        summary, examples = generate_summary_and_examples(trend["name"])
        score = score_trend(trend["name"])
        stage = determine_stage(score)

        trend_data = {
            "name": trend["name"],
            "summary": summary,
            "score": score,
            "stage": stage,
            "examples": str(examples),
            "url": trend.get("url")
        }

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO trends (name, summary, score, stage, examples, url)
                VALUES (:name, :summary, :score, :stage, :examples, :url)
            """, trend_data)
            print(f"✅ Saved trend: {trend['name']}")
            post_to_notion(trend_data)
        except sqlite3.OperationalError as e:
            print(f"❌ DB Error for trend '{trend['name']}': {e}")

    conn.commit()

def run_bot():
    trends = scrape_tiktok_discover(headless=True)
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
    scheduler = BlockingScheduler()
    scheduler.add_job(run_bot, 'interval', hours=1)
    print("🔁 Scheduler started. Scraping every hour.")
    run_bot()
    scheduler.start()

