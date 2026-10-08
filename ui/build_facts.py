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

The words are for someone who has never heard of a median or a macronutrient: the screen is
read by a panel and by diners, not by the people who built it. `what` is the fact's fixed name
(the tests and the build report key on it); `title` and `note` are what the screen says.
"""

# `after` is a path into ui.dataset_label.counted(); `as` is how to print what it finds.
# `before_value` is the before as a number, for the before-and-after chart; `better` says which
# way is the improvement, so the chart can say so without a judgement in the page.
CHANGED = (
    {
        "what": "Median calories in a serving",
        "title": "Calories in a typical dish",
        "icon": "nutrition",
        "before": "731 kcal",
        "before_value": 731,
        "after": "nutrition.median_calories",
        "as": "kcal",
        "better": None,  # the point is accuracy, not fewer calories
        "note": "The old method counted 15% of every plate's weight as pure cooking oil — about "
        "60 g, over four tablespoons, in one desi serving. That made every dish look bigger "
        "than it is.",
    },
    {
        "what": "Share of a dish's energy from fat, at the median",
        "title": "How much of a typical dish's calories come from fat",
        "icon": "fat",
        "before": "68%",
        "before_value": 0.68,
        "after": "nutrition.median_fat_share",
        "as": "share",
        "better": "closer",  # to the laboratory figure, below
        "reference": {"value": 0.44, "label": "Restaurant dishes measured in a lab"},
        "note": "A dish's calories come from three things: fat, carbohydrate and protein. The old "
        "estimate put about two thirds of a typical dish's calories down to fat, so almost "
        "everything looked heavy and unhealthy. Restaurant dishes that have been measured in a "
        "laboratory come out at about 44%.",
    },
    {
        "what": "Dishes carrying any allergen tag",
        "title": "Dishes with their allergens marked",
        "icon": "allergens",
        "before": "706",
        "before_value": 706,
        "after": "with_allergen_tag",
        "as": "count",
        "better": "higher",
        "note": "Allergens are now worked out from each dish's ingredients, not guessed from its "
        "name. When we don't know a dish's ingredients, it is never shown to anyone avoiding "
        "an allergen.",
    },
    {
        "what": "Dishes filed as 'other'",
        "title": "Dishes we couldn't say what kind they were",
        "icon": "kind",
        "before": "429",
        "before_value": 429,
        "after": "filed_as_other",
        "as": "count",
        "better": "lower",
        "note": "1,011 dishes were moved to the right kind in all. Many had been filed under the "
        "restaurant's cuisine instead of what the dish is: chicken wings at a desi restaurant "
        "were filed as desi food.",
    },
    {
        "what": "Dishes with no flavour values at all",
        "title": "Dishes with nothing known about their flavour",
        "icon": "taste",
        "before": "44.6%",
        "before_value": 44.6,
        "after": "no_flavour_at_all",
        "as": "percent_of_dishes",
        "better": "lower",
        "note": "Filled in from the dish's name, its kind, or its restaurant's usual flavours, "
        "and each dish records which. The less sure the source, the less flavour counts when "
        "dishes are compared.",
    },
    {
        "what": "Dishes marked vegan",
        "title": "Dishes marked vegan",
        "icon": "vegan",
        "before": "337",
        "before_value": 337,
        "after": "vegan",
        "as": "count",
        "better": None,  # more is not better here; right is
        "note": "Once the ingredients were read, 179 dishes lost a vegan label they should never "
        "have had: an omelette, a yogurt dip, a shakshuka. Others gained one. Vegetarian dishes "
        "went from 481 to 843.",
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
    # The same, for the screen
    "ours": 113,
    "measured": 28,
    "error_before": 20.1,
    "error_now": 2.8,
    "title": "How we checked our calorie estimates",
    "plain": "No restaurant here publishes nutrition, so every figure is an estimate worked out "
    "from a dish's ingredients. To test the estimates, we matched 113 of our dishes with 28 "
    "restaurant dishes that the US Department of Agriculture has measured in a laboratory, and "
    "compared how much of their calories each said came from fat.",
    "result": "The method we started with said too much of every dish was fat, by about 20 "
    "percentage points on average. The method we use now is about 3 points out.",
    "how": "We tried different ways of dividing a plate into its main part, its cooking fat "
    "and its vegetables. Seven of them did about equally well against the laboratory dishes, "
    "so we picked the one that was least wrong in one direction.",
}
