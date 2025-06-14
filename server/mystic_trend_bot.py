import sqlite3
import time
from playwright.sync_api import sync_playwright
import openai
import os
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

DB_PATH = "trends.db"

# Generate an AI summary with detail and examples
def generate_summary(trend_name):
    prompt = (
        f"""
        You're a trend analyst AI. Create a detailed summary for the TikTok trend #{trend_name}.
        Include:
        - Why it's trending
        - Demographics involved
        - Related memes, sounds, or aesthetics
        - Realistic, made-up but plausible TikTok example captions or video concepts
        Keep it short, informative, and fun.
        """
    )

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=250
    )

    return response["choices"][0]["message"]["content"].strip()

# Save new trends to the database
def save_trends_to_db(trends, cursor, conn):
    for trend in trends:
        name = trend['name']
        score = trend.get('score', 0)
        stage = trend.get('stage', 'emerging')
        url = trend.get('url', '')
        summary = generate_summary(name)
        examples = [f"Example: {name} dance challenge", f"Caption: 'Can you top this? #{name}'"]

        cursor.execute("""
            INSERT INTO trends (name, score, stage, url, summary, examples)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, score, stage, url, summary, '\n'.join(examples)))

    conn.commit()

# Scrape TikTok Discover
def scrape_discover():
    print("🌐 Scraping TikTok Discover...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.tiktok.com/discover")
        page.wait_for_timeout(5000)

        elements = page.query_selector_all("a[href*='/tag/']")
        trends = []

        for el in elements[:7]:
            try:
                tag = el.get_attribute("href").split("/tag/")[-1].split("?")[0]
                name = tag.replace('-', ' ')
                trends.append({
                    "name": name,
                    "score": 60 + 10 * len(name),
                    "stage": "emerging",
                    "url": el.get_attribute("href")
                })
            except Exception as e:
                print("Skipping invalid element", e)

        browser.close()
        print(f"🔍 Found {len(trends)} trends.")
        return trends

# Run the bot
def run_bot():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    trends = scrape_discover()
    if trends:
        save_trends_to_db(trends, cursor, conn)
        print("✅ Trends saved.")
    else:
        print("⚠️ No trends found.")

    conn.close()

if __name__ == "__main__":
    run_bot()

