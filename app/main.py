import os
# Load .env file manually if it exists
try:
    from pathlib import Path
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")
except Exception:
    pass

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from app.db import get_db, engine, Base
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    verify_google_id_token,
)
from app import models, schemas
from app.services.nutrition_engine import NutritionEngine
from app.services.recommendation_engine import RecommendationEngine
from app.services.optimization_engine import OptimizationEngine
from app.services.adaptive_planner import AdaptivePlanner
from app.services.ingredient_matcher import (
    compute_ingredient_match_score,
    normalise,
    clean_ingredient,
    fuzzy_match_ingredient,
)
from app.services.health_scorer import HealthScorer
from app.services.recipe_ranker import compute_final_score
from app.services.explanation_engine import ExplanationEngine
from app.services.classification_engine import ClassificationEngine
from app.services.barcode_service import BarcodeService
from app.services.ocr_engine import OCREngine
from app.services.analytics_engine import AnalyticsEngine
from app import schemas_recipes
from app.services import homely_meals_engine

# Create tables in the SQLite database if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="NutriX AI Diet Planner API",
    description="Intelligent, production-grade nutrition recommendation and meal plan optimization system.",
    version="1.0.0"
)

from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path

@app.get("/", response_class=HTMLResponse)
def read_root():
    template_path = Path(__file__).resolve().parent / "templates" / "index.html"
    if not template_path.exists():
        return HTMLResponse(content="<h1>NutriX - AI Diet Planner</h1><p>Frontend template not found.</p>")
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "NutriX AI Diet Planner"}


# =====================================================================
# AUTHENTICATION & SETTINGS SERVICES
# =====================================================================

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> models.User:
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email: str = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def format_user_profile(user: models.User) -> Dict[str, Any]:
    # Compute targets using NutritionEngine
    targets = NutritionEngine.calculate_targets(
        age=user.age or 25,
        gender=user.gender or "male",
        height=user.height or 170.0,
        weight=user.weight or 70.0,
        activity_level=user.activity_level or "sedentary",
        goal=user.goal or "maintenance"
    )
    
    # Get preferences
    diet_type = "Non-Vegetarian"
    likes_list = []
    allergies_list = []
    dislikes_list = []
    for p in user.preferences:
        t = p.preference_type.lower()
        val = p.value.strip()
        if t == "diet_type":
            diet_type = val
        elif t == "like":
            likes_list.append(val)
        elif t == "allergy":
            allergies_list.append(val)
        elif t == "dislike":
            dislikes_list.append(val)

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "age": user.age or 25,
        "gender": user.gender or "male",
        "height": user.height or 170.0,
        "weight": user.weight or 70.0,
        "activity_level": user.activity_level or "sedentary",
        "goal": user.goal or "maintenance",
        "target_calories": user.target_calories or targets.get("target_calories") or 2000.0,
        "target_protein": user.target_protein or targets.get("target_protein_g") or 120.0,
        "target_carbs": user.target_carbs or targets.get("target_carbs_g") or 250.0,
        "target_fat": user.target_fat or targets.get("target_fat_g") or 60.0,
        "bmi": targets.get("bmi"),
        "bmi_status": targets.get("bmi_status"),
        "bmr": targets.get("bmr"),
        "tdee": targets.get("tdee"),
        "created_at": user.created_at,
        "diet_type": diet_type,
        "likes": ", ".join(likes_list),
        "allergies": ", ".join(allergies_list),
        "dislikes": ", ".join(dislikes_list),
    }

@app.post("/api/auth/register", response_model=schemas.AuthTokenResponse, status_code=status.HTTP_201_CREATED)
def register_user(req: schemas.UserRegisterRequest, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(models.User).filter(models.User.email == req.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    # Compute targets using NutritionEngine
    targets = NutritionEngine.calculate_targets(
        age=req.age,
        gender=req.gender,
        height=req.height,
        weight=req.weight,
        activity_level=req.activity_level,
        goal=req.goal
    )

    # Create new user
    user = models.User(
        name=req.name,
        email=req.email,
        hashed_password=hash_password(req.password),
        age=req.age,
        gender=req.gender,
        height=req.height,
        weight=req.weight,
        activity_level=req.activity_level,
        goal=req.goal,
        target_calories=targets["target_calories"],
        target_protein=targets["target_protein_g"],
        target_carbs=targets["target_carbs_g"],
        target_fat=targets["target_fat_g"]
    )
    db.add(user)
    db.flush() # Eagerly generate ID

    # Save preferences if provided
    if req.preferences:
        for pref in req.preferences:
            db_pref = models.UserPreference(
                user_id=user.id,
                preference_type=pref.preference_type,
                value=pref.value
            )
            db.add(db_pref)

    db.commit()
    db.refresh(user)

    # Generate JWT
    token_data = {"sub": user.email, "id": user.id}
    access_token = create_access_token(data=token_data)

    user_profile = format_user_profile(user)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_profile
    }

@app.post("/api/auth/login", response_model=schemas.AuthTokenResponse)
def login_user(req: schemas.UserLoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == req.email).first()
    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )

    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password."
        )

    token_data = {"sub": user.email, "id": user.id}
    access_token = create_access_token(data=token_data)

    user_profile = format_user_profile(user)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_profile
    }

@app.post("/api/auth/google", response_model=schemas.AuthTokenResponse)
async def login_google(req: schemas.GoogleLoginRequest, db: Session = Depends(get_db)):
    try:
        payload = await verify_google_id_token(req.id_token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Google authentication failed: {str(e)}"
        )

    email = payload.get("email")
    name = payload.get("name", "Google User")
    google_id = payload.get("sub")
    picture = payload.get("picture")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google ID token does not contain a valid email address."
        )

    # Check if user exists
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        # Create a new user with default metrics
        targets = NutritionEngine.calculate_targets(
            age=25,
            gender="male",
            height=170.0,
            weight=70.0,
            activity_level="sedentary",
            goal="maintenance"
        )
        user = models.User(
            name=name,
            email=email,
            google_id=google_id,
            avatar_url=picture,
            age=25,
            gender="male",
            height=170.0,
            weight=70.0,
            activity_level="sedentary",
            goal="maintenance",
            target_calories=targets["target_calories"],
            target_protein=targets["target_protein_g"],
            target_carbs=targets["target_carbs_g"],
            target_fat=targets["target_fat_g"]
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # Update google_id and avatar if not set
        updated = False
        if not user.google_id:
            user.google_id = google_id
            updated = True
        if picture and not user.avatar_url:
            user.avatar_url = picture
            updated = True
        if updated:
            db.commit()
            db.refresh(user)

    token_data = {"sub": user.email, "id": user.id}
    access_token = create_access_token(data=token_data)

    user_profile = format_user_profile(user)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_profile
    }

