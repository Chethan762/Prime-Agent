import asyncio
import json
import os
from pathlib import Path

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


async def extract_reviews(page):
    reviews = []
    seen = set()

    testimonial_elements = await page.locator(".testimonial").element_handles()
    for el in testimonial_elements:
        # text
        text_el = await el.query_selector("p.text")
        review_text = await text_el.inner_text() if text_el else None
        review_text = review_text.strip() if review_text else None

        # rating: count of filled star svgs inside span.rating
        rating_el = await el.query_selector("span.rating")
        rating = None
        if rating_el:
            svgs = await rating_el.query_selector_all("svg")
            rating = len(svgs) if svgs else None

        # date: not present in the captured fragments
        date = None

        # deduplicate
        key = (review_text, rating, date)
        if key in seen:
            continue
        seen.add(key)

        reviews.append(
            {
                "review_text": review_text,
                "rating": rating,
                "date": date,
            }
        )
    return reviews, seen


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Navigate to the target page
        await page.goto("https://www.web-scraping.dev/testimonials", wait_until="networkidle")

        all_reviews = []
        seen_keys = set()
        last_height = await page.evaluate("() => document.body.scrollHeight")
        no_new_content_rounds = 0

        while True:
            # Try to capture the network response that loads more testimonials
            try:
                async with page.expect_response(
                    lambda r: r.url.startswith("https://www.web-scraping.dev/api/testimonials")
                    and r.status == 200,
                    timeout=10000,
                ) as resp_info:
                    # Trigger loading – scroll to bottom
                    await page.evaluate(
                        """() => {
                            window.scrollBy(0, document.body.scrollHeight);
                        }"""
                    )
                # If we get here, a response was captured
                response = await resp_info.value
                # The response body is HTML fragment; Playwright can give us text
                await response.body()  # just to ensure it's loaded; we will parse DOM later
            except PlaywrightTimeoutError:
                # No response captured within timeout – may still have loaded content via DOM
                pass

            # Give the page a moment to render new content
            await page.wait_for_timeout(1000)

            # Extract current reviews from DOM
            new_reviews, new_seen = await extract_reviews(page)

            # Add only new ones
            for rev in new_reviews:
                key = (rev["review_text"], rev["rating"], rev["date"])
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_reviews.append(rev)

            # Check for scroll height change to decide whether to continue
            new_height = await page.evaluate("() => document.body.scrollHeight")
            if new_height == last_height:
                no_new_content_rounds += 1
            else:
                no_new_content_rounds = 0
                last_height = new_height

            # Stop after a few consecutive rounds with no new content
            if no_new_content_rounds >= 3:
                break

        # Ensure output directory exists
        output_path = Path("generated")
        output_path.mkdir(parents=True, exist_ok=True)

        # Write results
        with open(output_path / "reviews.json", "w", encoding="utf-8") as f:
            json.dump(all_reviews, f, ensure_ascii=False, indent=2)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
