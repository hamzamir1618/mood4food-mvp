"""
Phase 3 decision core (tier_2/scoring.py). Pure: no database, network or clock.
"""

import random
from dataclasses import replace

import pytest

from tier_2 import scoring
from tier_2.scoring import build_preferences, rank, score_dish, traces

BALANCED = build_preferences({})  # balanced persona, no craving, no budget


def dish(**overrides) -> dict:
    base = {
        "dish_id": "d1",
        "name": "Dish",
        "category": "desi_traditional",
        "price_pkr": 800.0,
        "price_status": "trusted",
        "taste_source": "original",
        "review_status": "human_confirmed",
        "nutrition_confidence": "high",
        "macros": {"calories": 600.0, "protein_g": 30.0, "carbs_g": 60.0, "fat_g": 25.0},
        "taste_profile": {
            "sweet": 0.1,
            "salty": 0.5,
            "sour": 0.1,
            "bitter": 0.0,
            "umami": 0.6,
            "spice": 0.5,
        },
        "ingredients": ["chicken"],
    }
    return {**base, **overrides}


# ── Taste ────────────────────────────────────────────────────────────────────


def test_taste_measures_intensity_not_just_direction():
    # Cosine similarity scored both of these 0.9234 against a sweet craving.
    p = build_preferences({"mood_vector": {"sweet": 1.0}})
    intense = scoring.taste_term(dish(taste_profile={"sweet": 1.0, "salty": 0.1}), p)
    faint = scoring.taste_term(dish(taste_profile={"sweet": 0.1, "salty": 0.01}), p)
    assert intense.utility > faint.utility + 0.3
    assert "strongly sweet" in intense.sentence and "barely sweet" in faint.sentence


def test_a_dish_matching_the_usual_taste_exactly_scores_one():
    p = build_preferences({})
    assert scoring.taste_term(dish(taste_profile=dict(p.taste)), p).utility == pytest.approx(1.0)


# ── Budget ───────────────────────────────────────────────────────────────────


def test_a_price_within_the_limit_scores_full_and_says_so():
    t = scoring.budget_term(dish(price_pkr=800), build_preferences({"budget_max_pkr": 1000}))
    assert t.utility == 1.0
    assert t.sentence == "Rs 800, within your Rs 1,000 limit."


def test_a_much_cheaper_dish_is_fine_but_not_preferred():
    t = scoring.budget_term(dish(price_pkr=100), build_preferences({"budget_max_pkr": 1000}))
    assert scoring.CHEAP_FLOOR < t.utility < 1.0
    assert "well under your Rs 1,000 limit" in t.sentence


# ── Wording, the Double rule and the summary ─────────────────────────────────

KARAHI = {"calories": 890.3, "protein_g": 59.7, "carbs_g": 7.1, "fat_g": 69.2}
SPICY_UNDER_1500 = {"mood_vector": {"spice": 0.8}, "budget_max_pkr": 1500}


def test_reason_sentences_use_no_semicolons_or_colon_chains():
    for goal in ("balanced", "muscle_gain", "weight_loss", "light"):
        sentence = scoring.health_term(dish(macros=KARAHI), goal).sentence
        assert ";" not in sentence and ":" not in sentence, sentence
    scored = score_dish(dish(macros=KARAHI, price_pkr=1400), build_preferences(SPICY_UNDER_1500))
    for term in ("taste", "budget", "health"):
        assert ";" not in scored["reasons"][term] and ":" not in scored["reasons"][term]


def test_a_split_mostly_from_fat_is_heavy_on_fat_not_light_on_carbs():
    assert scoring.health_term(dish(macros=KARAHI), "balanced").sentence == (
        "About 890 kcal, with 70% of it from fat, 27% from protein and 3% from carbs. Heavy on fat."
    )


