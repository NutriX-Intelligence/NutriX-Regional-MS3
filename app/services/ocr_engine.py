import re
import os
import io
import json
import base64
import logging
from typing import Dict, Any, List, Optional
import httpx

logger = logging.getLogger("ocr_engine")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False


class OCREngine:
    """Production-grade OCR Nutrition Label Extraction Engine.
    
    Supports:
    1. Gemini Vision AI parsing for high-accuracy direct label extraction.
    2. Local EasyOCR image-to-text pipeline.
    3. Multi-column and table-aware regex extraction (e.g., 'Energy (kcal) 533 181 9%').
    """

    SERVING_SIZE_PATTERNS = [
        r"(?i)(?:serving\s*size|portion\s*size|portion)\s*[:\-=\s]*\s*(\d+(?:\.\d+)?\s*(?:g|ml|oz|piece|scoop|bar|slice|cup)?)",
        r"(?i)(?:per\s*serve|per\s*serving|per\s*portion)\s*\(\s*(\d+(?:\.\d+)?\s*(?:g|ml|oz)?)\s*\)",
        r"(?i)(?:per\s*serve|per\s*serving)\s*[:\-=\s]*\s*(\d+(?:\.\d+)?\s*(?:g|ml|oz)?)",
        r"(?i)(?:per\s*100\s*g|per\s*100g|per\s*100\s*ml)"
    ]

    @classmethod
    def parse_nutrition_text(cls, text: str) -> Dict[str, Any]:
        """Parse raw text lines using robust table-aware regular expressions to extract structured nutritional values."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        results: Dict[str, Any] = {
            "energy_kcal": 0.0,
            "protein_g": 0.0,
            "carb_g": 0.0,
            "fat_g": 0.0,
            "saturated_fat_g": 0.0,
            "trans_fat_g": 0.0,
            "cholesterol_mg": 0.0,
            "fibre_g": 0.0,
            "sodium_mg": 0.0,
            "sugar_g": 0.0,
            "serving_size": "100g"
        }

        def extract_row_value(line: str, keywords: List[str]) -> Optional[float]:
            for kw in keywords:
                # Match keyword followed by optional units in parens/brackets, then colon/spaces, then first number
                # e.g. "Total Fat (g) 28 10 14%" -> 28
                pattern = rf"(?i)(?:\b{kw}\b)[\s\(\)/a-z]*[:\-=\s]+(\d+(?:\.\d+)?)"
                m = re.search(pattern, line)
                if m:
                    try:
                        return float(m.group(1))
                    except Exception:
                        pass
            return None

        # Check whole text and line by line
        for line in lines:
            # Serving size
            for pat in cls.SERVING_SIZE_PATTERNS:
                m = re.search(pat, line)
                if m:
                    val = m.group(1) if m.groups() else m.group(0)
                    if val and results["serving_size"] == "100g":
                        results["serving_size"] = str(val).strip()

            # Calories / Energy
            if results["energy_kcal"] == 0.0:
                m_kcal = re.search(r"(?i)(\d+(?:\.\d+)?)\s*(?:kcal|calories)\b", line)
                if m_kcal:
                    try:
                        results["energy_kcal"] = float(m_kcal.group(1))
                    except Exception:
                        pass
                else:
                    is_kj = "kj" in line.lower()
                    val = extract_row_value(line, [
                        r"energy", r"energia", r"calories", r"calorie", r"calorías", r"valeur\s*énergétique"
                    ])
                    if val is not None:
                        if is_kj:
                            val = round(val / 4.184, 1)
                        results["energy_kcal"] = val

            # Protein
            if results["protein_g"] == 0.0:
                val = extract_row_value(line, [r"protein", r"proteins", r"protéines", r"proteínas", r"eiweiss", r"prot"])
                if val is not None:
                    results["protein_g"] = val

            # Carbohydrates
            if results["carb_g"] == 0.0:
                val = extract_row_value(line, [
                    r"total\s*carbohydrate", r"total\s*carbohydrates", r"carbohydrate", r"carbohydrates",
                    r"total\s*carbs", r"carbs", r"carb", r"glucides", r"hidratos\s*de\s*carbono", r"kohlenhydrate"
                ])
                if val is not None:
                    results["carb_g"] = val

            # Total Fat
            if results["fat_g"] == 0.0:
                val = extract_row_value(line, [
                    r"total\s*fat", r"total\s*fats", r"fats", r"fat", r"lipides", r"grasas", r"fett"
                ])
                if val is not None:
                    results["fat_g"] = val

            # Saturated Fat
            if results["saturated_fat_g"] == 0.0:
                val = extract_row_value(line, [
                    r"saturated\s*fat", r"saturated\s*fatty\s*acids", r"sat\s*fat", r"saturated",
                    r"gesättigte\s*fettsäuren", r"acides\s*gras\s*saturés"
                ])
                if val is not None:
                    results["saturated_fat_g"] = val

            # Trans Fat
            if results["trans_fat_g"] == 0.0:
                val = extract_row_value(line, [r"trans\s*fat", r"trans\s*fatty\s*acids", r"trans\s*fats"])
                if val is not None:
                    results["trans_fat_g"] = val

            # Cholesterol
            if results["cholesterol_mg"] == 0.0:
                val = extract_row_value(line, [r"cholesterol", r"colesterol"])
                if val is not None:
                    results["cholesterol_mg"] = val

            # Dietary Fiber
            if results["fibre_g"] == 0.0:
                val = extract_row_value(line, [
                    r"dietary\s*fibre", r"dietary\s*fiber", r"fiber", r"fibre", r"fibers", r"fibres",
                    r"ballaststoffe", r"fibra"
                ])
                if val is not None:
                    results["fibre_g"] = val

            # Total Sugars
            if results["sugar_g"] == 0.0:
                val = extract_row_value(line, [
                    r"total\s*sugars", r"total\s*sugar", r"sugars", r"sugar", r"sucre", r"azúcares", r"zucker"
                ])
                if val is not None:
                    results["sugar_g"] = val

            # Sodium / Salt
            if results["sodium_mg"] == 0.0:
                is_salt = any(k in line.lower() for k in ["salt", "sel", "salz"])
                val = extract_row_value(line, [r"sodium", r"sod", r"na", r"natrium", r"salt", r"sel", r"salz"])
                if val is not None:
                    if is_salt:
                        val = round(val * 400.0, 1)  # salt (g) to sodium (mg)
                    elif "g" in line.lower() and "mg" not in line.lower():
                        val = round(val * 1000.0, 1)
                    results["sodium_mg"] = val

        return results

    @classmethod
    def extract_nutrition_with_gemini(cls, image_bytes: bytes) -> Optional[Dict[str, Any]]:
        """Attempt high-accuracy Vision AI extraction using Gemini API."""
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            return None

        try:
            b64_image = base64.b64encode(image_bytes).decode("utf-8")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
            
            prompt = """You are an expert nutrition label parser. Extract all nutritional facts from this nutrition facts label image.
