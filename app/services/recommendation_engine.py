from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload
from app.models import Recipe, RecipeIngredient, RecipeNutrition, UserPreference, User, HomelyMeal

class RecommendationEngine:
    MEAT_KEYWORDS = [
        "chicken", "mutton", "fish", "beef", "pork", "seafood", "prawn", 
        "crab", "meat", "shrimp", "lamb", "duck", "turkey", "bacon", "ham", "salami", "gelatin"
    ]
    
    NON_VEG_KEYWORDS = MEAT_KEYWORDS + ["egg"]
    
    ANIMAL_KEYWORDS = NON_VEG_KEYWORDS + [
        "milk", "cheese", "butter", "curd", "yogurt", "ghee", "cream", "paneer", "honey", "whey", "casein"
    ]

    JAIN_KEYWORDS = NON_VEG_KEYWORDS + [
        "onion", "garlic", "shallot", "scallion", "leek", "potato", "radish", 
        "carrot", "beetroot", "turnip", "ginger", "kanda", "lhsun", "lasun", "pyaz", "pyaaz", "aloo", "alu"
    ]

    @classmethod
    def is_vegan(cls, recipe: Recipe) -> bool:
        """Check if a recipe is vegan by examining its ingredient names."""
        for ing in recipe.ingredients:
            ing_name = (ing.food_name or "").lower()
            if any(kw in ing_name for kw in cls.ANIMAL_KEYWORDS):
                return False
        recipe_name = recipe.recipe_name.lower()
        if any(kw in recipe_name for kw in cls.ANIMAL_KEYWORDS):
            return False
        return True

    @classmethod
    def is_vegetarian(cls, recipe: Recipe) -> bool:
        """Check if a recipe is vegetarian by examining its ingredient names."""
        for ing in recipe.ingredients:
            ing_name = (ing.food_name or "").lower()
            if any(kw in ing_name for kw in cls.NON_VEG_KEYWORDS):
                return False
        recipe_name = recipe.recipe_name.lower()
        if any(kw in recipe_name for kw in cls.NON_VEG_KEYWORDS):
            return False
        return True

    @classmethod
    def is_jain(cls, recipe: Recipe) -> bool:
        """Check if a recipe is Jain compliant (no meat, eggs, onion, garlic, or root vegetables)."""
        for ing in recipe.ingredients:
            ing_name = (ing.food_name or "").lower()
            if any(kw in ing_name for kw in cls.JAIN_KEYWORDS):
                return False
        recipe_name = recipe.recipe_name.lower()
        if any(kw in recipe_name for kw in cls.JAIN_KEYWORDS):
            return False
        return True

    @classmethod
    def is_eggetarian(cls, recipe: Recipe) -> bool:
        """Check if a recipe is eggetarian compliant (allows eggs/dairy, no meat/fish)."""
        for ing in recipe.ingredients:
            ing_name = (ing.food_name or "").lower()
            if any(kw in ing_name for kw in cls.MEAT_KEYWORDS):
                return False
        recipe_name = recipe.recipe_name.lower()
        if any(kw in recipe_name for kw in cls.MEAT_KEYWORDS):
            return False
        return True

    @classmethod
    def is_homely_meal_vegan(cls, meal: HomelyMeal) -> bool:
        """Check if a homely meal is vegan by examining its ingredient names."""
        for ing in meal.ingredients:
            ing_name = (ing.ingredient_name or "").lower()
            if any(kw in ing_name for kw in cls.ANIMAL_KEYWORDS):
                return False
        if any(kw in meal.name.lower() for kw in cls.ANIMAL_KEYWORDS):
            return False
        return True

    @classmethod
    def is_homely_meal_vegetarian(cls, meal: HomelyMeal) -> bool:
        """Check if a homely meal is vegetarian by examining its ingredient names."""
        for ing in meal.ingredients:
            ing_name = (ing.ingredient_name or "").lower()
            if any(kw in ing_name for kw in cls.NON_VEG_KEYWORDS):
                return False
        if any(kw in meal.name.lower() for kw in cls.NON_VEG_KEYWORDS):
            return False
        return True

    @classmethod
    def is_homely_meal_jain(cls, meal: HomelyMeal) -> bool:
        """Check if a homely meal is Jain compliant."""
        for ing in meal.ingredients:
            ing_name = (ing.ingredient_name or "").lower()
            if any(kw in ing_name for kw in cls.JAIN_KEYWORDS):
                return False
        if any(kw in meal.name.lower() for kw in cls.JAIN_KEYWORDS):
            return False
        return True

    @classmethod
    def is_homely_meal_eggetarian(cls, meal: HomelyMeal) -> bool:
        """Check if a homely meal is eggetarian compliant."""
        for ing in meal.ingredients:
            ing_name = (ing.ingredient_name or "").lower()
            if any(kw in ing_name for kw in cls.MEAT_KEYWORDS):
                return False
        if any(kw in meal.name.lower() for kw in cls.MEAT_KEYWORDS):
            return False
        return True

    @classmethod
    def get_dietary_tag(cls, recipe: Recipe) -> str:
        """Determine the canonical dietary tag for a recipe, respecting explicit dataset tags."""
        ps = (recipe.primarysource or "").strip()
        rname = (recipe.recipe_name or "").lower()

        # Explicit dataset tags & dish names
        if ps == "Jain" or "jain" in rname:
            return "Jain"
        if ps == "Vegan" or "vegan" in rname:
            return "Vegan"
        if ps == "Vegetarian":
            return "Vegetarian"
        if ps == "Eggetarian":
            return "Eggetarian"
        if ps == "Non-Vegetarian":
            return "Non-Vegetarian"

        # Dynamic fallback based on ingredient rules
        if cls.is_jain(recipe):
            return "Jain"
        elif cls.is_vegan(recipe):
            return "Vegan"
        elif cls.is_vegetarian(recipe):
            return "Vegetarian"
        elif cls.is_eggetarian(recipe):
            return "Eggetarian"
        else:
            return "Non-Vegetarian"

    @classmethod
    def get_homely_meal_dietary_tag(cls, meal: HomelyMeal) -> str:
        """Determine the strictest canonical dietary tag for a homely meal."""
        if cls.is_homely_meal_jain(meal):
            return "Jain"
        elif cls.is_homely_meal_vegan(meal):
            return "Vegan"
        elif cls.is_homely_meal_vegetarian(meal):
            return "Vegetarian"
        elif cls.is_homely_meal_eggetarian(meal):
            return "Eggetarian"
        else:
            return "Non-Vegetarian"

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
                    if like_lower in ing.ingredient_name.lower():
                        boost += 15.0
                        break

        return round(macro_score + nds + boost, 2)

    @classmethod
    def get_recommendations(cls, db: Session, user_id: int, limit: int = 50) -> list:
        """Fetch and rank recipes & homely meals based on user preferences and nutritional target alignment."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return []

        # Retrieve preferences
        prefs = db.query(UserPreference).filter(UserPreference.user_id == user_id).all()
        
        allergies = []
        dislikes = []
        likes = []
        diet_type = "Non-Vegetarian"

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

        recipes = db.query(Recipe).options(
            joinedload(Recipe.nutrition),
            joinedload(Recipe.ingredients)
        ).all()
        
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
            ranked_recipes.append({
                "recipe_code": recipe.recipe_code,
                "recipe_name": recipe.recipe_name,
                "category": recipe.category,
                "score": score,
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
            ranked_recipes.append({
                "recipe_code": f"HOMELY_{meal.id}",
                "recipe_name": meal.name,
                "category": "Lunch/Dinner",
                "score": score,
                "dietary_tag": cls.get_homely_meal_dietary_tag(meal),
                "energy_kcal": meal.nutrition.energy_kcal if meal.nutrition else 0.0,
                "protein_g": meal.nutrition.protein_g if meal.nutrition else 0.0,
                "carb_g": meal.nutrition.carb_g if meal.nutrition else 0.0,
                "fat_g": meal.nutrition.fat_g if meal.nutrition else 0.0
            })

        ranked_recipes.sort(key=lambda x: x["score"], reverse=True)
        return ranked_recipes[:limit]
