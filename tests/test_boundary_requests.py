"""
Requests the menus can't meet in full, end to end through /chat: the closest dishes first, the
other ways to read the request, the walkthrough, conflicts with the user's own rules, and requests
that aren't about food at all.

Everything real runs — the keyword extractor, Tier 1's relaxation, the closeness ranking, Tier 2,
the trade-offs, the walkthrough and the layout. Only the graph is replaced, by a small menu that
the query is applied to the way PRUNE_CYPHER applies it: rules, limit, and what was asked for.
"""

import fakeredis
import pytest
from fastapi.testclient import TestClient

from tier_1.keyword_extractor import KeywordExtractorImpl
from tier_1.symbolic_anchoring import exclusion_terms, requested_match


def dish(name, price, category, spice=0.0, sweet=0.0, ingredients=(), vegan=False, kcal=450.0):
    return {
        "dish_id": name.lower().replace(" ", "-").replace("&", "and"),
        "name": name,
        "restaurant_name": f"{name.split()[0]} House",
        "category": category,
        "price_pkr": float(price),
        "price_status": "trusted",
        "taste_source": "original",
        "nutrition_confidence": "high",
        "macros": {"calories": kcal, "protein_g": 25.0, "carbs_g": 45.0, "fat_g": 18.0},
        "taste_profile": {
            "sweet": sweet,
            "salty": 0.4,
            "sour": 0.1,
            "bitter": 0.0,
            "umami": 0.5,
            "spice": spice,
        },
        "ingredients": list(ingredients),
        "allergens": [],
        "is_vegan": vegan,
        "serves_min": 1,
        "serves_max": 1,
    }


MENU = [
    dish("Hot & Sour Soup", 195, "chinese_asian", spice=0.6, ingredients=["chicken", "tofu"]),
    dish("Chicken Corn Soup", 175, "chinese_asian", ingredients=["chicken", "corn"]),
    dish("Lahori Channay", 175, "desi_traditional", spice=0.5, vegan=True),
    dish("Masala Fries", 160, "fast_food", spice=0.7, vegan=True),
    dish("Badami Kulfi", 149, "cafe_bakery", sweet=0.8),
    dish("Pogaca", 150, "cafe_bakery"),
    dish("Namkeen Chicken Tikka", 255, "desi_traditional", spice=0.5, ingredients=["chicken"]),
    dish("Chicken Tandoori Tikka", 275, "desi_traditional", spice=0.5, ingredients=["chicken"]),
    dish("Chicken Tikka Burger", 330, "fast_food", spice=0.5, ingredients=["chicken", "bun"]),
    dish("Chicken Karahi", 1000, "desi_traditional", spice=0.7, ingredients=["chicken"]),
    dish("Mutton Handi", 900, "desi_traditional", spice=0.5, ingredients=["mutton"]),
    dish("Daal Maharani", 625, "desi_traditional", spice=0.3, ingredients=["lentils"], vegan=True),
    dish("Vegetable Rolls", 600, "sandwich", vegan=True),
    dish("Masala Fried Rice", 650, "chinese_asian", spice=0.4, ingredients=["rice"], vegan=True),
    dish("Sindhi Biryani Half", 525, "desi_traditional", spice=0.6, ingredients=["rice"]),
    dish("Chicken Biryani", 700, "desi_traditional", spice=0.6, ingredients=["chicken", "rice"]),
    dish("Mutton Biryani", 795, "desi_traditional", spice=0.6, ingredients=["mutton", "rice"]),
    # What "not sweet and doesn't have onions" must stay clear of
    dish("Fried Beef With Onions", 900, "chinese_asian", spice=0.3, ingredients=["beef", "onion"]),
    dish("Onion Rings Platter", 850, "fast_food", ingredients=["onion", "flour"]),
    dish("Gulab Jamun", 300, "cafe_bakery", sweet=0.9, ingredients=["milk", "sugar"]),
]


def query(allergens, budget, category="", vegan=False, veg=False, is_halal=False, driver=None):
    """The menu, filtered as PRUNE_CYPHER filters the graph."""
    match = requested_match(category)
    vegan = vegan or "vegan" in [a.lower() for a in allergens]
    _, excluded = exclusion_terms(allergens)
    out = []
    for d in MENU:
        if d["price_pkr"] > budget or (vegan and not d["is_vegan"]):
            continue
        if set(excluded) & set(d["ingredients"]):
            continue
        if category and not (
            match["category_key"] in d["category"]
            or (match["match_names"] and category in d["name"].lower())
            or set(match["preferred_ingredients"]) & set(d["ingredients"])
        ):
            continue
        out.append({**d, "ingredients": list(d["ingredients"])})
    return out


