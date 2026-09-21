from agent import PrimeAgentClient

a = PrimeAgentClient()

prompt = """
Use IPython with Playwright ASYNC API.

Open:
https://www.web-scraping.dev/reviews

After navigation, inspect the FINAL page.

Print:
1. FINAL_URL
2. TITLE
3. BODY_TEXT
4. The outer HTML of the first 3 elements that appear to represent reviews.
5. The text of the first 3 reviews.

Do not create files.
Do not use sync_playwright.
Do not stop until the page has been inspected.

Use this exact approach:
- launch Chromium headless
- create a page
- goto the URL with wait_until="domcontentloaded"
- wait briefly if necessary for content
- inspect the DOM
- print the findings
- close browser
"""

events = a.send_prompt(prompt)

print()
print("=" * 60)
print("TOOL RESULTS")
print("=" * 60)

for event in events:
    if event.get("type") == "tool_execution_end":
        print(event)