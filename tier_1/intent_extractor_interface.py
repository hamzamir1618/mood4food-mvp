from abc import ABC, abstractmethod

from tier_1.contracts.schemas import GroundedIntent


class IntentExtractor(ABC):
    @abstractmethod
    def extract(self, text: str) -> GroundedIntent:
        """
        Extracts structured intent (budget, allergens, mood) from raw text.
        """
        pass


def get_extractor() -> IntentExtractor:
    from config import settings

    if settings.INTENT_EXTRACTOR == "slm":
        from tier_1.slm_extractor import SLMExtractorImpl

        return SLMExtractorImpl()
    else:
        from tier_1.keyword_extractor import KeywordExtractorImpl

        return KeywordExtractorImpl()