@app.get("/api/auth/me", response_model=schemas.UserProfileResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    return format_user_profile(current_user)

@app.post("/api/auth/me", response_model=schemas.UserProfileResponse)
def post_me(current_user: models.User = Depends(get_current_user)):
    return format_user_profile(current_user)

@app.post("/api/auth/reset-password")
def reset_password(req: schemas.PasswordResetRequest, db: Session = Depends(get_db)):
    import logging
    logger = logging.getLogger("auth_reset")
    user = db.query(models.User).filter(models.User.email == req.email).first()
    if not user:
        logger.warning(f"Password reset requested for non-existent email: {req.email}")
        return {"status": "success", "message": "If the email exists, a password reset link has been simulated."}

    import uuid
    reset_token = str(uuid.uuid4())
    simulated_link = f"http://localhost:8000/api/auth/reset-confirm?token={reset_token}&email={user.email}"
    
    print("------------------------------------------------------------")
    print(f"SIMULATED EMAIL: Password reset requested for {user.name} ({user.email})")
    print(f"Simulated Reset Link: {simulated_link}")
    print("------------------------------------------------------------")
    logger.info(f"Simulated reset link for {user.email}: {simulated_link}")

    return {"status": "success", "message": "Password reset link has been simulated in console logs."}

@app.get("/api/search-history", response_model=List[schemas.SearchHistoryResponse])
def get_search_history(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    history = db.query(models.SearchHistory).filter(
        models.SearchHistory.user_id == current_user.id
    ).order_by(models.SearchHistory.searched_at.desc()).limit(50).all()
    return history

@app.post("/api/search-history", response_model=schemas.SearchHistoryResponse, status_code=status.HTTP_201_CREATED)
def add_search_history(req: schemas.SearchHistoryCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_history = models.SearchHistory(
        user_id=current_user.id,
        query=req.query
    )
    db.add(db_history)
    db.commit()
    db.refresh(db_history)
    return db_history

@app.get("/api/settings", response_model=List[schemas.SettingsResponse])
def get_settings(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_settings = db.query(models.Settings).filter(
        models.Settings.user_id == current_user.id
    ).all()
    return user_settings

@app.put("/api/settings", response_model=schemas.SettingsResponse)
def update_settings(req: schemas.SettingsUpdate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_setting = db.query(models.Settings).filter(
        models.Settings.user_id == current_user.id,
        models.Settings.key == req.key
    ).first()

    if db_setting:
        db_setting.value = req.value
    else:
        db_setting = models.Settings(
            user_id=current_user.id,
            key=req.key,
            value=req.value
        )
        db.add(db_setting)
    
    db.commit()
    db.refresh(db_setting)
    return db_setting

@app.get("/users/{email}", response_model=schemas.UserLookupResponse)
def get_user_by_email(email: str, db: Session = Depends(get_db)):
    """Look up a user by email address."""
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email {email} not found."
        )
    return user

@app.get("/users/{user_id}/targets", response_model=schemas.UserProfileResponse)
def get_user_targets(user_id: int, db: Session = Depends(get_db)):
    """Get user profile with targets."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )
    
    # Compute targets on the fly using NutritionEngine
    targets = NutritionEngine.calculate_targets(
        age=user.age,
        gender=user.gender,
        height=user.height,
        weight=user.weight,
        activity_level=user.activity_level,
        goal=user.goal
    )

    # Get preferences
    diet_type = "Non-Vegetarian"
    likes_list = []
    allergies_list = []
    dislikes_list = []
    for p in user.preferences:
        t = p.preference_type.lower()
        val = p.value.strip()
        if t == "diet_type":
            diet_type = val
        elif t == "like":
            likes_list.append(val)
        elif t == "allergy":
            allergies_list.append(val)
        elif t == "dislike":
            dislikes_list.append(val)

    response_data = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "age": user.age,
        "gender": user.gender,
        "height": user.height,
        "weight": user.weight,
        "activity_level": user.activity_level,
        "goal": user.goal,
        "target_calories": user.target_calories,
        "target_protein": user.target_protein,
        "target_carbs": user.target_carbs,
        "target_fat": user.target_fat,
        "bmi": targets.get("bmi"),
        "bmi_status": targets.get("bmi_status"),
        "bmr": targets.get("bmr"),
        "tdee": targets.get("tdee"),
        "created_at": user.created_at,
        "diet_type": diet_type,
        "likes": ", ".join(likes_list),
        "allergies": ", ".join(allergies_list),
        "dislikes": ", ".join(dislikes_list),
    }
    return response_data

@app.get("/users/{user_id}/weight-history", response_model=List[schemas.WeightLogEntry])
def get_weight_history(user_id: int, db: Session = Depends(get_db)):
    """Get weight log history for a user."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )
    logs = db.query(models.WeightLog).filter(
        models.WeightLog.user_id == user_id
    ).order_by(models.WeightLog.logged_at.desc()).limit(90).all()
    return logs

@app.get("/users/{user_id}/meal-plans", response_model=List[schemas.MealPlanHistoryItem])
def get_meal_plan_history(user_id: int, db: Session = Depends(get_db)):
    """Get meal plan history for a user."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )
    plans = db.query(models.GeneratedMealPlan).filter(
        models.GeneratedMealPlan.user_id == user_id
    ).order_by(models.GeneratedMealPlan.plan_date.desc()).limit(30).all()
    
    result = []
    for p in plans:
        item = schemas.MealPlanHistoryItem(
            id=p.id,
            plan_date=p.plan_date,
            actual_calories=p.actual_calories,
            actual_protein=p.actual_protein,
            actual_carbs=p.actual_carbs,
            actual_fat=p.actual_fat,
            adherence=p.adherence
        )
        if p.breakfast_recipe:
            item.breakfast_recipe_name = p.breakfast_recipe.recipe_name
        if p.lunch_recipe:
            item.lunch_recipe_name = p.lunch_recipe.recipe_name
        if p.dinner_recipe:
            item.dinner_recipe_name = p.dinner_recipe.recipe_name
        if p.snack_recipe:
            item.snack_recipe_name = p.snack_recipe.recipe_name
        result.append(item)
    
    return result

@app.post("/calculate-profile", response_model=schemas.UserProfileResponse, status_code=status.HTTP_201_CREATED)
def calculate_profile(profile_in: schemas.UserProfileCreate, db: Session = Depends(get_db)):
    """Calculate target nutrients based on user metrics and save/update the user profile."""
    # Compute targets using NutritionEngine
    targets = NutritionEngine.calculate_targets(
        age=profile_in.age,
        gender=profile_in.gender,
        height=profile_in.height,
        weight=profile_in.weight,
        activity_level=profile_in.activity_level,
        goal=profile_in.goal
    )

    # Check if user already exists
    user = db.query(models.User).filter(models.User.email == profile_in.email).first()
    if user:
        # Update existing user profile
        user.name = profile_in.name
        user.age = profile_in.age
        user.gender = profile_in.gender
        user.height = profile_in.height
        user.weight = profile_in.weight
        user.activity_level = profile_in.activity_level
        user.goal = profile_in.goal
        user.target_calories = targets["target_calories"]
        user.target_protein = targets["target_protein_g"]
        user.target_carbs = targets["target_carbs_g"]
        user.target_fat = targets["target_fat_g"]
        
        # Delete old preferences to replace them
        db.query(models.UserPreference).filter(models.UserPreference.user_id == user.id).delete()
    else:
        # Create new user
        user = models.User(
            name=profile_in.name,
            email=profile_in.email,
            age=profile_in.age,
            gender=profile_in.gender,
            height=profile_in.height,
            weight=profile_in.weight,
            activity_level=profile_in.activity_level,
            goal=profile_in.goal,
            target_calories=targets["target_calories"],
            target_protein=targets["target_protein_g"],
            target_carbs=targets["target_carbs_g"],
            target_fat=targets["target_fat_g"]
        )
        db.add(user)
        db.flush() # Eagerly generate ID

    # Save preferences if provided
    if profile_in.preferences:
        for pref in profile_in.preferences:
            db_pref = models.UserPreference(
                user_id=user.id,
                preference_type=pref.preference_type,
                value=pref.value
            )
            db.add(db_pref)

    db.commit()
    db.refresh(user)

    # Return targets as additional dict fields (not stored in DB but computed)
    diet_type = "Non-Vegetarian"
    likes_list = []
    allergies_list = []
    dislikes_list = []
    for p in user.preferences:
        t = p.preference_type.lower()
        val = p.value.strip()
        if t == "diet_type":
            diet_type = val
        elif t == "like":
            likes_list.append(val)
        elif t == "allergy":
            allergies_list.append(val)
        elif t == "dislike":
            dislikes_list.append(val)

    response_data = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "age": user.age,
        "gender": user.gender,
        "height": user.height,
        "weight": user.weight,
        "activity_level": user.activity_level,
        "goal": user.goal,
        "target_calories": user.target_calories,
        "target_protein": user.target_protein,
        "target_carbs": user.target_carbs,
        "target_fat": user.target_fat,
        "bmi": targets.get("bmi"),
        "bmi_status": targets.get("bmi_status"),
        "bmr": targets.get("bmr"),
        "tdee": targets.get("tdee"),
        "created_at": user.created_at,
        "diet_type": diet_type,
        "likes": ", ".join(likes_list),
        "allergies": ", ".join(allergies_list),
        "dislikes": ", ".join(dislikes_list),
    }
    return response_data

@app.post("/recommend-foods", response_model=List[schemas.RankedFoodItem])
def recommend_foods(req: schemas.RecommendFoodsRequest, db: Session = Depends(get_db)):
    """Get ranked recipes customized to user targets, allergies, likes, and dislikes."""
    user = db.query(models.User).filter(models.User.id == req.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"User with ID {req.user_id} not found."
        )
    
    recommendations = RecommendationEngine.get_recommendations(
        db=db, 
        user_id=req.user_id, 
        limit=req.limit
    )
    return recommendations

@app.post("/generate-meal-plan", response_model=schemas.MealPlanResponse)
def generate_meal_plan(req: schemas.GenerateMealPlanRequest, db: Session = Depends(get_db)):
    """Generate a daily meal plan satisfying targets using OR-Tools Linear Programming."""
    user = db.query(models.User).filter(models.User.id == req.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"User with ID {req.user_id} not found."
        )

    plan_date = req.plan_date or datetime.utcnow().date()
    
    # Run MIP solver to find optimal plan
    plan = OptimizationEngine.generate_daily_plan(
        db=db, 
        user_id=req.user_id, 
        tolerance=req.tolerance or 0.15,
        preference=req.preference or "balanced",
        meal_cuisines=req.meal_cuisines
    )

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not generate a feasible meal plan satisfying nutrient targets. Try widening the tolerance."
        )

    # Save generated plan to database
    # Deleting any existing plan for the same day first to override
    db.query(models.GeneratedMealPlan).filter(
        models.GeneratedMealPlan.user_id == req.user_id,
        models.GeneratedMealPlan.plan_date == plan_date
    ).delete()

    db_plan = models.GeneratedMealPlan(
        user_id=req.user_id,
        plan_date=plan_date,
        breakfast_recipe_code=plan["meals"]["Breakfast"]["recipe_code"],
        lunch_recipe_code=plan["meals"]["Lunch"]["recipe_code"],
        dinner_recipe_code=plan["meals"]["Dinner"]["recipe_code"],
        snack_recipe_code=plan["meals"]["Snack"]["recipe_code"],
        breakfast_servings=1.0,
        lunch_servings=1.0,
        dinner_servings=1.0,
        snack_servings=1.0,
        actual_calories=plan["totals"]["calories"],
        actual_protein=plan["totals"]["protein_g"],
        actual_carbs=plan["totals"]["carbs_g"],
        actual_fat=plan["totals"]["fat_g"]
    )
    db.add(db_plan)
    db.commit()

    return {
        "user_id": req.user_id,
        "plan_date": plan_date,
        "meals": plan["meals"],
        "totals": plan["totals"],
        "targets": plan["targets"],
        "tolerance_used": plan["tolerance_used"]
    }

# =====================================================================
# RECIPE INTELLIGENCE ENGINE ENDPOINTS
# =====================================================================


@app.get("/recipes/top", response_model=schemas_recipes.TopRecipesResponse)
def get_top_recipes(
    limit: int = 10,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """GET /recipes/top — Return top-rated recipes by health score."""
    from sqlalchemy.orm import joinedload

    query = db.query(models.Recipe).options(
        joinedload(models.Recipe.nutrition),
    )

    if category:
        query = query.filter(models.Recipe.category == category)

    recipes = query.all()

    scored = []
    for r in recipes:
        if not r.nutrition or not r.nutrition.energy_kcal:
            continue
        hs, hcat, _ = HealthScorer.score_from_per_serving(r.nutrition)
        d_tag = RecommendationEngine.get_dietary_tag(r)
        scored.append({
            "recipe_code": r.recipe_code,
            "recipe_name": r.recipe_name,
            "category": r.category,
            "cuisine": r.cuisine,
            "difficulty": r.difficulty,
            "cooking_time_minutes": r.cooking_time_minutes,
            "dietary_tag": d_tag,
            "health_score": hs,
            "health_category": hcat,
            "calories": r.nutrition.energy_kcal,
            "protein_g": r.nutrition.protein_g,
            "carbs_g": r.nutrition.carb_g,
            "fat_g": r.nutrition.fat_g,
        })

    scored.sort(key=lambda x: x["health_score"], reverse=True)
    return {"recipes": scored[:limit], "total": len(scored)}


@app.get("/recipes/search", response_model=List[schemas_recipes.RecipeSearchResult])
def search_recipes(
    q: str,
    category: Optional[str] = None,
    cuisine: Optional[str] = None,
    max_results: int = 20,
    db: Session = Depends(get_db),
):
    """GET /recipes/search — Search recipes by name."""
    query = db.query(models.Recipe).filter(
        models.Recipe.recipe_name.ilike(f"%{q}%")
    )

    if category:
        query = query.filter(models.Recipe.category == category)
    if cuisine:
        query = query.filter(models.Recipe.cuisine.ilike(f"%{cuisine}%"))

    results = query.limit(max_results).all()

    return [
        {
            "recipe_code": r.recipe_code,
            "recipe_name": r.recipe_name,
            "category": r.category,
            "cuisine": r.cuisine,
            "dietary_tag": RecommendationEngine.get_dietary_tag(r),
        }
        for r in results
    ]


@app.get("/recipes/{recipe_code}", response_model=schemas_recipes.RecipeDetailResponse)
def get_recipe_detail(recipe_code: str, db: Session = Depends(get_db)):
    """GET /recipes/{id} — Get full details for a single recipe."""
    from sqlalchemy.orm import joinedload

    recipe = db.query(models.Recipe).options(
        joinedload(models.Recipe.nutrition),
        joinedload(models.Recipe.servings),
        joinedload(models.Recipe.ingredients),
    ).filter(models.Recipe.recipe_code == recipe_code).first()

    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe '{recipe_code}' not found."
        )

    # Compute health score
    hs, hcat, hexp = HealthScorer.score_from_per_serving(recipe.nutrition)

    ingredients_list = []
    for ing in recipe.ingredients:
        ingredients_list.append({
            "ingredient_name": ing.ingredient_name,
            "food_name": ing.food_name,
            "amount": ing.amount,
            "unit": ing.unit,
        })

    nutrition_data = None
    if recipe.nutrition:
        nutrition_data = {
            "energy_kcal": recipe.nutrition.energy_kcal,
            "unit_serving_energy_kcal": recipe.nutrition.unit_serving_energy_kcal,
            "protein_g": recipe.nutrition.protein_g,
            "carb_g": recipe.nutrition.carb_g,
            "fat_g": recipe.nutrition.fat_g,
            "freesugar_g": recipe.nutrition.freesugar_g,
            "fibre_g": recipe.nutrition.fibre_g,
            "sodium_mg": recipe.nutrition.sodium_mg,
        }

    return {
        "recipe_code": recipe.recipe_code,
        "recipe_name": recipe.recipe_name,
        "category": recipe.category,
        "cuisine": recipe.cuisine,
        "difficulty": recipe.difficulty,
        "cooking_time_minutes": recipe.cooking_time_minutes,
        "dietary_tag": RecommendationEngine.get_dietary_tag(recipe),
        "instructions": recipe.instructions,
        "primarysource": recipe.primarysource,
        "ingredients": ingredients_list,
        "nutrition": nutrition_data,
        "health_score": hs,
        "health_category": hcat,
    }


@app.post("/recipes/recommend", response_model=schemas_recipes.RecipeRecommendResponse)
def recommend_recipes_by_ingredients(
    req: schemas_recipes.RecipeRecommendRequest,
    db: Session = Depends(get_db),
):
    """
    POST /recipes/recommend — Find recipes you can cook with your ingredients.

    Uses fuzzy matching, health scoring, rule-based ranking, and
    deterministic explanations — no external AI APIs.
    """
    from sqlalchemy.orm import joinedload

    # Clean & normalise user ingredients
    user_ings = [clean_ingredient(i) for i in req.ingredients if i.strip()]
    user_ings = list(set(user_ings))  # deduplicate

    if not user_ings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide at least one valid ingredient."
        )

    aliases = {
        "bengali": ["bengal", "bengali", "machher", "kosha", "shorshe", "mishti", "sandesh", "pitha", "luchi", "cholar"],
        "rajasthani": ["rajasthan", "rajasthani", "baati", "gatte", "laal maas", "sangri", "kachori", "ghevar", "baati"],
        "gujarati": ["gujarat", "gujarati", "dhokla", "thepla", "khichdi", "khandvi", "undhiyu", "handvo", "farsan"],
        "maharashtrian": ["maharashtra", "maharashtrian", "marathi", "misal", "pavitra", "poha", "modak", "puran poli", "vada pav", "pitla"],
        "punjabi": ["punjab", "punjabi", "paneer butter", "tandoori", "chole", "bhature", "sarson", "makki", "dal makhani", "amritsari"],
        "south indian": ["south indian", "dosa", "idli", "sambar", "rasam", "uttapam", "hyderabadi", "kerala", "chettinad", "bisi bele", "appam", "vada", "payasam"],
        "north indian": ["north indian", "paneer", "dal makhani", "korma", "naan", "tikka", "kofta", "biryani", "paratha"],
        "mughlai": ["mughlai", "biryani", "korma", "pasanda", "shahi", "nargisi", "nihari"],
        "kashmiri": ["kashmiri", "rogan josh", "dum aloo", "yakhni", "kahwa"],
        "chinese": ["chinese", "indo-chinese", "hakka", "manchurian", "chow mein", "schezwan", "noodle", "fried rice", "dim sum", "congee", "bao", "sichuan"],
        "indo-chinese": ["chinese", "indo-chinese", "hakka", "manchurian", "chow mein", "schezwan", "noodle", "fried rice"],
        "italian": ["italian", "pasta", "pizza", "risotto", "spaghetti", "bruschetta", "cornetto", "frittata", "arancini", "pesto", "lasagna"],
        "japanese": ["japanese", "sushi", "ramen", "teriyaki", "tempura", "miso", "udon", "donburi", "matcha", "bento", "soba"],
        "mexican": ["mexican", "taco", "burrito", "quesadilla", "enchilada", "fajita", "guacamole", "salsa", "nacho", "chili"],
        "continental": ["continental", "steak", "roast", "soup", "salad", "bake", "grill", "stew"],
        "asian": ["asian", "thai", "japanese", "korean", "vietnamese", "chinese"],
    }

    # High-Performance SQL Query with SQL-level Pre-filtering
    from sqlalchemy import or_
    query = db.query(models.Recipe).options(
        joinedload(models.Recipe.ingredients),
        joinedload(models.Recipe.nutrition),
    )

    # 1. SQL Cuisine Pre-Filter
    if req.cuisine:
        c_lower = req.cuisine.lower()
        sub_kws = aliases.get(c_lower, [c_lower])
        c_conds = [models.Recipe.cuisine.ilike(f"%{kw}%") | models.Recipe.recipe_name.ilike(f"%{kw}%") for kw in sub_kws]
        query = query.filter(or_(*c_conds))

    # 2. SQL Max Cooking Time Filter
    if req.max_cooking_time is not None:
        query = query.filter(models.Recipe.cooking_time_minutes <= req.max_cooking_time)

    # 3. SQL Candidate Pre-Filter for fast ingredient matching (when no cuisine constraint)
    if not req.cuisine and user_ings:
        ing_conds = []
        for term in user_ings:
            if len(term) >= 3:
                ing_conds.append(models.RecipeIngredient.ingredient_name.ilike(f"%{term}%"))
                ing_conds.append(models.RecipeIngredient.food_name.ilike(f"%{term}%"))
                ing_conds.append(models.Recipe.recipe_name.ilike(f"%{term}%"))
        if ing_conds:
            query = query.join(models.Recipe.ingredients).filter(or_(*ing_conds)).distinct()

    recipes = query.all()

    # Apply remaining Python rule filters
    filtered_recipes = []
    for r in recipes:
        # Diet type filter
        if req.diet_type:
            dt = req.diet_type.lower()
            if "jain" in dt and not RecommendationEngine.is_jain(r):
                continue
            elif "vegan" in dt and not RecommendationEngine.is_vegan(r):
                continue
            elif "eggetarian" in dt and not RecommendationEngine.is_eggetarian(r):
                continue
            elif "vegetarian" in dt and "non" not in dt and not RecommendationEngine.is_vegetarian(r):
                continue

        # Max cooking time
        if req.max_cooking_time is not None:
            if r.cooking_time_minutes and r.cooking_time_minutes > req.max_cooking_time:
                continue

        # Exclude ingredient filter
        if req.exclude_ingredients:
            exclude_norm = [clean_ingredient(e) for e in req.exclude_ingredients]
            skip = False
            for ing in r.ingredients:
                ing_name = clean_ingredient(ing.food_name or ing.ingredient_name or "")
                for ex in exclude_norm:
                    if fuzzy_match_ingredient(ex, ing_name):
                        skip = True
                        break
                if skip:
                    break
            if skip:
                continue

        # Must have nutrition data to score
        if not r.nutrition or not r.nutrition.energy_kcal:
            continue

        filtered_recipes.append(r)

    # Score each recipe
    scored_results = []
    for r in filtered_recipes:
        # Get recipe ingredient names
        recipe_ing_names = []
        for ing in r.ingredients:
            name = ing.food_name or ing.ingredient_name or ""
            name = clean_ingredient(name)
            if name:
                recipe_ing_names.append(name)
        recipe_ing_names = list(set(recipe_ing_names))

        # 1. Ingredient match
        match_score, matched, missing = compute_ingredient_match_score(
            user_ings, recipe_ing_names
        )

        if match_score == 0.0 or not matched:
            continue

        # 2. Health score
        hs, hcat, hexp = HealthScorer.score_from_per_serving(r.nutrition)

        # 3. Compute final ranking score
        final = compute_final_score(
            match_score, hs,
            r.nutrition.protein_g,
            r.nutrition.energy_kcal,
        )

        # Goal adjustment
        goal_mult = 1.0
        if req.goal:
            gl = req.goal.lower()
            if gl == "weight loss":
                if (r.nutrition.energy_kcal or 999) < 250:
                    goal_mult = 1.1
                else:
                    goal_mult = 0.85
            elif gl in ("muscle gain", "weight gain"):
                if (r.nutrition.protein_g or 0) >= 12:
                    goal_mult = 1.15
        final *= goal_mult

        d_tag = RecommendationEngine.get_dietary_tag(r)
        # 4. Generate explanation
        explanation = ExplanationEngine.generate(
            recipe_name=r.recipe_name,
            match_score=match_score,
            health_score=hs,
            health_category=hcat,
            health_explanation=hexp,
            matched_ingredients=matched,
            unmatched_ingredients=missing,
            user_ingredients=user_ings,
            protein_g=r.nutrition.protein_g,
            energy_kcal=r.nutrition.energy_kcal,
            carb_g=r.nutrition.carb_g,
            fat_g=r.nutrition.fat_g,
            goal=req.goal,
            cuisine=r.cuisine,
            difficulty=r.difficulty,
            dietary_tag=d_tag,
        )

        scored_results.append({
            "recipe_code": r.recipe_code,
            "recipe_name": r.recipe_name,
            "category": r.category,
            "cuisine": r.cuisine,
            "difficulty": r.difficulty,
            "cooking_time_minutes": r.cooking_time_minutes,
            "dietary_tag": d_tag,
            "match_score": round(match_score, 2),
            "health_score": round(hs, 2),
            "health_category": hcat,
            "final_score": round(final, 2),
            "calories": r.nutrition.unit_serving_energy_kcal or r.nutrition.energy_kcal or 0.0,
            "protein_g": r.nutrition.unit_serving_protein_g or r.nutrition.protein_g or 0.0,
            "carbs_g": r.nutrition.unit_serving_carb_g or r.nutrition.carb_g or 0.0,
            "fat_g": r.nutrition.unit_serving_fat_g or r.nutrition.fat_g or 0.0,
            "fibre_g": r.nutrition.fibre_g or 0.0,
            "sugar_g": r.nutrition.freesugar_g or 0.0,
            "ingredient_match": {
                "score": round(match_score, 2),
                "matched": matched,
                "missing": missing[:5],  # show at most 5 missing
            },
            "reason": explanation["summary"],
        })

    # Sort by final_score descending
    scored_results.sort(key=lambda x: x["final_score"], reverse=True)

    # Return top_n
    top = scored_results[:req.top_n]

    return {
        "query": req,
        "total_results": len(scored_results),
        "top_recipes": top,
    }


@app.post("/recipes/filter", response_model=List[schemas_recipes.RecipeDetailResponse])
def filter_recipes(req: schemas_recipes.RecipeFilterRequest, db: Session = Depends(get_db)):
    """POST /recipes/filter — Filter recipes by nutrition, diet, cuisine, etc."""
    from sqlalchemy.orm import joinedload

    query = db.query(models.Recipe).options(
        joinedload(models.Recipe.nutrition),
        joinedload(models.Recipe.ingredients),
    )

    # Filters
    if req.category:
        query = query.filter(models.Recipe.category == req.category)
    if req.cuisine:
        query = query.filter(models.Recipe.cuisine.ilike(f"%{req.cuisine}%"))
    if req.difficulty:
        query = query.filter(models.Recipe.difficulty == req.difficulty)

    recipes = query.limit(req.max_results).all()

    # Apply post-filters that need nutrition data
    results = []
    for r in recipes:
        if r.nutrition:
            if req.min_protein is not None and (r.nutrition.protein_g or 0) < req.min_protein:
                continue
            if req.max_calories is not None and (r.nutrition.energy_kcal or 0) > req.max_calories:
                continue

        if req.max_cooking_time is not None:
            if r.cooking_time_minutes and r.cooking_time_minutes > req.max_cooking_time:
                continue

        # Diet type filter
        if req.diet_type:
            dt = req.diet_type.lower()
            if dt == "vegetarian" and not RecommendationEngine.is_vegetarian(r):
                continue
            if dt == "vegan" and not RecommendationEngine.is_vegan(r):
                continue

        # Goal filter: customize response
        hs, hcat, _ = HealthScorer.score_from_per_serving(r.nutrition) if r.nutrition else (50.0, "Moderate", "")

        ingredients_list = []
        for ing in r.ingredients:
            ingredients_list.append({
                "ingredient_name": ing.ingredient_name,
                "food_name": ing.food_name,
                "amount": ing.amount,
                "unit": ing.unit,
            })

        nutrition_data = None
        if r.nutrition:
            nutrition_data = {
                "energy_kcal": r.nutrition.energy_kcal,
                "unit_serving_energy_kcal": r.nutrition.unit_serving_energy_kcal,
                "protein_g": r.nutrition.protein_g,
                "carb_g": r.nutrition.carb_g,
                "fat_g": r.nutrition.fat_g,
                "freesugar_g": r.nutrition.freesugar_g,
                "fibre_g": r.nutrition.fibre_g,
                "sodium_mg": r.nutrition.sodium_mg,
            }

        results.append({
            "recipe_code": r.recipe_code,
            "recipe_name": r.recipe_name,
            "category": r.category,
            "cuisine": r.cuisine,
            "difficulty": r.difficulty,
            "cooking_time_minutes": r.cooking_time_minutes,
            "instructions": r.instructions,
            "primarysource": r.primarysource,
            "ingredients": ingredients_list,
            "nutrition": nutrition_data,
            "health_score": hs,
            "health_category": hcat,
        })

    return results


@app.post("/recipes/train-ml")
def train_ml_model(
    db: Session = Depends(get_db),
):
    """
    POST /recipes/train-ml — Train ML model on synthetic interaction data
    (demo / extension endpoint). Requires scikit-learn installed.
    """
    from app.services.ml_extension import train_model, prepare_training_data
    from app.services.ingredient_matcher import clean_ingredient

    # Build synthetic training records from current recipes
    recipes = db.query(models.Recipe).options(
        joinedload(models.Recipe.ingredients),
        joinedload(models.Recipe.nutrition),
    ).limit(200).all()

    records = []
    import random
    random.seed(42)

    sample_ingredient_sets = [
        ["rice", "onion", "tomato"],
        ["paneer", "spinach", "onion"],
        ["chicken", "rice", "garlic", "ginger"],
        ["potato", "cauliflower", "peas"],
        ["lentil", "tomato", "onion", "garlic"],
    ]

    for r in recipes:
        if not r.nutrition or not r.ingredients:
            continue
        recipe_ings = [clean_ingredient(ing.food_name or ing.ingredient_name or "")
                       for ing in r.ingredients if ing.food_name or ing.ingredient_name]
        if not recipe_ings:
            continue

        for user_ings in sample_ingredient_sets:
            # Compute target score using existing rule-based system
            from app.services.recipe_ranker import compute_final_score
            from app.services.health_scorer import HealthScorer
            from app.services.ingredient_matcher import compute_ingredient_match_score

            match_score, _, _ = compute_ingredient_match_score(user_ings, recipe_ings)
            hs, _, _ = HealthScorer.score_from_per_serving(r.nutrition)
            target = compute_final_score(
                match_score, hs,
                r.nutrition.protein_g,
                r.nutrition.energy_kcal,
            )

            records.append({
                "user_ingredients": user_ings,
                "recipe_ingredients": recipe_ings,
                "recipe": {
                    "protein_g": r.nutrition.protein_g or 0,
                    "energy_kcal": r.nutrition.energy_kcal or 0,
                    "carb_g": r.nutrition.carb_g or 0,
                    "fat_g": r.nutrition.fat_g or 0,
                    "fibre_g": r.nutrition.fibre_g or 0,
                    "sugar_g": r.nutrition.freesugar_g or 0,
                    "sodium_mg": r.nutrition.sodium_mg or 0,
                    "difficulty": r.difficulty or "Medium",
                },
                "goal": random.choice(["fat loss", "muscle gain", "maintenance"]),
                "target_score": target,
            })

    if len(records) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough recipe data to train. Got {len(records)} records (need ≥10)."
        )

    result = train_model(records, model_type="random_forest")
    return result


# =====================================================================
# EXISTING ENDPOINTS FOLLOW
# =====================================================================


@app.post("/track-weight")
def track_weight(req: schemas.TrackWeightRequest, db: Session = Depends(get_db)):
    """Log weight, update adherence, and run adaptive planner to adjust future targets."""
    user = db.query(models.User).filter(models.User.id == req.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"User with ID {req.user_id} not found."
        )

    logged_at = req.logged_at or datetime.utcnow().date()

    # 1. Log weight
    # Delete existing log for same day if any, to update
    db.query(models.WeightLog).filter(
        models.WeightLog.user_id == req.user_id,
        models.WeightLog.logged_at == logged_at
    ).delete()

    db_log = models.WeightLog(
        user_id=req.user_id,
        weight=req.weight,
        logged_at=logged_at
    )
    db.add(db_log)

    # Update current user weight
    user.weight = req.weight

    # 2. Update adherence on meal plan for the day if specified
    if req.adherence is not None:
        meal_plan = db.query(models.GeneratedMealPlan).filter(
            models.GeneratedMealPlan.user_id == req.user_id,
            models.GeneratedMealPlan.plan_date == logged_at
        ).first()
        if meal_plan:
            meal_plan.adherence = req.adherence
        else:
            # Create a shell meal plan just to record adherence if none existed
            db_plan = models.GeneratedMealPlan(
                user_id=req.user_id,
                plan_date=logged_at,
                adherence=req.adherence
            )
            db.add(db_plan)

    db.commit()

    # 3. Run Adaptive Planner to check trends and adjust targets
    analysis = AdaptivePlanner.track_and_adjust(db=db, user_id=req.user_id)
    
    return {
        "status": "success",
        "weight_logged": {
            "weight": req.weight,
            "date": logged_at
        },
        "adherence_logged": req.adherence,
        "adaptive_adjustment": analysis
    }


# =====================================================================
# NEW CORE ENGINE ENDPOINTS (PHASE 2 & 3)
# =====================================================================

@app.post("/api/classify", response_model=schemas.ClassifyResponse)
def classify_food(req: schemas.ClassifyRequest, db: Session = Depends(get_db)):
    """Classify ingredients list or an existing recipe against dietary rules (Vegetarian, Vegan, Jain, Eggetarian)."""
    if req.recipe_code:
        recipe = db.query(models.Recipe).filter(models.Recipe.recipe_code == req.recipe_code).first()
        if not recipe:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recipe '{req.recipe_code}' not found."
            )
        classification = ClassificationEngine.classify_recipe(db, recipe)
    elif req.ingredients:
        rules_map = ClassificationEngine.get_rules_map(db)
        classification = ClassificationEngine.classify_ingredients(req.ingredients, rules_map)
        classification["tags"] = []
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either recipe_code or ingredients list."
        )
    return classification


@app.get("/api/barcode/{barcode}")
def scan_barcode(barcode: str, db: Session = Depends(get_db)):
    """Fetch product details by barcode, utilizing local caching and Open Food Facts API."""
    result = BarcodeService.get_product(db, barcode)
    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    return result


@app.post("/api/barcode/manual")
def save_manual_barcode(req: schemas.ManualBarcodeRequest, db: Session = Depends(get_db)):
    """Manually add barcode details and save to cache."""
    import json
    
    # Check if barcode already exists
    existing = db.query(models.BarcodeCache).filter(models.BarcodeCache.barcode == req.barcode).first()
    if existing:
        db.delete(existing)
        db.commit()

    nutrients_100g = {
        "energy_kcal": req.energy_kcal,
        "protein_g": req.protein_g,
        "carb_g": req.carb_g,
        "fat_g": req.fat_g,
        "fibre_g": req.fibre_g,
        "sodium_mg": req.sodium_mg,
        "sugar_g": req.sugar_g,
        "saturated_fat_g": req.saturated_fat_g
    }

    # Calculate local health score
    score, category, explanation = HealthScorer.score_from_nutrition_dict(nutrients_100g)

    new_cache = models.BarcodeCache(
        barcode=req.barcode,
        product_name=req.product_name,
        brand=req.brand,
        ingredients_text=req.ingredients_text,
        nutrition_grade=category[0].lower() if (category and len(category) > 0) else "unknown",
        nutriments_json=json.dumps(nutrients_100g),
        health_score=score,
        health_category=category
    )
    db.add(new_cache)
    db.commit()
    db.refresh(new_cache)

    return {
        "status": "success",
        "source": "manual",
        "barcode": req.barcode,
        "product_name": req.product_name,
        "brand": req.brand,
        "ingredients_text": req.ingredients_text,
        "nutrition_grade": new_cache.nutrition_grade,
        "health_score": score,
        "health_category": category,
        "explanation": explanation,
        "nutriments": nutrients_100g
    }


ALTERNATIVES_LIST = [
    {
        "keywords": ["chips", "kurkure", "lays", "bingo", "fried", "namkeen", "crisps", "snack"],
        "category": "Snack",
        "name": "Tata Sampann Roasted Chana (Spiced)",
        "price": 30,
        "protein_g": 20.0,
        "energy_kcal": 360,
        "link": "https://www.amazon.in/dp/B09D3R5WYS",
        "reason": "100% roasted, high-protein snack (20g protein per 100g), low fat, and extremely budget-friendly!"
    },
    {
        "keywords": ["coke", "cola", "pepsi", "sprite", "fanta", "maaza", "frooti", "soda", "drink", "juice", "beverage", "nimbu"],
        "category": "Snack",
        "name": "Amul Masti Spiced Buttermilk (Chaas)",
        "price": 15,
        "protein_g": 1.5,
        "energy_kcal": 28,
        "link": "https://www.amazon.in/dp/B084G2W3R8",
        "reason": "Refreshing, low calorie (only 28 kcal), completely sugar-free natural probiotic drink for the same cost as soda!"
    },
    {
        "keywords": ["biscuit", "parle", "marie", "cookies", "good day", "cracker"],
        "category": "Snack",
        "name": "Yoga Bar Oats (Instant)",
        "price": 45,
        "protein_g": 13.6,
        "energy_kcal": 390,
        "link": "https://www.amazon.in/dp/B08PBDZYZK",
        "reason": "100% whole grain oats, high fibre, low glycemic index, and significantly higher protein than refined flour biscuits."
    },
    {
        "keywords": ["chips", "kurkure", "lays", "bingo", "fried", "namkeen", "crisps", "snack"],
        "category": "Snack",
        "name": "Happilo Premium Roasted Makhana (Salt & Pepper)",
        "price": 120,
        "protein_g": 9.0,
        "energy_kcal": 350,
        "link": "https://www.amazon.in/dp/B07NPHSP8N",
        "reason": "Baked and roasted instead of deep fried, lower in saturated fats and contains 9g protein!"
    },
    {
        "keywords": ["coke", "cola", "pepsi", "sprite", "fanta", "maaza", "frooti", "soda", "drink", "juice", "beverage", "nimbu"],
        "category": "Snack",
        "name": "Paper Boat Tender Coconut Water",
        "price": 40,
        "protein_g": 0.0,
        "energy_kcal": 20,
        "link": "https://www.amazon.in/dp/B01H7B7T58",
        "reason": "100% natural, no added white sugar, high in potassium and hydration compared to sugary sodas."
    },
    {
        "keywords": ["bar", "chocolate", "cadbury", "dairymilk", "snickers", "kitkat", "candy", "sweet", "protein bar"],
        "category": "Snack",
        "name": "The Whole Truth Protein Bars (Double Cocoa)",
        "price": 100,
        "protein_g": 25.0,
        "energy_kcal": 366,
        "link": "https://www.amazon.in/dp/B08L84Q1V2",
        "reason": "Clean ingredients (only dates, whey protein, cocoa, almonds), no added sugar, and gives 15g protein per bar!"
    },
    {
        "keywords": ["yogabar", "protein bar", "muesli bar", "granola bar"],
        "category": "Snack",
        "name": "MuscleBlaze Protein Bar (Choco Delight)",
        "price": 90,
        "protein_g": 22.0,
        "energy_kcal": 380,
        "link": "https://www.amazon.in/dp/B07K48C9M4",
        "reason": "Higher protein content (22g protein vs 10g in standard bars) for the same price point."
    },
    {
        "keywords": ["noodles", "maggi", "yippee", "ramen", "pasta"],
        "category": "Lunch/Dinner",
        "name": "Slurrp Farm Millet Noodles",
        "price": 80,
        "protein_g": 12.0,
        "energy_kcal": 360,
        "link": "https://www.amazon.in/dp/B08P8LFSQ7",
        "reason": "Made from foxtail millet and wheat, not maida, and provides 12g protein per 100g."
    },
    {
        "keywords": ["biscuit", "parle", "marie", "cookies", "good day", "cracker"],
        "category": "Snack",
        "name": "NutroActive Keto Cookies (High Protein & Low Carb)",
        "price": 150,
        "protein_g": 20.0,
        "energy_kcal": 450,
        "link": "https://www.amazon.in/dp/B07GD4Z8K3",
        "reason": "Low glycemic load, only 3g net carbs per cookie and extremely high protein (20g per 100g)."
    }
]


@app.post("/api/barcode/alternatives")
def get_barcode_alternatives(req: schemas.AlternativesRequest):
    """Recommend healthier alternative products based on meal type, nutrients, and price range."""
    name_lower = req.product_name.lower()
    
    # 1. Try keyword matching on alternative database
    matched_alts = []
    for alt in ALTERNATIVES_LIST:
        if any(kw in name_lower for kw in alt["keywords"]):
            matched_alts.append(alt)
            
    # 2. Fallback to category/macro matching if no keywords match
    if not matched_alts:
        if req.sugar_g > 10.0 or req.energy_kcal > 250:
            matched_alts.append(ALTERNATIVES_LIST[0]) # Chana
            matched_alts.append(ALTERNATIVES_LIST[1]) # Chaas
            matched_alts.append(ALTERNATIVES_LIST[5]) # Whole Truth Bar
        else:
            if req.meal_type == "Snack":
                matched_alts.append(ALTERNATIVES_LIST[0])
                matched_alts.append(ALTERNATIVES_LIST[1])
            else:
                matched_alts.append(ALTERNATIVES_LIST[7]) # Millet Noodles

    results = []
    for alt in matched_alts:
        # Distance calculation for budget matching
        price_diff = abs(alt["price"] - req.estimated_price)
        
        # Heavy penalty on premium products if scanned product was budget (<= 40 INR)
        penalty = 0.0
        if req.estimated_price <= 40.0 and alt["price"] > 70.0:
            penalty = 200.0  # pushes them down the rank
            
        protein_diff = alt["protein_g"] - req.protein_g
        kcal_diff = req.energy_kcal - alt["energy_kcal"]
        
        comparison = ""
        if protein_diff > 0:
            comparison += f"Provides {protein_diff:.1f}g MORE protein per 100g. "
        if kcal_diff > 0:
            comparison += f"Saves {kcal_diff:.0f} kcal per 100g. "
            
        results.append({
            "name": alt["name"],
            "price": alt["price"],
            "protein_g": alt["protein_g"],
            "energy_kcal": alt["energy_kcal"],
            "link": alt["link"],
            "reason": alt["reason"],
            "comparison": comparison or "Higher nutritional density.",
            "rank_score": price_diff + penalty
        })
        
    # Sort results by price/budget rank score
    results.sort(key=lambda x: x["rank_score"])
    
    # Remove rank_score from final response to keep clean contract
    for r in results:
        r.pop("rank_score", None)
        
    return {"alternatives": results}


from fastapi import UploadFile, File, Form

@app.post("/api/ocr")
def ocr_image(
    file: UploadFile = File(...),
    user_id: Optional[int] = Form(None),
    meal_type: Optional[str] = Form(None),
    food_name: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Process an uploaded nutrition label image to extract nutritional values."""
    contents = file.file.read()
    res = OCREngine.extract_nutrition_from_image(contents)
    
    # Save metadata/log if user info is provided
    if user_id and meal_type and res["status"] == "success":
        parsed = res["parsed_nutrition"]
        food_label = food_name or file.filename or "Scanned Label"
        db_log = models.MealLog(
            user_id=user_id,
            log_date=datetime.utcnow().date(),
            meal_type=meal_type,
            food_name=food_label,
            calories=parsed["energy_kcal"],
            protein=parsed["protein_g"],
            carbs=parsed["carb_g"],
            fat=parsed["fat_g"]
        )
        db.add(db_log)
        db.commit()
        res["meal_logged"] = True
        
    return res


@app.get("/api/analytics/{user_id}")
def get_user_analytics(user_id: int, db: Session = Depends(get_db)):
    """Retrieve nutritional statistics and weight trend analysis for the user."""
    result = AnalyticsEngine.calculate_and_save_metrics(db, user_id)
    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["message"]
        )
    return result


@app.get("/api/analytics/{user_id}/history")
def get_user_analytics_history(
    user_id: int,
    metric_name: str,
    limit: int = 30,
    db: Session = Depends(get_db)
):
    """Retrieve historical values of a specific calculated analytics metric."""
    return AnalyticsEngine.get_historical_metrics(db, user_id, metric_name, limit)


def format_homely_meal_response(m):
    return {
        "id": m.id,
        "name": m.name,
        "creator_id": m.creator_id,
        "is_community": m.is_community,
        "status": m.status,
        "popularity": m.popularity,
        "cuisine": m.cuisine,
        "region": m.region,
        "created_at": m.created_at,
        "ingredients": [
            {
                "ingredient_name": ing.ingredient_name,
                "amount": ing.amount,
                "unit": ing.unit,
                "gram_weight": ing.gram_weight,
                "food_code": ing.food_code
            } for ing in m.ingredients
        ],
        "nutrition": {
            "energy_kcal": m.nutrition.energy_kcal if m.nutrition else 0.0,
            "protein_g": m.nutrition.protein_g if m.nutrition else 0.0,
            "carb_g": m.nutrition.carb_g if m.nutrition else 0.0,
            "fat_g": m.nutrition.fat_g if m.nutrition else 0.0,
            "fibre_g": m.nutrition.fibre_g if m.nutrition else 0.0,
            "sodium_mg": m.nutrition.sodium_mg if m.nutrition else 0.0,
            "sugar_g": m.nutrition.sugar_g if m.nutrition else 0.0
        } if m.nutrition else None,
        "tags": [t.tag for t in m.tags]
    }


@app.get("/api/homely/builder-defaults")
def get_homely_builder_defaults(db: Session = Depends(get_db)):
    """Get defaults for homely meal builder including base items and condiments."""
    from sqlalchemy.orm import joinedload
    
    # We query the food items from database
    codes = {
        "paneer_tikka": "IND_FOOD_0078",
        "chicken_tikka": "IND_FOOD_0026",
        "mint_chutney": "IND_FOOD_0045",
        "tamarind_chutney": "IND_FOOD_0046",
        "tomato_sauce": "PACKAGED_0756",
        "curd": "PACKAGED_0902"
    }
    
    # Fetch them
    items = db.query(models.Food).options(joinedload(models.Food.nutrients)).filter(models.Food.food_code.in_(list(codes.values()))).all()
    items_map = {item.food_code: item for item in items}
    
    def get_nutrients_or_fallback(code, fallback_dict):
        item = items_map.get(code)
        if item and item.nutrients:
            n = item.nutrients
            return {
                "name": item.name,
                "energy_kcal": n.energy_kcal,
                "protein_g": n.protein_g,
                "carb_g": n.carb_g,
                "fat_g": n.fat_g,
                "fibre_g": n.fibre_g or 0.0,
                "sodium_mg": n.sodium_mg or 0.0,
                "sugar_g": n.sugar_g or 0.0
            }
        return fallback_dict

    base_meals = [
        {
            "code": "IND_FOOD_0078",
            "name": "Paneer Tikka (Home Made)",
            "unit": "piece",
            "unit_weight_g": 25.0,
            "nutrients_100g": get_nutrients_or_fallback("IND_FOOD_0078", {
                "name": "Paneer Tikka", "energy_kcal": 190.0, "protein_g": 14.0, "carb_g": 4.5, "fat_g": 13.0, "fibre_g": 0.5, "sodium_mg": 380.0, "sugar_g": 1.2
            })
        },
        {
            "code": "IND_FOOD_0026",
            "name": "Chicken Tikka (Home Made)",
            "unit": "piece",
            "unit_weight_g": 30.0,
            "nutrients_100g": get_nutrients_or_fallback("IND_FOOD_0026", {
                "name": "Chicken Tikka", "energy_kcal": 150.0, "protein_g": 18.0, "carb_g": 3.0, "fat_g": 7.0, "fibre_g": 0.2, "sodium_mg": 410.0, "sugar_g": 0.8
            })
        },
        {
            "code": "Samosa",
            "name": "Samosa (Home Made)",
            "unit": "piece",
            "unit_weight_g": 50.0,
            "nutrients_100g": {
                "name": "Samosa", "energy_kcal": 260.0, "protein_g": 4.5, "carb_g": 32.0, "fat_g": 12.0, "fibre_g": 1.5, "sodium_mg": 290.0, "sugar_g": 1.0
            }
        },
        {
            "code": "Dhokla",
            "name": "Khaman Dhokla (Home Made)",
            "unit": "piece",
            "unit_weight_g": 35.0,
            "nutrients_100g": {
                "name": "Dhokla", "energy_kcal": 160.0, "protein_g": 6.0, "carb_g": 28.0, "fat_g": 2.5, "fibre_g": 1.8, "sodium_mg": 340.0, "sugar_g": 4.0
            }
        },
        {
            "code": "Idli",
            "name": "Idli (Home Made)",
            "unit": "piece",
            "unit_weight_g": 40.0,
            "nutrients_100g": {
                "name": "Idli", "energy_kcal": 100.0, "protein_g": 2.5, "carb_g": 22.0, "fat_g": 0.2, "fibre_g": 1.0, "sodium_mg": 120.0, "sugar_g": 0.2
            }
        },
        {
            "code": "Dosa",
            "name": "Plain Dosa (Home Made)",
            "unit": "serving",
            "unit_weight_g": 80.0,
            "nutrients_100g": {
                "name": "Dosa", "energy_kcal": 170.0, "protein_g": 4.0, "carb_g": 35.0, "fat_g": 1.5, "fibre_g": 1.2, "sodium_mg": 180.0, "sugar_g": 0.3
            }
        }
    ]

    condiments = [
        {
            "id": "green_chutney",
            "name": "Green Chutney (Mint & Cilantro)",
            "unit": "tsp",
            "unit_weight_g": 5.0,
            "nutrients_100g": get_nutrients_or_fallback("IND_FOOD_0045", {
                "name": "Mint Chutney", "energy_kcal": 40.0, "protein_g": 2.0, "carb_g": 6.0, "fat_g": 1.0, "fibre_g": 2.0, "sodium_mg": 600.0, "sugar_g": 0.5
            })
        },
        {
            "id": "imli_chutney",
            "name": "Imli Chutney (Tamarind)",
            "unit": "tsp",
            "unit_weight_g": 5.0,
            "nutrients_100g": get_nutrients_or_fallback("IND_FOOD_0046", {
                "name": "Tamarind Chutney", "energy_kcal": 180.0, "protein_g": 1.0, "carb_g": 45.0, "fat_g": 0.2, "fibre_g": 1.5, "sodium_mg": 450.0, "sugar_g": 38.0
            })
        },
        {
            "id": "tomato_sauce",
            "name": "Tomato Ketchup / Sauce",
            "unit": "tsp",
            "unit_weight_g": 5.0,
            "nutrients_100g": get_nutrients_or_fallback("PACKAGED_0756", {
                "name": "Tomato Sauce", "energy_kcal": 120.0, "protein_g": 1.0, "carb_g": 29.0, "fat_g": 0.1, "fibre_g": 0.8, "sodium_mg": 900.0, "sugar_g": 22.0
            })
        },
        {
            "id": "butter_ghee",
            "name": "Butter / Ghee / Oil",
            "unit": "tsp",
            "unit_weight_g": 5.0,
            "nutrients_100g": {
                "name": "Butter", "energy_kcal": 717.0, "protein_g": 0.8, "carb_g": 0.1, "fat_g": 81.0, "fibre_g": 0.0, "sodium_mg": 643.0, "sugar_g": 0.1
            }
        },
        {
            "id": "curd_raita",
            "name": "Curd / Plain Yogurt",
            "unit": "tbsp",
            "unit_weight_g": 15.0,
            "nutrients_100g": get_nutrients_or_fallback("PACKAGED_0902", {
                "name": "Curd", "energy_kcal": 60.0, "protein_g": 3.5, "carb_g": 4.5, "fat_g": 3.0, "fibre_g": 0.0, "sodium_mg": 50.0, "sugar_g": 4.0
            })
        }
    ]

    return {"base_meals": base_meals, "condiments": condiments}


@app.post("/api/homely-meals/calculate", response_model=schemas.HomelyMealCalculateResponse)
def calculate_homely_meal(req: schemas.HomelyMealCalculateRequest, db: Session = Depends(get_db)):
    """Computes nutrition parameters of raw ingredients list on-the-fly."""
    res = homely_meals_engine.calculate_meal_nutrition(db, req.ingredients)
    return res

@app.post("/api/homely-meals/create", response_model=schemas.HomelyMealResponse)
def create_custom_homely_meal(req: schemas.HomelyMealCreateRequest, db: Session = Depends(get_db)):
    """Adds a homely meal to the database (defaults to status='pending')."""
    meal = homely_meals_engine.create_homely_meal(db, req)
    return format_homely_meal_response(meal)

@app.get("/api/homely-meals/pending", response_model=List[schemas.HomelyMealResponse])
def get_pending_homely_meals(db: Session = Depends(get_db)):
    """Retrieve all pending homely meals for community kitchen moderation."""
    from sqlalchemy.orm import joinedload
    meals = db.query(models.HomelyMeal).options(
        joinedload(models.HomelyMeal.nutrition),
        joinedload(models.HomelyMeal.ingredients),
        joinedload(models.HomelyMeal.tags)
    ).filter(models.HomelyMeal.status == "pending").all()
    return [format_homely_meal_response(m) for m in meals]

@app.post("/api/homely-meals/review/{meal_id}", response_model=schemas.HomelyMealResponse)
def review_homely_meal(meal_id: int, req: schemas.HomelyMealStatusUpdateRequest, db: Session = Depends(get_db)):
    """Approves or rejects a user-submitted meal for community use."""
    meal = homely_meals_engine.update_meal_status(db, meal_id, req.status, req.reviewer_id, req.comment)
    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Homely meal with ID {meal_id} not found."
        )
    return format_homely_meal_response(meal)

@app.get("/api/homely-meals/search", response_model=List[schemas.HomelyMealResponse])
def search_homely_meals(q: str = "", db: Session = Depends(get_db)):
    """Fuzzy searches approved community homely meals."""
    from sqlalchemy.orm import joinedload
    query = db.query(models.HomelyMeal).options(
        joinedload(models.HomelyMeal.nutrition),
        joinedload(models.HomelyMeal.ingredients),
        joinedload(models.HomelyMeal.tags)
    ).filter(models.HomelyMeal.status == "approved")
    
    if q.strip():
        query = query.filter(models.HomelyMeal.name.ilike(f"%{q}%"))
        
    meals = query.all()
    return [format_homely_meal_response(m) for m in meals]

@app.get("/api/homely-meals/{meal_id}", response_model=schemas.HomelyMealResponse)
def get_homely_meal_detail(meal_id: int, scale: float = 1.0, db: Session = Depends(get_db)):
    """Retrieves meal components and allows custom quantity scaling."""
    from sqlalchemy.orm import joinedload
    meal = db.query(models.HomelyMeal).options(
        joinedload(models.HomelyMeal.nutrition),
        joinedload(models.HomelyMeal.ingredients),
        joinedload(models.HomelyMeal.tags)
    ).filter(models.HomelyMeal.id == meal_id).first()
    
    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Homely meal with ID {meal_id} not found."
        )
        
    res = format_homely_meal_response(meal)
    
    if scale != 1.0:
        for ing in res["ingredients"]:
            ing["amount"] = round(ing["amount"] * scale, 2)
            ing["gram_weight"] = round(ing["gram_weight"] * scale, 2)
        if res["nutrition"]:
            for k in res["nutrition"]:
                res["nutrition"][k] = round(res["nutrition"][k] * scale, 2)
                
    return res

@app.post("/api/homely-meals/{meal_id}/review", response_model=schemas.HomelyMealReviewResponse)
def review_comment_homely_meal(meal_id: int, req: schemas.HomelyMealReviewRequest, db: Session = Depends(get_db)):
    """Submit rating and comment for a homely meal."""
    meal = db.query(models.HomelyMeal).filter(models.HomelyMeal.id == meal_id).first()
    if not meal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Homely meal with ID {meal_id} not found."
        )
    review = homely_meals_engine.add_review(db, meal_id, req.reviewer_id, req.rating, req.comment)
    return review

