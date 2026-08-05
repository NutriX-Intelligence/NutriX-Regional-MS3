import os
import httpx
import json
import re
import urllib.parse
from sqlalchemy.orm import Session
from app.models import BarcodeCache, Food
from app.services.health_scorer import HealthScorer

class BarcodeService:
    API_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"

    @classmethod
    def is_valid_nutrients(cls, nutrients: dict) -> bool:
        """Check if a nutrient dictionary contains realistic non-zero macro/caloric values."""
        if not nutrients or not isinstance(nutrients, dict):
            return False
        cal = float(nutrients.get("energy_kcal", 0.0) or 0.0)
        p = float(nutrients.get("protein_g", 0.0) or 0.0)
        c = float(nutrients.get("carb_g", 0.0) or 0.0)
        f = float(nutrients.get("fat_g", 0.0) or 0.0)
        return (cal > 0.0 or (p + c + f) > 0.0)

    @classmethod
    def scrape_product_name_from_search(cls, barcode: str) -> str:
        """Query DuckDuckGo HTML search for the barcode to identify product name and brand."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(barcode)}"
        try:
            res = httpx.get(url, headers=headers, timeout=8.0)
            if res.status_code == 200:
                html = res.text
                titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html)
                for t in titles:
                    clean_t = re.sub(r'<[^>]+>', '', t).strip()
                    # Filter out search indexing portals to get genuine product title matches
                    if len(clean_t) > 10 and not any(k in clean_t.lower() for k in ["upcitemdb", "barcodelookup", "search", "barcodedatabase", "findproduct", "go-upc"]):
                        # Clean up suffixes like " - BigBasket", " - Grofers", etc.
                        clean_t = re.sub(r'\s*-\s*(?:BigBasket|Amazon|iHerb|Grofers|Flipkart|JioMart|Blinkit).*$', '', clean_t, flags=re.IGNORECASE)
                        # Clean up prefix like "Digit-Eyes UPC data: "
                        clean_t = re.sub(r'^Digit-Eyes\s+UPC\s+data:\s*\d+\s*UPC\s*', '', clean_t, flags=re.IGNORECASE)
                        return clean_t
        except Exception:
            pass
        return None

    @classmethod
    def extract_price_from_text(cls, text: str) -> float:
        """Parse estimated retail price in INR from title snippets if available."""
        price_match = re.search(r'(?:Rs\.?|INR)\s*(\d+)', text, re.IGNORECASE)
        if price_match:
            return float(price_match.group(1))
        return 20.0  # default fallback estimated price in INR

    @classmethod
    def estimate_nutrition_from_gemini(cls, product_name: str, barcode: str = "") -> dict:
        """Query Google Gemini API (if GEMINI_API_KEY / GEMINI_3_6_API_KEY is present) to estimate realistic per-100g nutrients."""
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_3_6_API_KEY") or os.environ.get("GEMINI_API_KEY_1")
        if not api_key:
            return None

        prompt = f"""
