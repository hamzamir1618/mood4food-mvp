from tier_1.intent_extractor_interface import get_extractor


def test_budget_under():
    extractor = get_extractor()
    res = extractor.extract("I want something under 800 and spicy")
    assert res.budget_max_pkr == 800


def test_budget_rupees():
    extractor = get_extractor()
    res = extractor.extract("Find me 1500 rupees dinner")
    assert res.budget_max_pkr == 1500


def test_budget_rs():
    extractor = get_extractor()
    res = extractor.extract("Can I get pizza for Rs. 1000")
    assert res.budget_max_pkr == 1000


def test_budget_around():
    extractor = get_extractor()
    res = extractor.extract("around 500 with no meat")
    assert res.budget_max_pkr == 500


def test_budget_none():
    extractor = get_extractor()
    res = extractor.extract("I just want a nice hearty meal")
    assert res.budget_max_pkr is None


def test_allergen_single():
    extractor = get_extractor()
    res = extractor.extract("I want pizza with no dairy")
    assert "dairy" in res.allergens_pruned
    assert "meat" not in res.allergens_pruned


def test_allergen_multiple():
    extractor = get_extractor()
    res = extractor.extract("no dairy or peanuts please")
    assert "dairy" in res.allergens_pruned
    assert "nuts" in res.allergens_pruned


def test_allergen_multiple_comma():
    extractor = get_extractor()
    res = extractor.extract("without meat, eggs, and gluten")
    assert set(res.allergens_pruned) == {"meat", "egg", "gluten"}


def test_allergen_false_positive():
    extractor = get_extractor()
    res = extractor.extract("I love dairy and cheese but no meat")
    assert "dairy" not in res.allergens_pruned
    assert "meat" in res.allergens_pruned


def test_allergen_none():
    extractor = get_extractor()
    res = extractor.extract("I am very hungry")
    assert len(res.allergens_pruned) == 0


def test_allergen_free_suffix():
    extractor = get_extractor()
    res = extractor.extract("gluten free pizza")
    assert "gluten" in res.allergens_pruned
