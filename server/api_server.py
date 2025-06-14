from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sqlite3

app = FastAPI()

# CORS so your frontend can access it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fetch data from the local SQLite DB
def fetch_trends_from_db():
    try:
        conn = sqlite3.connect("trends.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name, score, stage, summary, url FROM trends")
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "name": row[0],
                "score": row[1],
                "stage": row[2],
                "summary": row[3],
                "url": row[4],
            }
            for row in rows
        ]
    except Exception as e:
        print("DB fetch error:", e)
        return []

@app.get("/trends")
def get_trends():
    return fetch_trends_from_db()

