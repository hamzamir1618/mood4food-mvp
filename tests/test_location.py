"""
Phase 6 locations: straight-line distances from the user's location, the /areas list,
and the location a request can send (/submit form fields, or a /chat turn's `location`).
The pipeline's first two tiers are mocked, so this runs without Neo4j, Groq or network.
"""

import fakeredis
import pytest
from fastapi.testclient import TestClient

from api.areas import group_areas
from api.location import distance_km, with_distances
from tier_1.contracts.schemas import GroundedIntent

G9 = (33.6938, 73.0302)  # G-9 Markaz


def _dish(dish_id: str, **place) -> dict:
    return {
        "dish_id": dish_id,
        "name": f"{dish_id.title()} Karahi",
        "restaurant_name": dish_id.title(),
        "category": "desi_traditional",
        "price_pkr": 900.0,
        "price_status": "trusted",
        "taste_source": "original",
        "nutrition_confidence": "high",
        "macros": {"calories": 600.0, "protein_g": 35.0, "carbs_g": 50.0, "fat_g": 25.0},
        "taste_profile": {
            "sweet": 0.1,
            "salty": 0.5,
            "sour": 0.1,
            "bitter": 0.0,
            "umami": 0.6,
            "spice": 0.7,
        },
        "ingredients": [],
        "allergens": [],
        **place,
    }


POOL = [
    _dish(
        "near",
        restaurant_area="G-9",
        location_precision="place",
        restaurant_lat=33.6914,
        restaurant_lng=73.0307,
    ),
    # geocoded outside the city: Tier 1 passes no coordinates on
    _dish("far", location_precision="unknown", restaurant_lat=None, restaurant_lng=None),
]


def test_distance_is_a_straight_line_in_km():
    assert distance_km(*G9, 33.7204333, 73.0561174) == pytest.approx(3.8, abs=0.1)  # F-7
    assert distance_km(*G9, *G9) == 0.0


def test_a_restaurant_with_unknown_coordinates_gets_no_distance():
    location = {"lat": G9[0], "lng": G9[1]}
    found = with_distances(
        [
            {"restaurant_lat": 33.6918, "restaurant_lng": 73.0067},
            {"restaurant_lat": None, "restaurant_lng": None},
        ],
        location,
    )
    assert found[0]["distance_km"] == pytest.approx(2.2, abs=0.1)
    assert found[1]["distance_km"] is None
    no_location = with_distances([{"restaurant_lat": 33.7, "restaurant_lng": 73.0}], None)
    assert no_location[0]["distance_km"] is None


def test_areas_are_the_mean_of_their_restaurants_without_unknown_ones():
    got = group_areas(
        [
            {"area": "F-10", "lat": 33.69, "lng": 73.00, "precision": "area"},
            {"area": "F-10", "lat": 33.70, "lng": 73.02, "precision": "place"},
            {"area": "F-7", "lat": 33.72, "lng": 73.05, "precision": "place"},
            {"area": "Rawat", "lat": 33.49, "lng": 73.19, "precision": "place"},
            {"area": None, "lat": 22.3, "lng": 91.8, "precision": "unknown"},
        ]
    )
    assert [a["area"] for a in got] == ["F-7", "F-10", "Rawat"]  # sectors in order, then places
    assert got[1] == {"area": "F-10", "lat": 33.695, "lng": 73.01, "restaurants": 2}


@pytest.fixture
def client(monkeypatch):
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("tier_1.contracts.session_store.get_redis", lambda: fake_redis)

    def ingest(**kwargs):
        return {**GroundedIntent().model_dump(), "raw_input": kwargs.get("raw_input") or ""}

    def anchor(intent):
        return {
            "source_intent": intent,
            "safe_candidates": [dict(d) for d in POOL],
            "message": "",
        }

    monkeypatch.setattr("tier_1.multi_modal_ingestion.run_ingestion_pipeline", ingest)
    monkeypatch.setattr("tier_1.symbolic_anchoring.run_anchoring_pipeline", anchor)
    monkeypatch.setattr("tier_3.fulfillment_engine.enrich_blueprint", lambda bp: dict(bp))
    from orchestrator import app

    return TestClient(app)


def _dishes(blueprint: dict) -> dict:
    return {c["dish_id"]: c for c in blueprint["top_candidates"]}


def test_submit_with_a_location_gives_each_dish_a_distance(client):
    form = {"text": "karahi", "lat": G9[0], "lng": G9[1], "location_label": "G-9 Markaz"}
    r = client.post("/submit", data=form)
    assert r.status_code == 200, r.text
    dishes = _dishes(r.json())
    assert dishes["near"]["distance_km"] == pytest.approx(0.3, abs=0.1)
    assert dishes["near"]["restaurant_area"] == "G-9"
    assert dishes["far"]["distance_km"] is None  # never a guess
    assert r.json()["winning_dish"]["restaurant_name"]


def test_the_session_keeps_the_location_for_later_requests(client):
    client.post("/submit", data={"text": "karahi", "lat": G9[0], "lng": G9[1]})
    r = client.post("/submit", data={"text": "karahi again"})
    assert r.status_code == 200, r.text
    assert _dishes(r.json())["near"]["distance_km"] is not None


def test_half_a_location_is_refused(client):
    r = client.post("/submit", data={"text": "karahi", "lat": G9[0]})
    assert r.status_code == 400


def test_a_chat_turn_can_send_a_location(client):
    r = client.post("/chat", json={"text": "karahi", "location": {"lat": G9[0], "lng": G9[1]}})
    assert r.status_code == 200, r.text
    body = r.json()
    if body["type"] == "question":
        body = client.post("/chat", json={"skip": True}).json()
    assert _dishes(body["recommendation"])["near"]["distance_km"] is not None
