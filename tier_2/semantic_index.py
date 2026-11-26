"""
Hybrid semantic–symbolic context retrieval for Mood4Food.

Uses ONNXMiniLM_L6_V2 (384-dim dense sentence embeddings, ONNX Runtime, no PyTorch) to
embed each dish's full culinary context — name, cuisine, ingredients, flavour profile,
nutrition band, portion/sharing context, and weather/occasion suitability — and score
Tier 1's safe candidates by cosine similarity to the user's natural-language request.

Tier 1 (Neo4j symbolic anchoring) remains the sole hard safety filter: semantic search
never bypasses allergies, diet, halal, or budget ceilings.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)

DEFAULT_INDEX_PATH = Path("data/dish_embeddings.npz")
DEFAULT_CSV_PATH = Path("data/dishes_v2.csv")

# Calibrated cosine similarity band for MiniLM-L6-v2 on short food queries vs dish docs.
# Fixed bounds (rather than per-query min-max) prevent unrelated queries from inflating
# a poor match to 1.0.
SEMANTIC_FLOOR = 0.15
SEMANTIC_CEIL = 0.62

# Queries shorter than this or purely punctuation carry too little semantic signal.
MIN_QUERY_CHARS = 3

CATEGORY_CONTEXT = {
    "desi_traditional": "Pakistani desi traditional spicy karahi curry biryani barbecue local food",
    "afghan": "Afghan traditional charcoal grill pulao kebab hearty meat dish",
    "chinese_asian": "Chinese Thai Asian wok stir fry noodles rice dumplings oriental",
    "continental_upscale": "Continental European fine dining steak grill pasta western",
    "middle_eastern": "Middle Eastern Turkish Arabic shawarma grill pide hummus mezze",
    "fast_food": "Fast food burger fries crispy fried chicken casual comfort food",
    "pizza": "Italian pizza cheesy baked crust sharing comfort food",
    "cafe_bakery": "Cafe bakery breakfast dessert sweet coffee pastry light bite",
    "beverages": "Drink beverage refreshment cold hot",
    "side_addon": "Side dish accompaniment bread naan starter",
}

_WARM_COMFORT_RE = re.compile(
    r"\b(soup|yakhni|karahi|nihari|haleem|daal|dal|curry|stew|ramen|chai|khichdi|biryani|pulao)\b",
    re.I,
)
_BREAKFAST_RE = re.compile(
    r"\b(breakfast|nashta|halwa|puri|paratha|omelette|omellete|egg|"
    r"pancake|waffle|shakshuka|french toast|chai)\b",
    re.I,
)
_FRESH_COOL_RE = re.compile(
    r"\b(salad|raita|lassi|smoothie|ice cream|kulfi|cold|iced|lemonade|mint|mojito|fresh|tangy)\b",
    re.I,
)


def _as_float(val, default: float = 0.0) -> float:
    try:
        return float(val) if val not in (None, "") else default
    except (TypeError, ValueError):
        return default


def _as_bool(val) -> bool:
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in ("true", "1", "yes")


def dish_document(dish: dict) -> str:
    """
    Turns a dish record (either a dishes_v2.csv row or a Tier 1 candidate dict) into a
    rich contextual text document for dense semantic embedding.
    """
    name = (dish.get("dish_name") or dish.get("name") or "").strip()
    cat = (dish.get("category") or "").strip()
    cat_desc = CATEGORY_CONTEXT.get(cat, cat.replace("_", " "))

    # Ingredients (CSV has semicolon/comma string; candidate dict has list[str])
    raw_ing = dish.get("ingredients")
    if isinstance(raw_ing, list):
        ing_str = ", ".join(str(x) for x in raw_ing[:14])
    else:
        ing_str = str(raw_ing or "").replace(";", ", ")

    # Taste profile (CSV has taste_* columns; candidate dict has taste_profile dict)
    tp = dish.get("taste_profile") if isinstance(dish.get("taste_profile"), dict) else {}
    spice = _as_float(tp.get("spice", dish.get("taste_spice")))
    sweet = _as_float(tp.get("sweet", dish.get("taste_sweet")))
    sour = _as_float(tp.get("sour", dish.get("taste_sour")))
    umami = _as_float(tp.get("umami", dish.get("taste_umami")))
    salty = _as_float(tp.get("salty", dish.get("taste_salty")))

    flavours = []
    if spice >= 0.45:
        flavours.append("spicy hot fiery chatpata masala")
    elif spice <= 0.15 and sweet < 0.4:
        flavours.append("mild gentle not spicy")
    if sweet >= 0.45:
        flavours.append("sweet dessert treat sugary meetha")
    if sour >= 0.35:
        flavours.append("tangy sour zesty citrus khatta")
    if umami >= 0.45 or salty >= 0.45:
        flavours.append("savoury rich hearty umami")

    # Nutrition & meal-size context
    macros = dish.get("macros") if isinstance(dish.get("macros"), dict) else {}
    kcal = _as_float(macros.get("calories", dish.get("calories")))
    protein = _as_float(macros.get("protein_g", dish.get("protein_g")))
    carbs = _as_float(macros.get("carbs_g", dish.get("carbs_g")))
    serves_max = _as_float(dish.get("serves_max"), 1.0)

    context_tags = []
    if protein >= 30:
        context_tags.append("high protein gym post-workout muscle building")
    if 0 < kcal <= 450:
        context_tags.append("light low calorie healthy diet office lunch")
    elif kcal >= 650:
        context_tags.append("filling hearty heavy meal comfort food dinner")
    if 0 < carbs <= 20 and protein >= 15:
        context_tags.append("low carb keto friendly")
    if serves_max >= 2:
        context_tags.append("sharing group family platter for two or more")
    if _as_bool(dish.get("is_vegan")):
        context_tags.append("vegan plant-based")
    elif _as_bool(dish.get("is_vegetarian")):
        context_tags.append("vegetarian meatless")

    if _WARM_COMFORT_RE.search(name):
        context_tags.append("warm comforting rainy cold weather winter")
    if _BREAKFAST_RE.search(name):
        context_tags.append("breakfast morning nashta brunch")
    if _FRESH_COOL_RE.search(name):
        context_tags.append("cool refreshing summer hot weather")

    parts = [name]
    if cat_desc:
        parts.append(f"Cuisine: {cat_desc}")
    if ing_str:
        parts.append(f"Ingredients: {ing_str}")
    if flavours:
        parts.append(f"Flavour: {', '.join(flavours)}")
    if context_tags:
        parts.append(f"Context: {', '.join(context_tags)}")
    return ". ".join(p for p in parts if p)


def _l2_normalize(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return mat / norms


class SemanticIndex:
    """Lazy-loaded ONNX MiniLM-L6-v2 semantic index over Mood4Food dishes."""

    def __init__(self, index_path: Path = DEFAULT_INDEX_PATH):
        self.index_path = Path(index_path)
        self._ef = None
        self._ids: list[str] = []
        self._id_to_row: dict[str, int] = {}
        self._vectors: np.ndarray | None = None  # float32 unit vectors, shape (N, 384)
        self._loaded = False
        self._query_cache: dict[str, np.ndarray] = {}

    def _get_ef(self):
        if self._ef is None:
            from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

            self._ef = ONNXMiniLM_L6_V2()
        return self._ef

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 384), dtype=np.float32)
        ef = self._get_ef()
        vecs = np.asarray(ef(texts), dtype=np.float32)
        if vecs.ndim == 1:
            vecs = vecs.reshape(1, -1)
        return _l2_normalize(vecs)

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self.index_path.exists():
            log.info(
                "semantic index %s not found; will embed candidates on demand", self.index_path
            )
            return
        try:
            data = np.load(self.index_path, allow_pickle=False)
            ids = [str(x) for x in data["dish_ids"].tolist()]
            vecs = np.asarray(data["vectors"], dtype=np.float32)
            self._ids = ids
            self._id_to_row = {uid: i for i, uid in enumerate(ids)}
            self._vectors = _l2_normalize(vecs)
            log.info("loaded %d dish embeddings from %s", len(ids), self.index_path)
        except Exception as exc:
            log.warning("could not load semantic index %s: %s", self.index_path, exc)

    def _add_runtime_candidates(self, missing: list[dict]) -> None:
        """Embeds any candidates absent from the prebuilt file and caches them in memory."""
        if not missing:
            return
        docs = [dish_document(c) for c in missing]
        new_ids = [str(c.get("dish_id") or c.get("dish_uid") or "") for c in missing]
        new_vecs = self.embed_texts(docs)
        start = len(self._ids)
        self._ids.extend(new_ids)
        for offset, uid in enumerate(new_ids):
            self._id_to_row[uid] = start + offset
        if self._vectors is None or len(self._vectors) == 0:
            self._vectors = new_vecs
        else:
            self._vectors = np.vstack([self._vectors, new_vecs])

    def score_candidates(self, query: str, candidates: list[dict]) -> dict[str, float]:
        """
        Returns {dish_id: raw_cosine_similarity} for each candidate against `query`.
        Returns {} if semantic search is disabled or query has too little text.
        """
        if not is_enabled():
            return {}
        q = (query or "").strip()
        if len(q) < MIN_QUERY_CHARS or not candidates:
            return {}

        self._ensure_loaded()

        missing = [
            c
            for c in candidates
            if str(c.get("dish_id") or c.get("dish_uid") or "") not in self._id_to_row
        ]
        if missing:
            self._add_runtime_candidates(missing)

        if self._vectors is None or not self._id_to_row:
            return {}

        q_key = q.lower()
        q_vec = self._query_cache.get(q_key)
        if q_vec is None:
            q_vec = self.embed_texts([q])[0]  # shape (384,)
            if len(self._query_cache) >= 128:
                self._query_cache.clear()
            self._query_cache[q_key] = q_vec
        rows = []
        valid_ids = []
        for c in candidates:
            uid = str(c.get("dish_id") or c.get("dish_uid") or "")
            idx = self._id_to_row.get(uid)
            if idx is not None:
                rows.append(idx)
                valid_ids.append(uid)

        if not rows:
            return {}

        sub = self._vectors[rows]  # shape (M, 384)
        sims = sub @ q_vec  # cosine similarity (unit vectors)
        return {uid: float(sim) for uid, sim in zip(valid_ids, sims)}


def calibrate_similarity(raw_cosine: float) -> float:
    """Maps raw MiniLM cosine similarity from [SEMANTIC_FLOOR, SEMANTIC_CEIL] to [0, 1]."""
    if raw_cosine <= SEMANTIC_FLOOR:
        return 0.0
    if raw_cosine >= SEMANTIC_CEIL:
        return 1.0
    return (raw_cosine - SEMANTIC_FLOOR) / (SEMANTIC_CEIL - SEMANTIC_FLOOR)


def is_enabled() -> bool:
    """Enabled by default; set SEMANTIC_SEARCH=0 for keyword-only ablation runs."""
    return os.getenv("SEMANTIC_SEARCH", "1").strip().lower() not in ("0", "false", "no", "off")


_SINGLETON: SemanticIndex | None = None


def get_semantic_index() -> SemanticIndex:
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = SemanticIndex()
    return _SINGLETON


def score_query_candidates(query: str, candidates: list[dict]) -> dict[str, float]:
    """Convenience entry point used by the pipeline. Never raises — degrades to {}."""
    if not is_enabled():
        return {}
    try:
        return get_semantic_index().score_candidates(query, candidates)
    except Exception as exc:
        log.warning("semantic scoring unavailable, continuing without it: %s", exc)
        return {}
