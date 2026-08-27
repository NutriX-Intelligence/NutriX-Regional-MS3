import re
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from app.models import Food, FoodNutrient, UnitConversion, HomelyMeal, HomelyMealIngredient, HomelyMealNutrition, HomelyMealReview, HomelyMealTag, HomelyMealVersion

def parse_gram_weight(db_session: Session, food_item: str, unit: str, amount: float) -> float:
    """
    Resolves ingredient quantity to grams using unit_conversions database and standard fallback rules.
    """
    unit_normalized = unit.strip().lower()
    food_normalized = food_item.strip().lower()

    # 1. Try exact match in database
    exact = db_session.query(UnitConversion).filter(
        func.lower(UnitConversion.food_item) == food_normalized,
        func.lower(UnitConversion.unit) == unit_normalized
    ).first()
    if exact:
        return exact.gram_weight * amount

    # 2. Try fuzzy match on food item name with same unit
    words = [w for w in re.findall(r'[a-z0-9]+', food_normalized) if len(w) > 2]
    if words:
        query_filters = [UnitConversion.food_item.ilike(f"%{w}%") for w in words]
        potential_convs = db_session.query(UnitConversion).filter(
            or_(*query_filters),
            func.lower(UnitConversion.unit) == unit_normalized
        ).all()
        if potential_convs:
            # Score matches based on overlap
            best_match = None
            best_score = -1.0
            query_set = set(words)
            for conv in potential_convs:
                conv_words = set(re.findall(r'[a-z0-9]+', conv.food_item.lower()))
                overlap = query_set.intersection(conv_words)
                score = len(overlap) / len(query_set)
                if score > best_score:
                    best_score = score
                    best_match = conv
            if best_match:
                return best_match.gram_weight * amount

    # 3. Fallback to standard conversion rules
    coeff = amount
    if 'tsp' in unit_normalized or 'teaspoon' in unit_normalized:
        return coeff * 5.0
    elif 'tbsp' in unit_normalized or 'tablespoon' in unit_normalized:
        return coeff * 15.0
    elif 'cup' in unit_normalized or unit_normalized == 'c':
        return coeff * 240.0
    elif 'glass' in unit_normalized:
        return coeff * 200.0
    elif 'bowl' in unit_normalized:
        return coeff * 200.0
    elif 'piece' in unit_normalized or 'pcs' in unit_normalized or 'pc' in unit_normalized or 'slice' in unit_normalized:
        return coeff * 50.0
    elif 'pinch' in unit_normalized or 'dash' in unit_normalized:
        return coeff * 1.0
    elif 'g' == unit_normalized or 'gram' in unit_normalized or 'ml' == unit_normalized:
        return coeff * 1.0

    # General default fallback: 1.0 gram per unit
    return coeff * 1.0