@app.post("/api/meal-logs", response_model=schemas.MealLogResponse, status_code=status.HTTP_201_CREATED)
def log_meal_directly(req: schemas.MealLogCreate, db: Session = Depends(get_db)):
    """Log a meal intake for tracking metrics."""
    db_log = models.MealLog(
        user_id=req.user_id,
        log_date=req.log_date,
        meal_type=req.meal_type,
        food_name=req.food_name,
        calories=req.calories,
        protein=req.protein,
        carbs=req.carbs,
        fat=req.fat
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log


@app.post("/api/recipes/generate-instructions")
def generate_recipe_instructions(payload: Dict[str, Any], db: Session = Depends(get_db)):
    """Generate detailed preparation and recipe instructions using Gemini API."""
    import os
    import httpx

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gemini API Key is not set in the environment. Please set GEMINI_API_KEY to enable dynamic AI instructions generation."
        )

    recipe_name = payload.get("recipe_name")
    ingredients = payload.get("ingredients")
    recipe_code = payload.get("recipe_code")
    
    if not recipe_name:
        raise HTTPException(status_code=400, detail="Recipe name is required.")

    # Format prompt for instructions
    prompt = f"""
    You are an expert chef and nutrition scientist.
    Please provide clear, step-by-step cooking preparation and cooking instructions for:
    Recipe Name: {recipe_name}
    Ingredients: {', '.join(ingredients) if ingredients else 'standard ingredients'}

    Format your response cleanly with numbered steps. Keep it concise, practical, and focus on healthy cooking techniques.
    """

    # Call Gemini API using httpx
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    try:
        response = httpx.post(url, headers=headers, json=data, timeout=30.0)
        response.raise_for_status()
        resp_json = response.json()
        
        # Parse output text from Gemini response structure
        text = resp_json['candidates'][0]['content']['parts'][0]['text']
        instructions_text = text.strip()

        # If it's a database recipe, save it for future lookups so we don't call the API again
        if recipe_code:
            recipe = db.query(models.Recipe).filter(models.Recipe.recipe_code == recipe_code).first()
            if recipe:
                recipe.instructions = instructions_text
                db.commit()

        return {"instructions": instructions_text}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate instructions: {str(e)}"
        )


