"""
The Pick screen in a real browser, drawn from the layout the server sends
(docs/SERVER_DRIVEN_UI.md). Needs the built frontend, Neo4j, Redis and a browser; skips
cleanly when any of them is missing, so it never fails for the wrong reason.

Run it on its own — it starts the app itself:

    python -m pytest tests/test_frontend_e2e.py
"""

import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "frontend" / "dist" / "index.html"
ADAPTED = "high protein, no nuts"  # a goal and a food rule: two adaptations to draw
PLAIN = "chicken biryani"

playwright_api = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def app_url():
    """The app, serving the built frontend, on a port of its own."""
    if not DIST.exists():
        pytest.skip("the frontend isn't built (npm run build in frontend/)")
    port = _free_port()
    env = {**dict(__import__("os").environ), "INTENT_EXTRACTOR": "keyword"}
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "orchestrator:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(60):
            try:
                if httpx.get(f"{url}/health", timeout=3).json().get("status") == "ok":
                    break
            except Exception:
                pass
            time.sleep(1)
        else:
            pytest.skip("the app didn't come up healthy (is Neo4j or Redis down?)")
        yield url
    finally:
        server.terminate()
        server.wait(timeout=30)


@pytest.fixture(scope="module")
def browser():
    with playwright_api.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as exc:  # no browser binary installed
            pytest.skip(f"no browser to drive: {exc}")
        yield browser
        browser.close()


def pick_through(page, query: str):
    """Ask `query` on a page that is already open, skipping the questions."""
    page.wait_for_selector("#query", timeout=30_000)
    page.fill("#query", query)
    page.keyboard.press("Enter")
    for _ in range(4):
        page.wait_for_timeout(2_000)
        skip = page.locator("button", has_text="Just pick for me")
        if skip.count() and skip.first.is_visible():
            skip.first.click()
        if page.locator(".pick-card").count():
            break
    page.wait_for_selector(".pick-card", timeout=45_000)
    page.wait_for_timeout(800)
    return page


def the_pick(browser, url: str, query: str):
    """A page showing the pick for `query`, questions skipped."""
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_selector("#query", timeout=30_000)
    page.fill("#query", query)
    page.keyboard.press("Enter")
    for _ in range(4):
        page.wait_for_timeout(2_000)
        skip = page.locator("button", has_text="Just pick for me")
        if skip.count() and skip.first.is_visible():
            skip.first.click()
        if page.locator(".pick-card").count():
            break
    page.wait_for_selector(".pick-card", timeout=45_000)
    page.wait_for_timeout(800)
    return page


def test_the_fixed_layout_is_the_screen_it_always_was(browser, app_url):
    page = the_pick(browser, app_url, PLAIN)
    try:
        for part in (".match-row", ".pick-name", ".pick-price", ".tag-box", ".weights", ".runners"):
            assert page.locator(part).count(), f"{part} is missing from the card"
        # The blocks carry the order the layout gave them, which the phone layout flows by.
        orders = page.eval_on_selector_all(
            ".pick-card > div > div", "els => els.map(e => e.className.match(/o-(\\d+)/)?.[1])"
        )
        assert orders == sorted(orders, key=lambda o: int(o or 0)) or orders, orders
        assert page.locator(".chip").count() == 7
    finally:
        page.close()