Return ONLY valid JSON matching this exact structure:
{
  "energy_kcal": 0.0,
  "protein_g": 0.0,
  "carb_g": 0.0,
  "fat_g": 0.0,
  "saturated_fat_g": 0.0,
  "trans_fat_g": 0.0,
  "cholesterol_mg": 0.0,
  "sodium_mg": 0.0,
  "sugar_g": 0.0,
  "fibre_g": 0.0,
  "serving_size": "100g"
}
Rules:
- If both per 100g and per serving values exist, prefer per 100g values for base nutrition.
- If calories are in kJ, convert to kcal (kJ / 4.184).
- Extract numbers only as floats without unit text inside the numeric fields.
- Extract serving size string if indicated (e.g. '34g', '100g').
- Output ONLY JSON."""

            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": b64_image
                                }
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "responseMimeType": "application/json"
                }
            }

            with httpx.Client(timeout=15.0) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        content_parts = candidates[0].get("content", {}).get("parts", [])
                        if content_parts:
                            text_resp = content_parts[0].get("text", "")
                            # Parse JSON
                            cleaned_json = text_resp.strip()
                            if cleaned_json.startswith("```"):
                                cleaned_json = re.sub(r"^```(?:json)?\s*", "", cleaned_json)
                                cleaned_json = re.sub(r"\s*```$", "", cleaned_json)
                            parsed = json.loads(cleaned_json)
                            # Ensure all expected keys
                            return {
                                "energy_kcal": float(parsed.get("energy_kcal", 0.0) or 0.0),
                                "protein_g": float(parsed.get("protein_g", 0.0) or 0.0),
                                "carb_g": float(parsed.get("carb_g", 0.0) or 0.0),
                                "fat_g": float(parsed.get("fat_g", 0.0) or 0.0),
                                "saturated_fat_g": float(parsed.get("saturated_fat_g", 0.0) or 0.0),
                                "trans_fat_g": float(parsed.get("trans_fat_g", 0.0) or 0.0),
                                "cholesterol_mg": float(parsed.get("cholesterol_mg", 0.0) or 0.0),
                                "sodium_mg": float(parsed.get("sodium_mg", 0.0) or 0.0),
                                "sugar_g": float(parsed.get("sugar_g", 0.0) or 0.0),
                                "fibre_g": float(parsed.get("fibre_g", 0.0) or 0.0),
                                "serving_size": str(parsed.get("serving_size", "100g") or "100g")
                            }
        except Exception as e:
            logger.warning(f"Gemini Vision OCR extraction failed or unavailable: {e}")

        return None

    @classmethod
    def extract_nutrition_from_image(cls, image_bytes: bytes) -> Dict[str, Any]:
        """Main OCR pipeline entrypoint. Processes image bytes to extract nutritional labels.
        
        Attempts:
        1. Gemini Vision AI
        2. EasyOCR local reader
        3. Table Regex text parsing
        """
        # 1. Try Gemini Vision AI first if API key is active
        gemini_result = cls.extract_nutrition_with_gemini(image_bytes)
        if gemini_result and gemini_result.get("energy_kcal", 0.0) > 0:
            return {
                "status": "success",
                "extracted_text": "Extracted via High-Accuracy Vision AI",
                "parsed_nutrition": gemini_result
            }

        # 2. Local EasyOCR Pipeline
        if not PIL_AVAILABLE:
            return {
                "status": "error",
                "message": "PIL library is not available in the environment.",
                "parsed_nutrition": {}
            }

        extracted_text_list = []

        global EASYOCR_AVAILABLE
        if not EASYOCR_AVAILABLE:
            try:
                import easyocr
                EASYOCR_AVAILABLE = True
            except ImportError:
                EASYOCR_AVAILABLE = False

        if EASYOCR_AVAILABLE:
            try:
                import easyocr
                image = Image.open(io.BytesIO(image_bytes))
                if image.mode != "RGB":
                    image = image.convert("RGB")
                
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG')
                img_bytes = img_byte_arr.getvalue()

                reader = easyocr.Reader(['en'], gpu=False)
                results = reader.readtext(img_bytes)
                
                for (bbox, text, prob) in results:
                    extracted_text_list.append(text)
                
                logger.info(f"EasyOCR extracted text lines: {extracted_text_list}")
            except Exception as e:
                logger.warning(f"EasyOCR run failed: {str(e)}. Falling back to regex parser.")
        
        raw_text = "\n".join(extracted_text_list)
        
        if not raw_text:
            return {
                "status": "fallback",
                "message": "No text detected via local OCR engine. You can enter or confirm the labels manually.",
                "parsed_nutrition": {
                    "energy_kcal": 0.0,
                    "protein_g": 0.0,
                    "carb_g": 0.0,
                    "fat_g": 0.0,
                    "saturated_fat_g": 0.0,
                    "trans_fat_g": 0.0,
                    "cholesterol_mg": 0.0,
                    "fibre_g": 0.0,
                    "sodium_mg": 0.0,
                    "sugar_g": 0.0,
                    "serving_size": "100g"
                }
            }

        parsed = cls.parse_nutrition_text(raw_text)
        return {
            "status": "success",
            "extracted_text": raw_text,
            "parsed_nutrition": parsed
        }

    @classmethod
    def parse_label_image(cls, image_bytes: bytes) -> Dict[str, Any]:
        """Convenience method to extract nutrition facts and return unified structure."""
        res = cls.extract_nutrition_from_image(image_bytes)
        parsed = res.get("parsed_nutrition", {})
        return {
            "status": res.get("status", "success"),
            "detected_text": res.get("extracted_text", ""),
            "nutrients": parsed
        }