def test_a_double_for_one_counts_both_servings():
    double = dish(
        serves_source="double",
        serves_min=2,
        serves_max=2,
        macros={"calories": 315.4, "protein_g": 19.6, "carbs_g": 30.0, "fat_g": 12.0},
    )
    alone = build_preferences({})
    pair = replace(alone, party_size=2)
    assert scoring.portions(double, 1) == 2.0 and scoring.portions(double, 2) == 1.0
    assert scoring.portions(dish(serves_min=4, serves_max=4), 1) == 1.0  # a platter is shared
    assert "About 631 kcal" in score_dish(double, alone)["reasons"]["health"]
    assert "both servings" in score_dish(double, alone)["reasons"]["health"]
    assert "About 315 kcal" in score_dish(double, pair)["reasons"]["health"]
    diet = replace(alone, goal="weight_loss")
    alone_score = score_dish(double, diet)["u_health"]
    assert alone_score < score_dish(double, replace(diet, party_size=2))["u_health"]


def test_the_summary_gives_the_strongest_points_then_one_caveat():
    karahi = dish(
        macros=KARAHI,
        price_pkr=1400,
        taste_profile={"sweet": 0.1, "salty": 0.5, "sour": 0.1, "umami": 0.6, "spice": 0.8},
    )
    assert score_dish(karahi, build_preferences(SPICY_UNDER_1500))["summary"] == (
        "It's properly spicy, as you asked, and comes in Rs 100 under your limit. "
        "It's also rich, at around 890 kcal and mostly fat."
    )


def test_the_summary_leaves_out_what_the_data_cannot_support():
    guessed = dish(price_pkr=1400, taste_source="global_prior", macros={})
    summary = score_dish(guessed, build_preferences({"budget_max_pkr": 1500}))["summary"]
    assert summary == "It comes in Rs 100 under your limit."


def test_a_usual_spend_sets_a_band_that_dearer_dishes_fall_out_of():
    p = build_preferences({}, {"typical_spend": 1000})
    assert scoring.budget_term(dish(price_pkr=1100), p).utility == 1.0
    assert scoring.budget_term(dish(price_pkr=1800), p).utility == pytest.approx(0.5)


def test_with_no_budget_only_dearer_than_typical_dishes_lose_and_price_counts_less():
    prices = {"side": 30, "typical": 1000, "dear": 5000}
    options = [dish(dish_id=k, name=k, price_pkr=v) for k, v in prices.items()]
    scored = {s["dish_id"]: s for s in rank(options, BALANCED)}
    assert scored["side"]["u_budget"] == scored["typical"]["u_budget"] == 1.0  # no prize for cheap
    assert scored["dear"]["u_budget"] == 0.0
    assert scored["side"]["confidence"]["budget"] == scoring.NO_BUDGET_CONFIDENCE
    assert "No budget was given" in scored["dear"]["reasons"]["budget"]


def test_the_frugal_persona_prefers_the_cheaper_dish_even_within_a_budget():
    p = build_preferences({"budget_max_pkr": 1000}, persona="frugal_student")
    ranked = rank(
        [dish(dish_id="a", name="A", price_pkr=900), dish(dish_id="b", name="B", price_pkr=400)], p
    )
    assert ranked[0]["dish_id"] == "b"
    assert ranked[0]["confidence"]["budget"] == 1.0


def test_a_shared_platter_is_priced_per_person():
    p = replace(build_preferences({"budget_max_pkr": 1000}), party_size=4)
    t = scoring.budget_term(dish(price_pkr=3200, serves_min=4, serves_max=4), p)
    assert "Rs 800 each for 4" in t.sentence and t.utility == 1.0


def test_an_unchecked_price_counts_less_and_says_so():
    p = build_preferences({"budget_max_pkr": 1000})
    t = scoring.budget_term(dish(price_status="unverified"), p)
    assert t.confidence == scoring.PRICE_STATUS_CONFIDENCE["unverified"]
    assert "couldn't be checked" in t.sentence


# ── Health ───────────────────────────────────────────────────────────────────


def test_muscle_gain_prefers_protein_density():
    lean = dish(macros={"calories": 500, "protein_g": 45, "carbs_g": 40, "fat_g": 15})
    heavy = dish(macros={"calories": 900, "protein_g": 15, "carbs_g": 100, "fat_g": 45})
    assert (
        scoring.health_term(lean, "muscle_gain").utility
        > scoring.health_term(heavy, "muscle_gain").utility
    )
    assert "9.0 g per 100 kcal" in scoring.health_term(lean, "muscle_gain").sentence


