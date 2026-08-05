import fakeredis
import httpx

from tier_3.fulfillment_engine import OSMRestaurantProvider


def test_restaurant_provider_caching(monkeypatch):
    # Mock redis
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("tier_3.fulfillment_engine.get_redis", lambda: fake_redis)

    # Mock httpx
    call_count = 0

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"elements": [{"tags": {"name": "Test Place"}, "lat": 1.0, "lon": 1.0}]}

    def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return MockResponse()

    monkeypatch.setattr(httpx, "post", mock_post)

    provider = OSMRestaurantProvider()

    # First call - cache miss, triggers API
    res1 = provider.find_nearby("Pizza")
    assert call_count == 1
    assert len(res1) == 1
    assert res1[0].name == "Test Place"

    # Second call - cache hit, no API trigger
    res2 = provider.find_nearby("Pizza")
    assert call_count == 1
    assert len(res2) == 1

    # Confirm cache TTL is set correctly (600 seconds)
    ttl = fake_redis.ttl("osm_cache:Pizza:islamabad")
    assert ttl > 0 and ttl <= 600