VERIFIED_INGREDIENTS_NUTRITION = {
    # Dairy / Fats / Oils
    "butter": {"energy_kcal": 717.0, "protein_g": 0.9, "carb_g": 0.1, "fat_g": 81.1, "fibre_g": 0.0, "sodium_mg": 600.0, "sugar_g": 0.1},
    "white butter": {"energy_kcal": 717.0, "protein_g": 0.9, "carb_g": 0.1, "fat_g": 81.1, "fibre_g": 0.0, "sodium_mg": 20.0, "sugar_g": 0.1},
    "makkhan": {"energy_kcal": 717.0, "protein_g": 0.9, "carb_g": 0.1, "fat_g": 81.1, "fibre_g": 0.0, "sodium_mg": 20.0, "sugar_g": 0.1},
    "paneer": {"energy_kcal": 265.0, "protein_g": 18.3, "carb_g": 3.4, "fat_g": 20.8, "fibre_g": 0.0, "sodium_mg": 25.0, "sugar_g": 2.5},
    "cottage cheese": {"energy_kcal": 265.0, "protein_g": 18.3, "carb_g": 3.4, "fat_g": 20.8, "fibre_g": 0.0, "sodium_mg": 25.0, "sugar_g": 2.5},
    "dahi": {"energy_kcal": 60.0, "protein_g": 3.5, "carb_g": 4.7, "fat_g": 3.2, "fibre_g": 0.0, "sodium_mg": 50.0, "sugar_g": 4.0},
    "curd": {"energy_kcal": 60.0, "protein_g": 3.5, "carb_g": 4.7, "fat_g": 3.2, "fibre_g": 0.0, "sodium_mg": 50.0, "sugar_g": 4.0},
    "yogurt": {"energy_kcal": 60.0, "protein_g": 3.5, "carb_g": 4.7, "fat_g": 3.2, "fibre_g": 0.0, "sodium_mg": 50.0, "sugar_g": 4.0},
    "ghee": {"energy_kcal": 900.0, "protein_g": 0.0, "carb_g": 0.0, "fat_g": 100.0, "fibre_g": 0.0, "sodium_mg": 0.0, "sugar_g": 0.0},
    "desi ghee": {"energy_kcal": 900.0, "protein_g": 0.0, "carb_g": 0.0, "fat_g": 100.0, "fibre_g": 0.0, "sodium_mg": 0.0, "sugar_g": 0.0},
    "oil": {"energy_kcal": 884.0, "protein_g": 0.0, "carb_g": 0.0, "fat_g": 100.0, "fibre_g": 0.0, "sodium_mg": 0.0, "sugar_g": 0.0},
    "mustard oil": {"energy_kcal": 884.0, "protein_g": 0.0, "carb_g": 0.0, "fat_g": 100.0, "fibre_g": 0.0, "sodium_mg": 0.0, "sugar_g": 0.0},
    "olive oil": {"energy_kcal": 884.0, "protein_g": 0.0, "carb_g": 0.0, "fat_g": 100.0, "fibre_g": 0.0, "sodium_mg": 0.0, "sugar_g": 0.0},
    "coconut oil": {"energy_kcal": 884.0, "protein_g": 0.0, "carb_g": 0.0, "fat_g": 100.0, "fibre_g": 0.0, "sodium_mg": 0.0, "sugar_g": 0.0},
    "cheese": {"energy_kcal": 320.0, "protein_g": 20.0, "carb_g": 2.5, "fat_g": 26.0, "fibre_g": 0.0, "sodium_mg": 800.0, "sugar_g": 0.5},
    "milk": {"energy_kcal": 62.0, "protein_g": 3.2, "carb_g": 4.8, "fat_g": 3.3, "fibre_g": 0.0, "sodium_mg": 45.0, "sugar_g": 4.8},
    "chaas": {"energy_kcal": 40.0, "protein_g": 2.0, "carb_g": 4.8, "fat_g": 1.2, "fibre_g": 0.0, "sodium_mg": 120.0, "sugar_g": 3.5},
    "buttermilk": {"energy_kcal": 40.0, "protein_g": 2.0, "carb_g": 4.8, "fat_g": 1.2, "fibre_g": 0.0, "sodium_mg": 120.0, "sugar_g": 3.5},
    "cream": {"energy_kcal": 340.0, "protein_g": 2.8, "carb_g": 3.7, "fat_g": 36.0, "fibre_g": 0.0, "sodium_mg": 35.0, "sugar_g": 3.5},
    "malai": {"energy_kcal": 340.0, "protein_g": 2.8, "carb_g": 3.7, "fat_g": 36.0, "fibre_g": 0.0, "sodium_mg": 35.0, "sugar_g": 3.5},
    
    # Spices / Condiments / Toppings
    "salt": {"energy_kcal": 0.0, "protein_g": 0.0, "carb_g": 0.0, "fat_g": 0.0, "fibre_g": 0.0, "sodium_mg": 38758.0, "sugar_g": 0.0},
    "namak": {"energy_kcal": 0.0, "protein_g": 0.0, "carb_g": 0.0, "fat_g": 0.0, "fibre_g": 0.0, "sodium_mg": 38758.0, "sugar_g": 0.0},
    "sugar": {"energy_kcal": 387.0, "protein_g": 0.0, "carb_g": 100.0, "fat_g": 0.0, "fibre_g": 0.0, "sodium_mg": 1.0, "sugar_g": 100.0},
    "jaggery": {"energy_kcal": 383.0, "protein_g": 0.4, "carb_g": 95.0, "fat_g": 0.1, "fibre_g": 0.0, "sodium_mg": 30.0, "sugar_g": 85.0},
    "gud": {"energy_kcal": 383.0, "protein_g": 0.4, "carb_g": 95.0, "fat_g": 0.1, "fibre_g": 0.0, "sodium_mg": 30.0, "sugar_g": 85.0},
    "turmeric": {"energy_kcal": 354.0, "protein_g": 7.8, "carb_g": 65.0, "fat_g": 10.0, "fibre_g": 21.0, "sodium_mg": 38.0, "sugar_g": 3.0},
    "haldi": {"energy_kcal": 354.0, "protein_g": 7.8, "carb_g": 65.0, "fat_g": 10.0, "fibre_g": 21.0, "sodium_mg": 38.0, "sugar_g": 3.0},
    "chilli powder": {"energy_kcal": 282.0, "protein_g": 12.0, "carb_g": 50.0, "fat_g": 14.0, "fibre_g": 34.0, "sodium_mg": 30.0, "sugar_g": 7.0},
    "lal mirch": {"energy_kcal": 282.0, "protein_g": 12.0, "carb_g": 50.0, "fat_g": 14.0, "fibre_g": 34.0, "sodium_mg": 30.0, "sugar_g": 7.0},
    "coriander powder": {"energy_kcal": 298.0, "protein_g": 12.4, "carb_g": 55.0, "fat_g": 17.8, "fibre_g": 42.0, "sodium_mg": 35.0, "sugar_g": 2.0},
    "dhania": {"energy_kcal": 298.0, "protein_g": 12.4, "carb_g": 55.0, "fat_g": 17.8, "fibre_g": 42.0, "sodium_mg": 35.0, "sugar_g": 2.0},
    "cumin": {"energy_kcal": 375.0, "protein_g": 18.0, "carb_g": 44.0, "fat_g": 22.0, "fibre_g": 10.5, "sodium_mg": 168.0, "sugar_g": 2.2},
    "jeera": {"energy_kcal": 375.0, "protein_g": 18.0, "carb_g": 44.0, "fat_g": 22.0, "fibre_g": 10.5, "sodium_mg": 168.0, "sugar_g": 2.2},
    "mustard seeds": {"energy_kcal": 508.0, "protein_g": 26.0, "carb_g": 28.0, "fat_g": 36.0, "fibre_g": 12.0, "sodium_mg": 13.0, "sugar_g": 6.0},
    "rai": {"energy_kcal": 508.0, "protein_g": 26.0, "carb_g": 28.0, "fat_g": 36.0, "fibre_g": 12.0, "sodium_mg": 13.0, "sugar_g": 6.0},
    "garam masala": {"energy_kcal": 378.0, "protein_g": 13.0, "carb_g": 58.0, "fat_g": 15.0, "fibre_g": 25.0, "sodium_mg": 50.0, "sugar_g": 3.0},
    "ginger garlic paste": {"energy_kcal": 80.0, "protein_g": 4.0, "carb_g": 15.0, "fat_g": 0.8, "fibre_g": 3.0, "sodium_mg": 120.0, "sugar_g": 2.0},
    "ginger": {"energy_kcal": 80.0, "protein_g": 1.8, "carb_g": 17.8, "fat_g": 0.7, "fibre_g": 2.0, "sodium_mg": 13.0, "sugar_g": 1.7},
    "adrak": {"energy_kcal": 80.0, "protein_g": 1.8, "carb_g": 17.8, "fat_g": 0.7, "fibre_g": 2.0, "sodium_mg": 13.0, "sugar_g": 1.7},
    "garlic": {"energy_kcal": 149.0, "protein_g": 6.4, "carb_g": 33.0, "fat_g": 0.5, "fibre_g": 2.1, "sodium_mg": 17.0, "sugar_g": 1.0},
    "lahsun": {"energy_kcal": 149.0, "protein_g": 6.4, "carb_g": 33.0, "fat_g": 0.5, "fibre_g": 2.1, "sodium_mg": 17.0, "sugar_g": 1.0},
    "green chutney": {"energy_kcal": 40.0, "protein_g": 2.0, "carb_g": 6.0, "fat_g": 1.0, "fibre_g": 2.0, "sodium_mg": 600.0, "sugar_g": 0.5},
    "chutney": {"energy_kcal": 65.0, "protein_g": 2.0, "carb_g": 10.0, "fat_g": 2.0, "fibre_g": 2.0, "sodium_mg": 500.0, "sugar_g": 2.0},
    "imli chutney": {"energy_kcal": 180.0, "protein_g": 1.0, "carb_g": 45.0, "fat_g": 0.2, "fibre_g": 1.5, "sodium_mg": 450.0, "sugar_g": 38.0},
    "tamarind chutney": {"energy_kcal": 180.0, "protein_g": 1.0, "carb_g": 45.0, "fat_g": 0.2, "fibre_g": 1.5, "sodium_mg": 450.0, "sugar_g": 38.0},
    "pickle": {"energy_kcal": 175.0, "protein_g": 2.0, "carb_g": 11.0, "fat_g": 14.0, "fibre_g": 3.0, "sodium_mg": 1200.0, "sugar_g": 2.0},
    "achar": {"energy_kcal": 175.0, "protein_g": 2.0, "carb_g": 11.0, "fat_g": 14.0, "fibre_g": 3.0, "sodium_mg": 1200.0, "sugar_g": 2.0},
    "sev": {"energy_kcal": 560.0, "protein_g": 12.0, "carb_g": 42.0, "fat_g": 38.0, "fibre_g": 4.5, "sodium_mg": 720.0, "sugar_g": 1.5},
    "bhujia": {"energy_kcal": 560.0, "protein_g": 12.0, "carb_g": 42.0, "fat_g": 38.0, "fibre_g": 4.5, "sodium_mg": 720.0, "sugar_g": 1.5},
    "peanuts": {"energy_kcal": 567.0, "protein_g": 25.8, "carb_g": 16.1, "fat_g": 49.2, "fibre_g": 8.5, "sodium_mg": 18.0, "sugar_g": 4.7},
    "singdana": {"energy_kcal": 567.0, "protein_g": 25.8, "carb_g": 16.1, "fat_g": 49.2, "fibre_g": 8.5, "sodium_mg": 18.0, "sugar_g": 4.7},

    # Grains & Flours
    "atta": {"energy_kcal": 340.0, "protein_g": 12.0, "carb_g": 72.0, "fat_g": 1.7, "fibre_g": 10.5, "sodium_mg": 5.0, "sugar_g": 0.4},
    "wheat flour": {"energy_kcal": 340.0, "protein_g": 12.0, "carb_g": 72.0, "fat_g": 1.7, "fibre_g": 10.5, "sodium_mg": 5.0, "sugar_g": 0.4},
    "rice": {"energy_kcal": 360.0, "protein_g": 7.5, "carb_g": 79.0, "fat_g": 0.6, "fibre_g": 1.5, "sodium_mg": 5.0, "sugar_g": 0.1},
    "chawal": {"energy_kcal": 360.0, "protein_g": 7.5, "carb_g": 79.0, "fat_g": 0.6, "fibre_g": 1.5, "sodium_mg": 5.0, "sugar_g": 0.1},
    "cooked rice": {"energy_kcal": 130.0, "protein_g": 2.7, "carb_g": 28.0, "fat_g": 0.3, "fibre_g": 0.4, "sodium_mg": 1.0, "sugar_g": 0.1},
    "maida": {"energy_kcal": 364.0, "protein_g": 10.3, "carb_g": 76.3, "fat_g": 1.0, "fibre_g": 2.7, "sodium_mg": 2.0, "sugar_g": 0.3},
    "besan": {"energy_kcal": 387.0, "protein_g": 22.4, "carb_g": 57.8, "fat_g": 6.7, "fibre_g": 10.8, "sodium_mg": 64.0, "sugar_g": 10.8},
    "gram flour": {"energy_kcal": 387.0, "protein_g": 22.4, "carb_g": 57.8, "fat_g": 6.7, "fibre_g": 10.8, "sodium_mg": 64.0, "sugar_g": 10.8},
    "sooji": {"energy_kcal": 360.0, "protein_g": 12.7, "carb_g": 73.0, "fat_g": 1.0, "fibre_g": 3.9, "sodium_mg": 1.0, "sugar_g": 0.1},
    "rava": {"energy_kcal": 360.0, "protein_g": 12.7, "carb_g": 73.0, "fat_g": 1.0, "fibre_g": 3.9, "sodium_mg": 1.0, "sugar_g": 0.1},
    "oats": {"energy_kcal": 389.0, "protein_g": 16.9, "carb_g": 66.3, "fat_g": 6.9, "fibre_g": 10.6, "sodium_mg": 2.0, "sugar_g": 0.0},
    "poha": {"energy_kcal": 350.0, "protein_g": 6.6, "carb_g": 77.0, "fat_g": 1.2, "fibre_g": 2.8, "sodium_mg": 5.0, "sugar_g": 0.5},

    # Dals & Pulses
    "toor dal": {"energy_kcal": 343.0, "protein_g": 22.0, "carb_g": 63.0, "fat_g": 1.5, "fibre_g": 15.0, "sodium_mg": 17.0, "sugar_g": 0.0},
    "arhar dal": {"energy_kcal": 343.0, "protein_g": 22.0, "carb_g": 63.0, "fat_g": 1.5, "fibre_g": 15.0, "sodium_mg": 17.0, "sugar_g": 0.0},
    "moong dal": {"energy_kcal": 347.0, "protein_g": 24.0, "carb_g": 60.0, "fat_g": 1.2, "fibre_g": 16.0, "sodium_mg": 15.0, "sugar_g": 0.0},
    "chana dal": {"energy_kcal": 372.0, "protein_g": 21.0, "carb_g": 60.0, "fat_g": 5.6, "fibre_g": 15.0, "sodium_mg": 20.0, "sugar_g": 0.0},
    "urad dal": {"energy_kcal": 341.0, "protein_g": 25.0, "carb_g": 59.0, "fat_g": 1.6, "fibre_g": 18.0, "sodium_mg": 18.0, "sugar_g": 0.0},
    "rajma": {"energy_kcal": 333.0, "protein_g": 24.0, "carb_g": 60.0, "fat_g": 1.0, "fibre_g": 24.0, "sodium_mg": 24.0, "sugar_g": 2.0},
    "chole": {"energy_kcal": 364.0, "protein_g": 19.0, "carb_g": 61.0, "fat_g": 6.0, "fibre_g": 17.0, "sodium_mg": 24.0, "sugar_g": 2.0},
    "chickpeas": {"energy_kcal": 364.0, "protein_g": 19.0, "carb_g": 61.0, "fat_g": 6.0, "fibre_g": 17.0, "sodium_mg": 24.0, "sugar_g": 2.0},
    "dal": {"energy_kcal": 345.0, "protein_g": 23.0, "carb_g": 61.0, "fat_g": 2.0, "fibre_g": 16.0, "sodium_mg": 16.0, "sugar_g": 0.0},

    # Proteins & Meats
    "egg": {"energy_kcal": 143.0, "protein_g": 12.6, "carb_g": 0.7, "fat_g": 9.5, "fibre_g": 0.0, "sodium_mg": 142.0, "sugar_g": 0.4},
    "egg white": {"energy_kcal": 52.0, "protein_g": 11.0, "carb_g": 0.7, "fat_g": 0.2, "fibre_g": 0.0, "sodium_mg": 166.0, "sugar_g": 0.7},
    "chicken": {"energy_kcal": 215.0, "protein_g": 24.0, "carb_g": 0.0, "fat_g": 13.0, "fibre_g": 0.0, "sodium_mg": 70.0, "sugar_g": 0.0},
    "chicken breast": {"energy_kcal": 165.0, "protein_g": 31.0, "carb_g": 0.0, "fat_g": 3.6, "fibre_g": 0.0, "sodium_mg": 65.0, "sugar_g": 0.0},
    "mutton": {"energy_kcal": 250.0, "protein_g": 25.0, "carb_g": 0.0, "fat_g": 16.0, "fibre_g": 0.0, "sodium_mg": 72.0, "sugar_g": 0.0},
    "fish": {"energy_kcal": 120.0, "protein_g": 20.0, "carb_g": 0.0, "fat_g": 4.0, "fibre_g": 0.0, "sodium_mg": 60.0, "sugar_g": 0.0},
    "tofu": {"energy_kcal": 76.0, "protein_g": 8.0, "carb_g": 1.9, "fat_g": 4.8, "fibre_g": 0.3, "sodium_mg": 7.0, "sugar_g": 0.5},
    "soya chunks": {"energy_kcal": 345.0, "protein_g": 52.0, "carb_g": 33.0, "fat_g": 0.5, "fibre_g": 13.0, "sodium_mg": 20.0, "sugar_g": 0.0},

    # Vegetables
    "potato": {"energy_kcal": 77.0, "protein_g": 2.0, "carb_g": 17.0, "fat_g": 0.1, "fibre_g": 2.2, "sodium_mg": 6.0, "sugar_g": 0.8},
    "aloo": {"energy_kcal": 77.0, "protein_g": 2.0, "carb_g": 17.0, "fat_g": 0.1, "fibre_g": 2.2, "sodium_mg": 6.0, "sugar_g": 0.8},
    "onion": {"energy_kcal": 40.0, "protein_g": 1.1, "carb_g": 9.3, "fat_g": 0.1, "fibre_g": 1.7, "sodium_mg": 4.0, "sugar_g": 4.2},
    "pyaz": {"energy_kcal": 40.0, "protein_g": 1.1, "carb_g": 9.3, "fat_g": 0.1, "fibre_g": 1.7, "sodium_mg": 4.0, "sugar_g": 4.2},
    "tomato": {"energy_kcal": 18.0, "protein_g": 0.9, "carb_g": 3.9, "fat_g": 0.2, "fibre_g": 1.2, "sodium_mg": 5.0, "sugar_g": 2.6},
    "tamatar": {"energy_kcal": 18.0, "protein_g": 0.9, "carb_g": 3.9, "fat_g": 0.2, "fibre_g": 1.2, "sodium_mg": 5.0, "sugar_g": 2.6},
    "spinach": {"energy_kcal": 23.0, "protein_g": 2.9, "carb_g": 3.6, "fat_g": 0.4, "fibre_g": 2.2, "sodium_mg": 79.0, "sugar_g": 0.4},
    "palak": {"energy_kcal": 23.0, "protein_g": 2.9, "carb_g": 3.6, "fat_g": 0.4, "fibre_g": 2.2, "sodium_mg": 79.0, "sugar_g": 0.4},
    "cauliflower": {"energy_kcal": 25.0, "protein_g": 1.9, "carb_g": 5.0, "fat_g": 0.3, "fibre_g": 2.0, "sodium_mg": 30.0, "sugar_g": 1.9},
    "gobi": {"energy_kcal": 25.0, "protein_g": 1.9, "carb_g": 5.0, "fat_g": 0.3, "fibre_g": 2.0, "sodium_mg": 30.0, "sugar_g": 1.9},
    "green peas": {"energy_kcal": 81.0, "protein_g": 5.4, "carb_g": 14.5, "fat_g": 0.4, "fibre_g": 5.7, "sodium_mg": 5.0, "sugar_g": 5.7},
    "matar": {"energy_kcal": 81.0, "protein_g": 5.4, "carb_g": 14.5, "fat_g": 0.4, "fibre_g": 5.7, "sodium_mg": 5.0, "sugar_g": 5.7},
    "capsicum": {"energy_kcal": 20.0, "protein_g": 0.9, "carb_g": 4.6, "fat_g": 0.2, "fibre_g": 1.7, "sodium_mg": 3.0, "sugar_g": 2.4},
    "carrot": {"energy_kcal": 41.0, "protein_g": 0.9, "carb_g": 9.6, "fat_g": 0.2, "fibre_g": 2.8, "sodium_mg": 69.0, "sugar_g": 4.7},
    "bhindi": {"energy_kcal": 33.0, "protein_g": 1.9, "carb_g": 7.5, "fat_g": 0.2, "fibre_g": 3.2, "sodium_mg": 7.0, "sugar_g": 1.5},
    "lauki": {"energy_kcal": 14.0, "protein_g": 0.6, "carb_g": 3.4, "fat_g": 0.1, "fibre_g": 0.5, "sodium_mg": 2.0, "sugar_g": 2.0},
    "mushroom": {"energy_kcal": 22.0, "protein_g": 3.1, "carb_g": 3.3, "fat_g": 0.3, "fibre_g": 1.0, "sodium_mg": 5.0, "sugar_g": 2.0},
    "coriander leaves": {"energy_kcal": 23.0, "protein_g": 2.1, "carb_g": 3.7, "fat_g": 0.5, "fibre_g": 2.8, "sodium_mg": 46.0, "sugar_g": 0.9},
    "mint": {"energy_kcal": 44.0, "protein_g": 3.3, "carb_g": 8.4, "fat_g": 0.7, "fibre_g": 6.8, "sodium_mg": 31.0, "sugar_g": 0.0},
    "pudina": {"energy_kcal": 44.0, "protein_g": 3.3, "carb_g": 8.4, "fat_g": 0.7, "fibre_g": 6.8, "sodium_mg": 31.0, "sugar_g": 0.0},
    "lemon": {"energy_kcal": 29.0, "protein_g": 1.1, "carb_g": 9.3, "fat_g": 0.3, "fibre_g": 2.8, "sodium_mg": 2.0, "sugar_g": 2.5},
    "nimbu": {"energy_kcal": 29.0, "protein_g": 1.1, "carb_g": 9.3, "fat_g": 0.3, "fibre_g": 2.8, "sodium_mg": 2.0, "sugar_g": 2.5}
}


