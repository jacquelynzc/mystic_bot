import sqlite3
import subprocess
import threading
import time

DB_PATH = "server/trends.db"

def setup_database():
    print("🛠️ Setting up database...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS trends")
    cursor.execute("""
        CREATE TABLE trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            score REAL,
            stage TEXT,
            summary TEXT,
            url TEXT,
            insight TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("✅ Database schema initialized.")


def seed_trends():
    print("🌱 Seeding sample trends...")
    sample_trends = [
        {
            "name": "Grunge Fashion Aesthetic",
            "score": 88.5,
            "stage": "Emerging",
            "summary": "90s grunge revival with a soft-glam twist.",
            "url": "https://www.tiktok.com/tag/grungeaesthetic",
            "insight": "Combines nostalgia with alt-girl TikTok resurgence."
        },
        {
            "name": "Jelly Makeup",
            "score": 91.2,
            "stage": "Hot",
            "summary": "Bouncy translucent blushes and highlighters trending.",
            "url": "https://www.tiktok.com/tag/jellymakeup",
            "insight": "Driven by beauty creators mixing K-beauty and Euphoria-style shimmer."
        },
        {
            "name": "Silent Walking",
            "score": 79.3,
            "stage": "Growing",
            "summary": "Going for walks without your phone or music to reduce stress.",
            "url": "https://www.tiktok.com/tag/silentwalking",
            "insight": "Mental health and minimalism meet wellness-core."
        }
    ]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for trend in sample_trends:
        cursor.execute("""
            INSERT INTO trends (name, score, stage, summary, url, insight)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            trend["name"],
            trend["score"],
            trend["stage"],
            trend["summary"],
            trend["url"],
            trend["insight"]
        ))
    conn.commit()
    conn.close()
    print("✅ Sample trends seeded.")


def run_api_server():
    print("🚀 Starting FastAPI backend...")
    subprocess.run(["uvicorn", "server.api_server:app", "--reload"])


# Optional: run bot after short delay (uncomment if desired)
def run_bot():
    print("🤖 Running trend bot...")
    subprocess.run(["python3", "server/mystic_trend_bot.py"])


if __name__ == "__main__":
    setup_database()
    seed_trends()

    # Optional: Launch backend and bot in parallel
    threading.Thread(target=run_api_server).start()
    time.sleep(2)  # Give the server a moment to boot
    threading.Thread(target=run_bot).start()

