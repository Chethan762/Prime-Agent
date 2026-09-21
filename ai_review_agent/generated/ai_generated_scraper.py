"""Generated Playwright scraper for https://www.web-scraping.dev/reviews"""

import json
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = "https://www.web-scraping.dev/reviews"
OUTPUT_FILE = "reviews.json"

# Selectors
REVIEW_CONTAINER = "#latest-reviews .review"
DATE_SELECTOR = "[data-testid='review-date']"
STARS_SELECTOR = "[data-testid='review-stars'] svg"
TEXT_SELECTOR = "[data-testid='review-text']"
LOAD_MORE_SELECTOR = "button:has-text('Load More')"


def count_stars(element):
    """Return integer star count based on number of SVG elements.
    """
    return len(element.locator(STARS_SELECTOR).all())


def scrape_page(page):
    reviews = []
    # Wait for reviews container to load
    page.wait_for_selector(REVIEW_CONTAINER, timeout=12000)
    elements = page.locator(REVIEW_CONTAINER).all()
    for el in elements:
        try:
            date_text = el.locator(DATE_SELECTOR).inner_text().strip()
            # Parse date if needed; keep as string
            rating = count_stars(el)
            review_text = el.locator(TEXT_SELECTOR).inner_text().strip()
            reviews.append({
                "date": date_text,
                "rating": rating,
                "text": review_text
            })
        except Exception as e:
            # Skip problematic review
            print(f"Skipping review due to error: {e}")
    return reviews


def click_load_more_if_present(page):
    """Click Load More button until it disappears.
    Returns True if button was clicked, False otherwise.
    """
    try:
        button = page.locator(LOAD_MORE_SELECTOR)
        if button.is_visible():
            button.click(timeout=5000)
            # Wait for new content to load
            page.wait_for_load_state('networkidle', timeout=12000)
            return True
    except PlaywrightTimeoutError:
        # Button not found or not visible
        pass
    return False


def scrape_all_reviews():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto(BASE_URL, wait_until="networkidle")

        all_reviews = []
        while True:
            # Scrape current batch
            batch = scrape_page(page)
            all_reviews.extend(batch)
            if not click_load_more_if_present(page):
                break

        browser.close()

    # Remove duplicates based on date+rating+text
    unique_reviews = []
    seen = set()
    for r in all_reviews:
        key = (r["date"], r["rating"], r["text"])
        if key not in seen:
            seen.add(key)
            unique_reviews.append(r)

    # Save to JSON
    out_path = Path(OUTPUT_FILE)
    out_path.write_text(json.dumps(unique_reviews, ensure_ascii=False, indent=2))
    print(f"Saved {len(unique_reviews)} reviews to {OUTPUT_FILE}")

if __name__ == "__main__":
    scrape_all_reviews()
