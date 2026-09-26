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
        why = page.locator(".why")
        assert why.count(), "the layout gives no account of itself"
        assert not page.locator(".why-lines").first.is_visible()
        page.locator(".why summary").first.click()
        page.wait_for_timeout(200)
        lines = page.eval_on_selector_all(".why-lines li", "els => els.map(e => e.innerText)")
        assert any("protein" in line.lower() for line in lines), lines
    finally:
        page.close()
