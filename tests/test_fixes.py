import re
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine, get_db
from app.models import User, Profile, UserPreference, Recipe, RecipeNutrition, RecipeIngredient, HomelyMeal, HomelyMealNutrition
from app.services.ocr_engine import OCREngine
from app.services.optimization_engine import OptimizationEngine

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield


def test_ocr_label_parser_on_real_packaging():
    """Test OCR table-aware regex extraction on real multi-column Indian nutrition facts label."""
    sample_label_text = """
    NUTRITION FACTS
    Approximate Value
    Serving per Pack 3
    Nutritions per 100g per serve(34g) ^%RDA per serve (34g)
    Energy (kcal) 533 181 9%
    Total Fat (g) 28 10 14%
    Saturated Fat (g) 13 4 20%
    Trans Fat (g) 0 0 0%
    Cholesterol (mg) 3 1 -
    Sodium (mg) 417 142 7%
    Carbohydrate (g) 66 22 -
    Total Sugars (g) 2 0.5 -
    Added Sugars (g) 0 0 0%
    Dietary Fibre (g) 4 1 -
    Protein (g) 3 1 -
    """
    
    parsed = OCREngine.parse_nutrition_text(sample_label_text)
    
    assert parsed["energy_kcal"] == 533.0
    assert parsed["fat_g"] == 28.0
    assert parsed["saturated_fat_g"] == 13.0
    assert parsed["trans_fat_g"] == 0.0
    assert parsed["cholesterol_mg"] == 3.0
    assert parsed["sodium_mg"] == 417.0
    assert parsed["carb_g"] == 66.0
    assert parsed["sugar_g"] == 2.0
    assert parsed["fibre_g"] == 4.0
    assert parsed["protein_g"] == 3.0
    assert "34g" in parsed["serving_size"] or "3" in parsed["serving_size"]


def test_jain_compliance_in_meal_optimizer():
    """Ensure that a user with Jain diet type never receives chicken, meat, or non-veg dishes."""
    db = next(get_db())
    
    # Create or fetch test Jain user
    test_user = db.query(User).filter(User.email == "jain_test_user@nutrix.io").first()
    if not test_user:
        test_user = User(
            name="Jain Tester",
            email="jain_test_user@nutrix.io",
            hashed_password="testpassword123"
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)

    # Set profile with Jain diet
    prof = db.query(Profile).filter(Profile.user_id == test_user.id).first()
    if not prof:
        prof = Profile(
            user_id=test_user.id,
            age=30,
            gender="female",
            height=165.0,
            weight=58.0,
            activity_level="moderate",
            goal="maintenance",
            diet_type="Jain",
            target_calories=1800.0,
            target_protein=80.0,
            target_carbs=225.0,
            target_fat=55.0
        )
        db.add(prof)
    else:
        prof.diet_type = "Jain"
        prof.target_calories = 1800.0
    db.commit()
    db.refresh(test_user)

    # Generate daily plan automatically without user-selected tolerance
    plan = OptimizationEngine.generate_daily_plan(
        db=db,
        user_id=test_user.id,
        tolerance=None,
        preference="balanced"
    )

    assert plan is not None
    assert "meals" in plan
    
    for slot, meal in plan["meals"].items():
        recipe_name = (meal.get("recipe_name") or "").lower()
        # Verify no chicken, egg, meat or non-veg dishes
        assert "chicken" not in recipe_name, f"Jain plan contained chicken in {slot}: {recipe_name}"
        assert "mutton" not in recipe_name, f"Jain plan contained mutton in {slot}: {recipe_name}"
        assert "fish" not in recipe_name, f"Jain plan contained fish in {slot}: {recipe_name}"
        assert "pork" not in recipe_name, f"Jain plan contained pork in {slot}: {recipe_name}"
        assert not re.search(r"\beggs?\b", recipe_name), f"Jain plan contained egg in {slot}: {recipe_name}"


def test_builder_defaults_api():
    """Verify builder-defaults API returns base meals and 15+ condiments."""
    res = client.get("/api/homely/builder-defaults")
    assert res.status_code == 200
    data = res.json()
    
    assert "base_meals" in data
    assert "condiments" in data
    assert len(data["base_meals"]) >= 6
    assert len(data["condiments"]) >= 10
    
    # Check specific condiments
    cond_ids = [c["id"] for c in data["condiments"]]
    assert "green_chutney" in cond_ids
    assert "imli_chutney" in cond_ids
    assert "garlic_chutney" in cond_ids
    assert "coconut_chutney" in cond_ids
    assert "crispy_sev" in cond_ids
    assert "grated_paneer" in cond_ids
    assert "shredded_cheese" in cond_ids


def test_user_diet_type_property_fallback():
    """Test User.diet_type property fallback to user_preferences."""
    db = next(get_db())
    existing = db.query(User).filter(User.email == "pref_diet_tester@nutrix.io").first()
    if existing:
        db.delete(existing)
        db.commit()

    u = User(
        name="Pref User",
        email="pref_diet_tester@nutrix.io",
        hashed_password="pw"
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    
    pref = UserPreference(
        user_id=u.id,
        preference_type="diet_type",
        value="Jain"
    )
    db.add(pref)
    db.commit()
    
    reloaded_u = db.query(User).filter(User.id == u.id).first()
    assert reloaded_u.diet_type == "Jain"
    
    db.delete(reloaded_u)
    db.commit()
