import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, date, timedelta

from app.db import Base, get_db
from app.main import app
from app import models

class TestNewEnginesAPI(unittest.TestCase):
    def setUp(self):
        # Create in-memory database with shared cache
        self.engine = create_engine(
            "sqlite:///file:test_new_api?mode=memory&cache=shared",
            connect_args={"check_same_thread": False, "uri": True}
        )
        self.connection = self.engine.connect()
        Base.metadata.drop_all(self.connection)
        Base.metadata.create_all(self.connection)

        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        # Seed Ingredient Rules
        rules = [
            models.IngredientRule(ingredient_name="onion", rule_type="exclude_jain", value=True),
            models.IngredientRule(ingredient_name="garlic", rule_type="exclude_jain", value=True),
            models.IngredientRule(ingredient_name="chicken", rule_type="exclude_vegetarian", value=True),
            models.IngredientRule(ingredient_name="chicken", rule_type="exclude_vegan", value=True),
            models.IngredientRule(ingredient_name="milk", rule_type="exclude_vegan", value=True),
        ]
        self.db.add_all(rules)

        # Seed a test recipe
        r = models.Recipe(recipe_code="R99", recipe_name="Onion Chicken Curry", category="Lunch/Dinner")
        self.db.add(r)
        self.db.flush()

        self.db.add(models.RecipeNutrition(
            recipe_id=r.id,
            recipe_code="R99",
            energy_kcal=400.0,
            protein_g=30.0, # High protein (30g * 4 = 120 kcal / 400 = 30%)
            carb_g=20.0,
            fat_g=20.0
        ))
        
        self.db.add(models.RecipeIngredient(
            recipe_id=r.id,
            recipe_code="R99",
            ingredient_name="onion",
            food_name="Onion"
        ))
        self.db.add(models.RecipeIngredient(
            recipe_id=r.id,
            recipe_code="R99",
            ingredient_name="chicken",
            food_name="Chicken"
        ))

        # Seed a test user
        self.user = models.User(
            name="Bob Builder",
            email="bob@builder.com"
        )
        self.db.add(self.user)
        self.db.flush()

        # Create user profile
        self.profile = models.Profile(
            user_id=self.user.id,
            age=35,
            gender="male",
            height=180.0,
            weight=80.0,
            activity_level="active",
            goal="muscle gain",
            diet_type="Non-Vegetarian",
            target_calories=2500.0,
            target_protein=150.0,
            target_carbs=300.0,
            target_fat=70.0
        )
        self.db.add(self.profile)
        self.db.commit()

        # Override dependency
        def override_get_db():
            db_session = self.SessionLocal()
            try:
                yield db_session
            finally:
                db_session.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.connection.close()

    def test_classify_recipe(self):
        res = self.client.post("/api/classify", json={"recipe_code": "R99"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["is_vegan"])
        self.assertFalse(data["is_vegetarian"])
        self.assertFalse(data["is_jain"])
        self.assertIn("High Protein", data["tags"])
        self.assertIn("Non-vegetarian: contains Onion Chicken Curry", data["reasons"])

    def test_classify_ingredients(self):
        res = self.client.post("/api/classify", json={"ingredients": ["potato", "spinach", "milk"]})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["is_vegan"]) # Milk excludes vegan
        self.assertTrue(data["is_vegetarian"]) # Dairy is ok for vegetarian
        self.assertTrue(data["is_eggetarian"])

    @patch("app.services.barcode_service.httpx.get")
    def test_barcode_scan_and_cache(self, mock_get):
        # Mock Open Food Facts API response
        mock_response = unittest.mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": 1,
            "product": {
                "product_name": "Test Peanut Butter",
                "brands": "Organic Brands",
                "ingredients_text": "Peanuts, salt",
                "nutrition_grades": "a",
                "nutriments": {
                    "energy-kcal_100g": 588,
                    "proteins_100g": 25,
                    "carbohydrates_100g": 20,
                    "fat_100g": 50,
                    "fiber_100g": 8,
                    "sodium_100g": 0.15 # 0.15g = 150mg
                }
            }
        }
        mock_get.return_value = mock_response

        # Scan new barcode
        res = self.client.get("/api/barcode/1234567890123")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        print("DEBUG SCAN DATA:", data)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["source"], "api")
        self.assertEqual(data["product_name"], "Test Peanut Butter")
        self.assertEqual(data["nutriments"]["energy_kcal"], 588.0)
        self.assertEqual(data["nutriments"]["sodium_mg"], 150.0)

        # Retrieve from cache
        res_cached = self.client.get("/api/barcode/1234567890123")
        self.assertEqual(res_cached.status_code, 200)
        data_cached = res_cached.json()
        self.assertEqual(data_cached["source"], "cache")
        self.assertEqual(data_cached["product_name"], "Test Peanut Butter")

    def test_ocr_label_regex_parsing(self):
        # We can upload a mock image, but since the OCR engine supports fallback,
        # we can test the fallback with text or mock file uploading
        import io
        fake_file = io.BytesIO(b"dummy image bytes")
        
        # Test OCR endpoint with form parameters to log a meal
        res = self.client.post(
            "/api/ocr",
            files={"file": ("label.jpg", fake_file, "image/jpeg")},
            data={"user_id": self.user.id, "meal_type": "Breakfast", "food_name": "OCR Oats"}
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        print("DEBUG OCR DATA:", data)
        # Since dummy bytes won't resolve text under easyocr, it returns "fallback" status
        self.assertEqual(data["status"], "fallback")
        self.assertIn("No text detected", data["message"])

    def test_analytics_generation(self):
        # Log some weight and meals
        log_date = date.today()
        m1 = models.MealLog(user_id=self.user.id, log_date=log_date, meal_type="Breakfast", food_name="Idli", calories=300, protein=8, carbs=60, fat=2)
        m2 = models.MealLog(user_id=self.user.id, log_date=log_date, meal_type="Lunch", food_name="Rice Dal", calories=600, protein=18, carbs=100, fat=12)
        w1 = models.WeightLog(user_id=self.user.id, logged_at=log_date - timedelta(days=7), weight=80.0)
        w2 = models.WeightLog(user_id=self.user.id, logged_at=log_date, weight=79.5)
        
        self.db.add_all([m1, m2, w1, w2])
        self.db.commit()

        # Call analytics endpoint
        res = self.client.get(f"/api/analytics/{self.user.id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["user_id"], self.user.id)
        # Average calorie of logged meals: (300 + 600) / 2 = 450
        self.assertEqual(data["averages_7_days"]["calories"], 450.0)
        # Weight loss trend: -0.5kg over 7 days = -0.5kg/week
        self.assertEqual(data["weight_stats"]["rate_kg_per_week"], -0.5)

        # Call analytics history endpoint
        res_history = self.client.get(f"/api/analytics/{self.user.id}/history?metric_name=weight_trend")
        self.assertEqual(res_history.status_code, 200)
        history_data = res_history.json()
        self.assertEqual(len(history_data), 1)
        self.assertEqual(history_data[0]["value"], -0.5)

if __name__ == "__main__":
    unittest.main()
