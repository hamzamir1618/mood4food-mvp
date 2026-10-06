"""
Taste in fifteen seconds (accounts/taste_start.py): six dishes, tap what you'd eat.

The rules are pure, so most of this needs no database: dishes are made up here, with the
sparse flavour vectors the real data has — mostly zeroes with a couple of strong values, which
is exactly what an earlier version of the fold read as agreement and announced as a dislike.
"""

import pytest

from accounts import taste_start
from accounts.models import TASTE_DIMS, TasteModel

FLAVOURS = {
    "brownie": {"sweet": 0.9, "bitter": 0.6},
    "spicy beef": {"umami": 0.8, "spice": 0.8},
    "lemon rice": {"sour": 0.8},
    "sweet sour beef": {"sweet": 0.8, "umami": 0.8},
    "burger": {"salty": 0.5, "umami": 0.7},
    "masala": {"spice": 0.6},
}


def dish(name: str, kitchen: str | None = None) -> dict:
    return {
        "dish_id": name.replace(" ", "-"),
        "name": name.title(),
        "restaurant_name": kitchen or f"{name} house",
        "category": "desi_traditional",
        **{d: 0.0 for d in TASTE_DIMS},
        **FLAVOURS[name],
    }


SIX = [dish(n) for n in FLAVOURS]


def told_about(*names: str) -> dict:
    return taste_start.fold([dish(n) for n in names], SIX)


# ── Which six to ask about ───────────────────────────────────────────────────
def test_the_six_are_spread_out_rather_than_six_of_a_kind():
    """Six dishes that taste alike would ask the same question six times."""
    alike = [dish("spicy beef", f"kitchen {i}") | {"dish_id": f"beef-{i}"} for i in range(6)]
    picked = taste_start.spread_out(alike + SIX, how_many=3)
    tastes = [tuple(round(float(d[t]), 2) for t in TASTE_DIMS) for d in picked]
    assert len(set(tastes)) == 3, tastes


def test_no_two_come_from_the_same_kitchen():
    same_house = [dish(n, "one kitchen") for n in FLAVOURS]
    picked = taste_start.spread_out(same_house + SIX)
    kitchens = [d["restaurant_name"] for d in picked]
    assert kitchens.count("one kitchen") == 1, kitchens


def test_no_two_are_shown_under_the_same_photograph():
    """Two cards carrying one picture ask the reader to choose between the same thing twice."""
    picked = taste_start.spread_out(SIX * 2, looks=lambda d: d["name"])
    assert len({d["name"] for d in picked}) == len(picked)


def test_the_same_six_come_back_every_time():
    assert taste_start.spread_out(SIX) == taste_start.spread_out(list(reversed(SIX)))


# ── What the taps mean ───────────────────────────────────────────────────────
def test_the_taste_is_the_average_of_what_was_tapped():
    told = told_about("spicy beef", "masala")
    assert told["vector"]["spice"] == pytest.approx(0.7)
    assert told["vector"]["umami"] == pytest.approx(0.4)


def test_a_flavour_nobody_could_have_chosen_earns_no_confidence():
    """
    Recorded flavours are sparse. Three picks all sitting at zero sourness is not agreement
    that the reader dislikes sour — it is six dishes that mostly had none. Reading it as a
    dislike is how the app would come to announce a preference nobody expressed.
    """
    told = told_about("spicy beef", "masala")
    assert told["confidence"]["spice"] > told["confidence"]["bitter"]
    flat = taste_start.fold([dish("masala")], [dish("masala"), dish("masala")])
    assert all(c == 0 for c in flat["confidence"].values())


def test_it_names_what_they_chose_not_what_the_menu_happened_to_lack():
    assert "spicy" in taste_start.in_words(told_about("spicy beef", "masala"))
    sweet = taste_start.in_words(told_about("brownie", "sweet sour beef"))
    assert "sweet" in sweet and "steer clear of" in sweet


def test_picks_that_look_like_the_menu_say_so_rather_than_inventing_a_taste():
    said = taste_start.in_words(taste_start.fold(SIX, SIX))
    assert "learn as you go" in said


def test_a_flavour_they_leaned_on_counts_for_more_in_the_scoring():
    """Confidence never reaches the scorer; importance does, so the lean has to land there."""
    weights = taste_start.weighting(told_about("spicy beef", "masala"))
    assert weights["spice"] > weights["bitter"]
    assert min(weights.values()) >= taste_start.IMPORTANCE_RANGE[0]
    assert max(weights.values()) <= taste_start.IMPORTANCE_RANGE[1]
    assert sum(weights.values()) == pytest.approx(len(TASTE_DIMS), abs=0.5)


# ── What it does to the saved taste ──────────────────────────────────────────
def test_taps_give_the_taste_something_to_go_on():
    taste = TasteModel.from_persona("balanced")
    assert not taste.has_evidence()  # which is why the flavour term sits out
    assert taste_start.started(taste, told_about("spicy beef", "masala")).has_evidence()


def test_taps_are_not_an_approval():
    """`updates` drives the learning rate, so a tap must not spend a first approval's step."""
    taste = TasteModel.from_persona("balanced")
    assert taste_start.started(taste, told_about("brownie", "burger")).updates == taste.updates


def test_a_value_the_user_set_by_hand_is_never_overwritten_by_a_tap():
    taste = TasteModel.from_persona("balanced")
    by_hand = taste.model_copy(
        update={
            "vector": {**taste.vector, "spice": 0.05},
            "confidence": {**taste.confidence, "spice": 1.0},
        }
    )
    started = taste_start.started(by_hand, told_about("spicy beef", "masala"))
    assert started.vector["spice"] == 0.05
    assert started.confidence["spice"] == 1.0


def test_importance_learned_from_approvals_outranks_the_taps():
    taste = TasteModel.from_persona("balanced").model_copy(
        update={"updates": 4, "importance": {d: 1.0 for d in TASTE_DIMS}}
    )
    started = taste_start.started(taste, told_about("spicy beef", "masala"))
    assert started.importance == taste.importance
