"""
The dataset, counted — a label for the whole collection, the way ui/provenance.py is a label
for one dish.

Everything here is counted from the graph the app is serving, not read from the build report.
The report (data/build_report.md) is the record of one build on one machine, it is not shipped
with the code, and a screen that quoted it would be both blank in production and free to drift
from what is actually on the shelves. Counting the live graph means the label can only ever say
what the app would actually recommend.

The numbers the graph cannot hold — what a figure was *before* the build corrected it, and how
the estimator was calibrated — live in ui/build_facts.py, which is checked against the build
report by tests/test_dataset_label.py whenever that report is present.

One round of small aggregates, cached for the process. Nothing here is on the recommendation
path: the label is its own screen, and a failure returns None so the screen can say the count
is unavailable rather than invent one.
"""

import logging
import time

log = logging.getLogger(__name__)

TTL_SECONDS = 15 * 60  # the graph only changes when someone reseeds it
_CACHE: dict = {"at": 0.0, "facts": None}

# Dishes the app will never pick: drinks and sides are on the menu for A2 ("make it a meal"),
# and quarantined rows are kept on file but never served.
RECOMMENDABLE = "NOT coalesce(d.quarantined, false) AND NOT d.category IN ['beverages', 'add_ons']"

TOTALS = f"""
MATCH (d:Dish)
RETURN count(*) AS dishes,
       count(DISTINCT d.restaurant_name) AS restaurants,
       sum(CASE WHEN coalesce(d.quarantined, false) THEN 1 ELSE 0 END) AS quarantined,
       sum(CASE WHEN {RECOMMENDABLE} THEN 1 ELSE 0 END) AS recommendable,
       sum(CASE WHEN d.allergens_known = false THEN 1 ELSE 0 END) AS allergens_unknown,
       sum(CASE WHEN d.allergens_known = false AND {RECOMMENDABLE} THEN 1 ELSE 0 END)
           AS allergens_unknown_recommendable,
       sum(CASE WHEN d.calories IS NOT NULL THEN 1 ELSE 0 END) AS with_nutrition,
       sum(CASE WHEN d.nutrition_flag IS NOT NULL THEN 1 ELSE 0 END) AS nutrition_flagged,
       sum(CASE WHEN d.is_vegetarian THEN 1 ELSE 0 END) AS vegetarian,
       sum(CASE WHEN d.is_vegan THEN 1 ELSE 0 END) AS vegan,
       sum(CASE WHEN size(coalesce(d.allergens, [])) > 0 THEN 1 ELSE 0 END) AS with_allergen_tag,
       sum(CASE WHEN d.category = 'other' THEN 1 ELSE 0 END) AS filed_as_other,
       // A dish whose flavour is all zeroes has none: the enrichment left it alone deliberately.
       sum(CASE WHEN d.taste_sweet = 0 AND d.taste_salty = 0 AND d.taste_sour = 0
                 AND d.taste_bitter = 0 AND d.taste_umami = 0 AND d.taste_spice = 0
                THEN 1 ELSE 0 END) AS no_flavour_at_all
"""

