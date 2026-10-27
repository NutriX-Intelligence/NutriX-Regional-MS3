import os
import shutil
import time
import pandas as pd
from pathlib import Path

BASE_DIR = Path("d:/NutriX/AI Diet Planner")
DATASET_DIR = BASE_DIR / "Dataset"
WACV_DIR = BASE_DIR / "WACV"
TARGET_DIR = BASE_DIR / "Food Dataset"

TARGET_DIR.mkdir(parents=True, exist_ok=True)

# 1. Process and Copy 217-Class Regional Food Datasets
regional_cuisines = [
    ("rajasthani_foods.csv", "Rajasthani"),
    ("bengali_foods.csv", "Bengali"),
    ("punjabi_foods.csv", "Punjabi"),
    ("gujarati_kathiyawadi_foods.csv", "Gujarati / Kathiyawadi"),
    ("maharashtrian_foods.csv", "Maharashtrian"),
    ("south_indian_foods.csv", "South Indian"),
    ("chinese_foods.csv", "Chinese"),
    ("mexican_foods.csv", "Mexican"),
    ("italian_foods.csv", "Italian"),
    ("japanese_foods.csv", "Japanese"),
]

print("=" * 60)
print("1. Processing 10 Regional Food Datasets (217 Classes Total)")
print("=" * 60)

dfs = []
for filename, cuisine_name in regional_cuisines:
    src_file = DATASET_DIR / filename
    dst_file = TARGET_DIR / filename
    if src_file.exists():
        shutil.copy2(src_file, dst_file)
        df = pd.read_csv(src_file)
        df.insert(0, "Cuisine", cuisine_name)
        dfs.append(df)
        print(f"  [COPIED] {filename:32s} -> {len(df):2d} classes ({cuisine_name})")
    else:
        print(f"  [MISSING] {filename}")

# Generate consolidated 217-class dataset
combined_217_df = pd.concat(dfs, ignore_index=True)
combined_217_df.insert(0, "Class_ID", range(1, len(combined_217_df) + 1))
master_217_file = TARGET_DIR / "all_217_regional_recipes_and_ingredients.csv"
combined_217_df.to_csv(master_217_file, index=False)
print(f"  [GENERATED] {master_217_file.name} -> {len(combined_217_df)} total classes")

# 2. Copy WACV 217-Class Metadata & Audits
wacv_meta_files = [
    "REGIONAL_PRIORITY_CLASSES.csv",
    "CORE_REGIONAL_MAPPING.csv",
    "REGIONAL_CLASSES.md",
    "CORE_123_CLASSES.txt",
]

print("\n" + "=" * 60)
print("2. Copying 217-Class Reference & Mapping Files")
print("=" * 60)

for filename in wacv_meta_files:
    src_file = WACV_DIR / filename
    dst_file = TARGET_DIR / filename
    if src_file.exists():
        shutil.copy2(src_file, dst_file)
        print(f"  [COPIED] {filename} ({src_file.stat().st_size:,} bytes)")
    else:
        print(f"  [MISSING] {filename}")

# 3. Copy Recipe & Ingredient Datasets
recipe_ingredient_files = [
    "recipes.xlsx",
    "recipes_names.xlsx",
    "recipes_servingsize.xlsx",
    "recipe_links.xlsx",
    "Indian_Food_Ingredients_Nutrition_CookingMethods.csv",
    "Indain_Food_Cuisine_Dataset.csv",
    "Multi_Cuisine_Recipe_Dataset.csv",
    "Indian_Food_DF.csv",
    "Indian_Food_Nutrition_Processed.csv",
    "indian_food_nutrition_dataset.csv",
    "INDB.xlsx",
    "Units.xlsx",
    "foods_dataset_.csv",
    "ingr_map.pkl",
    "UK_fct.xlsx",
    "US_fct.xlsx",
    "USDA_nrf.xlsx",
    "epi_r.csv",
    "full_format_recipes.json",
    "RAW_recipes.csv",
    "PP_recipes.csv",
    "RecipeNLG_dataset.csv",
]

print("\n" + "=" * 60)
print("3. Copying Recipes and Ingredients Datasets")
print("=" * 60)

for filename in recipe_ingredient_files:
    src_file = DATASET_DIR / filename
    dst_file = TARGET_DIR / filename
    if src_file.exists():
        t0 = time.time()
        shutil.copy2(src_file, dst_file)
        t1 = time.time()
        size_mb = src_file.stat().st_size / (1024 * 1024)
        print(f"  [COPIED] {filename:52s} ({size_mb:7.2f} MB in {t1-t0:5.2f}s)")
    else:
        print(f"  [MISSING] {filename}")

# 3.5. Copy Fast Food Datasets
fast_food_src = DATASET_DIR / "Fast Food"
fast_food_dst = TARGET_DIR / "Fast Food"
if fast_food_src.exists():
    fast_food_dst.mkdir(parents=True, exist_ok=True)
    print("\n" + "=" * 60)
    print("3.5. Copying Fast Food Chains Datasets")
    print("=" * 60)
    for ff_file in fast_food_src.glob("*.xlsx"):
        shutil.copy2(ff_file, fast_food_dst / ff_file.name)
        print(f"  [COPIED] Fast Food: {ff_file.name}")

