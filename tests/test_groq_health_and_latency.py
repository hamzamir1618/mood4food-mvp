import time

import pytest

from config import settings
from tier_1.contracts.schemas import GroundedIntent
from tier_1.groq_extractor import GroqExtractorImpl


@pytest.mark.skipif(not settings.GROQ_API_KEY, reason="GROQ_API_KEY is not set")
def test_groq_extraction_returns_valid_output():
    extractor = GroqExtractorImpl()
    result = extractor.extract("I want a cheap spicy burger")
    assert isinstance(result, GroundedIntent)
    assert result.craving is not None
    assert result.budget_max_pkr is not None or result.mood_vector.spice > 0


@pytest.mark.skipif(not settings.GROQ_API_KEY, reason="GROQ_API_KEY is not set")
def test_groq_extraction_latency():
    extractor = GroqExtractorImpl()
    phrases = [
        "I want something sweet",
        "Craving a burger under 500",
        "Healthy salad please",
        "Spicy chicken wings",
        "Vegan wrap",
        "Lots of cheese and meat",
        "Just a cold drink",
        "Comfort food without tomatoes",
        "Fish and chips",
        "Ice cream",
    ]
    latencies = []

    for phrase in phrases:
        start_time = time.time()
        extractor.extract(phrase)
        latencies.append(time.time() - start_time)

    avg_latency = sum(latencies) / len(latencies)
    print(f"\nAverage Groq latency over 10 calls: {avg_latency:.2f} seconds")

    # Assert average latency is under 3 seconds (vs old ~15s Ollama baseline)
    assert avg_latency < 3.0, f"Average latency {avg_latency:.2f}s exceeded threshold of 3.0s"
