from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TasteProfile(BaseModel):
    sweet: float = 0.0
    salty: float = 0.0
    sour: float = 0.0
    bitter: float = 0.0
    umami: float = 0.0
    spice: float = 0.0


class GroundedIntent(BaseModel):
    raw_input: str = ""
    budget_max_pkr: Optional[float] = None
    allergens_pruned: List[str] = Field(default_factory=list)
    mood_vector: TasteProfile = Field(default_factory=TasteProfile)
    craving: str = ""


class Candidate(BaseModel):
    dish_id: str = ""
    name: str = ""
    price_pkr: float = 0.0
    category: str = ""
    taste_profile: TasteProfile = Field(default_factory=TasteProfile)
    image_url: str = ""
    human_tags: List[str] = Field(default_factory=list)
    u_health: float = 0.0
    u_budget: float = 0.0
    u_taste: float = 0.0
    u_total: float = 0.0
    macros: Dict[str, Any] = Field(default_factory=dict)
    allergens: List[str] = Field(default_factory=list)


class CandidateEvaluation(BaseModel):
    source_intent: GroundedIntent = Field(default_factory=GroundedIntent)
    safe_candidates: List[Candidate] = Field(default_factory=list)
    soft_constraints: Dict[str, Any] = Field(default_factory=dict)
    relaxations: List[Dict[str, Any]] = Field(default_factory=list)
    message: str = ""


class SourceContext(BaseModel):
    budget_max_pkr: Optional[float] = None
    allergens_pruned: List[str] = Field(default_factory=list)
    mood_vector_seed: str = ""


class Persona(BaseModel):
    display_name: str = ""
    icon: str = ""
    description: str = ""


class DecisionBlueprint(BaseModel):
    active_persona: str = ""
    top_candidates: List[Candidate] = Field(default_factory=list)
    source_context: SourceContext = Field(default_factory=SourceContext)
    personas_available: Dict[str, Persona] = Field(default_factory=dict)
    relaxation_notice: Optional[str] = None