def test_weight_loss_prefers_fewer_calories():
    light = dish(macros={"calories": 350, "protein_g": 25, "carbs_g": 30, "fat_g": 10})
    rich = dish(macros={"calories": 950, "protein_g": 25, "carbs_g": 90, "fat_g": 50})
    assert (
        scoring.health_term(light, "weight_loss").utility
        > scoring.health_term(rich, "weight_loss").utility
    )


def test_missing_nutrition_is_unknown_not_zero():
    unknown = dish(macros={"calories": None, "protein_g": None}, nutrition_confidence="none")
    assert scoring.health_term(unknown, "balanced").confidence == 0.0
    zero_kcal = dish(macros={"calories": 0, "protein_g": 0})  # no division by zero
    assert scoring.health_term(zero_kcal, "balanced").confidence == 0.0


# ── Aggregation, novelty, context ────────────────────────────────────────────


def test_the_total_shrinks_each_term_toward_neutral_by_its_uncertainty():
    p = build_preferences({"budget_max_pkr": 1000})
    s = score_dish(dish(price_status="unverified"), p)  # budget confidence 0.6
    w = {
        "health": p.weights["w_health"],
        "budget": p.weights["w_budget"],
        "taste": p.weights["w_taste"],
    }
    expected = sum(
        w[k]
        * (s["confidence"][k] * s[f"u_{k}"] + (1 - s["confidence"][k]) * scoring.NEUTRAL_UTILITY)
        for k in w
    )
    # context applies too: a main dish when a meal is expected, full confidence, fit 1
    expected += scoring.CONTEXT_WEIGHT * s["u_context"]
    expected /= sum(w.values()) + scoring.CONTEXT_WEIGHT
    assert s["u_context"] == 1.0
    assert s["u_total"] == pytest.approx(expected, abs=1e-5)


def test_a_dish_that_cant_be_assessed_counts_as_average_there():
    unknown = score_dish(dish(macros={}, nutrition_confidence="none"), BALANCED)
    assert unknown["u_health"] is None
    assert "counts as average" in unknown["reasons"]["coverage"]
    good = score_dish(
        dish(macros={"calories": 600, "protein_g": 35, "carbs_g": 70, "fat_g": 18}), BALANCED
    )
    poor = score_dish(
        dish(macros={"calories": 1400, "protein_g": 5, "carbs_g": 20, "fat_g": 140}), BALANCED
    )
    assert poor["u_total"] < unknown["u_total"] < good["u_total"]


def test_a_recently_passed_over_dish_ranks_lower_and_says_why():
    fresh = score_dish(dish(), BALANCED)["u_total"]
    history = [{"dish_uid": "d1", "kind": "rejected", "days_ago": 1.0}]
    again = score_dish(dish(), replace(BALANCED, history=history))
    assert again["u_total"] == pytest.approx(fresh * scoring.NOVELTY_REJECTED, abs=1e-5)
    assert "passed on this recently" in again["reasons"]["novelty"]


def test_a_meal_the_query_names_counts_more_than_the_default_expectation():
    main, snack = dish(), dish(dish_id="s", name="Snack", category="cafe_bakery")
    gap = score_dish(main, BALANCED)["u_total"] - score_dish(snack, BALANCED)["u_total"]
    lunch = build_preferences({"raw_input": "cheap lunch"})
    gap_lunch = score_dish(main, lunch)["u_total"] - score_dish(snack, lunch)["u_total"]
    assert 0 < gap < gap_lunch


def test_context_prefers_a_meal_and_only_speaks_when_something_applies():
    assert scoring.context_term(dish(), BALANCED).sentence == ""  # a main dish, nothing special
    snack = scoring.context_term(dish(category="cafe_bakery"), BALANCED)
    assert snack.utility == scoring.SNACK_FIT and "snack or dessert" in snack.sentence

    sweet = build_preferences({"mood_vector": {"sweet": 1.0}})
    assert scoring.context_term(dish(category="cafe_bakery"), sweet).applies is False

    morning = replace(BALANCED, hour=8)
    assert scoring.context_term(dish(category="cafe_bakery"), morning).utility == 1.0
    assert scoring.context_term(dish(), morning).utility == 0.5

    dinner = build_preferences({"raw_input": "vegetarian dinner"})
    assert "You asked for dinner" in scoring.context_term(dish(), dinner).sentence


