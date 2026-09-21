import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        page.on(
            "response",
            lambda r: print("RESPONSE", r.status, r.url)
            if "/api/testimonials" in r.url
            else None,
        )

        await page.goto(
            "https://www.web-scraping.dev/testimonials",
            wait_until="networkidle",
        )

        print(
            "INITIAL_SCROLL_HEIGHT",
            await page.evaluate("document.body.scrollHeight"),
        )

        await page.evaluate(
            "window.scrollTo(0, document.body.scrollHeight)"
        )

        await page.wait_for_timeout(3000)

        print(
            "AFTER_SCROLL_HEIGHT",
            await page.evaluate("document.body.scrollHeight"),
        )

        await browser.close()


asyncio.run(main())
