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

def match_food_item(db_session: Session, ingredient_name: str) -> Food:
    """
    Fuzzy matches raw ingredient string to a base food item in the foods database table.
    """
    cleaned_name = ingredient_name.lower().strip()
    
    # 1. Exact match
    exact = db_session.query(Food).filter(func.lower(Food.name) == cleaned_name).first()
    if exact:
        return exact

    # 2. String overlap matching
    stopwords = {'and', 'or', 'with', 'in', 'of', 'for', 'to', 'a', 'an', 'the', 'powder', 'chopped', 'sliced', 'ground'}
    words = [w for w in re.findall(r'[a-z0-9]+', cleaned_name) if w not in stopwords and len(w) > 1]
    
    if not words:
        return None

    # Retrieve potentially matching records
    query_filters = [Food.name.ilike(f"%{w}%") for w in words]
    matched_foods = db_session.query(Food).filter(or_(*query_filters)).limit(100).all()

    if not matched_foods:
        return None

    # Score by overlap
    best_food = None
    best_score = -1.0
    query_set = set(words)

    for food in matched_foods:
        food_words = set(re.findall(r'[a-z0-9]+', food.name.lower()))
        overlap = query_set.intersection(food_words)
        score = len(overlap) / len(query_set)
        if score > best_score:
            best_score = score
            best_food = food
            if score == 1.0:
                break

    return best_food

def calculate_ingredient_nutrition(db_session: Session, ingredient_name: str, amount: float, unit: str) -> dict:
    """
    Calculates nutrition for a single ingredient on the fly.
    """
    gram_weight = parse_gram_weight(db_session, ingredient_name, unit, amount)
    food = match_food_item(db_session, ingredient_name)
    
    nutrients = {
        "energy_kcal": 0.0,
        "protein_g": 0.0,
        "carb_g": 0.0,
        "fat_g": 0.0,
        "fibre_g": 0.0,
        "sodium_mg": 0.0,
        "sugar_g": 0.0
    }
    
    if food and food.nutrients:
        fn = food.nutrients
        # FCT values are per 100g
        factor = gram_weight / 100.0
        nutrients["energy_kcal"] = round((fn.energy_kcal or 0.0) * factor, 2)
        nutrients["protein_g"] = round((fn.protein_g or 0.0) * factor, 2)
        nutrients["carb_g"] = round((fn.carb_g or 0.0) * factor, 2)
        nutrients["fat_g"] = round((fn.fat_g or 0.0) * factor, 2)
        nutrients["fibre_g"] = round((fn.fibre_g or 0.0) * factor, 2)
        nutrients["sodium_mg"] = round((fn.sodium_mg or 0.0) * factor, 2)
        nutrients["sugar_g"] = round((fn.sugar_g or 0.0) * factor, 2)

    return {
        "ingredient_name": ingredient_name,
        "amount": amount,
        "unit": unit,
        "gram_weight": round(gram_weight, 2),
        "matched_food_code": food.food_code if food else None,
        "matched_food_name": food.name if food else None,
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
        status="pending",
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
