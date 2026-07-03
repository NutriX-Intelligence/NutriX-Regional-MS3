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
    def estimate_nutrition_from_name(cls, db: Session, product_name: str) -> dict:
        """Match product name against our local foods table to estimate nutritional composition."""
        from app.services.homely_meals_engine import match_food_item
        matched_food = match_food_item(db, product_name)
        if matched_food and matched_food.nutrients:
            fn = matched_food.nutrients
            return {
                "energy_kcal": float(fn.energy_kcal or 0.0),
                "protein_g": float(fn.protein_g or 0.0),
                "carb_g": float(fn.carb_g or 0.0),
                "fat_g": float(fn.fat_g or 0.0),
                "fibre_g": float(fn.fibre_g or 0.0),
                "sodium_mg": float(fn.sodium_mg or 0.0),
                "sugar_g": float(fn.sugar_g or 0.0),
                "saturated_fat_g": float(fn.saturated_fat_g or 0.0)
            }
        return {
            "energy_kcal": 120.0,
            "protein_g": 2.0,
            "carb_g": 18.0,
            "fat_g": 4.0,
            "fibre_g": 1.0,
            "sodium_mg": 150.0,
            "sugar_g": 3.0,
            "saturated_fat_g": 0.8
        }

    @classmethod
    def get_product(cls, db: Session, barcode: str) -> dict:
        """Get product information for a given barcode, utilizing caching and fetching from OFF API if needed.
        
        Returns:
            Dict containing product details or error.
        """
        barcode = str(barcode).strip()
        if not barcode:
            return {"status": "error", "message": "Barcode cannot be empty"}

        # 1. Check local cache
        cached = db.query(BarcodeCache).filter(BarcodeCache.barcode == barcode).first()
        if cached:
            return {
                "status": "success",
                "source": "cache",
                "barcode": cached.barcode,
                "product_name": cached.product_name,
                "brand": cached.brand,
                "ingredients_text": cached.ingredients_text,
                "nutrition_grade": cached.nutrition_grade,
                "health_score": cached.health_score,
                "health_category": cached.health_category,
                "nutriments": json.loads(cached.nutriments_json) if cached.nutriments_json else {}
            }

        # 2. Fetch from Open Food Facts API (if online)
        url = cls.API_URL.format(barcode=barcode)
        headers = {"User-Agent": "NutriX/1.0.0 (FastAPI Backend)"}
        
        try:
            res = httpx.get(url, headers=headers, timeout=5.0)
            if res.status_code == 200:
                data = res.json()
                if data.get("status") == 1:
                    product = data.get("product", {})
                    product_name = product.get("product_name") or product.get("product_name_en") or "Unknown Product"
                    brand = product.get("brands") or "Unknown Brand"
                    ingredients_text = product.get("ingredients_text") or "No ingredients listed"
                    nutrition_grade = product.get("nutrition_grades") or "unknown"
                    
                    nutriments = product.get("nutriments", {})
                    nutrients_100g = {
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
                    score, category, explanation = HealthScorer.score_from_nutrition_dict(nutrients_100g)
                    
                    new_cache = BarcodeCache(
                        barcode=barcode,
                        product_name=product_name,
                        brand=brand,
                        ingredients_text=ingredients_text,
                        nutrition_grade=nutrition_grade,
                        nutriments_json=json.dumps(nutrients_100g),
                        health_score=score,
                        health_category=category
                    )
                    db.add(new_cache)
                    db.commit()

                    return {
                        "status": "success",
                        "source": "api",
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

            # If OFF API fails or returns 404, fall back to Google/DDG Web Search!
            fallback_name = cls.scrape_product_name_from_search(barcode)
            if fallback_name:
                brand = "Unknown Brand"
                brand_match = re.match(r"^([A-Za-z0-9]+)\b", fallback_name)
                if brand_match:
                    brand = brand_match.group(1)
                
                nutrients_100g = cls.estimate_nutrition_from_name(db, fallback_name)
                price = cls.extract_price_from_text(fallback_name)
                nutrients_100g["estimated_price"] = price
                
                score, category, explanation = HealthScorer.score_from_nutrition_dict(nutrients_100g)
                new_cache = BarcodeCache(
                    barcode=barcode,
                    product_name=fallback_name,
                    brand=brand,
                    ingredients_text="No ingredients listed (extracted via Web Search fallback)",
                    nutrition_grade=category[0].lower() if (category and len(category) > 0) else "unknown",
                    nutriments_json=json.dumps(nutrients_100g),
                    health_score=score,
                    health_category=category
                )
                db.add(new_cache)
                db.commit()

                return {
                    "status": "success",
                    "source": "web_search",
                    "barcode": barcode,
                    "product_name": fallback_name,
                    "brand": brand,
                    "ingredients_text": new_cache.ingredients_text,
                    "nutrition_grade": new_cache.nutrition_grade,
                    "health_score": score,
                    "health_category": category,
                    "explanation": explanation,
                    "nutriments": nutrients_100g
                }
            
            return {"status": "error", "message": "Product not found on Open Food Facts or Web Search"}

        except Exception as e:
            # Also catch any network exceptions and try the search scraper
            try:
                fallback_name = cls.scrape_product_name_from_search(barcode)
                if fallback_name:
                    brand = "Unknown Brand"
                    brand_match = re.match(r"^([A-Za-z0-9]+)\b", fallback_name)
                    if brand_match:
                        brand = brand_match.group(1)
                    
                    nutrients_100g = cls.estimate_nutrition_from_name(db, fallback_name)
                    price = cls.extract_price_from_text(fallback_name)
                    nutrients_100g["estimated_price"] = price
                    
                    score, category, explanation = HealthScorer.score_from_nutrition_dict(nutrients_100g)
                    new_cache = BarcodeCache(
                        barcode=barcode,
                        product_name=fallback_name,
                        brand=brand,
                        ingredients_text="No ingredients listed (extracted via Web Search fallback)",
                        nutrition_grade=category[0].lower() if (category and len(category) > 0) else "unknown",
                        nutriments_json=json.dumps(nutrients_100g),
                        health_score=score,
                        health_category=category
                    )
                    db.add(new_cache)
                    db.commit()

                    return {
                        "status": "success",
                        "source": "web_search",
                        "barcode": barcode,
                        "product_name": fallback_name,
                        "brand": brand,
                        "ingredients_text": new_cache.ingredients_text,
                        "nutrition_grade": new_cache.nutrition_grade,
                        "health_score": score,
                        "health_category": category,
                        "explanation": explanation,
                        "nutriments": nutrients_100g
                    }
            except Exception:
                pass
            return {
                "status": "error",
                "message": f"Error connecting to Open Food Facts API and Web Search fallback: {str(e)}"
            }