# field -> the heading its breakdown is printed under
BREAKDOWNS = {
    "review_status": "How each row was read",
    "price_status": "How each price was checked",
    "ingredients_basis": "Where the ingredients came from",
    "nutrition_confidence": "How far the nutrition estimate is trusted",
    "taste_source": "Where the flavour values came from",
    "serves_source": "How many each dish serves",
    "quarantine_reason": "Why a row is kept on file but never served",
    "category": "What kind of dish",
}
BREAKDOWN = """
MATCH (d:Dish) WHERE d.{field} IS NOT NULL
RETURN d.{field} AS value, count(*) AS dishes ORDER BY dishes DESC
"""
# A quarantined row can fail more than one check, and its reasons are stored joined by "; ".
# Counting the strings would print "price under Rs 20; owner discarded the name" as a reason of
# its own, so they are split back into the checks that failed.
REASONS = """
MATCH (d:Dish) WHERE d.quarantine_reason IS NOT NULL
UNWIND split(d.quarantine_reason, '; ') AS reason
RETURN reason AS value, count(*) AS dishes ORDER BY dishes DESC
"""
ALLERGENS = """
MATCH (d:Dish) UNWIND coalesce(d.allergens, []) AS tag
RETURN tag AS value, count(*) AS dishes ORDER BY dishes DESC
"""
# The medians the label prints beside their before-values, over the dishes the app can pick.
MEDIANS = f"""
MATCH (d:Dish) WHERE {RECOMMENDABLE} AND d.calories > 0
RETURN count(*) AS dishes,
       percentileCont(d.calories, 0.5) AS median_calories,
       percentileCont(9.0 * d.fat_g / d.calories, 0.5) AS median_fat_share,
       sum(CASE WHEN 9.0 * d.fat_g / d.calories > 0.75 THEN 1 ELSE 0 END) AS over_three_quarters_fat
"""
PLACES = """
MATCH (r:Restaurant)
RETURN coalesce(r.location_precision, 'unknown') AS value, count(*) AS restaurants
ORDER BY restaurants DESC
"""
AREAS = """
MATCH (r:Restaurant) WHERE r.area IS NOT NULL
RETURN r.area AS value, count(*) AS restaurants ORDER BY restaurants DESC, value
"""


def _rows(ask, cypher: str, key: str = "dishes") -> list[dict]:
    return [{"value": r["value"], "count": r[key]} for r in ask(cypher) if r["value"]]


def counted(fresh: bool = False) -> dict | None:
    """
    What the graph holds, counted. None when it cannot be reached.

    Cached for TTL_SECONDS: the numbers only move when the graph is reseeded, and the label is
    read far more often than that.
    """
    if not fresh and _CACHE["facts"] and time.time() - _CACHE["at"] < TTL_SECONDS:
        return _CACHE["facts"]

    from accounts.store import get_driver  # the app's own pool, not a second one

    def ask(cypher: str) -> list[dict]:
        records, _, _ = get_driver().execute_query(cypher)
        return [dict(r) for r in records]

    try:
        facts = ask(TOTALS)[0]
        facts["breakdowns"] = {
            field: _rows(ask, BREAKDOWN.format(field=field))
            for field in BREAKDOWNS
            if field != "quarantine_reason"
        }
        facts["breakdowns"]["quarantine_reason"] = _rows(ask, REASONS)
        facts["nutrition"] = ask(MEDIANS)[0]
        facts["allergen_tags"] = _rows(ask, ALLERGENS)
        facts["located"] = _rows(ask, PLACES, key="restaurants")
        facts["areas"] = _rows(ask, AREAS, key="restaurants")
    except Exception as exc:
        # A label that cannot be counted says so. It never falls back to a figure typed in by
        # hand, which is the one thing a page about honesty cannot do.
        log.error("the dataset label could not be counted: %s", exc)
        return None

    _CACHE.update(at=time.time(), facts=facts)
    return facts


# ── The label itself ────────────────────────────────────────────────────────
#
# The counts above are turned into the screen here, so the frontend draws what it is given and
# nothing it has to interpret. Each row carries the same badge and tone vocabulary the dish's
# own panel uses (ui/provenance.py), because they are the same statuses: a row that says
# "Person checked" on one dish is the group that says "Person checked" here.

from ui import build_facts, provenance  # noqa: E402  (after the queries, for reading order)

# Which provenance vocabulary explains each breakdown's values.
VOCABULARIES = {
    "review_status": provenance.REVIEW,
    "price_status": provenance.PRICE,
    "ingredients_basis": provenance.INGREDIENTS,
    "taste_source": provenance.TASTE,
    "serves_source": provenance.SERVES,
}
# A confidence row is its own badge ("medium" beside MEDIUM reads as a stutter), so only the
# dishes with no estimate at all get one — that is the part worth marking.
NO_ESTIMATE = ("Not estimated", "unchecked")


def _figure(value) -> str:
    return f"{round(value):,}"


