"""
Scripted conversations against the real dataset, for demos and the report.

    DEPLOY_MODE=test python -m scripts.conversation_demo

Runs each script through /chat in-process (Tier 1 on the real Neo4j data, sessions in
fakeredis). DEPLOY_MODE=test uses the keyword extractor, so no Groq quota is spent.
Prints every turn: what the concierge said, the question and why, the pick, and how
long the turn took.
"""

import logging
import sys
import time

import fakeredis
from fastapi.testclient import TestClient

from tier_1.contracts import session_store

SCRIPTS = [
    ("A vague request", [{"text": "I'm hungry"}, "first", "first", {"critique": "cheaper"}]),
    ("A specific request", [{"text": "spicy chicken karahi under 1500"}, {"critique": "milder"}]),
    ("Refining in words", [{"text": "pizza"}, "skip", {"text": "something lighter"}]),
]


def _show(reply: dict, took_ms: float) -> None:
    if reply.get("reply"):
        print(f"   concierge: {reply['reply']}")
    if reply["type"] == "question":
        q = reply["question"]
        chips = " | ".join(c["label"] for c in q["chips"])
        print(f"   asks: {q['text']}  [{chips}]  ({q['why']})  leading: {reply['leading']}")
    else:
        dish = reply["recommendation"].get("winning_dish") or {}
        price = f"Rs {dish.get('price_pkr', 0):,.0f}"
        print(f"   picks: {dish.get('name')}  {price}  ({dish.get('category')})")
    print(f"   ({took_ms:.0f} ms)")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    logging.disable(logging.WARNING)
    session_store._redis_client = fakeredis.FakeRedis(decode_responses=True)
    from orchestrator import app

    for title, steps in SCRIPTS:
        print(f"\n== {title}")
        client, reply = TestClient(app), None
        for step in steps:
            if step == "first":
                if reply["type"] != "question":
                    continue
                q = reply["question"]
                step = {"answer": {"question": q["id"], "value": q["chips"][0]["value"]}}
                print(f" > {q['chips'][0]['label']}")
            elif step == "skip":
                if reply["type"] != "question":
                    continue
                step = {"skip": True}
                print(" > (just pick for me)")
            else:
                print(f" > {step}")
            start = time.perf_counter()
            response = client.post("/chat", json=step)
            took = 1000 * (time.perf_counter() - start)
            if response.status_code != 200:
                print(f"   HTTP {response.status_code}: {response.text[:200]}")
                break
            reply = response.json()
            _show(reply, took)


if __name__ == "__main__":
    main()
