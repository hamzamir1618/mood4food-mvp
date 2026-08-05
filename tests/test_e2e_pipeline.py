import pytest
from fastapi.testclient import TestClient

from orchestrator import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_e2e_env(monkeypatch, tmp_path):
    import fakeredis

    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("tier_1.contracts.session_store.get_redis", lambda: fake_redis)

    # Ensure uploads dir exists (file is tracked in git)
    from api.submit import UPLOADS_DIR

    UPLOADS_DIR.mkdir(exist_ok=True)

    # Mock the external AI pipelines to provide deterministic inputs for debate
    def mock_ingestion(raw_input=None, audio_path=None, image_path=None):
        budget = 100 if raw_input and "relax" in str(raw_input).lower() else 1000
        return {
            "query_intent": raw_input or "audio query",
            "hard_constraints": {"budget_max_pkr": budget, "allergens": []},
            "soft_constraints": {"mood_vector_seed": "spicy", "direct_dish_prompt": ""},
        }

    def mock_anchoring(intent):
        budget = intent.get("hard_constraints", {}).get("budget_max_pkr", 1000)
        # If budget is 100, we "fail" and have to relax
        message = "Relaxed constraints" if budget < 500 else ""
        return {
            "source_intent": intent,
            "safe_candidates": [
                {
                    "dish_id": "dish1",
                    "name": "Spicy Chicken",
                    "price_pkr": 500,
                    "category": "Main",
                    "taste_profile": {
                        "spice": 1.0,
                        "sweet": 0.0,
                        "salty": 0.0,
                        "sour": 0.0,
                        "bitter": 0.0,
                        "umami": 0.0,
                    },
                    "protein_g": 30.0,
                    "calories": 400.0,
                    "allergens": [],
                    "ingredients": ["Chicken"],
                },
                {
                    "dish_id": "dish2",
                    "name": "Sweet Dessert",
                    "price_pkr": 600,
                    "category": "Dessert",
                    "taste_profile": {
                        "spice": 0.0,
                        "sweet": 1.0,
                        "salty": 0.0,
                        "sour": 0.0,
                        "bitter": 0.0,
                        "umami": 0.0,
                    },
                    "protein_g": 5.0,
                    "calories": 300.0,
                    "allergens": [],
                    "ingredients": ["Sugar"],
                },
            ],
            "soft_constraints": intent.get("soft_constraints", {}),
            "message": message,
        }

    monkeypatch.setattr("tier_1.multi_modal_ingestion.run_ingestion_pipeline", mock_ingestion)
    monkeypatch.setattr("tier_1.symbolic_anchoring.run_anchoring_pipeline", mock_anchoring)

    # Mock Recipes
    from tier_3.fulfillment_engine import RECIPES

    monkeypatch.setitem(
        RECIPES,
        "Spicy Chicken",
        {
            "prep_time": "10 min",
            "cook_time": "20 min",
            "servings": 1,
            "difficulty": "Easy",
            "steps": ["Cook"],
            "grocery_list": [],
        },
    )
    monkeypatch.setitem(
        RECIPES,
        "Sweet Dessert",
        {
            "prep_time": "5 min",
            "cook_time": "0 min",
            "servings": 1,
            "difficulty": "Easy",
            "steps": ["Serve"],
            "grocery_list": [],
        },
    )

    # We DO NOT mock debate (tier_2) or fulfillment (tier_3) because we want to test
    # the actual product behavior.

    yield


def test_e2e_flow():
    # 1. Submit text query
    res_submit = client.post("/submit", data={"text": "I want something spicy"})
    assert res_submit.status_code == 200
    submit_data = res_submit.json()

    assert "winning_dish" in submit_data
    assert submit_data["winning_dish"]["name"] == "Spicy Chicken"
    assert len(submit_data.get("top_candidates", [])) > 0
    runners_up = submit_data["top_candidates"]
    assert any(c["name"] == "Sweet Dessert" for c in runners_up)

    # 2. Recalculate with different persona (e.g. sweet_tooth)
    # We expect Sweet Dessert to win now because persona dictates sweet taste
    res_recalc = client.post(
        "/recalculate",
        json={"w_health": 0.0, "w_budget": 0.0, "w_taste": 1.0, "persona": "sweet_tooth"},
    )
    assert res_recalc.status_code == 200
    recalc_data = res_recalc.json()
    assert recalc_data["winning_dish"]["name"] == "Sweet Dessert"

    # 3. Alternate
    # If Sweet Dessert was winner, and we reject it, it should go back to Spicy Chicken
    res_alt = client.post("/alternate", json={"already_rejected": ["dish2"]})
    assert res_alt.status_code == 200
    alt_data = res_alt.json()
    assert alt_data["winning_dish"]["name"] == "Spicy Chicken"

    # 4. Fulfillment endpoint
    res_fulfill = client.get("/decision_blueprint")
    assert res_fulfill.status_code == 200
    fulfill_data = res_fulfill.json()
    assert fulfill_data["winning_dish"]["name"] == "Spicy Chicken"

    # Verify deep links are present
    assert "fulfillment" in fulfill_data
    fulfillment = fulfill_data["fulfillment"]
    restaurants = fulfillment.get("restaurants", [])
    # Even if there are none, we should check that the API returns the schema properly
    for rest in restaurants:
        assert "foodpanda_link" in rest or "whatsapp_link" in rest or "name" in rest


def test_e2e_constraint_relaxation():
    # Submit query engineered to trigger relaxation
    res = client.post("/submit", data={"text": "relax budget"})
    assert res.status_code == 200
    data = res.json()
    # Our mock emits "Relaxed constraints" if budget < 500
    assert "relaxation_notice" in data
    assert data["relaxation_notice"] == "Relaxed constraints"


def test_e2e_audio_submission():
    # Submit uploads/Recording.m4a via audio path
    from api.submit import UPLOADS_DIR

    audio_path = UPLOADS_DIR / "Recording.m4a"
    with open(audio_path, "rb") as f:
        res = client.post("/submit", files={"audio": ("Recording.m4a", f, "audio/mp4")})
    assert res.status_code == 200
    data = res.json()
    assert "winning_dish" in data
    assert "utility_breakdown" in data