You are a expert nutrition database parser.
Estimate realistic per-100g nutritional composition for packaged food item: '{product_name}' (Barcode: {barcode}).
Return ONLY a valid JSON object without markdown or code formatting:
{{
  "energy_kcal": 420.0,
  "protein_g": 6.5,
  "carb_g": 64.0,
  "fat_g": 18.0,
  "fibre_g": 2.5,
  "sodium_mg": 700.0,
  "sugar_g": 4.0,
  "saturated_fat_g": 7.5,
  "brand": "Brand Name",
  "ingredients_text": "Corn meal, edible vegetable oil, seasoning spices, salt"
}}
"""
        models_to_try = [
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-2.5-flash",
            "gemini-1.5-pro"
        ]

        for model in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                res = httpx.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=8.0)
                if res.status_code == 200:
                    res_json = res.json()
                    candidates = res_json.get("candidates", [])
                    if candidates:
                        raw_text = candidates[0]["content"]["parts"][0]["text"]
                        clean_json = re.sub(r'^```(?:json)?\s*', '', raw_text.strip(), flags=re.IGNORECASE)
                        clean_json = re.sub(r'\s*```$', '', clean_json)
                        parsed = json.loads(clean_json)
                        
                        nutrients = {
                            "energy_kcal": float(parsed.get("energy_kcal", 0.0)),
                            "protein_g": float(parsed.get("protein_g", 0.0)),
                            "carb_g": float(parsed.get("carb_g", 0.0)),
                            "fat_g": float(parsed.get("fat_g", 0.0)),
                            "fibre_g": float(parsed.get("fibre_g", 0.0)),
                            "sodium_mg": float(parsed.get("sodium_mg", 0.0)),
                            "sugar_g": float(parsed.get("sugar_g", 0.0)),
                            "saturated_fat_g": float(parsed.get("saturated_fat_g", 0.0)),
                            "brand": parsed.get("brand") or "Estimated Brand",
                            "ingredients_text": parsed.get("ingredients_text") or "Ingredients estimated via Gemini AI"
                        }
                        if cls.is_valid_nutrients(nutrients):
                            return nutrients
            except Exception:
                continue
        return None

    @classmethod
    def estimate_nutrition_from_name(cls, db: Session, product_name: str) -> dict:
        """Match product name against local master food database to estimate nutritional composition."""
        from app.services.homely_meals_engine import match_food_item
        matched_food = match_food_item(db, product_name)
        if matched_food and matched_food.nutrients:
            fn = matched_food.nutrients
            nut = {
                "energy_kcal": float(fn.energy_kcal or 0.0),
                "protein_g": float(fn.protein_g or 0.0),
                "carb_g": float(fn.carb_g or 0.0),
                "fat_g": float(fn.fat_g or 0.0),
                "fibre_g": float(fn.fibre_g or 0.0),
                "sodium_mg": float(fn.sodium_mg or 0.0),
                "sugar_g": float(fn.sugar_g or 0.0),
                "saturated_fat_g": float(fn.saturated_fat_g or 0.0)
            }
            if cls.is_valid_nutrients(nut):
                return nut

        # General packaged snack default fallback if matching fails
        return {
            "energy_kcal": 420.0,
            "protein_g": 5.5,
            "carb_g": 60.0,
            "fat_g": 18.0,
            "fibre_g": 2.0,
            "sodium_mg": 680.0,
            "sugar_g": 3.5,
            "saturated_fat_g": 6.5
        }

    @classmethod
    def get_product(cls, db: Session, barcode: str) -> dict:
        """Get product info for barcode utilizing 4-tier fallback:
        Tier 1: Open Food Facts (OFF API)
        Tier 2: DuckDuckGo Web Search Scraper (Title extraction)
        Tier 3: Google Gemini AI (Per-100g macro estimation)
        Tier 4: Local Master DB Standardization
        """
        barcode = str(barcode).strip()
        if not barcode:
            return {"status": "error", "message": "Barcode cannot be empty"}

        # 1. Check local cache (ignore stale 0-nutrient cache entries)
        cached = db.query(BarcodeCache).filter(BarcodeCache.barcode == barcode).first()
        if cached and cached.nutriments_json:
            cached_nut = json.loads(cached.nutriments_json)
            if cls.is_valid_nutrients(cached_nut):
                source_det = getattr(cached, "source_detail", None) or "Local Cache (Verified)"
                return {
                    "status": "success",
                    "source": "cache",
                    "source_detail": source_det,
                    "barcode": cached.barcode,
                    "product_name": cached.product_name,
                    "brand": cached.brand,
                    "ingredients_text": cached.ingredients_text,
                    "nutrition_grade": cached.nutrition_grade,
                    "health_score": cached.health_score,
                    "health_category": cached.health_category,
                    "nutriments": cached_nut
                }
            else:
                # Evict bad zero-nutrient cache entry to allow full fallback execution
                db.delete(cached)
                db.commit()

        product_name = None
        brand = "Unknown Brand"
        ingredients_text = "No ingredients listed"
        nutrition_grade = "unknown"
        nutrients_100g = None
        source_name = "api"
        source_detail = "Open Food Facts API"

        # Tier 1: Fetch from Open Food Facts API
        url = cls.API_URL.format(barcode=barcode)
        headers = {"User-Agent": "NutriX/1.0.0 (FastAPI Backend)"}
        
        try:
            res = httpx.get(url, headers=headers, timeout=5.0)
            if res.status_code == 200:
                data = res.json()
                if data.get("status") == 1:
                    product = data.get("product", {})
                    p_name = product.get("product_name") or product.get("product_name_en")
                    if p_name and len(p_name.strip()) > 2 and not p_name.lower().startswith("digit-eyes"):
                        product_name = p_name.strip()
                    brand = product.get("brands") or "Unknown Brand"
                    ingredients_text = product.get("ingredients_text") or "No ingredients listed"
                    nutrition_grade = product.get("nutrition_grades") or "unknown"
                    
                    nutriments = product.get("nutriments", {})
                    off_nutrients = {
                        "energy_kcal": float(nutriments.get("energy-kcal_100g") or nutriments.get("energy-kcal") or 0.0),
                        "protein_g": float(nutriments.get("proteins_100g") or 0.0),
                        "carb_g": float(nutriments.get("carbohydrates_100g") or 0.0),
                        "fat_g": float(nutriments.get("fat_100g") or 0.0),
                        "fibre_g": float(nutriments.get("fiber_100g") or 0.0),
                        "sodium_mg": float(nutriments.get("sodium_100g") or 0.0) * 1000.0,
                        "sugar_g": float(nutriments.get("sugars_100g") or 0.0),
                        "saturated_fat_g": float(nutriments.get("saturated-fat_100g") or 0.0),
                        "estimated_price": 40.0
                    }
                    if cls.is_valid_nutrients(off_nutrients):
                        nutrients_100g = off_nutrients
                        source_detail = "Open Food Facts API"
        except Exception:
            pass

        # Tier 2: DuckDuckGo Web Search Scraper (if product name is missing)
        if not product_name:
            fallback_name = cls.scrape_product_name_from_search(barcode)
            if fallback_name:
                product_name = fallback_name
                brand_match = re.match(r"^([A-Za-z0-9]+)\b", product_name)
                if brand_match:
                    brand = brand_match.group(1)

        # If product name is still completely missing, default fallback title
        if not product_name:
            product_name = f"Packaged Food Item #{barcode}"

        # Tier 3: Gemini AI API (If OFF nutrients were missing or 0)
        if not cls.is_valid_nutrients(nutrients_100g):
            gemini_result = cls.estimate_nutrition_from_gemini(product_name, barcode)
            if gemini_result and cls.is_valid_nutrients(gemini_result):
                nutrients_100g = gemini_result
                if gemini_result.get("brand") and brand == "Unknown Brand":
                    brand = gemini_result["brand"]
                if gemini_result.get("ingredients_text") and ingredients_text == "No ingredients listed":
                    ingredients_text = gemini_result["ingredients_text"]
                source_name = "gemini_ai"
                source_detail = "DuckDuckGo Scraper + Gemini AI (3.6/Flash)"

        # Tier 4: Local Master DB Standardization (If Gemini AI key is missing or failed)
        if not cls.is_valid_nutrients(nutrients_100g):
            nutrients_100g = cls.estimate_nutrition_from_name(db, product_name)
            price = cls.extract_price_from_text(product_name)
            nutrients_100g["estimated_price"] = price
            source_name = "web_search"
            source_detail = "DuckDuckGo Scraper + Local Master DB"

        # Calculate Health Score
        score, category, explanation = HealthScorer.score_from_nutrition_dict(nutrients_100g)
        
        # Save to Barcode Cache
        try:
            new_cache = BarcodeCache(
                barcode=barcode,
                product_name=product_name,
                brand=brand,
                ingredients_text=ingredients_text,
                nutrition_grade=nutrition_grade if nutrition_grade != "unknown" else (category[0].lower() if category else "m"),
                nutriments_json=json.dumps(nutrients_100g),
                health_score=score,
                health_category=category,
                source_detail=source_detail
            )
            db.add(new_cache)
            db.commit()
        except Exception:
            db.rollback()

        return {
            "status": "success",
            "source": source_name,
            "source_detail": source_detail,
            "barcode": barcode,
            "product_name": product_name,
            "brand": brand,
            "ingredients_text": ingredients_text,
            "nutrition_grade": nutrition_grade,
            "health_score": score,
            "health_category": category,
            "explanation": explanation,
            "nutriments": nutrients_100g
        }
