import os
import sqlite3
import time
import shutil
import httpx
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from apscheduler.schedulers.background import BackgroundScheduler

# Load environment variables
load_dotenv()

# Constants
db_path = os.path.join(os.path.dirname(__file__), "trends.db")
history_db_path = os.path.join(os.path.dirname(__file__), "trend_history.db")
openai_api_key = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=openai_api_key)

TIKTOK_SUGGEST_API = "https://www.tiktok.com/api/search/general/full/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/115.0.0.0 Safari/537.36",
    "Referer": "https://www.tiktok.com/",
}

TREND_SEEDS = ["trending", "viral", "challenge", "meme", "fashion", "music"]


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


def scrape_tiktok_trends():
    print("\U0001F4E1 GPT Agent: Scraping TikTok Search Suggestions")
    trends = []

    for seed in TREND_SEEDS:
        try:
            resp = httpx.get(
                TIKTOK_SUGGEST_API,
                params={"keyword": seed, "from_page": "search", "region": "US"},
                headers=HEADERS,
                timeout=10
            )
            suggestions = resp.json().get("data", {}).get("suggests", [])
            for s in suggestions:
                tag = s.get("keyword")
                if tag and tag.startswith("#"):
                    trend_name = tag[1:]
                    trends.append({
                        "name": trend_name,
                        "url": f"https://www.tiktok.com/tag/{trend_name}",
                        "views": s.get("extra", {}).get("view_count", ""),
                        "snippet": s.get("desc", ""),
                        "likes": "",
                        "comments": "",
                        "timestamp": datetime.utcnow().isoformat(),
                        "leaderboard_rank": None
                    })
        except Exception as e:
            print(f"⚠️ Error fetching suggestions for '{seed}': {e}")

    print(f"✅ Fetched {len(trends)} suggested trends")
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

        cursor.execute("SELECT summary FROM trends WHERE name = ?", (trend["name"],))
        existing = cursor.fetchone()
        summary_already_generated = existing and existing[0] and existing[0] != "Summary unavailable."

        if summary_already_generated:
            summary, examples = existing[0], []
            print(f"⏭️ Already summarized: {trend['name']}")
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
    trends = scrape_tiktok_trends()
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

