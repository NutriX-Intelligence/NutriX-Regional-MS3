import functools
from typing import Optional, List, Dict, Any
from sqlalchemy import or_
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
        
        prot_density = (nutrition.protein_g or 0.0) / kcal_100
        fib_density = (nutrition.fibre_g or 0.0) / kcal_100
        sod_density = (nutrition.sodium_mg or 0.0) / kcal_100
        sug_density = (nutrition.freesugar_g or 0.0) / kcal_100

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
    def recommend_foods(cls, db: Session, user_id: int, limit: int = 50) -> list:
        # Alias for get_recommendations
        return cls.get_recommendations(db, user_id, limit)

    @classmethod
    def get_recommendations(cls, db: Session, user_id: int, limit: int = 50) -> list:
        # Load user and profile
        user = db.query(User).options(joinedload(User.profile), joinedload(User.preferences)).filter(User.id == user_id).first()
        if not user or not user.profile:
            return []

        # Extract Preferences
        prefs = user.preferences
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

        diet_lower = diet_type.lower()

        query = db.query(Recipe).options(
            joinedload(Recipe.nutrition),
            joinedload(Recipe.ingredients)
        )
        if "jain" in diet_lower or "vegan" in diet_lower or ("vegetarian" in diet_lower and "non" not in diet_lower):
            query = query.filter(or_(Recipe.primarysource != "Non-Vegetarian", Recipe.primarysource.is_(None)))

        recipes = query.limit(500).all()
        
        homely_meals = db.query(HomelyMeal).options(
            joinedload(HomelyMeal.nutrition),
            joinedload(HomelyMeal.ingredients)
        ).filter(
            or_(
                HomelyMeal.status == "approved",
                HomelyMeal.creator_id == user_id
            )
        ).all()
        
        ranked_recipes = []
        diet_lower = diet_type.lower()
        
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
                for ing in recipe.ingredients:
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
            cuisine = cls.infer_cuisine(recipe.recipe_name, recipe.cuisine)
            health_sc = 80.0
            if hasattr(recipe, "health_score") and recipe.health_score:
                health_sc = float(recipe.health_score)

            ranked_recipes.append({
                "recipe_code": recipe.recipe_code,
                "recipe_name": recipe.recipe_name,
                "category": recipe.category,
                "cuisine": cuisine,
                "score": score,
                "health_score": health_sc,
                "dietary_tag": cls.get_dietary_tag(recipe),
                "energy_kcal": recipe.nutrition.energy_kcal if recipe.nutrition else 0.0,
                "protein_g": recipe.nutrition.protein_g if recipe.nutrition else 0.0,
                "carb_g": recipe.nutrition.carb_g if recipe.nutrition else 0.0,
                "fat_g": recipe.nutrition.fat_g if recipe.nutrition else 0.0
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
                for ing in meal.ingredients:
                    if term_lower in ing.ingredient_name.lower():
                        excluded = True
                        break
                if excluded:
                    break
            
            if excluded:
                continue

            score = cls.calculate_homely_score(meal, user, likes)
            cuisine = cls.infer_cuisine(meal.name, "Homely Indian")
            ranked_recipes.append({
                "recipe_code": f"HOMELY_{meal.id}",
                "recipe_name": meal.name,
                "category": "Lunch/Dinner",
                "cuisine": cuisine,
                "score": score,
                "health_score": 85.0,
                "dietary_tag": cls.get_homely_meal_dietary_tag(meal),
                "energy_kcal": meal.nutrition.energy_kcal if meal.nutrition else 0.0,
                "protein_g": meal.nutrition.protein_g if meal.nutrition else 0.0,
                "carb_g": meal.nutrition.carb_g if meal.nutrition else 0.0,
                "fat_g": meal.nutrition.fat_g if meal.nutrition else 0.0
            })

        ranked_recipes.sort(key=lambda x: x["score"], reverse=True)
        return ranked_recipes[:limit]
