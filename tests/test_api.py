import unittest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app import models

class TestAPIEndpoints(unittest.TestCase):
    def setUp(self):
        # Create in-memory database with shared cache for multi-connection sharing
        self.engine = create_engine(
            "sqlite:///file:test_api?mode=memory&cache=shared",
            connect_args={"check_same_thread": False, "uri": True}
        )
        self.connection = self.engine.connect()
        Base.metadata.drop_all(self.connection)
        Base.metadata.create_all(self.connection)
        
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        # Seed minimal database requirements so recomendation/optimization works
        # A breakfast recipe
        r1 = models.Recipe(recipe_code="B01", recipe_name="Poha", category="Breakfast")
        self.db.add(r1)
        self.db.add(models.RecipeNutrition(
            recipe_code="B01", energy_kcal=245.0, protein_g=20.0, carb_g=30.0, fat_g=5.0,
            unit_serving_energy_kcal=245.0, unit_serving_protein_g=20.0, unit_serving_carb_g=30.0, unit_serving_fat_g=5.0
        ))
        self.db.add(models.Serving(recipe_code="B01", no_of_servings=1, size_of_servings=1, servings_unit="plate"))

        # Two lunch/dinner recipes
        r2 = models.Recipe(recipe_code="L01", recipe_name="Roti and Bhindi", category="Lunch/Dinner")
        self.db.add(r2)
        self.db.add(models.RecipeNutrition(
            recipe_code="L01", energy_kcal=390.0, protein_g=30.0, carb_g=45.0, fat_g=10.0,
            unit_serving_energy_kcal=390.0, unit_serving_protein_g=30.0, unit_serving_carb_g=45.0, unit_serving_fat_g=10.0
        ))
        self.db.add(models.Serving(recipe_code="L01", no_of_servings=1, size_of_servings=1, servings_unit="plate"))

        r3 = models.Recipe(recipe_code="L02", recipe_name="Chicken Curry Rice", category="Lunch/Dinner")
        self.db.add(r3)
        self.db.add(models.RecipeNutrition(
            recipe_code="L02", energy_kcal=600.0, protein_g=35.0, carb_g=70.0, fat_g=12.0,
            unit_serving_energy_kcal=600.0, unit_serving_protein_g=35.0, unit_serving_carb_g=70.0, unit_serving_fat_g=12.0
        ))
        self.db.add(models.Serving(recipe_code="L02", no_of_servings=1, size_of_servings=1, servings_unit="plate"))

        # A snack recipe
        r4 = models.Recipe(recipe_code="S01", recipe_name="Fruit Salad", category="Snack")
        self.db.add(r4)
        self.db.add(models.RecipeNutrition(
            recipe_code="S01", energy_kcal=158.0, protein_g=15.0, carb_g=20.0, fat_g=2.0,
            unit_serving_energy_kcal=158.0, unit_serving_protein_g=15.0, unit_serving_carb_g=20.0, unit_serving_fat_g=2.0
        ))
        self.db.add(models.Serving(recipe_code="S01", no_of_servings=1, size_of_servings=1, servings_unit="bowl"))
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
        try:
            self.connection.close()
        except Exception:
            pass

    def test_flow_calculate_profile_and_recommend_and_optimize_and_track(self):
        # 1. POST /calculate-profile
        payload_profile = {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "age": 28,
            "gender": "female",
            "height": 165.0,
            "weight": 65.0,
            "activity_level": "sedentary",
            "goal": "fat loss",
            "preferences": [
                {"preference_type": "diet_type", "value": "Vegetarian"},
                {"preference_type": "allergy", "value": "peanut"}
            ]
        }
        res = self.client.post("/calculate-profile", json=payload_profile)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["name"], "Jane Doe")
        self.assertEqual(data["email"], "jane@example.com")
        self.assertIn("target_calories", data)
        self.assertIn("id", data)
        
        user_id = data["id"]
        target_calories = data["target_calories"]

        # 2. POST /recommend-foods
        payload_recommend = {
            "user_id": user_id,
            "limit": 10
        }
        res_rec = self.client.post("/recommend-foods", json=payload_recommend)
        self.assertEqual(res_rec.status_code, 200)
        data_rec = res_rec.json()
        self.assertGreater(len(data_rec), 0)
        
        # Verify vegetarian filter is applied - Chicken Curry (L02) contains non-veg, should not be here
        rec_codes = [item["recipe_code"] for item in data_rec]
        self.assertNotIn("L02", rec_codes)
        self.assertIn("L01", rec_codes)

        # 3. POST /generate-meal-plan
        # Targets are:
        # calories target = BMR * 1.2 - 500 = (10*65 + 6.25*165 - 5*28 - 161)*1.2 - 500 = (650+1031.25-140-161)*1.2 - 500 = 1380.25*1.2 - 500 = 1656.3 - 500 = 1156.3
        # Since 1156.3 is below female floor (1200), calorie target is 1200 kcal.
        # Protein: 1200 * 0.3 / 4 = 90g
        # Carbs: 1200 * 0.4 / 4 = 120g
        # Fat: 1200 * 0.3 / 9 = 40g
        #
        # Seeded recipes total serving calories: B01(250) + L01(450) + L01(450) [wait, Lunch and Dinner must be different, but we have L01 and L02, but L02 is non-veg and user is vegetarian, so L02 is filtered out, leaving only L01! Since Lunch and Dinner must select different recipes, and only L01 is available, solver will fail to solve with tolerance 10%.]
        # Let's verify that solver returns 400 Bad Request because of infeasibility.
        payload_plan = {
            "user_id": user_id,
            "tolerance": 0.20
        }
        res_plan = self.client.post("/generate-meal-plan", json=payload_plan)
        self.assertEqual(res_plan.status_code, 400) # Fails due to lack of distinct veg lunch/dinner options!

        # Now let's add another veg option for Lunch/Dinner so it can solve successfully
        r5 = models.Recipe(recipe_code="L03", recipe_name="Paneer Bhurji", category="Lunch/Dinner")
        self.db.add(r5)
        self.db.add(models.RecipeNutrition(
            recipe_code="L03", energy_kcal=350.0, protein_g=20.0, carb_g=10.0, fat_g=25.0,
            unit_serving_energy_kcal=350.0, unit_serving_protein_g=20.0, unit_serving_carb_g=10.0, unit_serving_fat_g=25.0
        ))
        self.db.add(models.Serving(recipe_code="L03", no_of_servings=1, size_of_servings=1, servings_unit="plate"))
        self.db.commit()

        # Let's widen tolerance to 30% to fit the limited mock pool
        payload_plan_ok = {
            "user_id": user_id,
            "tolerance": 0.30
        }
        res_plan_ok = self.client.post("/generate-meal-plan", json=payload_plan_ok)
        self.assertEqual(res_plan_ok.status_code, 200)
        data_plan = res_plan_ok.json()
        self.assertEqual(data_plan["user_id"], user_id)
        self.assertIn("meals", data_plan)
        self.assertIn("totals", data_plan)

        # 4. POST /track-weight
        payload_weight = {
            "user_id": user_id,
            "weight": 65.0,
            "adherence": True
        }
        res_weight = self.client.post("/track-weight", json=payload_weight)
        self.assertEqual(res_weight.status_code, 200)
        data_weight = res_weight.json()
        self.assertEqual(data_weight["status"], "success")
        self.assertEqual(data_weight["weight_logged"]["weight"], 65.0)

    def test_auth_endpoints(self):
        # 1. Register a new user
        register_payload = {
            "email": "testauth@example.com",
            "password": "securepassword123",
            "name": "Auth User",
            "age": 30,
            "gender": "male",
            "height": 180.0,
            "weight": 80.0,
            "activity_level": "active",
            "goal": "maintenance",
            "preferences": [
                {"preference_type": "diet_type", "value": "Non-Vegetarian"}
            ]
        }
        res = self.client.post("/api/auth/register", json=register_payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["user"]["email"], "testauth@example.com")
        self.assertEqual(data["user"]["name"], "Auth User")
        token = data["access_token"]

        # 2. Login user
        login_payload = {
            "email": "testauth@example.com",
            "password": "securepassword123"
        }
        res = self.client.post("/api/auth/login", json=login_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertTrue(len(data["access_token"]) > 0)

        # 3. Get /api/auth/me
        headers = {"Authorization": f"Bearer {token}"}
        res = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["email"], "testauth@example.com")

        # 4. Search history logging and reading
        search_payload = {"query": "apple"}
        res = self.client.post("/api/search-history", json=search_payload, headers=headers)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["query"], "apple")

        res = self.client.get("/api/search-history", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["query"], "apple")

        # 5. Settings update and sync
        setting_payload = {"key": "theme", "value": "dark"}
        res = self.client.put("/api/settings", json=setting_payload, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["key"], "theme")
        self.assertEqual(data["value"], "dark")

        res = self.client.get("/api/settings", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["key"], "theme")

        # 6. Google Sign-In with mock token
        google_payload = {"id_token": "mock-google-john"}
        res = self.client.post("/api/auth/google", json=google_payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["user"]["email"], "john@example.com")

if __name__ == "__main__":
    unittest.main()