@pytest.fixture
def chat(monkeypatch):
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("tier_1.contracts.session_store.get_redis", lambda: fake_redis)
    calls = {"extract": 0}

    def ingest(**kwargs):
        calls["extract"] += 1
        return KeywordExtractorImpl().extract(kwargs.get("raw_input") or "").model_dump()

    monkeypatch.setattr("tier_1.multi_modal_ingestion.run_ingestion_pipeline", ingest)
    monkeypatch.setattr("tier_1.symbolic_anchoring.query_safe_candidates", query)
    monkeypatch.setattr(
        "tier_1.symbolic_anchoring.write_candidate_evaluation", lambda *a, **k: None
    )
    monkeypatch.setattr("tier_2.trade_offs.recommendable", lambda: len(MENU))
    monkeypatch.setattr("tier_3.fulfillment_engine.enrich_blueprint", lambda bp: dict(bp))
    monkeypatch.setattr("tier_2.context.weather", lambda: None, raising=False)
    from orchestrator import app

    client = TestClient(app)
    client.calls = calls
    return client


def say(chat, **turn) -> dict:
    reply = chat.post("/chat", json=turn)
    assert reply.status_code == 200, reply.text
    return reply.json()


def block(reply: dict, kind: str) -> dict | None:
    blocks = (reply["recommendation"].get("layout") or {}).get("blocks") or []
    return next((b for b in blocks if b["type"] == kind), None)


def until_pick(chat, text: str) -> dict:
    reply = say(chat, text=text)
    while reply["type"] == "question" and reply["question"]["id"] != "tradeoff":
        reply = say(chat, skip=True)
    return reply


# ── Close, rather than anything ──────────────────────────────────────────────
def test_nothing_quite_fits_so_the_closest_dish_wins_rather_than_whatever_scores_best(chat):
    """The reported failure: "spicy chicken under 200" was won by a kulfi."""
    reply = until_pick(chat, "spicy chicken under 200")
    rec = reply["recommendation"]
    assert rec["winning_dish"]["name"] == "Hot & Sour Soup"  # chicken inside, and spicy
    # It outranks spicy dishes with no chicken that score better on their own
    assert {"Lahori Channay", "Masala Fries"} <= {c["name"] for c in rec["top_candidates"]}
    assert rec["top_candidates"][0]["closeness"] > rec["top_candidates"][1]["closeness"]
    assert "Nothing at Rs 200 or less is spicy chicken" in rec["relaxation_notice"]
    assert all(c["price_pkr"] <= 200 for c in rec["top_candidates"])  # the limit never moved


def test_the_pick_says_which_parts_of_the_request_it_meets(chat):
    winner = until_pick(chat, "spicy chicken under 200")["recommendation"]["winning_dish"]
    said = {m["words"] for m in winner["meets"]}
    assert said == {"spicy", "chicken inside"}


def test_it_offers_the_other_ways_to_read_the_request_each_with_its_dish(chat):
    options = block(until_pick(chat, "spicy chicken under 200"), "tradeoffs")["props"]["options"]
    by_id = {o["id"]: o for o in options}
    # Spend more: enough for three spicy chicken dishes, rounded to a price a person would say
    assert by_id["budget"]["label"] == "Spend up to Rs 350"
    assert by_id["budget"]["dish"]["price_pkr"] <= 350
    assert "chicken" in by_id["budget"]["dish"]["name"].lower()
    # Keep the limit, forget the spice: chicken under Rs 200
    assert by_id["taste:spice"]["dish"]["name"] == "Chicken Corn Soup"


def test_choosing_an_option_runs_the_request_again_with_that_one_thing_changed(chat):
    until_pick(chat, "spicy chicken under 200")
    extracted = chat.calls["extract"]
    reply = say(chat, trade_off="budget")
    rec = reply["recommendation"]
    assert "chicken" in rec["winning_dish"]["name"].lower()
    assert 200 < rec["winning_dish"]["price_pkr"] <= 350
    assert all(c["price_pkr"] <= 350 for c in rec["top_candidates"])
    assert chat.calls["extract"] == extracted  # the request isn't read twice
    steps = [s["text"] for s in block(reply, "walkthrough")["props"]["steps"]]
    assert "Then you chose: Spend up to Rs 350." in steps


def test_an_option_not_on_offer_cannot_be_taken(chat):
    until_pick(chat, "spicy chicken under 200")
    assert chat.post("/chat", json={"trade_off": "vegan"}).status_code == 409


