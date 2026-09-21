from agent import PrimeAgentClient

a = PrimeAgentClient()

prompt = """
Use IPython.

Run exactly this Python code:

import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        print("CHROMIUM_OK")
        await browser.close()

await main()

Do nothing else.
"""

events = a.send_prompt(prompt)

print()
print("--- TOOL RESULT ---")

for event in events:
    if event.get("type") == "tool_execution_end":
        print(event)