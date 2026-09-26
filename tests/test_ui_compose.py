"""
Server-driven UI (ui/signals.py, ui/compose.py): the same recommendation is composed
differently for different users, every adaptation says why, and nothing a user relies on
for safety can be composed away. Pure: no database.
"""

from types import SimpleNamespace

import pytest

from accounts.models import DietaryProfile
from dialogue.critiques import CRITIQUES
from ui import compose, signals

WINNER = {
    "dish_id": "d1",
    "name": "Chicken Tikka",
    "price_pkr": 1200.0,
    "serves_max": 2,
    "macros": {"calories": 650.0, "protein_g": 48.0},
    "nutrition_confidence": "estimated",
    "allergens": ["dairy"],
}
EVEN = {"w_h": 0.34, "w_b": 0.33, "w_t": 0.33}


def blueprint(weights=EVEN, **extra) -> dict:
    return {
        "winning_dish": dict(WINNER),
        "agent_weights": weights,
        "top_candidates": [{"dish_id": "d1"}, {"dish_id": "d2"}, {"dish_id": "d3"}],
        **extra,
    }


def ids(layout: dict, slot: str | None = None) -> list[str]:
    return [b["id"] for b in layout["blocks"] if slot is None or b["slot"] == slot]


def block(layout: dict, block_id: str) -> dict:
    return next(b for b in layout["blocks"] if b["id"] == block_id)


def event(kind: str, dish_uid: str | None = None, critique: str | None = None) -> dict:
    return {
        "kind": kind,
        "dish_uid": dish_uid,
        "dish_name": dish_uid or "",
        "detail": {"critique": critique} if critique else {},
    }


# ── The fixed layout is the default ─────────────────────────────────────────────
def test_with_nothing_known_the_layout_is_todays_pick_screen():
    layout = compose.pick(blueprint(), {})
    assert ids(layout) == [b for b, _ in compose.DEFAULT if b != "notice"]
    assert layout["actions"] == {"refinements": list(CRITIQUES), "lead": None}
    assert layout["why"] == []


def test_near_even_weights_keep_the_usual_reason_order():
    layout = compose.pick(blueprint(), {})
    assert block(layout, "reasons")["props"]["order"] == list(compose.DEFAULT_REASONS)


# ── Pinned blocks ────────────────────────────────────────────────────────────
def test_the_widened_search_notice_leads_when_there_is_one():
    layout = compose.pick(blueprint(relaxation_notice="I couldn't find sushi."), {})
    assert ids(layout, "top") == ["notice"]
    assert block(layout, "notice")["props"]["text"] == "I couldn't find sushi."


@pytest.mark.parametrize(
    "sig",
    [
        {},
        {"persona": "frugal_student", "cheap_query": True},
        {"goal": "muscle_gain", "refinements": {"cheaper": 9}},
        {"signed_in": True, "allergens": ["nuts"], "halal": True},
    ],
)
def test_the_allergen_line_is_never_composed_away(sig):
    assert "allergens" in ids(compose.pick(blueprint(), sig))


def test_a_rule_cannot_remove_a_pinned_block():
    layout = compose.Layout()
    layout.remove("allergens")
    assert layout.get("allergens") is not None


# ── Food rules ───────────────────────────────────────────────────────────────
def test_food_rules_from_the_profile_are_confirmed_first_on_the_card():
    sig = {
        "dietary": {"allergies": ["nuts"], "diet": "none", "halal_only": True},
        "allergens": ["nuts"],
        "halal": True,
    }
    layout = compose.pick(blueprint(), sig)
    assert ids(layout, "main")[0] == "safety"
    assert block(layout, "safety")["props"]["lines"] == [
        "No dishes with nuts — from your profile",
        "Halal only",
    ]
    assert block(layout, "allergens")["variant"] == "emphasised"
    assert any(w["block"] == "safety" and w["source"] == "profile" for w in layout["why"])


