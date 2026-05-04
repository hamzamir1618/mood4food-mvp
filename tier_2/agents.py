"""
Tier 2 — Vector Retrieval Pipeline
Provides three deterministic utility calculators and a lightweight local
vector store stub (no C++ build dependency).
"""

import json
import math
import logging
from pathlib import Path

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


# ── Utility Calculators ─────────────────────────────────────────────────────
# Each returns a float in [0.0, 1.0].  No external models — pure math.

def calculate_taste_utility(dish_vector: list[float],
                            mood_vector: list[float]) -> float:
    """
    Cosine similarity between a dish embedding and a mood embedding.

    cos(A,B) = (A · B) / (||A|| * ||B||)

    Returns 0.0 when vectors are orthogonal/zero, 1.0 when identical.
    """
    if len(dish_vector) != len(mood_vector):
        log.warning("vector length mismatch: dish=%d mood=%d — returning 0.0",
                    len(dish_vector), len(mood_vector))
        return 0.0

    dot = sum(a * b for a, b in zip(dish_vector, mood_vector))
    mag_a = math.sqrt(sum(a * a for a in dish_vector))
    mag_b = math.sqrt(sum(b * b for b in mood_vector))

    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0

    cosine = dot / (mag_a * mag_b)
    # Clamp to [0, 1] — negative similarity treated as zero affinity
    return max(0.0, min(1.0, cosine))


def calculate_health_utility(dish_data: dict) -> float:
    """
    Simple protein-to-calorie ratio normalisation.

    Formula:  ratio = protein_g / calories
    Normalised against a reference ceiling of 0.05 (i.e. 50 g protein per
    1000 kcal is a perfect 1.0).

    Expects dish_data to contain 'protein_g' and 'calories' keys.
    """
    protein = dish_data.get("protein_g", 0.0)
    calories = dish_data.get("calories", 1.0)  # avoid div-by-zero

    if calories <= 0:
        return 0.0

    ratio = protein / calories
    reference_ceiling = 0.05  # 50g protein / 1000 kcal
    normalised = ratio / reference_ceiling

    return max(0.0, min(1.0, normalised))


def calculate_budget_utility(price: float, max_budget: float) -> float:
    """
    Exponential decay budget utility.

    U_b = exp(-0.01 * price)

    Dishes near 0 PKR → ~1.0, dishes at 800 PKR → ~0.00034.
    The max_budget parameter is accepted for interface consistency but the
    formula is price-only per spec.
    """
    if price < 0:
        return 1.0
    return math.exp(-0.01 * price)


# ── Vector Retrieval Helpers ────────────────────────────────────────────────

def retrieve_dish_vector(store: LocalVectorStore, dish_id: str) -> list[float]:
    """Retrieves the embedding for a dish_id from the local store."""
    return store.get_embedding(dish_id)


def retrieve_mood_vector(store: LocalVectorStore, mood_seed: str) -> list[float]:
    """Retrieves a mood vector by seed key (e.g. 'mood_spicy')."""
    return store.get_embedding(f"mood_{mood_seed}")


# ── Standalone smoke test ───────────────────────────────────────────────────
if __name__ == "__main__":
    print("-- Utility Calculator Smoke Test --")

    # Taste: identical vectors -> 1.0
    t = calculate_taste_utility([1, 0, 0], [1, 0, 0])
    print(f"taste (identical):   {t:.4f}")  # 1.0

    # Taste: orthogonal -> 0.0
    t2 = calculate_taste_utility([1, 0, 0], [0, 1, 0])
    print(f"taste (orthogonal):  {t2:.4f}")  # 0.0

    # Health: 25g protein, 500 cal -> ratio 0.05 -> 1.0
    h = calculate_health_utility({"protein_g": 25, "calories": 500})
    print(f"health (25g/500cal): {h:.4f}")  # 1.0

    # Health: 10g protein, 800 cal -> ratio 0.0125 -> 0.25
    h2 = calculate_health_utility({"protein_g": 10, "calories": 800})
    print(f"health (10g/800cal): {h2:.4f}")  # 0.25

    # Budget: price 100 -> exp(-1) ~ 0.3679
    b = calculate_budget_utility(100, 800)
    print(f"budget (100 PKR):    {b:.4f}")  # 0.3679

    # Budget: price 0 -> 1.0
    b2 = calculate_budget_utility(0, 800)
    print(f"budget (0 PKR):      {b2:.4f}")  # 1.0

    print("\n-- Local Vector Store Test --")
    store = get_vector_store()
    print(f"store count: {store.count()}")
