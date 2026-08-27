import os
import httpx
import json
import re
import urllib.parse
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models import BarcodeCache, Food
from app.services.health_scorer import HealthScorer
from app.services.classification_engine import ClassificationEngine

class BarcodeService:
    API_URL_V2 = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
    API_URL_V0 = "https://world.openfoodfacts.org/api/v0/product/{barcode}.json"

    # Pre-curated high-accuracy database for top Indian & Global packaged FMCG foods
    KNOWN_POPULAR_BARCODES: Dict[str, Dict[str, Any]] = {
        "8901058852712": {
            "product_name": "Maggi 2-Minute Masala Instant Noodles",
            "brand": "Nestlé",
            "ingredients_text": "Wheat flour (Maida), Palm oil, Salt, Wheat gluten, Mineral (Calcium carbonate), Thickeners (508 & 412), Acidity regulators (501(i) & 500(i)), Humectant (451(i)), Masala tastemaker: Hydrolysed groundnut protein, Mixed spices (Onion powder, Coriander, Chili, Turmeric, Garlic, Cumin, Aniseed, Fenugreek, Ginger, Black pepper, Clove, Nutmeg, Cardamom), Noodle flour, Sugar, Edible starch, Palm oil, Caramel color (150d), Salt, Flavor enhancer (635)",
            "nutrition_grade": "d",
            "nutriments": {
                "energy_kcal": 427.0,
                "protein_g": 8.0,
                "carb_g": 63.5,
                "fat_g": 15.7,
                "fibre_g": 3.6,
                "sodium_mg": 1020.0,
                "sugar_g": 2.2,
                "saturated_fat_g": 6.8,
                "estimated_price": 14.0
            }
        },
        "8901058002476": {
            "product_name": "Maggi 2-Minute Masala Noodles (Single Pack)",
            "brand": "Nestlé",
            "ingredients_text": "Refined wheat flour (Maida), Palm oil, Iodised salt, Wheat gluten, Masala tastemaker spices (Onion, Garlic, Coriander, Turmeric, Chili), Hydrolysed peanut protein, Sugar, Edible starch",
            "nutrition_grade": "d",
            "nutriments": {
                "energy_kcal": 427.0,
                "protein_g": 8.0,
                "carb_g": 63.5,
                "fat_g": 15.7,
                "fibre_g": 3.6,
                "sodium_mg": 1020.0,
                "sugar_g": 2.2,
                "saturated_fat_g": 6.8,
                "estimated_price": 14.0
            }
        },
        "8901262010052": {
            "product_name": "Amul Pasteurized Butter",
            "brand": "Amul",
            "ingredients_text": "Butter (Milk fat 80%), Common salt, Saturated fat, Permitted natural color (Annatto)",
            "nutrition_grade": "e",
            "nutriments": {
                "energy_kcal": 722.0,
                "protein_g": 0.5,
                "carb_g": 0.0,
                "fat_g": 80.0,
                "fibre_g": 0.0,
                "sodium_mg": 830.0,
                "sugar_g": 0.0,
                "saturated_fat_g": 51.0,
                "estimated_price": 56.0
            }
        },
        "8901719101037": {
            "product_name": "Parle-G Original Gluco Biscuits",
            "brand": "Parle",
            "ingredients_text": "Wheat flour (Maida 67%), Sugar, Edible vegetable oil (Palm oil), Invert sugar syrup, Leavening agents (503(ii), 500(ii)), Salt, Milk solids (0.6%), Emulsifiers (322, 471), Dough conditioner (223)",
            "nutrition_grade": "d",
            "nutriments": {
                "energy_kcal": 464.0,
                "protein_g": 6.5,
                "carb_g": 78.2,
                "fat_g": 14.0,
                "fibre_g": 2.0,
                "sodium_mg": 280.0,
                "sugar_g": 26.5,
                "saturated_fat_g": 6.5,
                "estimated_price": 10.0
            }
        },
        "8901491101835": {
            "product_name": "Lay's India's Magic Masala Potato Chips",
            "brand": "Lay's (PepsiCo)",
            "ingredients_text": "Potato, Edible vegetable oil (Palmolein), Seasoning (Spices & condiments, Onion powder, Chili powder, Dry mango powder, Coriander powder, Ginger powder, Garlic powder, Black pepper powder, Turmeric powder, Cumin powder), Salt, Black salt, Sugar, Tomato powder, Acidity regulator (330)",
            "nutrition_grade": "d",
            "nutriments": {
                "energy_kcal": 555.0,
                "protein_g": 6.9,
                "carb_g": 52.3,
                "fat_g": 35.5,
                "fibre_g": 4.1,
                "sodium_mg": 790.0,
                "sugar_g": 3.2,
                "saturated_fat_g": 14.8,
                "estimated_price": 20.0
            }
        },
        "8904063200143": {
            "product_name": "Haldiram's Nagpur Aloo Bhujia",
            "brand": "Haldiram's",
            "ingredients_text": "Potato flakes (22%), Edible vegetable oil (Cottonseed, Corn, Palmolein), Gram pulse flour (Besan 19%), Dew bean flour (Moth flour 12%), Tapioca starch, Spices & condiments (Red chili, Black pepper, Clove, Cardamom, Betel leaves, Cinnamon, Nutmeg, Mace, Ginger, Cumin, Bay leaf), Iodized salt, Mango powder",
            "nutrition_grade": "d",
            "nutriments": {
                "energy_kcal": 583.0,
                "protein_g": 9.2,
                "carb_g": 42.1,
                "fat_g": 42.0,
                "fibre_g": 3.8,
                "sodium_mg": 680.0,
                "sugar_g": 1.5,
                "saturated_fat_g": 13.5,
                "estimated_price": 45.0
            }
        },
        "8000500310427": {
            "product_name": "Nutella Hazelnut Spread with Cocoa",
            "brand": "Ferrero",
            "ingredients_text": "Sugar, Palm oil, Hazelnuts (13%), Skimmed milk powder (8.7%), Fat-reduced cocoa (7.4%), Emulsifier: lecithins (soya), Vanillin",
            "nutrition_grade": "e",
            "nutriments": {
                "energy_kcal": 539.0,
                "protein_g": 6.3,
                "carb_g": 57.5,
                "fat_g": 30.9,
                "fibre_g": 3.0,
                "sodium_mg": 42.0,
                "sugar_g": 56.3,
                "saturated_fat_g": 10.6,
                "estimated_price": 299.0
            }
        },
        "5449000000996": {
            "product_name": "Coca-Cola Original Taste",
            "brand": "Coca-Cola",
            "ingredients_text": "Carbonated water, Sugar, Color (Caramel E150d), Phosphoric acid, Natural flavorings (including caffeine)",
            "nutrition_grade": "e",
            "nutriments": {
                "energy_kcal": 44.0,
                "protein_g": 0.0,
                "carb_g": 10.6,
                "fat_g": 0.0,
                "fibre_g": 0.0,
                "sodium_mg": 4.0,
                "sugar_g": 10.6,
                "saturated_fat_g": 0.0,
                "estimated_price": 40.0
            }
        },
        "7622210449283": {
            "product_name": "Oreo Chocolate Sandwich Cookies",
            "brand": "Cadbury / Mondelēz",
            "ingredients_text": "Wheat flour, Sugar, Palm oil, Rapeseed oil, Fat-reduced cocoa powder 4.5%, Wheat starch, Glucose-fructose syrup, Raising agents (potassium carbonates, ammonium carbonates, sodium carbonates), Salt, Emulsifiers (soya lecithin, sunflower lecithin), Flavoring (vanillin)",
            "nutrition_grade": "e",
            "nutriments": {
                "energy_kcal": 474.0,
                "protein_g": 5.4,
                "carb_g": 68.0,
                "fat_g": 19.0,
                "fibre_g": 2.7,
                "sodium_mg": 296.0,
                "sugar_g": 38.0,
                "saturated_fat_g": 5.2,
                "estimated_price": 35.0
            }
        },
        "1234567890123": {
            "product_name": "NutriX High-Protein Multi-Grain Muesli",
            "brand": "NutriX Organic",
            "ingredients_text": "Rolled oats (40%), Roasted almonds (15%), Chia seeds (10%), Pumpkin seeds (10%), Raw honey, Dried blueberries, Pea protein isolate, Cinnamon",
            "nutrition_grade": "a",
            "nutriments": {
                "energy_kcal": 380.0,
                "protein_g": 22.0,
                "carb_g": 48.0,
                "fat_g": 11.0,
                "fibre_g": 9.5,
                "sodium_mg": 45.0,
                "sugar_g": 6.0,
                "saturated_fat_g": 1.8,
                "estimated_price": 180.0
            }
        }
    }

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
    def fetch_from_open_food_facts(cls, barcode: str) -> Optional[Dict[str, Any]]:
        """Tier 2: Fetch genuine product details from Open Food Facts API (v2 and v0)."""
        headers = {"User-Agent": "NutriX-Diet-Planner/1.0 (Nutrition Intelligence Platform)"}
        urls = [
            cls.API_URL_V2.format(barcode=barcode),
            cls.API_URL_V0.format(barcode=barcode)
        ]

        for url in urls:
            try:
                res = httpx.get(url, headers=headers, timeout=5.0)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("status") == 1:
                        product = data.get("product", {})
                        p_name = product.get("product_name") or product.get("product_name_en")
                        if p_name and len(p_name.strip()) > 2 and not p_name.lower().startswith("digit-eyes"):
                            p_name = p_name.strip()
                        else:
                            p_name = None

                        brand = product.get("brands") or product.get("brand_owner") or "Unknown Brand"
                        ingredients_text = product.get("ingredients_text") or product.get("ingredients_text_en") or "No ingredients listed"
                        nutrition_grade = product.get("nutrition_grades") or "unknown"
                        
                        nutriments = product.get("nutriments", {})
                        energy_val = float(nutriments.get("energy-kcal_100g") or nutriments.get("energy-kcal") or 0.0)
                        if energy_val == 0.0 and nutriments.get("energy_100g"):
                            # Energy in kJ to kcal
                            energy_val = round(float(nutriments.get("energy_100g")) / 4.184, 1)

                        off_nutrients = {
                            "energy_kcal": energy_val,
                            "protein_g": float(nutriments.get("proteins_100g") or nutriments.get("proteins") or 0.0),
                            "carb_g": float(nutriments.get("carbohydrates_100g") or nutriments.get("carbohydrates") or 0.0),
                            "fat_g": float(nutriments.get("fat_100g") or nutriments.get("fat") or 0.0),
                            "fibre_g": float(nutriments.get("fiber_100g") or nutriments.get("fiber") or 0.0),
                            "sodium_mg": float(nutriments.get("sodium_100g") or nutriments.get("sodium") or 0.0) * (1000.0 if float(nutriments.get("sodium_100g") or 0.0) < 50 else 1.0),
                            "sugar_g": float(nutriments.get("sugars_100g") or nutriments.get("sugars") or 0.0),
                            "saturated_fat_g": float(nutriments.get("saturated-fat_100g") or nutriments.get("saturated-fat") or 0.0),
                            "estimated_price": 40.0
                        }

                        if p_name and cls.is_valid_nutrients(off_nutrients):
                            return {
                                "product_name": p_name,
                                "brand": brand,
                                "ingredients_text": ingredients_text,
                                "nutrition_grade": nutrition_grade,
                                "nutriments": off_nutrients,
                                "source_detail": "Open Food Facts API"
                            }
            except Exception:
                continue
        return None

    @classmethod
    def scrape_product_name_from_search(cls, barcode: str) -> Optional[Dict[str, Any]]:
        """Tier 3: Query search engines and open barcode registries to scrape product title, brand, and pricing."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        
        # 1. DuckDuckGo HTML query
        urls = [
            f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(barcode)}",
            f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(barcode)}"
        ]
        
        for url in urls:
            try:
                res = httpx.get(url, headers=headers, timeout=5.0)
                if res.status_code == 200:
                    html = res.text
                    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html) or re.findall(r'class="result-link"[^>]*>(.*?)</a>', html)
                    for t in titles:
                        clean_t = re.sub(r'<[^>]+>', '', t).strip()
                        if len(clean_t) > 6 and not any(k in clean_t.lower() for k in ["upcitemdb", "barcodelookup", "search", "barcodedatabase", "findproduct", "go-upc"]):
                            clean_t = re.sub(r'\s*-\s*(?:BigBasket|Amazon|iHerb|Grofers|Flipkart|JioMart|Blinkit|Zepto|Nature\'s Basket).*$', '', clean_t, flags=re.IGNORECASE)
                            clean_t = re.sub(r'^Digit-Eyes\s+UPC\s+data:\s*\d+\s*UPC\s*', '', clean_t, flags=re.IGNORECASE)
                            
                            brand_match = re.match(r"^([A-Za-z0-9'&]+)\b", clean_t)
                            brand = brand_match.group(1) if brand_match else "Packaged Brand"
                            price = cls.extract_price_from_text(clean_t)
                            return {
                                "product_name": clean_t,
                                "brand": brand,
                                "estimated_price": price
                            }
            except Exception:
                pass
        return None

    @classmethod
    def extract_price_from_text(cls, text: str) -> float:
        """Parse estimated retail price in INR from title snippets if available."""
        price_match = re.search(r'(?:Rs\.?|INR|₹)\s*(\d+)', text, re.IGNORECASE)
        if price_match:
            return float(price_match.group(1))
        return 35.0

    @classmethod
    def estimate_nutrition_from_gemini(cls, product_name: str, barcode: str = "") -> Optional[dict]:
        """Tier 4: Query Google Gemini API to resolve product and compute genuine per-100g nutrients."""
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_3_6_API_KEY") or os.environ.get("GEMINI_API_KEY_1")
        if not api_key:
            return None

        prompt = f"""
