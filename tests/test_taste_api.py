"""
GET/POST /taste/start (api/taste.py): asking a first-time reader what they like.

No database: the six dishes are stubbed and the session lives in fakeredis, so what is under
test is the endpoint's own contract — what it shows, what it refuses, and what it keeps.
"""

import fakeredis
import pytest
from fastapi.testclient import TestClient

from accounts import taste_start
from accounts.models import TASTE_DIMS

FLAVOURS = {
    "brownie": {"sweet": 0.9, "bitter": 0.6},
    "spicy beef": {"umami": 0.8, "spice": 0.8},
    "lemon rice": {"sour": 0.8},
    "sweet sour beef": {"sweet": 0.8, "umami": 0.8},
    "burger": {"salty": 0.5, "umami": 0.7},
    "masala": {"spice": 0.6},
}
SIX = [
    {
        "dish_id": name.replace(" ", "-"),
        "name": name.title(),
        "restaurant_name": f"{name} house",
        "restaurant_area": "F-7",
        "category": "desi_traditional",
        **{d: 0.0 for d in TASTE_DIMS},
        **flavour,
    }
    for name, flavour in FLAVOURS.items()
]


@pytest.fixture
def client(monkeypatch):
    fake = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("tier_1.contracts.session_store.get_redis", lambda: fake)
    monkeypatch.setattr(taste_start, "offered", lambda *a, **k: SIX)

    from orchestrator import app

    return TestClient(app)


def test_it_offers_six_dishes_and_says_they_are_stock_photographs(client):
    body = client.get("/taste/start").json()
    assert body["known"] is False
    assert len(body["dishes"]) == 6
    for card in body["dishes"]:
        assert card["name"] and card["restaurant_name"] and card["image_url"]
        assert card["is_rep_image"] is True  # no dish here has a photograph of its own


def test_the_cards_never_show_the_flavour_they_are_asking_about(client):
    """Printing "spicy" on the card would collect the answer we handed the reader."""
    card = client.get("/taste/start").json()["dishes"][0]
    assert not set(card) & set(TASTE_DIMS)


def test_one_tap_is_not_enough_to_read_a_taste_from(client):
    assert client.post("/taste/start", json={"dish_ids": ["brownie"]}).status_code == 422
    unknown = client.post("/taste/start", json={"dish_ids": ["nothing", "here"]})
    assert unknown.status_code == 400


def test_the_taps_are_read_back_in_words_and_kept_for_the_session(client):
    reply = client.post("/taste/start", json={"dish_ids": ["spicy-beef", "masala"]})
    assert reply.status_code == 200
    body = reply.json()
    assert "spicy" in body["said"]
    assert body["taste"]["spice"] == pytest.approx(0.7)
    assert body["importance"]["spice"] > body["importance"]["bitter"]
    # ...and the app now knows something about this reader, so it stops asking.
    assert client.get("/taste/start").json()["known"] is True


def test_a_reader_who_skips_is_left_exactly_as_they_were(client):
    client.get("/taste/start")
    assert client.get("/taste/start").json()["known"] is False


def test_the_dishes_being_unreachable_is_said_plainly(client, monkeypatch):
    monkeypatch.setattr(taste_start, "offered", lambda *a, **k: [])
    assert client.get("/taste/start").status_code == 503
