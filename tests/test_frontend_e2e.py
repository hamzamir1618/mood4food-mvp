import re

from playwright.sync_api import Page, expect


def test_frontend_flow(page: Page):
    # Navigate to local server
    page.goto("http://localhost:8000/")

    # Wait for the UI to be ready
    page.wait_for_selector("#query-input")

    # Type a query
    page.fill("#query-input", "spicy food")
    page.click("#query-submit")

    # Assert Winner Card renders
    winner_card = page.locator(".winner-card").first
    expect(winner_card).to_be_visible(timeout=30000)

    # Wait for the initial score to render
    health_score = page.locator(".score-value.health").first
    initial_text = health_score.inner_text()

    # Assert XAI reason strings are present
    reason = page.locator(".score-reason").first
    expect(reason).to_be_visible(timeout=10000)

    # Assert runners-up cards render and are clickable
    runner_card = page.locator(".runner-card").first
    expect(runner_card).to_be_visible()

    expect(runner_card).not_to_have_class(re.compile(r"\bexpanded\b"))
    runner_card.click()
    expect(runner_card).to_have_class(re.compile(r"\bexpanded\b"))

    # Drag a slider (simulate drag by updating value and firing 'input')
    slider = page.locator("#slider-health")
    slider.evaluate("el => { el.value = 0.99; el.dispatchEvent(new Event('input')); }")

    # Wait for the UI to reflect the recalculation
    expect(health_score).not_to_have_text(initial_text, timeout=15000)

    # Click "not this one" to swap winner
    winner_name = page.locator("#winner-name").inner_text()
    alt_btn = page.locator("#btn-alternate")
    expect(alt_btn).to_be_visible()
    alt_btn.click()

    # Wait for winner name to change
    expect(page.locator("#winner-name")).not_to_have_text(winner_name, timeout=15000)

    # Perform a zero-match query to trigger the empty state
    page.fill("#query-input", "food under 1 rupee")
    page.click("#query-submit")

    # Assert empty state renders and Winner Card is hidden
    empty_state = page.locator(".empty-state-container").first
    expect(empty_state).to_be_visible(timeout=30000)
    expect(page.locator(".winner-card")).not_to_be_visible()