You are an expert food scientist and packaged food nutrition parser.
Identify the exact packaged food item for Barcode: '{barcode}' and Scraped Name/Context: '{product_name}'.
Provide genuine, realistic per-100g nutritional facts, ingredients, brand, and Nutri-Score grade (a, b, c, d, or e).

Return ONLY a valid JSON object matching this exact schema:
{{
  "product_name": "Accurate Full Product Name",
  "brand": "Brand Name",
  "ingredients_text": "Detailed list of ingredients",
  "nutrition_grade": "c",
  "energy_kcal": 420.0,
  "protein_g": 6.5,
  "carb_g": 64.0,
  "fat_g": 18.0,
  "fibre_g": 2.5,
  "sodium_mg": 700.0,
  "sugar_g": 4.0,
  "saturated_fat_g": 7.5,
  "estimated_price": 30.0
}}
"""
        models_to_try = [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro"
        ]

        for model in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                res = httpx.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=7.0)
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
                            "estimated_price": float(parsed.get("estimated_price", 35.0)),
                            "product_name": parsed.get("product_name") or product_name,
                            "brand": parsed.get("brand") or "Verified Brand",
                            "ingredients_text": parsed.get("ingredients_text") or "Ingredients analyzed via Gemini AI",
                            "nutrition_grade": str(parsed.get("nutrition_grade", "c")).lower()
                        }
                        if cls.is_valid_nutrients(nutrients):
                            return nutrients
            except Exception:
                continue
        return None

    @classmethod
    def estimate_nutrition_from_name(cls, db: Session, product_name: str) -> dict:
        """Tier 5 Fallback: Match product name against local master food database."""
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
                "saturated_fat_g": float(fn.saturated_fat_g or 0.0),
                "estimated_price": 40.0
            }
            if cls.is_valid_nutrients(nut):
                return nut

        # General packaged snack default fallback
        return {
            "energy_kcal": 420.0,
            "protein_g": 5.5,
            "carb_g": 60.0,
            "fat_g": 18.0,
            "fibre_g": 2.0,
            "sodium_mg": 680.0,
            "sugar_g": 3.5,
            "saturated_fat_g": 6.5,
            "estimated_price": 30.0
        }

    @classmethod
    def detect_barcode_from_image(cls, image_bytes: bytes) -> Optional[str]:
        """Detect and extract barcode numbers from image utilizing OpenCV multi-preprocessing and Gemini Vision AI."""
        if not image_bytes:
            return None

        # 1. OpenCV Multi-Scale and Rotation Barcode Detection
        try:
            import numpy as np
            import cv2

            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is not None:
                detector = cv2.barcode.BarcodeDetector()
                
                # Check original, rotations, contrast-enhanced, and multiple scales
                scales = [1.0, 0.75, 0.5, 1.25, 1.5, 2.0]
                rotations = [0, 90, 180, 270]
                
                for rot in rotations:
                    if rot == 0:
                        r_img = img
                    elif rot == 90:
                        r_img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                    elif rot == 180:
                        r_img = cv2.rotate(img, cv2.ROTATE_180)
                    elif rot == 270:
                        r_img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)

                    # Try color and grayscale with CLAHE
                    gray = cv2.cvtColor(r_img, cv2.COLOR_BGR2GRAY)
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                    enhanced_gray = clahe.apply(gray)

                    for test_mat in [r_img, enhanced_gray]:
                        for scale in scales:
                            if scale == 1.0:
                                scaled_mat = test_mat
                            else:
                                scaled_mat = cv2.resize(test_mat, (0, 0), fx=scale, fy=scale)

                            retval, decoded_info, decoded_type, points = detector.detectAndDecode(scaled_mat)
                            if retval and decoded_info:
                                for info in decoded_info:
                                    code = str(info).strip()
                                    if len(code) >= 6 and code.isdigit():
                                        return code
        except Exception:
            pass

        # 2. Gemini Vision AI Barcode Reader Fallback
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_3_6_API_KEY") or os.environ.get("GEMINI_API_KEY_1")
        if api_key:
            import base64
            try:
                b64_data = base64.b64encode(image_bytes).decode("utf-8")
                prompt = "Locate and read the 8 to 14 digit barcode (UPC / EAN-13 / EAN-8 / Code-128) visible on this product packaging. Return ONLY a JSON object: {\"barcode\": \"8901058852712\"}. If no barcode is visible, return {\"barcode\": null}."
                
                models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
                for m in models:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
                    payload = {
                        "contents": [{
                            "parts": [
                                {"text": prompt},
                                {"inline_data": {"mime_type": "image/jpeg", "data": b64_data}}
                            ]
                        }]
                    }
                    res = httpx.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=8.0)
                    if res.status_code == 200:
                        cand = res.json().get("candidates", [])
                        if cand:
                            text = cand[0]["content"]["parts"][0]["text"]
                            clean = re.sub(r'^```(?:json)?\s*', '', text.strip(), flags=re.IGNORECASE)
                            clean = re.sub(r'\s*```$', '', clean)
                            parsed = json.loads(clean)
                            bc = str(parsed.get("barcode") or "").strip()
                            if bc and bc.isdigit() and len(bc) >= 6:
                                return bc
            except Exception:
                pass

        return None

    @classmethod
    def get_healthier_alternatives(
        cls,
        product_name: str,
        meal_type: str = "Snack",
        nutrients: Optional[dict] = None,
        diet_type: str = "all"
    ) -> List[Dict[str, Any]]:
        """Generate healthier culinary alternative swaps strictly matching the user's diet preferences."""
        p_name = (product_name or "").lower()
        diet = (diet_type or "all").lower()
        
        is_jain = "jain" in diet
        is_vegan = "vegan" in diet
        is_keto = "keto" in diet or "low carb" in diet
        is_eggetarian = "eggetarian" in diet
        is_veg = "vegetarian" in diet or is_jain or is_vegan or is_eggetarian
        is_nonveg = "non" in diet or "meat" in diet

        alts = []

        # 1. Noodles / Pasta / Instant Meals
        if any(w in p_name for w in ["noodle", "noodles", "maggi", "ramen", "pasta", "macaroni", "spaghetti", "chowmein", "cup"]):
            if is_jain:
                alts = [
                    {
                        "name": "Slurrp Farm Foxtail Millet & Oats Noodles (Jain Spices)",
                        "price": 35,
                        "diet_badge": "🌿 100% Jain Approved",
                        "reason": "100% millet & oats without maida, MSG, onion, garlic, or root starches",
                        "comparison": "3x more Fiber, 40% less Saturated Fat, zero root additives",
                        "link": f"https://www.amazon.in/s?k={urllib.parse.quote('millet noodles no maida jain')}"
                    },
                    {
                        "name": "Jain Sprouted Whole Moong & Tomato Chaat",
                        "price": 20,
                        "diet_badge": "🌿 100% Jain Approved",
                        "reason": "Freshly sprouted whole moong with lime, tomato, roasted cumin & rock salt",
                        "comparison": "12g bio-available plant protein & zero processed sodium",
                        "link": f"https://www.bigbasket.com/ps/?q={urllib.parse.quote('sprouted moong')}"
                    },
                    {
                        "name": "Organic Whole Wheat Hakka Noodles (Jain Masala)",
                        "price": 45,
                        "diet_badge": "🌿 100% Jain Approved",
                        "reason": "Stone-ground whole wheat noodles without palm oil, onion, or garlic",
                        "comparison": "Complex carbohydrates with sustained slow energy release",
                        "link": f"https://www.amazon.in/s?k={urllib.parse.quote('whole wheat noodles')}"
                    }
                ]
            elif is_vegan:
                alts = [
                    {
                        "name": "Slurrp Farm Foxtail Millet & Oats Noodles",
                        "price": 35,
                        "diet_badge": "🌱 100% Vegan Swap",
                        "reason": "Not fried, 100% millet & oats without maida, animal fats, or MSG",
                        "comparison": "3x more Fiber, 40% less Saturated Fat & 100% plant-based",
                        "link": f"https://www.amazon.in/s?k={urllib.parse.quote('millet noodles no maida')}"
                    },
                    {
                        "name": "Sprouted Moong & Vegetable Masala Chaat",
                        "price": 20,
                        "diet_badge": "🌱 100% Vegan Swap",
                        "reason": "Freshly sprouted whole moong with lime, tomato, cucumber & cumin",
                        "comparison": "12g natural bio-available plant protein & zero processed sodium",
                        "link": f"https://www.bigbasket.com/ps/?q={urllib.parse.quote('sprouted moong')}"
                    }
                ]
            elif is_keto:
                alts = [
                    {
                        "name": "Miracle Konjac Shirataki Low-Carb Noodles",
                        "price": 95,
                        "diet_badge": "🥑 Keto / Low-Carb",
                        "reason": "Zero net carbs, glucomannan fiber noodles sautéed in olive oil & spices",
                        "comparison": "Only 10 kcal vs 427 kcal in instant noodles; zero spike in blood sugar",
                        "link": f"https://www.amazon.in/s?k={urllib.parse.quote('shirataki konjac noodles')}"
                    },
                    {
                        "name": "Zucchini Spiralized Noodles (Zoodles) with Paneer Tikka",
                        "price": 60,
                        "diet_badge": "🥑 Keto / Low-Carb",
                        "reason": "Fresh spiraled zucchini tossed with herbs and grilled high-fat paneer",
                        "comparison": "18g Protein, under 4g Net Carbs, rich in potassium and Vitamin C",
                        "link": f"https://www.bigbasket.com/ps/?q={urllib.parse.quote('fresh zucchini')}"
                    }
                ]
            else:
                alts = [
                    {
                        "name": "Slurrp Farm Foxtail Millet & Oats Noodles",
                        "price": 35,
                        "diet_badge": "🥗 Balanced Healthy Swap",
                        "reason": "Not fried, 100% millet & oats without maida or MSG",
                        "comparison": "3x more Fiber, 40% less Saturated Fat & zero palm oil",
                        "link": f"https://www.amazon.in/s?k={urllib.parse.quote('millet noodles no maida')}"
                    },
                    {
                        "name": "Sprouted Moong & Vegetable Masala Chaat",
                        "price": 20,
                        "diet_badge": "🥗 Balanced Healthy Swap",
                        "reason": "Freshly sprouted whole moong with lime, tomato, cucumber & cumin",
                        "comparison": "12g natural bio-available protein & zero processed sodium",
                        "link": f"https://www.bigbasket.com/ps/?q={urllib.parse.quote('sprouted moong')}"
                    },
                    {
                        "name": "Organic Whole Wheat Hakka Noodles",
                        "price": 45,
                        "diet_badge": "🥗 Balanced Healthy Swap",
                        "reason": "Made with 100% stone-ground whole wheat without palm oil",
                        "comparison": "Complex carbohydrates with sustained slow energy release",
                        "link": f"https://www.amazon.in/s?k={urllib.parse.quote('whole wheat hakka noodles')}"
                    }
                ]

        # 2. Chips / Crisps / Namkeen / Bhujia
        elif any(w in p_name for w in ["chip", "chips", "lay", "lays", "bhujia", "doritos", "kurkure", "namkeen", "snack", "nacho", "pringles"]):
            if is_jain:
                alts = [
                    {
                        "name": "Roasted Masala Phool Makhana (Jain Lotus Seeds)",
                        "price": 40,
                        "diet_badge": "🌿 100% Jain Approved",
                        "reason": "Slow-roasted lotus seeds with rock salt & cumin; zero onion/garlic/roots",
                        "comparison": "Zero trans-fat, 70% lower calories than potato chips",
                        "link": f"https://www.amazon.in/s?k={urllib.parse.quote('roasted makhana jain')}"
                    },
                    {
                        "name": "Crispy Jain Raw Banana Chips (Rock Salt & Pepper)",
                        "price": 35,
                        "diet_badge": "🌿 100% Jain Approved",
                        "reason": "Crisped raw green plantain without underground potatoes or root starches",
                        "comparison": "High resistant starch, gut prebiotic & 60% less saturated fat",
                        "link": f"https://www.amazon.in/s?k={urllib.parse.quote('raw banana chips rock salt')}"
                    },
                    {
                        "name": "Jain Spiced Roasted Bengal Gram (Chana)",
                        "price": 25,
                        "diet_badge": "🌿 100% Jain Approved",
                        "reason": "Crunchy roasted chana loaded with plant protein and cumin seasoning",
                        "comparison": "18g Protein per 100g vs 6g in regular chips",
                        "link": f"https://www.bigbasket.com/ps/?q={urllib.parse.quote('roasted chana')}"
                    }
                ]
            elif is_keto:
                alts = [
                    {
                        "name": "Roasted Salted Pumpkin & Sunflower Seeds",
                        "price": 45,
                        "diet_badge": "🥑 Keto / Low-Carb",
                        "reason": "Crunchy mineral-rich seed mix packed with healthy monounsaturated fats",
                        "comparison": "Only 3g Net Carbs, 19g Protein & zero processed starch",
                        "link": f"https://www.amazon.in/s?k={urllib.parse.quote('roasted pumpkin seeds')}"
                    },
                    {
                        "name": "Crispy Baked Almond & Flax Crackers",
                        "price": 60,
                        "diet_badge": "🥑 Keto / Low-Carb",
                        "reason": "Grain-free crackers baked from whole crushed almonds and golden flax",
                        "comparison": "High Omega-3s, under 2g net carbs per serving",
                        "link": f"https://www.amazon.in/s?k={urllib.parse.quote('keto almond crackers')}"
                    }
                ]
            else:
                alts = [
                    {
                        "name": "Roasted Masala Phool Makhana (Foxnuts)",
                        "price": 40,
                        "diet_badge": "🥗 Healthy Snack Swap",
                        "reason": "Slow-roasted lotus seeds rich in magnesium, potassium & antioxidants",
                        "comparison": "Zero trans-fat, 70% lower calories than deep-fried potato chips",
                        "link": f"https://www.amazon.in/s?k={urllib.parse.quote('roasted makhana masala')}"
                    },
                    {
                        "name": "Spiced Roasted Bengal Gram (Chana)",
                        "price": 25,
                        "diet_badge": "🥗 Healthy Snack Swap",
                        "reason": "Crunchy roasted chana loaded with prebiotic fiber and plant protein",
                        "comparison": "18g Protein per 100g vs 6g in regular chips",
                        "link": f"https://www.bigbasket.com/ps/?q={urllib.parse.quote('roasted chana')}"
                    },
                    {
                        "name": "Vacuum-Fried Sweet Potato & Beetroot Chips",
                        "price": 50,
                        "diet_badge": "🥗 Healthy Snack Swap",
                        "reason": "Low-temperature vacuum cooked with 50% less oil absorption",
                        "comparison": "Rich in natural beta-carotene, Vitamin A & low sodium",
                        "link": f"https://www.amazon.in/s?k={urllib.parse.quote('vacuum fried veggie chips')}"
                    }
                ]

        # 3. Biscuits / Cookies / Chocolate Spread / Sweets
        elif any(w in p_name for w in ["biscuit", "biscuits", "cookie", "cookies", "parle", "oreo", "nutella", "chocolate", "sweet", "cadbury", "cake"]):
            if is_vegan:
                alts = [
                    {
                        "name": "The Whole Truth Dark Chocolate Peanut Butter (Vegan)",
                        "price": 120,
                        "diet_badge": "🌱 100% Vegan Swap",
                        "reason": "100% whole roasted peanuts, unsweetened cacao, sweetened with dates",
                        "comparison": "No added refined sugar, zero dairy, 28g plant protein",
                        "link": f"https://www.amazon.in/s?k={urllib.parse.quote('the whole truth peanut butter')}"
                    },
                    {
                        "name": "Medjool Dates stuffed with Roasted Walnuts",
                        "price": 40,
                        "diet_badge": "🌱 100% Vegan Swap",
                        "reason": "Natural low-GI whole fruit sweet packed with Omega-3 fats",
                        "comparison": "Zero processed chemicals, natural sweetness with high fiber",
                        "link": f"https://www.bigbasket.com/ps/?q={urllib.parse.quote('medjool dates')}"
                    }
                ]
            elif is_keto:
                alts = [
                    {
                        "name": "85% Single-Origin Dark Chocolate (Stevia Sweetened)",
                        "price": 90,
                        "diet_badge": "🥑 Keto / Low-Carb",
                        "reason": "Rich organic cocoa with healthy antioxidant flavonoids and zero added sugar",
                        "comparison": "Under 4g net carbs per bar vs 35g sugar in commercial biscuits",
                        "link": f"https://www.amazon.in/s?k={urllib.parse.quote('sugar free dark chocolate stevia')}"
                    },
                    {
                        "name": "Roasted Almond & Chia Seed Energy Bites",
                        "price": 50,
                        "diet_badge": "🥑 Keto / Low-Carb",
                        "reason": "Cold-pressed roasted almond meal, chia seeds and erythritol",
                        "comparison": "High satiety healthy fats and zero insulin spike",
                        "link": f"https://www.amazon.in/s?k={urllib.parse.quote('keto energy bites almond')}"
                    }
                ]
            else:
                alts = [
                    {
                        "name": "The Whole Truth Dark Chocolate Peanut Butter",
                        "price": 120,
                        "diet_badge": "🥗 Clean Sweet Swap",
                        "reason": "100% whole roasted peanuts, unsweetened cacao, sweetened with dates",
                        "comparison": "No added sugar, zero hydrogenated palm oil, 28g Protein",
                        "link": f"https://www.amazon.in/s?k={urllib.parse.quote('the whole truth peanut butter')}"
                    },
                    {
                        "name": "Almond & Flaxseed Ragi Jaggery Cookies",
                        "price": 60,
                        "diet_badge": "🥗 Clean Sweet Swap",
                        "reason": "Baked with finger millet (ragi), crunchy almonds and organic jaggery",
                        "comparison": "High calcium & iron, zero refined white sugar or maida",
                        "link": f"https://www.amazon.in/s?k={urllib.parse.quote('ragi cookies jaggery')}"
                    },
                    {
                        "name": "Medjool Dates stuffed with Roasted Walnuts",
                        "price": 40,
                        "diet_badge": "🥗 Clean Sweet Swap",
                        "reason": "Natural low-GI whole fruit sweet packed with Omega-3 fats",
                        "comparison": "Zero processed chemicals, natural sweetness with high fiber",
                        "link": f"https://www.bigbasket.com/ps/?q={urllib.parse.quote('medjool dates')}"
                    }
                ]

        # 4. Soft Drinks / Sodas / Sugary Beverages
        elif any(w in p_name for w in ["cola", "coca", "pepsi", "soda", "fanta", "sprite", "drink", "beverage", "juice", "frooti", "maaza"]):
            if is_vegan or is_jain:
                alts = [
                    {
                        "name": "Fresh Tender Coconut Water (Nariyal Pani)",
                        "price": 50,
                        "diet_badge": "🌱 100% Plant-Based",
                        "reason": "Nature's isotonic electrolyte drink packed with potassium & magnesium",
                        "comparison": "Zero added sugar, 100% natural hydration, zero chemicals",
                        "link": f"https://www.bigbasket.com/ps/?q={urllib.parse.quote('tender coconut')}"
                    },
                    {
                        "name": "Raw Sparkling Ginger & Lemon Kombucha",
                        "price": 80,
                        "diet_badge": "🌱 Probiotic Refreshment",
                        "reason": "Naturally fermented bubbly tea with live digestive cultures",
                        "comparison": "Only 3g natural sugar vs 38g in soda, 100% vegan probiotics",
                        "link": f"https://www.amazon.in/s?k={urllib.parse.quote('raw kombucha ginger')}"
                    }
                ]
            else:
                alts = [
                    {
                        "name": "Fresh Tender Coconut Water (Nariyal Pani)",
                        "price": 50,
                        "diet_badge": "🥗 Natural Hydration",
                        "reason": "Nature's isotonic electrolyte drink packed with potassium",
                        "comparison": "Zero added sugar, zero phosphoric acid or caramel color",
                        "link": f"https://www.bigbasket.com/ps/?q={urllib.parse.quote('tender coconut')}"
                    },
                    {
                        "name": "Chilled Spiced Buttermilk (Masala Chaas)",
                        "price": 15,
                        "diet_badge": "🥛 Probiotic Superdrink",
                        "reason": "Traditional probiotic digestive drink with roasted jeera & rock salt",
                        "comparison": "Rich in natural lactobacillus probiotics, under 30 kcal",
                        "link": f"https://www.bigbasket.com/ps/?q={urllib.parse.quote('amul buttermilk')}"
                    }
                ]

        # 5. Default General Healthy Packaged Food Alternatives
        if not alts:
            if is_jain:
                alts = [
                    {
                        "name": "Jain Roasted Masala Makhana (Foxnuts)",
                        "price": 45,
                        "diet_badge": "🌿 100% Jain Approved",
                        "reason": "Crunchy lotus seed superfood snack with rock salt & jeera",
                        "comparison": "Zero trans fats, rich in plant antioxidants and slow energy",
                        "link": f"https://www.amazon.in/s?k={urllib.parse.quote('roasted makhana jain')}"
                    },
                    {
                        "name": "Whole Fruit & Nut Energy Bar (No Added Sugar)",
                        "price": 40,
                        "diet_badge": "🌿 100% Jain Approved",
                        "reason": "100% clean-label whole dates, almonds, cashews and pumpkin seeds",
                        "comparison": "Zero preservatives, zero high fructose corn syrup",
                        "link": f"https://www.amazon.in/s?k={urllib.parse.quote('clean label fruit nut bar')}"
                    }
                ]
            elif is_vegan:
                alts = [
                    {
                        "name": "Organic Roasted Spiced Edamame",
                        "price": 55,
                        "diet_badge": "🌱 100% Vegan Swap",
                        "reason": "Dry-roasted young soybeans packed with complete plant amino acids",
                        "comparison": "14g plant protein, zero cholesterol or dairy additives",
                        "link": f"https://www.amazon.in/s?k={urllib.parse.quote('roasted edamame')}"
                    },
                    {
                        "name": "Whole Fruit & Nut Energy Bar (No Added Sugar)",
                        "price": 40,
                        "diet_badge": "🌱 100% Vegan Swap",
                        "reason": "100% clean-label dates, almonds, cashews and seeds",
                        "comparison": "Zero preservatives, zero high fructose corn syrup",
                        "link": f"https://www.amazon.in/s?k={urllib.parse.quote('clean label fruit nut bar')}"
                    }
                ]
            else:
                alts = [
                    {
                        "name": "Spiced Roasted Makhana & Pumpkin Seed Mix",
                        "price": 45,
                        "diet_badge": "🥗 Nutrient Dense Swap",
                        "reason": "Crunchy superfood snack packed with zinc, magnesium and healthy fats",
                        "comparison": "Zero trans fats, rich in plant antioxidants and slow-burning energy",
                        "link": f"https://www.amazon.in/s?k={urllib.parse.quote('roasted makhana seed mix')}"
                    },
                    {
                        "name": "Whole Fruit & Nut Energy Bar (No Added Sugar)",
                        "price": 40,
                        "diet_badge": "🥗 Clean Label Swap",
                        "reason": "100% clean-label whole dates, almonds, cashews and seeds",
                        "comparison": "Zero preservatives, zero high fructose corn syrup",
                        "link": f"https://www.amazon.in/s?k={urllib.parse.quote('clean label fruit nut bar')}"
                    }
                ]

        return alts

    @classmethod
    def get_product(cls, db: Session, barcode: str, diet_type: str = "all") -> dict:
        """Get product info for barcode utilizing strict 4-tier hierarchy:
        Tier 1: Database Cache (BarcodeCache table & verified FMCG cache)
        Tier 2: Open Food Facts API (OFF API v2/v0)
        Tier 3: Web Scraper (DuckDuckGo & Open Barcode Registries)
        Tier 4: Google Gemini AI API (Accurate AI Macro, Brand, & Ingredients Parser)
        Tier 5: Local Master Food DB Standardization (Fallback)
        """
        barcode = str(barcode).strip()
        if not barcode:
            return {"status": "error", "message": "Barcode cannot be empty"}

        # ----------------------------------------------------
        # TIER 1: Database Cache & Verified FMCG Registry
        # ----------------------------------------------------
        try:
            cached = db.query(BarcodeCache).filter(BarcodeCache.barcode == barcode).first()
            if cached and cached.nutriments_json:
                cached_nut = json.loads(cached.nutriments_json)
                if cls.is_valid_nutrients(cached_nut):
                    source_det = getattr(cached, "source_detail", None) or "Local Database Cache (Verified)"
                    ing_names = [cached.product_name] + [s.strip() for s in (cached.ingredients_text or "").split(",") if s.strip()]
                    classification = ClassificationEngine.classify_ingredients(ing_names)
                    alternatives = cls.get_healthier_alternatives(cached.product_name, "Snack", cached_nut, diet_type=diet_type)

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
                        "nutriments": cached_nut,
                        "dietary_classification": classification,
                        "alternatives": alternatives
                    }
                else:
                    db.delete(cached)
                    db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass

        if barcode in cls.KNOWN_POPULAR_BARCODES:
            item = cls.KNOWN_POPULAR_BARCODES[barcode]
            nutrients_100g = item["nutriments"]
            score, category, explanation = HealthScorer.score_from_nutrition_dict(nutrients_100g)
            ing_names = [item["product_name"]] + [s.strip() for s in item["ingredients_text"].split(",") if s.strip()]
            classification = ClassificationEngine.classify_ingredients(ing_names)
            alternatives = cls.get_healthier_alternatives(item["product_name"], "Snack", nutrients_100g, diet_type=diet_type)

            # Persist to database cache
            try:
                new_cache = BarcodeCache(
                    barcode=barcode,
                    product_name=item["product_name"],
                    brand=item["brand"],
                    ingredients_text=item["ingredients_text"],
                    nutrition_grade=item["nutrition_grade"],
                    nutriments_json=json.dumps(nutrients_100g),
                    health_score=score,
                    health_category=category,
                    source_detail="NutriX Verified FMCG Database"
                )
                db.add(new_cache)
                db.commit()
            except Exception:
                try:
                    db.rollback()
                except Exception:
                    pass

            return {
                "status": "success",
                "source": "curated_fmcg",
                "source_detail": "NutriX Verified FMCG Database",
                "barcode": barcode,
                "product_name": item["product_name"],
                "brand": item["brand"],
                "ingredients_text": item["ingredients_text"],
                "nutrition_grade": item["nutrition_grade"],
                "health_score": score,
                "health_category": category,
                "explanation": explanation,
                "nutriments": nutrients_100g,
                "dietary_classification": classification,
                "alternatives": alternatives
            }

        product_name = None
        brand = "Unknown Brand"
        ingredients_text = "No ingredients listed"
        nutrition_grade = "unknown"
        nutrients_100g = None
        source_name = "api"
        source_detail = "Open Food Facts API"

        # ----------------------------------------------------
        # TIER 2: Open Food Facts API
        # ----------------------------------------------------
        off_data = cls.fetch_from_open_food_facts(barcode)
        if off_data:
            product_name = off_data["product_name"]
            brand = off_data["brand"]
            ingredients_text = off_data["ingredients_text"]
            nutrition_grade = off_data["nutrition_grade"]
            nutrients_100g = off_data["nutriments"]
            source_name = "open_food_facts"
            source_detail = "Open Food Facts API"

        # ----------------------------------------------------
        # TIER 3: Web Scraper (DuckDuckGo Search & Open Catalogs)
        # ----------------------------------------------------
        scraped_info = None
        if not product_name:
            scraped_info = cls.scrape_product_name_from_search(barcode)
            if scraped_info and scraped_info.get("product_name"):
                product_name = scraped_info["product_name"]
                if scraped_info.get("brand"):
                    brand = scraped_info["brand"]

        # Default fallback title if still missing
        if not product_name:
            product_name = f"Packaged Food Item #{barcode}"

        # ----------------------------------------------------
        # TIER 4: Google Gemini AI API (Macro & Ingredients Resolver)
        # ----------------------------------------------------
        if not cls.is_valid_nutrients(nutrients_100g):
            gemini_result = cls.estimate_nutrition_from_gemini(product_name, barcode)
            if gemini_result and cls.is_valid_nutrients(gemini_result):
                nutrients_100g = gemini_result
                if gemini_result.get("product_name") and (product_name.startswith("Packaged Food Item #") or len(gemini_result["product_name"]) > len(product_name)):
                    product_name = gemini_result["product_name"]
                if gemini_result.get("brand") and (brand == "Unknown Brand" or brand == "Packaged Brand"):
                    brand = gemini_result["brand"]
                if gemini_result.get("ingredients_text") and ingredients_text == "No ingredients listed":
                    ingredients_text = gemini_result["ingredients_text"]
                if gemini_result.get("nutrition_grade") and nutrition_grade == "unknown":
                    nutrition_grade = gemini_result["nutrition_grade"]
                source_name = "gemini_ai"
                source_detail = "Gemini AI Nutrition Intelligence"

        # ----------------------------------------------------
        # TIER 5: Local Master Food DB Standardization (Fallback)
        # ----------------------------------------------------
        if not cls.is_valid_nutrients(nutrients_100g):
            nutrients_100g = cls.estimate_nutrition_from_name(db, product_name)
            price = cls.extract_price_from_text(product_name)
            nutrients_100g["estimated_price"] = price
            source_name = "web_search"
            source_detail = "DuckDuckGo Scraper + Local Master DB"

        # Calculate Health Score & Nutri-Score
        score, category, explanation = HealthScorer.score_from_nutrition_dict(nutrients_100g)
        
        # Dietary & Allergen Classification via ClassificationEngine
        ing_names = [product_name] + [s.strip() for s in (ingredients_text or "").split(",") if s.strip()]
        classification = ClassificationEngine.classify_ingredients(ing_names)

        # Healthier alternatives strictly matching user's diet
        alternatives = cls.get_healthier_alternatives(product_name, "Snack", nutrients_100g, diet_type=diet_type)

        # Persist newly resolved product into Database Cache
        try:
            new_cache = BarcodeCache(
                barcode=barcode,
                product_name=product_name,
                brand=brand,
                ingredients_text=ingredients_text,
                nutrition_grade=nutrition_grade if nutrition_grade != "unknown" else (category[0].lower() if category else "c"),
                nutriments_json=json.dumps(nutrients_100g),
                health_score=score,
                health_category=category,
                source_detail=source_detail
            )
            db.add(new_cache)
            db.commit()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass

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
            "nutriments": nutrients_100g,
            "dietary_classification": classification,
            "alternatives": alternatives
        }
