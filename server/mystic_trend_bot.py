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

BASE_URL = "https://www.tiktok.com"


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


def scrape_tiktok_discover(headless=False):
    print(f"\U0001F310 Scraping TikTok Discover... (headless={headless})")
    trends = []
    seen = set()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()
            page.goto(f"{BASE_URL}/discover", timeout=15000)
            print("⌛ Waiting for page to load...")
            page.wait_for_timeout(5000)

            for _ in range(15):
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(2000)

            items = page.query_selector_all("a[href*='/tag/']")
            print(f"🔍 Found {len(items)} tag links.")

            for item in items:
                name = item.inner_text().strip().replace("#", "")
                href = item.get_attribute("href")
                url = href if href.startswith("http") else f"{BASE_URL}{href}"
                views = item.query_selector("div[data-e2e='browse-video-views']")
                view_count = views.inner_text().strip() if views else None
                if name and name not in seen:
                    snippet, likes, comments = scrape_tag_snippet(browser, url)
                    trends.append({
                        "name": name,
                        "url": url,
                        "snippet": snippet,
                        "views": view_count,
                        "likes": likes,
                        "comments": comments
                    })
                    seen.add(name)
                if len(trends) >= 50:
                    break

            browser.close()
    except Exception as e:
        print(f"❌ Browser scraping error: {e}")
    print(f"✅ Scraped {len(trends)} trend(s).")
    return trends


def scrape_tag_snippet(browser, url):
    try:
        tag_page = browser.new_page()
        tag_page.goto(url, timeout=15000)
        tag_page.wait_for_timeout(4000)

        captions = tag_page.locator("div[data-e2e='browse-video-desc']").all_inner_texts()
        try:
            likes = tag_page.locator("strong[data-e2e='like-count']").first.inner_text(timeout=5000)
        except Exception:
            likes = "N/A"

        try:
            comments = tag_page.locator("strong[data-e2e='comment-count']").first.inner_text(timeout=5000)
        except Exception:
            comments = "N/A"

        tag_page.close()
        return " | ".join(captions[:3]) if captions else "No preview", likes, comments
    except Exception as e:
        print(f"⚠️ Snippet scrape error: {e}")
    return "No content preview available.", "", ""


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
    trends = scrape_tiktok_discover(headless=False)
    if not trends:
        print("⚠️ No trends found. Exiting.")
        return

    print("💾 Saving to local database...")
    con
