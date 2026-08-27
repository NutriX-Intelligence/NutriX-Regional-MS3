from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from ortools.linear_solver import pywraplp

from app.models import Recipe, User, HomelyMeal
from app.services.recommendation_engine import RecommendationEngine

def categorize_meal(name):
    name_lower = name.lower()
    breakfast_kws = [
        "sandwich", "toast", "pancake", "egg", "omelet", "paratha", "poha", "upma", 
        "idli", "dosa", "oats", "porridge", "muesli", "cereal", "dalia", "flakes",
        "bhurji", "thepla", "cheela", "chilla", "puri", "poori", "chapati", "parotta",
        "appe", "dhokla", "khandvi", "uttapam"
    ]
    if any(kw in name_lower for kw in breakfast_kws):
        if any(kw in name_lower for kw in ["curry", "gravy", "korma"]):
            return "Lunch/Dinner"
        return "Breakfast"
        
    snack_kws = [
        "tea", "coffee", "juice", "shake", "drink", "lassi", "smoothie", "sharbat", 
        "beverage", "soda", "punch", "lemonade", "biscuit", "cookie", "cake", "muffin", 
        "souffle", "pudding", "kheer", "halwa", "laddu", "sweet", "burfi", "chutney", 
        "pickle", "sauce", "dip", "raita", "chips", "popcorn", "samosa", "pakora", 
        "fritter", "chaat", "bhel", "kachori", "salad", "soup", "roll", "cutlet", 
        "snack", "papad", "fry", "bhajia", "vada", "bonda", "kozhukattai", "murukku", 
        "mathri", "namkeen", "shakarpara", "chikki", "pedha", "rasgulla", "gulab jamun",
        "jalebi", "ice cream", "custard", "compote", "sherbet", "jam", "jelly",
        "cooler", "cocoa", "stock", "water", "infusion", "puff"
    ]
    if any(kw in name_lower for kw in snack_kws):
        return "Snack"
        
    return "Lunch/Dinner"

class HomelyMealRecipeWrapper:
    def __init__(self, meal):
        self._homely_meal = meal
        self.recipe_code = f"HOMELY_{meal.id}"
        self.recipe_name = meal.name
        self.category = categorize_meal(meal.name)
        
        class ServingsMock:
            size_of_servings = 1.0
            servings_unit = "serving"
        self.servings = ServingsMock()
        
        class NutritionMock:
            def __init__(self, n):
                self.unit_serving_energy_kcal = n.energy_kcal if n else 0.0
                self.unit_serving_protein_g = n.protein_g if n else 0.0
                self.unit_serving_carb_g = n.carb_g if n else 0.0
                self.unit_serving_fat_g = n.fat_g if n else 0.0
                self.unit_serving_fibre_g = n.fibre_g if n else 0.0
                self.energy_kcal = n.energy_kcal if n else 0.0
                self.protein_g = n.protein_g if n else 0.0
                self.carb_g = n.carb_g if n else 0.0
                self.fat_g = n.fat_g if n else 0.0
                self.fibre_g = n.fibre_g if n else 0.0
                self.sodium_mg = getattr(n, "sodium_mg", 0.0) if n else 0.0
                self.sugar_g = getattr(n, "sugar_g", 0.0) if n else 0.0
                self.freesugar_g = getattr(n, "sugar_g", 0.0) if n else 0.0
        self.nutrition = NutritionMock(meal.nutrition)

