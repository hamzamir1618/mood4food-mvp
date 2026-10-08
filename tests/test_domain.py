"""
The out-of-domain check (tier_1/domain.py): a request has to be about food before the pipeline,
and the language model, ever see it. Run on the built-in vocabulary alone, without the menus'
own words, so it holds even when the graph can't be read.
"""

import pytest

from tier_1 import domain


@pytest.fixture(autouse=True)
def no_graph(monkeypatch):
    monkeypatch.setattr(domain, "_menu_words", lambda: frozenset())


@pytest.mark.parametrize(
    "text",
    [
        "spicy chicken under 200",
        "biryani under 50",
        "vegan chicken karahi",
        "sweet",
        "something cheap but filling",
        "surprise me",
        "i'm starving",
        "kuch teekha",
        "chiken karahi",  # a misspelling, beside a word it knows
        "biriyani",
        "what should I have tonight",
        "something for a rainy day",
        "no nuts please",
        "high protein meal",
        "nihari",
        "i feel sad",
        "dinner for 4 under 3000",
        "gol gappay",
        "something in F-7",
    ],
)
def test_requests_about_food_go_through(text):
    verdict = domain.check(text)
    assert verdict.food, text
    assert verdict.heard


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("(", "empty"),
        ("!!!", "empty"),
        ("123", "empty"),
        ("what is the capital of france", "other"),
        ("who is the prime minister", "other"),
        ("write me a poem", "other"),
        ("asdfgh", "other"),
        ("how do i fix my car", "other"),
        ("hello", "greeting"),
        ("hi there", "greeting"),
        ("قورمہ", "script"),
    ],
)
def test_anything_else_is_answered_and_says_why(text, kind):
    verdict = domain.check(text)
    assert not verdict.food
    assert verdict.kind == kind
    assert verdict.reply


def test_a_refusal_quotes_what_was_said():
    assert "“write me a poem”" in domain.check("write me a poem").reply


def test_a_word_from_the_menus_themselves_counts(monkeypatch):
    monkeypatch.setattr(domain, "_menu_words", lambda: frozenset({"pogaca"}))
    assert domain.check("pogaca").food
