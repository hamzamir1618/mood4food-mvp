"""
Phase 5 conversation (/chat and dialogue/). The pipeline's first two tiers are mocked
with a fixed pool, so the questions, answers and refinements run on real scoring
without Neo4j, Groq or the network.
"""

import fakeredis
import pytest
from fastapi.testclient import TestClient

from dialogue import critiques, questions
from dialogue.pool import allows, winner_under
from dialogue.state import Adjustments, Question
from tier_1.contracts.schemas import GroundedIntent

CATEGORIES = ("desi_traditional", "chinese_asian", "fast_food", "cafe_bakery")


def _pool() -> list[dict]:
    dishes = []
    for i in range(24):
        category = CATEGORIES[i % 4]
        sweet_shop = category == "cafe_bakery"
        shared = category == "fast_food" and i % 3 == 0
        dishes.append(
            {
                "dish_id": f"d{i}",
                "name": f"Dish {i}",
                "category": category,
                "price_pkr": 300.0 + 150 * i,
                "price_status": "trusted",
                "taste_source": "original",
                "nutrition_confidence": "high",
                "macros": {
                    "calories": 350.0 + 40 * i,
                    "protein_g": 20.0 + i,
                    "carbs_g": 50.0,
                    "fat_g": 15.0 + i / 2,
                },
                "taste_profile": {
                    "sweet": 0.8 if sweet_shop else 0.1,
                    "salty": 0.5,
                    "sour": 0.2,
                    "bitter": 0.1,
                    "umami": 0.1 if sweet_shop else 0.6,
                    "spice": 0.0 if sweet_shop else (0.1, 0.5, 0.9)[i % 3],
                },
                "serves_min": 3 if shared else 1,
                "serves_max": 4 if shared else 1,
                "ingredients": [],
                "allergens": [],
            }
        )
    return dishes


INTENTS = {
    "spicy desi food under 2000": {
        "mood_vector": {"spice": 0.9},
        "preferred_category": "desi",
        "budget_max_pkr": 2000.0,
    },
}


@pytest.fixture
def chat(monkeypatch):
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("tier_1.contracts.session_store.get_redis", lambda: fake_redis)
    calls = {"ingest": 0, "anchor": 0}

    def ingest(**kwargs):
        calls["ingest"] += 1
        text = kwargs.get("raw_input") or ""
        return {**GroundedIntent().model_dump(), "raw_input": text, **INTENTS.get(text, {})}

    def anchor(intent):  # Tier 1, roughly: the budget ceiling and the requested category
        calls["anchor"] += 1
        budget, category = intent.get("budget_max_pkr"), intent.get("preferred_category")
        found = [
            d
            for d in _pool()
            if (not budget or d["price_pkr"] <= budget)
            and (not category or category in d["category"])
        ]
        return {"source_intent": intent, "safe_candidates": found, "message": ""}

    monkeypatch.setattr("tier_1.multi_modal_ingestion.run_ingestion_pipeline", ingest)
    monkeypatch.setattr("tier_1.symbolic_anchoring.run_anchoring_pipeline", anchor)
    monkeypatch.setattr("tier_3.fulfillment_engine.enrich_blueprint", lambda bp: dict(bp))
    from orchestrator import app

    client = TestClient(app)
    client.calls = calls
    return client


def _say(client, **turn) -> dict:
    r = client.post("/chat", json=turn)
    assert r.status_code == 200, r.text
    return r.json()


# ── Asking ───────────────────────────────────────────────────────────────────


def test_a_vague_request_gets_at_most_two_questions_then_a_pick(chat):
    reply = _say(chat, text="I'm hungry")
    assert reply["type"] == "question" and reply["leading"]
    asked = 0
    while reply["type"] == "question":
        asked += 1
        question = reply["question"]
        assert len(question["chips"]) >= 2
        assert "would change what I pick" in question["why"]
        first = question["chips"][0]["value"]
        reply = _say(chat, answer={"question": question["id"], "value": first})
    assert 1 <= asked <= questions.MAX_QUESTIONS
    assert reply["type"] == "recommendation" and reply["recommendation"]["winning_dish"]
    assert chat.calls == {"ingest": 1, "anchor": 1}  # answers never re-query or call an LLM


def test_a_specific_request_goes_straight_to_a_pick(chat):
    reply = _say(chat, text="spicy desi food under 2000")
    assert reply["type"] == "recommendation"
    assert reply["recommendation"]["winning_dish"]["name"] == "Dish 8"  # the spiciest desi dish


def test_an_answer_steers_the_pick():
    pool = _pool()
    spicy = winner_under(pool, {}, {}, Adjustments(craved={"spice": 0.9}))
    sweet = winner_under(pool, {}, {}, Adjustments(craved={"sweet": 0.9}))
    by_id = {d["dish_id"]: d for d in pool}
    assert by_id[spicy]["taste_profile"]["spice"] == 0.9
    assert by_id[sweet]["category"] == "cafe_bakery"


def test_a_stale_or_made_up_answer_is_refused(chat):
    reply = _say(chat, text="I'm hungry")
    question = reply["question"]
    stale = {"answer": {"question": "nope", "value": "x"}}
    assert chat.post("/chat", json=stale).status_code == 409
    made_up = {"answer": {"question": question["id"], "value": "made-up"}}
    assert chat.post("/chat", json=made_up).status_code == 422
    assert chat.post("/chat", json={"critique": "cheaper"}).status_code == 409  # answer first
    assert chat.post("/chat", json={"text": "hi", "skip": True}).status_code == 422
    assert _say(chat, skip=True)["type"] == "recommendation"


