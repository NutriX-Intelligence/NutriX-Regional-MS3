"""
NutriX - ML Extension (Optional)

Provides a scikit-learn / XGBoost based training pipeline that learns
recipe recommendation scores from user interaction data.

Features used:
  - Number of matching ingredients (normalised)
  - Ingredient match ratio
  - Health score
  - Protein content (g/100g)
  - Calorie content (kcal/100g)
  - Carb content (g/100g)
  - Fat content (g/100g)
  - Cuisine (one-hot encoded)
  - Difficulty (ordinal: Easy=1, Medium=2, Hard=3)
  - User goal (one-hot encoded)

Target: recommendation score (regression)

The pipeline supports:
  - Training a RandomForestRegressor or XGBRegressor
  - Saving/loading the model with joblib
  - Feature importance analysis
"""

import os
import json
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd
from rapidfuzz import fuzz

# Optional imports – gracefully degrade if scikit-learn isn't installed
try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import LabelEncoder
    from sklearn.metrics import mean_absolute_error, r2_score
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

try:
    import joblib
    HAS_JOBLIB = True
except ImportError:
    HAS_JOBLIB = False

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

MODEL_PATH = MODEL_DIR / "recipe_ranker.pkl"
ENCODER_PATH = MODEL_DIR / "label_encoders.pkl"
FEATURES_PATH = MODEL_DIR / "feature_names.json"


# ---------------------------------------------------------------------------
# Feature Engineering
# ---------------------------------------------------------------------------

def _extract_features_for_recipe(
    recipe: Dict[str, Any],
    user_ingredients: List[str],
    recipe_ingredients: List[str],
    goal: Optional[str] = None,
) -> Dict[str, float]:
    """Build feature vector for one (user_ings, recipe) pair."""
    from app.services.ingredient_matcher import compute_ingredient_match_score
    from app.services.health_scorer import HealthScorer

    match_score, matched, _ = compute_ingredient_match_score(
        user_ingredients, recipe_ingredients
    )
    health_score, _, _ = HealthScorer.score_from_nutrition_dict(recipe)

    features = {
        "match_score": match_score,
        "matched_count": len(matched),
        "total_user_ings": len(user_ingredients),
        "health_score": health_score,
        "protein_g": recipe.get("protein_g") or 0.0,
        "energy_kcal": recipe.get("energy_kcal") or 0.0,
        "carb_g": recipe.get("carb_g") or 0.0,
        "fat_g": recipe.get("fat_g") or 0.0,
        "fibre_g": recipe.get("fibre_g") or 0.0,
        "sugar_g": recipe.get("sugar_g") or 0.0,
        "sodium_mg": recipe.get("sodium_mg") or 0.0,
        "difficulty_num": {"Easy": 1, "Medium": 2, "Hard": 3}.get(
            recipe.get("difficulty", ""), 0
        ),
        "goal_fat_loss": 1.0 if goal and "fat loss" in goal.lower() else 0.0,
        "goal_muscle_gain": 1.0 if goal and "muscle" in goal.lower() else 0.0,
        "goal_weight_gain": 1.0 if goal and "weight gain" in goal.lower() else 0.0,
        "goal_maintenance": 1.0 if goal and goal.lower() == "maintenance" else 0.0,
    }
    return features


def prepare_training_data(
    interaction_records: List[Dict[str, Any]],
) -> Tuple[pd.DataFrame, np.ndarray]:
    """
    Convert raw interaction records into a feature matrix and target vector.

    Each record should have:
      user_ingredients: List[str]
      recipe_ingredients: List[str]
      recipe: dict with nutritional fields
      goal: str (optional)
      target_score: float  (the ground-truth rating / score)
    """
    rows = []
    targets = []
    for rec in interaction_records:
        feats = _extract_features_for_recipe(
            rec["recipe"],
            rec["user_ingredients"],
            rec["recipe_ingredients"],
            rec.get("goal"),
        )
        rows.append(feats)
        targets.append(rec.get("target_score", 0.0))

    df = pd.DataFrame(rows)
    return df, np.array(targets)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def train_model(
    interaction_records: List[Dict[str, Any]],
    model_type: str = "random_forest",
    test_size: float = 0.2,
    **kwargs,
) -> Dict[str, Any]:
    """
    Train a regression model on interaction data.

    model_type: 'random_forest' or 'xgboost'
    Returns training metrics and the trained model.
    """
    if not HAS_SKLEARN:
        return {"error": "scikit-learn is not installed. Run: pip install scikit-learn"}

    df, y = prepare_training_data(interaction_records)

    if len(df) < 10:
        return {"error": f"Not enough data to train (got {len(df)} samples, need ≥10)."}

    X_train, X_test, y_train, y_test = train_test_split(
        df.values, y, test_size=test_size, random_state=42
    )
    feature_names = df.columns.tolist()

    if model_type == "xgboost" and HAS_XGB:
        model = xgb.XGBRegressor(
            n_estimators=kwargs.get("n_estimators", 200),
            max_depth=kwargs.get("max_depth", 6),
            learning_rate=kwargs.get("learning_rate", 0.08),
            random_state=42,
            verbosity=0,
        )
    else:
        model = RandomForestRegressor(
            n_estimators=kwargs.get("n_estimators", 200),
            max_depth=kwargs.get("max_depth", 10),
            min_samples_leaf=kwargs.get("min_samples_leaf", 4),
            random_state=42,
            n_jobs=-1,
        )

    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    # Save model and metadata
    if HAS_JOBLIB:
        joblib.dump(model, MODEL_PATH)
        with open(FEATURES_PATH, "w") as f:
            json.dump(feature_names, f)
        # Save feature importances
        importances = model.feature_importances_
        feat_imp = sorted(
            zip(feature_names, importances), key=lambda x: x[1], reverse=True
        )
    else:
        feat_imp = []

    return {
        "model_type": model_type,
        "samples": len(df),
        "mae": round(mae, 4),
        "r2_score": round(r2, 4),
        "feature_importance": feat_imp[:15],
        "model_path": str(MODEL_PATH),
    }


def load_model():
    """Load the trained model from disk."""
    if not HAS_JOBLIB or not MODEL_PATH.exists():
        return None
    try:
        return joblib.load(MODEL_PATH)
    except Exception:
        return None


def predict_score(
    user_ingredients: List[str],
    recipe: Dict[str, Any],
    recipe_ingredients: List[str],
    goal: Optional[str] = None,
) -> float:
    """
    Use the trained ML model to predict a recommendation score.
    Falls back to rule-based scoring if no model is available.
    """
    model = load_model()
    if model is None:
        from app.services.recipe_ranker import compute_final_score
        from app.services.ingredient_matcher import compute_ingredient_match_score
        from app.services.health_scorer import HealthScorer

        match_score, _, _ = compute_ingredient_match_score(
            user_ingredients, recipe_ingredients
        )
        hs, _, _ = HealthScorer.score_from_nutrition_dict(recipe)
        return compute_final_score(
            match_score, hs,
            recipe.get("protein_g"),
            recipe.get("energy_kcal"),
        )

    feats = _extract_features_for_recipe(recipe, user_ingredients, recipe_ingredients, goal)
    with open(FEATURES_PATH) as f:
        expected_features = json.load(f)

    # Align feature vector with training order
    vec = np.array([[feats.get(f, 0.0) for f in expected_features]])
    pred = model.predict(vec)[0]
    return round(float(pred), 2)
