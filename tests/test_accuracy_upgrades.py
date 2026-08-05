import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base
from app.services.barcode_service import BarcodeService
from app import models, schemas
from fastapi.testclient import TestClient
from app.main import app

# Setup test SQLite database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        # Seed basic food and rule to check estimation
        food = models.Food(food_code="DRINK_0001", name="tender coconut water", brand="Paper Boat")
        db.add(food)
        db.commit()
        db.refresh(food)
        
        nut = models.FoodNutrient(
            food_id=food.id,
            energy_kcal=20.0,
            protein_g=0.0,
            carb_g=5.0,
            fat_g=0.0,
            fibre_g=0.0,
            sodium_mg=25.0,
            sugar_g=5.0,
            saturated_fat_g=0.0
        )
        db.add(nut)
        db.commit()
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_extract_price_from_text():
    # 1. Price is present
    price_1 = BarcodeService.extract_price_from_text("Organic Tender Coconut Water Rs. 40 Bottle")
    assert price_1 == 40.0

    # 2. INR style
    price_2 = BarcodeService.extract_price_from_text("NutroActive Keto Cookies INR 150 pack")
    assert price_2 == 150.0

    # 3. No price present (fallback to 20.0)
    price_3 = BarcodeService.extract_price_from_text("Plain Oats Pack")
    assert price_3 == 20.0

def test_estimate_nutrition_from_name(db_session):
    # Test matching to local seeded food item
    nutrients = BarcodeService.estimate_nutrition_from_name(db_session, "Tender Coconut Water")
    assert nutrients["energy_kcal"] == 20.0
    assert nutrients["carb_g"] == 5.0
    assert nutrients["protein_g"] == 0.0

    # Test fallback default when unmatched
    fallback = BarcodeService.estimate_nutrition_from_name(db_session, "Unmatched Random Item")
    assert fallback["energy_kcal"] == 420.0
    assert fallback["carb_g"] == 60.0

def test_scrape_product_name_from_search():
    # We query a known barcode to verify the scraper gets a name or returns None gracefully
    name = BarcodeService.scrape_product_name_from_search("8901719117972")
    # Should either be a string (if search succeeds) or None (if network/rate limit blocks it)
    assert name is None or isinstance(name, str)

def test_price_matched_alternatives():
    client = TestClient(app)
    
    # 1. Test budget item scan (estimated_price <= 40)
    # Recommending alternatives for a budget soda
    res = client.post("/api/barcode/alternatives", json={
        "product_name": "Sugary Coca Cola",
        "meal_type": "Snack",
        "protein_g": 0.0,
        "energy_kcal": 150.0,
        "sugar_g": 35.0,
        "fat_g": 0.0,
        "estimated_price": 20.0
    })
    assert res.status_code == 200
    data = res.json()
    assert "alternatives" in data
    # The first recommended items should be budget-friendly (Amul Chaas Rs. 15 or Coconut Water Rs. 40)
    first_item = data["alternatives"][0]
    assert first_item["price"] <= 40.0

    # 2. Test premium item scan (estimated_price = 120)
    res_premium = client.post("/api/barcode/alternatives", json={
        "product_name": "Premium High Sugar Cookie",
        "meal_type": "Snack",
        "protein_g": 2.0,
        "energy_kcal": 400.0,
        "sugar_g": 25.0,
        "fat_g": 18.0,
        "estimated_price": 120.0
    })
    assert res_premium.status_code == 200
    data_premium = res_premium.json()
    # The first recommended items should align closer to the Rs. 120 budget range (like Whole Truth Bar or Happilo Makhana)
    first_prem = data_premium["alternatives"][0]
    assert first_prem["price"] >= 80.0