# ── Refining ─────────────────────────────────────────────────────────────────


def test_refining_narrows_what_the_query_already_found(chat):
    first = _say(chat, text="spicy desi food under 2000")["recommendation"]["winning_dish"]
    cheaper = _say(chat, critique="cheaper")
    assert cheaper["reply"] == "Here's something cheaper."
    second = cheaper["recommendation"]["winning_dish"]
    assert second["price_pkr"] < first["price_pkr"]

    typed = _say(chat, text="same but cheaper")["recommendation"]["winning_dish"]
    assert typed["price_pkr"] < second["price_pkr"]
    last = _say(chat, critique="cheaper")
    # already the cheapest, and "cheaper" is the user's own choice, so there's nothing to loosen
    assert last["reply"].startswith("Nothing cheaper is left in what you asked for")
    assert last["recommendation"]["winning_dish"]["name"] == typed["name"]  # the pick stays
    assert chat.calls == {"ingest": 1, "anchor": 1}  # never re-queried


def test_milder_and_different_move_the_way_asked(chat):
    first = _say(chat, text="spicy desi food under 2000")["recommendation"]["winning_dish"]
    milder = _say(chat, critique="milder")["recommendation"]["winning_dish"]
    assert milder["taste_profile"]["spice"] < first["taste_profile"]["spice"]


def test_different_in_a_one_cuisine_pool_finds_another_of_the_same_kind(chat):
    # Everything the query found is desi, so another cuisine is impossible. "Different" used to
    # stop there; it now means a different dish of the kind that was asked for.
    first = _say(chat, text="spicy desi food under 2000")["recommendation"]["winning_dish"]
    reply = _say(chat, critique="different")
    other = reply["recommendation"]["winning_dish"]
    assert other["dish_id"] != first["dish_id"]
    assert other["category"] == "desi_traditional"
    assert reply["reply"].startswith("Everything here is desi")


def test_a_refinement_that_finds_nothing_asks_what_to_loosen(chat):
    _say(chat, text="spicy desi food under 2000")
    cheaper = _say(chat, critique="cheaper")["recommendation"]["winning_dish"]
    # spicier than this, and still cheaper than the first pick: nothing in the pool does both
    asked = _say(chat, critique="spicier")
    assert asked["type"] == "question"
    assert asked["question"]["id"] == "relax"
    labels = [c["label"] for c in asked["question"]["chips"]]
    # only the user's own earlier choice, and only because loosening it finds a dish
    assert labels == ["Forget “cheaper”"]
    assert asked["question"]["skip_label"] == "Keep my pick"
    loosened = _say(chat, answer={"question": "relax", "value": "price_below"})
    dish = loosened["recommendation"]["winning_dish"]
    assert dish["taste_profile"]["spice"] > cheaper["taste_profile"]["spice"]  # spicier was kept


def test_nothing_to_loosen_says_so_rather_than_asking(chat):
    _say(chat, text="spicy desi food under 2000")
    _say(chat, critique="spicier")  # to the hottest desi dish there is
    again = _say(chat, critique="spicier")
    assert again["type"] == "recommendation"
    assert "A new search is the way to widen it" in again["reply"]


def test_loosening_never_offers_allergies_or_diet():
    from dialogue.manager import RELAXABLE

    offered = {field for fields, _ in RELAXABLE for field in fields}
    assert not offered & {"allergens_pruned", "is_vegan", "is_vegetarian", "is_halal"}


# ── Reading free text ────────────────────────────────────────────────────────


def test_more_filling_is_not_just_more_calories():
    # Found on the live app: "more filling" than a tikka picked a Rs 35 naan at 1,109 kcal.
    tikka = {"name": "Tikka", "macros": {"calories": 830.0, "protein_g": 34.0}}
    adj = Adjustments().merged(critiques.adjustment("more_filling", tikka, {}))
    naan = {"price_pkr": 35.0, "macros": {"calories": 1109.0, "protein_g": 21.0}}
    biryani = {"price_pkr": 800.0, "macros": {"calories": 950.0, "protein_g": 38.0}}
    assert not allows(adj, naan)
    assert allows(adj, biryani)


def test_adjustments_only_ever_tighten():
    adj = Adjustments().merged({"ceiling": 1000}).merged({"ceiling": 1500})
    assert adj.ceiling == 1000
    adj = adj.merged({"exclude_categories": ["pizza"]}).merged({"exclude_categories": ["afghan"]})
    assert adj.exclude_categories == ["afghan", "pizza"]


def test_refinements_are_read_from_short_messages_only():
    assert critiques.parse("same but cheaper") == "cheaper"
    assert critiques.parse("not so spicy please") == "milder"
    assert critiques.parse("make it spicier") == "spicier"
    assert critiques.parse("something different") == "different"
    assert critiques.parse("biryani") is None
    long_request = "actually a cheaper chinese place near F-7 for four of us tonight please"
    assert critiques.parse(long_request) is None


def test_typed_answers_are_understood():
    taste = Question(slot="taste", text="", chips=questions.TASTE_CHIPS)
    assert questions.parse_answer("something hot", taste)[0] == "spicy"
    assert questions.parse_answer("I'm not sure", taste) is None
    budget = Question(slot="budget", text="", chips={})
    assert questions.parse_answer("around 1,200", budget)[1]["adjust"] == {"ceiling": 1200.0}
    party = Question(slot="party", text="", chips=questions.PARTY_CHIPS)
    assert questions.parse_answer("for 3 people", party)[1]["adjust"] == {"party_size": 3}
    assert questions.parse_answer("just me", party)[0] == "1"
