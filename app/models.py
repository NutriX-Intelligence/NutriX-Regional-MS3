from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Date, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime
from app.db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=True)
    google_id = Column(String, nullable=True, unique=True)
    avatar_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan", lazy="joined")
    preferences = relationship("UserPreference", back_populates="user", cascade="all, delete-orphan")
    weight_logs = relationship("WeightLog", back_populates="user", cascade="all, delete-orphan")
    meal_plans = relationship("GeneratedMealPlan", back_populates="user", cascade="all, delete-orphan")
    water_logs = relationship("WaterLog", back_populates="user", cascade="all, delete-orphan")
    meal_logs = relationship("MealLog", back_populates="user", cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan")
    recommendation_history = relationship("RecommendationHistory", back_populates="user", cascade="all, delete-orphan")
    analytics = relationship("Analytics", back_populates="user", cascade="all, delete-orphan")
    homely_meals = relationship("HomelyMeal", foreign_keys="[HomelyMeal.creator_id]", back_populates="creator", cascade="all, delete-orphan")
    search_history = relationship("SearchHistory", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("Settings", back_populates="user", cascade="all, delete-orphan")

    def _get_profile_val(self, field):
        return getattr(self.profile, field) if self.profile else None

    def _set_profile_val(self, field, value):
        if not self.profile:
            self.profile = Profile()
        setattr(self.profile, field, value)

    @property
    def age(self): return self._get_profile_val("age")
    @age.setter
    def age(self, val): self._set_profile_val("age", val)

    @property
    def gender(self): return self._get_profile_val("gender")
    @gender.setter
    def gender(self, val): self._set_profile_val("gender", val)

    @property
    def height(self): return self._get_profile_val("height")
    @height.setter
    def height(self, val): self._set_profile_val("height", val)

    @property
    def weight(self): return self._get_profile_val("weight")
    @weight.setter
    def weight(self, val): self._set_profile_val("weight", val)

    @property
    def activity_level(self): return self._get_profile_val("activity_level")
    @activity_level.setter
    def activity_level(self, val): self._set_profile_val("activity_level", val)

    @property
    def goal(self): return self._get_profile_val("goal")
    @goal.setter
    def goal(self, val): self._set_profile_val("goal", val)

    @property
    def diet_type(self): return self._get_profile_val("diet_type")
    @diet_type.setter
    def diet_type(self, val): self._set_profile_val("diet_type", val)

    @property
    def target_calories(self): return self._get_profile_val("target_calories")
    @target_calories.setter
    def target_calories(self, val): self._set_profile_val("target_calories", val)

    @property
    def target_protein(self): return self._get_profile_val("target_protein")
    @target_protein.setter
    def target_protein(self, val): self._set_profile_val("target_protein", val)

    @property
    def target_carbs(self): return self._get_profile_val("target_carbs")
    @target_carbs.setter
    def target_carbs(self, val): self._set_profile_val("target_carbs", val)

    @property
    def target_fat(self): return self._get_profile_val("target_fat")
    @target_fat.setter
    def target_fat(self, val): self._set_profile_val("target_fat", val)


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    age = Column(Integer)
    gender = Column(String)
    height = Column(Float)
    weight = Column(Float)
    activity_level = Column(String)
    goal = Column(String)
    diet_type = Column(String)
    target_calories = Column(Float)
    target_protein = Column(Float)
    target_carbs = Column(Float)
    target_fat = Column(Float)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="profile")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    preference_type = Column(String, nullable=False)  # 'allergy', 'dislike', 'like', 'diet_type'
    value = Column(String, nullable=False)

    # Relationships
    user = relationship("User", back_populates="preferences")


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    goal_type = Column(String)
    target_weight = Column(Float)
    target_date = Column(Date)

    # Relationships
    user = relationship("User", back_populates="goals")


class Food(Base):
    __tablename__ = "foods"

    id = Column(Integer, primary_key=True, autoincrement=True)
    food_code = Column(String, unique=True, index=True)
    name = Column(String, nullable=False)
    brand = Column(String)
    barcode = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    nutrients = relationship("FoodNutrient", back_populates="food", uselist=False, cascade="all, delete-orphan")
    portions = relationship("FoodPortion", back_populates="food", cascade="all, delete-orphan")
    aliases = relationship("FoodAlias", back_populates="food", cascade="all, delete-orphan")
    tags = relationship("FoodTag", back_populates="food", cascade="all, delete-orphan")


class FoodCategory(Base):
    __tablename__ = "food_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)


class FoodNutrient(Base):
    __tablename__ = "food_nutrients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    food_id = Column(Integer, ForeignKey("foods.id", ondelete="CASCADE"), unique=True, nullable=False)
    energy_kcal = Column(Float, default=0.0)
    protein_g = Column(Float, default=0.0)
    carb_g = Column(Float, default=0.0)
    fat_g = Column(Float, default=0.0)
    fibre_g = Column(Float, default=0.0)
    sodium_mg = Column(Float, default=0.0)
    sugar_g = Column(Float, default=0.0)
    saturated_fat_g = Column(Float, default=0.0)
    calcium_mg = Column(Float, default=0.0)
    iron_mg = Column(Float, default=0.0)
    vitc_mg = Column(Float, default=0.0)
    folate_ug = Column(Float, default=0.0)

    # Relationships
    food = relationship("Food", back_populates="nutrients")


class FoodPortion(Base):
    __tablename__ = "food_portions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    food_id = Column(Integer, ForeignKey("foods.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float)
    unit = Column(String)
    gram_weight = Column(Float)

    # Relationships
    food = relationship("Food", back_populates="portions")


