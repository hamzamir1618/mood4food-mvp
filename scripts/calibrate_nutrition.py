"""
Calibrates the nutrition estimator's split of a serving (pipeline/nutrition.py SHARES)
against restaurant dishes USDA measured whole.

    python -m scripts.calibrate_nutrition

USDA SR Legacy (public domain, already on disk for pipeline/usda_reference.py) includes
lab-analysed restaurant plates: "Restaurant, Chinese, kung pao chicken", "Fast foods,
cheeseburger" and so on. Our dishes whose names are the same food are re-estimated with
the pipeline's own estimate() at each candidate split, and compared with the measured
fat share of energy and calories per 100 g. The split with the smallest combined median
error is the one to use; the table printed is the evidence behind SHARES.

Serving weights are left alone: calories per 100 g and fat share don't depend on them.
"""

import csv
import json
import re
import statistics as st
import sys

from pipeline import nutrition, paths
from pipeline.usda_reference import load_reference

NUTRIENT_IDS = {"1008": "kcal", "1003": "protein", "1004": "fat", "1005": "carbs"}

# Our dish name (a regex on the lower-case name) -> the USDA-measured dish that is the same food.
MATCHES = (
    (r"kung pao chicken", "Restaurant, Chinese, kung pao chicken"),
    (r"general tso", "Restaurant, Chinese, general tso's chicken"),
    (r"orange chicken", "Restaurant, Chinese, orange chicken"),
    (r"lemon chicken", "Restaurant, Chinese, lemon chicken"),
    (r"sesame chicken", "Restaurant, Chinese, sesame chicken"),
    (r"sweet (and|&|n) sour chicken", "Restaurant, Chinese, sweet and sour chicken"),
    (r"chicken chow ?mein", "Restaurant, Chinese, chicken chow mein"),
    (r"(vegetable|veg) fried rice", "Restaurant, Chinese, fried rice, without meat"),
    (r"(vegetable|veg) lo ?mein", "Restaurant, Chinese, vegetable lo mein, without meat"),
    (r"chicken (with|and|&) vegetables", "Restaurant, Chinese, chicken and vegetables"),
    (r"beef (with|and|&) vegetables", "Restaurant, Chinese, beef and vegetables"),
    (
        r"prawns? (with|and|&) vegetables|shrimp (with|and|&) vegetables",
        "Restaurant, Chinese, shrimp and vegetables",
    ),
    (r"(egg|spring) rolls?", "Restaurant, Chinese, egg rolls, assorted"),
    (r"lasagn", "Restaurant, Italian, lasagna with meat"),
    (r"spaghetti (bolognese|with meat)", "Restaurant, Italian, spaghetti with meat sauce"),
    (r"chicken parm", "Restaurant, Italian, chicken parmesan without pasta"),
    (r"spaghetti (and|&|with) meatballs", "Restaurant, family style, spaghetti and meatballs"),
    (
        r"mac(aroni)? (and|&|n) cheese",
        "Restaurant, family style, macaroni & cheese, from kids' menu",
    ),
    (r"mozzarella sticks", "Restaurant, family style, fried mozzarella sticks"),
    (r"onion rings", "Fast foods, onion rings, breaded and fried"),
    (
        r"^(plain |regular |salted )?(french )?fries$",
        "Fast foods, potato, french fried in vegetable oil",
    ),
    (r"chicken (tenders|strips)", "Fast foods, chicken tenders"),
    (r"nuggets", "Fast foods, chicken, breaded and fried, boneless pieces, plain"),
    (
        r"^(beef |classic |plain )?burger$|^hamburger$",
        "Fast foods, hamburger, large, single patty, with condiments",
    ),
    (
        r"^cheese ?burger$|^(beef |classic )cheese ?burger$",
        "Fast foods, cheeseburger; single, large patty; with condiments",
    ),
    (r"(zinger|crispy chicken) burger", "Fast foods, chicken fillet sandwich, plain with pickles"),
    (r"fish (burger|sandwich)", "Fast foods, fish sandwich, with tartar sauce"),
    (r"chicken quesadilla", "Fast foods, quesadilla, with chicken"),
    (r"^(beef )?tacos?$|beef tacos?", "Fast foods, taco with beef, cheese and lettuce, soft"),
    (r"chicken tacos?", "Fast foods, taco with chicken, lettuce and cheese, soft"),
    (r"nachos", "Fast foods, nachos, with cheese"),
    (r"coleslaw", "Fast foods, coleslaw"),
    (r"hash ?browns?", "Fast foods, potatoes, hash browns, round pieces or patty"),
    (r"mashed potato", "Fast foods, potato, mashed"),
    (
        r"(fried|crispy) prawns?|(fried|crispy) shrimps?|prawn tempura|shrimp tempura",
        "Restaurant, family style, shrimp, breaded and fried",
    ),
    (
        r"fish (and|&|n) chips|fried fish|fish fingers",
        "Restaurant, family style, fish fillet, battered or breaded, fried",
    ),
)
# Soups, against USDA's measured soups (Chinese restaurant soups where USDA has them, ready-to-
# serve otherwise). Soups with no fair counterpart (chicken corn soup, yakhni) are left out.
SOUP_MATCHES = (
    (r"hot ?(and|&|n|'n'|n') ?sour soup", "Soup, hot and sour, Chinese restaurant"),
    (r"wonton soup", "Soup, wonton, Chinese restaurant"),
    (r"egg drop", "Soup, egg drop, Chinese restaurant"),
    (r"chicken noodles? soup", "Soup, chicken noodle, reduced sodium, canned, ready-to-serve"),
    (r"chicken (and |& )?vegetables? soup", "Soup, chicken and vegetable, canned, ready-to-serve"),
    (r"beef (and |& )?vegetables? soup", "Soup, beef and vegetables, canned, ready-to-serve"),
    (r"^(clear )?vegetable soup", "Soup, chunky vegetable, canned, ready-to-serve"),
    (
        r"(cream of )?mushroom soup",
        "Soup, cream of mushroom, canned, prepared with equal volume low fat (2%) milk",
    ),
    (r"lentil soup", "Soup, lentil with ham, canned, ready-to-serve"),
    (r"^chicken soup$", "Soup, chicken, canned, chunky, ready-to-serve"),
)
SOUP_SOLIDS = (0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 1.0)
FAT_SHARES = (0.05, 0.06, 0.07, 0.08, 0.10, 0.12, 0.15)
BULK_SHARES = (0.50, 0.59, 0.62, 0.65, 0.68, 0.71, 0.74)
VEG = 0.15
TIE = 0.005  # combined median errors this close are a tie


