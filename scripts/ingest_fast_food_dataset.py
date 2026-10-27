import os
import re
import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path("d:/NutriX/AI Diet Planner")
FAST_FOOD_DIR = BASE_DIR / "Dataset" / "Fast Food"
DB_PATH = BASE_DIR / "output" / "nutrition_master.db"

def clean_num(val, default=0.0):
    if pd.isna(val) or val in ['ND', 'Not specified', '-', '', 'nan', None]:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    val_str = re.sub(r'[^\d\.]', '', str(val))
    try:
        return float(val_str)
    except:
        return default

def clean_str(val, default=""):
    if pd.isna(val) or val is None:
        return default
    return str(val).strip()

def parse_fast_food_datasets():
    all_items = []
    
    # 1. BURGER KING
    bk_path = FAST_FOOD_DIR / "Burger_King_India_Nutrition_Dietary.xlsx"
    if bk_path.exists():
        xl = pd.ExcelFile(bk_path)
        # BK Main Menu
        if "BK Main Menu" in xl.sheet_names:
            df = pd.read_excel(bk_path, sheet_name="BK Main Menu")
            for idx, r in df.iterrows():
                name = clean_str(r.get("Product"))
                if not name:
                    continue
                subcat = clean_str(r.get("Category"), "Burgers")
                portion = clean_str(r.get("Avg Portion (g/ml)"))
                cal = clean_num(r.get("Energy (kcal)"))
                carb = clean_num(r.get("Carbohydrate (g)"))
                sugar = clean_num(r.get("Sugar (g)"))
                fat = clean_num(r.get("Fat (g)"))
                sat_fat = clean_num(r.get("Saturated Fat (g)"))
                prot = clean_num(r.get("Protein (g)"))
                sod = clean_num(r.get("Sodium (mg)"))
                diet = clean_str(r.get("Dietary Type"), "Vegetarian")
                jain = clean_str(r.get("Jain / No Onion No Garlic"), "No")
                
                diet_tag = "Non-Vegetarian" if "non" in diet.lower() else ("Jain" if "yes" in jain.lower() else "Vegetarian")
                cat = "Beverage" if "beverage" in subcat.lower() or "shake" in subcat.lower() else ("Snack" if "side" in subcat.lower() or "fries" in subcat.lower() or "dessert" in subcat.lower() else "Lunch/Dinner")
                
                all_items.append({
                    "brand": "Burger King",
                    "recipe_code": f"FF_BK_{len(all_items)+1:04d}",
                    "recipe_name": name,
                    "sub_category": subcat,
                    "category": cat,
                    "cuisine": "Burger King",
                    "dietary_tag": diet_tag,
                    "portion_str": f"{portion}g/ml" if portion else "1 serve",
                    "portion_g": clean_num(portion, 100.0),
                    "energy_kcal": cal,
                    "protein_g": prot,
                    "carb_g": carb,
                    "fat_g": fat,
                    "sugar_g": sugar,
                    "sodium_mg": sod,
                    "fibre_g": 0.0,
                })
        # BK Cafe
        if "BK Cafe" in xl.sheet_names:
            df = pd.read_excel(bk_path, sheet_name="BK Cafe")
            for idx, r in df.iterrows():
                name = clean_str(r.get("Product"))
                if not name:
                    continue
                portion = clean_str(r.get("Portion"))
                cal = clean_num(r.get("Energy (kcal)"))
                carb = clean_num(r.get("Carbohydrate (g)"))
                sugar = clean_num(r.get("Sugar (g)"))
                fat = clean_num(r.get("Fat (g)"))
                prot = clean_num(r.get("Protein (g)"))
                sod = clean_num(r.get("Sodium (mg)"))
                diet = clean_str(r.get("Dietary Type"), "Vegetarian")
                jain = clean_str(r.get("Jain / No Onion No Garlic"), "No")
                diet_tag = "Non-Vegetarian" if "non" in diet.lower() else ("Jain" if "yes" in jain.lower() else "Vegetarian")
                
                all_items.append({
                    "brand": "Burger King",
                    "recipe_code": f"FF_BK_{len(all_items)+1:04d}",
                    "recipe_name": f"{name} ({portion})" if portion else name,
                    "sub_category": "BK Cafe",
                    "category": "Beverage",
                    "cuisine": "Burger King",
                    "dietary_tag": diet_tag,
                    "portion_str": portion or "1 cup",
                    "portion_g": clean_num(portion, 200.0),
                    "energy_kcal": cal,
                    "protein_g": prot,
                    "carb_g": carb,
                    "fat_g": fat,
                    "sugar_g": sugar,
                    "sodium_mg": sod,
                    "fibre_g": 0.0,
                })

    # 2. DOMINOS
    dom_path = FAST_FOOD_DIR / "Dominos_Nutrition_Data.xlsx"
    if dom_path.exists():
        df = pd.read_excel(dom_path, sheet_name="Nutrition Data")
        for idx, r in df.iterrows():
            item = clean_str(r.get("Item"))
            if not item:
                continue
            cat_raw = clean_str(r.get("Category"), "Veg")
            size = clean_str(r.get("Size"))
            size_map = {"R": "Regular", "M": "Medium", "L": "Large"}
            size_desc = size_map.get(size.upper(), size) if size else ""
            serving_size = clean_num(r.get("Serving Size (g)"))
            cal = clean_num(r.get("Energy (kcal)"))
            prot = clean_num(r.get("Protein (g)"))
            fat = clean_num(r.get("Fat (g)"))
            carb = clean_num(r.get("Carbohydrates (g)"))
            sug = clean_num(r.get("Sugars (g)"))
            sod = clean_num(r.get("Sodium (mg)"))
            diet_raw = clean_str(r.get("Dietary Type"), "Vegetarian")
            
            if "jain" in diet_raw.lower():
                diet_tag = "Jain"
            elif "vegan" in diet_raw.lower():
                diet_tag = "Vegan"
            elif "non" in diet_raw.lower() or "non" in cat_raw.lower():
                diet_tag = "Non-Vegetarian"
            else:
                diet_tag = "Vegetarian"
                
            dish_name = f"{item} ({size_desc})" if size_desc else item
            cat = "Lunch/Dinner"
            if "bread" in item.lower() or "parcel" in item.lower() or "dip" in item.lower() or "taco" in item.lower():
                cat = "Snack"
            elif "cake" in item.lower() or "mousse" in item.lower() or "dessert" in item.lower():
                cat = "Snack"
            elif "pepsi" in item.lower() or "mirinda" in item.lower() or "drink" in item.lower():
                cat = "Beverage"
                
            all_items.append({
                "brand": "Domino's",
                "recipe_code": f"FF_DOM_{len(all_items)+1:04d}",
                "recipe_name": dish_name,
                "sub_category": f"Domino's {cat_raw} Pizza" if "pizza" in item.lower() or size_desc else f"Domino's {cat_raw}",
                "category": cat,
                "cuisine": "Domino's",
                "dietary_tag": diet_tag,
                "portion_str": f"{serving_size}g" if serving_size > 0 else "1 serving",
                "portion_g": serving_size or 100.0,
                "energy_kcal": cal,
                "protein_g": prot,
                "carb_g": carb,
                "fat_g": fat,
                "sugar_g": sug,
                "sodium_mg": sod,
                "fibre_g": 0.0,
            })

    # 3. KFC
    kfc_path = FAST_FOOD_DIR / "KFC_Nutrition_Allergen_Data.xlsx"
    if kfc_path.exists():
        df = pd.read_excel(kfc_path, sheet_name="Nutrition Data")
        for idx, r in df.iterrows():
            prod = clean_str(r.get("Product"))
            if not prod:
                continue
            section = clean_str(r.get("Section"), "Hot & Crispy")
            serv_wt = clean_num(r.get("Avg Portion Weight (g)"))
            cal = clean_num(r.get("Energy (kcal/serve)"))
            carb = clean_num(r.get("Carbohydrate (g/serve)"))
            prot = clean_num(r.get("Protein (g/serve)"))
            fat = clean_num(r.get("Total Fat (g/serve)"))
            sod = clean_num(r.get("Sodium (mg/serve)"))
            sug = clean_num(r.get("Sugar (g/serve)"))
            
            p_low = prod.lower()
            s_low = section.lower()
            if "veg" in p_low or "veg" in s_low:
                diet_tag = "Vegetarian"
            elif any(k in p_low for k in ["chicken", "wing", "leg", "strip", "popcorn", "zinger", "chizza", "roll", "hc", "hw", "mutton", "meat", "fish"]) or any(k in s_low for k in ["hot & crispy", "smoky & grilled", "strips", "wings", "leg piece", "zinger"]):
                diet_tag = "Non-Vegetarian"
            elif any(k in s_low for k in ["french fries", "krushers", "retail products", "dips/sauces", "sides"]):
                diet_tag = "Vegetarian"
            else:
                diet_tag = "Non-Vegetarian"
                
            cat = "Beverage" if "pepsi" in p_low or "krushers" in s_low or "retail products" in s_low else ("Snack" if "fries" in p_low or "dip" in p_low or "dessert" in s_low else "Lunch/Dinner")
            
            all_items.append({
                "brand": "KFC",
                "recipe_code": f"FF_KFC_{len(all_items)+1:04d}",
                "recipe_name": prod,
                "sub_category": section,
                "category": cat,
                "cuisine": "KFC",
                "dietary_tag": diet_tag,
                "portion_str": f"{serv_wt}g" if serv_wt > 0 else "1 serve",
                "portion_g": serv_wt or 120.0,
                "energy_kcal": cal,
                "protein_g": prot,
                "carb_g": carb,
                "fat_g": fat,
                "sugar_g": sug,
                "sodium_mg": sod,
                "fibre_g": 0.0,
            })

    # 4. MCDONALDS
    mcd_path = FAST_FOOD_DIR / "McDonalds_Nutrition_Data-gpt.xlsx"
    if mcd_path.exists():
        df = pd.read_excel(mcd_path, sheet_name="Nutrition Data")
        for idx, r in df.iterrows():
            item = clean_str(r.get("Item"))
            if not item:
                continue
            cat_raw = clean_str(r.get("Category"), "Burgers")
            serv_sz = clean_str(r.get("Serving Size"))
            diet_raw = clean_str(r.get("Dietary Type"), "Vegetarian")
            cal = clean_num(r.get("Energy (kcal)"))
            prot = clean_num(r.get("Protein (g)"))
            fat = clean_num(r.get("Total Fat (g)"))
            carb = clean_num(r.get("Carbohydrates (g)"))
            sug = clean_num(r.get("Sugar (g)"))
            fib = clean_num(r.get("Dietary Fiber (g)"))
            sod = clean_num(r.get("Sodium (mg)"))
            
            diet_tag = "Non-Vegetarian" if "non" in diet_raw.lower() or "chicken" in item.lower() or "fish" in item.lower() or "egg" in item.lower() else "Vegetarian"
            if "breakfast" in cat_raw.lower():
                cat = "Breakfast"
            elif "beverage" in cat_raw.lower() or "shake" in cat_raw.lower() or "coffee" in cat_raw.lower() or "mccafe" in cat_raw.lower():
                cat = "Beverage"
            elif "dessert" in cat_raw.lower() or "sides" in cat_raw.lower() or "fries" in cat_raw.lower():
                cat = "Snack"
            else:
                cat = "Lunch/Dinner"
                
            all_items.append({
                "brand": "McDonald's",
                "recipe_code": f"FF_MCD_{len(all_items)+1:04d}",
                "recipe_name": item,
                "sub_category": cat_raw,
                "category": cat,
                "cuisine": "McDonald's",
                "dietary_tag": diet_tag,
                "portion_str": f"{serv_sz}g" if serv_sz and serv_sz.isdigit() else (serv_sz or "1 serve"),
                "portion_g": clean_num(serv_sz, 100.0),
                "energy_kcal": cal,
                "protein_g": prot,
                "carb_g": carb,
                "fat_g": fat,
                "sugar_g": sug,
                "sodium_mg": sod,
                "fibre_g": fib,
            })

    # 5. PIZZA HUT
    ph_path = FAST_FOOD_DIR / "Pizza_Hut_Nutrition_Dietary_Data.xlsx"
    if ph_path.exists():
        df = pd.read_excel(ph_path, sheet_name="Nutrition Data")
        for idx, r in df.iterrows():
            prod = clean_str(r.get("Product"))
            if not prod:
                continue
            section = clean_str(r.get("Section"), "Pan Pizza")
            diet_raw = clean_str(r.get("Dietary Type"), "Vegetarian")
            vegan_raw = clean_str(r.get("Vegan"), "")
            jain_raw = clean_str(r.get("Jain"), "")
            wt = clean_num(r.get("Net Weight (g)"))
            cal = clean_num(r.get("Energy (kcal)"))
            carb = clean_num(r.get("Carbohydrate (g)"))
            prot = clean_num(r.get("Protein (g)"))
            fib = clean_num(r.get("Dietary Fibre (g)"))
            sug = clean_num(r.get("Total Sugar (g)"))
            fat = clean_num(r.get("Total Fat (g)"))
            sod = clean_num(r.get("Sodium (mg)"))
            
            if "non" in diet_raw.lower():
                diet_tag = "Non-Vegetarian"
            elif "jain" in jain_raw.lower() or "yes" in jain_raw.lower():
                diet_tag = "Jain"
            elif "vegan" in vegan_raw.lower() or "yes" in vegan_raw.lower():
                diet_tag = "Vegan"
            else:
                diet_tag = "Vegetarian"
                
            cat = "Snack" if "side" in section.lower() or "dessert" in section.lower() or "garlic bread" in prod.lower() else ("Beverage" if "beverage" in section.lower() or "drink" in prod.lower() else "Lunch/Dinner")
            
            all_items.append({
                "brand": "Pizza Hut",
                "recipe_code": f"FF_PH_{len(all_items)+1:04d}",
                "recipe_name": prod,
                "sub_category": section,
                "category": cat,
                "cuisine": "Pizza Hut",
                "dietary_tag": diet_tag,
                "portion_str": f"{wt}g" if wt > 0 else "1 serve",
                "portion_g": wt or 150.0,
                "energy_kcal": cal,
                "protein_g": prot,
                "carb_g": carb,
                "fat_g": fat,
                "sugar_g": sug,
                "sodium_mg": sod,
                "fibre_g": fib,
            })

    # 6. STARBUCKS
    sb_path = FAST_FOOD_DIR / "Starbucks_Beverage_Nutrition_Data.xlsx"
    if sb_path.exists():
        df = pd.read_excel(sb_path, sheet_name="Nutrition Data")
        for idx, r in df.iterrows():
            item = clean_str(r.get("Menu Item"))
            if not item:
                continue
            cat_raw = clean_str(r.get("Category"), "Coffee & Beverages")
            size = clean_str(r.get("Size"), "Grande")
            diet_raw = clean_str(r.get("Dietary Type"), "Vegetarian")
            cal = clean_num(r.get("Energy (kcal)"))
            fat = clean_num(r.get("Fat (g)"))
            carb = clean_num(r.get("Carbohydrates (g)"))
            sug = clean_num(r.get("Sugar (g)"))
            fib = clean_num(r.get("Fibre (g)"))
            prot = clean_num(r.get("Protein (g)"))
            salt = clean_num(r.get("Salt (g)"))
            sod = salt * 400.0  # ~400mg sodium per 1g salt
            
            if "jain" in diet_raw.lower():
                diet_tag = "Jain"
            elif "vegan" in diet_raw.lower():
                diet_tag = "Vegan"
            elif "non" in diet_raw.lower():
                diet_tag = "Non-Vegetarian"
            else:
                diet_tag = "Vegetarian"
                
            dish_name = f"{item} ({size})" if size else item
            all_items.append({
                "brand": "Starbucks",
                "recipe_code": f"FF_SBX_{len(all_items)+1:04d}",
                "recipe_name": dish_name,
                "sub_category": cat_raw,
                "category": "Beverage",
                "cuisine": "Starbucks",
                "dietary_tag": diet_tag,
                "portion_str": size or "1 cup",
                "portion_g": 354.0 if "tall" in size.lower() else (473.0 if "grande" in size.lower() else (591.0 if "venti" in size.lower() else 236.0)),
                "energy_kcal": cal,
                "protein_g": prot,
                "carb_g": carb,
                "fat_g": fat,
                "sugar_g": sug,
                "sodium_mg": sod,
                "fibre_g": fib,
            })

    # 7. SUBWAY
    sub_path = FAST_FOOD_DIR / "Subway_Nutrition_Dietary_Data.xlsx"
    if sub_path.exists():
        df = pd.read_excel(sub_path, sheet_name="Nutrition Data")
        for idx, r in df.iterrows():
            prod = clean_str(r.get("Product"))
            if not prod:
                continue
            cat_raw = clean_str(r.get("Category"), "Sub / Sandwich")
            qty = clean_num(r.get("Serving Qty (g)"))
            cal = clean_num(r.get("Calories (kcal)"))
            fat = clean_num(r.get("Total Fat (g)"))
            carb = clean_num(r.get("Carbohydrates (g)"))
            sug = clean_num(r.get("Sugars (g)"))
            prot = clean_num(r.get("Protein (g)"))
            sod = clean_num(r.get("Sodium (mg)"))
            diet_raw = clean_str(r.get("Dietary Type"), "Veg")
            jain_raw = clean_str(r.get("Jain"), "")
            vegan_raw = clean_str(r.get("Vegan"), "")
            
            if "non" in diet_raw.lower() or "chicken" in prod.lower() or "tuna" in prod.lower() or "turkey" in prod.lower() or "egg" in prod.lower() or "meat" in prod.lower():
                diet_tag = "Non-Vegetarian"
            elif "jain" in jain_raw.lower() or "yes" in jain_raw.lower():
                diet_tag = "Jain"
            elif "vegan" in vegan_raw.lower() or "yes" in vegan_raw.lower():
                diet_tag = "Vegan"
            else:
                diet_tag = "Vegetarian"
                
            cat = "Lunch/Dinner"
            if "cookie" in prod.lower() or "toastie" in prod.lower() or "sides" in cat_raw.lower() or "crisps" in prod.lower():
                cat = "Snack"
            elif "drink" in prod.lower() or "coffee" in prod.lower() or "tea" in prod.lower():
                cat = "Beverage"
                
            all_items.append({
                "brand": "Subway",
                "recipe_code": f"FF_SUB_{len(all_items)+1:04d}",
                "recipe_name": prod,
                "sub_category": cat_raw if cat_raw != "Unknown" else "Sub / Wrap",
                "category": cat,
                "cuisine": "Subway",
                "dietary_tag": diet_tag,
                "portion_str": f"{qty}g" if qty > 0 else "1 sub",
                "portion_g": qty or 200.0,
                "energy_kcal": cal,
                "protein_g": prot,
                "carb_g": carb,
                "fat_g": fat,
                "sugar_g": sug,
                "sodium_mg": sod,
                "fibre_g": 0.0,
            })

    # 8. TACO BELL
    tb_path = FAST_FOOD_DIR / "Taco_Bell_Nutrition_Dietary_Data.xlsx"
    if tb_path.exists():
        df = pd.read_excel(tb_path, sheet_name="Nutrition Data")
        for idx, r in df.iterrows():
            prod = clean_str(r.get("Product"))
            if not prod:
                continue
            cat_raw = clean_str(r.get("Category"), "Tacos & Burritos")
            serv_sz = clean_str(r.get("Serving Size"))
            cal = clean_num(r.get("Energy (kcal)"))
            prot = clean_num(r.get("Protein (g)"))
            carb = clean_num(r.get("Carbohydrate (g)"))
            sug = clean_num(r.get("Total Sugar (g)"))
            fat = clean_num(r.get("Fat (g)"))
            sod = clean_num(r.get("Sodium (mg)"))
            diet_raw = clean_str(r.get("Dietary Type"), "Vegetarian")
            
            diet_tag = "Non-Vegetarian" if "non" in diet_raw.lower() or "chicken" in prod.lower() or "beef" in prod.lower() or "fish" in prod.lower() else "Vegetarian"
            cat = "Beverage" if "beverage" in cat_raw.lower() or "twist" in prod.lower() or "lemon-ade" in prod.lower() else ("Snack" if "nachos" in prod.lower() or "dessert" in cat_raw.lower() or "sides" in cat_raw.lower() else "Lunch/Dinner")
            
            all_items.append({
                "brand": "Taco Bell",
                "recipe_code": f"FF_TB_{len(all_items)+1:04d}",
                "recipe_name": prod,
                "sub_category": cat_raw,
                "category": cat,
                "cuisine": "Taco Bell",
                "dietary_tag": diet_tag,
                "portion_str": serv_sz or "1 serve",
                "portion_g": clean_num(serv_sz, 150.0),
                "energy_kcal": cal,
                "protein_g": prot,
                "carb_g": carb,
                "fat_g": fat,
                "sugar_g": sug,
                "sodium_mg": sod,
                "fibre_g": 0.0,
            })

    return all_items

