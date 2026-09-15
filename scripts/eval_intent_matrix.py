"""
Intent-extraction evaluation matrix.

Runs a fixed phrase set through the configured extractor and reports, per phrase,
what was extracted, whether Groq answered or the keyword fallback did, and - for
phrases with a known correct exclusion set - whether the allergens were right.

    python scripts/eval_intent_matrix.py                 # markdown to stdout
    python scripts/eval_intent_matrix.py --out report.md

Makes one live Groq API call per phrase against the free-tier quota.

Replaces scratch/run_matrix_v3.py, whose summary line printed
len(phrases) / len(phrases) unconditionally and labelled every row "Groq" even
when the keyword fallback answered. Every score here is computed, not asserted.
"""

import argparse
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tier_1.groq_extractor import GroqExtractorImpl  # noqa: E402

# Open-ended phrasings, scored on whether anything structured came back.
OPEN_ENDED = [
    "I'm craving something sweet",
    "something spicy please",
    "I want comfort food",
    "give me something light and refreshing",
    "I want seafood or fish",
    "something with chicken",
    "keep it under 500 rupees",
    "cheap eats",
    "I don't have much money",
    "something salty and savory",
    "I want dessert",
    "i need a heavy protein meal for the gym",
    "give me a cheap burger",
    "i feel like having pasta today",
    "healthy low calorie meal",
    "just want a snack, 100 rupees max",
    "gym food with high protein under 800",
    "sweet and creamy dessert under 500",
]

# Phrasings with a known correct exclusion set (carried over from the retired
# root-level test_suite.py). Correct when the expected set is a subset of what
# was extracted, matching that suite's original semantics.
ALLERGEN_CASES = [
    ("I'm vegetarian", {"meat"}),
    ("no dairy please", {"dairy"}),
    ("I'm vegan", {"meat", "dairy", "egg"}),
    ("nothing with nuts, I'm allergic", {"nuts"}),
    ("under 1000 without cheese", {"dairy"}),
    ("food under 300 rupees, no dairy", {"dairy"}),
    ("I am vegetarian, no meat no chicken", {"meat"}),
    ("cheap food without nuts", {"nuts"}),
    ("high protein food, I am allergic to shellfish", {"shellfish"}),
    ("something spicy for dinner, no gluten", {"gluten"}),
    ("no beef or pork under 600", {"meat"}),
    ("no milk no cheese under 200", {"dairy"}),
    ("no eggs for me", {"egg"}),
    ("seafood allergy", {"fish"}),
    ("shrimp and fish are bad for me", {"shellfish", "fish"}),
    ("no wheat gluten free please 400", {"gluten"}),
    ("I cant eat mutton", {"meat"}),
]


def structured_fields(intent) -> list[str]:
    """Names of the structured fields the extractor actually populated."""
    found = []
    if intent.budget_max_pkr:
        found.append("budget")
    if intent.allergens_pruned:
        found.append("allergens")
    if any(v > 0 for v in intent.mood_vector.model_dump().values()):
        found.append("mood")
    if intent.is_vegan or intent.is_vegetarian:
        found.append("diet")
    if intent.preferred_category:
        found.append("category")
    return found


def run() -> str:
    extractor = GroqExtractorImpl()

    # Record every time the keyword fallback answers, so each row's path is
    # observed rather than assumed.
    fallback_calls: list[str] = []
    real_fallback = extractor.fallback.extract

    def tracking_fallback(text):
        fallback_calls.append(text)
        return real_fallback(text)

    extractor.fallback.extract = tracking_fallback

    rows = []
    for phrase, expected in [(p, None) for p in OPEN_ENDED] + ALLERGEN_CASES:
        before = len(fallback_calls)
        start = time.perf_counter()
        intent = extractor.extract(phrase)
        elapsed = time.perf_counter() - start
        rows.append(
            {
                "phrase": phrase,
                "intent": intent,
                "elapsed": elapsed,
                "path": "keyword fallback" if len(fallback_calls) > before else "Groq",
                "fields": structured_fields(intent),
                "expected": expected,
            }
        )

    lines = [
        "# Intent Extraction Matrix",
        "",
        "| Phrase | Budget | Allergens | Mood | Diet | Category "
        "| Expected allergens | Path | Time |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        i = r["intent"]
        mood = ", ".join(f"{k} {v:g}" for k, v in i.mood_vector.model_dump().items() if v > 0)
        diet = "vegan" if i.is_vegan else ("vegetarian" if i.is_vegetarian else "")
        if r["expected"] is None:
            verdict = ""
        else:
            ok = r["expected"] <= set(i.allergens_pruned)
            verdict = ("correct " if ok else "WRONG ") + ", ".join(sorted(r["expected"]))
        lines.append(
            f"| `{r['phrase']}` | {i.budget_max_pkr or ''} | {', '.join(i.allergens_pruned)} "
            f"| {mood} | {diet} | {i.preferred_category or ''} | {verdict} "
            f"| {r['path']} | {r['elapsed']:.2f}s |"
        )

    open_rows = [r for r in rows if r["expected"] is None]
    case_rows = [r for r in rows if r["expected"] is not None]
    meaningful = sum(1 for r in open_rows if r["fields"])
    correct = sum(1 for r in case_rows if r["expected"] <= set(r["intent"].allergens_pruned))
    groq_rows = [r for r in rows if r["path"] == "Groq"]
    groq_times = [r["elapsed"] for r in groq_rows]

    lines += [
        "",
        "## Summary",
        "",
        "- Open-ended phrases with at least one structured field: "
        f"**{meaningful} / {len(open_rows)}**",
        f"- Allergen cases with the expected exclusions: **{correct} / {len(case_rows)}**",
        f"- Answered by Groq: **{len(groq_rows)} / {len(rows)}** "
        f"(keyword fallback: {len(rows) - len(groq_rows)})",
    ]
    if groq_times:
        lines.append(
            f"- Groq latency: median {statistics.median(groq_times):.2f}s, "
            f"max {max(groq_times):.2f}s"
        )
    if extractor.client is None:
        lines.append("- GROQ_API_KEY is not set, so every row used the keyword fallback.")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, help="write the markdown report to this file")
    args = parser.parse_args()

    report = run()
    if args.out:
        args.out.write_text(report, encoding="utf-8")
        print(f"Report written to {args.out}")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(report)


if __name__ == "__main__":
    main()