def measured_dishes(matches) -> dict[str, dict]:
    wanted = {usda for _, usda in matches}
    with open(paths.USDA_SR_DIR / "food.csv", encoding="utf-8") as f:
        ids = {
            r["fdc_id"]: r["description"] for r in csv.DictReader(f) if r["description"] in wanted
        }
    values: dict[str, dict] = {}
    with open(paths.USDA_SR_DIR / "food_nutrient.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["fdc_id"] in ids and r["nutrient_id"] in NUTRIENT_IDS:
                values.setdefault(ids[r["fdc_id"]], {})[NUTRIENT_IDS[r["nutrient_id"]]] = float(
                    r["amount"]
                )
    missing = wanted - set(values)
    if missing:
        sys.exit(f"USDA entries not found: {sorted(missing)}")
    return values


def matched_pairs(matches, soups: bool) -> list[tuple[dict, str]]:
    """Our dishes that are the same food as a measured one: plates, or soups only."""
    with open(paths.DATASET_CSV, encoding="utf-8") as f:
        rows = [
            r
            for r in csv.DictReader(f)
            if r["quarantined"] != "True" and r["ingredients"] not in ("", "[]")
        ]
    pairs = []
    for r in rows:
        name = r["dish_name"].lower()
        if nutrition.is_soup(name) != soups:
            continue
        usda = next((u for pattern, u in matches if re.search(pattern, name)), None)
        if usda:
            pairs.append((r, usda))
    return pairs


def errors(
    shares: dict, pairs, measured, reference, solids: float | None = None
) -> tuple[list[float], list[float]]:
    """Per dish: fat share of energy minus measured (points), and relative kcal/100 g error."""
    saved, nutrition.SHARES = nutrition.SHARES, shares
    saved_solids = nutrition.SOUP_SOLIDS
    if solids is not None:
        nutrition.SOUP_SOLIDS = solids
    try:
        fat, kcal = [], []
        for r, usda in pairs:
            soup = nutrition.is_soup(r["dish_name"])
            est = nutrition.estimate(
                json.loads(r["ingredients"]), r["category"], reference, soup=soup
            )
            if not est or est["calories"] <= 0:
                continue
            m = measured[usda]
            fat.append(9 * est["fat_g"] / est["calories"] - 9 * m["fat"] / m["kcal"])
            kcal.append((100 * est["calories"] / est["serving_g"] - m["kcal"]) / m["kcal"])
        return fat, kcal
    finally:
        nutrition.SHARES = saved
        nutrition.SOUP_SOLIDS = saved_solids


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    reference = load_reference()
    measured, pairs = measured_dishes(MATCHES), matched_pairs(MATCHES, soups=False)
    print(f"{len(pairs)} of our dishes match {len({u for _, u in pairs})} USDA-measured dishes\n")
    results = []
    for fat in FAT_SHARES:
        for bulk in BULK_SHARES:
            if fat + bulk + VEG > 1:
                continue
            ef, ek = errors({"bulk": bulk, "fat": fat, "veg": VEG}, pairs, measured, reference)
            mf, mk = st.median(map(abs, ef)), st.median(map(abs, ek))
            results.append((mf + mk, fat, bulk, mf, st.median(ef), mk, st.median(ek)))
    print("fat   bulk | fat share: median |error|  bias | kcal/100 g: median |error|  bias")
    current = (nutrition.SHARES["fat"], nutrition.SHARES["bulk"])
    for score, fat, bulk, mf, bf, mk, bk in sorted(results)[:8]:
        mark = "  <- in use" if (fat, bulk) == current else ""
        print(f"{fat:.2f}  {bulk:.2f} | {mf:10.1%}  {bf:+6.1%} | {mk:10.1%}  {bk:+6.1%}{mark}")
    # Several splits tie on error; among those, the one that is least wrong in one direction.
    best = min(r[0] for r in results)
    tied = [r for r in results if r[0] <= best + TIE]
    chosen = min(tied, key=lambda r: abs(r[4]) + abs(r[6]))
    print(
        f"\nchosen (least bias among splits within {TIE} of the best error): "
        f"fat {chosen[1]:.2f}, bulk {chosen[2]:.2f}"
        + ("" if (chosen[1], chosen[2]) == current else "  — differs from SHARES in use")
    )
    old = next(r for r in results if (r[1], r[2]) == (0.15, 0.50))
    print(
        f"the sourcing project's 0.15 / 0.50: fat share {old[3]:.1%} ({old[4]:+.1%}), "
        f"kcal {old[5]:.1%} ({old[6]:+.1%})"
    )

    # Soups: only the solid share of the bowl is fitted, against calories per 100 g.
    soup_measured = measured_dishes(SOUP_MATCHES)
    soups = matched_pairs(SOUP_MATCHES, soups=True)
    print(
        f"\n{len(soups)} of our soups match {len({u for _, u in soups})} USDA-measured soups\n"
        "solids | kcal/100 g: median |error|  bias"
    )
    fits = []
    for solids in SOUP_SOLIDS:
        _, ek = errors(nutrition.SHARES, soups, soup_measured, reference, solids=solids)
        fits.append((st.median(map(abs, ek)), solids, st.median(ek)))
        mark = "  <- in use" if solids == nutrition.SOUP_SOLIDS else ""
        label = "(as a plate)" if solids == 1.0 else ""
        print(f"{solids:6.2f} | {fits[-1][0]:10.1%}  {fits[-1][2]:+6.1%} {label}{mark}")
    tied = [f for f in fits if f[0] <= min(fits)[0] + TIE]
    chosen_solids = min(tied, key=lambda f: abs(f[2]))[1]
    print(
        f"chosen (least bias among shares within {TIE} of the best error): solids "
        f"{chosen_solids:.2f}"
        + ("" if chosen_solids == nutrition.SOUP_SOLIDS else "  — differs from SOUP_SOLIDS in use")
    )


if __name__ == "__main__":
    main()
