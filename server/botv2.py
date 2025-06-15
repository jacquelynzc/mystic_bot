import os
import sqlite3
import time
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from playwright.sync_api import sync_playwright
from apscheduler.schedulers.blocking import BlockingScheduler

# Load environment variables
load_dotenv()

# Constants
db_path = os.path.join(os.path.dirname(__file__), "trends.db")
history_db_path = os.path.join(os.path.dirname(__file__), "trend_history.db")
openai_api_key = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=openai_api_key)

BASE_URL = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en"
BRAVE_EXECUTABLE_PATH = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
USER_DATA_DIR = "/tmp/mystic_brave_profile"

def ensure_db_schema(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            summary TEXT,
            score INTEGER,
            stage TEXT,
            examples TEXT,
            url TEXT,
            snippet TEXT,
            views TEXT,
            likes TEXT,
            comments TEXT
        )
    """)
    for column in ["examples", "url", "snippet", "views", "likes", "comments"]:
        try:
            cursor.execute(f"ALTER TABLE trends ADD COLUMN {column} TEXT")
        except sqlite3.OperationalError:
            pass

def ensure_history_schema():
    conn = sqlite3.connect(history_db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trend_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            timestamp TEXT,
            score INTEGER,
            stage TEXT,
            views TEXT,
            likes TEXT,
            comments TEXT
        )
    """)
    conn.commit()
    conn.close()

def scrape_tiktok_creative_center():
    print(f"\U0001F310 Scraping TikTok Creative Center... (headless=False)")
    trends = []
    try:
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=False,
                executable_path=BRAVE_EXECUTABLE_PATH,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized"
                ]
            )
            page = context.new_page()
            page.goto(BASE_URL, timeout=60000)
            print("⌛ Waiting for page to load...")
            page.wait_for_timeout(8000)

            # Aggressive scroll to simulate user behavior
            for _ in range(20):
                page.mouse.wheel(0, 2000)
                time.sleep(1.5)

            # Save HTML for debug
            with open("debug_output.html", "w", encoding="utf-8") as f:
                f.write(page.content())

            # Get all hashtag cards based on updated selectors
            cards = page.locator("#hashtagItemContainer div[class*=CardPc_detail]").all()
            print(f"🔍 Found {len(cards)} trend cards.")

            for card in cards:
                try:
                    title = card.locator("h3").inner_text().strip()
                    views = card.locator(".CardPc_number__1l4Z1").first.inner_text().strip()
                    url = card.locator("a").first.get_attribute("href")
                    full_url = f"https://ads.tiktok.com{url}" if url else ""

                    trends.append({
                        "name": title.replace("#", ""),
                        "url": full_url,
                        "views": views,
                        "snippet": "",
                        "likes": "",
                        "comments": ""
                    })
                except Exception as e:
                    print(f"⚠️ Error parsing trend card: {e}")

            context.close()

    except Exception as e:
        print(f"❌ Browser scraping error: {e}")

    print(f"✅ Scraped {len(trends)} trend(s).")
    return trends

def generate_summary_and_examples(trend_name, snippet):
    prompt = (
        f"You're a sharp, slightly elitist trend-savvy cultural critic with Gen Z wit and NYC edge. "
        f"TikTok's #{trend_name} is trending. Here's a sample of the content: {snippet}\n\n"
        "Give me a short, smart summary of the trend in 2-3 sentences—make it human, sarcastic (but not cheesy), and insightful. "
        "Skip suggestions. Don't be a cheerleader. You’re not trying to be cool—you just are. Assume the reader knows TikTok but isn’t drinking the Kool-Aid. Avoid disclaimers about being an AI."
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a cultural trend analyst who thinks like a NYC creative director and talks like a laid-back LA it-girl. You decode viral trends with ease, always clocking what’s legit vs. cringe."},
                {"role": "user", "content": prompt},
            ]
        )
        full_text = response.choices[0].message.content.strip()
        return full_text, []
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
    history_conn = sqlite3.connect(history_db_path)
    history_cursor = history_conn.cursor()
    ensure_history_schema()

    for trend in trends:
        cursor.execute("SELECT snippet FROM trends WHERE name = ?", (trend["name"],))
        existing = cursor.fetchone()
        if existing and existing[0] == trend.get("snippet"):
            print(f"⏩ Skipping unchanged trend: {trend['name']}")
            continue

        summary, examples = generate_summary_and_examples(trend["name"], trend.get("snippet", ""))
        score = score_trend(trend["name"])
        stage = determine_stage(score)

        trend_data = {
            "name": trend["name"],
            "summary": summary,
            "score": score,
            "stage": stage,
            "examples": str(examples),
            "url": trend.get("url"),
            "snippet": trend.get("snippet"),
            "views": trend.get("views"),
            "likes": trend.get("likes"),
            "comments": trend.get("comments")
        }

        try:
            cursor.execute("""
                INSERT INTO trends (name, summary, score, stage, examples, url, snippet, views, likes, comments)
                VALUES (:name, :summary, :score, :stage, :examples, :url, :snippet, :views, :likes, :comments)
                ON CONFLICT(name) DO UPDATE SET
                    summary=excluded.summary,
                    score=excluded.score,
                    stage=excluded.stage,
                    examples=excluded.examples,
                    url=excluded.url,
                    snippet=excluded.snippet,
                    views=excluded.views,
                    likes=excluded.likes,
                    comments=excluded.comments
            """, trend_data)
            print(f"✅ Saved trend: {trend['name']}")

            history_cursor.execute("""
                INSERT INTO trend_history (name, timestamp, score, stage, views, likes, comments)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                trend["name"], datetime.utcnow().isoformat(), score, stage, trend.get("views"), trend.get("likes"), trend.get("comments")
            ))

        except sqlite3.OperationalError as e:
            print(f"❌ DB Error for trend '{trend['name']}': {e}")

    conn.commit()
    history_conn.commit()
    history_conn.close()

def run_bot():
    trends = scrape_tiktok_creative_center()
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
    scheduler = BlockingScheduler()
    scheduler.add_job(run_bot, 'interval', hours=1)
    print("🔁 Scheduler started. Scraping every hour.")
    scheduler.start()

