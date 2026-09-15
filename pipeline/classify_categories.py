"""
Per-dish cuisine classification and typical ingredients (Phase 1).

Sends every dish — restaurant name, dish name and a short menu description — to
the project's free Groq model and records one category from a fixed list,
whether the dish name looks damaged by OCR, and the dish's typical ingredients
from the controlled vocabulary in pipeline.ingredients. Answers are cached per dish in
data/cache/category_llm.json, so the pass can be stopped and resumed without
asking about any dish twice.

    python -m pipeline.classify_categories              # every dish not yet cached
    python -m pipeline.classify_categories --limit 80   # a small trial

Sends 30 dishes per request and paces itself under the free tier's
tokens-per-minute limit. If Groq asks for a long wait (a daily limit), it saves
what it has and stops; run it again later to continue.

Everything this returns is an automated estimate. The build records it with
category_source / ingredients_source = "llm:<model>" so it is never presented
as a human judgement or as a restaurant-confirmed recipe.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone

import groq

from config import settings
from pipeline import paths
from pipeline.ingredients import SPELLING_TO_NAMES, VOCABULARY
from pipeline.sources import load_handoff, load_master

MODEL = "openai/gpt-oss-120b"
PROMPT_VERSION = "2026-09-14.4"
BATCH_SIZE = 25
MIN_BATCH = 5
TOKENS_PER_MINUTE = 8000
MAX_ATTEMPTS = 3
LONGEST_WAIT_S = 7200  # longer waits than this: save and stop (run again later to resume)

CATEGORIES = (
    "desi_traditional",
    "afghan",
    "middle_eastern",
    "chinese_asian",
    "continental_upscale",
    "fast_food",
    "pizza",
    "sandwich",
    "cafe_bakery",
    "beverages",
    "add_ons",
)

SYSTEM_PROMPT = f"""You classify restaurant dishes from Islamabad, Pakistan into exactly one cuisine category.

- desi_traditional: Pakistani / North Indian mains — karahi, biryani, nihari, handi, qorma, daal, haleem, sajji, BBQ tikka and seekh kebab, stuffed naan or paratha served as a meal
- afghan: Afghan and Pashtun cuisine — Kabuli or Turkmen pulao, mantu, bolani, namkeen rosh, namkeen tikka or karahi, Shinwari karahi, pata tikka, dumpukht, and Afghan-style kebabs and tikka at Afghan or Shinwari restaurants. Not fast food that merely has "Afghan" in its name.
- middle_eastern: Arab, Lebanese, Levantine and Turkish — shawarma, mandi, kabsa, hummus, fattoush, kebbe, fatayer, pide, shish tawook, Arabic grills and rice
- chinese_asian: Chinese, Thai, Japanese, Korean and other East or Southeast Asian
- continental_upscale: European and American mains — steak, pasta, grilled fish or chicken with sauces, soups, salads
- fast_food: burgers, fries, fried chicken, wings, nuggets, wraps, rolls, broast
- pizza
- sandwich: sandwiches, subs, clubs, paninis
- cafe_bakery: desserts and sweets of any cuisine (kheer, kulfi, halwa, kunafa, cakes), pastries, bakery items, breakfast plates
- beverages: drinks of any kind
- add_ons: sauces, dips, toppings, raita, and plain bread or plain rice ordered as a side
- unknown: only when the name is too damaged to tell what the dish is

Soups and salads belong to the cuisine they come from — Turkish lentil soup is middle_eastern, Caesar salad is continental_upscale, hot and sour soup is chinese_asian. They are never cafe_bakery.

Use the restaurant name as context, but judge each dish on its own: many restaurants serve several cuisines.
Also report whether the dish name looks damaged by OCR: garbled or made-up words, stray symbols, or fragments of another script.

Finally, list the dish's ingredients using ONLY names from this list. First include every ingredient the dish name or description itself mentions (a 'Feta Cheese Salad' has cheese). Then add the main ingredients it is normally made with in Pakistani restaurants (shakshuka and omelettes have egg):
{", ".join(VOCABULARY)}
Include ingredients that carry common allergens even when the name does not mention them: ghee or butter in curries, yogurt in marinades, nut paste in kormas, egg in batters, soy, oyster or fish sauce in Chinese and Thai dishes.
Include pork or alcohol ONLY if the name or description explicitly says so — restaurants here are halal by default.
Leave out salt and dry spices. At most 10 ingredients. Use an empty list when the name is too damaged to tell.