class FoodAlias(Base):
    __tablename__ = "food_aliases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    food_id = Column(Integer, ForeignKey("foods.id", ondelete="CASCADE"), nullable=False)
    alias = Column(String, nullable=False)

    # Relationships
    food = relationship("Food", back_populates="aliases")


class FoodTag(Base):
    __tablename__ = "food_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    food_id = Column(Integer, ForeignKey("foods.id", ondelete="CASCADE"), nullable=False)
    tag = Column(String, nullable=False)

    # Relationships
    food = relationship("Food", back_populates="tags")


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_code = Column(String, unique=True, nullable=False, index=True)
    recipe_name = Column(String, nullable=False)
    category = Column(String, nullable=False)  # 'Breakfast', 'Lunch/Dinner', 'Snack'
    cuisine = Column(String)
    difficulty = Column(String)  # 'Easy', 'Medium', 'Hard'
    cooking_time_minutes = Column(Integer)
    instructions = Column(Text)
    primarysource = Column(String)

    # Relationships
    servings = relationship("Serving", back_populates="recipe", uselist=False, foreign_keys="[Serving.recipe_code]", primaryjoin="Recipe.recipe_code == Serving.recipe_code", cascade="all, delete-orphan")
    nutrition = relationship("RecipeNutrition", back_populates="recipe", uselist=False, foreign_keys="[RecipeNutrition.recipe_code]", primaryjoin="Recipe.recipe_code == RecipeNutrition.recipe_code", cascade="all, delete-orphan")
    ingredients = relationship("RecipeIngredient", back_populates="recipe", foreign_keys="[RecipeIngredient.recipe_code]", primaryjoin="Recipe.recipe_code == RecipeIngredient.recipe_code", cascade="all, delete-orphan")
    steps = relationship("RecipeStep", back_populates="recipe", cascade="all, delete-orphan")


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=True)
    recipe_code = Column(String, ForeignKey("recipes.recipe_code", ondelete="CASCADE"), nullable=True)
    ingredient_name = Column(String)
    food_code = Column(String)
    food_name = Column(String)
    amount = Column(Float)
    unit = Column(String)
    amount_org = Column(String)
    unit_org = Column(String)

    # Relationships
    recipe = relationship("Recipe", back_populates="ingredients", foreign_keys=[recipe_code], primaryjoin="RecipeIngredient.recipe_code == Recipe.recipe_code")


