"""
Composes the Pick screen for one user. Takes the recommendation and the user's signals
(ui/signals.py) and returns a layout: which blocks appear, in which column and order, how
each is drawn, which refinement leads, and why the page looks the way it does.

Every rule is deterministic and says why it fired. No model writes the interface: the same
recommendation and signals always give the same layout, so a layout can be tested and
explained. The frontend draws a layout it is sent, and draws today's fixed Pick screen when
there is none, so a missing layout costs the user nothing.

Two blocks are pinned and can never be removed: the allergen line, and the notice that the
search had to widen. A rule may move or emphasise them, never drop them.

The contract is in docs/SERVER_DRIVEN_UI.md.
"""

import logging

from dialogue.critiques import CRITIQUES

log = logging.getLogger(__name__)

VERSION = 1
SLOTS = ("top", "main", "side", "band")
PINNED = ("allergens", "notice")

# Today's Pick screen, block for block: what a layout with no adaptations looks like.
DEFAULT = (
    ("notice", "top"),
    ("match", "main"),
    ("name", "main"),
    ("place", "main"),
    ("price", "main"),
    ("summary", "main"),
    ("allergens", "main"),
    ("weights", "main"),
    ("photo", "side"),
    ("reasons", "side"),
    ("runners", "band"),
)
DEFAULT_REASONS = ("taste", "budget", "health", "distance")
WEIGHT_KEYS = {"taste": "w_t", "budget": "w_b", "health": "w_h"}

# A habit is a refinement asked for at least this often, and in at least this share of all.
HABIT_MIN = 3
HABIT_SHARE = 0.4
USUAL_MIN = 2  # approvals of one dish before it counts as a usual
BUDGET_MINDED = 0.45  # a budget weight this high, and the highest, reads as budget-minded
ALLERGEN_WORDS = {
    "nuts": "nuts",
    "gluten": "gluten",
    "dairy": "dairy",
    "egg": "egg",
    "fish": "fish",
    "shellfish": "shellfish",
    "soy": "soy",
    "meat": "meat",
    "honey": "honey",
}
PROTEIN_GOALS = ("muscle_gain",)
LIGHT_GOALS = ("weight_loss", "light")
PROTEIN_PERSONAS = ("gym_bro",)
LIGHT_PERSONAS = ("health_nut",)
BUDGET_PERSONAS = ("frugal_student",)
EXPLORING_PERSONAS = ("adventurous_foodie",)
GOAL_PHRASES = {
    "muscle_gain": "your goal is building muscle",
    "weight_loss": "your goal is losing weight",
    "light": "you prefer eating light",
}
PERSONA_PHRASES = {
    "gym_bro": "you chose the Gym Bro profile",
    "health_nut": "you chose the Health Nut profile",
    "frugal_student": "you chose the Frugal Student profile",
    "adventurous_foodie": "you chose the Adventurous Foodie profile",
}


class Layout:
    """A layout being composed: blocks by slot, the refinement that leads, and the reasons."""

    def __init__(self):
        self.blocks = [
            {"id": block, "type": block, "slot": slot, "variant": "default", "props": {}}
            for block, slot in DEFAULT
        ]
        self.lead: str | None = None
        self.why: list[dict] = []

    def get(self, block_id: str) -> dict | None:
        return next((b for b in self.blocks if b["id"] == block_id), None)

    def insert(self, block: dict, after: str | None = None, first_in: str | None = None) -> None:
        """Adds a block after another, or first in a slot."""
        block = {"variant": "default", "props": {}, **block}
        if after and (anchor := self.get(after)):
            self.blocks.insert(self.blocks.index(anchor) + 1, {**block, "slot": anchor["slot"]})
        elif first_in:
            at = next(
                (i for i, b in enumerate(self.blocks) if b["slot"] == first_in), len(self.blocks)
            )
            self.blocks.insert(at, {**block, "slot": first_in})
        else:
            self.blocks.append(block)

    def remove(self, block_id: str) -> None:
        if block_id in PINNED:
            return
        self.blocks = [b for b in self.blocks if b["id"] != block_id]

    def lead_with(self, critique: str, text: str, source: str) -> None:
        """The first rule to choose a lead wins; the rules run in order of precedence."""
        if self.lead is None and critique in CRITIQUES:
            self.lead = critique
            self.explain(text, source, "actions")

    def explain(self, text: str, source: str, block: str | None = None) -> None:
        self.why.append({"text": text, "source": source, "block": block})

    def as_dict(self) -> dict:
        order = list(CRITIQUES)
        if self.lead:
            order.remove(self.lead)
            order.insert(0, self.lead)
        return {
            "version": VERSION,
            "screen": "pick",
            "blocks": self.blocks,
            "actions": {"refinements": order, "lead": self.lead},
            "why": self.why,
        }