Return JSON only: {{"results": [{{"id": <id>, "category": "<one of: {", ".join(CATEGORIES)}, unknown>", "name_damaged": true or false, "ingredients": ["<name from the list>", ...]}}]}}"""


def load_cache() -> dict:
    if paths.CATEGORY_CACHE.exists():
        return json.loads(paths.CATEGORY_CACHE.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict) -> None:
    paths.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = paths.CATEGORY_CACHE.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(paths.CATEGORY_CACHE)


def retry_after_seconds(exc: groq.RateLimitError) -> float:
    try:
        return float(exc.response.headers.get("retry-after", 30))
    except (AttributeError, TypeError, ValueError):
        return 30.0


def ask(
    client: groq.Groq, batch: list[dict], descriptions: dict, reasoning_low: bool
) -> tuple[list, int]:
    items = []
    for i, r in enumerate(batch):
        item = {"id": i, "restaurant": r["restaurant_name"], "dish": r["dish_name"]}
        desc = descriptions.get(r["dish_uid"], "")
        if desc:
            item["description"] = desc[:100]
        items.append(item)
    kwargs = {
        "model": MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(items, ensure_ascii=False)},
        ],
    }
    if reasoning_low:
        kwargs["reasoning_effort"] = "low"
    resp = client.chat.completions.create(**kwargs)
    results = json.loads(resp.choices[0].message.content).get("results", [])
    return results, (resp.usage.total_tokens if resp.usage else 0)


def classify(limit: int | None = None) -> dict:
    if not settings.GROQ_API_KEY:
        sys.exit("GROQ_API_KEY is not set; nothing classified.")
    client = groq.Groq(api_key=settings.GROQ_API_KEY, timeout=120)
    rows = load_handoff()
    descriptions = {
        uid: (m.get("dish_description") or "").strip() for uid, m in load_master().items()
    }
    cache = load_cache()
    todo = [r for r in rows if cache.get(r["dish_uid"], {}).get("prompt_version") != PROMPT_VERSION]
    if limit:
        todo = todo[:limit]
    total, done, tokens_used = len(todo), 0, 0
    attempts: dict[str, int] = {}
    reasoning_low = True
    size = BATCH_SIZE
    print(f"{total} dishes to classify ({len(rows) - total} already cached)", flush=True)

    while todo:
        batch, todo = todo[:size], todo[size:]
        started = time.monotonic()
        failure = ""
        try:
            results, tokens = ask(client, batch, descriptions, reasoning_low)
        except groq.BadRequestError as exc:
            if reasoning_low and "reasoning_effort" in str(exc):
                reasoning_low = False
                todo = batch + todo
                continue
            results, tokens, failure = [], 0, f"request rejected: {str(exc)[:200]}"
        except groq.RateLimitError as exc:
            wait = retry_after_seconds(exc)
            if wait > LONGEST_WAIT_S:
                save_cache(cache)
                print(
                    f"Rate limit asks for {wait:.0f}s — likely the daily limit. Saved {done} answers; run again later."
                )
                return cache
            print(f"  rate limited; waiting {wait:.0f}s", flush=True)
            time.sleep(wait + 1)
            todo = batch + todo
            continue
        except (
            groq.APIConnectionError,
            groq.APITimeoutError,
            json.JSONDecodeError,
            AttributeError,
        ) as exc:
            results, tokens, failure = [], 0, f"request failed: {str(exc)[:200]}"
            time.sleep(5)

        # A rejected batch (typically JSON-mode validation on a long reply) is retried
        # in smaller batches; only at the smallest size do its dishes use up attempts.
        if failure and size > MIN_BATCH:
            size = max(MIN_BATCH, size // 2)
            print(f"  {failure} -> retrying in batches of {size}", flush=True)
            todo = batch + todo
            continue
        if failure:
            print(f"  {failure}", flush=True)
        elif size < BATCH_SIZE:
            size = min(BATCH_SIZE, size + 5)

        tokens_used += tokens
        by_id = {x.get("id"): x for x in results if isinstance(x, dict)}
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for i, r in enumerate(batch):
            x = by_id.get(i)
            valid = (
                x is not None
                and x.get("category") in (*CATEGORIES, "unknown")
                and isinstance(x.get("name_damaged"), bool)
                and isinstance(x.get("ingredients"), list)
            )
            if valid:
                cache[r["dish_uid"]] = {
                    "category": x["category"],
                    "name_damaged": x["name_damaged"],
                    # Known spellings map to their vocabulary name ("feta" -> "cheese");
                    # anything else is dropped and recorded, never guessed at.
                    "ingredients": list(
                        dict.fromkeys(
                            n
                            for i in x["ingredients"]
                            for n in SPELLING_TO_NAMES.get(str(i).strip().lower(), ())
                        )
                    ),
                    "ingredients_rejected": [
                        i
                        for i in x["ingredients"]
                        if str(i).strip().lower() not in SPELLING_TO_NAMES
                    ],
                    "model": MODEL,
                    "prompt_version": PROMPT_VERSION,
                    "classified_at": stamp,
                }
                done += 1
                continue
            attempts[r["dish_uid"]] = attempts.get(r["dish_uid"], 0) + 1
            if attempts[r["dish_uid"]] < MAX_ATTEMPTS:
                todo.append(r)
            else:
                print(
                    f"  no valid answer after {MAX_ATTEMPTS} tries: {r['restaurant_name']} | {r['dish_name']}",
                    flush=True,
                )
        save_cache(cache)
        print(f"  {done}/{total} classified, {tokens_used} tokens so far", flush=True)

        # Stay under the tokens-per-minute limit.
        needed = tokens / TOKENS_PER_MINUTE * 60
        elapsed = time.monotonic() - started
        if needed > elapsed:
            time.sleep(needed - elapsed)

    print(f"Finished: {done} classified this run, {tokens_used} tokens.")
    return cache


def main():
    parser = argparse.ArgumentParser(
        description="Classify every dish's cuisine with Groq (resumable)."
    )
    parser.add_argument("--limit", type=int, help="classify at most this many dishes")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    classify(args.limit)


if __name__ == "__main__":
    main()
