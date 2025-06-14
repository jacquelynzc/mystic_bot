import sqlite3

def initialize_database():
    conn = sqlite3.connect("trends.db")
    cursor = conn.cursor()

    # Drop table if you want a clean reset (optional)
    # cursor.execute("DROP TABLE IF EXISTS trends")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trends (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        score INTEGER,
        stage TEXT,
        summary TEXT,
        examples TEXT,  -- stored as a JSON string
        url TEXT
    )
    """)

    conn.commit()
    conn.close()
    print("✅ Database schema initialized.")

if __name__ == "__main__":
    initialize_database()

