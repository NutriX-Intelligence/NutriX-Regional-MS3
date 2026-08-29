import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.nutrition_engine import NutritionEngine
from app.services.ocr_engine import OCREngine

client = TestClient(app)

def unique_email(prefix="user"):
    return f"{prefix}_{uuid.uuid4().hex[:8]}@nutrix.io"

# -------------------------------------------------------------
# 1. Nutrition Engine Water Target Unit Tests
# -------------------------------------------------------------
def test_water_target_calculation():
    # 70kg sedentary: 70 * 35 = 2450 ml
    assert NutritionEngine.calculate_water_target(70.0, "sedentary") == 2450.0
    
    # 80kg moderately_active: 80 * 35 + 700 = 2800 + 700 = 3500 ml
    assert NutritionEngine.calculate_water_target(80.0, "moderately_active") == 3500.0
    
    # 60kg very_active: 60 * 35 + 1400 = 2100 + 1400 = 3500 ml
    assert NutritionEngine.calculate_water_target(60.0, "very_active") == 3500.0
    
    # Default fallback (70.0 * 35 = 2450.0)
    assert NutritionEngine.calculate_water_target(0.0, "sedentary") == 2450.0


# -------------------------------------------------------------
# 2. Auth Endpoint Validation & Specific Error Messages
# -------------------------------------------------------------
def test_auth_login_nonexistent_user():
    response = client.post("/api/auth/login", json={
        "email": unique_email("nonexistent"),
        "password": "somepassword123"
    })
    assert response.status_code == 404
    assert response.json()["detail"] == "Please sign up or create an account."


def test_auth_register_and_login_validation():
    test_email = unique_email("revamp_user")
    
    # Register new user
    reg_response = client.post("/api/auth/register", json={
        "name": "Revamp User",
        "email": test_email,
        "password": "securepassword123",
        "age": 28,
        "gender": "male",
        "height": 175.0,
        "weight": 75.0,
        "activity_level": "moderately_active",
        "goal": "maintenance",
        "preferences": [{"preference_type": "diet_type", "value": "Vegetarian"}]
    })
    assert reg_response.status_code == 201
    reg_data = reg_response.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == test_email
    assert reg_data["user"]["water_target_ml"] == 75.0 * 35 + 700  # 3325.0

    # Wrong password test
    wrong_pw_response = client.post("/api/auth/login", json={
        "email": test_email,
        "password": "wrongpassword999"
    })
    assert wrong_pw_response.status_code == 401
    assert wrong_pw_response.json()["detail"] == "Incorrect password. Please try again."

    # Duplicate registration test
    dup_response = client.post("/api/auth/register", json={
        "name": "Duplicate User",
        "email": test_email,
        "password": "anotherpassword",
        "age": 30,
        "gender": "female",
        "height": 160.0,
        "weight": 60.0
    })
    assert dup_response.status_code == 400
    assert "already exists" in dup_response.json()["detail"]