class VerifiedFoodItem:
    def __init__(self, food_code: str, name: str, nutrients_dict: dict):
        self.food_code = food_code
        self.name = name
        self.nutrients = type('Nutrients', (), nutrients_dict)()
        self.nutrients_100g = nutrients_dict

    def __getitem__(self, item):
        if item == "food_code":
            return self.food_code
        elif item == "name":
            return self.name
        elif item in ("nutrients", "nutrients_100g"):
            return self.nutrients_100g
        raise KeyError(item)


def match_food_item(db_session: Session, ingredient_name: str):
    """
    Fuzzy matches raw ingredient string to verified ingredient composition database or foods database table.
    """
    cleaned_name = ingredient_name.lower().strip()
    
    # 1. Database table exact match
    exact = db_session.query(Food).filter(func.lower(Food.name) == cleaned_name).first()
    if exact and exact.nutrients and (exact.nutrients.energy_kcal or 0) > 0:
        return exact

    # 2. Check verified reference database
    if cleaned_name in VERIFIED_INGREDIENTS_NUTRITION:
        return VerifiedFoodItem(f"VERIFIED_{cleaned_name.upper()}", cleaned_name, VERIFIED_INGREDIENTS_NUTRITION[cleaned_name])

    for key, val in VERIFIED_INGREDIENTS_NUTRITION.items():
        if key in cleaned_name or cleaned_name in key:
            return VerifiedFoodItem(f"VERIFIED_{key.upper()}", key, val)

    # 3. Word overlap in database
    stopwords = {'and', 'or', 'with', 'in', 'of', 'for', 'to', 'a', 'an', 'the', 'powder', 'chopped', 'sliced', 'ground'}
    words = [w for w in re.findall(r'[a-z0-9]+', cleaned_name) if w not in stopwords and len(w) > 1]
    
    if words:
        query_filters = [Food.name.ilike(f"%{w}%") for w in words]
        matched_foods = db_session.query(Food).filter(or_(*query_filters)).limit(50).all()
        for f in matched_foods:
            if f.nutrients and (f.nutrients.energy_kcal or 0) > 0:
                return f

    return None



