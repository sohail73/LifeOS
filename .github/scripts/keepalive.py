"""
Opens the Streamlit app in a real headless browser (a plain HTTP ping does
NOT count as traffic) and clicks "Yes, get this app back up!" if the app
had already gone to sleep. Run by .github/workflows/keepalive.yml.
"""

import os
import sys

from playwright.sync_api import sync_playwright

APP_URL = os.environ.get("APP_URL", "").strip()
if not APP_URL:
    print("APP_URL is not set (add it as a GitHub repo secret).")
    sys.exit(1)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(APP_URL, wait_until="domcontentloaded", timeout=120_000)
    page.wait_for_timeout(8_000)

    wake = page.get_by_role("button", name="Yes, get this app back up!")
    if wake.count() > 0:
        print("App was asleep -- clicking the wake-up button.")
        wake.first.click()
        page.wait_for_timeout(90_000)  # give it time to boot (and restore the backup)
    else:
        print("App is awake.")
        page.wait_for_timeout(20_000)  # stay connected for a few seconds so it counts as a visit

    browser.close()
print("Done.")
