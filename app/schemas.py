from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict
from datetime import date, datetime

class PreferenceItem(BaseModel):
    preference_type: str = Field(..., description="Type of preference: 'allergy', 'dislike', 'like', 'diet_type'")
    value: str = Field(..., description="Preference value: e.g. 'Milk, whole, Cow' or 'Vegetarian'")

class UserProfileCreate(BaseModel):
    name: str
    email: EmailStr
    age: int = Field(..., gt=0, lt=120)
    gender: str = Field(..., description="'male' or 'female'")
    height: float = Field(..., gt=30.0, lt=300.0, description="Height in cm")
    weight: float = Field(..., gt=10.0, lt=600.0, description="Weight in kg")
    activity_level: str = Field(..., description="'sedentary', 'lightly_active', 'moderately_active', 'active', 'very_active'")
    goal: str = Field(..., description="'fat loss', 'weight gain', 'muscle gain', 'maintenance'")
    preferences: Optional[List[PreferenceItem]] = None

class UserProfileResponse(BaseModel):
    id: int
    name: str
    email: str
    age: int
    gender: str
    height: float
    weight: float
    activity_level: str
    goal: str
    target_calories: float
    target_protein_g: float = Field(..., alias="target_protein")
    target_carbs_g: float = Field(..., alias="target_carbs")
    target_fat_g: float = Field(..., alias="target_fat")
    bmi: Optional[float] = None
    bmi_status: Optional[str] = None
    bmr: Optional[float] = None
    tdee: Optional[float] = None
    created_at: datetime
    diet_type: Optional[str] = None
    likes: Optional[str] = None
    allergies: Optional[str] = None
    dislikes: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True

class RecommendFoodsRequest(BaseModel):
    user_id: int
    limit: Optional[int] = Field(50, ge=1, le=200)

class RankedFoodItem(BaseModel):
    recipe_code: str
    recipe_name: str
    category: str
    score: float
    dietary_tag: Optional[str] = "Vegetarian"
    energy_kcal: float
    protein_g: float
    carb_g: float
    fat_g: float

class GenerateMealPlanRequest(BaseModel):
    user_id: int
    plan_date: Optional[date] = None # Defaults to today
    tolerance: Optional[float] = Field(0.15, ge=0.01, le=0.50)
    preference: Optional[str] = "balanced"  # 'balanced', 'high_protein', 'low_carb', 'low_fat', 'high_fiber'
    meal_cuisines: Optional[Dict[str, str]] = Field(
        None,
        description="Per-meal slot cuisine preference, e.g. {'Breakfast': 'South Indian', 'Lunch': 'Gujarati', 'Dinner': 'Chinese', 'Snack': 'Continental'}"
    )

class MealItem(BaseModel):
    recipe_code: str
    recipe_name: str
    serving_size: float
    serving_unit: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fibre_g: Optional[float] = 0.0

class MealPlanResponse(BaseModel):
    user_id: int
    plan_date: date
    meals: Dict[str, MealItem]
    totals: Dict[str, float]
    targets: Dict[str, float]
    tolerance_used: float

class TrackWeightRequest(BaseModel):
    user_id: int
    weight: float = Field(..., gt=10.0, lt=600.0)
    logged_at: Optional[date] = None # Defaults to today
    adherence: Optional[bool] = None # Optional adherence update for current date's meal plan

class WeightLogEntry(BaseModel):
    id: int
    weight: float
    logged_at: date

    class Config:
        from_attributes = True

class MealPlanHistoryItem(BaseModel):
    id: int
    plan_date: date
    breakfast_recipe_name: Optional[str] = None
    lunch_recipe_name: Optional[str] = None
    dinner_recipe_name: Optional[str] = None
    snack_recipe_name: Optional[str] = None
    actual_calories: Optional[float] = None
    actual_protein: Optional[float] = None
    actual_carbs: Optional[float] = None
    actual_fat: Optional[float] = None
    adherence: Optional[bool] = None

    class Config:
        from_attributes = True