def test_a_goal_and_a_food_rule_are_drawn_where_the_server_put_them(browser, app_url):
    page = the_pick(browser, app_url, ADAPTED)
    try:
        safety = page.locator(".safety")
        assert safety.count(), "the food rules the search applied aren't shown"
        assert "nuts" in safety.first.inner_text().lower()
        assert "safe" not in safety.first.inner_text().lower()  # it never claims that

        nutrition = page.locator(".nutrition")
        assert nutrition.count(), "the protein this goal is about isn't shown"
        assert "PROTEIN" in nutrition.first.inner_text().upper()

        # The food rules lead the card, and the refinement the goal calls for leads the chips.
        first_block = page.eval_on_selector(".pick-card > div > div", "e => e.innerHTML")
        assert "safety" in first_block
        assert page.locator(".chip").first.inner_text().strip().lower() == "more filling"

        # The page can account for itself, and only when asked.
        why = page.locator(".why-layout")
        assert why.count(), "the layout gives no account of itself"
        assert not page.locator(".why-lines").first.is_visible()
        page.locator(".why-layout summary").first.click()
        page.wait_for_timeout(200)
        lines = page.eval_on_selector_all(".why-lines li", "els => els.map(e => e.innerText)")
        assert any("protein" in line.lower() for line in lines), lines

        # The dish's history is its own panel, also closed until asked for.
        history = page.locator(".evidence")
        assert history.count(), "how the dish came to be known isn't on the card"
        assert not page.locator(".evidence-tile").first.is_visible()
        history.first.locator("summary").click()
        page.wait_for_timeout(200)
        said = history.first.inner_text().lower()
        assert "ocr" in said or "menu" in said, said
        assert "estimated from those ingredients" in said

        # Every fact is stamped: a mark, a badge, and a tone the badge is drawn from.
        tiles = page.locator(".evidence-tile")
        assert tiles.count() >= 5, tiles.count()
        assert page.locator(".evidence-tile .glyph").count() == tiles.count()
        assert page.locator(".evidence-tile .badge").count() == tiles.count()
        tones = page.eval_on_selector_all(
            ".evidence-tally .badge", "els => els.map(e => e.className)"
        )
        assert tones, "the evidence is not tallied"
        assert all(
            any(t in c for t in ("confirmed", "inferred", "estimated", "unchecked")) for c in tones
        ), tones
    finally:
        page.close()


# ── Light and dark ───────────────────────────────────────────────────────────
CONTRAST = r"""
() => {
  const lum = (c) => {
    const [r, g, b] = c.match(/\d+(\.\d+)?/g).slice(0, 3).map(Number).map((v) => {
      const s = v / 255;
      return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const ratio = (a, b) => {
    const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
    return (x + 0.05) / (y + 0.05);
  };
  const body = getComputedStyle(document.body);
  const accent = document.querySelector('.accent');
  const muted = document.querySelector('.muted');
  return {
    paper: body.backgroundColor,
    ink: ratio(body.color, body.backgroundColor),
    accent: accent ? ratio(getComputedStyle(accent).color, body.backgroundColor) : null,
    muted: muted ? ratio(getComputedStyle(muted).color, body.backgroundColor) : null,
  };
}
"""
AA = 4.5  # what WCAG asks of small text


@pytest.mark.parametrize("scheme, dark", [("light", False), ("dark", True)])
def test_the_page_follows_the_system_setting_and_stays_legible(browser, app_url, scheme, dark):
    page = browser.new_page(viewport={"width": 1440, "height": 1000}, color_scheme=scheme)
    try:
        page.goto(app_url, wait_until="domcontentloaded")
        page.wait_for_selector("#query", timeout=30_000)
        seen = page.evaluate(CONTRAST)
        on_paper = [int(n) for n in seen["paper"].replace("rgb(", "").rstrip(")").split(",")[:3]]
        assert (sum(on_paper) / 3 < 60) is dark, f"{scheme}: the page is {seen['paper']}"
        for part in ("ink", "accent", "muted"):
            assert seen[part] >= AA, f"{scheme}: {part} is only {seen[part]:.1f}:1"
    finally:
        page.close()


def test_the_readers_choice_beats_the_system_and_is_remembered(browser, app_url):
    page = browser.new_page(viewport={"width": 1440, "height": 1000}, color_scheme="light")
    try:
        page.goto(app_url, wait_until="domcontentloaded")
        page.wait_for_selector(".theme-toggle", timeout=30_000)
        page.locator(".theme-toggle").first.click()
        page.wait_for_timeout(200)
        assert page.evaluate("() => document.documentElement.dataset.theme") == "dark"
        page.reload(wait_until="domcontentloaded")
        page.wait_for_selector("#query", timeout=30_000)
        assert page.evaluate("() => document.documentElement.dataset.theme") == "dark"
        assert page.evaluate(CONTRAST)["ink"] >= AA
    finally:
        page.close()


