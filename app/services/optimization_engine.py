from typing import Dict, List, Optional, Tuple
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
        self.nutrition = NutritionMock(meal.nutrition)

class OptimizationEngine:
    @classmethod
    def generate_daily_plan(
        cls, 
        db: Session, 
        user_id: int, 
        tolerance: float = 0.15, 
        max_tolerance: float = 0.40,
        preference: str = "balanced"
    ) -> Optional[Dict]:
        """Generate a daily meal plan satisfying calorie and macronutrient targets using Google OR-Tools.
        
        Args:
            db: SQLAlchemy Session
            user_id: User database ID
            tolerance: initial nutrient tolerance (e.g. 0.15 = +/- 15%)
            max_tolerance: maximum tolerance if initial run is infeasible
            preference: dietary preference for macro splits and targets
            
        Returns:
            Dict containing selected recipes and totals, or None if completely infeasible
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None

        # Fetch ranked recipes for the user using recommendation engine
        # We fetch a larger pool (e.g. 300) to give OR-Tools plenty of options to optimize macros
        ranked = RecommendationEngine.get_recommendations(db, user_id, limit=300)
        if not ranked:
            return None

        # Map codes to recipe database items
        recipe_codes = [r["recipe_code"] for r in ranked]
        std_codes = [c for c in recipe_codes if not c.startswith("HOMELY_")]
        homely_ids = [int(c.split("_")[1]) for c in recipe_codes if c.startswith("HOMELY_")]

        from sqlalchemy.orm import joinedload
        db_recipes = db.query(Recipe).options(
            joinedload(Recipe.nutrition),
            joinedload(Recipe.servings)
        ).filter(Recipe.recipe_code.in_(std_codes)).all()
        
        recipe_map = {r.recipe_code: r for r in db_recipes}
        
        if homely_ids:
            db_homely = db.query(HomelyMeal).options(
                joinedload(HomelyMeal.nutrition)
            ).filter(HomelyMeal.id.in_(homely_ids)).all()
            for meal in db_homely:
                wrapper = HomelyMealRecipeWrapper(meal)
                recipe_map[wrapper.recipe_code] = wrapper

        # Organize recipes by category
        categories = {
            "Breakfast": [],
            "Lunch": [],
            "Dinner": [],
            "Snack": []
        }

        # Keep track of recommendation scores
        scores = {}
        for r in ranked:
            code = r["recipe_code"]
            db_rec = recipe_map.get(code)
            if not db_rec or not db_rec.nutrition:
                continue
            
            # Skip recipes with 0 serving size or 0 serving energy to ensure real meals
            u_energy = db_rec.nutrition.unit_serving_energy_kcal
            if not u_energy or u_energy < 10.0:
                continue

            scores[code] = r["score"]
            cat = db_rec.category
            if cat == "Breakfast":
                categories["Breakfast"].append(db_rec)
            elif cat == "Lunch/Dinner":
                categories["Lunch"].append(db_rec)
                categories["Dinner"].append(db_rec)
            elif cat == "Snack":
                categories["Snack"].append(db_rec)

        # Validate that we have options in every category
        for cat_name, items in categories.items():
            if not items:
                print(f"Error: No recipes found for category: {cat_name}")
                return None

        # Define targets based on calorie needs and preference splits
        target_cal = user.target_calories or 2000.0
        
        pref = (preference or "balanced").lower().strip()
        if pref == "high_protein":
            # 30% Protein, 40% Carbs, 30% Fat
            target_prot = (target_cal * 0.30) / 4.0
            target_carb = (target_cal * 0.40) / 4.0
            target_fat = (target_cal * 0.30) / 9.0
        elif pref == "low_carb":
            # 25% Protein, 20% Carbs, 55% Fat
            target_prot = (target_cal * 0.25) / 4.0
            target_carb = (target_cal * 0.20) / 4.0
            target_fat = (target_cal * 0.55) / 9.0
        elif pref == "low_fat":
            # 20% Protein, 60% Carbs, 20% Fat
            target_prot = (target_cal * 0.20) / 4.0
            target_carb = (target_cal * 0.60) / 4.0
            target_fat = (target_cal * 0.20) / 9.0
        else: # "balanced" or "high_fiber"
            # Use user's profile targets if available, otherwise fall back to standard balanced splits
            target_prot = user.target_protein if user.target_protein and user.target_protein > 0 else (target_cal * 0.20) / 4.0
            target_carb = user.target_carbs if user.target_carbs and user.target_carbs > 0 else (target_cal * 0.50) / 4.0
            target_fat = user.target_fat if user.target_fat and user.target_fat > 0 else (target_cal * 0.30) / 9.0

        # Solve iteratively with increasing tolerance if infeasible
        current_tol = tolerance
        while current_tol <= max_tolerance:
            print(f"Attempting to optimize meal plan with tolerance: {current_tol:.2%}")
            result = cls._solve_mip(
                categories=categories,
                scores=scores,
                target_cal=target_cal,
                target_prot=target_prot,
                target_carb=target_carb,
                target_fat=target_fat,
                tolerance=current_tol,
                preference=pref
            )
            if result:
                return result
            current_tol += 0.05

        print("Failed to optimize meal plan: Infeasible even at max tolerance.")
        return None

    @staticmethod
    def _solve_mip(
        categories: Dict[str, List[Recipe]],
        scores: Dict[str, float],
        target_cal: float,
        target_prot: float,
        target_carb: float,
        target_fat: float,
        tolerance: float,
        preference: str = "balanced"
    ) -> Optional[Dict]:
        """Internal MIP solver execution."""
        # Create solver
        solver = pywraplp.Solver.CreateSolver("SCIP")
        if not solver:
            return None

        # 1. Variables
        # y[slot, recipe_code] is binary
        y = {}
        slots = ["Breakfast", "Lunch", "Dinner", "Snack"]
        for slot in slots:
            for recipe in categories[slot]:
                y[slot, recipe.recipe_code] = solver.BoolVar(f"y_{slot}_{recipe.recipe_code}")

        # 2. Constraints
        # Rule 1: Choose exactly one recipe per slot
        for slot in slots:
            solver.Add(solver.Sum(y[slot, r.recipe_code] for r in categories[slot]) == 1)

        # Rule 2: Lunch and Dinner must be different recipes
        # Find the overlap (both categories draw from 'Lunch/Dinner' pool)
        lunch_codes = {r.recipe_code for r in categories["Lunch"]}
        dinner_codes = {r.recipe_code for r in categories["Dinner"]}
        common_codes = lunch_codes.intersection(dinner_codes)
        
        for code in common_codes:
            solver.Add(y["Lunch", code] + y["Dinner", code] <= 1)

        # Rule 3: Nutrient Targets (+/- tolerance)
        # Total nutrition per serving
        def get_nutrient_sum(nutrient_attr: str):
            terms = []
            for slot in slots:
                for r in categories[slot]:
                    val = getattr(r.nutrition, nutrient_attr) or 0.0
                    terms.append(val * y[slot, r.recipe_code])
            return solver.Sum(terms)

        total_cal = get_nutrient_sum("unit_serving_energy_kcal")
        total_prot = get_nutrient_sum("unit_serving_protein_g")
        total_carb = get_nutrient_sum("unit_serving_carb_g")
        total_fat = get_nutrient_sum("unit_serving_fat_g")

        # Add range constraints
        solver.Add(total_cal >= target_cal * (1.0 - tolerance))
        solver.Add(total_cal <= target_cal * (1.0 + tolerance))

        solver.Add(total_prot >= target_prot * (1.0 - tolerance))
        solver.Add(total_prot <= target_prot * (1.0 + tolerance))

        solver.Add(total_carb >= target_carb * (1.0 - tolerance))
        solver.Add(total_carb <= target_carb * (1.0 + tolerance))

        solver.Add(total_fat >= target_fat * (1.0 - tolerance))
        solver.Add(total_fat <= target_fat * (1.0 + tolerance))

        # Enforce high-fiber constraint if requested
        if preference == "high_fiber":
            total_fiber = get_nutrient_sum("unit_serving_fibre_g")
            # Require at least 25g of fiber daily, adjusted by tolerance
            solver.Add(total_fiber >= 25.0 * (1.0 - tolerance))

        # 3. Objective: Maximize recommendation scores
        objective_terms = []
        for slot in slots:
            for r in categories[slot]:
                score = scores.get(r.recipe_code, 0.0)
                objective_terms.append(score * y[slot, r.recipe_code])
        
        solver.Maximize(solver.Sum(objective_terms))

        # Solve
        status = solver.Solve()

        if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
            plan = {
                "meals": {},
                "totals": {
                    "calories": 0.0,
                    "protein_g": 0.0,
                    "carbs_g": 0.0,
                    "fat_g": 0.0
                },
                "targets": {
                    "calories": round(target_cal, 2),
                    "protein_g": round(target_prot, 2),
                    "carbs_g": round(target_carb, 2),
                    "fat_g": round(target_fat, 2)
                },
                "tolerance_used": tolerance
            }

            for slot in slots:
                for r in categories[slot]:
                    if y[slot, r.recipe_code].solution_value() > 0.5:
                        plan["meals"][slot] = {
                            "recipe_code": r.recipe_code,
                            "recipe_name": r.recipe_name,
                            "serving_size": r.servings.size_of_servings if r.servings else 1.0,
                            "serving_unit": r.servings.servings_unit if r.servings else "serving",
                            "calories": round(r.nutrition.unit_serving_energy_kcal, 2),
                            "protein_g": round(r.nutrition.unit_serving_protein_g, 2),
                            "carbs_g": round(r.nutrition.unit_serving_carb_g, 2),
                            "fat_g": round(r.nutrition.unit_serving_fat_g, 2)
                        }
                        
                        plan["totals"]["calories"] += r.nutrition.unit_serving_energy_kcal
                        plan["totals"]["protein_g"] += r.nutrition.unit_serving_protein_g
                        plan["totals"]["carbs_g"] += r.nutrition.unit_serving_carb_g
                        plan["totals"]["fat_g"] += r.nutrition.unit_serving_fat_g
                        break

            plan["totals"]["calories"] = round(plan["totals"]["calories"], 2)
            plan["totals"]["protein_g"] = round(plan["totals"]["protein_g"], 2)
            plan["totals"]["carbs_g"] = round(plan["totals"]["carbs_g"], 2)
            plan["totals"]["fat_g"] = round(plan["totals"]["fat_g"], 2)

            return plan

        return None