def calculate_ingredient_nutrition(db_session: Session, ingredient_name: str, amount: float, unit: str) -> dict:
    """
    Calculates nutrition for a single ingredient on the fly with verified precision.
    """
    gram_weight = parse_gram_weight(db_session, ingredient_name, unit, amount)
    food_match = match_food_item(db_session, ingredient_name)
    
    nutrients = {
        "energy_kcal": 0.0,
        "protein_g": 0.0,
        "carb_g": 0.0,
        "fat_g": 0.0,
        "fibre_g": 0.0,
        "sodium_mg": 0.0,
        "sugar_g": 0.0
    }
    
    matched_food_code = None
    matched_food_name = None

    if food_match:
        factor = gram_weight / 100.0
        if isinstance(food_match, dict):
            fn = food_match["nutrients_100g"]
            matched_food_code = food_match["food_code"]
            matched_food_name = food_match["name"].capitalize()
            nutrients["energy_kcal"] = round(fn.get("energy_kcal", 0.0) * factor, 2)
            nutrients["protein_g"] = round(fn.get("protein_g", 0.0) * factor, 2)
            nutrients["carb_g"] = round(fn.get("carb_g", 0.0) * factor, 2)
            nutrients["fat_g"] = round(fn.get("fat_g", 0.0) * factor, 2)
            nutrients["fibre_g"] = round(fn.get("fibre_g", 0.0) * factor, 2)
            nutrients["sodium_mg"] = round(fn.get("sodium_mg", 0.0) * factor, 2)
            nutrients["sugar_g"] = round(fn.get("sugar_g", 0.0) * factor, 2)
        elif hasattr(food_match, "nutrients") and food_match.nutrients:
            fn = food_match.nutrients
            matched_food_code = food_match.food_code
            matched_food_name = food_match.name
            nutrients["energy_kcal"] = round((fn.energy_kcal or 0.0) * factor, 2)
            nutrients["protein_g"] = round((fn.protein_g or 0.0) * factor, 2)
            nutrients["carb_g"] = round((fn.carb_g or 0.0) * factor, 2)
            nutrients["fat_g"] = round((fn.fat_g or 0.0) * factor, 2)
            nutrients["fibre_g"] = round((fn.fibre_g or 0.0) * factor, 2)
            nutrients["sodium_mg"] = round((fn.sodium_mg or 0.0) * factor, 2)
            nutrients["sugar_g"] = round((fn.sugar_g or 0.0) * factor, 2)

    # Heuristic fallback if unknown ingredient is added
    if nutrients["energy_kcal"] == 0.0 and gram_weight > 0:
        factor = gram_weight / 100.0
        nutrients["energy_kcal"] = round(120.0 * factor, 2)
        nutrients["protein_g"] = round(4.0 * factor, 2)
        nutrients["carb_g"] = round(18.0 * factor, 2)
        nutrients["fat_g"] = round(2.5 * factor, 2)
        matched_food_name = ingredient_name.capitalize()

    return {
        "ingredient_name": ingredient_name,
        "amount": amount,
        "unit": unit,
        "gram_weight": round(gram_weight, 2),
        "matched_food_code": matched_food_code,
        "matched_food_name": matched_food_name,
        "nutrients": nutrients
    }

