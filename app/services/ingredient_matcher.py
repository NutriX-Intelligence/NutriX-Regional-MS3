"""
NutriX - Ingredient Matching Engine

Provides fuzzy ingredient matching using RapidFuzz and a curated
synonym dictionary for common Indian ingredient name variations.

Supports:
  - Fuzzy string matching (tomato ≈ tomatoes, chilli ≈ chili)
  - Synonym resolution (capsicum ≈ bell pepper)
  - Ingredient match scoring per recipe
"""

from rapidfuzz import fuzz, process
from typing import List, Dict, Set, Tuple, Optional
import re

# ---------------------------------------------------------------------------
# Synonym dictionary: normalises variant spellings and Indian/English names
# ---------------------------------------------------------------------------
SYNONYM_MAP: Dict[str, str] = {
    # Chilli / Chilly / Chili
    "chilli": "chili",
    "chillies": "chili",
    "chilly": "chili",
    "green chilli": "green chili",
    "red chilli": "red chili",
    "dry red chilli": "dry red chili",
    "dried red chilli": "dry red chili",
    "chilli powder": "chili powder",
    "red chilli powder": "red chili powder",

    # Tomato / Tomatoes
    "tomatoes": "tomato",
    "tomato puree": "tomato puree",
    "tomato ketchup": "tomato sauce",

    # Capsicum / Bell pepper
    "capsicum": "bell pepper",
    "green capsicum": "green bell pepper",
    "red capsicum": "red bell pepper",
    "yellow capsicum": "yellow bell pepper",
    "bell peppers": "bell pepper",

    # Curd / Yogurt
    "curd": "yogurt",
    "curds": "yogurt",

    # Paneer / Cottage cheese
    "paneer": "paneer",
    "cottage cheese": "paneer",

    # Coriander / Cilantro
    "coriander": "cilantro",
    "coriander leaves": "cilantro",
    "fresh coriander": "cilantro",
    "dhaniya": "cilantro",

    # Aubergine / Eggplant / Brinjal
    "aubergine": "eggplant",
    "brinjal": "eggplant",
    "baingan": "eggplant",

    # Potato / Potatoes
    "potatoes": "potato",
    "aloo": "potato",

    # Onion / Onions
    "onions": "onion",
    "pyaaz": "onion",

    # Carrot / Carrots
    "carrots": "carrot",
    "gajar": "carrot",

    # Cauliflower / Gobi
    "gobi": "cauliflower",
    "phool gobi": "cauliflower",

    # Cabbage / Patta gobi
    "patta gobi": "cabbage",
    "band gobi": "cabbage",

    # Spinach / Palak
    "palak": "spinach",
    "saag": "spinach",

    # Ladyfinger / Okra / Bhindi
    "ladyfinger": "okra",
    "lady finger": "okra",
    "bhindi": "okra",
    "okra": "okra",

    # Peas / Mattar
    "mattar": "peas",
    "matar": "peas",
    "green peas": "peas",

    # Gram flour / Besan
    "besan": "gram flour",
    "chickpea flour": "gram flour",

    # Semolina / Sooji / Rava
    "sooji": "semolina",
    "rava": "semolina",

    # Ghee / Clarified butter
    "ghee": "ghee",
    "clarified butter": "ghee",

    # Coconut
    "coconut milk": "coconut milk",
    "coconut cream": "coconut cream",
    "grated coconut": "coconut",
    "fresh coconut": "coconut",

    # Ginger
    "adrak": "ginger",
    "fresh ginger": "ginger",

    # Garlic
    "lasan": "garlic",
    "lahsun": "garlic",

    # Turmeric
    "turmeric powder": "turmeric",
    "haldi": "turmeric",

    # Cumin
    "cumin seeds": "cumin",
    "jeera": "cumin",
    "zeera": "cumin",

    # Mustard
    "mustard seeds": "mustard",
    "rai": "mustard",
    "sarson": "mustard",

    # Fenugreek
    "methi": "fenugreek",
    "fenugreek leaves": "fenugreek",
    "fenugreek seeds": "fenugreek",

    # Asafoetida
    "hing": "asafoetida",

    # Cardamom
    "elaichi": "cardamom",
    "green cardamom": "cardamom",

    # Cloves
    "laung": "cloves",
    "lavang": "cloves",

    # Cinnamon
    "dalchini": "cinnamon",

    # Black pepper
    "kali mirch": "black pepper",
    "peppercorns": "black pepper",

    # Lemon / Lime / Nimbu
    "nimbu": "lemon",
    "nimbu pani": "lemonade",
    "nimbu paani": "lemonade",
    "lemonade": "lemonade",
    "lime": "lemon",
    "lemons": "lemon",
    "limes": "lemon",

    # Mint / Pudina
    "pudina": "mint",
    "mint leaves": "mint",

    # Curd / Dahi / Yogurt
    "dahi": "yogurt",
    "yogurt": "yogurt",

    # Dal / Lentils / Pulses
    "toor dal": "dal",
    "tuvar dal": "dal",
    "chana dal": "dal",
    "moong dal": "dal",
    "urad dal": "dal",
    "masoor dal": "dal",
    "arhar dal": "dal",
    "yellow dal": "dal",
    "split chickpeas": "dal",
    "lentils": "dal",
    "pulses": "dal",
}

# ---------------------------------------------------------------------------
# Ingredient normalisation
# ---------------------------------------------------------------------------
# Stop-words that add no semantic value for matching
_STOP_WORDS: Set[str] = {"fresh", "dried", "dry", "raw", "chopped", "diced",
                         "sliced", "crushed", "minced", "grated", "ground",
                         "whole", "powdered", "roasted", "fried", "boiled",
                         "cooked", "small", "large", "medium", "optional",
                         "to", "taste", "as", "needed", "for", "garnish",
                         "some", "a", "an", "the", "or", "and", ","}


