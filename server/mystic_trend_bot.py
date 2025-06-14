import os
import sqlite3
import time
from dotenv import load_dotenv
from openai import OpenAI
from playwright.sync_api import sync_playwright
from apscheduler.schedulers.blocking import BlockingScheduler

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

def scrape_tiktok_discover(headless=False):
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

            for _ in range(10):
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(2000)

            items = page.query_selector_all("a[href*='/tag/']")
            print(f"🔍 Found {len(items)} tag links.")

            for item in items:
                name = item.inner_text().strip().replace("#", "")
                url = item.get_attribute("href")
                views = item.query_selector("div[data-e2e='browse-video-views']")
                view_count = views.inner_text().strip() if views else None
                if name and name not in seen:
                    snippet, likes, comments = scrape_tag_snippet(page, url)
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

def scrape_tag_snippet(page, url):
    try:
        page.goto(url, timeout=10000)
        page.wait_for_timeout(3000)
        captions = page.locator("div[data-e2e='browse-video-desc']").all_inner_texts()
        likes = page.locator("strong[data-e2e='like-count']").first.inner_text(timeout=3000) or ""
        comments = page.locator("strong[data-e2e='comment-count']").first.inner_text(timeout=3000) or ""
        return " | ".join(captions[:3]) if captions else "No preview", likes, comments
    except Exception as e:
        print(f"⚠️ Snippet scrape error: {e}")
    return "No content preview available.", "", ""

def generate_summary_and_examples(trend_name, snippet):
    prompt = (
        f"You're an elite-level trend forecaster with an it-girl edge. The TikTok hashtag #{trend_name} is trending. "
        f"Here's a snippet from current posts: {snippet}\n\n"
        "Analyze in your signature voice: casually iconic, zillennial sarcasm meets timeless taste. "
        "Keep it smart, sharp, grounded, and a little savage. Say whether it's giving viral longevity or just a flash trend. "
        "Suggest 2–3 content ideas for creators to ride this wave before it crashes."
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

def save_trends_to_db(trends, cursor, conn):
    ensure_db_schema(cursor)
    for trend in trends:
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
                INSERT OR REPLACE INTO trends (name, summary, score, stage, examples, url, snippet, views, likes, comments)
                VALUES (:name, :summary, :score, :stage, :examples, :url, :snippet, :views, :likes, :comments)
            """, trend_data)
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
    scheduler = BlockingScheduler()
    scheduler.add_job(run_bot, 'interval', hours=1)
    print("🔁 Scheduler started. Scraping every hour.")
    run_bot()
    scheduler.start()