# --- AI Studio UI Integration Request Models & Endpoints ---
from pydantic import BaseModel
from typing import List, Optional, Dict

class CoachChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = None

class DietPlanRequest(BaseModel):
    user_id: int

class RecipeGeneratorRequest(BaseModel):
    ingredients: str


def get_offline_coach_reply(message: str) -> str:
    msg = message.lower().strip()
    if "pringles" in msg or "chips" in msg or "junk" in msg:
        return (
            "While Pringles can technically fit into a calorie-controlled budget, they are high in processed saturated fats and sodium, while lacking fiber or protein. This makes them highly snackable and low in satiety.\n\n"
            "**🍏 Healthy Tip:** Try air-popped popcorn, spicy roasted edamame, or baked sweet potato chips instead! You get the crunch with a fraction of the processing."
        )
    elif "breakfast" in msg or "morning" in msg:
        return (
            "Here is an elite **NutriX High Protein Breakfast Recipe**:\n\n"
            "**Scrambled Tofu/Egg & Egg Whites**\n"
            "• 2 whole eggs + 100g egg whites\n"
            "• 1/2 sliced avocado for premium fats\n"
            "• 1 slice whole wheat flatbread/toast\n\n"
            "**Macros:** ~420 kcal | 35g Protein | 18g Carbs | 16g Healthy Fats.\n"
            "Provides clean, long-lasting energy for your entire day!"
        )
    elif "snack" in msg or "hungry" in msg:
        return (
            "Some excellent snacks to keep hunger at bay with high nutrient density:\n"
            "1. **Greek Yogurt with Berries**: Probiotics + antioxidants + low calorie protein.\n"
            "2. **A Handful of Almonds**: Heart-healthy monounsaturated fatty acids.\n"
            "3. **Apple Slices with Peanut Butter**: Perfect fiber + fat combo for long-lasting satiety."
        )
    elif "workout" in msg or "training" in msg or "exercise" in msg:
        return (
            "Your post-workout window is crucial for glycogen replenishment and muscle tissue recovery:\n\n"
            "**⚡ Peak Recovery Shake:**\n"
            "• 1 Scoop Pure Whey Isolate Protein (~25g protein)\n"
            "• 1 Medium Ripe Banana (fast-acting glucose to spike insulin and force aminos into muscles)\n"
            "• 250ml cold water or coconut water (rehydration electrolytes)\n\n"
            "Drink this within 45 minutes of completing your workout for gold-standard recovery!"
        )
    else:
        return (
            "That is an excellent question! Nutrition is very personalized. To give you the best advice:\n\n"
            "Focus on getting **sufficient protein (1.6g - 2.0g per kg)**, consuming **plenty of dietary fiber (25g-35g daily)**, and drinking **adequate water (3L+ daily)**.\n\n"
            "Feel free to ask specific questions about ingredients, exercise, or timing!"
        )