def clean_ingredient(name: str) -> str:
    """Lowercase, strip, remove parenthetical notes and stop-words."""
    name = name.lower().strip()
    name = re.sub(r"\(.*?\)", "", name)          # remove (optional), (to taste) …
    name = re.sub(r"\s+", " ", name).strip()
    # Remove trailing/leading stop-words (single-pass)
    tokens = [t for t in name.split()
              if t not in _STOP_WORDS and not t.isdigit()]
    return " ".join(tokens)


def normalise(name: str) -> str:
    """Apply synonym map and clean."""
    name = clean_ingredient(name)
    # Apply synonym map – only whole-word matches
    for raw, canonical in SYNONYM_MAP.items():
        # Replace whole word occurrences
        name = re.sub(rf"\b{re.escape(raw)}\b", canonical, name)
    return name


def extract_core_ingredient(name: str) -> str:
    """Return the shortest meaningful ingredient stem (e.g. 'chili powder' → 'chili')."""
    name = normalise(name)
    # Take the first 1-2 tokens that aren't generic
    tokens = name.split()
    if not tokens:
        return ""
    # If the last token is a generic qualifier like 'powder', 'leaves', 'seeds',
    # keep the preceding term too
    generics = {"powder", "leaves", "seeds", "paste", "pieces", "strips", "root"}
    if len(tokens) >= 2 and tokens[-1] in generics:
        return " ".join(tokens[-2:])
    return tokens[0]


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------
MIN_FUZZY_SCORE: int = 78  # threshold for fuzzy ingredient match


def fuzzy_match_ingredient(user_ing: str, recipe_ing: str) -> bool:
    """
    Return True if the two ingredient names are considered a match,
    using normalisation, token-set-ratio and partial-ratio from RapidFuzz.
    """
    u_norm = normalise(user_ing)
    r_norm = normalise(recipe_ing)

    if not u_norm or not r_norm:
        return False

    # Exact match after normalisation
    if u_norm == r_norm:
        return True

    # Word boundary match (e.g. user enters "dal", "paneer", "rice", "curd")
    if len(u_norm) >= 3 and re.search(rf"\b{re.escape(u_norm)}\b", r_norm):
        return True
    if len(r_norm) >= 3 and re.search(rf"\b{re.escape(r_norm)}\b", u_norm):
        return True

    # Check if core ingredient is present in the other
    u_core = extract_core_ingredient(user_ing)
    r_core = extract_core_ingredient(recipe_ing)

    if u_core and r_core and u_core == r_core:
        return True

    # Fuzzy scoring
    score = fuzz.token_sort_ratio(u_norm, r_norm)
    if score >= MIN_FUZZY_SCORE:
        return True

    # Partial matching – user ingredient appears within recipe ingredient
    partial = fuzz.partial_ratio(u_norm, r_norm)
    if partial >= MIN_FUZZY_SCORE:
        return True

    return False


def compute_ingredient_match_score(
    user_ingredients: List[str],
    recipe_ingredients: List[str],
) -> Tuple[float, List[str], List[str]]:
    """
    For a single recipe, compute a composite match score:
      score = 0.7 * query_coverage + 0.3 * recipe_coverage
    
    Where:
      query_coverage = unique_matched_user_ingredients / total_user_ingredients
      recipe_coverage = matched_recipe_ingredients / total_recipe_ingredients

    Returns (score, matched_ingredients, unmatched_recipe_ingredients).
    """
    if not recipe_ingredients or not user_ingredients:
        return 0.0, [], recipe_ingredients

    matched: List[str] = []
    unmatched: List[str] = []
    matched_user_ingredients_set = set()

    for r_ing in recipe_ingredients:
        is_matched = False
        for u_ing in user_ingredients:
            if fuzzy_match_ingredient(u_ing, r_ing):
                is_matched = True
                matched.append(r_ing)
                matched_user_ingredients_set.add(u_ing)
                break
        if not is_matched:
            unmatched.append(r_ing)

    total_recipe = len(recipe_ingredients)
    recipe_coverage = len(matched) / total_recipe if total_recipe > 0 else 0.0

    total_user = len(user_ingredients)
    query_coverage = len(matched_user_ingredients_set) / total_user if total_user > 0 else 0.0

    score = 0.7 * query_coverage + 0.3 * recipe_coverage
    return score, matched, unmatched


def find_top_ingredient_matches(
    user_ingredients: List[str],
    all_recipe_ingredients: Dict[str, List[str]],
    top_n: int = 50,
) -> List[Tuple[str, float, List[str], List[str]]]:
    """
    Rank all recipes by ingredient match score.

    Returns list of (recipe_code, match_score, matched_ings, unmatched_ings).
    """
    scored: List[Tuple[str, float, List[str], List[str]]] = []
    for recipe_code, ings in all_recipe_ingredients.items():
        score, matched, unmatched = compute_ingredient_match_score(
            user_ingredients, ings
        )
        if score > 0.0:
            scored.append((recipe_code, score, matched, unmatched))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_n]


def build_synonym_suggestions(ingredient: str) -> List[str]:
    """Return known synonyms for a given ingredient (for autocomplete)."""
    ing = normalise(ingredient)
    suggestions: List[str] = []
    for raw, canonical in SYNONYM_MAP.items():
        if canonical == ing:
            suggestions.append(raw)
        elif raw == ing:
            suggestions.append(canonical)
    return list(set(suggestions))
