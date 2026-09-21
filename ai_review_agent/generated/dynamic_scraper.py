from playwright.sync_api import sync_playwright
from typing import List, Dict


def scrape_reviews() -> List[Dict[str, str]]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto(
            "https://www.web-scraping.dev/reviews",
            wait_until="load"
        )

        page.wait_for_selector(
            "#latest-reviews .review",
            state="visible",
            timeout=15000
        )

        reviews = []
        seen_ids = set()

        while True:
            review_elements = page.locator(
                "#latest-reviews .review"
            ).all()

            for elem in review_elements:
                review_id = elem.get_attribute("data-review-id")

                if review_id in seen_ids:
                    continue

                date = elem.locator(
                    '[data-testid="review-date"]'
                ).inner_text().strip()

                rating = elem.locator(
                    '[data-testid="review-stars"] svg'
                ).count()

                review_text = elem.locator(
                    '[data-testid="review-text"]'
                ).inner_text().strip()

                reviews.append({
                    "date": date,
                    "rating": rating,
                    "review_text": review_text
                })

                if review_id:
                    seen_ids.add(review_id)

            load_more = page.get_by_role(
                "button",
                name="Load More"
            )

            if not load_more.is_visible():
                break

            before_count = page.locator(
                "#latest-reviews .review"
            ).count()

            load_more.click()

