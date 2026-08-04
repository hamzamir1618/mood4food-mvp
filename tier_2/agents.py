"""
Tier 2 — Vector Retrieval Pipeline
Provides three deterministic utility calculators and a lightweight local
vector store stub (no C++ build dependency).
"""

import json
import logging
import math
from abc import ABC, abstractmethod
from pathlib import Path

from tier_1.contracts.schemas import Candidate, TasteProfile

# ── Config ──────────────────────────────────────────────────────────────────
VECTOR_STORE_PATH = Path(__file__).resolve().parent / "vector_store.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger(__name__)


# ── Lightweight Local Vector Store ──────────────────────────────────────────
# Drop-in stub that mirrors the ChromaDB API surface we actually use.
# Stores vectors as a JSON file on disk.  Swap for real ChromaDB when MSVC
# Build Tools are available: pip install chromadb==0.5.15


class LocalVectorStore:
    """Minimal persistent vector store backed by a JSON file."""

    def __init__(self, path: Path = VECTOR_STORE_PATH):
        self._path = path
        self._data: dict[str, dict] = {}
        if path.exists():
            with open(path, "r", encoding="utf-8") as fh:
                self._data = json.load(fh)
        log.info("local vector store loaded — %d entries from %s", len(self._data), path)

    def _persist(self):
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2, ensure_ascii=False)

    def add(self, doc_id: str, embedding: list[float], metadata: dict | None = None):
        self._data[doc_id] = {"embedding": embedding, "metadata": metadata or {}}
        self._persist()

    def get_embedding(self, doc_id: str) -> list[float]:
        entry = self._data.get(doc_id)
        if entry:
            return entry["embedding"]
        log.warning("no embedding found for id=%s", doc_id)
        return []

    def count(self) -> int:
        return len(self._data)


def get_vector_store() -> LocalVectorStore:
    """Returns the local vector store instance."""
    return LocalVectorStore()


class BaseAgent(ABC):
    @abstractmethod
    def score(self, candidate: Candidate) -> float:
        pass


class HealthAgent(BaseAgent):
    def score(self, candidate: Candidate) -> float:
        """
        Simple protein-to-calorie ratio normalisation.

        Formula:  ratio = protein_g / calories
        Normalised against a reference ceiling of 0.05 (i.e. 50 g protein per
        1000 kcal is a perfect 1.0).
        """
        protein = (
            candidate.macros.get("protein_g", 0.0) if isinstance(candidate.macros, dict) else 0.0
        )
        calories = (
            candidate.macros.get("calories", 1.0) if isinstance(candidate.macros, dict) else 1.0
        )

        if calories <= 0:
            return 0.0

        ratio = protein / calories
        reference_ceiling = 0.05  # 50g protein / 1000 kcal
        normalised = ratio / reference_ceiling

        return max(0.0, min(1.0, normalised))


class BudgetAgent(BaseAgent):
    def __init__(self, max_budget: float):
        self.max_budget = max_budget if max_budget is not None and max_budget > 0 else 1000.0

    def score(self, candidate: Candidate) -> float:
        """
        Log-scaled budget utility that creates high sensitivity in the
        typical price range (100-500 PKR), ensuring small price differences
        produce meaningful utility differences.

        U_b = 1 - log(1 + price) / log(1 + max_budget)
        """
        price = candidate.price_pkr
        if price < 0:
            return 1.0
        return max(0.0, 1.0 - math.log(1 + price) / math.log(1 + self.max_budget))


class TasteAgent(BaseAgent):
    def __init__(self, persona_taste: TasteProfile):
        self.persona_taste = persona_taste

    def score(self, candidate: Candidate) -> float:
        """
        6-dimensional taste cosine similarity between a dish's taste profile
        and a persona's taste preference.
        """
        keys = ["sweet", "salty", "sour", "bitter", "umami", "spice"]
        dish_taste_profile = candidate.taste_profile

        # Helper to get value whether it's dict or pydantic model
        def get_val(obj, key):
            if isinstance(obj, dict):
                return obj.get(key, 0.0)
            return getattr(obj, key, 0.0)

        dish_vec = [get_val(dish_taste_profile, k) for k in keys]
        pref_vec = [get_val(self.persona_taste, k) for k in keys]

        dot = sum(a * b for a, b in zip(dish_vec, pref_vec))
        mag_a = math.sqrt(sum(a * a for a in dish_vec))
        mag_b = math.sqrt(sum(b * b for b in pref_vec))

        if mag_a == 0.0 or mag_b == 0.0:
            return 0.0

        cosine = dot / (mag_a * mag_b)
        return max(0.0, min(1.0, cosine))


# Legacy fallback vector utility (not used in 6D)
def calculate_taste_utility(dish_vector: list[float], mood_vector: list[float]) -> float:
    """
    Cosine similarity between a dish embedding and a mood embedding.
    """
    if len(dish_vector) != len(mood_vector):
        log.warning(
            "vector length mismatch: dish=%d mood=%d — returning 0.0",
            len(dish_vector),
            len(mood_vector),
        )
        return 0.0

    dot = sum(a * b for a, b in zip(dish_vector, mood_vector))
    mag_a = math.sqrt(sum(a * a for a in dish_vector))
    mag_b = math.sqrt(sum(b * b for b in mood_vector))

    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0

    cosine = dot / (mag_a * mag_b)
    # Clamp to [0, 1] — negative similarity treated as zero affinity
    return max(0.0, min(1.0, cosine))


# ── Vector Retrieval Helpers ────────────────────────────────────────────────


def retrieve_dish_vector(store: LocalVectorStore, dish_id: str) -> list[float]:
    """Retrieves the embedding for a dish_id from the local store."""
    return store.get_embedding(dish_id)


def retrieve_mood_vector(store: LocalVectorStore, mood_seed: str) -> list[float]:
    """Retrieves a mood vector by seed key (e.g. 'mood_spicy')."""
    return store.get_embedding(f"mood_{mood_seed}")
