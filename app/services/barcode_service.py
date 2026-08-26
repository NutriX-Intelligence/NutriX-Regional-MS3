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
    API_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"

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
    def scrape_product_name_from_search(cls, barcode: str) -> str:
        """Query DuckDuckGo HTML search for the barcode to identify product name and brand."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(barcode)}"
        try:
            res = httpx.get(url, headers=headers, timeout=6.0)
            if res.status_code == 200:
                html = res.text
                titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html)
                for t in titles:
                    clean_t = re.sub(r'<[^>]+>', '', t).strip()
                    if len(clean_t) > 10 and not any(k in clean_t.lower() for k in ["upcitemdb", "barcodelookup", "search", "barcodedatabase", "findproduct", "go-upc"]):
                        clean_t = re.sub(r'\s*-\s*(?:BigBasket|Amazon|iHerb|Grofers|Flipkart|JioMart|Blinkit|Zepto).*$', '', clean_t, flags=re.IGNORECASE)
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
        return 20.0

    @classmethod
    def estimate_nutrition_from_gemini(cls, product_name: str, barcode: str = "") -> dict:
        """Query Google Gemini API to estimate realistic per-100g nutrients."""
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_3_6_API_KEY") or os.environ.get("GEMINI_API_KEY_1")
        if not api_key:
            return None

        prompt = f"""