def _row(field: str, value: str, count: int, total: int) -> dict:
    """One line of a breakdown: what it is, how many, and how strong that evidence is."""
    known = VOCABULARIES.get(field, {}).get(value)
    if known:
        badge, tone, _ = known
    elif field == "nutrition_confidence":
        badge, tone = NO_ESTIMATE if value == "none" else ("", "")
    elif field == "quarantine_reason":
        badge, tone = "Never served", "unchecked"
    else:
        badge, tone = "", ""
    return {
        "label": value.replace("_", " "),
        "count": count,
        "share": round(100 * count / total) if total else 0,
        "badge": badge,
        "tone": tone,
    }


def label() -> dict | None:
    """The dataset label, composed. None when the graph cannot be counted."""
    facts = counted()
    if not facts:
        return None

    dishes = facts["dishes"]
    by_review = facts["breakdowns"]["review_status"]
    checked = next((r["count"] for r in by_review if r["value"] == "human_confirmed"), 0)
    headline = [
        {"figure": _figure(dishes), "of": "dishes", "note": "every one read off a real menu"},
        {"figure": _figure(facts["restaurants"]), "of": "restaurants", "note": "in Islamabad"},
        {
            "figure": _figure(checked),
            "of": "confirmed by a person",
            "note": f"{round(100 * checked / dishes)}% of the rows, name and price",
        },
        {
            "figure": _figure(facts["recommendable"]),
            "of": "the app will pick from",
            "note": "drinks, sides and quarantined rows are held back",
        },
        {
            "figure": _figure(facts["quarantined"]),
            "of": "kept on file, never served",
            "note": "a damaged name or an impossible price",
        },
        {
            "figure": _figure(facts["allergens_unknown_recommendable"]),
            "of": "with allergens still unknown",
            "note": "never offered to anyone who excludes one",
        },
    ]

    changed = []
    for fact in build_facts.CHANGED:
        found = facts
        for key in fact["after"].split("."):
            found = (found or {}).get(key)
        if found is None:
            continue
        shown = {
            "kcal": lambda v: f"{round(v):,} kcal",
            "share": lambda v: f"{round(100 * v)}%",
            "count": lambda v: f"{v:,}",
            "percent_of_dishes": lambda v: f"{100 * v / dishes:.1f}%",
        }[fact["as"]](found)
        changed.append(
            {"what": fact["what"], "before": fact["before"], "after": shown, "note": fact["note"]}
        )

    sections = [
        {
            "id": field,
            "title": title,
            "rows": [
                _row(field, r["value"], r["count"], dishes) for r in facts["breakdowns"][field]
            ],
        }
        for field, title in BREAKDOWNS.items()
    ]
    sections.append(
        {
            "id": "allergens",
            "title": "Allergen tags, inferred from ingredients",
            "note": f"{facts['allergens_unknown']} dishes have ingredients too uncertain to tag, "
            "and are withheld from anyone excluding an allergen rather than guessed at.",
            "rows": [
                {
                    "label": r["value"],
                    "count": r["count"],
                    "share": round(100 * r["count"] / dishes),
                    "badge": "Inferred",
                    "tone": "inferred",
                }
                for r in facts["allergen_tags"]
            ],
        }
    )
    sections.append(
        {
            "id": "located",
            "title": "How the restaurants are placed on the map",
            "note": "Areas: " + ", ".join(f"{r['value']} {r['count']}" for r in facts["areas"]),
            "rows": [
                {
                    "label": r["value"],
                    "count": r["count"],
                    "share": round(100 * r["count"] / facts["restaurants"]),
                    "badge": (provenance.WHERE.get(r["value"]) or ("", "", ""))[0],
                    "tone": (provenance.WHERE.get(r["value"]) or ("", "", ""))[1],
                }
                for r in facts["located"]
            ],
        }
    )

    return {
        "headline": headline,
        "changed": changed,
        "sections": [s for s in sections if s["rows"]],
        "nutrition": facts["nutrition"],
        "calibration": build_facts.CALIBRATION,
    }