def ingest_to_database(items):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print(f"Total parsed items to ingest: {len(items)}")
    
    # Check existing fast food codes and delete them to avoid duplication if re-run
    c.execute("DELETE FROM recipe_nutrition WHERE recipe_code LIKE 'FF_%'")
    c.execute("DELETE FROM servings WHERE recipe_code LIKE 'FF_%'")
    c.execute("DELETE FROM recipes WHERE recipe_code LIKE 'FF_%'")
    conn.commit()
    print("Cleared any existing fast food recipes (FF_%)")
    
    recipe_rows = []
    nutrition_rows = []
    serving_rows = []
    
    for it in items:
        code = it["recipe_code"]
        name = it["recipe_name"]
        cat = it["category"]
        cuisine = it["cuisine"]
        brand = it["brand"]
        diet_tag = it["dietary_tag"]
        subcat = it["sub_category"]
        
        recipe_rows.append((
            code,
            name,
            cat,
            cuisine,
            brand,
            diet_tag,
            "Easy",
            10,
            f"Prepared fast food item from {brand} ({subcat}). Portion: {it['portion_str']}.",
            brand
        ))
        
        cal = it["energy_kcal"]
        prot = it["protein_g"]
        carb = it["carb_g"]
        fat = it["fat_g"]
        sug = it["sugar_g"]
        sod = it["sodium_mg"]
        fib = it["fibre_g"]
        
        nutrition_rows.append((
            code,
            cal,
            carb,
            prot,
            fat,
            sug,
            fib,
            sod,
            cal,
            carb,
            prot,
            fat,
            sug,
            fib,
            sod
        ))
        
        serving_rows.append((
            code,
            1.0,
            it["portion_g"],
            it["portion_str"]
        ))
    
    c.executemany("""
    INSERT INTO recipes (recipe_code, recipe_name, category, cuisine, brand, dietary_tag, difficulty, cooking_time_minutes, instructions, primarysource)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, recipe_rows)
    conn.commit()

    # Fetch assigned recipe IDs
    c.execute("SELECT id, recipe_code FROM recipes WHERE recipe_code LIKE 'FF_%'")
    code_to_id = {row[1]: row[0] for row in c.fetchall()}

    nutrition_rows_with_id = []
    for r in nutrition_rows:
        code = r[0]
        rec_id = code_to_id.get(code)
        if rec_id:
            nutrition_rows_with_id.append((rec_id, *r))

    c.executemany("""
    INSERT INTO recipe_nutrition (
        recipe_id, recipe_code, energy_kcal, carb_g, protein_g, fat_g, freesugar_g, fibre_g, sodium_mg,
        unit_serving_energy_kcal, unit_serving_carb_g, unit_serving_protein_g, unit_serving_fat_g,
        unit_serving_freesugar_g, unit_serving_fibre_g, unit_serving_sodium_mg
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, nutrition_rows_with_id)
    
    c.executemany("""
    INSERT INTO servings (recipe_code, no_of_servings, size_of_servings, servings_unit)
    VALUES (?, ?, ?, ?)
    """, serving_rows)
    
    # Also populate dietary_tag for existing non-fast-food recipes if not set!
    print("Backfilling dietary tags for existing regional recipes...")
    c.execute("""
    UPDATE recipes SET dietary_tag = 'Vegetarian' 
    WHERE dietary_tag IS NULL AND (primarysource = 'Vegetarian' OR cuisine IN ('Gujarati / Kathiyawadi', 'Rajasthani', 'South Indian') OR recipe_name LIKE '%paneer%' OR recipe_name LIKE '%dal%' OR recipe_name LIKE '%khichdi%' OR recipe_name LIKE '%sabzi%' OR recipe_name LIKE '%roti%' OR recipe_name LIKE '%dosa%' OR recipe_name LIKE '%idli%')
    """)
    c.execute("""
    UPDATE recipes SET dietary_tag = 'Non-Vegetarian' 
    WHERE dietary_tag IS NULL AND (primarysource = 'Non-Vegetarian' OR recipe_name LIKE '%chicken%' OR recipe_name LIKE '%mutton%' OR recipe_name LIKE '%fish%' OR recipe_name LIKE '%egg%' OR recipe_name LIKE '%prawn%' OR recipe_name LIKE '%pork%' OR recipe_name LIKE '%beef%' OR recipe_name LIKE '%keema%')
    """)
    c.execute("UPDATE recipes SET dietary_tag = 'Vegetarian' WHERE dietary_tag IS NULL")
    
    conn.commit()
    
    c.execute("SELECT COUNT(*) FROM recipes")
    total_recipes = c.fetchone()[0]
    c.execute("SELECT brand, COUNT(*), SUM(CASE WHEN dietary_tag = 'Vegetarian' THEN 1 ELSE 0 END), SUM(CASE WHEN dietary_tag = 'Non-Vegetarian' THEN 1 ELSE 0 END) FROM recipes WHERE brand IS NOT NULL GROUP BY brand")
    brand_stats = c.fetchall()
    
    print("\n" + "="*60)
    print(f"INGESTION SUCCESSFUL! Total recipes in DB: {total_recipes}")
    print("="*60)
    print(f"{'Brand':15s} | {'Total':6s} | {'Veg':6s} | {'Non-Veg':8s}")
    print("-" * 45)
    for b, tot, veg, nv in brand_stats:
        print(f"{b:15s} | {tot:6d} | {veg:6d} | {nv:8d}")
    print("="*60)
    
    conn.close()

if __name__ == "__main__":
    items = parse_fast_food_datasets()
    ingest_to_database(items)
