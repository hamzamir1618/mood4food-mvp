"""A signed-in user's saved dietary constraints, applied to every query."""

from accounts.models import DietaryProfile


def apply_dietary_profile(intent: dict, dietary: DietaryProfile) -> dict:
    """
    Adds the profile's hard constraints to a parsed query. It only ever adds: nothing
    typed in a query can loosen a saved allergy, diet or halal requirement.
    """
    merged = dict(intent)
    asked = {str(a).strip().lower() for a in intent.get("allergens_pruned") or []}
    merged["allergens_pruned"] = sorted((asked - {""}) | set(dietary.allergies))
    merged["is_vegan"] = bool(intent.get("is_vegan")) or dietary.diet == "vegan"
    merged["is_vegetarian"] = bool(intent.get("is_vegetarian")) or dietary.diet in (
        "vegetarian",
        "vegan",
    )
    merged["is_halal"] = bool(intent.get("is_halal")) or dietary.halal_only
    return merged
