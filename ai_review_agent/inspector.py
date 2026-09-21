import json
import sys
from playwright.sync_api import sync_playwright


def inspect_site(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(url, wait_until="domcontentloaded", timeout=30000)

        page.wait_for_timeout(3000)

        evidence = {
            "url": url,
            "title": page.title(),
            "final_url": page.url,
            "review_candidates": [],
            "buttons": [],
            "sample_html": "",
        }

        # Collect elements that look like review containers.
        candidates = page.locator(
            "[data-testid*='review'], "
            "[class*='review'], "
            "[id*='review']"
        )

        count = min(candidates.count(), 10)

        for i in range(count):
            element = candidates.nth(i)

            try:
                evidence["review_candidates"].append({
                    "tag": element.evaluate("(el) => el.tagName"),
                    "class": element.get_attribute("class"),
                    "id": element.get_attribute("id"),
                    "data_testid": element.get_attribute("data-testid"),
                    "text": element.inner_text(timeout=3000)[:500],
                    "html": element.evaluate(
                        "(el) => el.outerHTML"
                    )[:3000],
                })
            except Exception:
                continue

        # Collect visible buttons.
        buttons = page.locator("button")
        button_count = min(buttons.count(), 20)

        for i in range(button_count):
            button = buttons.nth(i)

            try:
                text = button.inner_text(timeout=1000).strip()

                if text:
                    evidence["buttons"].append({
                        "text": text,
                        "id": button.get_attribute("id"),
                        "class": button.get_attribute("class"),
                    })
            except Exception:
                continue

        # Compact page HTML evidence.
        try:
            evidence["sample_html"] = page.locator("body").inner_text()[:5000]
        except Exception:
            pass

        browser.close()

        return evidence


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python inspector.py <url>")
        sys.exit(1)

    url = sys.argv[1]

    try:
        result = inspect_site(url)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({
            "error": type(e).__name__,
            "message": str(e),
        }, indent=2))
        sys.exit(2)
