"""
NutriX - Rule-based Explanation Engine

Generates human-readable, deterministic explanations for recipe
recommendations. All logic is rule-based — no LLM calls.

Explanations cover:
  - Ingredient match quality
  - Health score interpretation
  - Goal suitability (weight loss, muscle gain, etc.)
  - Macro highlights (high protein, low carb, etc.)
"""

from typing import Dict, List, Optional, Any


class ExplanationEngine:
    """Stateless engine that generates explanation strings from structured data."""

    @staticmethod
    def generate(
        recipe_name: str,
        match_score: float,
        health_score: float,
        health_category: str,
        health_explanation: str,
        matched_ingredients: List[str],
        unmatched_ingredients: List[str],
        user_ingredients: List[str],
        protein_g: Optional[float] = None,
        energy_kcal: Optional[float] = None,
        carb_g: Optional[float] = None,
        fat_g: Optional[float] = None,
        goal: Optional[str] = None,
        cuisine: Optional[str] = None,
        difficulty: Optional[str] = None,
        dietary_tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a complete explanation for a recipe recommendation.

        Returns a dict with keys:
          summary, bullet_points (list), suitability, health_note
        """
        bullets: List[str] = []
        total_user = len(user_ingredients)
        matched_count = len(matched_ingredients)

        # --- Dietary Classification ---
        if dietary_tag:
            dt = dietary_tag.lower()
            if dt == "jain":
                bullets.append("🌱 Jain (Vegetarian — No onion, garlic, or root vegetables)")
            elif dt == "vegan":
                bullets.append("🌱 Vegan (100% Plant-based — Dairy-free & Vegetarian)")
            elif dt == "vegetarian":
                bullets.append("🥛 Vegetarian (Lacto-Vegetarian — Dairy allowed, No meat/eggs)")
            elif dt == "eggetarian":
                bullets.append("🥚 Eggetarian (Allows eggs & dairy — No meat or fish)")
            elif dt == "non-vegetarian":
                bullets.append("🍖 Non-Vegetarian (Contains meat, poultry, or seafood)")

        # --- Ingredient match ---
        if matched_count == total_user:
            bullets.append(f"✅ Uses all {total_user} of your ingredients")
        elif matched_count > 0:
            pct = int(match_score * 100)
            bullets.append(f"✅ Contains {pct}% of your ingredients ({matched_count}/{len(user_ingredients)})")

        if unmatched_ingredients:
            # Show at most 3 extra ingredients needed
            extras = unmatched_ingredients[:3]
            bullets.append(f"🛒 You'll also need: {', '.join(extras)}")

        # --- Health score ---
        if health_score >= 70:
            bullets.append(f"🥗 {health_category} — {health_explanation}")
        elif health_score >= 40:
            bullets.append(f"⚖️ {health_category} — {health_explanation}")
        else:
            bullets.append(f"⚠️ {health_category} — {health_explanation}")

        # --- Macro highlights ---
        if protein_g is not None:
            if protein_g >= 15:
                bullets.append(f"💪 High protein ({protein_g:.1f}g/100g)")
            elif protein_g >= 10:
                bullets.append(f"👍 Good protein source ({protein_g:.1f}g/100g)")

        if energy_kcal is not None:
            if energy_kcal < 100:
                bullets.append(f"🔥 Low calorie ({int(energy_kcal)} kcal/100g)")
            elif energy_kcal > 300:
                bullets.append(f"⚠️ Higher calorie ({int(energy_kcal)} kcal/100g)")

        if carb_g is not None and carb_g < 10:
            bullets.append(f"🌾 Low carb ({carb_g:.1f}g/100g)")

        if fat_g is not None and fat_g < 5:
            bullets.append(f"🥑 Low fat ({fat_g:.1f}g/100g)")

        # --- Goal suitability ---
        suitability = ""
        if goal:
            gl = goal.lower()
            if gl == "fat loss":
                if energy_kcal is not None and energy_kcal < 150:
                    suitability = "✅ Suitable for weight loss (low calorie density)"
                elif protein_g is not None and protein_g >= 12 and (energy_kcal or 999) < 250:
                    suitability = "✅ Good for weight loss — high protein keeps you full"
                else:
                    suitability = "Moderate for weight loss — watch portion size"
            elif gl in ("weight gain", "muscle gain"):
                if energy_kcal is not None and energy_kcal > 200:
                    suitability = "✅ Good for weight/muscle gain (calorie dense)"
                elif protein_g is not None and protein_g >= 12:
                    suitability = "✅ Good for muscle gain (high protein)"
                else:
                    suitability = "Moderate — consider adding a protein side"
            elif gl == "maintenance":
                suitability = "✅ Fits a balanced maintenance diet"

        # --- Cuisine / Difficulty bonus ---
        extra_note = ""
        if cuisine:
            extra_note += f"Cuisine: {cuisine}. "
        if difficulty:
            extra_note += f"Difficulty: {difficulty}."

        summary = "; ".join(bullets)

        return {
            "summary": summary,
            "bullet_points": bullets,
            "suitability": suitability,
            "health_note": f"Health Score: {health_score:.0f}/100 ({health_category})",
            "extra": extra_note.strip(),
        }

    @staticmethod
    def generate_brief(
        match_score: float,
        health_score: float,
        health_category: str,
        matched_count: int,
        total_user_ingredients: int,
        protein_g: Optional[float] = None,
    ) -> str:
        """Generate a one-line explanation string (for list views)."""
        parts: List[str] = []

        match_pct = int(match_score * 100)
        parts.append(f"{match_pct}% ingredient match")

        if health_category:
            parts.append(f"Health: {health_category}")

        if protein_g is not None and protein_g >= 12:
            parts.append("High protein")

        return " | ".join(parts)
