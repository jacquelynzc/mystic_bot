from playwright.sync_api import sync_playwright

BRAVE_EXECUTABLE_PATH = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
USER_DATA_DIR = "/tmp/mystic_brave_profile"
BASE_URL = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en"

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=USER_DATA_DIR,
        headless=False,
        executable_path=BRAVE_EXECUTABLE_PATH,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--start-maximized"
        ]
    )
    page = context.new_page()
    page.goto(BASE_URL)
    print("🧠 Log in manually, then close the browser to save the session.")
    input("Press ENTER here after logging in and verifying the page loaded.")
    context.close()

