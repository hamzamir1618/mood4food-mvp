"""Where the Phase 1 data pipeline reads from and writes to."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ── Inputs ───────────────────────────────────────────────────────────────────
HANDOFF_CSV = ROOT / "handoff_output" / "mood4food_dishes.csv"

# The data-sourcing project sits next to this repo by default; override with
# MOOD4FOOD_SOURCING_DIR if it lives somewhere else.
SOURCING_DIR = Path(
    os.environ.get(
        "MOOD4FOOD_SOURCING_DIR",
        ROOT.parent / "Data-Scraper" / "mood4food-data-sourcing",
    )
)
MASTER_CSV = SOURCING_DIR / "data" / "master_menu.csv"
OCR_RESULTS = (
    SOURCING_DIR / "data" / "ocr_results.json",
    SOURCING_DIR / "partner_kit" / "data" / "ocr_results.json",
)
MENU_PHOTOS = SOURCING_DIR / "data" / "menu_photos"
INGREDIENT_NUTRITION = SOURCING_DIR / "ingredient_nutrition_reference.csv"
INGREDIENT_ALLERGENS = SOURCING_DIR / "ingredient_allergen_map.csv"

# Worksheets the project owner fills in
REVIEW_DIR = ROOT / "data_review"
PLATTER_REVIEW = REVIEW_DIR / "platter_combo_review.xlsx"
OCR_REVIEW = REVIEW_DIR / "ocr_damage_review.xlsx"
OCR_REVIEW_GLOB = "ocr_damage_review*.xlsx"  # the first OCR worksheet and every later batch

# ── Outputs (git-ignored) ────────────────────────────────────────────────────
DATA_DIR = ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
CATEGORY_CACHE = CACHE_DIR / "category_llm.json"
DATASET_CSV = DATA_DIR / "dishes_v2.csv"
BUILD_REPORT = DATA_DIR / "build_report.md"

# USDA FoodData Central SR Legacy CSV, downloaded into data/ (public domain, CC0):
# https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip
USDA_SR_DIR = (
    DATA_DIR / "reference" / "usda" / "sr_legacy" / "FoodData_Central_sr_legacy_food_csv_2018-04"
)
NUTRITION_REFERENCE = DATA_DIR / "reference" / "ingredient_nutrition.csv"
