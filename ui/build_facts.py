"""
What the build changed — the before-values the graph cannot hold.

ui/dataset_label.py counts what is on the shelves now. It cannot count what was there before:
a dish that was filed as "other" and is now filed as afghan carries only its present category,
and the 44.6% of dishes that once had no flavour values at all left no trace once they were
filled in. Those before-values are the evidence that the curation happened, so they are kept
here, where the app can read them in production — `data/` is not shipped with the code.

Only the *before* is written down. Every after-value is read from the live graph through
`after` below, so the pair on screen is history against what the app is serving this minute
and cannot drift into a stale claim. tests/test_dataset_label.py checks each before-value
against data/build_report.md whenever that report is present.
"""

# `after` is a path into ui.dataset_label.counted(); `as` is how to print what it finds.
CHANGED = (
    {
        "what": "Median calories in a serving",
        "before": "731 kcal",
        "after": "nutrition.median_calories",
        "as": "kcal",
        "note": "Over the dishes the app can pick. The inherited method read 15% of every "
        "plate's weight as pure oil — 60 g in a desi serving.",
    },
    {
        "what": "Share of a dish's energy from fat, at the median",
        "before": "68%",
        "after": "nutrition.median_fat_share",
        "as": "share",
        "note": "Restaurant dishes USDA has measured whole sit at 44%. Under the inherited "
        "split, 78% of dishes read as over half fat, so almost everything looked heavy.",
    },
    {
        "what": "Dishes carrying any allergen tag",
        "before": "706",
        "after": "with_allergen_tag",
        "as": "count",
        "note": "Read from a controlled ingredient vocabulary rather than from the dish's "
        "name. Where the ingredients are unknown the dish is never offered to anyone who "
        "excludes an allergen.",
    },
    {
        "what": "Dishes filed as 'other'",
        "before": "429",
        "after": "filed_as_other",
        "as": "count",
        "note": "1,011 categories were corrected in all. The old category was often the "
        "restaurant's cuisine rather than the dish's — wings at a desi restaurant filed "
        "as desi.",
    },
    {
        "what": "Dishes with no flavour values at all",
        "before": "44.6%",
        "after": "no_flavour_at_all",
        "as": "percent_of_dishes",
        "note": "Filled from the dish's name, its kind, or its restaurant's average — each "
        "tagged with which, and the weaker the source, the less taste counts in the score.",
    },
    {
        "what": "Dishes marked vegan",
        "before": "337",
        "after": "vegan",
        "as": "count",
        "note": "179 of the old vegan flags were withdrawn once the ingredients were read: "
        "an omelette, a yogurt dip, a shakshuka. Vegetarian went from 481 to 843.",
    },
)

# How the nutrition estimator was fitted (scripts/calibrate_nutrition.py).
CALIBRATION = {
    "matched": "113 of our dishes matched 28 restaurant dishes USDA has measured whole",
    "inherited": "+20.1 points too high on fat share",
    "now": "+2.8 points",
    "method": "Seven splits of a serving come first in at least 5% of 2,000 bootstrap "
    "resamples, so the matched dishes cannot separate them; the one in use is the least "
    "biased of those.",
}