class RecipeNutrition(Base):
    __tablename__ = "recipe_nutrition"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), unique=True, nullable=True)
    recipe_code = Column(String, ForeignKey("recipes.recipe_code", ondelete="CASCADE"), unique=True, nullable=True)
    energy_kcal = Column(Float, default=0.0)
    carb_g = Column(Float, default=0.0)
    protein_g = Column(Float, default=0.0)
    fat_g = Column(Float, default=0.0)
    freesugar_g = Column(Float, default=0.0)
    fibre_g = Column(Float, default=0.0)
    sodium_mg = Column(Float, default=0.0)
    calcium_mg = Column(Float, default=0.0)
    iron_mg = Column(Float, default=0.0)
    vitc_mg = Column(Float, default=0.0)
    folate_ug = Column(Float, default=0.0)

    # Nutrition per serving
    unit_serving_energy_kcal = Column(Float, default=0.0)
    unit_serving_carb_g = Column(Float, default=0.0)
    unit_serving_protein_g = Column(Float, default=0.0)
    unit_serving_fat_g = Column(Float, default=0.0)
    unit_serving_freesugar_g = Column(Float, default=0.0)
    unit_serving_fibre_g = Column(Float, default=0.0)
    unit_serving_sodium_mg = Column(Float, default=0.0)
    unit_serving_calcium_mg = Column(Float, default=0.0)
    unit_serving_iron_mg = Column(Float, default=0.0)
    unit_serving_vitc_mg = Column(Float, default=0.0)
    unit_serving_folate_ug = Column(Float, default=0.0)

    # Relationships
    recipe = relationship("Recipe", back_populates="nutrition", foreign_keys=[recipe_code], primaryjoin="RecipeNutrition.recipe_code == Recipe.recipe_code")


class RecipeStep(Base):
    __tablename__ = "recipe_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False)
    step_number = Column(Integer, nullable=False)
    instruction = Column(Text, nullable=False)

    # Relationships
    recipe = relationship("Recipe", back_populates="steps")


class Serving(Base):
    __tablename__ = "servings"

    recipe_code = Column(String, ForeignKey("recipes.recipe_code", ondelete="CASCADE"), primary_key=True)
    no_of_servings = Column(Float)
    size_of_servings = Column(Float)
    servings_unit = Column(String)

    # Relationships
    recipe = relationship("Recipe", back_populates="servings", foreign_keys=[recipe_code], primaryjoin="Serving.recipe_code == Recipe.recipe_code")


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False, index=True)
    food_code = Column(String)


class IngredientRule(Base):
    __tablename__ = "ingredient_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ingredient_name = Column(String, nullable=False, index=True)
    rule_type = Column(String, nullable=False)  # 'exclude_vegan', 'exclude_vegetarian', 'exclude_jain', etc.
    value = Column(Boolean, nullable=False)


class MealLog(Base):
    __tablename__ = "meal_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    log_date = Column(Date, nullable=False)
    meal_type = Column(String, nullable=False)  # 'Breakfast', 'Lunch', 'Dinner', 'Snack'
    food_name = Column(String, nullable=False)
    calories = Column(Float, nullable=False)
    protein = Column(Float, nullable=False)
    carbs = Column(Float, nullable=False)
    fat = Column(Float, nullable=False)

    # Relationships
    user = relationship("User", back_populates="meal_logs")


class WaterLog(Base):
    __tablename__ = "water_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount_ml = Column(Float, nullable=False)
    logged_at = Column(Date, nullable=False)

    # Relationships
    user = relationship("User", back_populates="water_logs")


class WeightLog(Base):
    __tablename__ = "weight_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    weight = Column(Float, nullable=False)
    logged_at = Column(Date, nullable=False)

    # Relationships
    user = relationship("User", back_populates="weight_logs")


class BarcodeCache(Base):
    __tablename__ = "barcode_cache"

    barcode = Column(String, primary_key=True)
    product_name = Column(String)
    brand = Column(String)
    ingredients_text = Column(String)
    nutrition_grade = Column(String)
    nutriments_json = Column(String)  # JSON string
    health_score = Column(Float)
    health_category = Column(String)
    source_detail = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class RecommendationHistory(Base):
    __tablename__ = "recommendation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recommendation_type = Column(String, nullable=False)  # 'food', 'recipe', 'meal', etc.
    recommended_item_code = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="recommendation_history")


class HealthScore(Base):
    __tablename__ = "health_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_type = Column(String, nullable=False)  # 'recipe' or 'food'
    item_code = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    category = Column(String, nullable=False)
    explanation = Column(Text)
    calculated_at = Column(DateTime, default=datetime.utcnow)


class Analytics(Base):
    __tablename__ = "analytics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    metric_name = Column(String, nullable=False)  # e.g., 'calories_weekly', etc.
    metric_value = Column(Float, nullable=False)
    recorded_at = Column(Date, nullable=False)

    # Relationships
    user = relationship("User", back_populates="analytics")