# ── Rules, in order of precedence ───────────────────────────────────────────────
def _notice(layout: Layout, blueprint: dict, signals: dict) -> None:
    """The notice only shows when the search widened, so it is removed when there's none."""
    notice = blueprint.get("relaxation_notice")
    if notice:
        layout.get("notice")["props"] = {"text": notice}
    else:
        layout.blocks = [b for b in layout.blocks if b["id"] != "notice"]


def _safety(layout: Layout, blueprint: dict, signals: dict) -> None:
    """Confirms the rules that removed dishes, at the top of the card. It states what the
    search did, never that a dish is safe: allergen data is estimated from ingredients."""
    saved = signals.get("dietary") or {}
    saved_allergies = set(saved.get("allergies") or [])
    lines, sources = [], set()

    allergens = sorted(set(signals.get("allergens") or []) | saved_allergies)
    for a in allergens:
        word = ALLERGEN_WORDS.get(a, a)
        from_profile = a in saved_allergies
        sources.add("profile" if from_profile else "query")
        lines.append(f"No dishes with {word}" + (" — from your profile" if from_profile else ""))
    if signals.get("vegan"):
        lines.append("Vegan only")
        sources.add("profile" if saved.get("diet") == "vegan" else "query")
    elif signals.get("vegetarian"):
        lines.append("Vegetarian only")
        sources.add("profile" if saved.get("diet") == "vegetarian" else "query")
    if signals.get("halal"):
        lines.append("Halal only")
        sources.add("profile" if saved.get("halal_only") else "query")
    if not lines:
        return

    layout.insert({"id": "safety", "type": "safety", "props": {"lines": lines}}, first_in="main")
    layout.get("allergens")["variant"] = "emphasised"
    where = "your profile" if sources == {"profile"} else "what you asked"
    layout.explain(
        f"Your food rules are confirmed at the top, because they come from {where}.",
        "profile" if "profile" in sources else "query",
        "safety",
    )


def _habit(layout: Layout, blueprint: dict, signals: dict) -> None:
    """A refinement the user keeps asking for is offered first."""
    counts = signals.get("refinements") or {}
    total = sum(counts.values())
    if not counts:
        return
    critique, n = max(counts.items(), key=lambda kv: (kv[1], kv[0]))
    if n >= HABIT_MIN and n / total >= HABIT_SHARE:
        layout.lead_with(
            critique,
            f"“{CRITIQUES[critique]}” comes first: you've asked for it {n} times "
            f"in your last {total} refinements.",
            "learned",
        )


def _goal(layout: Layout, blueprint: dict, signals: dict) -> None:
    """A protein or calorie goal puts that number on the card, beside the price."""
    goal, persona = signals.get("goal"), signals.get("persona")
    macros = (blueprint.get("winning_dish") or {}).get("macros") or {}
    dish = blueprint.get("winning_dish") or {}
    wants_protein = goal in PROTEIN_GOALS or (
        goal in (None, "balanced") and persona in PROTEIN_PERSONAS
    )
    wants_light = goal in LIGHT_GOALS or (goal in (None, "balanced") and persona in LIGHT_PERSONAS)
    if not (wants_protein or wants_light):
        return
    reason = GOAL_PHRASES.get(goal) or PERSONA_PHRASES.get(persona, "")
    source = "profile" if goal in GOAL_PHRASES else "persona"
    key, variant, critique = (
        ("protein_g", "protein", "more_filling")
        if wants_protein
        else ("calories", "calories", "lighter")
    )
    if macros.get(key) is not None:
        layout.insert(
            {
                "id": "nutrition",
                "type": "nutrition",
                "variant": variant,
                "props": {
                    "protein_g": macros.get("protein_g"),
                    "calories": macros.get("calories"),
                    "confidence": dish.get("nutrition_confidence"),
                },
            },
            after="price",
        )
        label = "Protein" if wants_protein else "Calories"
        layout.explain(f"{label} is shown beside the price: {reason}.", source, "nutrition")
    layout.lead_with(critique, f"“{CRITIQUES[critique]}” comes first: {reason}.", source)


def _budget(layout: Layout, blueprint: dict, signals: dict) -> None:
    """A budget-minded user sees the price as the headline, per person where it serves more."""
    weights = blueprint.get("agent_weights") or {}
    w_b = weights.get("w_b") or 0.0
    heaviest = w_b >= max(weights.get("w_t") or 0.0, weights.get("w_h") or 0.0)
    persona = signals.get("persona")
    if persona in BUDGET_PERSONAS:
        reason, source = PERSONA_PHRASES[persona], "persona"
    elif signals.get("cheap_query"):
        reason, source = "you asked for something cheap", "query"
    elif w_b >= BUDGET_MINDED and heaviest:
        reason, source = "budget counts most for you right now", "weights"
    else:
        return
    dish = blueprint.get("winning_dish") or {}
    price, serves = dish.get("price_pkr"), dish.get("serves_max") or 1
    props = {"per_person": round(price / serves) if price and serves > 1 else None}
    price_block = layout.get("price")
    price_block.update(variant="headline", props=props)
    layout.explain(f"The price is the headline: {reason}.", source, "price")
    layout.lead_with("cheaper", f"“{CRITIQUES['cheaper']}” comes first: {reason}.", source)


