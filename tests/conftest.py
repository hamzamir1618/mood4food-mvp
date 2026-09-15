import pytest

from api.rate_limit import limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset the slowapi rate limiter before every test so tests don't pollute each other."""
    limiter.reset()


@pytest.fixture(autouse=True)
def no_clock_or_weather(monkeypatch):
    """
    The scoring context without the real clock or a weather call, so rankings are
    repeatable and no test reaches the network. Tests of the context term set the hour
    and temperature on Preferences directly.
    """
    monkeypatch.setattr("tier_2.context.local_hour", lambda now=None: None)
    monkeypatch.setattr("tier_2.context.current_temperature", lambda: None)