def test_google_login_simulation():
    res = client.post("/api/auth/google", json={
        "id_token": "google_simulated_token_rahul"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "rahul@gmail.com" in data["user"]["email"]



# -------------------------------------------------------------
# 3. Water Intake Logging API
# -------------------------------------------------------------
def test_water_logging_flow():
    # Register user for water test
    email = unique_email("water_user")
    reg = client.post("/api/auth/register", json={
        "name": "Water Tester",
        "email": email,
        "password": "password123",
        "age": 25,
        "gender": "female",
        "height": 165.0,
        "weight": 60.0,
        "activity_level": "lightly_active"
    })
    assert reg.status_code == 201
    user_id = reg.json()["user"]["id"]

    # Post water log: 500 ml
    log1 = client.post("/api/water-logs", json={
        "user_id": user_id,
        "amount_ml": 500.0
    })
    assert log1.status_code == 201
    log1_id = log1.json()["id"]

    # Post another water log: 250 ml
    log2 = client.post("/api/water-logs", json={
        "user_id": user_id,
        "amount_ml": 250.0
    })
    assert log2.status_code == 201
    log2_id = log2.json()["id"]

    # Get today's water summary
    today_res = client.get(f"/api/water-logs/today/{user_id}")
    assert today_res.status_code == 200
    today_data = today_res.json()
    assert today_data["total_ml"] == 750.0
    assert len(today_data["logs"]) == 2

    # Get water history
    hist_res = client.get(f"/api/water-logs/history/{user_id}")
    assert hist_res.status_code == 200
    assert len(hist_res.json()["history"]) >= 1

    # Delete first water log
    del_res = client.delete(f"/api/water-logs/{log1_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "success"

    # Verify updated today total
    today_res_after = client.get(f"/api/water-logs/today/{user_id}")
    assert today_res_after.json()["total_ml"] == 250.0


# -------------------------------------------------------------
# 4. Dynamic Weight Tracking & Log Deletion
# -------------------------------------------------------------
def test_dynamic_weight_tracking_and_deletion():
    email = unique_email("weight_user")
    reg = client.post("/api/auth/register", json={
        "name": "Weight Dynamic",
        "email": email,
        "password": "password123",
        "age": 30,
        "gender": "male",
        "height": 180.0,
        "weight": 85.0,
        "activity_level": "sedentary"
    })
    assert reg.status_code == 201
    user_id = reg.json()["user"]["id"]

    # Log new weight of 80.0 kg
    track_res = client.post("/track-weight", json={
        "user_id": user_id,
        "weight": 80.0,
        "logged_at": "2026-08-27",
        "adherence": True
    })
    assert track_res.status_code == 200
    data = track_res.json()
    assert data["weight_logged"]["weight"] == 80.0
    assert data["user_profile"]["weight"] == 80.0
    # Water target updated dynamically: 80 * 35 = 2800 ml
    assert data["user_profile"]["water_target_ml"] == 2800.0

    # Retrieve weight history
    hist_res = client.get(f"/users/{user_id}/weight-history")
    assert hist_res.status_code == 200
    logs = hist_res.json()
    assert len(logs) >= 1
    log_id = logs[0]["id"]

    # Delete weight log
    del_res = client.delete(f"/api/weight-logs/{log_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "success"


# -------------------------------------------------------------
# 5. OCR Engine Parsing (kJ to kcal, multi-macro extraction)
# -------------------------------------------------------------
def test_ocr_engine_parsing():
    sample_text = """
    NUTRITION INFORMATION
    Serving Size: 100g
    Energy: 836.8 kJ (200 kcal)
    Protein: 15.5 g
    Total Carbohydrate: 22.0 g
    Sugars: 3.2 g
    Dietary Fiber: 4.5 g
    Total Fat: 8.0 g
    Saturated Fat: 2.1 g
    Sodium: 450 mg
    """
    parsed = OCREngine.parse_nutrition_text(sample_text)
    assert parsed["energy_kcal"] == 200.0
    assert parsed["protein_g"] == 15.5
    assert parsed["carb_g"] == 22.0
    assert parsed["fat_g"] == 8.0
    assert parsed["saturated_fat_g"] == 2.1
    assert parsed["fibre_g"] == 4.5
    assert parsed["sugar_g"] == 3.2
    assert parsed["sodium_mg"] == 450.0
    assert "100" in str(parsed["serving_size"])


# -------------------------------------------------------------
# 6. Homely Meals Approval Logic & Creator Isolation
# -------------------------------------------------------------
def test_homely_meals_creator_auto_approval():
    email = unique_email("homely_chef")
    reg = client.post("/api/auth/register", json={
        "name": "Homely Chef",
        "email": email,
        "password": "password123",
        "age": 28,
        "gender": "male",
        "height": 170.0,
        "weight": 70.0
    })
    assert reg.status_code == 201
    creator_id = reg.json()["user"]["id"]

    # 1. Private meal is automatically approved
    private_meal = client.post("/api/homely-meals/create", json={
        "name": "Secret Family Khichdi",
        "creator_id": creator_id,
        "is_community": False,
        "cuisine": "Gujarati",
        "ingredients": [
            {"ingredient_name": "Moong Dal", "amount": 100.0, "unit": "grams"},
            {"ingredient_name": "Rice", "amount": 100.0, "unit": "grams"}
        ]
    })
    assert private_meal.status_code == 200
    assert private_meal.json()["status"] == "approved"

    # 2. Community meal is pending
    comm_meal = client.post("/api/homely-meals/create", json={
        "name": "Community Special Poha",
        "creator_id": creator_id,
        "is_community": True,
        "cuisine": "Maharashtrian",
        "ingredients": [
            {"ingredient_name": "Poha", "amount": 100.0, "unit": "grams"}
        ]
    })
    assert comm_meal.status_code == 200
    assert comm_meal.json()["status"] == "pending"

    # 3. Pending moderation list when excluding creator does not show creator's own meal
    pending_res = client.get(f"/api/homely-meals/pending?exclude_creator_id={creator_id}")
    assert pending_res.status_code == 200
    pending_list = pending_res.json()
    for item in pending_list:
        assert item["creator_id"] != creator_id

    # Teardown / cleanup created test meals
    from app.db import SessionLocal
    from app.models import HomelyMeal, HomelyMealIngredient, HomelyMealNutrition
    db = SessionLocal()
    try:
        test_meals = db.query(HomelyMeal).filter(HomelyMeal.creator_id == creator_id).all()
        for m in test_meals:
            db.query(HomelyMealIngredient).filter(HomelyMealIngredient.meal_id == m.id).delete()
            db.query(HomelyMealNutrition).filter(HomelyMealNutrition.meal_id == m.id).delete()
            db.delete(m)
        db.commit()
    finally:
        db.close()


# -------------------------------------------------------------
# 7. Meal Optimizer Feasibility Across Cuisines
# -------------------------------------------------------------
def test_optimization_engine_feasibility():
    email = unique_email("optimizer_user")
    reg = client.post("/api/auth/register", json={
        "name": "Optimizer User",
        "email": email,
        "password": "password123",
        "age": 26,
        "gender": "male",
        "height": 178.0,
        "weight": 72.0,
        "activity_level": "moderately_active",
        "goal": "maintenance",
        "preferences": [{"preference_type": "diet_type", "value": "Vegetarian"}]
    })
    assert reg.status_code == 201
    user_id = reg.json()["user"]["id"]

    # Generate meal plan with specific slot cuisines
    plan_res = client.post("/generate-meal-plan", json={
        "user_id": user_id,
        "preference": "balanced",
        "tolerance": 0.20,
        "meal_cuisines": {
            "Breakfast": "South Indian",
            "Lunch": "North Indian",
            "Dinner": "North Indian",
            "Snack": "Gujarati"
        }
    })
    assert plan_res.status_code == 200
    plan_data = plan_res.json()
    assert "meals" in plan_data
    assert "Breakfast" in plan_data["meals"]
    assert "Lunch" in plan_data["meals"]
    assert "Dinner" in plan_data["meals"]
    assert "Snack" in plan_data["meals"]
    assert plan_data["totals"]["calories"] > 0
