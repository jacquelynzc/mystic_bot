import sqlite3

sample_trends = [
    {
        "name": "Lana Del Rey AI Covers",
        "score": 93,
        "stage": "Exploding",
        "summary": "AI-generated Lana covers are going viral across TikTok and YouTube Shorts.",
        "url": "https://tiktok.com/tag/lanaai"
    },
    {
        "name": "Siren Eyes Makeup",
        "score": 78,
        "stage": "Trending",
        "summary": "The 'Siren Eyes' look is making a huge comeback with bold eyeliner tutorials.",
        "url": "https://tiktok.com/tag/sireneyes"
    },
    {
        "name": "Corecore Edits",
        "score": 65,
        "stage": "Early",
        "summary": "Moody, melancholic Corecore montages are gaining steam with Gen Z.",
        "url": "https://tiktok.com/tag/corecore"
    }
]

def seed_database():
    conn = sqlite3.connect("trends.db")
    cursor = conn.cursor()

    # Create the table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trends (
            name TEXT,
            score INTEGER,
            stage TEXT,
            summary TEXT,
            url TEXT
        )
    """)

    # Clear old data
    cursor.execute("DELETE FROM trends")

    # Insert sample data
    for trend in sample_trends:
        cursor.execute("""
            INSERT INTO trends (name, score, stage, summary, url)
            VALUES (?, ?, ?, ?, ?)
        """, (trend["name"], trend["score"], trend["stage"], trend["summary"], trend["url"]))

    conn.commit()
    conn.close()
    print("✅ Seeded trends.db with sample data.")

if __name__ == "__main__":
    seed_database()

