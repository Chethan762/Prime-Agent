from playwright.async_api import async_playwright


async def discover_dynamic_network(page, scrolls=5):
    """Observe requests/responses triggered by scrolling."""
    discovered = []

    async def on_response(response):
        if response.request.resource_type not in {"xhr", "fetch"}:
            return

        item = {
            "url": response.url,
            "method": response.request.method,
            "status": response.status,
            "content_type": response.headers.get("content-type"),
        }

        if response.request.post_data:
            item["request_body"] = response.request.post_data[:2000]

        try:
            body = await response.text()
            item["response_preview"] = body[:1000]
        except Exception:
            pass

        discovered.append(item)

    page.on("response", on_response)

    for _ in range(scrolls):
        previous_height = await page.evaluate("document.body.scrollHeight")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1500)
        new_height = await page.evaluate("document.body.scrollHeight")

        if new_height == previous_height:
            break

    return discovered


async def inspect_site(url):
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)
    page = await browser.new_page()

    try:
        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000,
        )

        await page.wait_for_timeout(3000)

        dynamic_network = await discover_dynamic_network(page)

        evidence = {
            "url": url,
            "title": await page.title(),
            "final_url": page.url,
            "review_containers": [],
            "field_examples": {},
            "pagination": [],
            "graphql_or_api_schema": [],
        }

        # Find actual rendered review containers.
        # Prefer explicit review test IDs and avoid unrelated
        # elements such as scripts, navigation, and cart items.
        containers = page.locator(
            "[data-testid='review']"
        )

        if await containers.count() == 0:
            containers = page.locator(
                "div.review"
            )

        if await containers.count() == 0:
            containers = page.locator(
                "[class~='review']"
            )

        count = min(await containers.count(), 3)

        for i in range(count):
            el = containers.nth(i)

            try:
                evidence["review_containers"].append({
                    "tag": await el.evaluate(
                        "(el) => el.tagName"
                    ),
                    "class": await el.get_attribute("class"),
                    "id": await el.get_attribute("id"),
                    "data_testid": await el.get_attribute(
                        "data-testid"
                    ),
                    "data_review_id": await el.get_attribute(
                        "data-review-id"
                    ),
                    "text": (
                        await el.inner_text()
                    )[:300],
                })
            except Exception:
                continue

        # Inspect common review fields inside the first
        # actual review container.
        if count:
            first = containers.nth(0)

            field_selectors = {
                "review_text": [
                    "[data-testid='review-text']",
                    "[class*='review-text']",
                    "[class*='content']",
                    "p",
                ],
                "rating": [
                    "[data-testid='review-stars']",
                    "[class*='rating']",
                    "[class*='star']",
                    "[class*='score']",
                ],
                "author": [
                    "[data-testid='review-author']",
                    "[class*='author']",
                    "[class*='user']",
                    "[class*='name']",
                ],
                "date": [
                    "[data-testid='review-date']",
                    "time",
                    "[class*='date']",
                    "[class*='posted']",
                ],
            }

            for field, selectors in field_selectors.items():
                for selector in selectors:
                    try:
                        loc = first.locator(selector)

                        if await loc.count():
                            sample = (
                                await loc.first.inner_text()
                            ).strip()

                            field_info = {
                                "selector": selector,
                                "text": sample[:250],
                            }

                            if field == "rating":
                                field_info["svg_count"] = await loc.first.locator("svg").count()

                            evidence["field_examples"][field] = field_info
                            break
                    except Exception:
                        continue

        # Detect visible pagination/loading controls.
        buttons = page.locator(
            "button, a, [role='button']"
        )

        button_count = min(await buttons.count(), 20)

        for i in range(button_count):
            button = buttons.nth(i)

            try:
                text = (
                    await button.inner_text()
                ).strip()

                if not text:
                    continue

                lower = text.lower()

                if any(
                    word in lower
                    for word in [
                        "load more",
                        "next",
                        "previous",
                        "more",
                        "page",
                    ]
                ):
                    evidence["pagination"].append({
                        "text": text[:100],
                        "tag": await button.evaluate(
                            "(el) => el.tagName"
                        ),
                        "id": await button.get_attribute("id"),
                        "class": await button.get_attribute("class"),
                    })
            except Exception:
                continue

        # Capture only small API/GraphQL schema snippets.
        scripts = page.locator(
            "script[type='application/graphql'], "
            "script[type='application/json']"
        )

        script_count = min(await scripts.count(), 3)

        for i in range(script_count):
            script = scripts.nth(i)

            try:
                text = (
                    await script.inner_text()
                ).strip()

                if text:
                    evidence["graphql_or_api_schema"].append(
                        text[:1200]
                    )
            except Exception:
                continue

        evidence["dynamic_network"] = dynamic_network

        return evidence

    finally:
        await browser.close()
        await pw.stop()
