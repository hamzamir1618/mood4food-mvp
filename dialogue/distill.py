"""
Distillation: what a signed-in user said in a conversation that belongs in their
long-term profile, offered as suggestions to save. Nothing is written silently:
allergies, diet and budget are the user's to set, so each suggestion carries the exact
profile update for the client to send if the user agrees.
"""

from pipeline.ingredients import ALLERGEN_TAGS


def suggestions(request, session_id: str, conversation) -> list[dict]:
    from accounts import store
    from accounts.deps import current_user_id
    from tier_1.contracts.session_store import load_contract

    try:
        user_id = current_user_id(request)
        profile = store.get_profile(user_id) if user_id else None
    except Exception:
        return []
    if profile is None:
        return []
    intent = load_contract(session_id, "grounded_intent")
    intent = intent.model_dump() if hasattr(intent, "model_dump") else (intent or {})

    out = []
    dietary = profile.dietary
    body, changes = dietary.model_dump(), []
    said = {a for a in intent.get("allergens_pruned") or [] if a in ALLERGEN_TAGS}
    new = sorted(said - set(dietary.allergies))
    if new:
        body["allergies"] = sorted({*dietary.allergies, *new})
        changes.append(f"always avoid {' and '.join(new)}")
    diet = (
        "vegan" if intent.get("is_vegan") else "vegetarian" if intent.get("is_vegetarian") else None
    )
    if diet and dietary.diet == "none":
        body["diet"] = diet
        changes.append(f"keep it {diet}")
    if changes:
        out.append(
            {
                "text": f"Save this to your profile: {'; '.join(changes)}?",
                "method": "PUT",
                "path": "/profile/dietary",
                "body": body,
            }
        )

    budget = ((conversation.stated.get("budget") or {}).get("adjust") or {}).get("ceiling")
    if budget and profile.goals.typical_spend_pkr is None:
        out.append(
            {
                "text": f"Is about Rs {budget:,.0f} what you usually spend? Save it as your "
                "budget.",
                "method": "PUT",
                "path": "/profile/goals",
                "body": {**profile.goals.model_dump(), "typical_spend_pkr": budget},
            }
        )
    return out