class OptimizationEngine:
    CUISINE_ALIASES = {
        "bengali": ["bengal", "bengali", "machher", "kosha", "shorshe", "mishti", "sandesh", "pitha", "luchi", "cholar"],
        "rajasthani": ["rajasthan", "rajasthani", "baati", "gatte", "laal maas", "sangri", "kachori", "ghevar"],
        "gujarati": ["gujarat", "gujarati", "dhokla", "thepla", "khichdi", "khandvi", "undhiyu", "handvo", "farsan", "dal dhokli"],
        "maharashtrian": ["maharashtra", "maharashtrian", "marathi", "misal", "poha", "modak", "puran poli", "vada pav", "pitla", "sabudana"],
        "punjabi": ["punjab", "punjabi", "paneer butter", "tandoori", "chole", "bhature", "sarson", "makki", "dal makhani", "amritsari", "rajma"],
        "south indian": ["south indian", "dosa", "idli", "sambar", "rasam", "uttapam", "hyderabadi", "kerala", "chettinad", "bisi bele", "appam", "vada", "payasam", "andhra"],
        "north indian": ["north indian", "paneer", "dal makhani", "korma", "naan", "tikka", "kofta", "biryani", "paratha", "roti", "aloo"],
        "mughlai": ["mughlai", "biryani", "korma", "pasanda", "shahi", "nargisi", "nihari"],
        "kashmiri": ["kashmiri", "rogan josh", "dum aloo", "yakhni", "kahwa"],
        "chinese": ["chinese", "indo-chinese", "hakka", "manchurian", "chow mein", "schezwan", "noodle", "fried rice", "dim sum", "congee", "bao", "sichuan"],
        "indo-chinese": ["chinese", "indo-chinese", "hakka", "manchurian", "chow mein", "schezwan", "noodle", "fried rice"],
        "italian": ["italian", "pasta", "pizza", "risotto", "spaghetti", "bruschetta", "cornetto", "frittata", "arancini", "pesto", "lasagna"],
        "japanese": ["japanese", "sushi", "ramen", "teriyaki", "tempura", "miso", "udon", "donburi", "matcha", "bento", "soba"],
        "mexican": ["mexican", "taco", "burrito", "quesadilla", "enchilada", "fajita", "guacamole", "salsa", "nacho", "chili"],
        "continental": ["continental", "steak", "roast", "soup", "salad", "bake", "grill", "stew", "sandwich", "toast", "pancake", "oats"],
        "asian": ["asian", "thai", "japanese", "korean", "vietnamese", "chinese"],
    }

    @classmethod
    def _fetch_slot_candidates(
        cls,
        db: Session,
        slot_name: str,
        user: User,
        likes: list,
        allergies: list,
        dislikes: list,
        cuisine_req: Optional[str] = None,
        limit_candidates: int = 60
    ) -> List[Tuple[Any, float]]:
        """Fetch and score candidate recipes directly from database for a specific meal slot."""
        from sqlalchemy import or_, and_
        from sqlalchemy.orm import joinedload

        db_category = "Lunch/Dinner" if slot_name in ("Lunch", "Dinner") else slot_name

        query = db.query(Recipe).options(
            joinedload(Recipe.nutrition),
            joinedload(Recipe.servings),
            joinedload(Recipe.ingredients)
        ).filter(Recipe.category == db_category)

        # Dietary preference pre-filter
        diet_type = ""
        if getattr(user, "diet_type", None):
            diet_type = user.diet_type
        if not diet_type:
            for p in (getattr(user, "preferences", []) or []):
                if (getattr(p, "preference_type", "") or "").lower().strip() == "diet_type":
                    diet_type = p.value
                    break
        if not diet_type and getattr(user, "profile", None) and getattr(user.profile, "diet_type", None):
            diet_type = user.profile.diet_type
        if not diet_type:
            diet_type = "Vegetarian"
        diet_type = diet_type.lower().strip()

        # Database-level strict pre-filtering
        if "jain" in diet_type or "vegan" in diet_type or ("vegetarian" in diet_type and "non" not in diet_type and "egg" not in diet_type):
            query = query.filter(or_(Recipe.primarysource != "Non-Vegetarian", Recipe.primarysource.is_(None)))
        elif "eggetarian" in diet_type:
            query = query.filter(or_(Recipe.primarysource != "Non-Vegetarian", Recipe.primarysource == "Eggetarian", Recipe.primarysource.is_(None)))

        import random

        # Cuisine filter
        matched_recipes = []
        if cuisine_req and str(cuisine_req).lower().strip() not in ("any", "all", "", "none"):
            c_lower = str(cuisine_req).lower().strip()
            kws = cls.CUISINE_ALIASES.get(c_lower, [c_lower])
            c_conds = [Recipe.cuisine.ilike(f"%{kw}%") | Recipe.recipe_name.ilike(f"%{kw}%") for kw in kws]
            matched_recipes = query.filter(or_(*c_conds)).limit(350).all()

        # If not enough cuisine matches or no cuisine requested, fetch general high-quality pool
        if len(matched_recipes) < 30:
            general_pool = query.limit(350).all()
            # Combine avoiding duplicates
            seen_codes = {r.recipe_code for r in matched_recipes}
            for r in general_pool:
                if r.recipe_code not in seen_codes:
                    matched_recipes.append(r)

        # Include Homely meals if applicable
        if slot_name in ("Lunch", "Dinner", "Snack"):
            homely_query = db.query(HomelyMeal).options(
                joinedload(HomelyMeal.nutrition),
                joinedload(HomelyMeal.ingredients)
            ).filter(
                or_(
                    HomelyMeal.status == "approved",
                    HomelyMeal.creator_id == user.id
                )
            )
            for hm in homely_query.limit(40).all():
                matched_recipes.append(HomelyMealRecipeWrapper(hm))

        # Filter & score candidates
        scored_candidates = []
        for r in matched_recipes:
            if not r.nutrition:
                continue
            u_energy = getattr(r.nutrition, "unit_serving_energy_kcal", None) or getattr(r.nutrition, "energy_kcal", 0.0)
            if not u_energy or u_energy < 15.0:
                continue

            # Check strict diet compliance
            if isinstance(r, HomelyMealRecipeWrapper) or hasattr(r, "_homely_meal"):
                hm_obj = getattr(r, "_homely_meal", None) or r
                if "jain" in diet_type and not RecommendationEngine.is_homely_meal_jain(hm_obj):
                    continue
                elif "vegan" in diet_type and not RecommendationEngine.is_homely_meal_vegan(hm_obj):
                    continue
                elif "eggetarian" in diet_type and not RecommendationEngine.is_homely_meal_eggetarian(hm_obj):
                    continue
                elif "vegetarian" in diet_type and "non" not in diet_type and not RecommendationEngine.is_homely_meal_vegetarian(hm_obj):
                    continue
            else:
                if "jain" in diet_type and not RecommendationEngine.is_jain(r):
                    continue
                elif "vegan" in diet_type and not RecommendationEngine.is_vegan(r):
                    continue
                elif "eggetarian" in diet_type and not RecommendationEngine.is_eggetarian(r):
                    continue
                elif "vegetarian" in diet_type and "non" not in diet_type and not RecommendationEngine.is_vegetarian(r):
                    continue

            # Check allergies & dislikes
            rname_lower = (r.recipe_name or "").lower()
            excluded = False
            for term in (allergies + dislikes):
                t_low = term.lower()
                if t_low and t_low in rname_lower:
                    excluded = True
                    break
                for ing in (getattr(r, "ingredients", []) or []):
                    ing_name = (getattr(ing, "food_name", "") or getattr(ing, "ingredient_name", "") or "").lower()
                    if t_low and t_low in ing_name:
                        excluded = True
                        break
                if excluded:
                    break

            if excluded:
                continue

            # Score recipe
            score = RecommendationEngine.calculate_score(r, user, likes)
            # Bonus if matches requested cuisine
            if cuisine_req and str(cuisine_req).lower().strip() not in ("any", "all", "", "none"):
                c_low = str(cuisine_req).lower().strip()
                kws = cls.CUISINE_ALIASES.get(c_lower, [c_lower])
                rc = (getattr(r, "cuisine", "") or "").lower()
                rn = (getattr(r, "recipe_name", "") or "").lower()
                if any(kw in rc or kw in rn for kw in kws):
                    score += 40.0

            # Add exploration jitter for fresh varied menus
            variety_jitter = random.uniform(-6.0, 6.0)
            scored_candidates.append((r, score + variety_jitter))

        # Sort by score descending and take top N
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        return scored_candidates[:limit_candidates]


    @classmethod
    def generate_daily_plan(
        cls, 
        db: Session, 
        user_id: int, 
        tolerance: Optional[float] = None, 
        max_tolerance: float = 0.45,
        preference: str = "balanced",
        meal_cuisines: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict]:
        """Generate a daily meal plan satisfying calorie, macronutrient, and fibre targets using Google OR-Tools."""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        # Extract user preferences
        likes = []
        allergies = []
        dislikes = []
        for p in (user.preferences or []):
            t = (p.preference_type or "").lower().strip()
            v = (p.value or "").strip()
            if t == "like":
                likes.append(v)
            elif t == "allergy":
                allergies.append(v)
            elif t == "dislike":
                dislikes.append(v)

        # Build candidate pools per slot
        slots = ["Breakfast", "Lunch", "Dinner", "Snack"]
        categories = {}
        scores = {}

        for slot in slots:
            req_c = (meal_cuisines or {}).get(slot)
            candidates = cls._fetch_slot_candidates(
                db=db,
                slot_name=slot,
                user=user,
                likes=likes,
                allergies=allergies,
                dislikes=dislikes,
                cuisine_req=req_c,
                limit_candidates=75
            )

            if not candidates:
                # Fallback: fetch without cuisine constraint to prevent failure
                candidates = cls._fetch_slot_candidates(
                    db=db,
                    slot_name=slot,
                    user=user,
                    likes=likes,
                    allergies=allergies,
                    dislikes=dislikes,
                    cuisine_req=None,
                    limit_candidates=75
                )

            if not candidates:
                return None

            categories[slot] = [c[0] for c in candidates]
            for r, sc in candidates:
                scores[r.recipe_code] = sc

        # Define targets based on calorie needs and preference splits
        target_cal = user.target_calories or 2000.0
        target_fiber = 28.0
        
        pref = (preference or "balanced").lower().strip()
        if pref == "high_protein":
            target_prot = (target_cal * 0.30) / 4.0
            target_carb = (target_cal * 0.40) / 4.0
            target_fat = (target_cal * 0.30) / 9.0
        elif pref == "low_carb":
            target_prot = (target_cal * 0.25) / 4.0
            target_carb = (target_cal * 0.20) / 4.0
            target_fat = (target_cal * 0.55) / 9.0
        elif pref == "low_fat":
            target_prot = (target_cal * 0.20) / 4.0
            target_carb = (target_cal * 0.60) / 4.0
            target_fat = (target_cal * 0.20) / 9.0
        elif pref in ("high_fiber", "high_fibre"):
            target_prot = (target_cal * 0.20) / 4.0
            target_carb = (target_cal * 0.55) / 4.0
            target_fat = (target_cal * 0.25) / 9.0
            target_fiber = 35.0
        else: # "balanced"
            target_prot = user.target_protein if user.target_protein and user.target_protein > 0 else (target_cal * 0.20) / 4.0
            target_carb = user.target_carbs if user.target_carbs and user.target_carbs > 0 else (target_cal * 0.50) / 4.0
            target_fat = user.target_fat if user.target_fat and user.target_fat > 0 else (target_cal * 0.30) / 9.0

        # Solve iteratively with increasing tolerance starting tightly
        current_tol = tolerance if (tolerance is not None and tolerance > 0) else 0.08
        while current_tol <= max_tolerance:
            result = cls._solve_mip(
                categories=categories,
                scores=scores,
                target_cal=target_cal,
                target_prot=target_prot,
                target_carb=target_carb,
                target_fat=target_fat,
                target_fiber=target_fiber,
                tolerance=current_tol,
                preference=pref
            )
            if result:
                return result
            current_tol += 0.05

        # Fallback solver with soft macro penalties if strict tolerance failed
        return cls._solve_soft_mip(
            categories=categories,
            scores=scores,
            target_cal=target_cal,
            target_prot=target_prot,
            target_carb=target_carb,
            target_fat=target_fat,
            target_fiber=target_fiber,
            preference=pref
        )

    @staticmethod
    def _solve_mip(
        categories: Dict[str, List[Any]],
        scores: Dict[str, float],
        target_cal: float,
        target_prot: float,
        target_carb: float,
        target_fat: float,
        target_fiber: float = 28.0,
        tolerance: float = 0.15,
        preference: str = "balanced"
    ) -> Optional[Dict]:
        """MIP solver with bounded tolerance."""
        solver = pywraplp.Solver.CreateSolver("SCIP")
        if not solver:
            return None

        slots = ["Breakfast", "Lunch", "Dinner", "Snack"]
        y = {}
        for slot in slots:
            for recipe in categories[slot]:
                y[slot, recipe.recipe_code] = solver.BoolVar(f"y_{slot}_{recipe.recipe_code}")

        # Choose exactly 1 per slot
        for slot in slots:
            solver.Add(solver.Sum(y[slot, r.recipe_code] for r in categories[slot]) == 1)

        # Lunch and Dinner must be distinct recipes
        lunch_codes = {r.recipe_code for r in categories["Lunch"]}
        dinner_codes = {r.recipe_code for r in categories["Dinner"]}
        common_codes = lunch_codes.intersection(dinner_codes)
        for code in common_codes:
            solver.Add(y["Lunch", code] + y["Dinner", code] <= 1)

        # Total nutrition helpers
        def get_nutrient_sum(nutrient_attr: str):
            terms = []
            for slot in slots:
                for r in categories[slot]:
                    val = getattr(r.nutrition, nutrient_attr, 0.0) or 0.0
                    terms.append(val * y[slot, r.recipe_code])
            return solver.Sum(terms)

        total_cal = get_nutrient_sum("unit_serving_energy_kcal")
        total_prot = get_nutrient_sum("unit_serving_protein_g")
        total_carb = get_nutrient_sum("unit_serving_carb_g")
        total_fat = get_nutrient_sum("unit_serving_fat_g")

        solver.Add(total_cal >= target_cal * (1.0 - tolerance))
        solver.Add(total_cal <= target_cal * (1.0 + tolerance))

        solver.Add(total_prot >= target_prot * (1.0 - tolerance))
        solver.Add(total_prot <= target_prot * (1.0 + tolerance))

        solver.Add(total_carb >= target_carb * (1.0 - tolerance))
        solver.Add(total_carb <= target_carb * (1.0 + tolerance))

        solver.Add(total_fat >= target_fat * (1.0 - tolerance))
        solver.Add(total_fat <= target_fat * (1.0 + tolerance))

        if preference in ("high_fiber", "high_fibre"):
            total_fiber = get_nutrient_sum("unit_serving_fibre_g")
            solver.Add(total_fiber >= target_fiber * (1.0 - tolerance))

        # Maximize score
        objective_terms = []
        for slot in slots:
            for r in categories[slot]:
                score = scores.get(r.recipe_code, 50.0)
                fib_val = getattr(r.nutrition, "unit_serving_fibre_g", 0.0) or 0.0
                fib_bonus = fib_val * 2.0 if preference in ("high_fiber", "high_fibre") else 0.0
                objective_terms.append((score + fib_bonus) * y[slot, r.recipe_code])

        solver.Maximize(solver.Sum(objective_terms))
        status = solver.Solve()

        if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
            return OptimizationEngine._extract_plan_result(
                y, categories, target_cal, target_prot, target_carb, target_fat, target_fiber, tolerance
            )
        return None

    @staticmethod
    def _solve_soft_mip(
        categories: Dict[str, List[Any]],
        scores: Dict[str, float],
        target_cal: float,
        target_prot: float,
        target_carb: float,
        target_fat: float,
        target_fiber: float = 28.0,
        preference: str = "balanced"
    ) -> Optional[Dict]:
        """Soft penalty-based MIP solver ensuring feasible meal plans for all combinations."""
        solver = pywraplp.Solver.CreateSolver("SCIP")
        if not solver:
            return None

        slots = ["Breakfast", "Lunch", "Dinner", "Snack"]
        y = {}
        for slot in slots:
            for recipe in categories[slot]:
                y[slot, recipe.recipe_code] = solver.BoolVar(f"y_{slot}_{recipe.recipe_code}")

        for slot in slots:
            solver.Add(solver.Sum(y[slot, r.recipe_code] for r in categories[slot]) == 1)

        lunch_codes = {r.recipe_code for r in categories["Lunch"]}
        dinner_codes = {r.recipe_code for r in categories["Dinner"]}
        for code in lunch_codes.intersection(dinner_codes):
            solver.Add(y["Lunch", code] + y["Dinner", code] <= 1)

        # Deviation variables for calories
        cal_dev_pos = solver.NumVar(0.0, 5000.0, "cal_dev_pos")
        cal_dev_neg = solver.NumVar(0.0, 5000.0, "cal_dev_neg")

        terms_cal = []
        for slot in slots:
            for r in categories[slot]:
                val = getattr(r.nutrition, "unit_serving_energy_kcal", 0.0) or 0.0
                terms_cal.append(val * y[slot, r.recipe_code])
        solver.Add(solver.Sum(terms_cal) - target_cal == cal_dev_pos - cal_dev_neg)

        # Objective: Maximize recommendation scores minus calorie deviation penalty
        objective_terms = []
        for slot in slots:
            for r in categories[slot]:
                score = scores.get(r.recipe_code, 50.0)
                objective_terms.append(score * y[slot, r.recipe_code])

        solver.Maximize(solver.Sum(objective_terms) - 0.5 * (cal_dev_pos + cal_dev_neg))
        status = solver.Solve()

        if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
            return OptimizationEngine._extract_plan_result(
                y, categories, target_cal, target_prot, target_carb, target_fat, target_fiber, 0.25
            )
        return None

    @staticmethod
    def _extract_plan_result(y, categories, target_cal, target_prot, target_carb, target_fat, target_fiber, tolerance):
        slots = ["Breakfast", "Lunch", "Dinner", "Snack"]
        plan = {
            "meals": {},
            "totals": {
                "calories": 0.0,
                "protein_g": 0.0,
                "carbs_g": 0.0,
                "fat_g": 0.0,
                "fibre_g": 0.0,
            },
            "targets": {
                "calories": round(target_cal, 2),
                "protein_g": round(target_prot, 2),
                "carbs_g": round(target_carb, 2),
                "fat_g": round(target_fat, 2),
                "fibre_g": round(target_fiber, 2),
            },
            "tolerance_used": tolerance
        }

        for slot in slots:
            for r in categories[slot]:
                if y[slot, r.recipe_code].solution_value() > 0.5:
                    u_cal = getattr(r.nutrition, "unit_serving_energy_kcal", 0.0) or getattr(r.nutrition, "energy_kcal", 0.0) or 0.0
                    u_prot = getattr(r.nutrition, "unit_serving_protein_g", 0.0) or getattr(r.nutrition, "protein_g", 0.0) or 0.0
                    u_carb = getattr(r.nutrition, "unit_serving_carb_g", 0.0) or getattr(r.nutrition, "carb_g", 0.0) or 0.0
                    u_fat = getattr(r.nutrition, "unit_serving_fat_g", 0.0) or getattr(r.nutrition, "fat_g", 0.0) or 0.0
                    f_val = getattr(r.nutrition, "unit_serving_fibre_g", 0.0) or getattr(r.nutrition, "fibre_g", 0.0) or 0.0

                    serv_size = getattr(getattr(r, "servings", None), "size_of_servings", 1.0) or 1.0
                    serv_unit = getattr(getattr(r, "servings", None), "servings_unit", "serving") or "serving"

                    plan["meals"][slot] = {
                        "recipe_code": r.recipe_code,
                        "recipe_name": r.recipe_name,
                        "serving_size": serv_size,
                        "serving_unit": serv_unit,
                        "calories": round(u_cal, 2),
                        "protein_g": round(u_prot, 2),
                        "carbs_g": round(u_carb, 2),
                        "fat_g": round(u_fat, 2),
                        "fibre_g": round(f_val, 2),
                    }
                    
                    plan["totals"]["calories"] += u_cal
                    plan["totals"]["protein_g"] += u_prot
                    plan["totals"]["carbs_g"] += u_carb
                    plan["totals"]["fat_g"] += u_fat
                    plan["totals"]["fibre_g"] += f_val
                    break

        plan["totals"]["calories"] = round(plan["totals"]["calories"], 2)
        plan["totals"]["protein_g"] = round(plan["totals"]["protein_g"], 2)
        plan["totals"]["carbs_g"] = round(plan["totals"]["carbs_g"], 2)
        plan["totals"]["fat_g"] = round(plan["totals"]["fat_g"], 2)
        plan["totals"]["fibre_g"] = round(plan["totals"]["fibre_g"], 2)

        return plan
