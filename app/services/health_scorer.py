"""
NutriX - Health Scoring Engine

Calculates a 0-100 health score for recipes based on their nutritional
profile (calories, protein, sugar, sodium, fat) and categorises them
as Healthy, Moderate, or Unhealthy.

The scoring model:
  - Rewards: high protein, high fibre
  - Penalises: high sugar, high sodium, excessive saturated fat
  - Moderates: total calories (extremes are penalised)
"""

from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Reference values (per 100 g of food)
# ---------------------------------------------------------------------------
# These are based on Codex / FDA / ICMR guidance adapted for Indian cuisine.

_OPTIMAL_PROTEIN_G = 15.0       # g / 100g
_OPTIMAL_FIBRE_G = 5.0          # g / 100g
_MAX_SUGAR_G = 10.0             # g / 100g  (max before heavy penalty)
_MAX_SODIUM_MG = 400.0          # mg / 100g
_OPTIMAL_FAT_G = 15.0           # g / 100g  (moderate, not too low, not too high)
_IDEAL_CALORIES = 150.0         # kcal / 100g  (sweet spot ~150-200)
_MAX_CALORIES = 350.0           # kcal / 100g  (above this → penalty)

# Weights for the final score components
W_PROTEIN = 25.0
W_FIBRE = 15.0
W_SUGAR = -20.0
W_SODIUM = -15.0
W_FAT = -10.0
W_CALORIES = -15.0

# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------


class HealthScorer:
    """Stateless health-scoring utility."""

    @staticmethod
    def score_from_nutrition_dict(nutrition: Dict[str, Optional[float]]) -> Tuple[float, str, str]:
        """
        Compute health score from a nutrition dictionary.

        Expected keys (all optional, default to 0):
          energy_kcal, protein_g, freesugar_g (or sugar_g),
          sodium_mg, fat_g, fibre_g

        Returns (score_0_100, category, explanation).
        """
        energy = nutrition.get("energy_kcal") or 0.0
        protein = nutrition.get("protein_g") or 0.0
        sugar = nutrition.get("freesugar_g") or nutrition.get("sugar_g") or 0.0
        sodium = nutrition.get("sodium_mg") or 0.0
        fat = nutrition.get("fat_g") or 0.0
        fibre = nutrition.get("fibre_g") or 0.0

        if energy <= 0:
            # No nutrition data – neutral score
            return 50.0, "Moderate", "Nutrition data unavailable."

        return HealthScorer._compute(protein, fibre, sugar, sodium, fat, energy)

    @staticmethod
    def score_from_per_serving(nutrition_obj) -> Tuple[float, str, str]:
        """
        Compute health score from a SQLAlchemy RecipeNutrition object
        using per-100g values for standardised comparison.
        """
        if not nutrition_obj:
            return 50.0, "Moderate", "No nutrition data."

        energy = nutrition_obj.energy_kcal or 0.0
        protein = nutrition_obj.protein_g or 0.0
        sugar = nutrition_obj.freesugar_g or 0.0
        sodium = nutrition_obj.sodium_mg or 0.0
        fat = nutrition_obj.fat_g or 0.0
        fibre = nutrition_obj.fibre_g or 0.0

        if energy <= 0:
            return 50.0, "Moderate", "Nutrition data unavailable."

        return HealthScorer._compute(protein, fibre, sugar, sodium, fat, energy)

    @classmethod
    def _compute(cls, protein: float, fibre: float, sugar: float,
                 sodium: float, fat: float, energy: float) -> Tuple[float, str, str]:
        """Core scoring logic."""
        # --- Component scores (0–1 range) ---

        # Protein: reward up to optimal, plateau after
        prot_score = min(protein / _OPTIMAL_PROTEIN_G, 1.5)

        # Fibre
        fibre_score = min(fibre / _OPTIMAL_FIBRE_G, 1.5)

        # Sugar: linear penalty after threshold
        sugar_penalty = 0.0
        if sugar > _MAX_SUGAR_G:
            sugar_penalty = min((sugar - _MAX_SUGAR_G) / 20.0, 2.0)

        # Sodium: linear penalty after threshold
        sodium_penalty = 0.0
        if sodium > _MAX_SODIUM_MG:
            sodium_penalty = min((sodium - _MAX_SODIUM_MG) / 500.0, 2.0)

        # Fat: penalty if too high (don't penalise moderate fat)
        fat_penalty = 0.0
        if fat > _OPTIMAL_FAT_G * 1.5:
            fat_penalty = min((fat - _OPTIMAL_FAT_G * 1.5) / 30.0, 2.0)

        # Calories: bell-curve around ideal
        cal_score = 1.0
        if energy < 50:
            cal_score = 0.3  # very low cal may be a drink, not a meal
        elif energy > _IDEAL_CALORIES:
            ratio = energy / _IDEAL_CALORIES
            if ratio > 2.0:
                cal_penalty = min((ratio - 2.0) * 0.5, 2.0)
                cal_score = max(0.0, 1.0 - cal_penalty)

        # --- Weighted sum → raw score ---
        raw = (W_PROTEIN * prot_score +
               W_FIBRE * fibre_score +
               W_SUGAR * sugar_penalty +
               W_SODIUM * sodium_penalty +
               W_FAT * fat_penalty +
               W_CALORIES * (1.0 - cal_score))

        # Shift to 0-100 range
        # Theoretical min ≈ -(20+15+10+15) = -60, max ≈ (25+15) = 40
        # So we shift by +60 and scale
        shifted = raw + 60.0
        score = max(0.0, min(100.0, shifted * 1.2))  # scale factor ≈1.2

        # --- Category ---
        if score >= 70.0:
            category = "Healthy"
        elif score >= 40.0:
            category = "Moderate"
        else:
            category = "Unhealthy"

        # --- Explanation fragments ---
        reasons: List[str] = []
        if prot_score >= 0.8:
            reasons.append(f"Good protein ({protein:.1f}g/100g)")
        elif prot_score < 0.3:
            reasons.append("Low protein")
        if fibre_score >= 0.8:
            reasons.append(f"High fibre ({fibre:.1f}g/100g)")
        if sugar_penalty > 0.5:
            reasons.append(f"High sugar ({sugar:.1f}g/100g)")
        if sodium_penalty > 0.5:
            reasons.append(f"High sodium ({sodium:.0f}mg/100g)")
        if fat_penalty > 0.5:
            reasons.append(f"High fat ({fat:.1f}g/100g)")

        explanation = "; ".join(reasons) if reasons else "Balanced nutrition."

        return round(score, 2), category, explanation
