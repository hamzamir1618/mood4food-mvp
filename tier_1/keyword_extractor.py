import re

from tier_1.contracts.schemas import GroundedIntent, TasteProfile
from tier_1.intent_extractor_interface import IntentExtractor


class KeywordExtractorImpl(IntentExtractor):
    def extract(self, text: str) -> GroundedIntent:
        raw_input = text
        text_lower = text.strip().lower()

        # ── Budget extraction ──
        budget = None
        match = re.search(
            r"(?:under|around|rs\.?|rupees|pkr)\s*(\d+)|\b(\d+)\s*(?:rupees|rs\.?|pkr)\b",
            text_lower,
        )
        if match:
            budget = float(match.group(1) or match.group(2))

        # ── Allergen / exclusion extraction ──
        # A named meat excludes that meat, not all meat: "mutton karahi, no chicken" had
        # removed every karahi. Tier 1 reads a vocabulary ingredient as an exclusion.
        # The allergen words were checked by the 2026-09-21 word sweep: "nut allergy" and
        # "lactose intolerant" matched nothing, so an allergy stated in words was ignored.
        exclusion_keywords = {
            "vegan": "vegan",
            "vegetarian": "vegetarian",
            "meat": "meat",
            "chicken": "chicken",
            "beef": "beef",
            "mutton": "mutton",
            "lamb": "lamb",
            "pork": "pork",
            "dairy": "dairy",
            "milk": "dairy",
            "lactose": "dairy",
            "cheese": "dairy",
            "cream": "dairy",
            "butter": "dairy",
            "yogurt": "dairy",
            "yoghurt": "dairy",
            "paneer": "dairy",
            "gluten": "gluten",
            "wheat": "gluten",
            "bread": "gluten",
            "naan": "gluten",
            "roti": "gluten",
            "pasta": "gluten",
            "nut": "nuts",
            "nuts": "nuts",
            "peanut": "nuts",
            "peanuts": "nuts",
            "almond": "nuts",
            "almonds": "nuts",
            "cashew": "nuts",
            "cashews": "nuts",
            "pistachio": "nuts",
            "pistachios": "nuts",
            "walnut": "nuts",
            "walnuts": "nuts",
            "hazelnut": "nuts",
            "hazelnuts": "nuts",
            "shellfish": "shellfish",
            "shrimp": "shellfish",
            "prawn": "shellfish",
            "prawns": "shellfish",
            "crab": "shellfish",
            "lobster": "shellfish",
            "egg": "egg",
            "eggs": "egg",
            "fish": "fish",
            "seafood": "fish",
            "soy": "soy",
            "soya": "soy",
            "sesame": "sesame",
        }

        negation_words = {
            "no",
            "without",
            "minus",
            "zero",
            "not",
            "dont",
            "don't",
            "cant",
            "can't",
            "allergic",
            "allergy",
            "skip",
        }
        stop_negation = {
            "but",
            "with",
            "plus",
            "add",
            "including",
            "contain",
            "contains",
            "want",
            "like",
            "love",
            "prefer",
            "give",
        }

        allergens_found = set()
        negated_words = set()
        negated_state = False

        words = text_lower.split()
        for i, word in enumerate(words):
            w_clean = word.strip(".,!?;:")

            # Turn off negation if we hit a contrast word
            if w_clean in stop_negation:
                negated_state = False

            # Turn on negation
            if w_clean in negation_words:
                negated_state = True
            elif negated_state:
                negated_words.add(w_clean)

            if w_clean in exclusion_keywords:
                lookahead = words[i + 1].strip(".,!?;:") if i + 1 < len(words) else ""
                if (
                    w_clean in ("vegan", "vegetarian")
                    or negated_state
                    or lookahead in {"free", "allergy", "intolerant", "intolerance"}
                ):
                    allergens_found.add(exclusion_keywords[w_clean])

            # Reset state on sentence boundaries
            if word.endswith((".", "!", "?", ";")):
                negated_state = False

        # ── Halal ──
        is_halal = bool(re.search(r"\bhalal\b", text_lower))

        # ── Mood vector seed ──
        # Whole words only ("hot" is not "photo"), and never a negated one: "not spicy" had
        # been read as spice 1.0. "Light" and "hearty" are about the meal, not its flavour
        # (tier_2/scoring.py reads them), so they no longer seed a taste.
        mood_map = {
            "spicy": TasteProfile(spice=1.0),
            "sweet": TasteProfile(sweet=1.0),
            "comfort": TasteProfile(salty=0.5, umami=0.5),
            "fresh": TasteProfile(sour=0.5, sweet=0.2),
            "crispy": TasteProfile(salty=0.5),
            "rich": TasteProfile(umami=0.8, sweet=0.2),
            "creamy": TasteProfile(sweet=0.3, umami=0.3),
            "tangy": TasteProfile(sour=1.0),
            "sour": TasteProfile(sour=1.0),
            "hot": TasteProfile(spice=1.0),
            "mild": TasteProfile(),
        }

        # A taste is negated only by a word right before it ("not spicy", "not too spicy"):
        # the exclusion scope runs on through lists, and "no chicken, something spicy" is spicy.
        mood_profile = TasteProfile()
        for keyword, profile in mood_map.items():
            said = re.search(rf"\b{keyword}\b", text_lower)
            negated = re.search(
                rf"\b(?:not|no|non|without|less|never)\s+(?:too\s+|very\s+|so\s+)?{keyword}\b",
                text_lower,
            )
            if said and not negated:
                mood_profile = profile
                break

        # ── Requested cuisine, dish or food: the first one named and not negated ──
        # Cuisines come first, so "desi biryani" asks for desi food.
        requests = (
            "fast food",
            "middle eastern",
            "afghan",
            "chinese",
            "desi",
            "pakistani",
            "pizza",
            "burger",
            "biryani",
            "karahi",
            "shawarma",
            "sandwich",
            "dessert",
            "cake",
            "salad",
            "soup",
            "seafood",
            "chicken",
            "beef",
            "mutton",
            "fish",
            # Foods the sweep found the fallback dropped: a request for rice or noodles
            # matches dishes with them, and "traditional" food here means desi.
            "rice",
            "noodles",
            "pasta",
            "traditional",
        )
        preferred = next(
            (
                r
                for r in requests
                if re.search(rf"\b{r}\b", text_lower) and r.split()[-1] not in negated_words
            ),
            None,
        )
        if preferred in ("pakistani", "traditional"):
            preferred = "desi"

        return GroundedIntent(
            raw_input=raw_input,
            budget_max_pkr=budget,
            allergens_pruned=sorted(allergens_found),
            mood_vector=mood_profile,
            is_halal=is_halal,
            preferred_category=preferred,
            preferred_category_raw_phrase=preferred,
        )