@app.post("/api/ai/coach")
def ai_coach(req: CoachChatRequest):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {"reply": get_offline_coach_reply(req.message)}

    import httpx
    instructions = (
        "You are 'NutriX AI Coach', a premium, highly expert smart nutrition and health assistant. "
        "You help users make incredibly healthy food choices, manage goals (like weight loss, muscle gain), "
        "and design customized nutrition plans. Be positive, encouraging, scientifically accurate, and precise. "
        "Provide actionable tips, keep answers punchy, conversational, and use styled bullets."
    )
    
    contents = []
    if req.history:
        for item in req.history:
            role = "user" if item.get("role") == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": item.get("message", "")}]
            })
    
    contents.append({
        "role": "user",
        "parts": [{"text": req.message}]
    })

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": contents,
        "systemInstruction": {
            "parts": [{"text": instructions}]
        }
    }

    try:
        response = httpx.post(url, headers=headers, json=data, timeout=30.0)
        response.raise_for_status()
        resp_json = response.json()
        text = resp_json['candidates'][0]['content']['parts'][0]['text']
        return {"reply": text.strip()}
    except Exception as e:
        return {"reply": get_offline_coach_reply(req.message)}


@app.post("/api/ai/diet-plan")
def ai_diet_plan(req: DietPlanRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    goal = user.goal or "maintenance"
    age = user.age or 30
    gender = user.gender or "male"
    height = user.height or 170.0
    weight = user.weight or 70.0
    activity_level = user.activity_level or "sedentary"
    target_calories = user.target_calories or 2000.0
    target_protein = user.target_protein or 80.0

    prompt = f"""
    Generate a 1-day customized nutrition diet meal plan for a person with the following statistics:
    - Goal: {goal}
    - Age: {age} years old
    - Gender: {gender}
    - Height: {height} cm
    - Weight: {weight} kg
    - Activity Level: {activity_level}
    - Target Calories: {target_calories} kcal
    - Target Protein: {target_protein} g
    
    Provide recommendations structured in 4 meals:
    1. Breakfast
    2. Lunch
    3. Dinner
    4. Snacks
    
    Explain briefly why this fits their specific goals. Include precise ingredients, serving sizes, and calorie counts for each meal. Make the design of output clean, readable, and energetic.
    """

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {"plan": f"Dynamic AI Onboarding Diet Plan generated locally:\n\nBreakfast: Oats with almonds and banana (~450 kcal)\nLunch: Grilled chicken breast with brown rice and broccoli (~600 kcal)\nDinner: Tofu/Paneer stir-fry with mixed vegetables (~450 kcal)\nSnacks: Greek yogurt with honey (~200 kcal)\n\nAdjusted calories to meet your target goal of {target_calories} kcal."}

    import httpx
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {
            "parts": [{"text": "You are an elite sports dietician. Output absolute gold-standard, premium recipe planning recommendations."}]
        }
    }

    try:
        response = httpx.post(url, headers=headers, json=data, timeout=30.0)
        response.raise_for_status()
        resp_json = response.json()
        text = resp_json['candidates'][0]['content']['parts'][0]['text']
        return {"plan": text.strip()}
    except Exception as e:
        return {"plan": f"AI Onboarding Diet Plan generated locally (Gemini API unavailable):\n\nBreakfast: Oats with almonds and banana (~450 kcal)\nLunch: Grilled chicken breast with brown rice and broccoli (~600 kcal)\nDinner: Tofu/Paneer stir-fry with mixed vegetables (~450 kcal)\nSnacks: Greek yogurt with honey (~200 kcal)\n\nAdjusted calories to meet your target goal of {target_calories} kcal."}


