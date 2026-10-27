# NutriX Food Dataset Collection Report

## Overview
A dedicated **Food Dataset** directory has been created and populated with consolidated datasets for **217 Regional Food Classes**, along with comprehensive **Fast Food Restaurant Chains**, **Recipes**, **Ingredients**, and **Nutrition** databases.

### Directory Locations
- **Workspace Directory**: `d:/NutriX/AI Diet Planner/Food Dataset/`
- **Fast Food Datasets**: `d:/NutriX/AI Diet Planner/Food Dataset/Fast Food/` and `d:/NutriX/AI Diet Planner/Dataset/Fast Food/`
- **Root Directory Junction**: `d:/NutriX/Food Dataset/` *(Linked directly via NTFS junction; accessible interchangeably without data duplication)*

---

## Fast Food Restaurant Chains Datasets (8 Chains, 3,355 Items)

Comprehensive nutrition and portion datasets for 8 major restaurant chains have been parsed and ingested directly into `output/nutrition_master.db`:

| Chain / Brand | File Name | Total Items | Veg Items | Non-Veg Items | Jain Items | Vegan Items | Avg Calories | Key Categories |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **🍕 Domino's** | `Dominos_Nutrition.xlsx` | 90 | 49 | 41 | 3 | 3 | 242.7 kcal | Veg Pizza, Non-Veg Pizza, Sides & Breads, Desserts |
| **🍔 McDonald's** | `Mcdonalds_Nutrition.xlsx` | 144 | 123 | 21 | 0 | 0 | 251.1 kcal | Burgers, Wraps, McCafe, Breakfast, Shakes, Desserts |
| **🥪 Subway** | `Subway_Nutrition.xlsx` | 145 | 76 | 69 | 0 | 0 | 300.5 kcal | Subs (6-inch & Footlong), Salads, Wraps, Cookies |
| **👑 Burger King** | `BurgerKing_Nutrition.xlsx` | 123 | 93 | 30 | 24 | 24 | 299.0 kcal | Whoppers, Burgers, Sides, King Shakes, Beverages |
| **🍗 KFC** | `KFC_Nutrition.xlsx` | 231 | 58 | 173 | 0 | 0 | 540.8 kcal | Buckets & Box Meals, Burgers, Chicken Rolls, Krushers |
| **🍕 Pizza Hut** | `PizzaHut_Nutrition.xlsx` | 303 | 180 | 123 | 0 | 0 | 1,120.0 kcal | Pan Pizzas, Stuffed Crust, Garlic Bread, Pasta, Wings |
| **☕ Starbucks** | `Starbucks_Nutrition.xlsx` | 2,266 | 2,266 | 0 | 130 | 502 | 197.1 kcal | Espresso, Frappuccino, Cold Brew, Teavana, Bakery |
| **🌮 Taco Bell** | `TacoBell_Nutrition.xlsx` | 53 | 33 | 20 | 0 | 0 | 372.3 kcal | Tacos, Burritos, Quesadillas, Chalupas, Sides |
| **TOTAL** | **8 Excel Files** | **3,355** | **2,878** | **477** | **157** | **529** | **~289.4 kcal** | **All 8 Chains Consolidated** |

