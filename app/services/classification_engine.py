from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.models import Recipe, IngredientRule

class ClassificationEngine:
    @classmethod
    def get_rules_map(cls, db: Session) -> Dict[str, List[str]]:
        """Fetch rules from database and group them by rule_type."""
        rules = db.query(IngredientRule).all()
        rules_map = {}
        for r in rules:
            if r.rule_type not in rules_map:
                rules_map[r.rule_type] = []
            rules_map[r.rule_type].append(r.ingredient_name.lower())
        return rules_map

    @classmethod
    def classify_ingredients(cls, ingredient_names: List[str], rules_map: Dict[str, List[str]]) -> Dict[str, Any]:
        """Classify a list of ingredients against the rule map.
        
        Returns a dict of boolean flags representing what the food IS.
        """
        exclude_vegan = rules_map.get("exclude_vegan", [])
        exclude_vegetarian = rules_map.get("exclude_vegetarian", [])
        exclude_eggetarian = rules_map.get("exclude_eggetarian", [])
        exclude_jain = rules_map.get("exclude_jain", [])

        # Default states: start as True, check for exclusions
        is_vegan = True
        is_vegetarian = True
        is_eggetarian = True
        is_jain = True

        reasons = []

        for name in ingredient_names:
            name_lower = name.lower()
            
            # Check Vegan
            for val in exclude_vegan:
                if val in name_lower:
                    is_vegan = False
                    reasons.append(f"Non-vegan: contains {name}")
                    break

            # Check Vegetarian
            for val in exclude_vegetarian:
                if val in name_lower:
                    is_vegetarian = False
                    reasons.append(f"Non-vegetarian: contains {name}")
                    break

            # Check Eggetarian
            for val in exclude_eggetarian:
                if val in name_lower:
                    is_eggetarian = False
                    reasons.append(f"Non-eggetarian: contains {name}")
                    break

            # Check Jain
            for val in exclude_jain:
                if val in name_lower:
                    is_jain = False
                    reasons.append(f"Non-jain: contains {name}")
                    break

        # A vegan or jain recipe is always vegetarian and eggetarian
        if is_jain:
            is_vegetarian = True
            is_eggetarian = True
        if is_vegan:
            is_vegetarian = True
            is_eggetarian = True
        elif is_vegetarian:
            is_eggetarian = True

        dietary_tag = "Non-Vegetarian"
        if is_jain:
            dietary_tag = "Jain"
        elif is_vegan:
            dietary_tag = "Vegan"
        elif is_vegetarian:
            dietary_tag = "Vegetarian"
        elif is_eggetarian:
            dietary_tag = "Eggetarian"

        return {
            "is_vegan": is_vegan,
            "is_vegetarian": is_vegetarian,
            "is_eggetarian": is_eggetarian,
            "is_jain": is_jain,
            "dietary_tag": dietary_tag,
            "reasons": list(set(reasons))
        }

    @classmethod
    def classify_recipe(cls, db: Session, recipe: Recipe) -> Dict[str, Any]:
        """Classify a recipe based on its name and ingredients."""
        rules_map = cls.get_rules_map(db)
        
        # Collect ingredients
        ingredient_names = []
        if recipe.recipe_name:
            ingredient_names.append(recipe.recipe_name)
        for ing in recipe.ingredients:
            if ing.food_name:
                ingredient_names.append(ing.food_name)
            if ing.ingredient_name:
                ingredient_names.append(ing.ingredient_name)

        classification = cls.classify_ingredients(ingredient_names, rules_map)

        # Add nutrition indicators if recipe has nutrition
        nutrition = recipe.nutrition
        tags = []
        if nutrition:
            energy = nutrition.energy_kcal or 0.0
            if energy > 0:
                p_cal = (nutrition.protein_g or 0.0) * 4.0
                c_cal = (nutrition.carb_g or 0.0) * 4.0
                f_cal = (nutrition.fat_g or 0.0) * 9.0
                total_cal = p_cal + c_cal + f_cal

                # Tag rules
                if p_cal / energy >= 0.20:
                    tags.append("High Protein")
                if c_cal / energy <= 0.35:
                    tags.append("Low Carb")
                if f_cal / energy <= 0.20:
                    tags.append("Low Fat")
                if (nutrition.fibre_g or 0.0) >= 3.0:
                    tags.append("High Fiber")
                if (nutrition.sodium_mg or 0.0) <= 140.0:
                    tags.append("Low Sodium")

        classification["tags"] = tags
        return classification
