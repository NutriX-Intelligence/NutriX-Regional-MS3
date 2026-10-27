import functools
from typing import Optional, List, Dict, Any
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session, joinedload
from app.models import Recipe, RecipeIngredient, RecipeNutrition, UserPreference, User, HomelyMeal
from app.services.classification_engine import ClassificationEngine

class RecommendationEngine:
    _RECIPE_TAG_CACHE: Dict[str, Dict[str, Any]] = {}
    _HOMELY_TAG_CACHE: Dict[int, Dict[str, Any]] = {}

    @classmethod
    def get_recipe_classification(cls, recipe: Recipe) -> Dict[str, Any]:
        """Compute and cache classification for a recipe."""
        code = recipe.recipe_code or str(recipe.id)
        if code in cls._RECIPE_TAG_CACHE:
            return cls._RECIPE_TAG_CACHE[code]

        if getattr(recipe, "dietary_tag", None):
            d_tag = recipe.dietary_tag
            res = {
                "is_vegan": d_tag in ("Vegan", "Jain"),
                "is_vegetarian": d_tag in ("Vegetarian", "Vegan", "Jain"),
                "is_jain": d_tag == "Jain",
                "is_eggetarian": d_tag in ("Eggetarian", "Vegetarian", "Vegan", "Jain"),
                "dietary_tag": d_tag
            }
            if len(cls._RECIPE_TAG_CACHE) < 50000:
                cls._RECIPE_TAG_CACHE[code] = res
            return res

        ps = (recipe.primarysource or "").strip()
        rname = (recipe.recipe_name or "").lower()

        names = [recipe.recipe_name] if recipe.recipe_name else []
        for ing in (recipe.ingredients or []):
            if ing.food_name:
                names.append(ing.food_name)
            if ing.ingredient_name and ing.ingredient_name != ing.food_name:
                names.append(ing.ingredient_name)

        c = ClassificationEngine.classify_ingredients(names)
        d_tag = c["dietary_tag"]
        if ps == "Jain" or "jain" in rname:
            d_tag = "Jain"
        elif ps == "Vegan" or "vegan" in rname:
            d_tag = "Vegan"
        elif ps == "Vegetarian":
            d_tag = "Vegetarian"
        elif ps == "Eggetarian":
            d_tag = "Eggetarian"
        elif ps == "Non-Vegetarian":
            d_tag = "Non-Vegetarian"

        res = {
            "is_vegan": c["is_vegan"] or d_tag == "Vegan",
            "is_vegetarian": c["is_vegetarian"] or d_tag in ("Vegetarian", "Vegan", "Jain"),
            "is_jain": c["is_jain"] or d_tag == "Jain",
            "is_eggetarian": c["is_eggetarian"] or d_tag in ("Eggetarian", "Vegetarian", "Vegan", "Jain"),
            "dietary_tag": d_tag
        }
        if len(cls._RECIPE_TAG_CACHE) < 50000:
            cls._RECIPE_TAG_CACHE[code] = res
        return res

    @classmethod
    def is_vegan(cls, recipe: Recipe) -> bool:
        return cls.get_recipe_classification(recipe)["is_vegan"]

    @classmethod
    def is_vegetarian(cls, recipe: Recipe) -> bool:
        return cls.get_recipe_classification(recipe)["is_vegetarian"]

    @classmethod
    def is_jain(cls, recipe: Recipe) -> bool:
        return cls.get_recipe_classification(recipe)["is_jain"]

    @classmethod
    def is_eggetarian(cls, recipe: Recipe) -> bool:
        return cls.get_recipe_classification(recipe)["is_eggetarian"]

    @classmethod
    def get_dietary_tag(cls, recipe: Recipe) -> str:
        return cls.get_recipe_classification(recipe)["dietary_tag"]

    @classmethod
    def get_homely_classification(cls, meal: HomelyMeal) -> Dict[str, Any]:
        """Compute and cache classification for a homely meal."""
        meal_id = meal.id or hash(meal.name)
        if meal_id in cls._HOMELY_TAG_CACHE:
            return cls._HOMELY_TAG_CACHE[meal_id]

        names = [meal.name] if meal.name else []
        for ing in (meal.ingredients or []):
            if ing.ingredient_name:
                names.append(ing.ingredient_name)

        c = ClassificationEngine.classify_ingredients(names)
        res = {
            "is_vegan": c["is_vegan"],
            "is_vegetarian": c["is_vegetarian"],
            "is_jain": c["is_jain"],
            "is_eggetarian": c["is_eggetarian"],
            "dietary_tag": c["dietary_tag"]
        }
        if len(cls._HOMELY_TAG_CACHE) < 20000:
            cls._HOMELY_TAG_CACHE[meal_id] = res
        return res

    @classmethod
    def is_homely_meal_vegan(cls, meal: HomelyMeal) -> bool:
        return cls.get_homely_classification(meal)["is_vegan"]

    @classmethod
    def is_homely_meal_vegetarian(cls, meal: HomelyMeal) -> bool:
        return cls.get_homely_classification(meal)["is_vegetarian"]

    @classmethod
    def is_homely_meal_jain(cls, meal: HomelyMeal) -> bool:
        return cls.get_homely_classification(meal)["is_jain"]

    @classmethod
    def is_homely_meal_eggetarian(cls, meal: HomelyMeal) -> bool:
        return cls.get_homely_classification(meal)["is_eggetarian"]

    @classmethod
    def get_homely_meal_dietary_tag(cls, meal: HomelyMeal) -> str:
        return cls.get_homely_classification(meal)["dietary_tag"]

    @classmethod
    def get_recipe_macros_pct(cls, nutrition: RecipeNutrition) -> tuple:
        """Calculate the macronutrient percentage split of a recipe's calories."""
        energy = nutrition.energy_kcal or 0.0
        if energy <= 0:
            return 0.0, 0.0, 0.0
        
        p_cal = (nutrition.protein_g or 0.0) * 4.0
        c_cal = (nutrition.carb_g or 0.0) * 4.0
        f_cal = (nutrition.fat_g or 0.0) * 9.0
        
        total_cal = p_cal + c_cal + f_cal
        if total_cal <= 0:
            return 0.0, 0.0, 0.0
            
        return p_cal / total_cal, c_cal / total_cal, f_cal / total_cal

    @classmethod
    def calculate_score(cls, recipe: Recipe, user: User, likes: list) -> float:
        """Calculate recommendation score for a recipe based on user targets and preferences."""
        nutrition = recipe.nutrition
        if not nutrition or not nutrition.energy_kcal or nutrition.energy_kcal <= 0:
            return 0.0

        # 1. Macro Match Score
        target_calories = user.target_calories or 2000.0
        t_p_pct = ((user.target_protein or 150.0) * 4.0) / target_calories
        t_c_pct = ((user.target_carbs or 200.0) * 4.0) / target_calories
        t_f_pct = ((user.target_fat or 67.0) * 9.0) / target_calories
        
        r_p_pct, r_c_pct, r_f_pct = cls.get_recipe_macros_pct(nutrition)
        
        diff = abs(r_p_pct - t_p_pct) + abs(r_c_pct - t_c_pct) + abs(r_f_pct - t_f_pct)
        macro_score = 100.0 * (1.0 - (diff / 2.0))

        # 2. Nutrient Density Score (NDS)
        kcal_100 = nutrition.energy_kcal / 100.0
        
        prot_density = (getattr(nutrition, "protein_g", 0.0) or 0.0) / kcal_100
        fib_density = (getattr(nutrition, "fibre_g", 0.0) or 0.0) / kcal_100
        sod_density = (getattr(nutrition, "sodium_mg", 0.0) or 0.0) / kcal_100
        sug_density = (getattr(nutrition, "freesugar_g", None) or getattr(nutrition, "sugar_g", 0.0) or 0.0) / kcal_100

        nds = (min(prot_density * 2.0, 20.0) + 
               min(fib_density * 4.0, 20.0) - 
               min(sod_density * 0.02, 15.0) - 
               min(sug_density * 1.0, 10.0))

        # 3. Preference Boost (Likes)
        boost = 0.0
        recipe_name_lower = recipe.recipe_name.lower()
        for like in likes:
            like_lower = like.lower()
            if like_lower in recipe_name_lower:
                boost += 25.0
            else:
                for ing in recipe.ingredients:
                    ing_name = (ing.food_name or "").lower()
                    if like_lower in ing_name:
                        boost += 15.0
                        break

        return round(macro_score + nds + boost, 2)

    @classmethod
    def calculate_homely_score(cls, meal: HomelyMeal, user: User, likes: list) -> float:
        """Calculate recommendation score for a homely meal based on user targets and preferences."""
        nutrition = meal.nutrition
        if not nutrition or not nutrition.energy_kcal or nutrition.energy_kcal <= 0:
            return 0.0

        target_calories = user.target_calories or 2000.0
        t_p_pct = ((user.target_protein or 150.0) * 4.0) / target_calories
        t_c_pct = ((user.target_carbs or 200.0) * 4.0) / target_calories
        t_f_pct = ((user.target_fat or 67.0) * 9.0) / target_calories
        
        p_cal = (nutrition.protein_g or 0.0) * 4.0
        c_cal = (nutrition.carb_g or 0.0) * 4.0
        f_cal = (nutrition.fat_g or 0.0) * 9.0
        total_cal = p_cal + c_cal + f_cal
        if total_cal <= 0:
            r_p_pct, r_c_pct, r_f_pct = 0.0, 0.0, 0.0
        else:
            r_p_pct, r_c_pct, r_f_pct = p_cal / total_cal, c_cal / total_cal, f_cal / total_cal
        
        diff = abs(r_p_pct - t_p_pct) + abs(r_c_pct - t_c_pct) + abs(r_f_pct - t_f_pct)
        macro_score = 100.0 * (1.0 - (diff / 2.0))

        kcal_100 = nutrition.energy_kcal / 100.0
        prot_density = (nutrition.protein_g or 0.0) / kcal_100
        fib_density = (nutrition.fibre_g or 0.0) / kcal_100
        sod_density = (nutrition.sodium_mg or 0.0) / kcal_100
        sug_density = (nutrition.sugar_g or 0.0) / kcal_100

        nds = (min(prot_density * 2.0, 20.0) + 
               min(fib_density * 4.0, 20.0) - 
               min(sod_density * 0.02, 15.0) - 
               min(sug_density * 1.0, 10.0))

        boost = 0.0
        meal_name_lower = meal.name.lower()
        for like in likes:
            like_lower = like.lower()
            if like_lower in meal_name_lower:
                boost += 25.0
            else:
                for ing in meal.ingredients:
                    if like_lower in (ing.ingredient_name or "").lower():
                        boost += 15.0
                        break

        return round(macro_score + nds + boost, 2)

    @classmethod
    @functools.lru_cache(maxsize=16384)
    def infer_cuisine(cls, recipe_name: str, explicit_cuisine: Optional[str] = None) -> str:
        """Infer cuisine category from dish name and ingredients."""
        if explicit_cuisine and len(explicit_cuisine.strip()) > 1 and explicit_cuisine.strip() != "Generic":
            return explicit_cuisine.strip()
        
        name = (recipe_name or "").lower()
        if any(w in name for w in ["dosa", "idli", "sambar", "uttapam", "vada", "upma", "rasam", "curry leaf", "payasam", "appam", "pongal", "chettinad"]):
            return "South Indian"
        if any(w in name for w in ["dhokla", "thepla", "khandvi", "undhiyu", "handvo", "fafda", "dal dhokli"]):
            return "Gujarati"
        if any(w in name for w in ["poha", "misal", "pav", "vada pav", "sabudana", "puran poli", "kanda poha"]):
            return "Maharashtrian"
        if any(w in name for w in ["chole", "bhature", "kulcha", "paneer butter", "dal makhani", "sarson", "makki", "rajma"]):
            return "Punjabi"
        if any(w in name for w in ["dal baati", "gatte", "ker sangri", "laal maas"]):
            return "Rajasthani"
        if any(w in name for w in ["machher", "shorshe", "sandesh", "rosogolla", "bengali"]):
            return "Bengali"
        if any(w in name for w in ["pasta", "spaghetti", "pizza", "sandwich", "salad", "soup", "oats", "pancake", "burger", "wrap", "quiche"]):
            return "Continental / Global"
        if any(w in name for w in ["noodle", "noodles", "manchurian", "fried rice", "schezwan", "chow mein", "dim sum", "ramen"]):
            return "Chinese / Pan-Asian"
        if any(w in name for w in ["hummus", "falafel", "pita", "greek", "mediterranean"]):
            return "Mediterranean"
        if any(w in name for w in ["paneer", "tikka", "korma", "biryani", "roti", "paratha", "naan", "jeera", "palak", "aloo", "kofta", "khichdi", "dal"]):
            return "North Indian"
        return "Indian"

    @classmethod
    def recommend_foods(
        cls, 
        db: Session, 
        user_id: int, 
        limit: int = 60,
        query_str: Optional[str] = None,
        category: Optional[str] = None,
        cuisine: Optional[str] = None,
        max_cooking_time: Optional[int] = None,
        brand: Optional[str] = None,
        diet_filter: Optional[str] = None,
        offset: int = 0
    ) -> list:
        return cls.get_recommendations(db, user_id, limit, query_str, category, cuisine, max_cooking_time, brand, diet_filter, offset)

    @classmethod
    def get_recommendations(
        cls, 
        db: Session, 
        user_id: int, 
        limit: int = 60,
        query_str: Optional[str] = None,
        category: Optional[str] = None,
        cuisine: Optional[str] = None,
        max_cooking_time: Optional[int] = None,
        brand: Optional[str] = None,
        diet_filter: Optional[str] = None,
        offset: int = 0
    ) -> list:
        # Load user and profile
        user = db.query(User).options(joinedload(User.profile), joinedload(User.preferences)).filter(User.id == user_id).first()
        if not user or not user.profile:
            return []

        # Extract Preferences
        prefs = user.preferences or []
        allergies = []
        dislikes = []
        likes = []
        diet_type = user.profile.diet_type or "Non-Vegetarian"
        
        for p in prefs:
            t = p.preference_type.lower()
            val = p.value.strip()
            if t == "allergy":
                allergies.append(val)
            elif t == "dislike":
                dislikes.append(val)
            elif t == "like":
                likes.append(val)
            elif t == "diet_type":
                diet_type = val

        # Allow explicit user override filter from the UI
        if diet_filter and diet_filter.lower() not in ("all", "any"):
            diet_type = diet_filter

        diet_lower = diet_type.lower()

        base_query = db.query(Recipe).options(
            joinedload(Recipe.nutrition),
            joinedload(Recipe.ingredients),
            joinedload(Recipe.servings)
        )

        # Apply strict dietary filter at SQL level
        if "jain" in diet_lower:
            base_query = base_query.filter(Recipe.dietary_tag == "Jain")
        elif "vegan" in diet_lower:
            base_query = base_query.filter(or_(Recipe.dietary_tag == "Vegan", Recipe.dietary_tag == "Jain"))
        elif "vegetarian" in diet_lower and "non" not in diet_lower:
            base_query = base_query.filter(Recipe.dietary_tag.in_(["Vegetarian", "Vegan", "Jain"]))

        brand_aliases = {
            "domino": "Domino's",
            "dominos": "Domino's",
            "domino's": "Domino's",
            "mcdonald": "McDonald's",
            "mcdonalds": "McDonald's",
            "mcdonald's": "McDonald's",
            "mcd": "McDonald's",
            "burger king": "Burger King",
            "burgerking": "Burger King",
            "bk": "Burger King",
            "subway": "Subway",
            "kfc": "KFC",
            "kentucky": "KFC",
            "pizza hut": "Pizza Hut",
            "pizzahut": "Pizza Hut",
            "starbucks": "Starbucks",
            "sbux": "Starbucks",
            "taco bell": "Taco Bell",
            "tacobell": "Taco Bell"
        }

        search_clean = (query_str or "").strip()
        has_search = bool(search_clean)
        has_brand_filter = bool(brand and brand.lower() != "all")
        has_category_filter = bool(category and category.lower() != "all")
        has_cuisine_filter = bool(cuisine and cuisine.lower() != "all")
        has_time_filter = bool(max_cooking_time and max_cooking_time > 0)

        recipes = []
        if has_search or has_brand_filter or has_category_filter or has_cuisine_filter or has_time_filter:
            filtered_query = base_query
            if has_search:
                s_lower = search_clean.lower()
                s_no_punct = s_lower.replace("'", "").replace("-", " ")
                canon_from_s = brand_aliases.get(s_lower) or brand_aliases.get(s_no_punct)

                if canon_from_s:
                    filtered_query = filtered_query.filter(
                        or_(
                            Recipe.brand == canon_from_s,
                            Recipe.brand.ilike(f"%{canon_from_s}%"),
                            Recipe.recipe_name.ilike(f"%{search_clean}%")
                        )
                    )
                else:
                    words = search_clean.split()
                    word_clauses = [
                        or_(
                            Recipe.recipe_name.ilike(f"%{w}%"),
                            Recipe.brand.ilike(f"%{w}%"),
                            Recipe.cuisine.ilike(f"%{w}%")
                        )
                        for w in words
                    ]
                    filtered_query = filtered_query.filter(
                        or_(
                            Recipe.recipe_name.ilike(f"%{search_clean}%"),
                            Recipe.brand.ilike(f"%{search_clean}%"),
                            Recipe.cuisine.ilike(f"%{search_clean}%"),
                            and_(*word_clauses),
                            Recipe.ingredients.any(RecipeIngredient.ingredient_name.ilike(f"%{search_clean}%")),
                            Recipe.ingredients.any(RecipeIngredient.food_name.ilike(f"%{search_clean}%"))
                        )
                    )

            if has_brand_filter:
                canon_brand = brand_aliases.get(brand.strip().lower(), brand)
                filtered_query = filtered_query.filter(
                    or_(
                        Recipe.brand.ilike(f"%{canon_brand}%"),
                        Recipe.cuisine.ilike(f"%{canon_brand}%")
                    )
                )

            if has_category_filter:
                if category.lower() in ("lunch/dinner", "lunch", "dinner"):
                    filtered_query = filtered_query.filter(Recipe.category == "Lunch/Dinner")
                else:
                    filtered_query = filtered_query.filter(Recipe.category.ilike(f"%{category}%"))

            if has_cuisine_filter:
                filtered_query = filtered_query.filter(
                    or_(
                        Recipe.cuisine.ilike(f"%{cuisine}%"),
                        Recipe.brand.ilike(f"%{cuisine}%")
                    )
                )

            if has_time_filter:
                filtered_query = filtered_query.filter(Recipe.cooking_time_minutes <= max_cooking_time)

            fetch_limit = max(500, limit * 3)
            recipes = filtered_query.limit(fetch_limit).all()
        else:
            # Default browse view: Load a diverse, representative sample including fast food and regional classes
            ff_recipes = base_query.filter(Recipe.recipe_code.like("FF_%")).limit(400).all()
            reg_recipes = base_query.filter(Recipe.recipe_code.like("REG_%")).all()
            lunch_recipes = base_query.filter(Recipe.category == "Lunch/Dinner").limit(350).all()
            bf_recipes = base_query.filter(Recipe.category == "Breakfast").limit(200).all()
            snack_recipes = base_query.filter(Recipe.category.in_(["Snack", "Beverage"])).limit(200).all()
            
            combined_map = {r.recipe_code: r for r in (ff_recipes + reg_recipes + lunch_recipes + bf_recipes + snack_recipes)}
            recipes = list(combined_map.values())
        
        # Homely meals query (unless brand is specified)
        homely_meals = []
        if not has_brand_filter:
            homely_query = db.query(HomelyMeal).options(
                joinedload(HomelyMeal.nutrition),
                joinedload(HomelyMeal.ingredients)
            ).filter(
                or_(
                    HomelyMeal.status == "approved",
                    HomelyMeal.creator_id == user_id
                )
            )
            all_homely = homely_query.all()
            if has_search:
                s_low = search_clean.lower()
                words_low = search_clean.lower().split()
                homely_meals = [
                    m for m in all_homely
                    if s_low in (m.name or "").lower()
                    or all(w in (m.name or "").lower() for w in words_low)
                    or any(s_low in (i.ingredient_name or "").lower() for i in (m.ingredients or []))
                ]
            else:
                homely_meals = all_homely
        
        ranked_recipes = []
        
        # 1. Evaluate recipes
        for recipe in recipes:
            recipe_name_lower = recipe.recipe_name.lower()
            
            # Check Diet Type constraint
            if "jain" in diet_lower and not cls.is_jain(recipe):
                continue
            elif "vegan" in diet_lower and not cls.is_vegan(recipe):
                continue
            elif "eggetarian" in diet_lower and not cls.is_eggetarian(recipe):
                continue
            elif "vegetarian" in diet_lower and "non" not in diet_lower and not cls.is_vegetarian(recipe):
                continue

            # Check Allergy/Dislike filters
            excluded = False
            for term in (allergies + dislikes):
                term_lower = term.lower()
                if term_lower in recipe_name_lower:
                    excluded = True
                    break
                for ing in (recipe.ingredients or []):
                    ing_name = (ing.food_name or "").lower()
                    ing_org_name = (ing.ingredient_name or "").lower()
                    if term_lower in ing_name or term_lower in ing_org_name:
                        excluded = True
                        break
                if excluded:
                    break
            
            if excluded:
                continue

            score = cls.calculate_score(recipe, user, likes)
            # Relevance boost for exact brand or dish match
            if has_search:
                s_lower = search_clean.lower()
                if recipe.brand and s_lower in recipe.brand.lower():
                    score += 60.0
                elif s_lower in recipe_name_lower:
                    score += 50.0

            cuisine_name = recipe.brand or cls.infer_cuisine(recipe.recipe_name, recipe.cuisine)
            health_sc = 80.0
            if hasattr(recipe, "health_score") and recipe.health_score:
                health_sc = float(recipe.health_score)

            portion_desc = None
            if recipe.servings and recipe.servings.servings_unit:
                portion_desc = str(recipe.servings.servings_unit)
            elif recipe.servings and recipe.servings.size_of_servings:
                portion_desc = f"{int(recipe.servings.size_of_servings)}g"

            ranked_recipes.append({
                "recipe_code": recipe.recipe_code,
                "recipe_name": recipe.recipe_name,
                "category": recipe.category,
                "cuisine": cuisine_name,
                "brand": recipe.brand,
                "portion_str": portion_desc or "1 serving",
                "cooking_time_minutes": recipe.cooking_time_minutes or 10,
                "score": score,
                "health_score": health_sc,
                "dietary_tag": cls.get_dietary_tag(recipe),
                "energy_kcal": round(recipe.nutrition.energy_kcal, 1) if recipe.nutrition else 0.0,
                "protein_g": round(recipe.nutrition.protein_g, 1) if recipe.nutrition else 0.0,
                "carb_g": round(recipe.nutrition.carb_g, 1) if recipe.nutrition else 0.0,
                "fat_g": round(recipe.nutrition.fat_g, 1) if recipe.nutrition else 0.0,
                "sodium_mg": round(recipe.nutrition.sodium_mg, 1) if (recipe.nutrition and recipe.nutrition.sodium_mg) else 0.0,
                "sugar_g": round(recipe.nutrition.freesugar_g, 1) if (recipe.nutrition and recipe.nutrition.freesugar_g) else 0.0,
                "fibre_g": round(recipe.nutrition.fibre_g, 1) if (recipe.nutrition and recipe.nutrition.fibre_g) else 0.0,
            })

        # 2. Evaluate homely meals
        for meal in homely_meals:
            meal_name_lower = meal.name.lower()
            
            # Check Diet Type constraint
            if "jain" in diet_lower and not cls.is_homely_meal_jain(meal):
                continue
            elif "vegan" in diet_lower and not cls.is_homely_meal_vegan(meal):
                continue
            elif "eggetarian" in diet_lower and not cls.is_homely_meal_eggetarian(meal):
                continue
            elif "vegetarian" in diet_lower and "non" not in diet_lower and not cls.is_homely_meal_vegetarian(meal):
                continue

            # Check Allergy/Dislike filters
            excluded = False
            for term in (allergies + dislikes):
                term_lower = term.lower()
                if term_lower in meal_name_lower:
                    excluded = True
                    break
                for ing in (meal.ingredients or []):
                    if term_lower in (ing.ingredient_name or "").lower():
                        excluded = True
                        break
                if excluded:
                    break
            
            if excluded:
                continue

            score = cls.calculate_homely_score(meal, user, likes)
            if has_search and (search_clean.lower() in meal_name_lower):
                score += 50.0

            cuisine = cls.infer_cuisine(meal.name, "Homely Indian")
            ranked_recipes.append({
                "recipe_code": f"HOMELY_{meal.id}",
                "recipe_name": meal.name,
                "category": "Lunch/Dinner",
                "cuisine": cuisine,
                "brand": "Homely Meal",
                "portion_str": "1 plate",
                "cooking_time_minutes": 25,
                "score": score,
                "health_score": 85.0,
                "dietary_tag": cls.get_homely_meal_dietary_tag(meal),
                "energy_kcal": round(meal.nutrition.energy_kcal, 1) if meal.nutrition else 0.0,
                "protein_g": round(meal.nutrition.protein_g, 1) if meal.nutrition else 0.0,
                "carb_g": round(meal.nutrition.carb_g, 1) if meal.nutrition else 0.0,
                "fat_g": round(meal.nutrition.fat_g, 1) if meal.nutrition else 0.0,
                "sodium_mg": round(meal.nutrition.sodium_mg, 1) if (meal.nutrition and meal.nutrition.sodium_mg) else 0.0,
                "sugar_g": round(meal.nutrition.sugar_g, 1) if (meal.nutrition and meal.nutrition.sugar_g) else 0.0,
                "fibre_g": round(meal.nutrition.fibre_g, 1) if (meal.nutrition and meal.nutrition.fibre_g) else 0.0,
            })

        ranked_recipes.sort(key=lambda x: x["score"], reverse=True)
        start_idx = offset or 0
        return ranked_recipes[start_idx:start_idx + limit]