def test_the_safety_block_never_claims_a_dish_is_safe():
    layout = compose.pick(blueprint(), {"allergens": ["gluten"]})
    text = " ".join(block(layout, "safety")["props"]["lines"]).lower()
    assert "safe" not in text
    assert block(layout, "safety")["props"]["lines"] == ["No dishes with gluten"]


# ── Goals and personas ─────────────────────────────────────────────────────────
def test_a_muscle_goal_puts_protein_beside_the_price_and_more_filling_first():
    layout = compose.pick(blueprint(), {"signed_in": True, "goal": "muscle_gain"})
    main = ids(layout, "main")
    assert main.index("nutrition") == main.index("price") + 1
    assert block(layout, "nutrition")["variant"] == "protein"
    assert block(layout, "nutrition")["props"]["protein_g"] == 48.0
    assert layout["actions"]["lead"] == "more_filling"
    assert layout["actions"]["refinements"][0] == "more_filling"


def test_a_light_goal_shows_calories_and_leads_with_lighter():
    layout = compose.pick(blueprint(), {"goal": "weight_loss"})
    assert block(layout, "nutrition")["variant"] == "calories"
    assert layout["actions"]["lead"] == "lighter"


def test_no_nutrition_block_when_the_number_is_unknown():
    bp = blueprint()
    bp["winning_dish"]["macros"] = {"calories": None, "protein_g": None}
    layout = compose.pick(bp, {"goal": "muscle_gain"})
    assert "nutrition" not in ids(layout)
    assert layout["actions"]["lead"] == "more_filling"  # the goal still decides the lead


def test_a_budget_minded_user_gets_the_price_as_the_headline_per_person():
    layout = compose.pick(blueprint(), {"persona": "frugal_student"})
    price = block(layout, "price")
    assert price["variant"] == "headline"
    assert price["props"]["per_person"] == 600
    assert layout["actions"]["lead"] == "cheaper"


def test_asking_for_cheap_reads_as_budget_minded_for_that_request():
    layout = compose.pick(blueprint(), {"cheap_query": True})
    assert block(layout, "price")["variant"] == "headline"
    assert any("you asked for something cheap" in w["text"] for w in layout["why"])


def test_the_budget_slider_at_the_top_makes_the_price_the_headline():
    layout = compose.pick(blueprint({"w_h": 0.2, "w_b": 0.6, "w_t": 0.2}), {})
    assert block(layout, "price")["variant"] == "headline"
    assert block(layout, "reasons")["props"]["order"][0] == "budget"


def test_an_adventurous_persona_leads_with_something_different():
    layout = compose.pick(blueprint(), {"persona": "adventurous_foodie"})
    assert layout["actions"]["lead"] == "different"


def test_the_same_dish_is_composed_differently_for_different_users():
    gym = compose.pick(blueprint(), {"persona": "gym_bro"})
    frugal = compose.pick(blueprint(), {"persona": "frugal_student"})
    assert gym["blocks"] != frugal["blocks"]
    assert gym["actions"]["lead"] != frugal["actions"]["lead"]


# ── Learned signals ──────────────────────────────────────────────────────────────
def test_a_refinement_habit_leads_and_beats_the_goal():
    sig = {"goal": "muscle_gain", "refinements": {"cheaper": 4, "spicier": 2}}
    layout = compose.pick(blueprint(), sig)
    assert layout["actions"]["lead"] == "cheaper"
    habit = next(w for w in layout["why"] if w["block"] == "actions")
    assert habit["source"] == "learned"
    assert "4 times in your last 6" in habit["text"]


def test_an_occasional_refinement_is_not_a_habit():
    layout = compose.pick(blueprint(), {"refinements": {"cheaper": 2, "spicier": 1}})
    assert layout["actions"]["lead"] is None


def test_the_reasons_follow_the_weights():
    layout = compose.pick(blueprint({"w_h": 0.7, "w_b": 0.1, "w_t": 0.2}), {})
    assert block(layout, "reasons")["props"]["order"] == ["health", "taste", "budget", "distance"]
    assert any(w["block"] == "reasons" for w in layout["why"])


