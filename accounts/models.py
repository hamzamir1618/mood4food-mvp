"""
Contracts for accounts and profiles (Phase 2).

A profile has three parts, each stored as its own node in Neo4j:
  DietaryProfile  hard constraints (allergies, diet, halal). Added to every query and
                  never weakened by learning.
  GoalProfile     fitness goal and usual spend, for Phase 3 scoring.
  TasteModel      a six-dimension taste vector with a confidence per dimension, seeded
                  from a persona and updated by the Phase 4 learning loop.
"""

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from pipeline.ingredients import ALLERGEN_TAGS
from tier_1.persona_manager import DEFAULT_PERSONA, PERSONAS

TASTE_DIMS = ("sweet", "salty", "sour", "bitter", "umami", "spice")
WEIGHT_KEYS = ("w_health", "w_budget", "w_taste")
MIN_PASSWORD_LENGTH = 10
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

Diet = Literal["none", "vegetarian", "vegan"]
Goal = Literal["balanced", "muscle_gain", "weight_loss", "light"]
EventKind = Literal["query", "rejected", "approved", "refined"]


def _known_persona(value: str) -> str:
    if value not in PERSONAS:
        raise ValueError(f"unknown persona; choose from {sorted(PERSONAS)}")
    return value


def _unit_interval(values: dict[str, float]) -> None:
    if any(not 0.0 <= float(x) <= 1.0 for x in values.values()):
        raise ValueError("every value must be between 0 and 1")


# ── Sign-in ──────────────────────────────────────────────────────────────────
class Credentials(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("not a valid email address")
        return v


class Registration(Credentials):
    password: str = Field(min_length=MIN_PASSWORD_LENGTH, max_length=256)
    display_name: str = Field(default="", max_length=60)
    persona: str = DEFAULT_PERSONA

    @field_validator("persona")
    @classmethod
    def known_persona(cls, v: str) -> str:
        return _known_persona(v)


class PasswordConfirmation(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class UserPublic(BaseModel):
    user_id: str
    email: str
    display_name: str = ""
    created_at: str = ""


# ── Profile ──────────────────────────────────────────────────────────────────
class DietaryProfile(BaseModel):
    allergies: list[str] = Field(default_factory=list)
    diet: Diet = "none"
    halal_only: bool = False

    @field_validator("allergies")
    @classmethod
    def known_allergens(cls, v: list[str]) -> list[str]:
        cleaned = sorted({a.strip().lower() for a in v if a.strip()})
        unknown = [a for a in cleaned if a not in ALLERGEN_TAGS]
        if unknown:
            raise ValueError(f"unknown allergens {unknown}; choose from {list(ALLERGEN_TAGS)}")
        return cleaned


class GoalProfile(BaseModel):
    goal: Goal = "balanced"
    typical_spend_pkr: Optional[float] = Field(default=None, gt=0, le=100_000)


class TasteModel(BaseModel):
    """
    The learned preference model (Phase 4 updates it; docs/LEARNING.md).

    vector         the user's taste, 0-1 per dimension
    confidence     0-1 per dimension: 0 means only the persona prior speaks for it; it
                   rises with approvals, and is 1 where the user set a value by hand
    importance     how much each dimension matters to this user (average 1)
    agent_weights  learned weights for health, budget and taste; None means the persona's
    updates        approvals learned from
    """

    vector: dict[str, float]
    confidence: dict[str, float]
    importance: dict[str, float] = Field(default_factory=lambda: {d: 1.0 for d in TASTE_DIMS})
    agent_weights: Optional[dict[str, float]] = None
    updates: int = 0
    persona_prior: str = DEFAULT_PERSONA

    @field_validator("importance")
    @classmethod
    def importance_per_dimension(cls, v: dict[str, float]) -> dict[str, float]:
        if set(v) != set(TASTE_DIMS) or any(float(x) <= 0 for x in v.values()):
            raise ValueError(f"needs a positive value for each of {list(TASTE_DIMS)}")
        return {d: float(v[d]) for d in TASTE_DIMS}

    @field_validator("agent_weights")
    @classmethod
    def three_weights(cls, v: Optional[dict[str, float]]) -> Optional[dict[str, float]]:
        if v is None:
            return None
        if set(v) != set(WEIGHT_KEYS) or any(x < 0 for x in v.values()) or not sum(v.values()):
            raise ValueError(f"needs non-negative {list(WEIGHT_KEYS)}, not all zero")
        total = sum(v.values())
        return {k: v[k] / total for k in WEIGHT_KEYS}

    @field_validator("vector", "confidence")
    @classmethod
    def six_dimensions(cls, v: dict[str, float]) -> dict[str, float]:
        if set(v) != set(TASTE_DIMS):
            raise ValueError(f"needs exactly these dimensions: {list(TASTE_DIMS)}")
        _unit_interval(v)
        return {d: float(v[d]) for d in TASTE_DIMS}

    @classmethod
    def from_persona(cls, persona: str) -> "TasteModel":
        persona = persona if persona in PERSONAS else DEFAULT_PERSONA
        prior = PERSONAS[persona]["taste_preference"]
        return cls(
            vector={d: prior[d] for d in TASTE_DIMS},
            confidence={d: 0.0 for d in TASTE_DIMS},
            persona_prior=persona,
        )

    def as_list(self) -> list[float]:
        return [self.vector[d] for d in TASTE_DIMS]

    def has_evidence(self) -> bool:
        """True once anything beyond the persona prior speaks for this taste."""
        return any(c > 0 for c in self.confidence.values())


class TasteEdit(BaseModel):
    """Dimensions the user sets by hand, e.g. {"spice": 0.9}. The rest keep their value."""

    values: dict[str, float]

    @field_validator("values")
    @classmethod
    def known_dimensions(cls, v: dict[str, float]) -> dict[str, float]:
        if not v or set(v) - set(TASTE_DIMS):
            raise ValueError(f"set one or more of: {list(TASTE_DIMS)}")
        _unit_interval(v)
        return v


class WeightsEdit(BaseModel):
    """How much health, budget and taste count, set by hand. Scaled to sum to 1."""

    w_health: float = Field(ge=0, le=1)
    w_budget: float = Field(ge=0, le=1)
    w_taste: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def not_all_zero(self) -> "WeightsEdit":
        if not (self.w_health + self.w_budget + self.w_taste):
            raise ValueError("at least one weight must be above zero")
        return self

    def as_weights(self) -> dict[str, float]:
        return {k: getattr(self, k) for k in WEIGHT_KEYS}


class TasteReset(BaseModel):
    persona: Optional[str] = None  # None keeps the current persona prior

    @field_validator("persona")
    @classmethod
    def known_persona(cls, v: Optional[str]) -> Optional[str]:
        return None if v is None else _known_persona(v)


class Profile(BaseModel):
    user: UserPublic
    dietary: DietaryProfile
    goals: GoalProfile
    taste: TasteModel


# ── Events ───────────────────────────────────────────────────────────────────
class Event(BaseModel):
    """
    One thing a user did: asked for a recommendation ("query"), passed over the dish
    they were shown ("rejected"), or approved one ("approved"). An approval's detail holds
    what learning needs: the dish's taste and how far it can be trusted, and its
    utilities next to the top pick's.
    """

    event_id: str
    kind: EventKind
    at: str
    session_id: str = ""
    query: str = ""
    dish_uid: Optional[str] = None
    dish_name: str = ""
    shown: list[str] = Field(default_factory=list)
    constraints: dict = Field(default_factory=dict)
    detail: dict = Field(default_factory=dict)
