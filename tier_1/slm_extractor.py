import httpx
import structlog

from tier_1.contracts.schemas import GroundedIntent
from tier_1.intent_extractor_interface import IntentExtractor
from tier_1.keyword_extractor import KeywordExtractorImpl

logger = structlog.get_logger()

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "phi3.5"


class SLMExtractorImpl(IntentExtractor):
    def __init__(self):
        self.fallback = KeywordExtractorImpl()

    def extract(self, text: str) -> GroundedIntent:
        prompt = f"""
You are a food ordering assistant. Extract the customer's intent from their message
into ONLY a JSON object matching this schema. If a value is unknown, use null or defaults.
{{
    "raw_input": "{text}",
    "budget_max_pkr": float (or null),
    "allergens_pruned": ["list", "of", "allergens"],
    "mood_vector": {{
        "sweet": 0.0,
        "salty": 0.0,
        "sour": 0.0,
        "bitter": 0.0,
        "umami": 0.0,
        "spice": 0.0
    }}
}}

Text: "{text}"
"""
        try:
            with httpx.Client(timeout=3.0) as client:
                response = client.post(
                    OLLAMA_URL,
                    json={
                        "model": OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                    },
                )
                response.raise_for_status()
                payload = response.json()
                raw_output = payload.get("response", "").strip()
                return GroundedIntent.model_validate_json(raw_output)
        except Exception as e:
            logger.warning(
                "SLM extraction failed, falling back to keyword extractor", error=str(e), text=text
            )
            return self.fallback.extract(text)
