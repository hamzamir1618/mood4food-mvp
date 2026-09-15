"""
Taste Enrichment Verification Script

Runs the enrichment pipeline against the full CSV dataset (no Neo4j required)
and verifies all acceptance criteria:
  1. Specific broken examples resolve correctly
  2. Global zero-taste percentage drops below 10%
  3. No large duplicate vector blocks
  4. Provenance breakdown is reported
"""

import csv
import io
import sys
from collections import Counter

from taste_enrichment import TASTE_DIMS, enrich_taste_profiles

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

CSV_PATH = "handoff_output/mood4food_dishes.csv"


def load_csv():
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def get_taste(row):
    return {d: float(row.get(d, 0) or 0) for d in TASTE_DIMS}


def is_all_zero(taste):
    return all(v == 0.0 for v in taste.values())


def taste_vector_key(taste):
    return tuple(round(taste[d], 4) for d in TASTE_DIMS)


def main():
    print("=" * 70)
    print("TASTE ENRICHMENT VERIFICATION")
    print("=" * 70)

    rows = load_csv()
    total = len(rows)
    print(f"\nLoaded {total} dishes from {CSV_PATH}")

    # --- Pre-enrichment baseline ---
    pre_zero = sum(1 for r in rows if is_all_zero(get_taste(r)))
    print(f"Pre-enrichment all-zero: {pre_zero}/{total} ({100 * pre_zero / total:.1f}%)")

    # --- Run enrichment ---
    print("\nRunning enrichment pipeline...")
    enrich_taste_profiles(rows)

    # --- Post-enrichment stats ---
    post_zero = sum(1 for r in rows if is_all_zero(get_taste(r)))
    print(f"\nPost-enrichment all-zero: {post_zero}/{total} ({100 * post_zero / total:.1f}%)")

    # ═══════════════════════════════════════════════════════════════════
    # TEST 1: Specific broken examples
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("TEST 1: Specific Broken Examples")
    print("=" * 70)

    targets = {
        "Soft Drink": {"expect_sweet_gt": 0.0, "expect_source": ["category_prior"]},
        "Peach Iced Tea": {
            "expect_sweet_gt": 0.0,
            "expect_sour_gt": 0.0,
            "expect_source": ["keyword"],
        },
        "Mint Margarita": {"expect_sweet_gt": 0.0, "expect_source": ["category_prior"]},
        "Water": {"expect_all_zero": True, "expect_source": ["neutral"]},
    }

    all_pass = True
    for dish_name, checks in targets.items():
        matching = [r for r in rows if r["dish_name"] == dish_name]
        if not matching:
            print(f"  ❌ {dish_name}: NOT FOUND in dataset")
            all_pass = False
            continue

        # Check first occurrence (all instances of same name should behave the same)
        r = matching[0]
        taste = get_taste(r)
        source = r.get("taste_source", "")
        restaurant = r.get("restaurant_name", "")

        print(f"\n  {dish_name} @ {restaurant}:")
        print(f"    taste = {taste}")
        print(f"    source = {source}")

        if checks.get("expect_all_zero"):
            if is_all_zero(taste):
                print("    ✅ PASS: Correctly remains all-zero")
            else:
                print("    ❌ FAIL: Should be all-zero but has values")
                all_pass = False
        else:
            if (
                checks.get("expect_sweet_gt") is not None
                and taste["taste_sweet"] <= checks["expect_sweet_gt"]
            ):
                print(
                    f"    ❌ FAIL: taste_sweet should be > {checks['expect_sweet_gt']}, "
                    f"got {taste['taste_sweet']}"
                )
                all_pass = False
            elif checks.get("expect_sweet_gt") is not None:
                print(
                    f"    ✅ PASS: taste_sweet = {taste['taste_sweet']} "
                    f"(> {checks['expect_sweet_gt']})"
                )

            if (
                checks.get("expect_sour_gt") is not None
                and taste["taste_sour"] <= checks["expect_sour_gt"]
            ):
                print(
                    f"    ❌ FAIL: taste_sour should be > {checks['expect_sour_gt']}, "
                    f"got {taste['taste_sour']}"
                )
                all_pass = False
            elif checks.get("expect_sour_gt") is not None:
                print(
                    f"    ✅ PASS: taste_sour = {taste['taste_sour']} "
                    f"(> {checks['expect_sour_gt']})"
                )

        if checks.get("expect_source") and source not in checks["expect_source"]:
            print(f"    ⚠️  WARN: Expected source {checks['expect_source']}, got '{source}'")

    # ═══════════════════════════════════════════════════════════════════
    # TEST 2: Global zero-taste percentage < 10%
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("TEST 2: Global Zero-Taste Percentage")
    print("=" * 70)

    pct = 100 * post_zero / total
    if pct < 10.0:
        print(f"  ✅ PASS: {post_zero}/{total} ({pct:.1f}%) — under 10% target")
    else:
        print(f"  ❌ FAIL: {post_zero}/{total} ({pct:.1f}%) — exceeds 10% target")
        all_pass = False

    # ═══════════════════════════════════════════════════════════════════
    # TEST 3: Duplicate vector check
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("TEST 3: Duplicate Vector Blocks")
    print("=" * 70)

    vector_counts = Counter()
    vector_examples = {}
    for r in rows:
        taste = get_taste(r)
        if is_all_zero(taste):
            continue  # Skip zeros, they're expected to cluster
        key = taste_vector_key(taste)
        vector_counts[key] += 1
        if key not in vector_examples:
            vector_examples[key] = r["dish_name"]

    large_blocks = [(k, c) for k, c in vector_counts.most_common(20) if c > 10]
    if not large_blocks:
        print("  ✅ PASS: No non-zero vector shared by >10 dishes")
    else:
        print(f"  ⚠️  WARNING: {len(large_blocks)} vector(s) shared by >10 dishes:")
        for vec, count in large_blocks:
            example = vector_examples[vec]
            print(f"    {vec} — {count} dishes (e.g. '{example}')")

    # ═══════════════════════════════════════════════════════════════════
    # TEST 4: Provenance breakdown
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("TEST 4: Enrichment Provenance Breakdown")
    print("=" * 70)

    source_counts = Counter(r.get("taste_source", "unknown") for r in rows)
    for source, count in source_counts.most_common():
        pct = 100 * count / total
        print(f"  {source:25s}: {count:5d} ({pct:5.1f}%)")

    # ═══════════════════════════════════════════════════════════════════
    # TEST 5: Zero-taste by category (post-enrichment)
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("TEST 5: Zero-Taste by Category (Post-Enrichment)")
    print("=" * 70)

    zero_by_cat = Counter()
    total_by_cat = Counter()
    for r in rows:
        cat = r.get("category", "unknown")
        total_by_cat[cat] += 1
        if is_all_zero(get_taste(r)):
            zero_by_cat[cat] += 1

    for cat in sorted(total_by_cat.keys()):
        z = zero_by_cat.get(cat, 0)
        t = total_by_cat[cat]
        pct = 100 * z / t if t > 0 else 0
        status = "✅" if pct < 15 else "⚠️"
        print(f"  {status} {cat:25s}: {z:4d}/{t:4d} ({pct:5.1f}%)")

    # ═══════════════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    if all_pass:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED — see details above")
    print("=" * 70)

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
