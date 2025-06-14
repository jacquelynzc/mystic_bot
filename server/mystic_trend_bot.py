import sqlite3
from datetime import datetime


def init_db():
    """Initialize the SQLite database and create the trends table."""
    conn = sqlite3.connect("trends.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            score INTEGER,
            insight TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn, cursor


def save_trends_to_db(trends, cursor, conn):
    """Save a list of trend dictionaries to the database."""
    for trend in trends:
        cursor.execute("""
            INSERT INTO trends (name, score, insight) VALUES (?, ?, ?)
        """, (trend["name"], trend["score"], trend["insight"]))
    conn.commit()


def get_tiktok_trends():
    """TEMP: Return a hardcoded list of trends. Replace with scraper later."""
    return [
        {"name": "Mob Wife Summer", "score": 92, "insight": "Backlash to minimalism—drama is desirable again."},
        {"name": "Jellyfish Haircut", "score": 77, "insight": "Wispy, layered bob with ethereal movement."},
        {"name": "Lazy Girl Job", "score": 88, "insight": "Soft work, big pay. Chill career aesthetics."}
    ]


def run_bot():
    """Main function to run the trend bot."""
    print("🌐 Loading sample trends...")
    trends = get_tiktok_trends()

    print("💾 Saving to local database...")
    conn, cursor = init_db()
    save_trends_to_db(trends, cursor, conn)
    conn.close()
    print("✅ All done!")


if __name__ == "__main__":
    run_bot()

