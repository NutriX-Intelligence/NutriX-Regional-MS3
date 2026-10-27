from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any, Union
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
    water_target_ml: Optional[float] = None
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
    water_target_ml: Optional[float] = None
    bmi: Optional[float] = None
    bmi_status: Optional[str] = None
    bmr: Optional[float] = None
    tdee: Optional[float] = None
    created_at: datetime
    diet_type: Optional[str] = None
    likes: Optional[str] = None
    allergies: Optional[str] = None
    dislikes: Optional[str] = None
    is_onboarded: Optional[bool] = False

    class Config:
        from_attributes = True
        populate_by_name = True

class RecommendFoodsRequest(BaseModel):
    user_id: int
    limit: Optional[int] = Field(60, ge=1, le=2000)
    query: Optional[str] = None
    category: Optional[str] = None
    cuisine: Optional[str] = None
    brand: Optional[str] = None
    diet_filter: Optional[str] = None
    offset: Optional[int] = 0
    max_cooking_time: Optional[int] = None

class RankedFoodItem(BaseModel):
    recipe_code: str
    recipe_name: str
    category: str
    cuisine: Optional[str] = "Indian"
    brand: Optional[str] = None
    cooking_time_minutes: Optional[int] = None
    score: float
    health_score: Optional[float] = 80.0
    dietary_tag: Optional[str] = "Vegetarian"
    portion_str: Optional[str] = None
    energy_kcal: float
    protein_g: float
    carb_g: float
    fat_g: float
    sodium_mg: Optional[float] = 0.0
    sugar_g: Optional[float] = 0.0
    fibre_g: Optional[float] = 0.0

class FastFoodItem(BaseModel):
    recipe_code: str
    recipe_name: str
    brand: str
    category: str
    sub_category: Optional[str] = None
    dietary_tag: str
    portion_str: Optional[str] = "1 serve"
    energy_kcal: float
    protein_g: float
    carb_g: float
    fat_g: float
    sugar_g: Optional[float] = 0.0
    sodium_mg: Optional[float] = 0.0
    fibre_g: Optional[float] = 0.0

class FastFoodSection(BaseModel):
    section_name: str
    items: List[FastFoodItem]

class FastFoodGroup(BaseModel):
    brand: str
    cuisine: str
    item_count: int
    veg_count: int
    non_veg_count: int
    jain_count: Optional[int] = 0
    vegan_count: Optional[int] = 0
    min_calories: Optional[float] = 0.0
    max_calories: Optional[float] = 0.0
    sections: List[FastFoodSection]

class FastFoodChainSummary(BaseModel):
    brand: str
    icon: str
    total_items: int
    veg_count: int
    non_veg_count: int
    jain_count: int
    vegan_count: int
    avg_calories: float
    categories: List[str]



class GenerateMealPlanRequest(BaseModel):
    user_id: int
    plan_date: Optional[date] = None # Defaults to today
    tolerance: Optional[float] = Field(None, ge=0.01, le=0.50)
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
    dietary_tag: Optional[str] = "Vegetarian"
    is_gluten_free: Optional[bool] = True
    is_dairy_free: Optional[bool] = True
    is_nut_free: Optional[bool] = True
    is_pescatarian: Optional[bool] = True
    is_halal: Optional[bool] = True
    is_kosher: Optional[bool] = True
    is_keto: Optional[bool] = True
    is_paleo: Optional[bool] = True
    is_low_fodmap: Optional[bool] = True
    is_sattvic: Optional[bool] = True
    is_clean_label: Optional[bool] = True
    confidence_score: Optional[float] = 0.99
    safety_rating: Optional[str] = "Safe / Highly Compliant"
    allergens: Optional[List[str]] = []
    dietary_flags: Optional[Dict[str, bool]] = {}
    detailed_reasons: Optional[Dict[str, List[str]]] = {}
    ingredient_breakdown: Optional[List[Dict[str, Any]]] = []
    substitutions: Optional[List[Dict[str, Any]]] = []
    reasons: List[str]
    tags: Optional[List[str]] = []


class SubstitutionRequest(BaseModel):
    ingredients: List[str]
    target_diet: str = "jain"


class SubstitutionItem(BaseModel):
    original_ingredient: str
    violates_diet: str
    detected_trigger: str
    recommended_substitutes: List[str]
    culinary_tip: str


class SubstitutionResponse(BaseModel):
    target_diet: str
    substitutions: List[SubstitutionItem]



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
    log_date: Optional[Union[date, str]] = None
    meal_type: str = "Snack"
    food_name: str
    calories: float = 0.0
    protein: float = 0.0
    carbs: float = 0.0
    fat: float = 0.0

class MealLogResponse(BaseModel):
    id: int
    user_id: int
    log_date: Union[datetime, date, str]
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
    age: Optional[int] = Field(25, gt=0, lt=120)
    gender: Optional[str] = Field("male", description="'male' or 'female'")
    height: Optional[float] = Field(170.0, gt=30.0, lt=300.0, description="Height in cm")
    weight: Optional[float] = Field(70.0, gt=10.0, lt=600.0, description="Weight in kg")
    activity_level: Optional[str] = Field("sedentary", description="'sedentary', 'lightly_active', 'moderately_active', 'active', 'very_active'")
    goal: Optional[str] = Field("maintenance", description="'fat loss', 'weight gain', 'muscle gain', 'maintenance'")
    water_target_ml: Optional[float] = Field(None, description="Daily water target in ml")
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
    is_new_user: Optional[bool] = False
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


class WaterLogCreate(BaseModel):
    user_id: int
    amount_ml: float = Field(..., gt=0.0, le=10000.0, description="Amount of water in ml")
    logged_at: Optional[Union[datetime, date]] = None


class WaterLogResponse(BaseModel):
    id: int
    user_id: int
    amount_ml: float
    logged_at: Union[datetime, date]

    class Config:
        from_attributes = True


class WaterTodayResponse(BaseModel):
    user_id: int
    date: date
    total_ml: float
    target_ml: float
    progress_pct: float
    logs: List[WaterLogResponse]


class WaterHistoryItem(BaseModel):
    date: str
    total_ml: float


class WaterHistoryResponse(BaseModel):
    user_id: int
    history: List[WaterHistoryItem]


class StatusResponse(BaseModel):
    status: str = "success"
    message: str