class UserLookupResponse(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class ClassifyRequest(BaseModel):
    recipe_code: Optional[str] = None
    ingredients: Optional[List[str]] = None


class ClassifyResponse(BaseModel):
    is_vegan: bool
    is_vegetarian: bool
    is_eggetarian: bool
    is_jain: bool
    reasons: List[str]
    tags: Optional[List[str]] = []


class HomelyMealIngredientSchema(BaseModel):
    ingredient_name: str
    amount: float
    unit: str

class HomelyMealCalculateRequest(BaseModel):
    ingredients: List[HomelyMealIngredientSchema]

class HomelyMealCalculateResponse(BaseModel):
    ingredients: List[Dict]
    totals: Dict[str, float]

class HomelyMealCreateRequest(BaseModel):
    name: str
    creator_id: Optional[int] = None
    is_community: Optional[bool] = False
    cuisine: Optional[str] = None
    region: Optional[str] = None
    ingredients: List[HomelyMealIngredientSchema]
    tags: Optional[List[str]] = None

class HomelyMealNutritionSchema(BaseModel):
    energy_kcal: float
    protein_g: float
    carb_g: float
    fat_g: float
    fibre_g: float
    sodium_mg: float
    sugar_g: float

    class Config:
        from_attributes = True

class HomelyMealResponse(BaseModel):
    id: int
    name: str
    creator_id: Optional[int] = None
    is_community: bool
    status: str
    popularity: int
    cuisine: Optional[str] = None
    region: Optional[str] = None
    created_at: datetime
    ingredients: List[Dict]
    nutrition: Optional[HomelyMealNutritionSchema] = None
    tags: List[str] = []

    class Config:
        from_attributes = True

class HomelyMealReviewRequest(BaseModel):
    reviewer_id: Optional[int] = None
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None

class HomelyMealReviewResponse(BaseModel):
    id: int
    meal_id: int
    reviewer_id: Optional[int] = None
    rating: int
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class HomelyMealStatusUpdateRequest(BaseModel):
    status: str
    reviewer_id: Optional[int] = None
    comment: Optional[str] = None


class MealLogCreate(BaseModel):
    user_id: int
    log_date: date
    meal_type: str
    food_name: str
    calories: float
    protein: float
    carbs: float
    fat: float

class MealLogResponse(BaseModel):
    id: int
    user_id: int
    log_date: date
    meal_type: str
    food_name: str
    calories: float
    protein: float
    carbs: float
    fat: float

    class Config:
        from_attributes = True


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    age: int = Field(..., gt=0, lt=120)
    gender: str = Field(..., description="'male' or 'female'")
    height: float = Field(..., gt=30.0, lt=300.0, description="Height in cm")
    weight: float = Field(..., gt=10.0, lt=600.0, description="Weight in kg")
    activity_level: str = Field(..., description="'sedentary', 'lightly_active', 'moderately_active', 'active', 'very_active'")
    goal: str = Field(..., description="'fat loss', 'weight gain', 'muscle gain', 'maintenance'")
    preferences: Optional[List[PreferenceItem]] = None


class GoogleLoginRequest(BaseModel):
    id_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class SearchHistoryCreate(BaseModel):
    query: str


class SearchHistoryResponse(BaseModel):
    id: int
    user_id: int
    query: str
    searched_at: datetime

    class Config:
        from_attributes = True


class SettingsUpdate(BaseModel):
    key: str
    value: str


class SettingsResponse(BaseModel):
    id: int
    user_id: int
    key: str
    value: str

    class Config:
        from_attributes = True


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse


class ManualBarcodeRequest(BaseModel):
    barcode: str
    product_name: str
    brand: Optional[str] = "Unknown Brand"
    ingredients_text: Optional[str] = "No ingredients listed"
    energy_kcal: float
    protein_g: float
    carb_g: float
    fat_g: float
    fibre_g: Optional[float] = 0.0
    sodium_mg: Optional[float] = 0.0
    sugar_g: Optional[float] = 0.0
    saturated_fat_g: Optional[float] = 0.0


class AlternativesRequest(BaseModel):
    product_name: str
    meal_type: str
    protein_g: float
    energy_kcal: float
    sugar_g: Optional[float] = 0.0
    fat_g: Optional[float] = 0.0
    estimated_price: Optional[float] = 20.0



