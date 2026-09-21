from agent import PrimeAgentClient

a = PrimeAgentClient()

prompt = """
Call the IPython tool NOW.

Run this exact Python code:

import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.web-scraping.dev/reviews", wait_until="domcontentloaded")
        print("TITLE=" + await page.title())
        print("BODY_LENGTH=" + str(len(await page.locator("body").inner_text())))
        await browser.close()

await main()

After the IPython tool returns, stop.
"""

events = a.send_prompt(prompt)

print()
print("=" * 60)
print("TOOL RESULTS")
print("=" * 60)

for event in events:
    if event.get("type") == "tool_execution_end":
        print(event)