def test_every_utility_stays_between_zero_and_one():
    rng = random.Random(0)
    for _ in range(200):
        d = dish(
            price_pkr=rng.uniform(0, 20000),
            macros={
                "calories": rng.uniform(1, 3000),
                "protein_g": rng.uniform(0, 150),
                "carbs_g": rng.uniform(0, 300),
                "fat_g": rng.uniform(0, 150),
            },
            taste_profile={k: rng.random() for k in scoring.TASTE_DIMS},
        )
        intent = {
            "budget_max_pkr": rng.choice([None, 500, 3000]),
            "mood_vector": {"spice": rng.random()},
        }
        for goal in ("balanced", "muscle_gain", "weight_loss", "light"):
            p = replace(
                build_preferences(intent),
                goal=goal,
                hour=rng.randrange(24),
                temperature_c=rng.uniform(0, 45),
            )
            s = score_dish(d, p)
            for k in ("u_health", "u_budget", "u_taste", "u_context", "u_total"):
                assert s[k] is None or 0.0 <= s[k] <= 1.0


# ── Preferences and traces ───────────────────────────────────────────────────


def test_preferences_come_from_the_query_the_persona_and_the_saved_profile():
    p = build_preferences(
        {"mood_vector": {"sweet": 0.9, "salty": 0.0}, "budget_max_pkr": 999999}, persona="gym_bro"
    )
    assert p.craved == {"sweet": 0.9}
    assert p.budget_ceiling is None  # Tier 1's "no budget" sentinel
    assert p.goal == "muscle_gain"
    assert sum(p.weights.values()) == pytest.approx(1.0)
    assert build_preferences({}, {"goal": "light"}, persona="gym_bro").goal == "light"


def test_traces_keep_the_shape_the_frontend_reads():
    p = build_preferences({"budget_max_pkr": 1000})
    lines = traces(rank([dish()], p), p)
    i = next(i for i, line in enumerate(lines) if "Dish Candidate Breakdown" in line)
    agents = [line.split(" Agent:")[0].strip() for line in lines[i + 1 : i + 4]]
    assert agents == ["- Health", "- Budget", "- Taste"]
    assert all(" (raw:" in line for line in lines[i + 1 : i + 4])


# ── What Phase 4 learning feeds in ───────────────────────────────────────────


def test_learned_importance_weights_the_taste_distance():
    flat = build_preferences({})
    focused = build_preferences(
        {}, {"importance": {**{d: 0.5 for d in scoring.TASTE_DIMS}, "spice": 2.0}}
    )
    off_on_spice = dish(taste_profile={**flat.taste, "spice": 1.0})
    assert (
        scoring.taste_term(off_on_spice, focused).utility
        < scoring.taste_term(off_on_spice, flat).utility
    )


def test_dishes_people_with_similar_tastes_approved_get_a_small_named_pull():
    p = build_preferences({}, {"peers": {"d1": 2}})
    pulled, plain = score_dish(dish(), p), score_dish(dish(dish_id="d2"), p)
    assert plain["u_total"] < pulled["u_total"] <= 1.0
    gap = 1 - plain["u_total"]
    assert pulled["u_total"] - plain["u_total"] == pytest.approx(
        gap * scoring.PEER_PULL * 2 / scoring.PEER_SATURATION, abs=1e-5
    )
    assert "2 people with tastes like yours" in pulled["reasons"]["peers"]


def test_learned_weights_apply_unless_the_sliders_or_a_chosen_persona_say_otherwise():
    learned = {"w_health": 0.1, "w_budget": 0.1, "w_taste": 0.8}
    assert build_preferences({}, {"weights": learned}).weights["w_taste"] == pytest.approx(0.8)
    chosen = build_preferences({}, {"weights": learned}, persona="gym_bro")
    assert chosen.weights["w_health"] == pytest.approx(0.8)
    sliders = {"w_health": 1, "w_budget": 0, "w_taste": 0}
    assert build_preferences({}, {"weights": learned}, sliders).weights["w_health"] == 1.0