def _explore(layout: Layout, blueprint: dict, signals: dict) -> None:
    persona = signals.get("persona")
    if persona in EXPLORING_PERSONAS:
        layout.lead_with(
            "different",
            f"“{CRITIQUES['different']}” comes first: {PERSONA_PHRASES[persona]}.",
            "persona",
        )


def _reasons(layout: Layout, blueprint: dict, signals: dict) -> None:
    """The reasons are listed in the order the user weighs them; distance stays last."""
    weights = blueprint.get("agent_weights") or {}
    if not weights:
        return
    # Rounded, so near-even weights (0.34 / 0.33 / 0.33) keep the usual order.
    ranked = sorted(
        WEIGHT_KEYS,
        key=lambda term: (
            -round(weights.get(WEIGHT_KEYS[term]) or 0.0, 1),
            DEFAULT_REASONS.index(term),
        ),
    )
    order = [*ranked, "distance"]
    layout.get("reasons")["props"] = {"order": order}
    if tuple(order) != DEFAULT_REASONS:
        layout.explain(
            f"The reasons start with {order[0]}: it counts most in how this pick was made.",
            "weights",
            "reasons",
        )


def _history(layout: Layout, blueprint: dict, signals: dict) -> None:
    """What the user and people like them chose before: on the winner, and as runner badges."""
    winner = (blueprint.get("winning_dish") or {}).get("dish_id")
    approvals = signals.get("approvals") or {}
    peers = signals.get("peers") or {}

    lines = []
    mine = (approvals.get(winner) or {}).get("count", 0) if winner else 0
    if mine:
        lines.append(f"You've chosen this {mine} time{'s' if mine != 1 else ''} before.")
    theirs = peers.get(winner, 0) if winner else 0
    if theirs:
        who = "person" if theirs == 1 else "people"
        lines.append(f"{theirs} {who} with a taste like yours chose this recently.")
    if lines:
        layout.insert(
            {"id": "history", "type": "history", "props": {"lines": lines}}, after="reasons"
        )
        layout.explain(
            "What you and people like you chose before is shown with the reasons.",
            "learned",
            "history",
        )

    badges = {}
    for c in blueprint.get("top_candidates") or []:
        uid = c.get("dish_id")
        if not uid or uid == winner:
            continue
        if (approvals.get(uid) or {}).get("count", 0) >= USUAL_MIN:
            badges[uid] = "Your usual"
        elif peers.get(uid):
            badges[uid] = "Liked by similar tastes"
    if badges:
        layout.get("runners")["props"] = {"badges": badges}
        layout.explain(
            "Runners you've chosen before, or people like you chose, are marked.",
            "learned",
            "runners",
        )


def _learning(layout: Layout, blueprint: dict, signals: dict) -> None:
    """Says how much the app knows about the user yet, so a generic pick isn't taken as
    a claim to know them."""
    n = signals.get("learned_from") or 0
    if signals.get("signed_in"):
        if n:
            text = f"Tuned by {n} of your choices."
            variant = "tuned"
        else:
            text = "Still learning you. Each “I'll have this” teaches it your taste."
            variant = "new"
    elif signals.get("queries"):
        text = "Sign in and I'll remember what you choose."
        variant = "guest"
    else:
        return
    layout.insert(
        {"id": "learning", "type": "learning", "variant": variant, "props": {"text": text}},
        after="reasons",
    )


RULES = (_notice, _safety, _habit, _goal, _budget, _explore, _reasons, _history, _learning)


def pick(blueprint: dict, signals: dict | None) -> dict:
    """The Pick screen's layout for this recommendation and user."""
    layout = Layout()
    for rule in RULES:
        rule(layout, blueprint or {}, signals or {})
    return layout.as_dict()


def pick_for_session(session_id: str, blueprint: dict) -> dict | None:
    """The layout for a session's recommendation, or None, which the frontend draws as the
    fixed Pick screen. A layout is never worth failing a recommendation over."""
    from tier_1.contracts.session_store import load_contract

    try:
        return pick(blueprint, load_contract(session_id, "ui_signals") or {})
    except Exception as exc:
        log.warning("layout not composed, the fixed one is used: %s", exc)
        return None