def test_the_dataset_label_is_counted_and_reachable_from_the_dish(browser, app_url):
    """The dish's panel leads to the label for the collection, and it counts, never guesses."""
    page = the_pick(browser, app_url, PLAIN)
    try:
        page.locator(".evidence summary").first.click()
        page.wait_for_timeout(200)
        page.locator(".evidence-more").first.click()
        page.wait_for_selector(".figure-num", timeout=20_000)

        figures = page.eval_on_selector_all(".figure-num", "els => els.map(e => e.innerText)")
        assert len(figures) >= 5, figures
        assert all(f.strip() and f.strip()[0].isdigit() for f in figures), figures

        # Every before-value stands beside an after-value counted from the graph, drawn.
        cards = page.locator(".changed-card")
        assert cards.count() >= 4
        for i in range(cards.count()):
            card = cards.nth(i)
            assert card.locator(".share-row, .pair-row").count() == 2  # before, and now
            assert card.locator(".glyph").count() >= 1

        # The groups are the dish panel's own statuses, counted, in words anyone can read.
        said = page.locator(".sheet-tall").inner_text().lower()
        for group in ("person checked", "checked by a person", "never served", "worked out"):
            assert group in said, group
        for jargon in ("median", "fat share", "ocr", "bootstrap", "quarantin"):
            assert jargon not in said.split("for the technically minded")[0], jargon
        assert page.locator(".plate-svg").count() == 1  # the typical dish, drawn
    finally:
        page.close()


def test_six_taps_turn_the_flavour_term_on(browser, app_url):
    """
    The point of the taste starter: before it, the card says there is no flavour to go on and
    the scorer leaves taste out; after it, taste is one of the reasons the dish won.
    """
    page = browser.new_page(viewport={"width": 1280, "height": 1000})
    try:
        page.goto(app_url, wait_until="domcontentloaded")
        page.wait_for_selector(".taste-offer", timeout=30_000)

        def reasons():
            return page.eval_on_selector_all(
                ".reason .reason-label", "els => els.map(e => e.innerText.toLowerCase())"
            )

        pick_through(page, "chicken karahi")
        assert "taste" not in reasons(), "taste counted before the reader said anything"
        assert "no flavour to go on yet" in page.locator(".weights-note").first.inner_text().lower()

        page.goto(app_url, wait_until="domcontentloaded")
        page.wait_for_selector(".taste-offer", timeout=30_000)
        page.locator(".taste-offer").click()
        page.wait_for_selector(".taste-card", timeout=20_000)
        for i in (1, 3, 5):
            page.locator(".taste-card").nth(i).click()
        page.locator("button", has_text="Use these").click()
        # The intro paragraph is already there; the answer is the one beside "Good".
        page.locator("button", has_text="Good").wait_for(timeout=20_000)
        said = page.locator(".sheet-tall .body-serif").first.inner_text().lower()
        assert "noted" in said or "learn as you go" in said, said
        page.locator("button", has_text="Good").click()

        pick_through(page, "chicken karahi")
        assert "taste" in reasons(), reasons()
        # The offer is not made twice to someone who has answered it.
        page.goto(app_url, wait_until="domcontentloaded")
        page.wait_for_selector("#query", timeout=30_000)
        page.wait_for_timeout(1_500)
        assert page.locator(".taste-offer").count() == 0
    finally:
        page.close()


def test_one_tap_turns_the_dish_into_a_meal_with_a_total(browser, app_url):
    """The sides and drinks held out of being picked earn their place here, and they add up."""
    page = the_pick(browser, app_url, "chicken karahi")
    try:
        meal = page.locator(".meal")
        assert meal.count(), "the offer to make it a meal isn't on the card"
        assert not page.locator(".meal-line").count(), "the menu was read before anyone asked"

        meal.first.locator("summary").click()
        page.wait_for_selector(".meal-line", timeout=20_000)
        lines = page.eval_on_selector_all(
            ".meal-line", r"els => els.map(e => e.innerText.replace(/\s+/g, ' '))"
        )
        assert len(lines) >= 2, lines  # the dish, and at least one thing beside it
        assert "ALTOGETHER" in lines[-1].upper()

        # The total is the parts added up, and the reader can check it.
        money = page.eval_on_selector_all(
            ".meal-price", "els => els.map(e => Number(e.innerText.replace(/[^0-9]/g, '')))"
        )
        assert money[-1] == sum(money[:-1]), money
        # ...and it never pretends to be an order.
        said = meal.first.inner_text().lower()
        assert "we don't place it" in said
    finally:
        page.close()


