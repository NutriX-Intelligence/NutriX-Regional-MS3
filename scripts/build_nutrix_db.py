import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "Dataset" / "raw"
OUTPUT_DIR = BASE_DIR / "output"
DB_PATH = OUTPUT_DIR / "nutrix.db"

print("Database path:", DB_PATH)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def categorize_recipe(name):
    name_lower = name.lower()
    
    # Check breakfast keywords
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
        
    # Check beverage/snack/dessert keywords
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
        
    # Default is Lunch/Dinner
    return "Lunch/Dinner"

def load_data_and_build():
    print("Loading raw datasets...")
    names_df = pd.read_excel(RAW_DIR / "recipes_names.xlsx")
    servings_df = pd.read_excel(RAW_DIR / "recipes_servingsize.xlsx")
    indb_df = pd.read_excel(RAW_DIR / "INDB.xlsx")
    recipes_df = pd.read_excel(RAW_DIR / "recipes.xlsx")
    
    # Standardize spaces in strings
    names_df['recipe_code'] = names_df['recipe_code'].astype(str).str.strip()
    names_df['recipe_name'] = names_df['recipe_name'].astype(str).str.strip()
    
    servings_df['recipe_code'] = servings_df['recipe_code'].astype(str).str.strip()
    
    indb_df['food_code'] = indb_df['food_code'].astype(str).str.strip()
    
    recipes_df['recipe_code'] = recipes_df['recipe_code'].astype(str).str.strip()
    recipes_df['food_code'] = recipes_df['food_code'].astype(str).str.strip()
    recipes_df['ingredient_name_org'] = recipes_df['ingredient_name_org'].astype(str).str.strip()
    recipes_df['food_name'] = recipes_df['food_name'].astype(str).str.strip()

    print(f"Loaded {len(names_df)} recipe names, {len(servings_df)} serving sizes, {len(indb_df)} INDB nutrition records, and {len(recipes_df)} recipe ingredients.")

    # Apply categorization
    names_df['category'] = names_df['recipe_name'].apply(categorize_recipe)
    print("\nCategorization Summary:")
    print(names_df['category'].value_counts())

    # Open SQLite connection
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Drop existing tables to start fresh
    cursor.execute("DROP TABLE IF EXISTS recipe_ingredients;")
    cursor.execute("DROP TABLE IF EXISTS recipe_nutrition;")
    cursor.execute("DROP TABLE IF EXISTS servings;")
    cursor.execute("DROP TABLE IF EXISTS generated_meal_plans;")
    cursor.execute("DROP TABLE IF EXISTS user_preferences;")
    cursor.execute("DROP TABLE IF EXISTS weight_logs;")
    cursor.execute("DROP TABLE IF EXISTS users;")
    cursor.execute("DROP TABLE IF EXISTS recipes;")

    # Enable foreign key support
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Create tables
    print("\nCreating SQLite tables...")
    cursor.execute("""
    CREATE TABLE recipes (
        recipe_code TEXT PRIMARY KEY,
        recipe_name TEXT NOT NULL,
        primarysource TEXT,
        category TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE servings (
        recipe_code TEXT PRIMARY KEY,
        no_of_servings REAL,
        size_of_servings REAL,
        servings_unit TEXT,
        FOREIGN KEY(recipe_code) REFERENCES recipes(recipe_code)
    );
    """)

    cursor.execute("""
    CREATE TABLE recipe_nutrition (
        recipe_code TEXT PRIMARY KEY,
        energy_kcal REAL,
        carb_g REAL,
        protein_g REAL,
        fat_g REAL,
        freesugar_g REAL,
        fibre_g REAL,
        sodium_mg REAL,
        calcium_mg REAL,
        iron_mg REAL,
        vitc_mg REAL,
        folate_ug REAL,
        unit_serving_energy_kcal REAL,
        unit_serving_carb_g REAL,
        unit_serving_protein_g REAL,
        unit_serving_fat_g REAL,
        unit_serving_freesugar_g REAL,
        unit_serving_fibre_g REAL,
        unit_serving_sodium_mg REAL,
        unit_serving_calcium_mg REAL,
        unit_serving_iron_mg REAL,
        unit_serving_vitc_mg REAL,
        unit_serving_folate_ug REAL,
        FOREIGN KEY(recipe_code) REFERENCES recipes(recipe_code)
    );
    """)

    cursor.execute("""
    CREATE TABLE recipe_ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipe_code TEXT NOT NULL,
        ingredient_name TEXT,
        food_code TEXT,
        food_name TEXT,
        amount REAL,
        unit TEXT,
        amount_org TEXT,
        unit_org TEXT,
        FOREIGN KEY(recipe_code) REFERENCES recipes(recipe_code)
    );
    """)

    cursor.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        age INTEGER,
        gender TEXT,
        height REAL,
        weight REAL,
        activity_level TEXT,
        goal TEXT,
        target_calories REAL,
        target_protein REAL,
        target_carbs REAL,
        target_fat REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    # 2. Insert recipe data
    print("Inserting recipes...")
    recipes_inserted = 0
    for idx, row in names_df.iterrows():
        cursor.execute(
            "INSERT INTO recipes (recipe_code, recipe_name, primarysource, category) VALUES (?, ?, ?, ?)",
            (row['recipe_code'], row['recipe_name'], row['primarysource'], row['category'])
        )
        recipes_inserted += 1
    print(f"Inserted {recipes_inserted} recipes.")

    # 3. Insert servings data
    print("Inserting servings...")
    servings_inserted = 0
    # Deduplicate servings just in case
    servings_df = servings_df.drop_duplicates(subset=['recipe_code'])
    for idx, row in servings_df.iterrows():
        # Clean numeric fields
        no_serv = float(row['no_of_servings']) if pd.notna(row['no_of_servings']) else None
        size_serv = float(row['size_of_servings']) if pd.notna(row['size_of_servings']) else None
        serv_unit = str(row['servings_unit']) if pd.notna(row['servings_unit']) else None
        
        cursor.execute(
            "INSERT INTO servings (recipe_code, no_of_servings, size_of_servings, servings_unit) VALUES (?, ?, ?, ?)",
            (row['recipe_code'], no_serv, size_serv, serv_unit)
        )
        servings_inserted += 1
    print(f"Inserted {servings_inserted} servings records.")

    # 4. Insert nutrition data
    print("Inserting nutrition...")
    nutrition_inserted = 0
    # Let's map INDB's columns and fill NAs with 0
    for idx, row in indb_df.iterrows():
        code = row['food_code']
        
        def get_val(col):
            val = row[col]
            if pd.isna(val) or val == 'N' or val == 'Tr' or str(val).strip() == '':
                return 0.0
            try:
                return float(val)
            except ValueError:
                return 0.0

        energy = get_val('energy_kcal')
        carb = get_val('carb_g')
        protein = get_val('protein_g')
        fat = get_val('fat_g')
        freesugar = get_val('freesugar_g')
        fibre = get_val('fibre_g')
        sodium = get_val('sodium_mg')
        calcium = get_val('calcium_mg')
        iron = get_val('iron_mg')
        vitc = get_val('vitc_mg')
        folate = get_val('folate_ug')

        u_energy = get_val('unit_serving_energy_kcal')
        u_carb = get_val('unit_serving_carb_g')
        u_protein = get_val('unit_serving_protein_g')
        u_fat = get_val('unit_serving_fat_g')
        u_freesugar = get_val('unit_serving_freesugar_g')
        u_fibre = get_val('unit_serving_fibre_g')
        u_sodium = get_val('unit_serving_sodium_mg')
        u_calcium = get_val('unit_serving_calcium_mg')
        u_iron = get_val('unit_serving_iron_mg')
        u_vitc = get_val('unit_serving_vitc_mg')
        u_folate = get_val('unit_serving_folate_ug')

        cursor.execute(
            """
            INSERT INTO recipe_nutrition (
                recipe_code, energy_kcal, carb_g, protein_g, fat_g, freesugar_g, fibre_g, sodium_mg, calcium_mg, iron_mg, vitc_mg, folate_ug,
                unit_serving_energy_kcal, unit_serving_carb_g, unit_serving_protein_g, unit_serving_fat_g, unit_serving_freesugar_g, unit_serving_fibre_g,
                unit_serving_sodium_mg, unit_serving_calcium_mg, unit_serving_iron_mg, unit_serving_vitc_mg, unit_serving_folate_ug
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                code, energy, carb, protein, fat, freesugar, fibre, sodium, calcium, iron, vitc, folate,
                u_energy, u_carb, u_protein, u_fat, u_freesugar, u_fibre, u_sodium, u_calcium, u_iron, u_vitc, u_folate
            )
        )
        nutrition_inserted += 1
    print(f"Inserted {nutrition_inserted} nutrition records.")

    # 5. Insert ingredients mapping
    print("Inserting ingredients...")
    ingredients_inserted = 0
    for idx, row in recipes_df.iterrows():
        # Handle cleaning
        amount_val = float(row['amount']) if pd.notna(row['amount']) else None
        
        cursor.execute(
            """
            INSERT INTO recipe_ingredients (
                recipe_code, ingredient_name, food_code, food_name, amount, unit, amount_org, unit_org
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row['recipe_code'],
                row['ingredient_name_org'],
                row['food_code'],
                row['food_name'],
                amount_val,
                row['unit'],
                str(row['amount_org']) if pd.notna(row['amount_org']) else None,
                str(row['unit_org']) if pd.notna(row['unit_org']) else None
            )
        )
        ingredients_inserted += 1
    print(f"Inserted {ingredients_inserted} ingredients mapping records.")

    # Commit and close
    conn.commit()
    conn.close()
    print("\nDatabase built successfully and seeded!")

if __name__ == "__main__":
    load_data_and_build()