You are an expert food nutrition database parser.
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
  "ingredients_text": "Wheat flour, edible vegetable oil, seasoning spices, salt"
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
                res = httpx.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=6.0)
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

        # General packaged snack default fallback
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
    def get_healthier_alternatives(
        cls,
        product_name: str,
        meal_type: str = "Snack",
        nutrients: Optional[dict] = None
    ) -> List[Dict[str, Any]]:
        """Generate smart, healthier, culturally relevant culinary alternatives."""
        p_name = (product_name or "").lower()
        nut = nutrients or {}
        
        sugar = float(nut.get("sugar_g", 0.0) or 0.0)
        fat = float(nut.get("fat_g", 0.0) or 0.0)
        sodium = float(nut.get("sodium_mg", 0.0) or 0.0)

        # 1. Noodles / Pasta / Instant Meals
        if any(w in p_name for w in ["noodle", "noodles", "maggi", "ramen", "pasta", "macaroni", "spaghetti", "chowmein", "cup"]):
            return [
                {
                    "name": "Slurrp Farm Foxtail Millet & Oats Noodles",
                    "price": 35,
                    "reason": "Not fried, 100% millet & oats without maida or MSG",
                    "comparison": "3x more Fiber, 40% less Saturated Fat & zero palm oil",
                    "link": f"https://www.amazon.in/s?k={urllib.parse.quote('millet noodles no maida')}"
                },
                {
                    "name": "Sprouted Moong & Vegetable Masala Chaat",
                    "price": 20,
                    "reason": "Freshly sprouted whole moong with lime, tomato, cucumber & cumin",
                    "comparison": "12g natural bio-available protein & zero processed sodium",
                    "link": f"https://www.bigbasket.com/ps/?q={urllib.parse.quote('sprouted moong')}"
                },
                {
                    "name": "Organic Whole Wheat Hakka Noodles",
                    "price": 45,
                    "reason": "Made with 100% stone-ground whole wheat without palm oil",
                    "comparison": "Complex carbohydrates with sustained slow energy release",
                    "link": f"https://www.amazon.in/s?k={urllib.parse.quote('whole wheat hakka noodles')}"
                }
            ]

        # 2. Chips / Crisps / Namkeen / Bhujia
        if any(w in p_name for w in ["chip", "chips", "lay", "lays", "bhujia", "doritos", "kurkure", "namkeen", "snack", "nacho", "pringles"]):
            return [
                {
                    "name": "Roasted Masala Phool Makhana (Foxnuts)",
                    "price": 40,
                    "reason": "Slow-roasted lotus seeds rich in magnesium, potassium & antioxidants",
                    "comparison": "Zero trans-fat, 70% lower calories than deep-fried potato chips",
                    "link": f"https://www.amazon.in/s?k={urllib.parse.quote('roasted makhana masala')}"
                },
                {
                    "name": "Spiced Roasted Bengal Gram (Chana)",
                    "price": 25,
                    "reason": "Crunchy roasted chana loaded with prebiotic fiber and plant protein",
                    "comparison": "18g Protein per 100g vs 6g in regular chips",
                    "link": f"https://www.bigbasket.com/ps/?q={urllib.parse.quote('roasted chana')}"
                },
                {
                    "name": "Vacuum-Fried Sweet Potato & Beetroot Chips",
                    "price": 50,
                    "reason": "Low-temperature vacuum cooked with 50% less oil absorption",
                    "comparison": "Rich in natural beta-carotene, Vitamin A & low sodium",
                    "link": f"https://www.amazon.in/s?k={urllib.parse.quote('vacuum fried veggie chips')}"
                }
            ]

        # 3. Biscuits / Cookies / Chocolate Spread / Sweets
        if any(w in p_name for w in ["biscuit", "biscuits", "cookie", "cookies", "parle", "oreo", "nutella", "chocolate", "sweet", "cadbury", "cake"]):
            return [
                {
                    "name": "The Whole Truth Dark Chocolate Peanut Butter",
                    "price": 120,
                    "reason": "100% whole roasted peanuts, unsweetened cacao, sweetened with dates",
                    "comparison": "No added sugar, zero hydrogenated palm oil, 28g Protein",
                    "link": f"https://www.amazon.in/s?k={urllib.parse.quote('the whole truth peanut butter')}"
                },
                {
                    "name": "Almond & Flaxseed Ragi Jaggery Cookies",
                    "price": 60,
                    "reason": "Baked with finger millet (ragi), crunchy almonds and organic jaggery",
                    "comparison": "High calcium & iron, zero refined white sugar or maida",
                    "link": f"https://www.amazon.in/s?k={urllib.parse.quote('ragi cookies jaggery')}"
                },
                {
                    "name": "Medjool Dates stuffed with Roasted Walnuts",
                    "price": 40,
                    "reason": "Natural low-GI whole fruit sweet packed with Omega-3 fats",
                    "comparison": "Zero processed chemicals, natural sweetness with high fiber",
                    "link": f"https://www.bigbasket.com/ps/?q={urllib.parse.quote('medjool dates')}"
                }
            ]

        # 4. Soft Drinks / Sodas / Sugary Beverages
        if any(w in p_name for w in ["cola", "coca", "pepsi", "soda", "fanta", "sprite", "drink", "beverage", "juice", "frooti", "maaza"]):
            return [
                {
                    "name": "Fresh Tender Coconut Water (Nariyal Pani)",
                    "price": 50,
                    "reason": "Nature's isotonic electrolyte drink packed with potassium",
                    "comparison": "Zero added sugar, zero phosphoric acid or caramel color",
                    "link": f"https://www.bigbasket.com/ps/?q={urllib.parse.quote('tender coconut')}"
                },
                {
                    "name": "Chilled Spiced Buttermilk (Masala Chaas)",
                    "price": 15,
                    "reason": "Traditional probiotic digestive drink with roasted jeera & mint",
                    "comparison": "Rich in natural gut-friendly lactobacillus probiotics, under 30 kcal",
                    "link": f"https://www.bigbasket.com/ps/?q={urllib.parse.quote('amul buttermilk')}"
                },
                {
                    "name": "Raw Sparkling Ginger & Lemon Kombucha",
                    "price": 80,
                    "reason": "Naturally fermented bubbly tea with live digestive cultures",
                    "comparison": "Only 3g natural sugar vs 38g in canned soda, boosts digestion",
                    "link": f"https://www.amazon.in/s?k={urllib.parse.quote('raw kombucha ginger')}"
                }
            ]

        # 5. Default General Healthy Packaged Food Alternatives
        return [
            {
                "name": "Spiced Roasted Makhana & Pumpkin Seed Mix",
                "price": 45,
                "reason": "Crunchy superfood snack packed with zinc, magnesium and healthy fats",
                "comparison": "Zero trans fats, rich in plant antioxidants and slow-burning energy",
                "link": f"https://www.amazon.in/s?k={urllib.parse.quote('roasted makhana seed mix')}"
            },
            {
                "name": "Whole Fruit & Nut Energy Bar (No Added Sugar)",
                "price": 40,
                "reason": "100% clean-label whole dates, almonds, cashews and seeds",
                "comparison": "Zero preservatives, zero high fructose corn syrup",
                "link": f"https://www.amazon.in/s?k={urllib.parse.quote('clean label fruit nut bar')}"
            }
        ]

    @classmethod
    def get_product(cls, db: Session, barcode: str) -> dict:
        """Get product info for barcode utilizing multi-tier fallback:
        Tier 0: Curated Popular Indian & Global FMCG Database
        Tier 1: Local Verified Database Cache
        Tier 2: Open Food Facts API (OFF API)
        Tier 3: DuckDuckGo Web Search Scraper (Title extraction)
        Tier 4: Google Gemini AI (Per-100g macro estimation)
        Tier 5: Local Master DB Standardization
        """
        barcode = str(barcode).strip()
        if not barcode:
            return {"status": "error", "message": "Barcode cannot be empty"}

        # 0. Check Pre-curated Popular FMCG Barcodes (Immediate 0ms response)
        if barcode in cls.KNOWN_POPULAR_BARCODES:
            item = cls.KNOWN_POPULAR_BARCODES[barcode]
            nutrients_100g = item["nutriments"]
            score, category, explanation = HealthScorer.score_from_nutrition_dict(nutrients_100g)
            
            # Dietary & Allergen Classification via ClassificationEngine
            ing_names = [item["product_name"]] + [s.strip() for s in item["ingredients_text"].split(",") if s.strip()]
            classification = ClassificationEngine.classify_ingredients(ing_names)
            
            alternatives = cls.get_healthier_alternatives(item["product_name"], "Snack", nutrients_100g)

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

        # 1. Check local cache (ignore stale 0-nutrient cache entries)
        try:
            cached = db.query(BarcodeCache).filter(BarcodeCache.barcode == barcode).first()
            if cached and cached.nutriments_json:
                cached_nut = json.loads(cached.nutriments_json)
                if cls.is_valid_nutrients(cached_nut):
                    source_det = getattr(cached, "source_detail", None) or "Local Cache (Verified)"
                    ing_names = [cached.product_name] + [s.strip() for s in (cached.ingredients_text or "").split(",") if s.strip()]
                    classification = ClassificationEngine.classify_ingredients(ing_names)
                    alternatives = cls.get_healthier_alternatives(cached.product_name, "Snack", cached_nut)

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

        product_name = None
        brand = "Unknown Brand"
        ingredients_text = "No ingredients listed"
        nutrition_grade = "unknown"
        nutrients_100g = None
        source_name = "api"
        source_detail = "Open Food Facts API"

        # Tier 2: Fetch from Open Food Facts API
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
                    ingredients_text = product.get("ingredients_text") or product.get("ingredients_text_en") or "No ingredients listed"
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

        # Tier 3: DuckDuckGo Web Search Scraper (if product name is missing)
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

        # Tier 4: Gemini AI API (If OFF nutrients were missing or 0)
        if not cls.is_valid_nutrients(nutrients_100g):
            gemini_result = cls.estimate_nutrition_from_gemini(product_name, barcode)
            if gemini_result and cls.is_valid_nutrients(gemini_result):
                nutrients_100g = gemini_result
                if gemini_result.get("brand") and brand == "Unknown Brand":
                    brand = gemini_result["brand"]
                if gemini_result.get("ingredients_text") and ingredients_text == "No ingredients listed":
                    ingredients_text = gemini_result["ingredients_text"]
                source_name = "gemini_ai"
                source_detail = "DuckDuckGo Scraper + Gemini AI"

        # Tier 5: Local Master DB Standardization (If Gemini AI key is missing or failed)
        if not cls.is_valid_nutrients(nutrients_100g):
            nutrients_100g = cls.estimate_nutrition_from_name(db, product_name)
            price = cls.extract_price_from_text(product_name)
            nutrients_100g["estimated_price"] = price
            source_name = "web_search"
            source_detail = "DuckDuckGo Scraper + Local Master DB"

        # Calculate Health Score
        score, category, explanation = HealthScorer.score_from_nutrition_dict(nutrients_100g)
        
        # Dietary & Allergen Classification via ClassificationEngine
        ing_names = [product_name] + [s.strip() for s in (ingredients_text or "").split(",") if s.strip()]
        classification = ClassificationEngine.classify_ingredients(ing_names)

        # Healthier alternatives
        alternatives = cls.get_healthier_alternatives(product_name, "Snack", nutrients_100g)

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
