import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger("ocr_engine")

try:
    from PIL import Image
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

class OCREngine:
    # Regex patterns for various nutritional attributes
    CALORIE_PATTERNS = [
        r"(?i)(?:energy|calories|calorie|kcal|cal)\s*[:\-=\s]*\s*(\d+(?:\.\d+)?)"
    ]
    PROTEIN_PATTERNS = [
        r"(?i)(?:protein|proteins|prot)\s*[:\-=\s]*\s*(\d+(?:\.\d+)?)\s*(?:g|grams)?"
    ]
    CARB_PATTERNS = [
        r"(?i)(?:carbohydrate|carbohydrates|carb|carbs|total carbohydrate)\s*[:\-=\s]*\s*(\d+(?:\.\d+)?)\s*(?:g|grams)?"
    ]
    FAT_PATTERNS = [
        r"(?i)(?:fat|fats|total fat)\s*[:\-=\s]*\s*(\d+(?:\.\d+)?)\s*(?:g|grams)?"
    ]
    SUGAR_PATTERNS = [
        r"(?i)(?:sugar|sugars|free sugar|added sugar)\s*[:\-=\s]*\s*(\d+(?:\.\d+)?)\s*(?:g|grams)?"
    ]
    SODIUM_PATTERNS = [
        r"(?i)(?:sodium|sod|na)\s*[:\-=\s]*\s*(\d+(?:\.\d+)?)\s*(mg|g)?"
    ]
    FIBER_PATTERNS = [
        r"(?i)(?:fiber|fibre|dietary fiber)\s*[:\-=\s]*\s*(\d+(?:\.\d+)?)\s*(?:g|grams)?"
    ]

    @classmethod
    def parse_nutrition_text(cls, text: str) -> Dict[str, float]:
        """Parse raw text lines using regular expressions to extract nutritional values.
        
        Returns:
            Dict containing energy_kcal, protein_g, carb_g, fat_g, fibre_g, sodium_mg, sugar_g.
        """
        # Split text into lines for individual parsing
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        results = {
            "energy_kcal": 0.0,
            "protein_g": 0.0,
            "carb_g": 0.0,
            "fat_g": 0.0,
            "fibre_g": 0.0,
            "sodium_mg": 0.0,
            "sugar_g": 0.0
        }

        # Helper to search line by line using patterns
        def match_patterns(patterns: List[str], text_to_search: str):
            for pat in patterns:
                m = re.search(pat, text_to_search)
                if m:
                    return m.group(1), m.groups()[-1] if len(m.groups()) > 1 else None
            return None, None

        for line in lines:
            # Calories
            val, _ = match_patterns(cls.CALORIE_PATTERNS, line)
            if val and results["energy_kcal"] == 0.0:
                results["energy_kcal"] = float(val)

            # Protein
            val, _ = match_patterns(cls.PROTEIN_PATTERNS, line)
            if val and results["protein_g"] == 0.0:
                results["protein_g"] = float(val)

            # Carbs
            val, _ = match_patterns(cls.CARB_PATTERNS, line)
            if val and results["carb_g"] == 0.0:
                results["carb_g"] = float(val)

            # Fat
            val, _ = match_patterns(cls.FAT_PATTERNS, line)
            if val and results["fat_g"] == 0.0:
                results["fat_g"] = float(val)

            # Sugar
            val, _ = match_patterns(cls.SUGAR_PATTERNS, line)
            if val and results["sugar_g"] == 0.0:
                results["sugar_g"] = float(val)

            # Fiber
            val, _ = match_patterns(cls.FIBER_PATTERNS, line)
            if val and results["fibre_g"] == 0.0:
                results["fibre_g"] = float(val)

            # Sodium
            val, unit = match_patterns(cls.SODIUM_PATTERNS, line)
            if val and results["sodium_mg"] == 0.0:
                sod_val = float(val)
                # If unit is 'g' (e.g. 1.2g), convert to mg (1200mg)
                if unit and unit.lower() == "g":
                    sod_val *= 1000.0
                results["sodium_mg"] = sod_val

        return results

    @classmethod
    def extract_nutrition_from_image(cls, image_bytes: bytes) -> Dict[str, Any]:
        """Main OCR pipeline entrypoint. Processes image bytes to extract nutritional labels.
        
        Returns:
            Dict containing parsed nutrition dictionary and status indicator.
        """
        if not PIL_AVAILABLE:
            return {
                "status": "error",
                "message": "PIL library is not available in the environment.",
                "parsed_nutrition": {}
            }

        extracted_text_list = []

        if EASYOCR_AVAILABLE:
            try:
                # Load image from bytes
                image = Image.open(io.BytesIO(image_bytes))
                # Convert image to RGB if not already
                if image.mode != "RGB":
                    image = image.convert("RGB")
                
                # We need to save to a temporary memory buffer because EasyOCR works best on file paths or numpy arrays
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG')
                img_bytes = img_byte_arr.getvalue()

                # Initialize reader
                reader = easyocr.Reader(['en'], gpu=False) # offline en-only OCR
                results = reader.readtext(img_bytes)
                
                # Extract words
                for (bbox, text, prob) in results:
                    extracted_text_list.append(text)
                
                logger.info(f"EasyOCR extracted text lines: {extracted_text_list}")
            except Exception as e:
                logger.warning(f"EasyOCR run failed: {str(e)}. Falling back to mock text parser.")
        
        # If no text was extracted (either easyocr failed or not available),
        # we try standard fallbacks or return instructions.
        raw_text = "\n".join(extracted_text_list)
        
        if not raw_text:
            # Return empty structure with flag so endpoint can ask for raw text input
            return {
                "status": "fallback",
                "message": "No text detected via local OCR engine. Please type/confirm the labels manually.",
                "parsed_nutrition": {
                    "energy_kcal": 0.0,
                    "protein_g": 0.0,
                    "carb_g": 0.0,
                    "fat_g": 0.0,
                    "fibre_g": 0.0,
                    "sodium_mg": 0.0,
                    "sugar_g": 0.0
                }
            }

        parsed = cls.parse_nutrition_text(raw_text)
        return {
            "status": "success",
            "extracted_text": raw_text,
            "parsed_nutrition": parsed
        }
