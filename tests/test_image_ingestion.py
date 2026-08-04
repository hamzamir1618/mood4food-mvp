import os

from tier_1.image_ingestion import classify_dish
from tier_1.symbolic_anchoring import get_all_dish_names


def test_classify_dish_biryani():
    image_path = os.path.join(
        os.path.dirname(__file__), "..", "uploads", "spicy_chicken_biryani.jpg"
    )

    # Get labels from neo4j (or fallback if neo4j is down)
    candidate_labels = get_all_dish_names()

    # Ensure there's a robust list of labels for the test, particularly if Neo4j returned a fallback
    if "spicy chicken biryani" not in [lbl.lower() for lbl in candidate_labels]:
        candidate_labels.append("Spicy Chicken Biryani")

    result = classify_dish(image_path, candidate_labels)
    assert isinstance(result, str)
    assert "biryani" in result.lower(), f"Expected 'biryani' in result, got '{result}'"