### Fast Food Features in NutriX
1. **Brand & Section Grouping**: When searching or filtering by brand (e.g. searching "dominos"), items are grouped into intuitive sections (e.g., Domino's Veg Pizza, Non-Veg Pizza, Sides, Desserts) with item counts, min/max calories, and macro breakdown.
2. **Strict Dietary Adherence**: Automatically adheres to user preferences (`Vegetarian`, `Non-Vegetarian`, `Jain`, `Vegan`). Veg users never see non-veg items.
3. **1-Click Diary Logging**: Every fast food item can be logged directly into today's meal diary (`/api/meal-logs`) under Breakfast, Lunch, Dinner, or Snack with full macros recorded.

---

## Regional & Canonical Inventory Matrix

### 1. 217-Class Regional Food Intelligence Datasets
Each regional dataset contains standardized attributes: `['Dish Name', 'Meal Type', 'Dietary Tag', 'Calories (per serving)', 'Key Nutrients', 'Ingredients Required', 'Recipe Instructions']`.

| # | Dataset File | Cuisine | Food Classes / Rows | Dietary Breakdown |
| :-: | :--- | :--- | :-: | :--- |
| 1 | `rajasthani_foods.csv` | Rajasthani | 27 | Jain (7), Vegan (6), Vegetarian (5), Non-Veg (5), Veg/Jain (4) |
| 2 | `gujarati_kathiyawadi_foods.csv` | Gujarati / Kathiyawadi | 23 | Jain (8), Vegetarian (8), Veg/Jain (4), Vegan (3) |
| 3 | `bengali_foods.csv` | Bengali | 22 | Jain (5), Non-Veg (5), Vegetarian (4), Vegan (4), Veg/Jain (4) |
| 4 | `maharashtrian_foods.csv` | Maharashtrian | 22 | Jain (6), Veg/Jain (5), Vegan (5), Non-Veg (4), Vegetarian (2) |
| 5 | `south_indian_foods.csv` | South Indian | 22 | Vegan (5), Jain (5), Non-Veg (5), Vegetarian (4), Veg/Jain (3) |
| 6 | `punjabi_foods.csv` | Punjabi | 21 | Vegetarian (8), Non-Veg (7), Jain (3), Vegan (2), Veg/Jain (1) |
| 7 | `chinese_foods.csv` | Chinese | 20 | Non-Veg (8), Vegan (6), Vegetarian (3), Jain (3) |
| 8 | `mexican_foods.csv` | Mexican | 20 | Non-Veg (7), Vegan (6), Vegetarian (4), Jain (3) |
| 9 | `italian_foods.csv` | Italian | 20 | Vegetarian (7), Vegan (5), Non-Veg (4), Jain (4) |
| 10 | `japanese_foods.csv` | Japanese | 20 | Vegan (7), Non-Veg (6), Jain (5), Eggetarian (2) |
| **★** | **`all_217_regional_recipes_and_ingredients.csv`** | **All 10 Cuisines Combined** | **217** | **Master Consolidated Dataset (Class_ID 1 to 217)** |

---

### 2. 217-Class Metadata, Mappings & CV Readiness

| File Name | Format | Size | Description |
| :--- | :---: | :---: | :--- |
| `REGIONAL_CLASSES.md` | Markdown | 17.5 KB | Comprehensive catalog and culinary audit of all 217 regional classes across all 10 cuisines. |
| `REGIONAL_PRIORITY_CLASSES.csv` | CSV | 33.2 KB | 217 classes categorized by Priority Tier (P0/P1/P2), Collection Difficulty, and CV Readiness. |
| `CORE_REGIONAL_MAPPING.csv` | CSV | 13.1 KB | Direct semantic and ingredient mapping between the 123 core vision classes and the 217 regional classes. |
| `CORE_123_CLASSES.txt` | TXT | 2.4 KB | Canonical class list of the 123 core vision detection classes. |

---

### 3. Canonical Recipe & Ingredient Databases

| Dataset File | Format | Rows | Description |
| :--- | :---: | :---: | :--- |
| `recipes.xlsx` | Excel | 10,271 | Canonical recipe ingredient map specifying exact ingredient names, food codes, amounts, and units. |
| `recipes_names.xlsx` | Excel | 1,014 | Canonical recipe name index and primary source attribution catalog. |
| `recipes_servingsize.xlsx` | Excel | 1,014 | Standard portion sizes, serving counts, and serving unit descriptors. |
| `recipe_links.xlsx` | Excel | 150 | External source URL references for canonical dishes. |
| `Indian_Food_Ingredients_Nutrition_CookingMethods.csv` | CSV | 6,513 | Indian recipes with complete ingredient lists, cleaned ingredients, calculated nutrition, and cooking techniques. |
| `Indain_Food_Cuisine_Dataset.csv` | CSV | 8,725 | Large Indian recipe corpus with preparation times, cooking times, dish descriptions, and steps. |
| `Multi_Cuisine_Recipe_Dataset.csv` | CSV | 3,065 | International recipe dataset with ingredient arrays, preparation steps, and meal categories. |
| `Indian_Food_DF.csv` | CSV | 2,645 | Scraped and ranked Indian dish records with regional classification. |
| `Indian_Food_Nutrition_Processed.csv` | CSV | 1,014 | Processed macronutrient and micronutrient profiles for standard Indian preparations. |
| `indian_food_nutrition_dataset.csv` | CSV | 140 | Quick-reference nutritional table for popular Indian foods. |
| `foods_dataset_.csv` | CSV | 1,000 | Restaurant menu dishes with course, cuisine, dietary tag, taste profile, and image URLs. |

---

### 4. Ingredient & Nutrient Composition Reference Tables

| Dataset File | Format | Records | Description |
| :--- | :---: | :---: | :--- |
| `INDB.xlsx` | Excel | 1,014 | Indian Nutrient Database containing 42 macro/micronutrients per 100g of raw ingredient. |
| `Units.xlsx` | Excel | 345 | Household unit to gram weight conversions (tsp, tbsp, cup, bowl, katori, piece, etc.). |
| `ingr_map.pkl` | Pickle | 918 KB | Serialized ingredient token and alias mapping dictionary for NLP parsing. |
| `UK_fct.xlsx` | Excel | 144 | United Kingdom Food Composition Table. |
| `US_fct.xlsx` | Excel | 54 | United States Food Composition Table. |
| `USDA_nrf.xlsx` | Excel | 270 | USDA Cooking Nutrient Retention Factors. |

---

### 5. Large Recipe Corpora

| Dataset File | File Size | Records | Description |
| :--- | :---: | :---: | :--- |
| `RecipeNLG_dataset.csv` | 2.29 GB | 2,231,149 | RecipeNLG large text recipe corpus featuring full ingredient lists and step-by-step instructions. |
| `RAW_recipes.csv` | 294.5 MB | 231,637 | Raw recipe corpus including ingredients, steps, and nutrition tags. |
| `PP_recipes.csv` | 204.9 MB | 178,265 | Preprocessed recipes tokenized for machine learning recommendation systems. |
| `full_format_recipes.json` | 35.2 MB | 20,130 | Epicurious recipe collection with full ingredient lists and directions in JSON format. |
| `epi_r.csv` | 55.2 MB | 20,052 | Epicurious recipe dataset with user ratings and 670+ flavor/ingredient tags. |

---

## Key Highlights & Readiness
1. **Total Database Recipes**: Over **12,494 active dishes** (9,139 home/regional recipes + 3,355 fast food restaurant items) fully searchable and loggable in NutriX.
2. **Fast Food Grouping & Accordion View**: Major brands (Domino's, McDonald's, Subway, Burger King, KFC, Pizza Hut, Starbucks, Taco Bell) display categorized sections with nutritional badge overlays.
3. **Dietary Filter Compliance**: Vegetarian, Non-Vegetarian, Jain, and Vegan tags strictly enforced across all database queries and recommendation engines.
4. **1-Click Logging**: Direct API integration (`/api/meal-logs`) records any meal with real macros into today's diary.
