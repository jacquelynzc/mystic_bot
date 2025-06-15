# auth_cookies.py
import json
from playwright.sync_api import sync_playwright

COOKIES_FILE = "cookies.txt"
TARGET_URL = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en"


def load_cookies_from_txt(context):
    with open(COOKIES_FILE, 'r') as f:
        cookies_raw = f.read()
    cookies_dict = json.loads(cookies_raw.split('= ', 1)[-1])
    cookie_list = []
    for name, value in cookies_dict.items():
        cookie_list.append({"name": name, "value": value, "domain": ".tiktok.com", "path": "/"})
    context.add_cookies(cookie_list)


def launch_browser_with_cookies():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, executable_path="/Applications/Brave Browser.app/Contents/MacOS/Brave Browser")
        context = browser.new_context()
        page = context.new_page()

        print("🌐 Loading TikTok Creative Center with cookies...")
        load_cookies_from_txt(context)

        page.goto(TARGET_URL)
        page.wait_for_timeout(10000)

        print("✅ Page loaded with cookies. You should be authenticated if cookies are valid.")
        input("Press Enter to close the browser...")
        browser.close()


if __name__ == '__main__':
    launch_browser_with_cookies()

