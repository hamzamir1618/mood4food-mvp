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
        exclusion_keywords = {
            "vegan": "vegan",
            "vegetarian": "vegetarian",
            "meat": "meat",
            "chicken": "meat",
            "beef": "meat",
            "mutton": "meat",
            "pork": "meat",
            "dairy": "dairy",
            "milk": "dairy",
            "cheese": "dairy",
            "gluten": "gluten",
            "wheat": "gluten",
            "bread": "gluten",
            "naan": "gluten",
            "roti": "gluten",
            "pasta": "gluten",
            "nuts": "nuts",
            "peanut": "nuts",
            "peanuts": "nuts",
            "shellfish": "shellfish",
            "shrimp": "shellfish",
            "prawns": "shellfish",
            "egg": "egg",
            "eggs": "egg",
            "fish": "fish",
            "seafood": "fish",
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
        mood_map = {
            "spicy": TasteProfile(spice=1.0),
            "sweet": TasteProfile(sweet=1.0),
            "comfort": TasteProfile(salty=0.5, umami=0.5),
            "light": TasteProfile(sour=0.5),
            "hearty": TasteProfile(umami=1.0),
            "fresh": TasteProfile(sour=0.5, sweet=0.2),
            "crispy": TasteProfile(salty=0.5),
            "rich": TasteProfile(umami=0.8, sweet=0.2),
            "creamy": TasteProfile(sweet=0.3, umami=0.3),
            "tangy": TasteProfile(sour=1.0),
            "hot": TasteProfile(spice=1.0),
            "mild": TasteProfile(),
        }

        mood_profile = TasteProfile()
        for keyword, profile in mood_map.items():
            if keyword in text_lower:
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
        )
        preferred = next(
            (
                r
                for r in requests
                if re.search(rf"\b{r}\b", text_lower) and r.split()[-1] not in negated_words
            ),
            None,
        )
        if preferred == "pakistani":
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