# ── Nothing fits at all ──────────────────────────────────────────────────────
def test_when_nothing_fits_it_asks_what_to_change_instead_of_giving_up(chat):
    """The reported failure: "biryani under 50" went straight to "nothing fits"."""
    reply = say(chat, text="biryani under 50")
    assert reply["type"] == "question"
    question = reply["question"]
    assert question["id"] == "tradeoff"
    assert question["why"] == "Nothing on the menus I hold costs Rs 50 or less."
    # The only thing to change is the limit: nothing at all costs Rs 50, so "forget biryani"
    # would find nothing either, and is not offered.
    labels = [c["label"] for c in question["chips"]]
    assert len(labels) == 1 and labels[0].startswith("Spend up to Rs 800: ")
    reply = say(chat, answer={"question": "tradeoff", "value": "budget"})
    winner = reply["recommendation"]["winning_dish"]
    assert "biryani" in winner["name"].lower() and winner["price_pkr"] <= 800


# ── The user's own rules always win ──────────────────────────────────────────
def test_a_food_the_users_own_rules_forbid_is_set_aside_and_said(chat):
    """The reported failure: "vegan chicken karahi" gave salad and pakora with no account."""
    rec = until_pick(chat, "vegan chicken karahi")["recommendation"]
    assert rec["relaxation_notice"].startswith(
        "Chicken isn't vegan, and your rules come first, so I've left chicken out."
    )
    assert all(
        next(d for d in MENU if d["dish_id"] == c["dish_id"])["is_vegan"]
        for c in rec["top_candidates"]
    )
    # No vegan karahi, so another curry: a daal, not the masala fried rice the word "masala" hid
    assert rec["winning_dish"]["name"] == "Daal Maharani"


def test_no_option_ever_offers_to_drop_a_rule(chat):
    reply = until_pick(chat, "vegan chicken karahi")
    options = (block(reply, "tradeoffs") or {}).get("props", {}).get("options", [])
    assert not any(o["id"] in ("vegan", "vegetarian", "halal") for o in options)
    assert not any(o["id"].startswith("food:chicken") for o in options)


# ── The walkthrough ──────────────────────────────────────────────────────────
def test_the_walkthrough_tells_each_step_with_the_counts_the_pipeline_saw(chat):
    steps = block(until_pick(chat, "spicy chicken under 200"), "walkthrough")["props"]["steps"]
    texts = [s["text"] for s in steps]
    assert texts[0] == "You said “spicy chicken under 200”."
    assert "I read that as: spicy, chicken and Rs 200 or less." in texts
    under = sum(1 for d in MENU if d["price_pkr"] <= 200)
    assert f"Rs 200 or less leaves {under} of them." in texts
    assert any(t.startswith("Hot & Sour Soup came out on top") for t in texts)


def test_a_request_met_in_full_offers_no_trade_and_ranks_as_it_always_did(chat):
    reply = until_pick(chat, "chicken karahi")
    rec = reply["recommendation"]
    assert rec["winning_dish"]["name"] == "Chicken Karahi"
    assert block(reply, "tradeoffs") is None
    assert all(c["closeness"] == 0 for c in rec["top_candidates"])


# ── Not food ─────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("text", ["(", "what is the capital of france", "asdfgh", "hello"])
def test_a_request_that_isnt_about_food_is_answered_before_anything_runs(chat, text):
    """The reported failure: a lone "(" went on to "What are you in the mood for?"."""
    reply = say(chat, text=text)
    assert reply["type"] == "not_food"
    assert reply["reply"] and reply["examples"]
    assert chat.calls["extract"] == 0  # the extractor, the only LLM call, never ran


# ── What the request leaves out ──────────────────────────────────────────────
def test_onions_left_out_are_left_out_and_not_sweet_means_not_sweet(chat):
    """
    The reported failure: "something that's not sweet and doesn't have onions" was won by fried
    beef with onions, and every dish behind it had onions in its name.
    """
    reply = until_pick(chat, "something thats not sweet and doesn't have onions")
    rec = reply["recommendation"]
    for c in rec["top_candidates"]:
        menu = next(d for d in MENU if d["dish_id"] == c["dish_id"])
        assert "onion" not in c["name"].lower() and "onion" not in menu["ingredients"], c["name"]
        assert menu["taste_profile"]["sweet"] < 0.4, c["name"]
    steps = [s["text"] for s in block(reply, "walkthrough")["props"]["steps"]]
    assert "I read that as: not sweet and no onion." in steps
