"""
Tier 1 — Persona Manager
Defines user taste personas that override default agent weights and provide
multi-dimensional taste profile vectors for the consensus debate.
"""

import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ── Persona Definitions ─────────────────────────────────────────────────────
# Each persona defines:
#   - display_name: Human-readable label
#   - description: Short tagline for the UI
#   - icon: Emoji for the UI
#   - weights: Override for {w_health, w_budget, w_taste} (must sum to 1.0)
#   - taste_preference: 6D vector {sweet, salty, sour, bitter, umami, spice}
#     representing the persona's ideal taste profile for cosine similarity

PERSONAS = {
    "balanced": {
        "display_name": "The Balanced Eater",
        "description": "Equal priority across health, budget, and taste",
        "icon": "⚖️",
        "weights": {"w_health": 0.34, "w_budget": 0.33, "w_taste": 0.33},
        "taste_preference": {
            "sweet": 0.4,
            "salty": 0.5,
            "sour": 0.3,
            "bitter": 0.2,
            "umami": 0.6,
            "spice": 0.4,
        },
    },
    "gym_bro": {
        "display_name": "The Gym Bro",
        "description": "Protein-obsessed, health-first",
        "icon": "💪",
        "weights": {"w_health": 0.65, "w_budget": 0.15, "w_taste": 0.20},
        "taste_preference": {
            "sweet": 0.2,
            "salty": 0.6,
            "sour": 0.2,
            "bitter": 0.1,
            "umami": 0.9,
            "spice": 0.5,
        },
    },
    "comfort_seeker": {
        "display_name": "The Comfort Seeker",
        "description": "Rich, warm, soul-satisfying meals",
        "icon": "🛋️",
        "weights": {"w_health": 0.15, "w_budget": 0.25, "w_taste": 0.60},
        "taste_preference": {
            "sweet": 0.5,
            "salty": 0.7,
            "sour": 0.2,
            "bitter": 0.1,
            "umami": 0.8,
            "spice": 0.3,
        },
    },
    "adventurous_foodie": {
        "display_name": "The Adventurous Foodie",
        "description": "Bold flavours, spicy adventures",
        "icon": "🌶️",
        "weights": {"w_health": 0.20, "w_budget": 0.20, "w_taste": 0.60},
        "taste_preference": {
            "sweet": 0.3,
            "salty": 0.5,
            "sour": 0.6,
            "bitter": 0.4,
            "umami": 0.7,
            "spice": 0.95,
        },
    },
    "frugal_student": {
        "display_name": "The Frugal Student",
        "description": "Maximum food, minimum spend",
        "icon": "🎓",
        "weights": {"w_health": 0.15, "w_budget": 0.65, "w_taste": 0.20},
        "taste_preference": {
            "sweet": 0.4,
            "salty": 0.5,
            "sour": 0.3,
            "bitter": 0.2,
            "umami": 0.5,
            "spice": 0.4,
        },
    },
    "health_nut": {
        "display_name": "The Health Nut",
        "description": "Clean eating, light and fresh",
        "icon": "🥗",
        "weights": {"w_health": 0.60, "w_budget": 0.15, "w_taste": 0.25},
        "taste_preference": {
            "sweet": 0.3,
            "salty": 0.3,
            "sour": 0.5,
            "bitter": 0.3,
            "umami": 0.4,
            "spice": 0.2,
        },
    },
    "sweet_tooth": {
        "display_name": "The Sweet Tooth",
        "description": "Desserts and treats first",
        "icon": "🍰",
        "weights": {"w_health": 0.10, "w_budget": 0.30, "w_taste": 0.60},
        "taste_preference": {
            "sweet": 0.95,
            "salty": 0.2,
            "sour": 0.3,
            "bitter": 0.1,
            "umami": 0.2,
            "spice": 0.1,
        },
    },
}

DEFAULT_PERSONA = "balanced"


def get_persona(persona_key: str) -> dict:
    """Returns a persona dict by key. Falls back to 'balanced' if not found."""
    persona = PERSONAS.get(persona_key, PERSONAS[DEFAULT_PERSONA])
    log.info("persona loaded: %s (%s)", persona["display_name"], persona_key)
    return persona


def get_all_personas() -> dict:
    """Returns the full persona registry for the frontend to render."""
    return PERSONAS


def get_persona_weights(persona_key: str) -> dict:
    """Returns just the weight overrides for a persona."""
    return get_persona(persona_key)["weights"]


def get_persona_taste(persona_key: str) -> dict:
    """Returns the 6D taste preference vector for a persona."""
    return get_persona(persona_key)["taste_preference"]


import math  # noqa: E402


def validate_persona_weights():
    """Validates that all defined persona weights sum to 1.0."""
    for key, data in PERSONAS.items():
        weights = data["weights"]
        total = sum(weights.values())
        if not math.isclose(total, 1.0, rel_tol=1e-5):
            raise ValueError(f"Persona '{key}' weights must sum to 1.0, but got {total}")


validate_persona_weights()
