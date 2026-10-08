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
    "review_status": "Who checked each dish",
    "price_status": "How sure we are of each price",
    "ingredients_basis": "Where each dish's ingredients come from",
    "nutrition_confidence": "How good each calorie estimate is",
    "taste_source": "Where each dish's flavour comes from",
    "serves_source": "How many people each dish feeds",
    "quarantine_reason": "Dishes we keep but never recommend",
    "category": "Kinds of dish",
}
# What each breakdown is about, in a sentence a diner can follow, and the mark beside it.
INTROS = {
    "review_status": (
        "row",
        "A computer read every dish off a photo of the menu. Some were then checked by a person "
        "against the photo.",
    ),
    "price_status": ("price", "Every price comes from a menu. Some could be double-checked."),
    "ingredients_basis": (
        "ingredients",
        "Menus rarely list everything in a dish, so where they don't, we fill in what that kind "
        "of dish usually has, and say so.",
    ),
    "nutrition_confidence": (
        "nutrition",
        "No restaurant here publishes calories, so we estimate them from the ingredients. The "
        "more we know about a dish's ingredients, the better the estimate.",
    ),
    "taste_source": (
        "taste",
        "How spicy, sweet or sour each dish is. The less sure the source, the less flavour "
        "counts when dishes are compared.",
    ),
    "serves_source": (
        "serves",
        "Most menus don't say how many a dish feeds, so we count it as one person unless "
        "something says otherwise.",
    ),
    "quarantine_reason": (
        "hidden",
        "These stay in the records so nothing is quietly deleted, but the app will never "
        "recommend them.",
    ),
    "category": ("kind", "Drinks and sides are kept for “make it a meal” and never picked."),
}
# Each value as a person would say it. A value not listed is shown as it is stored.
PLAIN = {
    "review_status": {
        "human_confirmed": "Checked by a person",
        "auto_imported": "Read by computer, not yet checked",
        "scraped": "Taken from the restaurant's website",
        "manual": "Typed in by hand",
    },
    "price_status": {
        "trusted": "Read straight off the menu",
        "verified": "Double-checked against the menu",
        "unverified": "Couldn't be double-checked",
    },
    "ingredients_basis": {
        "named + typical ingredients": "Some on the menu, the rest typical",
        "named ingredients": "All named on the menu",
        "typical ingredients": "Typical for that kind of dish",
        "none": "Not known",
    },
    "nutrition_confidence": {
        "high": "Good estimate",
        "medium": "Fair estimate",
        "low": "Rough estimate",
        "none": "No estimate",
    },
    "taste_source": {
        "original": "Came with the menu data",
        "restaurant_average": "That restaurant's usual flavours",
        "keyword": "Worked out from its name",
        "name_rule": "Worked out from its name",
        "category_prior": "Usual for that kind of dish",
        "global_prior": "Average of all dishes",
        "neutral": "Not known",
    },
    "serves_source": {
        "default": "Not stated, so counted as one",
        "price_estimate": "Worked out from its price",
        "menu": "Stated on the menu",
        "double": "Confirmed by the owner",
    },
    "quarantine_reason": {
        "owner discarded the name as OCR damage": "Name garbled when the photo was read",
        "owner removed the dish (platter worksheet)": "Taken off by the restaurant's owner",
        "name truncated by OCR": "Name cut off when the photo was read",
        "withheld rather than guessed": "Too uncertain to show",
        "price: price under Rs 20": "Price under Rs 20, a misreading",
        "price: over 8x the restaurant's median price, with no size or serving word": (
            "Price far too high for that restaurant"
        ),
        "price: no price": "No price on the menu",
    },
    "category": {
        "desi_traditional": "Desi",
        "chinese_asian": "Chinese and Asian",
        "middle_eastern": "Middle Eastern",
        "continental_upscale": "Continental",
        "fast_food": "Fast food",
        "cafe_bakery": "Café and desserts",
        "afghan": "Afghan",
        "pizza": "Pizza",
        "sandwich": "Sandwiches and wraps",
        "beverages": "Drinks (never picked)",
        "add_ons": "Sides (never picked)",
        "other": "Couldn't tell",
    },
    "located": {
        "place": "Mapped to its own door",
        "area": "Mapped to the middle of its area",
        "unknown": "Couldn't be mapped",
    },
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


def _plain(field: str, value: str) -> str:
    said = PLAIN.get(field, {})
    return said.get(value) or said.get(value.replace(" ", "_")) or value.replace("_", " ")


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
        "label": _plain(field, value),
        "value": value,
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
        {
            "figure": _figure(dishes),
            "of": "dishes",
            "icon": "dish",
            "note": "every one read off a photo of a real menu",
        },
        {
            "figure": _figure(facts["restaurants"]),
            "of": "restaurants",
            "icon": "store",
            "note": "all in Islamabad",
        },
        {
            "figure": _figure(checked),
            "of": "confirmed by a person",
            "icon": "checked",
            "note": f"{round(100 * checked / dishes)}% of dishes: name and price checked by hand",
        },
        {
            "figure": _figure(facts["recommendable"]),
            "of": "the app will pick from",
            "icon": "target",
            "note": "drinks and sides are kept for meals, never picked on their own",
        },
        {
            "figure": _figure(facts["quarantined"]),
            "of": "kept on file, never served",
            "icon": "hidden",
            "note": "a garbled name or an impossible price",
        },
        {
            "figure": _figure(facts["allergens_unknown_recommendable"]),
            "of": "with allergens still unknown",
            "icon": "allergens",
            "note": "never shown to anyone avoiding an allergen",
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
        # The pair as numbers too, on one scale, for the before-and-after chart.
        after_value = {
            "kcal": lambda v: float(v),
            "share": lambda v: float(v),
            "count": lambda v: float(v),
            "percent_of_dishes": lambda v: 100 * v / dishes,
        }[fact["as"]](found)
        changed.append(
            {
                "what": fact["what"],
                "title": fact.get("title") or fact["what"],
                "icon": fact.get("icon"),
                "kind": fact["as"],
                "before": fact["before"],
                "after": shown,
                "before_value": fact.get("before_value"),
                "after_value": after_value,
                "better": fact.get("better"),
                "reference": fact.get("reference"),
                "note": fact["note"],
            }
        )

    sections = [
        {
            "id": field,
            "title": title,
            "icon": INTROS.get(field, (None, None))[0],
            "note": INTROS.get(field, (None, None))[1],
            "rows": [
                _row(field, r["value"], r["count"], dishes) for r in facts["breakdowns"][field]
            ],
        }
        for field, title in BREAKDOWNS.items()
    ]
    sections.append(
        {
            "id": "allergens",
            "title": "Allergens we marked",
            "icon": "allergens",
            "note": "Worked out from each dish's ingredients, not tested in a laboratory. "
            f"{facts['allergens_unknown']} dishes have ingredients too unclear to work it out, "
            "so they are never shown to anyone avoiding an allergen.",
            "rows": [
                {
                    "label": r["value"],
                    "count": r["count"],
                    "share": round(100 * r["count"] / dishes),
                    "badge": "Worked out",
                    "tone": "inferred",
                }
                for r in facts["allergen_tags"]
            ],
        }
    )
    sections.append(
        {
            "id": "located",
            "title": "Where the restaurants are on the map",
            "icon": "where",
            "note": "Some restaurants are mapped to their own door; for others we only know the "
            "area, so their distances are approximate. Areas: "
            + ", ".join(f"{r['value']} {r['count']}" for r in facts["areas"]),
            "rows": [
                {
                    "label": _plain("located", r["value"]),
                    "value": r["value"],
                    "count": r["count"],
                    "share": round(100 * r["count"] / facts["restaurants"]),
                    "badge": (provenance.WHERE.get(r["value"]) or ("", "", ""))[0],
                    "tone": (provenance.WHERE.get(r["value"]) or ("", "", ""))[1],
                }
                for r in facts["located"]
            ],
        }
    )

    nutrition = facts["nutrition"]
    typical = {
        "dishes": nutrition["dishes"],
        "calories": round(nutrition["median_calories"]),
        "fat_share": nutrition["median_fat_share"],
        "over_three_quarters_fat": nutrition["over_three_quarters_fat"],
        "text": f"Take the dish in the middle of all {nutrition['dishes']:,} the app can pick, "
        f"half above it and half below. It has about {round(nutrition['median_calories']):,} "
        f"calories, and about {round(100 * nutrition['median_fat_share'])}% of them come from "
        f"fat. {nutrition['over_three_quarters_fat']} dishes are estimated at more than three "
        "quarters fat, and their cards say how far their estimate can be trusted.",
    }
    return {
        "headline": headline,
        "changed": changed,
        "sections": [s for s in sections if s["rows"]],
        "nutrition": nutrition,
        "typical": typical,
        "calibration": build_facts.CALIBRATION,
        "legend": [
            {
                "tone": "confirmed",
                "badge": "Checked",
                "text": "Seen on the menu, or checked by a person.",
            },
            {
                "tone": "inferred",
                "badge": "Worked out",
                "text": "Worked out by a rule from what we do know.",
            },
            {
                "tone": "estimated",
                "badge": "Estimated",
                "text": "Our best estimate, and it may be off.",
            },
            {
                "tone": "unchecked",
                "badge": "Unchecked",
                "text": "Not checked yet, or not known, so it counts for less.",
            },
        ],
    }
