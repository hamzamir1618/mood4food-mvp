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


class GroceryItem(BaseModel):
    item: str
    qty: str
    est_cost: Any


class Recipe(BaseModel):
    prep_time: str
    cook_time: str
    servings: int
    difficulty: str
    steps: List[str]
    grocery_list: List[GroceryItem]
    source: Optional[str] = None
    total_cost: Optional[Any] = None


class Restaurant(BaseModel):
    name: str
    delivery_time: Optional[str] = None
    rating: Optional[float] = None
    delivery_fee: Optional[float] = None
    dish_available: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class Fulfillment(BaseModel):
    recipe: Recipe
    restaurants: List[Restaurant]


class DecisionBlueprint(BaseModel):
    winning_dish: Optional[Dict[str, Any]] = None
    utility_breakdown: Optional[Dict[str, float]] = None
    agent_weights: Optional[Dict[str, float]] = None
    persona: str = ""
    relaxation_rounds: int = 0
    xai_traces: List[str] = Field(default_factory=list)
    all_candidate_scores: List[Dict[str, Any]] = Field(default_factory=list)
    active_persona: str = ""
    top_candidates: List[Candidate] = Field(default_factory=list)
    source_context: SourceContext = Field(default_factory=SourceContext)
    personas_available: Dict[str, Persona] = Field(default_factory=dict)
    relaxation_notice: Optional[str] = None
    fulfillment: Optional[Fulfillment] = None
