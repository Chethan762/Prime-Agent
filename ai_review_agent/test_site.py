from agent import PrimeAgentClient

a = PrimeAgentClient()

prompt = """
You are testing browser access for an autonomous review-scraping agent.

Use IPython with Playwright's ASYNC API.

Open this exact URL:

https://www.web-scraping.dev/reviews

Use Chromium in headless mode.

Inspect the page and determine:

1. Page title
2. Whether reviews are present
3. How many review elements are currently visible
4. The DOM structure surrounding one review
5. Author selector or identifying attribute
6. Rating selector or identifying attribute
7. Review text selector or identifying attribute
8. Date selector or identifying attribute
9. Whether there is pagination, Load More, or another mechanism for additional reviews

Print your findings clearly.

Do not create or modify any files.
Do not use sync_playwright.
Use playwright.async_api.

Do not stop until the page has actually been inspected.
"""

events = a.send_prompt(prompt)

print()
print("=" * 60)
print("TOOL RESULTS")
print("=" * 60)

for event in events:
    if event.get("type") == "tool_execution_end":
        print(event)