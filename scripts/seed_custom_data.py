import sqlite3
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "output" / "nutrition_master.db"

def seed_custom_data():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}. Run build_nutrition_master_db.py first.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Add extra Jain and Vegan ingredient rules
    extra_rules = [
        # Jain exclusions
        ("beetroot", "exclude_jain", 1),
        ("turnip", "exclude_jain", 1),
        ("yam", "exclude_jain", 1),
        ("suran", "exclude_jain", 1),
        ("sweet potato", "exclude_jain", 1),
        ("radish", "exclude_jain", 1),
        # Vegan exclusions
        ("ghee", "exclude_vegan", 1),
        ("clarified butter", "exclude_vegan", 1),
        ("gelatin", "exclude_vegan", 1),
        ("honey", "exclude_vegan", 1),
    ]
    print("Seeding extra ingredient rules...")
    for name, rule_type, val in extra_rules:
        cursor.execute(
            "INSERT OR IGNORE INTO ingredient_rules (ingredient_name, rule_type, value) VALUES (?, ?, ?);",
            (name, rule_type, val)
        )

    # 2. Add Drinks and Mocktails to foods and food_nutrients
    drinks = [
        # (food_code, name, brand, barcode, energy_kcal, protein_g, carb_g, fat_g, fibre_g, sodium_mg, sugar_g, saturated_fat_g)
        ("DRINK_0001", "Tender Coconut Water", "Paper Boat", "8901719117972", 20.0, 0.0, 5.0, 0.0, 0.0, 25.0, 5.0, 0.0),
        ("DRINK_0002", "Fresh Lime Soda Sweet", "Homemade", "", 60.0, 0.1, 15.0, 0.0, 0.0, 10.0, 14.0, 0.0),
        ("DRINK_0003", "Fresh Lime Soda Salted", "Homemade", "", 10.0, 0.1, 2.0, 0.0, 0.0, 200.0, 0.0, 0.0),
        ("DRINK_0004", "Masala Buttermilk (Chaas)", "Homemade", "", 30.0, 1.5, 2.5, 1.5, 0.0, 150.0, 2.0, 0.9),
        ("DRINK_0005", "Coca Cola Classic", "Coca-Cola", "5449000000996", 44.0, 0.0, 10.9, 0.0, 0.0, 4.0, 10.6, 0.0),
        ("DRINK_0006", "Diet Coke", "Coca-Cola", "5449000133335", 0.5, 0.0, 0.0, 0.0, 0.0, 10.0, 0.0, 0.0),
        ("DRINK_0007", "Sweet Lassi", "Homemade", "", 90.0, 2.5, 14.0, 3.0, 0.0, 50.0, 12.0, 1.8),
        ("DRINK_0008", "Virgin Mojito Mocktail", "Homemade", "", 70.0, 0.1, 17.0, 0.0, 0.0, 15.0, 16.0, 0.0),
        ("DRINK_0009", "Orange Blossom Mocktail", "Homemade", "", 80.0, 0.5, 19.0, 0.1, 0.0, 8.0, 18.0, 0.0),
        ("DRINK_0010", "Red Bull Energy Drink", "Red Bull", "9002490100070", 45.0, 0.0, 11.0, 0.0, 0.0, 80.0, 11.0, 0.0)
    ]
    
    print("Seeding drinks and mocktails into foods & nutrients...")
    for code, name, brand, barcode, kcal, prot, carb, fat, fib, sod, sug, sat_fat in drinks:
        # Check if already exists
        cursor.execute("SELECT id FROM foods WHERE food_code = ?;", (code,))
        row = cursor.fetchone()
        if row:
            food_id = row[0]
            # Update nutrients
            cursor.execute(
                """
                UPDATE food_nutrients 
                SET energy_kcal=?, protein_g=?, carb_g=?, fat_g=?, fibre_g=?, sodium_mg=?, sugar_g=?, saturated_fat_g=?
                WHERE food_id = ?;
                """,
                (kcal, prot, carb, fat, fib, sod, sug, sat_fat, food_id)
            )
        else:
            cursor.execute(
                "INSERT INTO foods (food_code, name, brand, barcode) VALUES (?, ?, ?, ?);",
                (code, name, brand, barcode or None)
            )
            food_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO food_nutrients (food_id, energy_kcal, protein_g, carb_g, fat_g, fibre_g, sodium_mg, sugar_g, saturated_fat_g)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (food_id, kcal, prot, carb, fat, fib, sod, sug, sat_fat)
            )

    # 3. Seeding homely meals supplement
    homely_meals = [
        # (name, energy_kcal, protein_g, carb_g, fat_g, fibre_g, sodium_mg, sugar_g)
        ("Paneer Tikka", 180.0, 12.0, 6.0, 12.0, 1.5, 450.0, 2.0),
        ("Moong Dal Khichdi", 120.0, 4.5, 22.0, 2.5, 3.0, 300.0, 0.5),
        ("Dal Tadka", 95.0, 5.0, 12.0, 3.0, 4.0, 350.0, 0.0),
        ("Roti (Phulka)", 110.0, 3.0, 22.0, 0.5, 2.5, 50.0, 0.0),
        ("Vegetable Poha", 180.0, 3.5, 35.0, 3.0, 3.5, 280.0, 1.0),
        ("Suji Upma", 160.0, 4.0, 30.0, 2.5, 2.0, 260.0, 1.0),
        ("Idli", 60.0, 1.5, 12.0, 0.1, 1.0, 80.0, 0.0),
        ("Coconut Chutney", 120.0, 1.5, 8.0, 10.0, 2.5, 180.0, 1.5)
    ]

    print("Seeding homely meals supplement...")
    for name, kcal, prot, carb, fat, fib, sod, sug in homely_meals:
        # Check if already exists
        cursor.execute("SELECT id FROM homely_meals WHERE name = ?;", (name,))
        row = cursor.fetchone()
        if row:
            meal_id = row[0]
            cursor.execute(
                """
                UPDATE homely_meal_nutrition 
                SET energy_kcal=?, protein_g=?, carb_g=?, fat_g=?, fibre_g=?, sodium_mg=?, sugar_g=?
                WHERE meal_id = ?;
                """,
                (kcal, prot, carb, fat, fib, sod, sug, meal_id)
            )
        else:
            cursor.execute(
                "INSERT INTO homely_meals (name, status, is_community, popularity, cuisine) VALUES (?, ?, ?, ?, ?);",
                (name, "approved", 1, 100, "Indian")
            )
            meal_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO homely_meal_nutrition (meal_id, energy_kcal, protein_g, carb_g, fat_g, fibre_g, sodium_mg, sugar_g)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (meal_id, kcal, prot, carb, fat, fib, sod, sug)
            )

    conn.commit()
    conn.close()
    print("Successfully seeded all custom datasets into nutrition_master.db!")

if __name__ == "__main__":
    seed_custom_data()
