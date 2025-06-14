import sqlite3

conn = sqlite3.connect("server/trends.db")
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

print("✅ trends table reset and all columns added.")

