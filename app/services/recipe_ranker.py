"""
NutriX - Recipe Ranking Engine

Combines ingredient match score, health score, and macro bonuses/penalties
into a single final_score used to rank recipe recommendations.

Final ranking formula:

    final_score =
        ingredient_match_score * W_MATCH
        + health_score_normalised * W_HEALTH
        + protein_bonus
        - calorie_penalty

Where:
  - W_MATCH   = 50 (weight for ingredient match)
  - W_HEALTH  = 30 (weight for health score)
  - protein_bonus  = +15 if protein per 100g ≥ 12g, +8 if ≥ 8g
  - calorie_penalty = scaled penalty for very high-calorie recipes
"""

from typing import Dict, List, Optional, Any

# Weights
W_MATCH = 50.0
W_HEALTH = 30.0

# Bonus / penalty thresholds
HIGH_PROTEIN_THRESHOLD = 12.0  # g / 100g → +15 bonus
MED_PROTEIN_THRESHOLD = 8.0    # g / 100g → +8 bonus
HIGH_CAL_THRESHOLD = 300.0     # kcal / 100g → penalty starts
MAX_CAL_PENALTY = 20.0


def _protein_bonus(protein_g: Optional[float]) -> float:
    if not protein_g:
        return 0.0
    if protein_g >= HIGH_PROTEIN_THRESHOLD:
        return 15.0
    if protein_g >= MED_PROTEIN_THRESHOLD:
        return 8.0
    return 0.0


def _calorie_penalty(calories: Optional[float]) -> float:
    if not calories or calories < HIGH_CAL_THRESHOLD:
        return 0.0
    excess = (calories - HIGH_CAL_THRESHOLD) / 100.0
    return min(excess * 5.0, MAX_CAL_PENALTY)


def compute_final_score(
    ingredient_match_score: float,   # 0.0 – 1.0
    health_score: float,             # 0–100
    protein_g: Optional[float] = None,
    energy_kcal: Optional[float] = None,
) -> float:
    """
    Compute the final ranking score for one recipe.

    Returns a float (higher = better recommendation).
    """
    # Normalise health score to 0-1
    health_norm = health_score / 100.0

    match_component = ingredient_match_score * W_MATCH
    health_component = health_norm * W_HEALTH
    prot_bonus = _protein_bonus(protein_g)
    cal_penalty = _calorie_penalty(energy_kcal)

    final = match_component + health_component + prot_bonus - cal_penalty
    return round(final, 2)


def rank_recipes(
    recipes: List[Dict[str, Any]],
    user_ingredients: List[str],
    ingredient_scores: Optional[Dict[str, float]] = None,
    health_scores: Optional[Dict[str, float]] = None,
    goal: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Rank a list of recipe dicts by final score.

    Each recipe dict should contain:
      recipe_code, recipe_name, ingredients (list of str),
      protein_g (per 100g), energy_kcal (per 100g)

    Optionally passes pre-computed scores via ingredient_scores and
    health_scores dicts (keyed by recipe_code).

    Returns the same dicts sorted descending by final_score with
    'final_score' and 'matched_ingredients' added.
    """
    for recipe in recipes:
        code = recipe["recipe_code"]

        match_score = (
            ingredient_scores.get(code, {}).get("score", 0.0)
            if ingredient_scores else 0.0
        )
        hs = (
            health_scores.get(code, 0.0)
            if health_scores else 50.0
        )

        prot = recipe.get("protein_g")
        cal = recipe.get("energy_kcal")

        # Goal-based adjustments
        goal_mult = 1.0
        if goal and goal.lower() == "weight loss":
            # Prefer lower calorie
            goal_mult = 0.85 if cal and cal > 250 else 1.1
        elif goal and goal.lower() == "muscle gain":
            # Prefer higher protein
            if prot and prot >= 15:
                goal_mult = 1.15

        final = compute_final_score(match_score, hs, prot, cal) * goal_mult
        recipe["final_score"] = round(final, 2)
        recipe["ingredient_match_score"] = round(match_score, 2)
        recipe["health_score"] = round(hs, 2)

    recipes.sort(key=lambda r: r["final_score"], reverse=True)
    return recipes
