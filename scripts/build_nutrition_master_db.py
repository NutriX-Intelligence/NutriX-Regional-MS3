import sqlite3
import pandas as pd
from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "Dataset"
OUTPUT_DIR = BASE_DIR / "output"
DB_PATH = OUTPUT_DIR / "nutrition_master.db"

print("Master Database path:", DB_PATH)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def create_schema(cursor):
    print("Dropping existing tables...")
    tables = [
        "search_history", "settings",
        "unit_conversions", "homely_meal_ingredients", "homely_meal_nutrition",
        "homely_meal_versions", "homely_meal_reviews", "homely_meal_tags", "homely_meals",
        "analytics", "health_scores", "recommendation_history", "barcode_cache",
        "generated_meal_plans", "user_preferences", "servings",
        "weight_logs", "water_logs", "meal_logs", "ingredient_rules", "ingredients",
        "recipe_steps", "recipe_nutrition", "recipe_ingredients", "recipes",
        "food_tags", "food_aliases", "food_portions", "food_nutrients",
        "food_categories", "foods", "goals", "profiles", "users"
    ]
    for table in tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table};")

    print("Creating tables...")
    cursor.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        hashed_password TEXT,
        google_id TEXT UNIQUE,
        avatar_url TEXT,
        is_active BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        age INTEGER,
        gender TEXT,
        height REAL,
        weight REAL,
        activity_level TEXT,
        goal TEXT,
        diet_type TEXT,
        target_calories REAL,
        target_protein REAL,
        target_carbs REAL,
        target_fat REAL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE user_preferences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        preference_type TEXT NOT NULL,
        value TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        goal_type TEXT,
        target_weight REAL,
        target_date DATE,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE foods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        food_code TEXT UNIQUE,
        name TEXT NOT NULL,
        brand TEXT,
        barcode TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE food_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE food_nutrients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        food_id INTEGER UNIQUE NOT NULL,
        energy_kcal REAL DEFAULT 0.0,
        protein_g REAL DEFAULT 0.0,
        carb_g REAL DEFAULT 0.0,
        fat_g REAL DEFAULT 0.0,
        fibre_g REAL DEFAULT 0.0,
        sodium_mg REAL DEFAULT 0.0,
        sugar_g REAL DEFAULT 0.0,
        saturated_fat_g REAL DEFAULT 0.0,
        calcium_mg REAL DEFAULT 0.0,
        iron_mg REAL DEFAULT 0.0,
        vitc_mg REAL DEFAULT 0.0,
        folate_ug REAL DEFAULT 0.0,
        FOREIGN KEY(food_id) REFERENCES foods(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE food_portions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        food_id INTEGER NOT NULL,
        amount REAL,
        unit TEXT,
        gram_weight REAL,
        FOREIGN KEY(food_id) REFERENCES foods(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE food_aliases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        food_id INTEGER NOT NULL,
        alias TEXT NOT NULL,
        FOREIGN KEY(food_id) REFERENCES foods(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE food_tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        food_id INTEGER NOT NULL,
        tag TEXT NOT NULL,
        FOREIGN KEY(food_id) REFERENCES foods(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE recipes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipe_code TEXT UNIQUE NOT NULL,
        recipe_name TEXT NOT NULL,
        category TEXT NOT NULL,
        cuisine TEXT,
        difficulty TEXT,
        cooking_time_minutes INTEGER,
        instructions TEXT,
        primarysource TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE servings (
        recipe_code TEXT PRIMARY KEY,
        no_of_servings REAL,
        size_of_servings REAL,
        servings_unit TEXT,
        FOREIGN KEY(recipe_code) REFERENCES recipes(recipe_code) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE recipe_ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipe_id INTEGER NOT NULL,
        recipe_code TEXT,
        ingredient_name TEXT,
        food_code TEXT,
        food_name TEXT,
        amount REAL,
        unit TEXT,
        amount_org TEXT,
        unit_org TEXT,
        FOREIGN KEY(recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE recipe_nutrition (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipe_id INTEGER UNIQUE NOT NULL,
        recipe_code TEXT UNIQUE,
        energy_kcal REAL DEFAULT 0.0,
        carb_g REAL DEFAULT 0.0,
        protein_g REAL DEFAULT 0.0,
        fat_g REAL DEFAULT 0.0,
        freesugar_g REAL DEFAULT 0.0,
        fibre_g REAL DEFAULT 0.0,
        sodium_mg REAL DEFAULT 0.0,
        calcium_mg REAL DEFAULT 0.0,
        iron_mg REAL DEFAULT 0.0,
        vitc_mg REAL DEFAULT 0.0,
        folate_ug REAL DEFAULT 0.0,
        unit_serving_energy_kcal REAL DEFAULT 0.0,
        unit_serving_carb_g REAL DEFAULT 0.0,
        unit_serving_protein_g REAL DEFAULT 0.0,
        unit_serving_fat_g REAL DEFAULT 0.0,
        unit_serving_freesugar_g REAL DEFAULT 0.0,
        unit_serving_fibre_g REAL DEFAULT 0.0,
        unit_serving_sodium_mg REAL DEFAULT 0.0,
        unit_serving_calcium_mg REAL DEFAULT 0.0,
        unit_serving_iron_mg REAL DEFAULT 0.0,
        unit_serving_vitc_mg REAL DEFAULT 0.0,
        unit_serving_folate_ug REAL DEFAULT 0.0,
        FOREIGN KEY(recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE recipe_steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipe_id INTEGER NOT NULL,
        step_number INTEGER NOT NULL,
        instruction TEXT NOT NULL,
        FOREIGN KEY(recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        food_code TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE ingredient_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ingredient_name TEXT NOT NULL,
        rule_type TEXT NOT NULL,
        value BOOLEAN NOT NULL,
        UNIQUE(ingredient_name, rule_type)
    );
    """)

    cursor.execute("""
    CREATE TABLE meal_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        log_date DATE NOT NULL,
        meal_type TEXT NOT NULL,
        food_name TEXT NOT NULL,
        calories REAL NOT NULL,
        protein REAL NOT NULL,
        carbs REAL NOT NULL,
        fat REAL NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE water_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount_ml REAL NOT NULL,
        logged_at DATE NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE weight_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        weight REAL NOT NULL,
        logged_at DATE NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE generated_meal_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        plan_date DATE NOT NULL,
        breakfast_recipe_code TEXT,
        lunch_recipe_code TEXT,
        dinner_recipe_code TEXT,
        snack_recipe_code TEXT,
        breakfast_servings REAL DEFAULT 1.0,
        lunch_servings REAL DEFAULT 1.0,
        dinner_servings REAL DEFAULT 1.0,
        snack_servings REAL DEFAULT 1.0,
        actual_calories REAL,
        actual_protein REAL,
        actual_carbs REAL,
        actual_fat REAL,
        adherence BOOLEAN,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(breakfast_recipe_code) REFERENCES recipes(recipe_code),
        FOREIGN KEY(lunch_recipe_code) REFERENCES recipes(recipe_code),
        FOREIGN KEY(dinner_recipe_code) REFERENCES recipes(recipe_code),
        FOREIGN KEY(snack_recipe_code) REFERENCES recipes(recipe_code)
    );
    """)

    cursor.execute("""
    CREATE TABLE barcode_cache (
        barcode TEXT PRIMARY KEY,
        product_name TEXT,
        brand TEXT,
        ingredients_text TEXT,
        nutrition_grade TEXT,
        nutriments_json TEXT,
        health_score REAL,
        health_category TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE recommendation_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        recommendation_type TEXT NOT NULL,
        recommended_item_code TEXT NOT NULL,
        score REAL NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE health_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_type TEXT NOT NULL,
        item_code TEXT NOT NULL,
        score REAL NOT NULL,
        category TEXT NOT NULL,
        explanation TEXT,
        calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE analytics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        metric_name TEXT NOT NULL,
        metric_value REAL NOT NULL,
        recorded_at DATE NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE unit_conversions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        food_item TEXT NOT NULL,
        unit TEXT NOT NULL,
        gram_weight REAL NOT NULL,
        source TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE homely_meals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        creator_id INTEGER,
        is_community BOOLEAN DEFAULT 0,
        status TEXT DEFAULT 'pending',
        popularity INTEGER DEFAULT 0,
        cuisine TEXT,
        region TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(creator_id) REFERENCES users(id) ON DELETE SET NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE homely_meal_ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meal_id INTEGER NOT NULL,
        ingredient_name TEXT NOT NULL,
        amount REAL NOT NULL,
        unit TEXT NOT NULL,
        gram_weight REAL NOT NULL,
        food_code TEXT,
        FOREIGN KEY(meal_id) REFERENCES homely_meals(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE homely_meal_nutrition (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meal_id INTEGER UNIQUE NOT NULL,
        energy_kcal REAL DEFAULT 0.0,
        protein_g REAL DEFAULT 0.0,
        carb_g REAL DEFAULT 0.0,
        fat_g REAL DEFAULT 0.0,
        fibre_g REAL DEFAULT 0.0,
        sodium_mg REAL DEFAULT 0.0,
        sugar_g REAL DEFAULT 0.0,
        FOREIGN KEY(meal_id) REFERENCES homely_meals(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE homely_meal_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meal_id INTEGER NOT NULL,
        version_number INTEGER NOT NULL,
        edited_by INTEGER,
        change_summary TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(meal_id) REFERENCES homely_meals(id) ON DELETE CASCADE,
        FOREIGN KEY(edited_by) REFERENCES users(id) ON DELETE SET NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE homely_meal_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meal_id INTEGER NOT NULL,
        reviewer_id INTEGER,
        rating INTEGER,
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(meal_id) REFERENCES homely_meals(id) ON DELETE CASCADE,
        FOREIGN KEY(reviewer_id) REFERENCES users(id) ON DELETE SET NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE homely_meal_tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meal_id INTEGER NOT NULL,
        tag TEXT NOT NULL,
        FOREIGN KEY(meal_id) REFERENCES homely_meals(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE search_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        query TEXT NOT NULL,
        searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        key TEXT NOT NULL,
        value TEXT NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

def categorize_recipe(name):
    name_lower = name.lower()
    breakfast_kws = [
        "sandwich", "toast", "pancake", "egg", "omelet", "paratha", "poha", "upma", 
        "idli", "dosa", "oats", "porridge", "muesli", "cereal", "dalia", "flakes",
        "bhurji", "thepla", "cheela", "chilla", "puri", "poori", "chapati", "parotta",
        "appe", "dhokla", "khandvi", "uttapam"
    ]
    if any(kw in name_lower for kw in breakfast_kws):
        if any(kw in name_lower for kw in ["curry", "gravy", "korma"]):
            return "Lunch/Dinner"
        return "Breakfast"
        
    snack_kws = [
        "tea", "coffee", "juice", "shake", "drink", "lassi", "smoothie", "sharbat", 
        "beverage", "soda", "punch", "lemonade", "biscuit", "cookie", "cake", "muffin", 
        "souffle", "pudding", "kheer", "halwa", "laddu", "sweet", "burfi", "chutney", 
        "pickle", "sauce", "dip", "raita", "chips", "popcorn", "samosa", "pakora", 
        "fritter", "chaat", "bhel", "kachori", "salad", "soup", "roll", "cutlet", 
        "snack", "papad", "fry", "bhajia", "vada", "bonda", "kozhukattai", "murukku", 
        "mathri", "namkeen", "shakarpara", "chikki", "pedha", "rasgulla", "gulab jamun",
        "jalebi", "ice cream", "custard", "compote", "sherbet", "jam", "jelly",
        "cooler", "cocoa", "stock", "water", "infusion", "puff"
    ]
    if any(kw in name_lower for kw in snack_kws):
        return "Snack"
        
    return "Lunch/Dinner"

def seed_data(cursor):
    # 1. Ingredient Rules
    rules = [
        # Jain exclusions (no onion, garlic, ginger, potatoes, root vegetables)
        ("onion", "exclude_jain", True),
        ("garlic", "exclude_jain", True),
        ("ginger", "exclude_jain", True),
        ("potato", "exclude_jain", True),
        ("potatoes", "exclude_jain", True),
        ("carrot", "exclude_jain", True),
        ("carrots", "exclude_jain", True),
        ("radish", "exclude_jain", True),
        ("baingan", "exclude_jain", True),
        ("eggplant", "exclude_jain", True),
        ("aubergine", "exclude_jain", True),
        
        # Vegetarian exclusions (no meat, chicken, mutton, fish, beef, pork, seafood)
        ("chicken", "exclude_vegetarian", True),
        ("mutton", "exclude_vegetarian", True),
        ("fish", "exclude_vegetarian", True),
        ("beef", "exclude_vegetarian", True),
        ("pork", "exclude_vegetarian", True),
        ("meat", "exclude_vegetarian", True),
        ("prawn", "exclude_vegetarian", True),
        ("shrimp", "exclude_vegetarian", True),
        ("crab", "exclude_vegetarian", True),
        ("lamb", "exclude_vegetarian", True),
        ("egg", "exclude_vegetarian", True),
        ("eggs", "exclude_vegetarian", True),
        
        # Eggetarian allows eggs but no meat
        ("chicken", "exclude_eggetarian", True),
        ("mutton", "exclude_eggetarian", True),
        ("fish", "exclude_eggetarian", True),
        ("beef", "exclude_eggetarian", True),
        ("pork", "exclude_eggetarian", True),
        ("meat", "exclude_eggetarian", True),
        
        # Vegan exclusions (no dairy, honey, eggs, meat)
        ("chicken", "exclude_vegan", True),
        ("mutton", "exclude_vegan", True),
        ("fish", "exclude_vegan", True),
        ("beef", "exclude_vegan", True),
        ("pork", "exclude_vegan", True),
        ("meat", "exclude_vegan", True),
        ("egg", "exclude_vegan", True),
        ("eggs", "exclude_vegan", True),
        ("milk", "exclude_vegan", True),
        ("cheese", "exclude_vegan", True),
        ("butter", "exclude_vegan", True),
        ("curd", "exclude_vegan", True),
        ("yogurt", "exclude_vegan", True),
        ("paneer", "exclude_vegan", True),
        ("ghee", "exclude_vegan", True),
        ("cream", "exclude_vegan", True),
        ("honey", "exclude_vegan", True),
    ]
    print("Seeding ingredient rules...")
    cursor.executemany(
        "INSERT OR IGNORE INTO ingredient_rules (ingredient_name, rule_type, value) VALUES (?, ?, ?);",
        rules
    )

    # 2. Recipes & Nutrition (INDB + recipes_names + recipes_servingsize)
    print("Loading recipes names, servings, and INDB datasets...")
    names_df = pd.read_excel(RAW_DIR / "recipes_names.xlsx")
    servings_df = pd.read_excel(RAW_DIR / "recipes_servingsize.xlsx")
    indb_df = pd.read_excel(RAW_DIR / "INDB.xlsx")
    recipe_ings_df = pd.read_excel(RAW_DIR / "recipes.xlsx")

    # Standardize codes
    names_df['recipe_code'] = names_df['recipe_code'].astype(str).str.strip()
    names_df['recipe_name'] = names_df['recipe_name'].astype(str).str.strip()
    servings_df['recipe_code'] = servings_df['recipe_code'].astype(str).str.strip()
    indb_df['food_code'] = indb_df['food_code'].astype(str).str.strip()
    recipe_ings_df['recipe_code'] = recipe_ings_df['recipe_code'].astype(str).str.strip()

    # Apply categorization
    names_df['category'] = names_df['recipe_name'].apply(categorize_recipe)

    # Insert recipes and link with auto-increment ID
    recipe_code_map = {}
    print("Inserting recipes into recipes table...")
    for idx, row in names_df.iterrows():
        # Extrapolate some metadata if exists or use placeholder
        cursor.execute(
            """
            INSERT INTO recipes (recipe_code, recipe_name, category, cuisine, difficulty, cooking_time_minutes, instructions, primarysource)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (row['recipe_code'], row['recipe_name'], row['category'], "Indian", "Medium", 30, "Follow standard preparation.", row['primarysource'])
        )
        recipe_code_map[row['recipe_code']] = cursor.lastrowid

    # Insert servings
    print("Inserting servings...")
    servings_df = servings_df.drop_duplicates(subset=['recipe_code'])
    for idx, row in servings_df.iterrows():
        no_serv = float(row['no_of_servings']) if pd.notna(row['no_of_servings']) else None
        size_serv = float(row['size_of_servings']) if pd.notna(row['size_of_servings']) else None
        serv_unit = str(row['servings_unit']) if pd.notna(row['servings_unit']) else None
        
        cursor.execute(
            "INSERT OR IGNORE INTO servings (recipe_code, no_of_servings, size_of_servings, servings_unit) VALUES (?, ?, ?, ?);",
            (row['recipe_code'], no_serv, size_serv, serv_unit)
        )

    # Insert recipe nutrition
    print("Inserting recipe nutrition...")
    for idx, row in indb_df.iterrows():
        code = row['food_code']
        recipe_id = recipe_code_map.get(code)
        if not recipe_id:
            continue

        def get_val(col):
            val = row[col]
            if pd.isna(val) or val == 'N' or val == 'Tr' or str(val).strip() == '':
                return 0.0
            try:
                return float(val)
            except ValueError:
                return 0.0

        cursor.execute(
            """
            INSERT INTO recipe_nutrition (
                recipe_id, recipe_code, energy_kcal, carb_g, protein_g, fat_g, freesugar_g, fibre_g, sodium_mg, calcium_mg, iron_mg, vitc_mg, folate_ug,
                unit_serving_energy_kcal, unit_serving_carb_g, unit_serving_protein_g, unit_serving_fat_g, unit_serving_freesugar_g, unit_serving_fibre_g,
                unit_serving_sodium_mg, unit_serving_calcium_mg, unit_serving_iron_mg, unit_serving_vitc_mg, unit_serving_folate_ug
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                recipe_id, code, get_val('energy_kcal'), get_val('carb_g'), get_val('protein_g'), get_val('fat_g'), get_val('freesugar_g'), get_val('fibre_g'), get_val('sodium_mg'), get_val('calcium_mg'), get_val('iron_mg'), get_val('vitc_mg'), get_val('folate_ug'),
                get_val('unit_serving_energy_kcal'), get_val('unit_serving_carb_g'), get_val('unit_serving_protein_g'), get_val('unit_serving_fat_g'), get_val('unit_serving_freesugar_g'), get_val('unit_serving_fibre_g'), get_val('unit_serving_sodium_mg'), get_val('unit_serving_calcium_mg'), get_val('unit_serving_iron_mg'), get_val('unit_serving_vitc_mg'), get_val('unit_serving_folate_ug')
            )
        )

    # Insert recipe ingredients mapping
    print("Inserting recipe ingredients...")
    for idx, row in recipe_ings_df.iterrows():
        code = row['recipe_code']
        recipe_id = recipe_code_map.get(code)
        if not recipe_id:
            continue

        amount_val = float(row['amount']) if pd.notna(row['amount']) else None
        cursor.execute(
            """
            INSERT INTO recipe_ingredients (recipe_id, recipe_code, ingredient_name, food_code, food_name, amount, unit, amount_org, unit_org)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                recipe_id,
                code,
                row['ingredient_name_org'],
                row['food_code'],
                row['food_name'],
                amount_val,
                row['unit'],
                str(row['amount_org']) if pd.notna(row['amount_org']) else None,
                str(row['unit_org']) if pd.notna(row['unit_org']) else None
            )
        )

    # 3. Seed foods & food_nutrients (Indian_Food_DF.csv, UK_fct.xlsx, US_fct.xlsx, indian_food_nutrition_dataset.csv)
    print("Loading Indian Food DF packaged dataset...")
    food_df = pd.read_csv(RAW_DIR / "Indian_Food_DF.csv", encoding="utf-8", on_bad_lines='skip')
    
    # We will build an in-memory list of loaded foods for cross-referencing
    loaded_foods = []
    
    print("Inserting foods into foods table (Indian Food DF)...")
    food_count = 0
    for idx, row in food_df.iterrows():
        name = row.get('name')
        if not name or pd.isna(name):
            continue
        brand = row.get('brand')
        brand_val = str(brand) if pd.notna(brand) else None

        cursor.execute(
            "INSERT INTO foods (food_code, name, brand) VALUES (?, ?, ?);",
            (f"PACKAGED_{idx:04d}", str(name).strip(), brand_val)
        )
        food_id = cursor.lastrowid

        # Insert nutrients
        def get_nutrient(col):
            val = row.get(col)
            if pd.isna(val):
                return 0.0
            try:
                return float(val)
            except ValueError:
                return 0.0

        # Convert salt to sodium (sodium_mg = salt_g * 400)
        salt = get_nutrient('nutri_salt')
        sodium = salt * 400.0
        
        energy_kcal = get_nutrient('nutri_energy')
        protein_g = get_nutrient('nutri_protein')
        carb_g = get_nutrient('nutri_carbohydrate')
        fat_g = get_nutrient('nutri_fat')
        fibre_g = get_nutrient('nutri_fiber')
        sugar_g = get_nutrient('nutri_sugar')
        saturated_fat_g = get_nutrient('nutri_satuFat')

        cursor.execute(
            """
            INSERT INTO food_nutrients (food_id, energy_kcal, protein_g, carb_g, fat_g, fibre_g, sodium_mg, sugar_g, saturated_fat_g)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (food_id, energy_kcal, protein_g, carb_g, fat_g, fibre_g, sodium, sugar_g, saturated_fat_g)
        )
        
        # Store for cross-referencing
        loaded_foods.append((str(name).strip().lower(), {
            'fibre_g': fibre_g,
            'sodium_mg': sodium,
            'sugar_g': sugar_g,
            'saturated_fat_g': saturated_fat_g,
            'calcium_mg': 0.0,
            'iron_mg': 0.0,
            'vitc_mg': 0.0,
            'folate_ug': 0.0
        }))
        food_count += 1

    print(f"Inserted {food_count} packaged foods.")

    # Ingestion functions for UK FCT and US FCT
    import re

    def clean_nutrient_value(val):
        if pd.isna(val):
            return 0.0
        val_str = str(val).strip()
        if val_str.lower() in ('tr', 'trace'):
            return 0.01
        if val_str.lower() in ('n', 'n/a', 'none', '', 'null'):
            return 0.0
        try:
            cleaned = re.sub(r'[^\d\.\-]', '', val_str)
            if not cleaned:
                return 0.0
            return float(cleaned)
        except Exception:
            return 0.0

    print("Loading UK_fct.xlsx...")
    uk_df = pd.read_excel(RAW_DIR / "UK_fct.xlsx", sheet_name="Sheet1")
    uk_count = 0
    for idx, row in uk_df.iterrows():
        fcode = row.get('food_code')
        fname = row.get('food_name')
        if not fname or pd.isna(fname) or not fcode or pd.isna(fcode):
            continue
        food_code_val = f"UKFCT_{str(fcode).strip()}"
        cursor.execute(
            "INSERT OR IGNORE INTO foods (food_code, name) VALUES (?, ?);",
            (food_code_val, str(fname).strip())
        )
        food_id = cursor.lastrowid
        
        energy_kcal = clean_nutrient_value(row.get('energy_kcal'))
        protein_g = clean_nutrient_value(row.get('protein_g'))
        carb_g = clean_nutrient_value(row.get('carb_g'))
        fat_g = clean_nutrient_value(row.get('fat_g'))
        fibre_g = clean_nutrient_value(row.get('fibre_g'))
        sodium_mg = clean_nutrient_value(row.get('sodium_mg'))
        sugar_g = clean_nutrient_value(row.get('freesugar_g'))
        # Convert sfa_mg (saturated fatty acids) to grams (saturated_fat_g)
        saturated_fat_g = clean_nutrient_value(row.get('sfa_mg')) / 1000.0
        calcium_mg = clean_nutrient_value(row.get('calcium_mg'))
        iron_mg = clean_nutrient_value(row.get('iron_mg'))
        vitc_mg = clean_nutrient_value(row.get('vitc_mg'))
        folate_ug = clean_nutrient_value(row.get('folate_ug'))

        cursor.execute(
            """
            INSERT OR IGNORE INTO food_nutrients (
                food_id, energy_kcal, protein_g, carb_g, fat_g, fibre_g, sodium_mg, sugar_g, saturated_fat_g, calcium_mg, iron_mg, vitc_mg, folate_ug
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                food_id, energy_kcal, protein_g, carb_g, fat_g, fibre_g, sodium_mg, sugar_g, saturated_fat_g, calcium_mg, iron_mg, vitc_mg, folate_ug
            )
        )
        
        loaded_foods.append((str(fname).strip().lower(), {
            'fibre_g': fibre_g,
            'sodium_mg': sodium_mg,
            'sugar_g': sugar_g,
            'saturated_fat_g': saturated_fat_g,
            'calcium_mg': calcium_mg,
            'iron_mg': iron_mg,
            'vitc_mg': vitc_mg,
            'folate_ug': folate_ug
        }))
        uk_count += 1
    print(f"Inserted {uk_count} foods from UK FCT.")

    print("Loading US_fct.xlsx...")
    us_df = pd.read_excel(RAW_DIR / "US_fct.xlsx", sheet_name="Sheet1")
    us_count = 0
    for idx, row in us_df.iterrows():
        fcode = row.get('food_code')
        fname = row.get('food_name')
        if not fname or pd.isna(fname) or not fcode or pd.isna(fcode):
            continue
        food_code_val = f"USFCT_{str(fcode).strip()}"
        cursor.execute(
            "INSERT OR IGNORE INTO foods (food_code, name) VALUES (?, ?);",
            (food_code_val, str(fname).strip())
        )
        food_id = cursor.lastrowid
        
        energy_kcal = clean_nutrient_value(row.get('energy_kcal'))
        protein_g = clean_nutrient_value(row.get('protein_g'))
        carb_g = clean_nutrient_value(row.get('carb_g'))
        fat_g = clean_nutrient_value(row.get('fat_g'))
        fibre_g = clean_nutrient_value(row.get('fibre_g'))
        sodium_mg = clean_nutrient_value(row.get('sodium_mg'))
        sugar_g = clean_nutrient_value(row.get('freesugar_g'))
        saturated_fat_g = clean_nutrient_value(row.get('sfa_mg')) / 1000.0
        calcium_mg = clean_nutrient_value(row.get('calcium_mg'))
        iron_mg = clean_nutrient_value(row.get('iron_mg'))
        vitc_mg = clean_nutrient_value(row.get('vitc_mg'))
        folate_ug = clean_nutrient_value(row.get('folate_ug'))

        cursor.execute(
            """
            INSERT OR IGNORE INTO food_nutrients (
                food_id, energy_kcal, protein_g, carb_g, fat_g, fibre_g, sodium_mg, sugar_g, saturated_fat_g, calcium_mg, iron_mg, vitc_mg, folate_ug
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                food_id, energy_kcal, protein_g, carb_g, fat_g, fibre_g, sodium_mg, sugar_g, saturated_fat_g, calcium_mg, iron_mg, vitc_mg, folate_ug
            )
        )
        
        loaded_foods.append((str(fname).strip().lower(), {
            'fibre_g': fibre_g,
            'sodium_mg': sodium_mg,
            'sugar_g': sugar_g,
            'saturated_fat_g': saturated_fat_g,
            'calcium_mg': calcium_mg,
            'iron_mg': iron_mg,
            'vitc_mg': vitc_mg,
            'folate_ug': folate_ug
        }))
        us_count += 1
    print(f"Inserted {us_count} foods from US FCT.")

    # Seed indian_food_nutrition_dataset.csv
    print("Loading indian_food_nutrition_dataset.csv...")
    def parse_serving_size(serving_str):
        match = re.match(r'^(\d+(?:\.\d+)?)\s+([a-zA-Z\s]+)\s*\((\d+(?:\.\d+)?)(?:g|ml)\)$', serving_str.strip())
        if match:
            amount = float(match.group(1))
            unit = match.group(2).strip()
            gram_weight = float(match.group(3))
            return amount, unit, gram_weight
        return None

    def find_matching_nutrients(food_name, loaded_foods_list):
        words = set(re.findall(r'[a-z0-9]+', food_name.lower()))
        if not words:
            return {}
        best_match = None
        best_score = 0.0
        for loaded_name, nutrients in loaded_foods_list:
            loaded_words = set(re.findall(r'[a-z0-9]+', loaded_name))
            if not loaded_words:
                continue
            overlap = words.intersection(loaded_words)
            score = len(overlap) / len(words)
            if score > best_score:
                best_score = score
                best_match = nutrients
                if score == 1.0:
                    break
        if best_score >= 0.5:
            return best_match
        return {}

    indian_csv_count = 0
    with open(RAW_DIR / "indian_food_nutrition_dataset.csv", "r", encoding="utf-8") as f:
        # Skip header
        f.readline()
        for idx, line in enumerate(f):
            parts = line.strip().split(',')
            if len(parts) < 8:
                continue
            name = ",".join(parts[:-7]).strip()
            category = parts[-7].strip()
            serving_size = parts[-6].strip()
            calories = clean_nutrient_value(parts[-5])
            protein = clean_nutrient_value(parts[-4])
            carbs = clean_nutrient_value(parts[-3])
            fats = clean_nutrient_value(parts[-2])
            dietary_preference = parts[-1].strip()

            food_code_val = f"IND_FOOD_{idx:04d}"
            cursor.execute(
                "INSERT OR IGNORE INTO foods (food_code, name) VALUES (?, ?);",
                (food_code_val, name)
            )
            food_id = cursor.lastrowid

            # Cross-reference missing micro-nutrients
            ref = find_matching_nutrients(name, loaded_foods)
            fibre_g = ref.get('fibre_g', 0.0)
            sodium_mg = ref.get('sodium_mg', 0.0)
            sugar_g = ref.get('sugar_g', 0.0)
            saturated_fat_g = ref.get('saturated_fat_g', 0.0)
            calcium_mg = ref.get('calcium_mg', 0.0)
            iron_mg = ref.get('iron_mg', 0.0)
            vitc_mg = ref.get('vitc_mg', 0.0)
            folate_ug = ref.get('folate_ug', 0.0)

            cursor.execute(
                """
                INSERT OR IGNORE INTO food_nutrients (
                    food_id, energy_kcal, protein_g, carb_g, fat_g, fibre_g, sodium_mg, sugar_g, saturated_fat_g, calcium_mg, iron_mg, vitc_mg, folate_ug
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    food_id, calories, protein, carbs, fats, fibre_g, sodium_mg, sugar_g, saturated_fat_g, calcium_mg, iron_mg, vitc_mg, folate_ug
                )
            )

            # Insert parsed portion size if match succeeds
            parsed_portion = parse_serving_size(serving_size)
            if parsed_portion:
                amt, unt, gr_wt = parsed_portion
                cursor.execute(
                    "INSERT INTO food_portions (food_id, amount, unit, gram_weight) VALUES (?, ?, ?, ?);",
                    (food_id, amt, unt, gr_wt)
                )

            # Insert tag
            cursor.execute(
                "INSERT INTO food_tags (food_id, tag) VALUES (?, ?);",
                (food_id, dietary_preference)
            )
            cursor.execute(
                "INSERT INTO food_tags (food_id, tag) VALUES (?, ?);",
                (food_id, "Indian")
            )
            indian_csv_count += 1
    print(f"Inserted {indian_csv_count} foods from indian_food_nutrition_dataset.csv.")

    # 4. Seed unit_conversions using Units.xlsx
    print("Loading Units.xlsx...")
    units_df = pd.read_excel(RAW_DIR / "Units.xlsx")
    units_df['Food items'] = units_df['Food items'].ffill()

    def parse_gram_weight(val):
        if pd.isna(val):
            return None
        val_str = str(val).strip().lower()
        val_str = val_str.replace('1/4', '0.25').replace('1/2', '0.5').replace('3/4', '0.75').replace('1/3', '0.33')
        match = re.match(r'^([\d\.]+)\s*(?:g|ml)$', val_str)
        if match:
            return float(match.group(1))
        coeff_match = re.search(r'([\d\.]+)', val_str)
        if coeff_match:
            coeff = float(coeff_match.group(1))
            unit_word = re.sub(r'[\d\.\s]', '', val_str)
            if 'tsp' in unit_word or 'teaspoon' in unit_word:
                return coeff * 5.0
            elif 'tbsp' in unit_word or 'tablespoon' in unit_word:
                return coeff * 15.0
            elif 'cup' in unit_word or unit_word == 'c':
                return coeff * 240.0
            elif 'glass' in unit_word:
                return coeff * 200.0
            elif 'bowl' in unit_word:
                return coeff * 200.0
            elif 'piece' in unit_word or 'pcs' in unit_word or 'pc' in unit_word:
                return coeff * 50.0
            elif 'knob' in unit_word:
                return coeff * 20.0
            elif 'blob' in unit_word:
                return coeff * 15.0
            elif 'slice' in unit_word:
                return coeff * 10.0
            elif 'drop' in unit_word:
                return coeff * 0.05
            elif 'sprig' in unit_word:
                return coeff * 1.0
            elif 'strand' in unit_word:
                return coeff * 0.01
            elif 'leaf' in unit_word or 'leaves' in unit_word:
                return coeff * 0.1
            elif 'no' in unit_word or 'number' in unit_word:
                return coeff * 1.0
            elif 'cauliflower' in unit_word:
                return coeff * 600.0
            if not unit_word:
                return coeff
        return None

    units_count = 0
    for idx, row in units_df.iterrows():
        food_item = row.get('Food items')
        unit = row.get('Units')
        units_1_val = row.get('Units.1')
        
        if pd.isna(food_item) or (pd.isna(unit) and pd.isna(units_1_val)):
            continue
            
        gram_weight = parse_gram_weight(units_1_val)
        if gram_weight is None:
            gram_weight = parse_gram_weight(unit)
        if gram_weight is None:
            continue
            
        unit_str = str(unit).strip() if pd.notna(unit) else "piece"
        source_val = str(row.get('Source')).strip() if pd.notna(row.get('Source')) else None
        
        cursor.execute(
            "INSERT INTO unit_conversions (food_item, unit, gram_weight, source) VALUES (?, ?, ?, ?);",
            (str(food_item).strip(), unit_str, float(gram_weight), source_val)
        )
        units_count += 1
    print(f"Inserted {units_count} unit conversions from Units.xlsx.")

    # 5. Seed popular homely meals (approved, community-available)
    print("Seeding popular homely meals...")
    homely_meals_to_seed = [
        {
            "name": "Vada pav",
            "cuisine": "Indian",
            "region": "West India",
            "is_community": 1,
            "status": "approved",
            "ingredients": [
                {"ingredient_name": "potato", "amount": 1.0, "unit": "piece", "gram_weight": 80.0},
                {"ingredient_name": "bread bun", "amount": 1.0, "unit": "piece", "gram_weight": 60.0},
                {"ingredient_name": "butter", "amount": 1.0, "unit": "tsp", "gram_weight": 5.0},
                {"ingredient_name": "oil", "amount": 1.0, "unit": "tsp", "gram_weight": 5.0}
            ],
            "nutrition": {
                "energy_kcal": 290.0,
                "protein_g": 6.5,
                "carb_g": 42.0,
                "fat_g": 11.0,
                "fibre_g": 3.2,
                "sodium_mg": 460.0,
                "sugar_g": 2.5
            }
        },
        {
            "name": "Ghee Rice",
            "cuisine": "Indian",
            "region": "South India",
            "is_community": 1,
            "status": "approved",
            "ingredients": [
                {"ingredient_name": "rice", "amount": 1.0, "unit": "cup", "gram_weight": 195.0},
                {"ingredient_name": "ghee", "amount": 2.0, "unit": "tsp", "gram_weight": 10.0}
            ],
            "nutrition": {
                "energy_kcal": 360.0,
                "protein_g": 6.0,
                "carb_g": 55.0,
                "fat_g": 12.0,
                "fibre_g": 1.5,
                "sodium_mg": 150.0,
                "sugar_g": 0.2
            }
        },
        {
            "name": "Poha",
            "cuisine": "Indian",
            "region": "Central India",
            "is_community": 1,
            "status": "approved",
            "ingredients": [
                {"ingredient_name": "flattened rice", "amount": 1.5, "unit": "cup", "gram_weight": 90.0},
                {"ingredient_name": "onion", "amount": 0.5, "unit": "piece", "gram_weight": 40.0},
                {"ingredient_name": "peanuts", "amount": 1.0, "unit": "tbsp", "gram_weight": 12.0},
                {"ingredient_name": "oil", "amount": 1.0, "unit": "tsp", "gram_weight": 5.0}
            ],
            "nutrition": {
                "energy_kcal": 280.0,
                "protein_g": 7.0,
                "carb_g": 40.0,
                "fat_g": 9.5,
                "fibre_g": 3.5,
                "sodium_mg": 320.0,
                "sugar_g": 1.8
            }
        }
    ]

    for hm in homely_meals_to_seed:
        cursor.execute(
            "INSERT INTO homely_meals (name, creator_id, is_community, status, popularity, cuisine, region) VALUES (?, ?, ?, ?, ?, ?, ?);",
            (hm["name"], None, hm["is_community"], hm["status"], 5, hm["cuisine"], hm["region"])
        )
        meal_id = cursor.lastrowid
        
        # Seed nutrition
        nut = hm["nutrition"]
        cursor.execute(
            "INSERT INTO homely_meal_nutrition (meal_id, energy_kcal, protein_g, carb_g, fat_g, fibre_g, sodium_mg, sugar_g) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
            (meal_id, nut["energy_kcal"], nut["protein_g"], nut["carb_g"], nut["fat_g"], nut["fibre_g"], nut["sodium_mg"], nut["sugar_g"])
        )
        
        # Seed ingredients
        for ing in hm["ingredients"]:
            cursor.execute(
                "INSERT INTO homely_meal_ingredients (meal_id, ingredient_name, amount, unit, gram_weight) VALUES (?, ?, ?, ?, ?);",
                (meal_id, ing["ingredient_name"], ing["amount"], ing["unit"], ing["gram_weight"])
            )

    # Ingest all multi-cuisine and regional datasets
    seed_all_cuisine_datasets(cursor)

def seed_all_cuisine_datasets(cursor):
    print("Loading all cuisine datasets (Regional, Indian Food Cuisine, Multi-Cuisine)...")
    import re
    import ast

    # 1. Regional Cuisines
    regional_files = [
        ("bengali_foods.csv", "Bengali", "REG_BENGALI"),
        ("chinese_foods.csv", "Chinese", "REG_CHINESE"),
        ("gujarati_kathiyawadi_foods.csv", "Gujarati", "REG_GUJARATI"),
        ("italian_foods.csv", "Italian", "REG_ITALIAN"),
        ("japanese_foods.csv", "Japanese", "REG_JAPANESE"),
        ("maharashtrian_foods.csv", "Maharashtrian", "REG_MAHARASHTRIAN"),
        ("mexican_foods.csv", "Mexican", "REG_MEXICAN"),
        ("punjabi_foods.csv", "Punjabi", "REG_PUNJABI"),
        ("rajasthani_foods.csv", "Rajasthani", "REG_RAJASTHANI"),
        ("south_indian_foods.csv", "South Indian", "REG_SOUTH_INDIAN"),
    ]

    reg_count = 0
    for filename, cuisine_name, prefix in regional_files:
        filepath = RAW_DIR / filename
        if not filepath.exists():
            continue
        try:
            df = pd.read_csv(filepath, encoding="utf-8", on_bad_lines='skip')
            for idx, row in df.iterrows():
                dish_name = str(row.get('Dish Name', '')).strip()
                if not dish_name:
                    continue
                code = f"{prefix}_{idx:04d}"
                cat = categorize_recipe(dish_name)
                instructions = str(row.get('Recipe Instructions', 'Follow standard recipe preparation.')).strip()

                cursor.execute("SELECT id FROM recipes WHERE recipe_code = ?;", (code,))
                if cursor.fetchone():
                    continue

                cursor.execute(
                    """
                    INSERT INTO recipes (recipe_code, recipe_name, category, cuisine, difficulty, cooking_time_minutes, instructions, primarysource)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (code, dish_name, cat, cuisine_name, "Medium", 30, instructions, filename)
                )
                recipe_id = cursor.lastrowid

                # Parse calories & nutrients
                cal_str = str(row.get('Calories (per serving)', ''))
                nut_str = str(row.get('Key Nutrients', ''))

                cal_m = re.search(r'(\d+)', cal_str)
                energy_kcal = float(cal_m.group(1)) if cal_m else 250.0

                p_m = re.search(r'Protein\s*\(([\d\.]+)g\)', nut_str, re.I)
                f_m = re.search(r'Fat\s*\(([\d\.]+)g\)', nut_str, re.I)
                c_m = re.search(r'Carbohydrates\s*\(([\d\.]+)g\)', nut_str, re.I)
                fib_m = re.search(r'Fiber\s*\(([\d\.]+)g\)', nut_str, re.I)

                prot = float(p_m.group(1)) if p_m else 8.0
                fat = float(f_m.group(1)) if f_m else 10.0
                carb = float(c_m.group(1)) if c_m else 35.0
                fib = float(fib_m.group(1)) if fib_m else 3.0

                cursor.execute(
                    """
                    INSERT INTO recipe_nutrition (
                        recipe_id, recipe_code, energy_kcal, carb_g, protein_g, fat_g, freesugar_g, fibre_g, sodium_mg, calcium_mg, iron_mg, vitc_mg, folate_ug,
                        unit_serving_energy_kcal, unit_serving_carb_g, unit_serving_protein_g, unit_serving_fat_g, unit_serving_freesugar_g, unit_serving_fibre_g,
                        unit_serving_sodium_mg, unit_serving_calcium_mg, unit_serving_iron_mg, unit_serving_vitc_mg, unit_serving_folate_ug
                    ) VALUES (?, ?, ?, ?, ?, ?, 0.0, ?, 300.0, 50.0, 2.0, 5.0, 20.0, ?, ?, ?, ?, 0.0, ?, 300.0, 50.0, 2.0, 5.0, 20.0);
                    """,
                    (recipe_id, code, energy_kcal, carb, prot, fat, fib, energy_kcal, carb, prot, fat, fib)
                )

                # Ingredients
                ings_str = str(row.get('Ingredients Required', ''))
                if ings_str:
                    ing_list = [i.strip() for i in ings_str.split(',') if i.strip()]
                    for ing_name in ing_list:
                        cursor.execute(
                            """
                            INSERT INTO recipe_ingredients (recipe_id, recipe_code, ingredient_name, food_name, amount, unit)
                            VALUES (?, ?, ?, ?, 1.0, 'portion');
                            """,
                            (recipe_id, code, ing_name, ing_name)
                        )

                # Serving
                cursor.execute(
                    "INSERT OR IGNORE INTO servings (recipe_code, no_of_servings, size_of_servings, servings_unit) VALUES (?, 1.0, 1.0, 'serving');",
                    (code,)
                )
                reg_count += 1
        except Exception as e:
            print(f"Error reading {filename}: {e}")

    print(f"Inserted {reg_count} recipes from 10 Regional Cuisine datasets.")

    # 2. Indian Food Cuisine Dataset
    ind_cuisine_file = RAW_DIR / "Indain_Food_Cuisine_Dataset.csv"
    if ind_cuisine_file.exists():
        try:
            df = pd.read_csv(ind_cuisine_file, encoding="utf-8", on_bad_lines='skip')
            ind_count = 0
            for idx, row in df.iterrows():
                dish_name = str(row.get('name_of_Dish', '')).strip()
                if not dish_name:
                    continue
                code = f"IND_CUISINE_{idx:05d}"
                cat = categorize_recipe(dish_name)

                raw_c = str(row.get('Cuisine_name', ''))
                c_match = re.search(r'Cuisine:\s*([^\\\'"\]]+)', raw_c)
                cuisine_name = c_match.group(1).replace("Recipes", "").strip() if c_match else "Indian"
                if not cuisine_name:
                    cuisine_name = "Indian"

                instructions = str(row.get('Recipe_Instructions', 'Follow standard recipe preparation.')).strip()

                cursor.execute("SELECT id FROM recipes WHERE recipe_code = ?;", (code,))
                if cursor.fetchone():
                    continue

                cursor.execute(
                    """
                    INSERT INTO recipes (recipe_code, recipe_name, category, cuisine, difficulty, cooking_time_minutes, instructions, primarysource)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (code, dish_name, cat, cuisine_name, "Medium", 35, instructions, "Indain_Food_Cuisine_Dataset.csv")
                )
                recipe_id = cursor.lastrowid

                # Macro estimation
                energy_kcal = 300.0
                prot = 10.0
                carb = 40.0
                fat = 12.0
                fib = 4.0

                cursor.execute(
                    """
                    INSERT INTO recipe_nutrition (
                        recipe_id, recipe_code, energy_kcal, carb_g, protein_g, fat_g, freesugar_g, fibre_g, sodium_mg, calcium_mg, iron_mg, vitc_mg, folate_ug,
                        unit_serving_energy_kcal, unit_serving_carb_g, unit_serving_protein_g, unit_serving_fat_g, unit_serving_freesugar_g, unit_serving_fibre_g,
                        unit_serving_sodium_mg, unit_serving_calcium_mg, unit_serving_iron_mg, unit_serving_vitc_mg, unit_serving_folate_ug
                    ) VALUES (?, ?, ?, ?, ?, ?, 0.0, ?, 350.0, 60.0, 2.5, 5.0, 20.0, ?, ?, ?, ?, 0.0, ?, 350.0, 60.0, 2.5, 5.0, 20.0);
                    """,
                    (recipe_id, code, energy_kcal, carb, prot, fat, fib, energy_kcal, carb, prot, fat, fib)
                )

                ing_raw = str(row.get('Ingredients_of_Dish', ''))
                try:
                    ing_list = ast.literal_eval(ing_raw) if ing_raw.startswith('[') else ing_raw.split(',')
                except Exception:
                    ing_list = re.findall(r"'([^']+)'", ing_raw)

                for ing_item in ing_list:
                    ing_name = str(ing_item).strip()
                    if ing_name:
                        cursor.execute(
                            """
                            INSERT INTO recipe_ingredients (recipe_id, recipe_code, ingredient_name, food_name, amount, unit)
                            VALUES (?, ?, ?, ?, 1.0, 'portion');
                            """,
                            (recipe_id, code, ing_name, ing_name)
                        )

                cursor.execute(
                    "INSERT OR IGNORE INTO servings (recipe_code, no_of_servings, size_of_servings, servings_unit) VALUES (?, 1.0, 1.0, 'serving');",
                    (code,)
                )
                ind_count += 1
            print(f"Inserted {ind_count} recipes from Indain_Food_Cuisine_Dataset.csv.")
        except Exception as e:
            print(f"Error loading Indain_Food_Cuisine_Dataset.csv: {e}")

    # 3. Multi Cuisine Recipe Dataset
    multi_file = RAW_DIR / "Multi_Cuisine_Recipe_Dataset.csv"
    if multi_file.exists():
        try:
            df = pd.read_csv(multi_file, encoding="utf-8", on_bad_lines='skip')
            multi_count = 0
            for idx, row in df.iterrows():
                dish_name = str(row.get('name', '')).strip()
                if not dish_name:
                    continue
                code = f"MULTI_CUISINE_{idx:05d}"
                cat = categorize_recipe(dish_name)
                cuisine_name = str(row.get('area', 'Multi-Cuisine')).strip() or "Multi-Cuisine"
                instructions = str(row.get('steps', 'Follow standard preparation steps.')).strip()

                cursor.execute("SELECT id FROM recipes WHERE recipe_code = ?;", (code,))
                if cursor.fetchone():
                    continue

                cursor.execute(
                    """
                    INSERT INTO recipes (recipe_code, recipe_name, category, cuisine, difficulty, cooking_time_minutes, instructions, primarysource)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (code, dish_name, cat, cuisine_name, "Medium", 30, instructions, "Multi_Cuisine_Recipe_Dataset.csv")
                )
                recipe_id = cursor.lastrowid

                energy_kcal = 320.0
                prot = 12.0
                carb = 42.0
                fat = 12.0
                fib = 4.0

                cursor.execute(
                    """
                    INSERT INTO recipe_nutrition (
                        recipe_id, recipe_code, energy_kcal, carb_g, protein_g, fat_g, freesugar_g, fibre_g, sodium_mg, calcium_mg, iron_mg, vitc_mg, folate_ug,
                        unit_serving_energy_kcal, unit_serving_carb_g, unit_serving_protein_g, unit_serving_fat_g, unit_serving_freesugar_g, unit_serving_fibre_g,
                        unit_serving_sodium_mg, unit_serving_calcium_mg, unit_serving_iron_mg, unit_serving_vitc_mg, unit_serving_folate_ug
                    ) VALUES (?, ?, ?, ?, ?, ?, 0.0, ?, 320.0, 50.0, 2.0, 5.0, 20.0, ?, ?, ?, ?, 0.0, ?, 320.0, 50.0, 2.0, 5.0, 20.0);
                    """,
                    (recipe_id, code, energy_kcal, carb, prot, fat, fib, energy_kcal, carb, prot, fat, fib)
                )

                ings_raw = str(row.get('ingredients', ''))
                ing_list = [i.strip() for i in ings_raw.split(',') if i.strip()]
                for ing_item in ing_list:
                    cursor.execute(
                        """
                        INSERT INTO recipe_ingredients (recipe_id, recipe_code, ingredient_name, food_name, amount, unit)
                        VALUES (?, ?, ?, ?, 1.0, 'portion');
                        """,
                        (recipe_id, code, ing_item, ing_item)
                    )

                cursor.execute(
                    "INSERT OR IGNORE INTO servings (recipe_code, no_of_servings, size_of_servings, servings_unit) VALUES (?, 1.0, 1.0, 'serving');",
                    (code,)
                )
                multi_count += 1
            print(f"Inserted {multi_count} recipes from Multi_Cuisine_Recipe_Dataset.csv.")
        except Exception as e:
            print(f"Error loading Multi_Cuisine_Recipe_Dataset.csv: {e}")


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    create_schema(cursor)
    seed_data(cursor)
    conn.commit()
    conn.close()
    print("Database nutrition_master.db created and seeded successfully!")

if __name__ == "__main__":
    main()
