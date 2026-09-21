from playwright.sync_api import sync_playwright


def open_page(url: str):
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto(url, wait_until="domcontentloaded")

    return playwright, browser, page
