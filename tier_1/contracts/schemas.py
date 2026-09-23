from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


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
    is_vegan: bool = False
    is_vegetarian: bool = False
    is_halal: bool = False
    preferred_category: Optional[str] = None
    preferred_category_raw_phrase: Optional[str] = None


class Candidate(BaseModel):
    dish_id: str = ""
    name: str = ""
    price_pkr: float = 0.0
    category: str = ""
    taste_profile: TasteProfile = Field(default_factory=TasteProfile)
    image_url: str = ""
    is_rep_image: bool = False
    human_tags: List[str] = Field(default_factory=list)
    # Provenance the decision core weighs (tier_2/scoring.py). Candidates pass through
    # the session store as this model, so a field missing here never reaches scoring.
    restaurant_name: Optional[str] = None
    restaurant_area: Optional[str] = None  # "F-7", "Blue Area"; None when not known
    location_precision: Optional[str] = None  # place, area (the sector's centre) or unknown
    restaurant_lat: Optional[float] = None
    restaurant_lng: Optional[float] = None
    distance_km: Optional[float] = None  # straight line from the user's location, if sent
    price_status: Optional[str] = None
    serves_min: Optional[int] = None
    serves_max: Optional[int] = None
    serves_source: Optional[str] = None
    nutrition_confidence: Optional[str] = None
    nutrition_flag: Optional[str] = None
    review_status: Optional[str] = None
    taste_source: Optional[str] = None
    # Utilities in [0, 1]; None where the term couldn't be assessed (tier_2/scoring.py)
    u_health: Optional[float] = None
    u_budget: Optional[float] = None
    u_taste: Optional[float] = None
    u_context: Optional[float] = None
    u_distance: Optional[float] = None  # None without a location or coordinates
    u_total: float = 0.0
    confidence: Dict[str, float] = Field(default_factory=dict)
    coverage: Optional[float] = None
    novelty: float = 1.0
    peers: int = 0  # users with a similar taste who approved this recently
    exploration: bool = False  # the shortlist's deliberate "something different"
    reasons: Dict[str, str] = Field(default_factory=dict)
    summary: str = ""  # the reasons in one short paragraph (tier_2/scoring.py summary)
    macros: Dict[str, Any] = Field(default_factory=dict)
    allergens: Optional[List[str]] = Field(default_factory=list)  # None: not known
    ingredients: List[str] = Field(default_factory=list)


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
    distance_km: Optional[float] = None


class Fulfillment(BaseModel):
    recipe: Recipe
    restaurants: List[Restaurant]


class DecisionBlueprint(BaseModel):
    winning_dish: Optional[Dict[str, Any]] = None
    utility_breakdown: Optional[Dict[str, Optional[float]]] = None
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
    candidate_count: int = 0
    fulfillment: Optional[Fulfillment] = None
    # How the Pick screen is composed for this user (ui/compose.py); None: the fixed layout
    layout: Optional[Dict[str, Any]] = None


class Dish(BaseModel):
    restaurant_name: str
    restaurant_address: str
    restaurant_lat: float
    restaurant_lng: float
    dish_name: str
    price_rs: float
    category: str
    protein_g: Optional[float] = None
    calories: Optional[float] = None
    allergens: List[str] = Field(default_factory=list)
    is_vegan: bool = False
    is_vegetarian: bool = False
    taste_sweet: Optional[float] = None
    taste_salty: Optional[float] = None
    taste_sour: Optional[float] = None
    taste_bitter: Optional[float] = None
    taste_umami: Optional[float] = None
    taste_spice: Optional[float] = None
    taste_source: Optional[str] = None
    source: str
    source_date: str
    verified: bool = True

    @field_validator("is_vegan", "is_vegetarian", mode="before")
    @classmethod
    def parse_bools(cls, v: Any):
        if isinstance(v, str):
            return v.lower() == "true"
        return bool(v)

    @field_validator(
        "protein_g",
        "calories",
        "taste_sweet",
        "taste_salty",
        "taste_sour",
        "taste_bitter",
        "taste_umami",
        "taste_spice",
        mode="before",
    )
    @classmethod
    def parse_empty_floats(cls, v: Any):
        if v == "" or v is None:
            return None
        return float(v)

    @field_validator("allergens", mode="before")
    @classmethod
    def parse_allergens(cls, v: Any):
        if isinstance(v, str):
            if v.strip() == "":
                return []
            try:
                import json

                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
            return [v]
        return v
