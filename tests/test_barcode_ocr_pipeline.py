import pytest
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from datetime import date

from app.main import app
from app.db import get_db, Base, engine
from app.models import User, Profile, BarcodeCache, MealLog
from app.services.barcode_service import BarcodeService
from app.services.ocr_engine import OCREngine


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    from app.db import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TestBarcodeLookupPipeline:
    """Test 4-tier barcode lookup pipeline: Cache -> OpenFoodFacts -> Web Scraper -> Gemini."""

    def test_tier_1_curated_fmcg_cache(self, client, db_session):
        """Tier 1: High accuracy curated Indian FMCG database (Maggi, Amul Butter, Lay's)."""
        res = client.get("/api/barcode/8901058852712")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "Maggi" in data["product_name"]
        assert data["brand"] == "Nestlé"
        assert data["nutriments"]["energy_kcal"] > 0
        assert data["nutriments"]["protein_g"] > 0
        assert "source" in data

        # Verify it is now saved in BarcodeCache table
        cached = db_session.query(BarcodeCache).filter(BarcodeCache.barcode == "8901058852712").first()
        assert cached is not None
        assert "Maggi" in cached.product_name

    def test_tier_1_database_cache_hit(self, client, db_session):
        """Tier 1: Direct database cache retrieval for pre-existing records."""
        test_barcode = "9998887776665"
        dummy_nutrients = {
            "energy_kcal": 350.0,
            "protein_g": 10.0,
            "carb_g": 50.0,
            "fat_g": 12.0,
            "fibre_g": 4.0,
            "sodium_mg": 400.0,
            "sugar_g": 5.0,
            "saturated_fat_g": 3.0
        }
        # Insert test item directly to DB cache
        db_cache = BarcodeCache(
            barcode=test_barcode,
            product_name="Test Organic Granola",
            brand="Nature Valley",
            ingredients_text="Rolled oats, almonds, honey",
            nutrition_grade="b",
            nutriments_json=json.dumps(dummy_nutrients),
            health_score=75.0,
            health_category="Healthy",
            source_detail="Local Database Cache (Verified)"
        )
        db_session.merge(db_cache)
        db_session.commit()

        res = client.get(f"/api/barcode/{test_barcode}")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["source"] == "cache"
        assert data["product_name"] == "Test Organic Granola"
        assert data["nutriments"]["energy_kcal"] == 350.0

    @patch("httpx.get")
    def test_tier_2_open_food_facts_api(self, mock_get, client, db_session):
        """Tier 2: Open Food Facts API fetches genuine product data."""
        test_bc = "3017620422003"
        # Delete if in cache
        db_session.query(BarcodeCache).filter(BarcodeCache.barcode == test_bc).delete()
        db_session.commit()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": 1,
            "product": {
                "product_name": "Nutella Ferrero 400g",
                "brands": "Ferrero",
                "ingredients_text": "Sugar, palm oil, hazelnuts (13%), skimmed milk powder",
                "nutrition_grades": "e",
                "nutriments": {
                    "energy-kcal_100g": 539.0,
                    "proteins_100g": 6.3,
                    "carbohydrates_100g": 57.5,
                    "fat_100g": 30.9,
                    "fiber_100g": 3.0,
                    "sodium_100g": 0.042,
                    "sugars_100g": 56.3,
                    "saturated-fat_100g": 10.6
                }
            }
        }
        mock_get.return_value = mock_resp

        res = client.get(f"/api/barcode/{test_bc}")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "Nutella" in data["product_name"]
        assert data["nutriments"]["energy_kcal"] == 539.0

    @patch.object(BarcodeService, "fetch_from_open_food_facts", return_value=None)
    @patch.object(BarcodeService, "scrape_product_name_from_search")
    @patch.object(BarcodeService, "estimate_nutrition_from_gemini")
    def test_tier_3_and_4_scraper_and_gemini(self, mock_gemini, mock_scraper, mock_off, client, db_session):
        """Tier 3 & 4: Scraper discovers product name, and Gemini API estimates accurate nutrition."""
        test_bc = "8909876543210"
        db_session.query(BarcodeCache).filter(BarcodeCache.barcode == test_bc).delete()
        db_session.commit()

        mock_scraper.return_value = {
            "product_name": "Sunfeast Dark Fantasy Choco Fills",
            "brand": "Sunfeast",
            "estimated_price": 40.0
        }
        mock_gemini.return_value = {
            "energy_kcal": 512.0,
            "protein_g": 5.5,
            "carb_g": 65.0,
            "fat_g": 26.0,
            "fibre_g": 2.0,
            "sodium_mg": 220.0,
            "sugar_g": 38.0,
            "saturated_fat_g": 12.0,
            "estimated_price": 40.0,
            "product_name": "Sunfeast Dark Fantasy Choco Fills",
            "brand": "Sunfeast",
            "ingredients_text": "Choco crème, wheat flour, hydrogenated vegetable oil, sugar",
            "nutrition_grade": "e"
        }

        res = client.get(f"/api/barcode/{test_bc}")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["source"] == "gemini_ai"
        assert "Dark Fantasy" in data["product_name"]
        assert data["nutriments"]["energy_kcal"] == 512.0