class GeneratedMealPlan(Base):
    __tablename__ = "generated_meal_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_date = Column(Date, nullable=False)

    breakfast_recipe_code = Column(String, ForeignKey("recipes.recipe_code"), nullable=True)
    lunch_recipe_code = Column(String, ForeignKey("recipes.recipe_code"), nullable=True)
    dinner_recipe_code = Column(String, ForeignKey("recipes.recipe_code"), nullable=True)
    snack_recipe_code = Column(String, ForeignKey("recipes.recipe_code"), nullable=True)

    breakfast_servings = Column(Float, default=1.0)
    lunch_servings = Column(Float, default=1.0)
    dinner_servings = Column(Float, default=1.0)
    snack_servings = Column(Float, default=1.0)

    # Nutrition actually planned
    actual_calories = Column(Float, nullable=True)
    actual_protein = Column(Float, nullable=True)
    actual_carbs = Column(Float, nullable=True)
    actual_fat = Column(Float, nullable=True)

    # tracking completion
    adherence = Column(Boolean, nullable=True)

    # Relationships
    user = relationship("User", back_populates="meal_plans")
    breakfast_recipe = relationship("Recipe", foreign_keys=[breakfast_recipe_code])
    lunch_recipe = relationship("Recipe", foreign_keys=[lunch_recipe_code])
    dinner_recipe = relationship("Recipe", foreign_keys=[dinner_recipe_code])
    snack_recipe = relationship("Recipe", foreign_keys=[snack_recipe_code])


class UnitConversion(Base):
    __tablename__ = "unit_conversions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    food_item = Column(String, nullable=False, index=True)
    unit = Column(String, nullable=False)
    gram_weight = Column(Float, nullable=False)
    source = Column(String)


class HomelyMeal(Base):
    __tablename__ = "homely_meals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, index=True)
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_community = Column(Boolean, default=False)
    status = Column(String, default="pending")  # 'pending', 'approved', 'rejected'
    popularity = Column(Integer, default=0)
    cuisine = Column(String)
    region = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    creator = relationship("User", foreign_keys=[creator_id], back_populates="homely_meals")
    ingredients = relationship("HomelyMealIngredient", back_populates="meal", cascade="all, delete-orphan")
    nutrition = relationship("HomelyMealNutrition", back_populates="meal", uselist=False, cascade="all, delete-orphan")
    versions = relationship("HomelyMealVersion", back_populates="meal", cascade="all, delete-orphan")
    reviews = relationship("HomelyMealReview", back_populates="meal", cascade="all, delete-orphan")
    tags = relationship("HomelyMealTag", back_populates="meal", cascade="all, delete-orphan")


class HomelyMealIngredient(Base):
    __tablename__ = "homely_meal_ingredients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meal_id = Column(Integer, ForeignKey("homely_meals.id", ondelete="CASCADE"), nullable=False)
    ingredient_name = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    gram_weight = Column(Float, nullable=False)
    food_code = Column(String, nullable=True)

    # Relationships
    meal = relationship("HomelyMeal", back_populates="ingredients")


class HomelyMealNutrition(Base):
    __tablename__ = "homely_meal_nutrition"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meal_id = Column(Integer, ForeignKey("homely_meals.id", ondelete="CASCADE"), unique=True, nullable=False)
    energy_kcal = Column(Float, default=0.0)
    protein_g = Column(Float, default=0.0)
    carb_g = Column(Float, default=0.0)
    fat_g = Column(Float, default=0.0)
    fibre_g = Column(Float, default=0.0)
    sodium_mg = Column(Float, default=0.0)
    sugar_g = Column(Float, default=0.0)

    # Relationships
    meal = relationship("HomelyMeal", back_populates="nutrition")


class HomelyMealVersion(Base):
    __tablename__ = "homely_meal_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meal_id = Column(Integer, ForeignKey("homely_meals.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    edited_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    change_summary = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    meal = relationship("HomelyMeal", back_populates="versions")


class HomelyMealReview(Base):
    __tablename__ = "homely_meal_reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meal_id = Column(Integer, ForeignKey("homely_meals.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    rating = Column(Integer)  # 1 to 5
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    meal = relationship("HomelyMeal", back_populates="reviews")


class HomelyMealTag(Base):
    __tablename__ = "homely_meal_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meal_id = Column(Integer, ForeignKey("homely_meals.id", ondelete="CASCADE"), nullable=False)
    tag = Column(String, nullable=False)

    # Relationships
    meal = relationship("HomelyMeal", back_populates="tags")


class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    query = Column(String, nullable=False)
    searched_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="search_history")


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    key = Column(String, nullable=False)
    value = Column(String, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="settings")

