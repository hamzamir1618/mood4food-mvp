import groq
import structlog
from groq import Groq

from config import settings
from tier_1.contracts.schemas import GroundedIntent
from tier_1.intent_extractor_interface import IntentExtractor
from tier_1.keyword_extractor import KeywordExtractorImpl

logger = structlog.get_logger()

# Falling back to a model explicitly available on this API key's whitelist
GROQ_MODEL = "openai/gpt-oss-120b"


class GroqExtractorImpl(IntentExtractor):
    def __init__(self):
        self.fallback = KeywordExtractorImpl()
        self.api_key = settings.GROQ_API_KEY
        if self.api_key:
            self.client = Groq(api_key=self.api_key, timeout=5.0)
        else:
            self.client = None

    def extract(self, text: str) -> GroundedIntent:
        if not self.client:
            logger.warning(
                "Groq API key not set, falling back to keyword extractor",
                text=text,
                extractor="fallback",
            )
            return self.fallback.extract(text)

        system_prompt = """You are a food ordering assistant. Extract intent into a minimal JSON object. Omit fields if they are false, null, empty, or 0.
Fields: budget_max_pkr(float), allergens_pruned([str]), mood_vector(sweet,salty,sour,bitter,umami,spice), craving(str), is_vegan(bool), is_vegetarian(bool), is_halal(bool), preferred_category(str), preferred_category_raw_phrase(str).
IMPORTANT: For allergens_pruned, strictly map excluded items to standard categories: gluten, dairy, fish, meat, egg, nuts, soy, shellfish. (e.g. "no bread" -> ["gluten"], "no cheese" -> ["dairy"]).

Examples:
"something sweet" -> {"mood_vector": {"sweet": 1.0}, "craving": "something sweet", "preferred_category": "dessert", "preferred_category_raw_phrase": "sweet"}
"comfort food" -> {"mood_vector": {"salty": 0.5, "umami": 0.8}, "craving": "comfort food"}
"light and refreshing" -> {"mood_vector": {"sweet": 0.2, "sour": 0.5}, "craving": "light and refreshing"}
"nothing with nuts, I'm allergic" -> {"allergens_pruned": ["nuts"]}
"no dairy" -> {"allergens_pruned": ["dairy"]}
"I'm vegan" -> {"allergens_pruned": ["meat", "dairy", "egg", "honey"], "is_vegan": true, "is_vegetarian": true}
# "no meat" -> {"allergens_pruned": ["meat"], "is_vegetarian": true}
"no bread" -> {"allergens_pruned": ["gluten"]}
"halal food only" -> {"is_halal": true}
"under 500" -> {"budget_max_pkr": 500.0}
"cheap eats" -> {"budget_max_pkr": 300.0, "craving": "cheap eats"}
"I don't have much money" -> {"budget_max_pkr": 400.0}
"something with chicken" -> {"craving": "something with chicken", "preferred_category": "chicken", "preferred_category_raw_phrase": "chicken"}
"I want seafood" -> {"craving": "I want seafood", "preferred_category": "seafood", "preferred_category_raw_phrase": "seafood"}
"biryani please" -> {"craving": "biryani", "preferred_category": "biryani", "preferred_category_raw_phrase": "biryani"}
"I want dessert" -> {"mood_vector": {"sweet": 1.0}, "craving": "I want dessert", "preferred_category": "dessert", "preferred_category_raw_phrase": "dessert"}
"""
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f'"{text}" ->'},
                ],
                model=GROQ_MODEL,
                temperature=0,
                response_format={"type": "json_object"},
            )
            raw_output = chat_completion.choices[0].message.content.strip()

            intent = GroundedIntent.model_validate_json(raw_output)
            intent.raw_input = text
            logger.info("Groq extraction succeeded", text=text, extractor="groq")
            return intent
        except groq.APITimeoutError as e:
            logger.warning(
                "Groq extraction timed out, falling back to keyword extractor",
                error=str(e),
                text=text,
                extractor="fallback",
                reason="timeout",
            )
            return self.fallback.extract(text)
        except groq.RateLimitError as e:
            logger.warning(
                "Groq rate limit exceeded, falling back to keyword extractor",
                error=str(e),
                text=text,
                extractor="fallback",
                reason="rate_limit",
            )
            return self.fallback.extract(text)
        except groq.APIConnectionError as e:
            logger.warning(
                "Groq network error, falling back to keyword extractor",
                error=str(e),
                text=text,
                extractor="fallback",
                reason="network_error",
            )
            return self.fallback.extract(text)
        except groq.APIStatusError as e:
            logger.warning(
                "Groq API error, falling back to keyword extractor",
                error=str(e),
                status_code=e.status_code,
                text=text,
                extractor="fallback",
                reason="api_error",
            )
            return self.fallback.extract(text)
        except Exception as e:
            logger.warning(
                "Groq extraction failed (malformed response or unknown error), falling back to keyword extractor",
                error=str(e),
                text=text,
                extractor="fallback",
                reason="unknown_error",
            )
            return self.fallback.extract(text)
