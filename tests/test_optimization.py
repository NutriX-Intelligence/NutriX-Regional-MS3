import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app import models
from app.services.optimization_engine import OptimizationEngine

class TestOptimizationEngine(unittest.TestCase):
    def setUp(self):
        # Create in-memory database
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        # Target user: 2000 kcal, 115g Protein, 235g Carbs, 57g Fat
        self.user = models.User(
            name="Alice",
            email="alice@example.com",
            age=25,
            gender="female",
            height=165.0,
            weight=60.0,
            activity_level="moderately_active",
            goal="maintenance",
            target_calories=2000.0,
            target_protein=115.0,
            target_carbs=235.0,
            target_fat=57.0
        )
        self.db.add(self.user)
        self.db.flush()

        # Seed 4 recipes (one for each slot)
        # Breakfast
        r_b = models.Recipe(recipe_code="REC_B", recipe_name="Oatmeal Breakfast", category="Breakfast")
        self.db.add(r_b)
        self.db.add(models.RecipeNutrition(
            recipe_code="REC_B", energy_kcal=400.0, protein_g=20.0, carb_g=55.0, fat_g=10.0,
            unit_serving_energy_kcal=400.0, unit_serving_protein_g=20.0, unit_serving_carb_g=55.0, unit_serving_fat_g=10.0
        ))
        self.db.add(models.Serving(recipe_code="REC_B", no_of_servings=1, size_of_servings=1, servings_unit="bowl"))

        # Lunch/Dinner options
        r_l1 = models.Recipe(recipe_code="REC_L1", recipe_name="Dal and Rice", category="Lunch/Dinner")
        self.db.add(r_l1)
        self.db.add(models.RecipeNutrition(
            recipe_code="REC_L1", energy_kcal=600.0, protein_g=35.0, carb_g=80.0, fat_g=15.0,
            unit_serving_energy_kcal=600.0, unit_serving_protein_g=35.0, unit_serving_carb_g=80.0, unit_serving_fat_g=15.0
        ))
        self.db.add(models.Serving(recipe_code="REC_L1", no_of_servings=1, size_of_servings=1, servings_unit="plate"))

        r_l2 = models.Recipe(recipe_code="REC_L2", recipe_name="Chicken and Roti", category="Lunch/Dinner")
        self.db.add(r_l2)
        self.db.add(models.RecipeNutrition(
            recipe_code="REC_L2", energy_kcal=700.0, protein_g=50.0, carb_g=65.0, fat_g=20.0,
            unit_serving_energy_kcal=700.0, unit_serving_protein_g=50.0, unit_serving_carb_g=65.0, unit_serving_fat_g=20.0
        ))
        self.db.add(models.Serving(recipe_code="REC_L2", no_of_servings=1, size_of_servings=1, servings_unit="plate"))

        # Snack
        r_s = models.Recipe(recipe_code="REC_S", recipe_name="Fruit and Nut Salad", category="Snack")
        self.db.add(r_s)
        self.db.add(models.RecipeNutrition(
            recipe_code="REC_S", energy_kcal=300.0, protein_g=10.0, carb_g=35.0, fat_g=12.0,
            unit_serving_energy_kcal=300.0, unit_serving_protein_g=10.0, unit_serving_carb_g=35.0, unit_serving_fat_g=12.0
        ))
        self.db.add(models.Serving(recipe_code="REC_S", no_of_servings=1, size_of_servings=1, servings_unit="cup"))

        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_meal_plan_optimization(self):
        # Run optimizer (targets sum: Breakfast(400) + Lunch(600) + Dinner(700) + Snack(300) = 2000 kcal)
        # Protein sum: 20 + 35 + 50 + 10 = 115g
        # Carbs sum: 55 + 80 + 65 + 35 = 235g
        # Fat sum: 10 + 15 + 20 + 12 = 57g
        # This matches the targets exactly!
        plan = OptimizationEngine.generate_daily_plan(self.db, self.user.id, tolerance=0.10)
        
        self.assertIsNotNone(plan)
        self.assertIn("meals", plan)
        self.assertIn("totals", plan)
        
        meals = plan["meals"]
        self.assertEqual(meals["Breakfast"]["recipe_code"], "REC_B")
        self.assertEqual(meals["Snack"]["recipe_code"], "REC_S")
        
        # Lunch and Dinner must be chosen from L1 and L2, and MUST be different
        lunch_code = meals["Lunch"]["recipe_code"]
        dinner_code = meals["Dinner"]["recipe_code"]
        
        self.assertIn(lunch_code, ["REC_L1", "REC_L2"])
        self.assertIn(dinner_code, ["REC_L1", "REC_L2"])
        self.assertNotEqual(lunch_code, dinner_code)

        # Check total calculations match
        totals = plan["totals"]
        self.assertAlmostEqual(totals["calories"], 2000.0, delta=20)
        self.assertAlmostEqual(totals["protein_g"], 115.0, delta=2)
        self.assertAlmostEqual(totals["carbs_g"], 235.0, delta=2)
        self.assertAlmostEqual(totals["fat_g"], 57.0, delta=2)

if __name__ == "__main__":
    unittest.main()
