"""
The dataset label (ui/dataset_label.py, ui/build_facts.py): what the whole collection holds.

Two things are worth guarding. That the label never prints a figure it did not count — a page
about honesty cannot fall back to a number typed in by hand — and that the before-values
written into build_facts.py still match the build report, so a rebuild that moves one fails
here instead of leaving a stale claim on screen.

Most of it runs without a database: `counted` is replaced with a fixed count.
"""

import re
from pathlib import Path

import pytest

from ui import build_facts, dataset_label

REPORT = Path(__file__).resolve().parent.parent / "data" / "build_report.md"

COUNTED = {
    "dishes": 2545,
    "restaurants": 48,
    "quarantined": 247,
    "recommendable": 1840,
    "allergens_unknown": 52,
    "allergens_unknown_recommendable": 11,
    "with_nutrition": 2493,
    "nutrition_flagged": 3,
    "vegetarian": 843,
    "vegan": 462,
    "with_allergen_tag": 1818,
    "filed_as_other": 25,
    "no_flavour_at_all": 4,
    "breakdowns": {
        "review_status": [
            {"value": "human_confirmed", "count": 1157},
            {"value": "auto_imported", "count": 1150},
        ],
        "price_status": [{"value": "trusted", "count": 1395}],
        "ingredients_basis": [{"value": "named ingredients", "count": 329}],
        "nutrition_confidence": [{"value": "medium", "count": 2322}],
        "taste_source": [{"value": "original", "count": 1314}],
        "serves_source": [{"value": "default", "count": 2194}],
        "quarantine_reason": [{"value": "name truncated by OCR", "count": 13}],
        "category": [{"value": "chinese_asian", "count": 891}],
    },
    "nutrition": {
        "dishes": 1829,
        "median_calories": 640.4,
        "median_fat_share": 0.5,
        "over_three_quarters_fat": 16,
    },
    "allergen_tags": [{"value": "gluten", "count": 956}],
    "located": [{"value": "place", "count": 25}, {"value": "area", "count": 22}],
    "areas": [{"value": "F-7", "count": 7}],
}


@pytest.fixture
def label(monkeypatch):
    monkeypatch.setattr(dataset_label, "counted", lambda *a, **k: COUNTED)
    return dataset_label.label()


def test_the_headline_is_counted_not_written(label):
    figures = {h["of"]: h["figure"] for h in label["headline"]}
    assert figures["dishes"] == "2,545"
    assert figures["confirmed by a person"] == "1,157"
    assert figures["the app will pick from"] == "1,840"
    assert figures["with allergens still unknown"] == "11"


def test_what_changed_puts_a_written_before_against_a_counted_after(label):
    changed = {c["what"]: c for c in label["changed"]}
    calories = changed["Median calories in a serving"]
    assert calories["before"] == "731 kcal"  # the sourcing project's method
    assert calories["after"] == "640 kcal"  # counted from the graph this minute
    assert changed["Dishes carrying any allergen tag"]["after"] == "1,818"
    assert changed["Dishes with no flavour values at all"]["after"] == "0.2%"


def test_every_after_value_resolves_against_what_is_counted(label):
    """A before-value with no counted pair would print half a claim, so it is dropped."""
    assert len(label["changed"]) == len(build_facts.CHANGED)


def test_a_group_carries_the_same_badge_the_dish_panel_gives_it(label):
    rows = {s["id"]: s["rows"] for s in label["sections"]}
    confirmed = next(r for r in rows["review_status"] if r["value"] == "human_confirmed")
    assert (confirmed["badge"], confirmed["tone"]) == ("Person checked", "confirmed")
    assert confirmed["share"] == 45
    unchecked = next(r for r in rows["review_status"] if r["value"] == "auto_imported")
    assert unchecked["tone"] == "unchecked"
    assert rows["quarantine_reason"][0]["tone"] == "unchecked"
    assert rows["allergens"][0]["badge"] == "Worked out"  # never "tested"
    assert rows["located"][0]["badge"] == "Mapped to the door"


def test_a_graph_that_cannot_be_counted_gives_no_label(monkeypatch):
    monkeypatch.setattr(dataset_label, "counted", lambda *a, **k: None)
    assert dataset_label.label() is None


def test_the_endpoint_refuses_to_guess(monkeypatch):
    from fastapi.testclient import TestClient

    from orchestrator import app

    monkeypatch.setattr(dataset_label, "counted", lambda *a, **k: None)
    assert TestClient(app).get("/dataset").status_code == 503


@pytest.mark.skipif(not REPORT.exists(), reason="the build report isn't on this machine")
@pytest.mark.parametrize(
    "what, pattern",
    [
        ("Median calories in a serving", r"731 before"),
        ("Dishes carrying any allergen tag", r"Before, (706) "),
        ("Dishes filed as 'other'", r"was (429)"),
        ("Dishes marked vegan", r"Vegan: \d+ \(was (337)\)"),
    ],
)
def test_the_before_values_still_match_the_build_report(what, pattern):
    """Rebuild the dataset and these must be refreshed; the suite says so rather than the screen."""
    report = REPORT.read_text(encoding="utf-8")
    fact = next(f for f in build_facts.CHANGED if f["what"] == what)
    found = re.search(pattern, report)
    assert found, f"{pattern!r} is no longer in the build report"
    number = found.group(1) if found.groups() else found.group(0).split()[0]
    written = fact["before"]
    assert number in written, f"{what}: the report says {number}, build_facts says {written}"


def test_the_label_is_written_for_someone_who_never_built_it(label):
    """Each group is named as a diner would say it, and the jargon stays in the code."""
    rows = {s["id"]: s["rows"] for s in label["sections"]}
    confirmed = next(r for r in rows["review_status"] if r["value"] == "human_confirmed")
    assert confirmed["label"] == "Checked by a person"
    shown = " ".join(
        [s["title"] + " " + (s.get("note") or "") for s in label["sections"]]
        + [r["label"] for s in label["sections"] for r in s["rows"]]
        + [c["title"] + " " + c["note"] for c in label["changed"]]
        + [label["typical"]["text"], label["calibration"]["plain"], label["calibration"]["result"]]
    ).lower()
    for jargon in (
        "median",
        "fat share",
        "energy from fat",
        "ocr",
        "bootstrap",
        "quarantin",
        "prior",
        "macronutrient",
        "inferred",
    ):
        assert jargon not in shown, jargon


def test_each_change_carries_numbers_for_its_chart(label):
    fat = next(c for c in label["changed"] if c["icon"] == "fat")
    assert fat["before_value"] == 0.68 and 0 < fat["after_value"] < 1
    assert fat["reference"]["value"] == 0.44