# 4. Create README in Food Dataset
readme_content = f"""# Food Dataset Collection

This directory contains consolidated datasets for **217 Regional Food Classes**, along with comprehensive **Recipes**, **Ingredients**, and **Nutrition** databases.

---

## 1. 217-Class Regional Food Intelligence Datasets

All regional datasets follow a standardized schema containing complete recipes, required ingredients, calorie counts, and nutrient profiles:
- `['Dish Name', 'Meal Type', 'Dietary Tag', 'Calories (per serving)', 'Key Nutrients', 'Ingredients Required', 'Recipe Instructions']`

| Dataset File | Cuisine | Food Classes / Rows |
| :--- | :--- | :--- |
| `rajasthani_foods.csv` | Rajasthani | 27 |
| `bengali_foods.csv` | Bengali | 22 |
| `punjabi_foods.csv` | Punjabi | 21 |
| `gujarati_kathiyawadi_foods.csv` | Gujarati / Kathiyawadi | 23 |
| `maharashtrian_foods.csv` | Maharashtrian | 22 |
| `south_indian_foods.csv` | South Indian | 22 |
| `chinese_foods.csv` | Chinese | 20 |
| `mexican_foods.csv` | Mexican | 20 |
| `italian_foods.csv` | Italian | 20 |
| `japanese_foods.csv` | Japanese | 20 |
| **`all_217_regional_recipes_and_ingredients.csv`** | **All 10 Cuisines** | **217 (Master Consolidated)** |

### 217-Class Supporting Documentation & Class Maps
- `REGIONAL_CLASSES.md`: Full catalog of 217 classes grouped by cuisine with caloric density and meal tags.
- `REGIONAL_PRIORITY_CLASSES.csv`: 217 regional classes categorized into Priority Tiers (P0, P1, P2) and CV Readiness.
- `CORE_REGIONAL_MAPPING.csv`: Alignment and mappings between 123 core computer-vision classes and the 217 regional classes.
- `CORE_123_CLASSES.txt`: The 123 core vision baseline classes.

---

## 2. Recipes & Ingredients Datasets

| Dataset File | File Type | Description |
| :--- | :--- | :--- |
| `recipes.xlsx` | Excel (10,271 rows) | Canonical recipe ingredient map with food codes, amounts, units, and nutrient bindings. |
| `recipes_names.xlsx` | Excel (1,014 rows) | Canonical recipe name registry with primary source attribution. |
| `recipes_servingsize.xlsx` | Excel (1,014 rows) | Recipe portion sizes, number of servings, and serving units. |
| `recipe_links.xlsx` | Excel (150 rows) | Source URLs and attribution links for canonical recipes. |
| `Indian_Food_Ingredients_Nutrition_CookingMethods.csv` | CSV (6,513 rows) | Indian recipes with full ingredient lists, cleaned ingredients, and calculated nutrition profiles. |
| `Indain_Food_Cuisine_Dataset.csv` | CSV (8,725 rows) | Large Indian recipe collection with cuisine types, ingredients, cooking times, and preparation instructions. |
| `Multi_Cuisine_Recipe_Dataset.csv` | CSV (3,065 rows) | International multi-cuisine recipes with ingredients, preparation steps, and category tags. |
| `Indian_Food_DF.csv` | CSV (2,645 rows) | Scraped and scored Indian food items and preparations. |
| `Indian_Food_Nutrition_Processed.csv` | CSV (1,014 rows) | Cleaned macronutrient and micronutrient profiles for Indian recipes. |
| `indian_food_nutrition_dataset.csv` | CSV | Quick-reference Indian food nutrition dataset. |
| `foods_dataset_.csv` | CSV (1,000 rows) | Restaurant menu dishes with course, cuisine, taste profile, and image URLs. |

---

## 3. Ingredient & Nutrient Reference Tables

| Dataset File | Description |
| :--- | :--- |
| `INDB.xlsx` | Indian Nutrient Database (1,014 raw ingredients with 42 macro/micronutrients). |
| `Units.xlsx` | Household measurement unit to gram weight conversions (cup, tbsp, piece, bowl, etc.). |
| `ingr_map.pkl` | Serialized ingredient token and alias mapping dictionary. |
| `UK_fct.xlsx` | United Kingdom Food Composition Table. |
| `US_fct.xlsx` | United States Food Composition Table. |
| `USDA_nrf.xlsx` | USDA Nutrient Retention Factors for cooking methods. |
| `Fast Food/*.xlsx` | Fast food nutritional datasets across 8 top chains (Domino's, McDonald's, Subway, Burger King, KFC, Pizza Hut, Starbucks, Taco Bell - 3,355 items). |

---

## 4. Large Recipe Corpora

| Dataset File | Size | Description |
| :--- | :--- | :--- |
| `RecipeNLG_dataset.csv` | ~2.29 GB | RecipeNLG large text recipe corpus (2.23M recipes with ingredients and directions). |
| `RAW_recipes.csv` | ~294 MB | Raw recipe corpus with ingredients, steps, and nutrition tags. |
| `PP_recipes.csv` | ~204 MB | Preprocessed recipes tokenized for NLP and recommendation systems. |
| `full_format_recipes.json` | ~35 MB | Epicurious recipe collection with full ingredient lists and directions in JSON format. |
| `epi_r.csv` | ~55 MB | Epicurious recipe dataset with ratings and 670+ ingredient/flavor tags. |
"""

readme_file = TARGET_DIR / "README.md"
with open(readme_file, "w", encoding="utf-8") as f:
    f.write(readme_content)
print("\n" + "=" * 60)
print(f"4. Created Documentation: {readme_file.name}")
print("=" * 60)

# Check total files copied
total_files = list(TARGET_DIR.glob("*"))
print(f"\nCompleted! Total files in '{TARGET_DIR.name}': {len(total_files)}")
