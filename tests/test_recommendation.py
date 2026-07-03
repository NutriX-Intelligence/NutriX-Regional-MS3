import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app import models
from app.services.recommendation_engine import RecommendationEngine

class TestRecommendationEngine(unittest.TestCase):
    def setUp(self):
        # Create in-memory database for testing
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        # Seed test user
        self.user = models.User(
            name="John Doe",
            email="john@example.com",
            age=30,
            gender="male",
            height=175.0,
            weight=70.0,
            activity_level="sedentary",
            goal="maintenance",
            target_calories=2000.0,
            target_protein=125.0, # 25% (500 kcal)
            target_carbs=225.0,   # 45% (900 kcal)
            target_fat=66.67      # 30% (600 kcal)
        )
        self.db.add(self.user)
        self.db.flush()

        # Seed test recipes
        # 1. Chicken Curry (Non-veg, high protein)
        self.recipe_chicken = models.Recipe(
            recipe_code="REC_CHICKEN",
            recipe_name="Spicy Chicken Curry",
            primarysource="test",
            category="Lunch/Dinner"
        )
        self.db.add(self.recipe_chicken)
        self.db.flush()

        self.chicken_nutrition = models.RecipeNutrition(
            recipe_code="REC_CHICKEN",
            energy_kcal=300.0,
            protein_g=25.0,  # 100 kcal (33%)
            carb_g=10.0,     # 40 kcal (13%)
            fat_g=18.0,      # 162 kcal (54%)
            unit_serving_energy_kcal=300.0,
            unit_serving_protein_g=25.0,
            unit_serving_carb_g=10.0,
            unit_serving_fat_g=18.0
        )
        self.db.add(self.chicken_nutrition)
        
        self.chicken_ing = models.RecipeIngredient(
            recipe_code="REC_CHICKEN",
            food_name="Chicken meat",
            amount=150.0,
            unit="g"
        )
        self.db.add(self.chicken_ing)

        # 2. Dal Fry (Veg, high carb/protein mix)
        self.recipe_dal = models.Recipe(
            recipe_code="REC_DAL",
            recipe_name="Yellow Dal Fry",
            primarysource="test",
            category="Lunch/Dinner"
        )
        self.db.add(self.recipe_dal)
        self.db.flush()

        self.dal_nutrition = models.RecipeNutrition(
            recipe_code="REC_DAL",
            energy_kcal=200.0,
            protein_g=12.0,  # 48 kcal (24%)
            carb_g=30.0,     # 120 kcal (60%)
            fat_g=3.5,       # 31.5 kcal (16%)
            unit_serving_energy_kcal=200.0,
            unit_serving_protein_g=12.0,
            unit_serving_carb_g=30.0,
            unit_serving_fat_g=3.5
        )
        self.db.add(self.dal_nutrition)

        self.dal_ing = models.RecipeIngredient(
            recipe_code="REC_DAL",
            food_name="Lentil (split yellow)",
            amount=80.0,
            unit="g"
        )
        self.db.add(self.dal_ing)
        
        # 3. Paneer Butter Masala (Veg, high fat/protein)
        self.recipe_paneer = models.Recipe(
            recipe_code="REC_PANEER",
            recipe_name="Paneer Butter Masala",
            primarysource="test",
            category="Lunch/Dinner"
        )
        self.db.add(self.recipe_paneer)
        self.db.flush()

        self.paneer_nutrition = models.RecipeNutrition(
            recipe_code="REC_PANEER",
            energy_kcal=350.0,
            protein_g=15.0,  # 60 kcal (17%)
            carb_g=15.0,     # 60 kcal (17%)
            fat_g=25.0,      # 225 kcal (64%)
            unit_serving_energy_kcal=350.0,
            unit_serving_protein_g=15.0,
            unit_serving_carb_g=15.0,
            unit_serving_fat_g=25.0
        )
        self.db.add(self.paneer_nutrition)

        self.paneer_ing = models.RecipeIngredient(
            recipe_code="REC_PANEER",
            food_name="Paneer (cottage cheese)",
            amount=100.0,
            unit="g"
        )
        self.db.add(self.paneer_ing)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_vegetarian_filter(self):
        # Set user preference to Vegetarian
        pref = models.UserPreference(
            user_id=self.user.id,
            preference_type="diet_type",
            value="Vegetarian"
        )
        self.db.add(pref)
        self.db.commit()

        # Dal and Paneer should be returned, Chicken should be filtered out
        recs = RecommendationEngine.get_recommendations(self.db, self.user.id)
        rec_codes = [r["recipe_code"] for r in recs]
        
        self.assertIn("REC_DAL", rec_codes)
        self.assertIn("REC_PANEER", rec_codes)
        self.assertNotIn("REC_CHICKEN", rec_codes)

    def test_allergy_filter(self):
        # Set user preference: Allergic to paneer
        pref = models.UserPreference(
            user_id=self.user.id,
            preference_type="allergy",
            value="paneer"
        )
        self.db.add(pref)
        self.db.commit()

        # Dal and Chicken should be returned, Paneer should be filtered out
        recs = RecommendationEngine.get_recommendations(self.db, self.user.id)
        rec_codes = [r["recipe_code"] for r in recs]
        
        self.assertIn("REC_DAL", rec_codes)
        self.assertIn("REC_CHICKEN", rec_codes)
        self.assertNotIn("REC_PANEER", rec_codes)

    def test_likes_boost(self):
        # Set user preference: Likes yellow lentil
        pref = models.UserPreference(
            user_id=self.user.id,
            preference_type="like",
            value="lentil"
        )
        self.db.add(pref)
        self.db.commit()

        # Dal should have a higher score because of the likes boost
        recs = RecommendationEngine.get_recommendations(self.db, self.user.id)
        
        dal_score = [r["score"] for r in recs if r["recipe_code"] == "REC_DAL"][0]
        chicken_score = [r["score"] for r in recs if r["recipe_code"] == "REC_CHICKEN"][0]

        # In a normal comparison, Dal matches macros better, but with the likes boost it should be significantly boosted
        # Dal has protein_pct=24%, carbs_pct=60%, fat_pct=16%. Target: 25%/45%/30%.
        # Chicken has protein_pct=33%, carbs_pct=13%, fat_pct=54%.
        # Let's verify that Dal is the top recommendation due to boost
        self.assertEqual(recs[0]["recipe_code"], "REC_DAL")

if __name__ == "__main__":
    unittest.main()
