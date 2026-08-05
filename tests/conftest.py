import pytest

from api.rate_limit import limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset the slowapi rate limiter before every test so tests don't pollute each other."""
    limiter.reset()