def test_choosing_a_dish_before_is_said_on_it_and_marked_among_the_runners():
    sig = {
        "approvals": {
            "d1": {"name": "Chicken Tikka", "count": 3},
            "d2": {"name": "Daal", "count": 2},
        },
        "peers": {"d1": 2, "d3": 1},
    }
    layout = compose.pick(blueprint(), sig)
    assert block(layout, "history")["props"]["lines"] == [
        "You've chosen this 3 times before.",
        "2 people with a taste like yours chose this recently.",
    ]
    assert block(layout, "runners")["props"]["badges"] == {
        "d2": "Your usual",
        "d3": "Liked by similar tastes",
    }


def test_the_learning_block_says_how_much_is_known():
    new = compose.pick(blueprint(), {"signed_in": True, "learned_from": 0})
    tuned = compose.pick(blueprint(), {"signed_in": True, "learned_from": 7})
    returning_guest = compose.pick(blueprint(), {"queries": 2})
    first_guest = compose.pick(blueprint(), {})
    assert block(new, "learning")["variant"] == "new"
    assert block(tuned, "learning")["props"]["text"] == "Tuned by 7 of your choices."
    assert block(returning_guest, "learning")["variant"] == "guest"
    assert "learning" not in ids(first_guest)


# ── The contract ────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("persona", ["balanced", "gym_bro", "frugal_student", "health_nut"])
def test_every_layout_is_well_formed(persona):
    layout = compose.pick(blueprint(), {"persona": persona, "allergens": ["nuts"]})
    assert layout["version"] == compose.VERSION and layout["screen"] == "pick"
    assert len(ids(layout)) == len(set(ids(layout)))
    assert all(b["slot"] in compose.SLOTS for b in layout["blocks"])
    assert sorted(layout["actions"]["refinements"]) == sorted(CRITIQUES)
    assert all({"text", "source", "block"} <= set(w) for w in layout["why"])


def test_a_layout_that_cannot_be_composed_falls_back_to_none(monkeypatch):
    monkeypatch.setattr(compose, "pick", lambda *_: 1 / 0)
    monkeypatch.setattr("tier_1.contracts.session_store.load_contract", lambda *_: {}, raising=True)
    assert compose.pick_for_session("s", blueprint()) is None


# ── Signals ───────────────────────────────────────────────────────────────────
def test_signals_count_refinements_and_approvals_from_history():
    history = [
        event("refined", "d1", "cheaper"),
        event("refined", "d2", "cheaper"),
        event("refined", "d2", "milder"),
        event("approved", "d1"),
        event("approved", "d1"),
        event("query"),
        event("rejected", "d3"),
    ]
    intent = {"raw_input": "something cheap", "allergens_pruned": ["nuts"], "is_halal": True}
    s = signals.gather(None, history, intent, {"persona": "balanced", "peers": {"d9": 1}})
    assert s["refinements"] == {"cheaper": 2, "milder": 1}
    assert s["approvals"] == {"d1": {"name": "d1", "count": 2}}
    assert s["queries"] == 1
    assert s["cheap_query"] is True
    assert s["signed_in"] is False and s["dietary"] is None
    assert s["allergens"] == ["nuts"] and s["halal"] is True
    assert s["peers"] == {"d9": 1}


def test_signals_carry_a_signed_in_users_saved_rules_and_learning():
    profile = SimpleNamespace(dietary=DietaryProfile(allergies=["dairy"], diet="vegan"))
    context = {"persona": "gym_bro", "goal": "muscle_gain", "learned_from": 5}
    s = signals.gather(profile, [], {"raw_input": "dinner"}, context)
    assert s["signed_in"] is True
    assert s["dietary"] == {"allergies": ["dairy"], "diet": "vegan", "halal_only": False}
    assert (s["goal"], s["persona"], s["learned_from"]) == ("muscle_gain", "gym_bro", 5)
    assert s["cheap_query"] is False