def calculate_meal_nutrition(db_session: Session, ingredients: list) -> dict:
    """
    Calculates dynamic nutrition totals by compiling a list of ingredients.
    """
    processed_ingredients = []
    totals = {
        "energy_kcal": 0.0,
        "protein_g": 0.0,
        "carb_g": 0.0,
        "fat_g": 0.0,
        "fibre_g": 0.0,
        "sodium_mg": 0.0,
        "sugar_g": 0.0
    }
    
    for ing in ingredients:
        res = calculate_ingredient_nutrition(db_session, ing.ingredient_name, ing.amount, ing.unit)
        processed_ingredients.append(res)
        for key in totals:
            totals[key] = round(totals[key] + res["nutrients"][key], 2)
            
    return {
        "ingredients": processed_ingredients,
        "totals": totals
    }

def create_homely_meal(db_session: Session, meal_data) -> HomelyMeal:
    """
    Creates and persists a new custom homely meal in the database, updating ingredients and nutrition.
    """
    # 1. Create HomelyMeal record
    meal = HomelyMeal(
        name=meal_data.name,
        creator_id=meal_data.creator_id,
        is_community=meal_data.is_community,
        status="pending" if meal_data.is_community else "approved",
        cuisine=meal_data.cuisine or "Indian",
        region=meal_data.region
    )
    db_session.add(meal)
    db_session.flush() # populated meal.id

    # 2. Process ingredients
    calc_res = calculate_meal_nutrition(db_session, meal_data.ingredients)
    
    for ing_res in calc_res["ingredients"]:
        ing_model = HomelyMealIngredient(
            meal_id=meal.id,
            ingredient_name=ing_res["ingredient_name"],
            amount=ing_res["amount"],
            unit=ing_res["unit"],
            gram_weight=ing_res["gram_weight"],
            food_code=ing_res["matched_food_code"]
        )
        db_session.add(ing_model)

    # 3. Add nutrition totals
    t = calc_res["totals"]
    nut_model = HomelyMealNutrition(
        meal_id=meal.id,
        energy_kcal=t["energy_kcal"],
        protein_g=t["protein_g"],
        carb_g=t["carb_g"],
        fat_g=t["fat_g"],
        fibre_g=t["fibre_g"],
        sodium_mg=t["sodium_mg"],
        sugar_g=t["sugar_g"]
    )
    db_session.add(nut_model)

    # 4. Save tags
    if meal_data.tags:
        for tag in meal_data.tags:
            tag_model = HomelyMealTag(meal_id=meal.id, tag=tag.strip())
            db_session.add(tag_model)

    # 5. Create version 1 record
    version = HomelyMealVersion(
        meal_id=meal.id,
        version_number=1,
        edited_by=meal_data.creator_id,
        change_summary="Initial Creation"
    )
    db_session.add(version)
    
    db_session.commit()
    db_session.refresh(meal)
    return meal

def update_meal_status(db_session: Session, meal_id: int, status: str, reviewer_id: int = None, comment: str = None) -> HomelyMeal:
    """
    Updates status of a community-submitted homely meal.
    """
    meal = db_session.query(HomelyMeal).filter(HomelyMeal.id == meal_id).first()
    if not meal:
        return None
        
    meal.status = status
    
    if comment or status == "approved":
        review = HomelyMealReview(
            meal_id=meal_id,
            reviewer_id=reviewer_id,
            rating=5 if status == "approved" else 1,
            comment=comment or f"System review: meal marked as {status}."
        )
        db_session.add(review)
        
    db_session.commit()
    db_session.refresh(meal)
    return meal

def add_review(db_session: Session, meal_id: int, reviewer_id: int, rating: int, comment: str = None) -> HomelyMealReview:
    """
    Adds a community review and increments popularity score.
    """
    review = HomelyMealReview(
        meal_id=meal_id,
        reviewer_id=reviewer_id,
        rating=rating,
        comment=comment
    )
    db_session.add(review)
    
    meal = db_session.query(HomelyMeal).filter(HomelyMeal.id == meal_id).first()
    if meal:
        meal.popularity += 1
        
    db_session.commit()
    return review
