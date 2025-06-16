import os
import sqlite3
import time
import shutil
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from playwright.sync_api import sync_playwright, TimeoutError
from apscheduler.schedulers.background import BackgroundScheduler

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

def clear_browser_cache(user_data_dir):
    cache_path = os.path.join(user_data_dir, "Default", "Cache")
    code_cache_path = os.path.join(user_data_dir, "Default", "Code Cache")
    for path in [cache_path, code_cache_path]:
        if os.path.exists(path):
            try:
                shutil.rmtree(path)
                print(f"🧹 Cleared browser cache: {path}")
            except Exception as e:
                print(f"⚠️ Failed to clear cache at {path}: {e}")

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
            comments TEXT,
            timestamp TEXT,
            leaderboard_rank INTEGER
        )
    """)
    for column, col_type in [
        ("examples", "TEXT"), ("url", "TEXT"), ("snippet", "TEXT"),
        ("views", "TEXT"), ("likes", "TEXT"), ("comments", "TEXT"),
        ("timestamp", "TEXT"), ("leaderboard_rank", "INTEGER")
    ]:
        try:
            cursor.execute(f"ALTER TABLE trends ADD COLUMN {column} {col_type}")
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
            comments TEXT,
            leaderboard_rank INTEGER
        )
    """)
    conn.commit()
    conn.close()

def scroll_until_loaded(page, target_count=100, max_scrolls=60, delay=1.05):
    for i in range(max_scrolls):
        page.mouse.wheel(0, 350)
        time.sleep(delay)
        try:
            card_count = page.locator("a.CardPc_container___oNb0").count()
            print(f"🌀 Scroll {i+1}/{max_scrolls} — Cards found: {card_count}")
            if card_count >= target_count:
                print("✅ Required number of trend cards loaded.")
                break
        except TimeoutError:
            print("⚠️ Timeout when counting cards. Retrying.")
            continue

def scrape_tiktok_creative_center():
    print(f"🌐 Scraping TikTok Creative Center... (persistent login, fresh cache)")
    trends = []
    try:
        clear_browser_cache(USER_DATA_DIR)
        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=False,
                executable_path=BRAVE_EXECUTABLE_PATH,
                args=["--disable-blink-features=AutomationControlled", "--start-maximized"]
            )
            page = context.new_page()
            print("🌍 Navigating to TikTok Creative Center...")
            page.goto(BASE_URL, timeout=60000)
            page.reload()
            page.wait_for_timeout(3000)

            print("🔄 Scrolling to load all trends...")
            scroll_until_loaded(page)

            cards = page.locator("a.CardPc_container___oNb0").all()
            print(f"🔍 Found {len(cards)} trend cards.")

            for idx, card in enumerate(cards):
                try:
                    title = card.locator(".CardPc_titleText__RYOWo").inner_text(timeout=3000).strip().replace("#", "")
                    views = card.locator(".CardPc_itemValue__XGDmG").nth(0).inner_text(timeout=3000).strip()
                    url = card.get_attribute("href")
                    full_url = f"https://ads.tiktok.com{url}" if url else ""
                    rank = card.locator(".RankingStatus_rankingIndex__ZMDrH").inner_text(timeout=3000).strip()

                    print(f"🔍 #{rank}: {title} — {views}")

                    trends.append({
                        "name": title,
                        "url": full_url,
                        "views": views,
                        "snippet": "",
                        "likes": "",
                        "comments": "",
                        "timestamp": datetime.utcnow().isoformat(),
                        "leaderboard_rank": int(rank) if rank.isdigit() else None
                    })
                except Exception as e:
                    print(f"⚠️ Error parsing trend card: {e}")

            page.close()
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
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a cultural trend analyst who thinks like a NYC creative director and talks like a laid-back LA it-girl. You decode viral trends with ease, always clocking what’s legit vs. cringe."},
                {"role": "user", "content": prompt},
            ]
        )
        return response.choices[0].message.content.strip(), []
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
    return "Niche"

def save_trends_to_db(trends, cursor, conn):
    ensure_db_schema(cursor)
    history_conn = sqlite3.connect(history_db_path)
    history_cursor = history_conn.cursor()
    ensure_history_schema()

    for trend in trends:
        score = score_trend(trend["name"])
        stage = determine_stage(score)

        cursor.execute("SELECT snippet FROM trends WHERE name = ?", (trend["name"],))
        existing = cursor.fetchone()
        is_unchanged = existing and existing[0] == trend.get("snippet")

        if is_unchanged:
            print(f"⏩ Skipping unchanged trend: {trend['name']}")
        else:
            summary, examples = generate_summary_and_examples(trend["name"], trend.get("snippet", ""))
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
                "comments": trend.get("comments"),
                "timestamp": trend.get("timestamp"),
                "leaderboard_rank": trend.get("leaderboard_rank")
            }

            try:
                cursor.execute("""
                    INSERT INTO trends (name, summary, score, stage, examples, url, snippet, views, likes, comments, timestamp, leaderboard_rank)
                    VALUES (:name, :summary, :score, :stage, :examples, :url, :snippet, :views, :likes, :comments, :timestamp, :leaderboard_rank)
                    ON CONFLICT(name) DO UPDATE SET
                        summary=excluded.summary,
                        score=excluded.score,
                        stage=excluded.stage,
                        examples=excluded.examples,
                        url=excluded.url,
                        snippet=excluded.snippet,
                        views=excluded.views,
                        likes=excluded.likes,
                        comments=excluded.comments,
                        timestamp=excluded.timestamp,
                        leaderboard_rank=excluded.leaderboard_rank
                """, trend_data)
                print(f"✅ Saved trend: {trend['name']}")
            except sqlite3.OperationalError as e:
                print(f"❌ DB Error for trend '{trend['name']}': {e}")

        history_cursor.execute("""
            INSERT INTO trend_history (name, timestamp, score, stage, views, likes, comments, leaderboard_rank)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trend["name"], trend["timestamp"], score, stage,
            trend.get("views"), trend.get("likes"),
            trend.get("comments"), trend.get("leaderboard_rank")
        ))

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
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_bot, 'interval', minutes=30)
    print("🔁 Scheduler started. Scraping every 30 minutes.")
    scheduler.start()

