def analyze_page(page):
    dom_candidates = page.locator("*").evaluate_all("""
        elements => elements
            .slice(0, 100)
            .map(el => ({
                tag: el.tagName.toLowerCase(),
                id: el.id || null,
                class: typeof el.className === "string" ? el.className : null,
                text: (el.innerText || "").trim().slice(0, 300),
                itemprop: el.getAttribute("itemprop")
            }))
    """)

    return {
        "url": page.url,
        "title": page.title(),
        "headings": page.locator("h1, h2, h3").all_inner_texts(),
        "links": page.locator("a").all_inner_texts(),
        "buttons": page.locator("button").all_inner_texts(),
        "body_text": page.locator("body").inner_text(),
        "dom_candidates": dom_candidates,
    }