class TestHealthierDietaryAlternatives:
    """Test dietitian-approved alternative swaps tailored strictly to user's diet preferences."""

    def test_jain_diet_alternatives(self):
        """Jain diet must exclude onion, garlic, potato, and root vegetables from food product name."""
        alts = BarcodeService.get_healthier_alternatives("Maggi Masala Instant Noodles", "Snack", diet_type="Jain")
        assert len(alts) > 0
        for alt in alts:
            assert "jain" in alt.get("diet_badge", "").lower()
            name_lower = alt["name"].lower()
            assert "onion" not in name_lower
            assert "garlic" not in name_lower
            assert "potato" not in name_lower

    def test_vegan_diet_alternatives(self):
        """Vegan diet must exclude dairy, butter, cheese, eggs, and animal products from food product name."""
        alts = BarcodeService.get_healthier_alternatives("Amul Butter", "Snack", diet_type="Vegan")
        assert len(alts) > 0
        for alt in alts:
            assert "vegan" in alt.get("diet_badge", "").lower() or "plant-based" in alt.get("diet_badge", "").lower()
            name_lower = alt["name"].lower()
            assert "egg" not in name_lower
            assert "meat" not in name_lower
            assert "chicken" not in name_lower

    def test_keto_diet_alternatives(self):
        """Keto diet must provide ultra low net carb swaps."""
        alts = BarcodeService.get_healthier_alternatives("Lay's Potato Chips", "Snack", diet_type="Keto")
        assert len(alts) > 0
        for alt in alts:
            assert "keto" in alt.get("diet_badge", "").lower()

    def test_barcode_lookup_with_user_profile_diet(self, client, db_session):
        """Barcode lookup endpoint honors user's profile diet type."""
        # Create user with Jain diet
        profile_res = client.post("/calculate-profile", json={
            "name": "Jain User",
            "email": "jain@example.com",
            "age": 28,
            "gender": "male",
            "height": 172.0,
            "weight": 68.0,
            "activity_level": "sedentary",
            "goal": "maintenance",
            "preferences": [{"preference_type": "diet_type", "value": "Jain"}]
        })
        assert profile_res.status_code == 201
        u_id = profile_res.json()["id"]

        res = client.get(f"/api/barcode/8901058852712?user_id={u_id}")
        assert res.status_code == 200
        data = res.json()
        assert len(data["alternatives"]) > 0
        # First alternative should have Jain badge
        assert "Jain" in data["alternatives"][0]["diet_badge"]


class TestMealLoggingAndProfileReflection:
    """Test that logging a meal reflects on the user's Profile & Nutrition diary immediately."""

    def test_meal_logging_string_date_parsing(self, client):
        """Ensure string date from client (YYYY-MM-DD) is accepted and parsed without SQLite StatementError."""
        # Create user
        p_res = client.post("/calculate-profile", json={
            "name": "Diary User",
            "email": "diary@example.com",
            "age": 25,
            "gender": "female",
            "height": 165.0,
            "weight": 58.0,
            "activity_level": "lightly_active",
            "goal": "fat loss",
            "preferences": [{"preference_type": "diet_type", "value": "Vegetarian"}]
        })
        user_id = p_res.json()["id"]

        # Log food with string date
        log_date_str = date.today().isoformat()
        meal_res = client.post("/api/meal-logs", json={
            "user_id": user_id,
            "log_date": log_date_str,
            "meal_type": "Snack",
            "food_name": "Maggi 2-Minute Noodles (100g)",
            "calories": 427.0,
            "protein": 8.0,
            "carbs": 63.5,
            "fat": 15.7
        })
        assert meal_res.status_code == 201
        log_id = meal_res.json()["id"]

        # Verify today's meal logs endpoint returns the logged food
        today_res = client.get(f"/api/meal-logs/today/{user_id}?log_date={log_date_str}")
        assert today_res.status_code == 200
        today_data = today_res.json()
        assert today_data["totals"]["calories"] == 427.0
        assert today_data["totals"]["protein"] == 8.0
        assert len(today_data["logs"]) == 1
        assert "Maggi" in today_data["logs"][0]["food_name"]

        # Delete log
        del_res = client.delete(f"/api/meal-logs/{log_id}")
        assert del_res.status_code == 200


class TestDualBarcodeAndOCRImageUpload:
    """Test image upload endpoint (/api/barcode/scan-image) for dual barcode and OCR detection."""

    @patch.object(BarcodeService, "detect_barcode_from_image", return_value="8901058852712")
    def test_scan_image_barcode_detected(self, mock_detect, client):
        """When barcode is visible in the photo, return product intelligence."""
        dummy_img_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
        files = {"file": ("product.jpg", dummy_img_bytes, "image/jpeg")}
        data = {"diet_type": "Vegetarian"}

        res = client.post("/api/barcode/scan-image", files=files, data=data)
        assert res.status_code == 200
        res_json = res.json()
        assert res_json["type"] in ["barcode", "dual"]
        assert res_json["barcode"] == "8901058852712"
        assert "Maggi" in res_json["product"]["product_name"]

    @patch.object(BarcodeService, "detect_barcode_from_image", return_value=None)
    @patch.object(OCREngine, "parse_label_image")
    def test_scan_image_ocr_fallback(self, mock_ocr, mock_detect, client):
        """When no barcode is visible but a nutrition facts label is present, return OCR facts."""
        mock_ocr.return_value = {
            "status": "success",
            "detected_text": "Nutrition Facts\nCalories 250\nProtein 15g\nTotal Fat 5g",
            "nutrients": {
                "energy_kcal": 250.0,
                "protein_g": 15.0,
                "carb_g": 35.0,
                "fat_g": 5.0,
                "serving_size": "100g"
            }
        }

        dummy_img_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
        files = {"file": ("label.jpg", dummy_img_bytes, "image/jpeg")}

        res = client.post("/api/barcode/scan-image", files=files)
        assert res.status_code == 200
        res_json = res.json()
        assert res_json["type"] == "ocr"
        assert res_json["ocr_result"]["nutrients"]["energy_kcal"] == 250.0
