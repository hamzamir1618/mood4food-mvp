from unittest.mock import patch

import fakeredis
import uvicorn

from orchestrator import app

# Apply all the same monkeypatches as test_e2e_pipeline.py
fake_redis = fakeredis.FakeRedis(decode_responses=True)
p1 = patch("tier_1.contracts.session_store.get_redis", return_value=fake_redis)
p2 = patch("tier_3.fulfillment_engine.get_redis", return_value=fake_redis)


def mock_ingestion(raw_input=None, audio_path=None, image_path=None):
    if raw_input and "1 rupee" in str(raw_input).lower():
        budget = 1
    elif raw_input and "relax" in str(raw_input).lower():
        budget = 100
    else:
        budget = 1000

    return {
        "query_intent": raw_input or "test query",
        "hard_constraints": {"budget_max_pkr": budget, "allergens": []},
        "soft_constraints": {"mood_vector_seed": "spicy", "direct_dish_prompt": ""},
    }


def mock_anchoring(intent):
    budget = intent.get("hard_constraints", {}).get("budget_max_pkr", 1000)

    if budget == 1:
        # Empty state scenario
        return {
            "source_intent": intent,
            "safe_candidates": [],
            "soft_constraints": intent.get("soft_constraints", {}),
            "message": "Nothing matched your constraints.",
        }

    message = (
        ("Nothing matched exactly, so we widened your budget slightly — here's the closest match")
        if budget < 500
        else ""
    )
    return {
        "source_intent": intent,
        "safe_candidates": [
            {
                "dish_id": "fixture_1",
                "name": "Afghan Single Chicken Tikka Burger",
                "price_pkr": 330.0,
                "category": "fast_food",
                "taste_profile": {
                    "sweet": 0.0,
                    "salty": 0.5,
                    "sour": 0.0,
                    "bitter": 0.0,
                    "umami": 0.7,
                    "spice": 0.5,
                },
                "macros": {"protein_g": 34.3, "calories": 491.7},
                "allergens": [],
                "ingredients": ["Chicken"],
            },
            {
                "dish_id": "fixture_2",
                "name": "Spicy & Sour Chicken Tom Yum Gai",
                "price_pkr": 1075.0,
                "category": "chinese_asian",
                "taste_profile": {
                    "sweet": 0.0,
                    "salty": 0.0,
                    "sour": 0.8,
                    "bitter": 0.0,
                    "umami": 0.6,
                    "spice": 0.8,
                },
                "macros": {"protein_g": 60.0, "calories": 860.5},
                "allergens": [],
                "ingredients": ["Chocolate"],
            },
            {
                "dish_id": "fixture_3",
                "name": "Cheese Sauce",
                "price_pkr": 95.0,
                "category": "other",
                "taste_profile": {
                    "sweet": 0.0,
                    "salty": 0.3,
                    "sour": 0.0,
                    "bitter": 0.0,
                    "umami": 0.5,
                    "spice": 0.0,
                },
                "macros": {"protein_g": 19.1, "calories": 551.0},
                "allergens": ["dairy"],
                "ingredients": ["Chicken"],
            },
        ],
        "soft_constraints": intent.get("soft_constraints", {}),
        "message": message,
    }


p3 = patch("tier_1.multi_modal_ingestion.run_ingestion_pipeline", side_effect=mock_ingestion)
p4 = patch("tier_1.symbolic_anchoring.run_anchoring_pipeline", side_effect=mock_anchoring)

p1.start()
p2.start()
p3.start()
p4.start()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
