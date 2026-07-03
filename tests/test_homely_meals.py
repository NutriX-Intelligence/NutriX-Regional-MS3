import unittest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app import models
from app.services import homely_meals_engine
from app.services.recommendation_engine import RecommendationEngine
from app.services.optimization_engine import OptimizationEngine

class TestHomelyMeals(unittest.TestCase):
    def setUp(self):
        # 1. Create in-memory SQLite database
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        # 2. Seed basic user
        self.user = models.User(
            name="Alice",
            email="alice@example.com",
            age=25,
            gender="female",
            height=165.0,
            weight=60.0,
            activity_level="lightly_active",
            goal="fat loss",
            target_calories=1500.0,
            target_protein=100.0,
            target_carbs=160.0,
            target_fat=50.0
        )
        self.db.add(self.user)
        self.db.flush()

        # 3. Seed some base foods & nutrients (per 100g)
        self.ghee = models.Food(food_code="IND_GHEE_01", name="Ghee")
        self.ghee_nut = models.FoodNutrient(
            food_id=1, # matches food id
            energy_kcal=900.0,
            protein_g=0.0,
            carb_g=0.0,
            fat_g=100.0,
            fibre_g=0.0,
            sodium_mg=5.0,
            sugar_g=0.0
        )
        self.ghee.nutrients = self.ghee_nut
        self.db.add(self.ghee)

        self.papad = models.Food(food_code="IND_PAPAD_01", name="Papad")
        self.papad_nut = models.FoodNutrient(
            food_id=2,
            energy_kcal=320.0,
            protein_g=20.0,
            carb_g=55.0,
            fat_g=2.0,
            fibre_g=8.0,
            sodium_mg=1200.0,
            sugar_g=1.0
        )
        self.papad.nutrients = self.papad_nut
        self.db.add(self.papad)
        
        # 4. Seed some unit conversions
        # Ghee: 1 tsp = 4.2g
        self.db.add(models.UnitConversion(food_item="ghee", unit="tsp", gram_weight=4.2))
        # Papad: 1 piece = 15.0g
        self.db.add(models.UnitConversion(food_item="papad", unit="piece", gram_weight=15.0))
        
        # 5. Seed some basic preferences for recommendation testing
        self.db.add(models.UserPreference(user_id=self.user.id, preference_type="diet_type", value="Vegetarian"))
        
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_parse_gram_weight(self):
        # Specific match
        w_ghee = homely_meals_engine.parse_gram_weight(self.db, "ghee", "tsp", 2.0)
        self.assertAlmostEqual(w_ghee, 8.4)  # 2.0 * 4.2 = 8.4

        w_papad = homely_meals_engine.parse_gram_weight(self.db, "papad", "piece", 3.0)
        self.assertAlmostEqual(w_papad, 45.0) # 3.0 * 15.0 = 45.0

        # Substring fuzzy match
        w_fuzzy = homely_meals_engine.parse_gram_weight(self.db, "cow ghee premium", "tsp", 1.0)
        self.assertAlmostEqual(w_fuzzy, 4.2)

        # Fallback rule: cup -> 240g
        w_fallback = homely_meals_engine.parse_gram_weight(self.db, "sugar", "cup", 2.0)
        self.assertAlmostEqual(w_fallback, 480.0)

    def test_match_food_item(self):
        # Exact match
        f1 = homely_meals_engine.match_food_item(self.db, "Ghee")
        self.assertIsNotNone(f1)
        self.assertEqual(f1.food_code, "IND_GHEE_01")

        # Fuzzy word overlap match
        f2 = homely_meals_engine.match_food_item(self.db, "crispy spicy papad roasted")
        self.assertIsNotNone(f2)
        self.assertEqual(f2.food_code, "IND_PAPAD_01")

    def test_calculate_ingredient_nutrition(self):
        # Papad 2 pieces (2 * 15g = 30g)
        # Nutrition per 100g: energy=320, protein=20, carbs=55, fat=2
        # Expected for 30g: energy=96, protein=6, carbs=16.5, fat=0.6
        res = homely_meals_engine.calculate_ingredient_nutrition(self.db, "spicy papad", 2.0, "piece")
        self.assertEqual(res["gram_weight"], 30.0)
        self.assertEqual(res["matched_food_code"], "IND_PAPAD_01")
        
        n = res["nutrients"]
        self.assertAlmostEqual(n["energy_kcal"], 96.0)
        self.assertAlmostEqual(n["protein_g"], 6.0)
        self.assertAlmostEqual(n["carb_g"], 16.5)
        self.assertAlmostEqual(n["fat_g"], 0.6)

    def test_create_and_moderate_homely_meal(self):
        # Define creation data payload
        class IngredientInput:
            def __init__(self, name, amount, unit):
                self.ingredient_name = name
                self.amount = amount
                self.unit = unit

        class MealInput:
            name = "Papad Churi"
            creator_id = 1
            is_community = True
            cuisine = "Rajasthani"
            region = "West India"
            ingredients = [
                IngredientInput("roasted papad", 2.0, "piece"),
                IngredientInput("cow ghee", 1.0, "tsp")
            ]
            tags = ["Healthy", "Snack"]

        # Create
        meal = homely_meals_engine.create_homely_meal(self.db, MealInput)
        self.assertIsNotNone(meal)
        self.assertEqual(meal.name, "Papad Churi")
        self.assertEqual(meal.status, "pending")
        self.assertEqual(len(meal.ingredients), 2)
        
        # Verify saved nutrition (30g papad + 4.2g ghee)
        # Papad 30g macros: energy=96, protein=6, carbs=16.5, fat=0.6, fiber=2.4, sodium=360, sugar=0.3
        # Ghee 4.2g macros: energy=37.8, protein=0, carbs=0, fat=4.2, fiber=0, sodium=0.21, sugar=0
        # Totals: energy=133.8, protein=6.0, carbs=16.5, fat=4.8, fiber=2.4, sodium=360.21, sugar=0.3
        n = meal.nutrition
        self.assertIsNotNone(n)
        self.assertAlmostEqual(n.energy_kcal, 133.8)
        self.assertAlmostEqual(n.protein_g, 6.0)
        self.assertAlmostEqual(n.carb_g, 16.5)
        self.assertAlmostEqual(n.fat_g, 4.8)

        # Verify Tags
        tags = [t.tag for t in meal.tags]
        self.assertIn("Healthy", tags)
        self.assertIn("Snack", tags)

        # Verify Versions
        self.assertEqual(len(meal.versions), 1)
        self.assertEqual(meal.versions[0].version_number, 1)

        # Moderate Approve
        homely_meals_engine.update_meal_status(self.db, meal.id, "approved", reviewer_id=1, comment="Looks tasty!")
        self.assertEqual(meal.status, "approved")
        self.assertEqual(len(meal.reviews), 1)

        # Review commenting
        homely_meals_engine.add_review(self.db, meal.id, reviewer_id=1, rating=5, comment="Amazing traditional snack.")
        self.assertEqual(meal.popularity, 1)

    def test_recommendation_and_optimization_integration(self):
        # Define approved homely meal
        class IngredientInput:
            def __init__(self, name, amount, unit):
                self.ingredient_name = name
                self.amount = amount
                self.unit = unit

        class MealInput:
            name = "Roti Ghee"
            creator_id = 1
            is_community = True
            cuisine = "Indian"
            region = "North"
            ingredients = [
                IngredientInput("ghee", 2.0, "tsp") # 8.4g ghee = 75.6 kcal
            ]
            tags = []

        # Create and approve
        meal = homely_meals_engine.create_homely_meal(self.db, MealInput)
        homely_meals_engine.update_meal_status(self.db, meal.id, "approved")

        # Get recommendations
        recs = RecommendationEngine.get_recommendations(self.db, self.user.id)
        # Should include our newly approved homely meal
        homely_rec = [r for r in recs if r["recipe_code"] == f"HOMELY_{meal.id}"]
        self.assertEqual(len(homely_rec), 1)
        self.assertEqual(homely_rec[0]["recipe_name"], "Roti Ghee")
        
        # Test optimization wrap conversion
        from app.services.optimization_engine import HomelyMealRecipeWrapper
        wrapper = HomelyMealRecipeWrapper(meal)
        self.assertEqual(wrapper.recipe_code, f"HOMELY_{meal.id}")
        self.assertEqual(wrapper.recipe_name, "Roti Ghee")
        self.assertEqual(wrapper.nutrition.energy_kcal, meal.nutrition.energy_kcal)

if __name__ == "__main__":
    unittest.main()
