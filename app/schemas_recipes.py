"""
NutriX - Schemas for Recipe Intelligence Engine endpoints
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ---------------------------------------------------------------------------
# Ingredient-based recommendation request / response
# ---------------------------------------------------------------------------

class RecipeRecommendRequest(BaseModel):
    """POST /recipes/recommend — find recipes matching user's ingredients."""
    ingredients: List[str] = Field(
        ..., min_length=1,
        description="List of ingredients the user has on hand, e.g. ['rice', 'paneer', 'tomato']"
    )
    goal: Optional[str] = Field(
        None,
        description="Fitness goal: 'weight loss', 'muscle gain', 'weight gain', 'maintenance'"
    )
    diet_type: Optional[str] = Field(
        None,
        description="'vegetarian', 'vegan', or None for no restriction"
    )
    cuisine: Optional[str] = Field(
        None,
        description="Filter by cuisine type, e.g. 'Indian', 'Italian'"
    )
    exclude_ingredients: Optional[List[str]] = Field(
        None,
        description="Ingredients to exclude (allergies/dislikes)"
    )
    max_cooking_time: Optional[int] = Field(
        None, ge=0,
        description="Maximum cooking time in minutes"
    )
    top_n: int = Field(5, ge=1, le=50)


class IngredientMatchInfo(BaseModel):
    score: float = Field(..., description="Ingredient match ratio 0.0-1.0")
    matched: List[str] = Field(..., description="Matched user ingredients")
    missing: List[str] = Field(..., description="Recipe ingredients user doesn't have")


class HealthScoreInfo(BaseModel):
    score: float = Field(..., description="Health score 0-100")
    category: str = Field(..., description="'Healthy', 'Moderate', or 'Unhealthy'")
    explanation: str = Field(..., description="Health explanation text")


class ExplanationInfo(BaseModel):
    summary: str
    bullet_points: List[str]
    suitability: str
    health_note: str
    extra: str


class RankedRecipeResponse(BaseModel):
    recipe_code: str
    recipe_name: str
    category: str
    cuisine: Optional[str] = None
    difficulty: Optional[str] = None
    cooking_time_minutes: Optional[int] = None
    dietary_tag: Optional[str] = "Vegetarian"
    match_score: float
    health_score: float
    health_category: str
    final_score: float
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fibre_g: float = 0.0
    sugar_g: float = 0.0
    ingredient_match: IngredientMatchInfo
    reason: str


class RecipeRecommendResponse(BaseModel):
    query: RecipeRecommendRequest
    total_results: int
    top_recipes: List[RankedRecipeResponse]


# ---------------------------------------------------------------------------
# Filter endpoint
# ---------------------------------------------------------------------------

class RecipeFilterRequest(BaseModel):
    goal: Optional[str] = Field(None, description="Fitness goal for filtering")
    diet_type: Optional[str] = Field(None, description="'vegetarian', 'vegan', 'jain', 'eggetarian', 'non-vegetarian'")
    cuisine: Optional[str] = None
    min_protein: Optional[float] = Field(None, ge=0)
    max_calories: Optional[float] = Field(None, ge=0)
    max_cooking_time: Optional[int] = Field(None, ge=0)
    category: Optional[str] = Field(None, description="'Breakfast', 'Lunch/Dinner', 'Snack'")
    difficulty: Optional[str] = Field(None, description="'Easy', 'Medium', 'Hard'")
    max_results: int = Field(50, ge=1, le=200)


class RecipeDetailResponse(BaseModel):
    recipe_code: str
    recipe_name: str
    category: str
    cuisine: Optional[str] = None
    difficulty: Optional[str] = None
    cooking_time_minutes: Optional[int] = None
    dietary_tag: Optional[str] = "Vegetarian"
    instructions: Optional[str] = None
    primarysource: Optional[str] = None
    ingredients: List[Dict[str, Any]] = []
    nutrition: Optional[Dict[str, Any]] = None
    health_score: Optional[float] = None
    health_category: Optional[str] = None


# ---------------------------------------------------------------------------
# Search endpoint
# ---------------------------------------------------------------------------

class RecipeSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Search term for recipe name")
    category: Optional[str] = None
    cuisine: Optional[str] = None
    max_results: int = Field(20, ge=1, le=100)


class RecipeSearchResult(BaseModel):
    recipe_code: str
    recipe_name: str
    category: str
    cuisine: Optional[str] = None
    dietary_tag: Optional[str] = "Vegetarian"


# ---------------------------------------------------------------------------
# Top recipes
# ---------------------------------------------------------------------------

class TopRecipesResponse(BaseModel):
    recipes: List[Dict[str, Any]]
    total: int
