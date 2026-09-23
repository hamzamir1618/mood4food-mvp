"""
Controlled ingredient vocabulary for the Phase 1 pipeline.

Every ingredient the pipeline can attach to a dish appears here exactly once.
Nutrition values are deliberately not stored here: they come from USDA
FoodData Central via pipeline.usda_reference, which records the FDC entry
behind every number.

Fields
  role       bulk | fat | veg | trace — how the nutrition estimate apportions a serving
             (bulk 71%, fat 7%, veg 15%, the rest water and trace; calibrated against
             USDA-measured restaurant dishes, see pipeline/nutrition.py)
  allergens  allergen tags it carries: dairy, egg, fish, shellfish, gluten, nuts, soy, sesame
  animal     meat | fish | shellfish | egg | dairy | honey | "" — drives is_vegan / is_vegetarian
  haram      True for pork and alcohol — drives is_halal
  aliases    other spellings and Urdu transliterations matched in dish names. An alias may
             appear under more than one ingredient ("hummus" is chickpeas and tahini).

Restaurants in Islamabad are halal by default, so pork and alcohol are only ever
attached when a dish name or description says so explicitly.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Ingredient:
    role: str
    allergens: tuple = ()
    animal: str = ""
    haram: bool = False
    aliases: tuple = ()


I = Ingredient  # noqa: E741 — keeps the table below readable

VOCABULARY: dict[str, Ingredient] = {
    # ── Meat, fish, eggs and plant proteins ──────────────────────────────────
    "chicken": I(
        "bulk",
        animal="meat",
        aliases=(
            "murgh",
            "murg",
            "wings",
            "winglets",
            "nuggets",
            "broast",
            "zinger",
            "tawook",
            "taouk",
            "drumstick",
            "drumsticks",
            "sajji",
            "malai boti",
            "tandoori boti",
            "tikka boti",
            "patakha boti",
            "reshmi kebab",
            "reshmi kabab",
        ),
    ),
    "beef": I("bulk", animal="meat", aliases=("steak", "bistecca")),
    "mutton": I("bulk", animal="meat", aliases=("goat",)),
    "lamb": I("bulk", animal="meat"),
    "lamb fat": I("fat", animal="meat", aliases=("dumba",)),
    "turkey": I("bulk", animal="meat"),
    "liver": I("bulk", animal="meat", aliases=("kaleji", "kalegi")),
    "fish": I(
        "bulk",
        ("fish",),
        "fish",
        aliases=(
            "salmon",
            "tuna",
            "snapper",
            "tilapia",
            "rahu",
            "seabass",
            "sea bass",
            "cod",
            "sole",
            "basa",
            "pomfret",
            "trout",
            "mahseer",
            "mackerel",
            "machli",
            "machhli",
            "sake",  # salmon, on Japanese menus
            "toro",
            "sashimi",
            "nigiri",
            "seafood",
        ),
    ),
    "prawns": I(
        "bulk",
        ("shellfish",),
        "shellfish",
        aliases=("prawn", "shrimp", "shrimps", "jhinga", "goong", "ebi", "seafood"),
    ),
    "crab": I("bulk", ("shellfish",), "shellfish", aliases=("crabs",)),
    "lobster": I("bulk", ("shellfish",), "shellfish", aliases=("lobsters",)),
    "squid": I("bulk", ("shellfish",), "shellfish", aliases=("calamari",)),
    # Mussels and scallops were read as "fish", so they carried no shellfish allergen. ("Oyster"
    # stays with oyster sauce: on these menus it is the sauce, as in Chilli Oyster Chicken.)
    "molluscs": I(
        "bulk",
        ("shellfish",),
        "shellfish",
        aliases=("mussel", "mussels", "scallop", "scallops", "clam", "clams"),
    ),
    "anchovy": I("trace", ("fish",), "fish", aliases=("anchovies",)),
    # Puffed, fried starch crackers flavoured with fish or prawn. Named so the longer spelling
    # wins: "fish crackers" was read as "fish" and estimated as a plate of fried fish (43 g of
    # protein). They keep the allergen and the diet flags of the seafood in them.
    "fish crackers": I("bulk", ("fish",), "fish", aliases=("fish cracker",)),
    "prawn crackers": I(
        "bulk",
        ("shellfish",),
        "shellfish",
        aliases=(
            "prawn cracker",
            "prawns crackers",
            "prawns cracker",
            "shrimp crackers",
            "shrimp cracker",
            "krupuk",
            "keropok",
        ),
    ),
    "egg": I(
        "bulk",
        ("egg",),
        "egg",
        aliases=(
            "eggs",
            "anda",
            "omelette",
            "omelet",
            "omellete",
            "shakshuka",
            "shakshouka",
            "menemen",
            "cake",
            "cakes",
            "brownie",
            "brownies",
            "muffin",
            "muffins",
            "cupcake",
            "cupcakes",
            "waffle",
            "waffles",
            "pancake",
            "pancakes",
            "crepe",
            "crepes",
            "tempura",
            "tamago",
        ),
    ),
    "paneer": I("bulk", ("dairy",), "dairy"),
    "tofu": I("bulk", ("soy",)),
    "edamame": I("bulk", ("soy",), aliases=("edamame beans",)),
    "chickpeas": I(
        "bulk",
        aliases=("chickpea", "chana", "cholay", "chole", "hummus", "houmous", "hommus", "falafel"),
    ),
    "lentils": I("bulk", aliases=("lentil", "daal", "dal", "dhal", "moong")),
    "kidney beans": I("bulk", aliases=("rajma", "kidney bean")),
    "beans": I("bulk", aliases=("baked beans",)),
    "sausage": I("bulk", animal="meat", aliases=("sausages", "pepperoni", "salami", "frankfurter")),
    "pork": I("bulk", animal="meat", haram=True, aliases=("ham", "prosciutto")),
    "alcohol": I(
        "trace", haram=True, aliases=("wine", "beer", "rum", "brandy", "liqueur", "mirin")
    ),
    # ── Grains, breads, starches ─────────────────────────────────────────────
    "rice": I(
        "bulk",
        aliases=(
            "basmati",
            "chawal",
            "biryani",
            "biriyani",
            "pulao",
            "palau",
            "pilaf",
            "mandi",
            "kabsa",
            "kheer",
            "firni",
            "sushi",
            "maki",
            "uramaki",
            "nigiri",
        ),
    ),
    "wheat flour": I(
        "bulk",
        ("gluten",),
        aliases=(
            "flour",
            "maida",
            "atta",
            "wheat",
            "cookie",
            "cookies",
            "biscuit",
            "biscuits",
            "cake",
            "cakes",
            "brownie",
            "brownies",
            "muffin",
            "muffins",
            "cupcake",
            "cupcakes",
            "waffle",
            "waffles",
            "pancake",
            "pancakes",
            "crepe",
            "crepes",
            "tempura",
            "breadcrumbs",
            "bread crumbs",
            "panko",
            # Wheat wrappers, which carried no gluten unless the automated pass listed flour
            "wonton",
            "wontons",
            "dumpling",
            "dumplings",
            "momo",
            "momos",
            "gyoza",
            "dim sum",
            "shumai",
            "siu mai",
        ),
    ),
    "bread": I(
        "bulk", ("gluten",), aliases=("toast", "baguette", "loaf", "croutons", "sandwich", "panini")
    ),
    "bun": I("bulk", ("gluten",), aliases=("buns", "burger", "burgers", "slider", "sliders")),
    "naan": I("bulk", ("gluten",), aliases=("nan", "kulcha", "sheermal", "taftan")),
    "roti": I("bulk", ("gluten",), aliases=("chapati", "chapatti", "phulka")),
    "paratha": I("bulk", ("gluten",), aliases=("parotta", "lachha")),
    "puri": I("bulk", ("gluten",), aliases=("poori",)),
    "pita": I("bulk", ("gluten",), aliases=("pitta", "khubz", "lavash", "shawarma")),
    "tortilla": I(
        "bulk",
        ("gluten",),
        aliases=("wrap", "wraps", "fajita", "fajitas", "quesadilla", "taco", "tacos", "burrito"),
    ),
    "pizza base": I("bulk", ("gluten",), aliases=("pizza", "calzone")),
    "pastry": I(
        "bulk",
        ("gluten",),
        aliases=(
            "puff pastry",
            "croissant",
            "samosa",
            "samosas",
            "spring roll",
            "spring rolls",
            "fatayer",
            "pie",
            "puff",
        ),
    ),
    "noodles": I(
        "bulk", ("gluten",), aliases=("noodle", "chowmein", "chow mein", "ramen", "udon", "lo mein")
    ),
    "rice noodles": I("bulk", aliases=("pad thai",)),
    "pasta": I(
        "bulk",
        ("gluten",),
        aliases=(
            "spaghetti",
            "penne",
            "fettuccine",
            "fettuccini",
            "lasagna",
            "lasagne",
            "macaroni",
            "ravioli",
            "linguine",
            "fusilli",
            "alfredo",
            "carbonara",
            "arrabbiata",
        ),
    ),
    "vermicelli": I("bulk", ("gluten",), aliases=("seviyan", "sevaiyan")),
    "semolina": I("bulk", ("gluten",), aliases=("suji", "sooji")),
    "bulgur": I("bulk", ("gluten",), aliases=("burghul", "tabbouleh")),
    "oats": I("bulk", ("gluten",), aliases=("oatmeal", "porridge")),
    "gram flour": I("bulk", aliases=("besan", "pakora", "pakoray", "pakoda")),
    "corn": I("bulk", aliases=("sweetcorn", "sweet corn", "bhutta")),
    "potato": I(
        "bulk",
        aliases=("potatoes", "aloo", "alu", "mashed potato", "wedges", "hash brown", "hash browns"),
    ),
    "fries": I("bulk", aliases=("french fries", "curly fries", "masala fries")),
    # ── Dairy ────────────────────────────────────────────────────────────────
    "milk": I(
        "bulk",
        ("dairy",),
        "dairy",
        aliases=("doodh", "milkshake", "shake", "latte", "cappuccino", "kheer", "firni", "pudding"),
    ),
    "yogurt": I(
        "bulk",
        ("dairy",),
        "dairy",
        aliases=("yoghurt", "dahi", "raita", "lassi", "labneh", "labnah"),
    ),
    "cream": I(
        "fat", ("dairy",), "dairy", aliases=("malai", "malai boti", "creamy", "whipped cream")
    ),
    "butter": I("fat", ("dairy",), "dairy", aliases=("makhan", "makhni", "makhani")),
    "ghee": I("fat", ("dairy",), "dairy", aliases=("desi ghee",)),
    "cheese": I(
        "fat",
        ("dairy",),
        "dairy",
        aliases=(
            "cheesy",
            "mozzarella",
            "mozzarella cheese",
            "cheddar",
            "parmesan",
            "halloumi",
            "haloumi",
            "feta",
        ),
    ),
    "cream cheese": I("fat", ("dairy",), "dairy", aliases=("cheesecake", "philadelphia")),
    "condensed milk": I("bulk", ("dairy",), "dairy"),
    "ice cream": I("bulk", ("dairy",), "dairy", aliases=("icecream", "gelato", "sundae", "kulfi")),
    "khoya": I("bulk", ("dairy",), "dairy", aliases=("khoa", "mawa")),
    "custard": I("bulk", ("dairy", "egg"), "dairy"),
    # ── Fats and oils ────────────────────────────────────────────────────────
    "cooking oil": I("fat", aliases=("oil", "fried", "deep fried")),
    "olive oil": I("fat"),
    "mayonnaise": I("fat", ("egg",), "egg", aliases=("mayo", "aioli", "dynamite")),
    "tahini": I("fat", ("sesame",), aliases=("tahina", "hummus", "houmous", "hommus")),
    "coconut milk": I("fat", ("nuts",)),
    # ── Vegetables, herbs, fruit used as vegetables ──────────────────────────
    "onion": I("veg", aliases=("onions", "pyaz", "piaz")),
    "tomato": I("veg", aliases=("tomatoes", "tamatar", "marinara", "arrabbiata")),
    "garlic": I("veg", aliases=("lehsan",)),
    "ginger": I("veg", aliases=("adrak", "gari", "shoga")),
    "green chilli": I(
        "veg", aliases=("chilli", "chili", "chillies", "chilies", "jalapeno", "jalapenos", "mirch")
    ),
    "bell pepper": I("veg", aliases=("bell peppers", "capsicum", "shimla mirch")),
    "spinach": I("veg", aliases=("palak", "saag")),
    "eggplant": I(
        "veg", aliases=("brinjal", "baingan", "aubergine", "moutabal", "mutabal", "baba ghanoush")
    ),
    "okra": I("veg", aliases=("bhindi", "ladyfinger")),
    "cauliflower": I("veg", aliases=("gobi", "gobhi")),
    "cabbage": I("veg"),
    "carrot": I("veg", aliases=("carrots", "gajar")),
    "peas": I("veg", aliases=("matar", "mattar")),
    "mushrooms": I("veg", aliases=("mushroom", "khumb")),
    "cucumber": I("veg", aliases=("kheera",)),
    "lettuce": I("veg", aliases=("iceberg", "arugula", "rocket")),
    "spring onion": I("veg", aliases=("scallion", "scallions", "green onion")),
    "broccoli": I("veg"),
    "zucchini": I("veg", aliases=("courgette",)),
    "green beans": I("veg"),
    "herbs": I(
        "veg", aliases=("coriander", "dhania", "mint", "pudina", "parsley", "basil", "cilantro")
    ),
    "lemon": I("veg", aliases=("lime", "nimbu")),
    "olives": I("veg", aliases=("olive",)),
    "pickles": I("veg", aliases=("achar", "pickle", "gherkins")),
    "avocado": I("veg"),
    "beetroot": I("veg"),
    "pumpkin": I("veg", aliases=("kaddu",)),
    "mixed vegetables": I(
        "veg", aliases=("vegetable", "vegetables", "veg", "veggie", "veggies", "sabzi", "subzi")
    ),
    # ── Nuts and seeds ───────────────────────────────────────────────────────
    "almonds": I("fat", ("nuts",), aliases=("almond", "badam")),
    "cashews": I("fat", ("nuts",), aliases=("cashew", "kaju")),
    "pistachios": I("fat", ("nuts",), aliases=("pistachio", "pista")),
    "peanuts": I("fat", ("nuts",), aliases=("peanut",)),
    "walnuts": I("fat", ("nuts",), aliases=("walnut", "akhrot")),
    # Nutella is hazelnut spread: it was only chocolate, so it carried no nut allergen.
    "hazelnuts": I("trace", ("nuts",), aliases=("hazelnut", "nutella", "praline", "ferrero")),
    "sesame": I("fat", ("sesame",), aliases=("sesame seeds", "til")),
    "coconut": I("fat", ("nuts",), aliases=("nariyal",)),
    # ── Sweet ────────────────────────────────────────────────────────────────
    "sugar": I("bulk", aliases=("shakar",)),
    "honey": I("bulk", animal="honey", aliases=("shehad",)),
    "chocolate": I("bulk", ("dairy",), "dairy", aliases=("choco", "cocoa", "nutella")),
    "dates": I("bulk", aliases=("khajoor",)),
    "fruit": I(
        "bulk",
        aliases=(
            "fruits",
            "peach",
            "peaches",
            "blueberry",
            "blueberries",
            "berries",
            "raspberry",
            "raspberries",
            "orange",
            "oranges",
            "grapes",
            "kiwi",
            "watermelon",
            "melon",
            "lychee",
            "guava",
            "passion fruit",
        ),
    ),
    "mango": I("bulk", aliases=("aam",)),
    "strawberry": I("bulk", aliases=("strawberries",)),
    "banana": I("bulk", aliases=("bananas", "kela")),
    "apple": I("bulk", aliases=("apples",)),
    "pineapple": I("bulk"),
    "pomegranate": I("bulk", aliases=("pomegranates", "anar")),
    "raisins": I("bulk", aliases=("raisin", "kishmish", "sultanas")),
    "apricots": I("bulk", aliases=("apricot", "khubani")),
    "syrup": I("bulk", aliases=("maple syrup",)),
    "caramel": I("bulk", ("dairy",), "dairy"),
    "jam": I("bulk"),
    # ── Sauces and condiments (allergens matter, calories negligible) ────────
    "soy sauce": I("trace", ("soy", "gluten"), aliases=("soya sauce", "teriyaki", "manchurian")),
    "oyster sauce": I("trace", ("shellfish",), "shellfish", aliases=("oyster",)),
    "fish sauce": I("trace", ("fish",), "fish", aliases=("nam pla",)),
    "vinegar": I("trace", aliases=("sirka",)),
    "ketchup": I("trace"),
    "chilli sauce": I(
        "trace",
        aliases=(
            "hot sauce",
            "sriracha",
            "schezwan",
            "szechuan",
            "chili sauce",
            "szechuan sauce",
            "schezwan sauce",
            "hot garlic sauce",
        ),
    ),
    "bbq sauce": I("trace", aliases=("barbecue sauce",)),
    "peanut sauce": I("trace", ("nuts",), aliases=("satay",)),
    "sweet and sour sauce": I("trace", aliases=("sweet and sour", "sweet & sour")),
    # ── Drinks ───────────────────────────────────────────────────────────────
    "tea": I("bulk", aliases=("chai", "kehwa", "kahwa", "green tea")),
    "coffee": I("bulk", aliases=("espresso", "mocha", "americano", "frappe")),
    "soft drink": I(
        "bulk", aliases=("cola", "coke", "pepsi", "sprite", "7up", "fanta", "soda", "mirinda")
    ),
    "juice": I("bulk", aliases=("juices",)),
    "water": I("bulk", aliases=("mineral water",)),
}

ALLERGEN_TAGS = ("dairy", "egg", "fish", "shellfish", "gluten", "nuts", "soy", "sesame")


def _spelling_index() -> dict[str, tuple[str, ...]]:
    by_spelling: dict[str, list[str]] = {}
    for name, ing in VOCABULARY.items():
        for spelling in (name, *ing.aliases):
            by_spelling.setdefault(spelling.lower(), []).append(name)
    return {s: tuple(names) for s, names in by_spelling.items()}


# Any known spelling -> the vocabulary ingredient(s) it names ("feta" -> ("cheese",)).
SPELLING_TO_NAMES = _spelling_index()


def _spellings() -> list[tuple[re.Pattern, tuple[str, ...]]]:
    """Every spelling with the ingredients it names, longest first so 'spring onion' wins over 'onion'."""
    ordered = sorted(SPELLING_TO_NAMES.items(), key=lambda kv: len(kv[0]), reverse=True)
    return [(re.compile(r"\b" + re.escape(s) + r"\b", re.I), names) for s, names in ordered]


_SPELLINGS = _spellings()


def detect_ingredients(text: str) -> list[str]:
    """
    Ingredients named in a dish's name or description, in vocabulary order.

    Each spelling consumes the text it matched before shorter spellings are tried,
    so 'spring onion' is not also counted as 'onion'. A spelling listed under two
    ingredients ("hummus") yields both.
    """
    remaining = f" {text or ''} "
    found: set[str] = set()
    for pattern, names in _SPELLINGS:
        if pattern.search(remaining):
            found.update(names)
            remaining = pattern.sub(" ", remaining)
    return [name for name in VOCABULARY if name in found]


def derive_diet_flags(ingredients: list[str]) -> dict:
    """Allergens and diet flags implied by a list of vocabulary ingredients."""
    allergens, animals, haram = set(), set(), False
    for name in ingredients:
        ing = VOCABULARY[name]
        allergens.update(ing.allergens)
        if ing.animal:
            animals.add(ing.animal)
        haram = haram or ing.haram
    return {
        "allergens": sorted(allergens),
        "is_vegetarian": not animals & {"meat", "fish", "shellfish"},
        "is_vegan": not animals,
        "is_halal": not haram,
    }


# Names that mean a fried coating. Menus rarely list the batter or crumb, and the automated
# pass often leaves it out too, so without this a breaded dish reads as gluten-free.
COATED_NAME = re.compile(
    r"\b(?:breaded|crumbed|battered|crispy|nuggets?|broast(?:ed)?|zinger|strips|tenders|"
    r"(?<!lady )fingers?(?! chips)|katsu|schnitzel|cordon bleu|kiev|croquettes?|arancini|"
    r"popcorn chicken|fried (?:chicken|fish)|(?:mozzarella|cheese|halloumi) sticks|"
    r"fish (?:and|&|n) chips)\b",
    re.I,
)
# In a description only the explicit words count ("served with crispy onions" is no coating).
COATED_WORDS = re.compile(r"\b(?:breaded|crumbed|battered)\b", re.I)


def implied_coating(name: str, description: str, ingredients: list[str]) -> list[str]:
    """
    ["wheat flour"] when a dish's name means a fried coating its ingredients don't account
    for, otherwise []. It only ever adds an allergen: a dish that already carries gluten or
    names a gluten-free batter (gram flour pakoras) is left alone, and a dish with no known
    ingredients stays unknown rather than becoming "known: gluten only".
    """
    if not ingredients:
        return []
    if not (COATED_NAME.search(name or "") or COATED_WORDS.search(description or "")):
        return []
    if any("gluten" in VOCABULARY[i].allergens or i == "gram flour" for i in ingredients):
        return []
    return ["wheat flour"]


# Dishes whose standard recipe contains an allergen the name doesn't state. Menus and the
# automated pass leave these out, and a missing allergen is the unsafe direction: the dish is
# served to someone who excluded it. Like a coating, what a recipe implies counts for allergens
# and exclusions only, never for nutrition (a spoon of flour in nihari is not 280 g of wheat).
# The allergen audit of 2026-09-21 found each of these missing on real dishes.
RECIPE_IMPLIES = (
    (r"nihari|haleem", ("wheat flour",), "is thickened with wheat"),
    (r"kunaf[ae]h?|knafeh", ("wheat flour",), "is a wheat pastry"),
    (r"kung pao", ("peanuts",), "is made with peanuts"),
    (r"chapli|kofta|koftay", ("egg",), "is usually bound with egg"),
    (r"katsu|schnitzel|cordon bleu", ("egg",), "is breaded with an egg wash"),
    (r"kabuli pulao|kunaf[ae]h?|knafeh", ("pistachios",), "is garnished with nuts"),
    (r"(?<!namkeen )tikka|tandoori", ("yogurt",), "is usually marinated in yogurt"),
    (r"tom yum|tom kha", ("fish sauce",), "is made with fish sauce"),
    (r"korma|qorma", ("almonds",), "is often made with nuts"),
    (r"ca?esar|ceaser", ("anchovy",), "dressing is made with anchovy"),
)
_RECIPE_PATTERNS = [
    (re.compile(rf"\b(?:{p})\b", re.I), adds, why) for p, adds, why in RECIPE_IMPLIES
]


def implied_by_recipe(name: str, ingredients: list[str]) -> list[str]:
    """
    Ingredients a dish's standard recipe has that its list doesn't, for allergens only. Like
    the coating rule, it only ever adds, and a dish with no known ingredients stays unknown.
    """
    if not ingredients:
        return []
    added = []
    for pattern, adds, _ in _RECIPE_PATTERNS:
        if pattern.search(name or ""):
            added += [a for a in adds if a not in ingredients and a not in added]
    return added