@app.post("/api/ai/recipe-generator")
def ai_recipe_generator(req: RecipeGeneratorRequest):
    prompt = f"""
    I have the following ingredients:
    {req.ingredients}
    
    Generate a delicious, healthy, high-nutrient recipe containing these ingredients.
    Output:
    - Recipe Name
    - Cooking Difficulty
    - Total Prep & Cook Time
    - Detailed Ingredients list
    - Step-by-Step Cooking instructions (easy to follow, structured)
    - Total Calories & Core Macro nutrient Breakdown (Protein, Carbs, Fat)
    - Health score / Benefits for fitness
    """

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {"recipe": f"Simulated Recipe based on ingredients: {req.ingredients}\n\nRecipe Name: Healthy Homely Stir-fry\nPrep Time: 15 mins\nInstructions:\n1. Chop ingredients.\n2. Heat a non-stick pan.\n3. Toss in ingredients and stir cook for 10 minutes.\nMacros: ~350 kcal | 20g Protein | 30g Carbs | 12g Fats"}

    import httpx
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {
            "parts": [{"text": "You are a professional chef and health nutritionist combined. Give clean, highly structured kitchen instructions."}]
        }
    }

    try:
        response = httpx.post(url, headers=headers, json=data, timeout=30.0)
        response.raise_for_status()
        resp_json = response.json()
        text = resp_json['candidates'][0]['content']['parts'][0]['text']
        return {"recipe": text.strip()}
    except Exception as e:
        return {"recipe": f"Simulated Recipe based on ingredients (Gemini API offline): {req.ingredients}\n\nRecipe Name: Healthy Homely Stir-fry\nPrep Time: 15 mins\nInstructions:\n1. Chop ingredients.\n2. Heat a non-stick pan.\n3. Toss in ingredients and stir cook for 10 minutes.\nMacros: ~350 kcal | 20g Protein | 30g Carbs | 12g Fats"}