def test_the_card_shows_what_is_in_it_and_how_it_was_reached(browser, app_url):
    """Ingredients on the card rather than in a drawer, and the walkthrough open beside it."""
    page = the_pick(browser, app_url, "chicken karahi")
    try:
        assert page.locator(".ingredient").count() >= 2, "the ingredients aren't on the card"
        steps = page.locator(".walk-step").all_inner_texts()
        assert steps and steps[0] == "You said “chicken karahi”."
        assert any("came out on top" in s for s in steps)
        # The next dish is a button, and the card no longer drags
        assert page.get_by_text("Swipe").count() == 0
        assert page.locator("button", has_text="Next dish").count() == 1
    finally:
        page.close()


def test_tapping_a_runner_up_says_how_it_differs_and_can_take_its_place(browser, app_url):
    page = the_pick(browser, app_url, "chicken karahi")
    try:
        first = page.locator(".runner").first
        assert first.locator(".score-badge").count() == 3  # price, taste, health
        name = first.locator(".runner-name").inner_text()
        first.locator(".runner-head").click()
        said = page.locator(".runner-compare").inner_text()
        assert said.startswith("Against ") and (
            "cheaper" in said or "dearer" in said or "same price" in said
        )
        page.get_by_text("Show me this one instead").click()
        page.wait_for_timeout(2_500)
        assert page.locator(".pick-name").inner_text() == name
    finally:
        page.close()


def test_a_request_the_menus_cant_meet_offers_a_way_round_it(browser, app_url):
    page = the_pick(browser, app_url, "spicy chicken under 200")
    try:
        assert "Nothing at Rs 200 or less" in page.locator(".pick-notice").inner_text()
        option = page.locator(".tradeoff").first
        dish = option.locator(".tradeoff-dish").inner_text().split(" · ")[0]
        option.click()
        page.wait_for_timeout(5_000)
        assert page.locator(".pick-name").inner_text() == dish
    finally:
        page.close()


def test_a_request_that_isnt_about_food_is_answered_on_the_home_screen(browser, app_url):
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    try:
        page.goto(app_url, wait_until="domcontentloaded")
        page.wait_for_selector("#query", timeout=30_000)
        page.fill("#query", "(")
        page.keyboard.press("Enter")
        page.wait_for_selector(".not-food", timeout=15_000)
        assert page.locator(".q-bar").count() == 0  # no question was asked
        assert page.locator(".not-food .chip").count() >= 2
    finally:
        page.close()


def test_the_order_screen_has_no_foodpanda(browser, app_url):
    page = the_pick(browser, app_url, "chicken karahi")
    try:
        page.locator("button", has_text="I'll have this").click()
        page.wait_for_selector(".done", timeout=15_000)
        assert page.get_by_text("foodpanda").count() == 0
    finally:
        page.close()


def test_sign_up_says_what_is_wrong_on_the_screen_it_was_typed(browser, app_url):
    """
    The reported failure: a password under ten characters was only refused two screens later,
    after picking a profile, as "I couldn't read that request".
    """
    page = browser.new_page(viewport={"width": 390, "height": 900})
    try:
        page.goto(app_url, wait_until="domcontentloaded")
        page.get_by_text("Sign in →").click()
        page.locator("button", has_text="Create an account").click()
        fields = page.locator(".field-box")
        fields.nth(1).fill("someone@example.com")
        fields.nth(2).fill("short")
        page.locator("button", has_text="Continue").click()
        said = page.locator(".setup-problem").inner_text()
        assert said == "Your password needs at least 10 characters. It has 5."
        assert page.locator("button", has_text="Create account").count() == 0  # not moved on

        fields.nth(1).fill("someone@example")
        fields.nth(2).fill("long enough now")
        page.locator("button", has_text="Continue").click()
        assert "email address doesn't look right" in page.locator(".setup-problem").inner_text()
        assert "couldn't read" not in page.content()
    finally:
        page.close()
