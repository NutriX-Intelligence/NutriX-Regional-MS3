import sqlite3

def delete_target_homely_meals():
    conn = sqlite3.connect('output/nutrition_master.db')
    cur = conn.cursor()
    
    # 1. Identify target meal IDs
    cur.execute("""
        SELECT id, name FROM homely_meals 
        WHERE name LIKE '%Secret%Khichdi%' 
           OR name LIKE '%Secret Family Khichdi%'
           OR name LIKE '%Maru%Chatni%' 
           OR name LIKE '%Ghee%Sabzi%' 
           OR name LIKE '%Ghee Sabzi%'
           OR name LIKE '%Community Special Poha%'
    """)
    records = cur.fetchall()
    
    if not records:
        print("No target meals found in database.")
        conn.close()
        return
    
    meal_ids = [r[0] for r in records]
    print(f"Found {len(records)} meal records to delete:")
    for r in records:
        print(f"  ID: {r[0]}, Name: '{r[1]}'")
        
    id_placeholders = ','.join(['?'] * len(meal_ids))
    
    # 2. Delete related records in child tables
    cur.execute(f"DELETE FROM homely_meal_ingredients WHERE meal_id IN ({id_placeholders})", meal_ids)
    print(f"Deleted {cur.rowcount} rows from homely_meal_ingredients")
    
    cur.execute(f"DELETE FROM homely_meal_nutrition WHERE meal_id IN ({id_placeholders})", meal_ids)
    print(f"Deleted {cur.rowcount} rows from homely_meal_nutrition")
    
    cur.execute(f"DELETE FROM homely_meal_versions WHERE meal_id IN ({id_placeholders})", meal_ids)
    print(f"Deleted {cur.rowcount} rows from homely_meal_versions")
    
    cur.execute(f"DELETE FROM homely_meal_reviews WHERE meal_id IN ({id_placeholders})", meal_ids)
    print(f"Deleted {cur.rowcount} rows from homely_meal_reviews")
    
    cur.execute(f"DELETE FROM homely_meal_tags WHERE meal_id IN ({id_placeholders})", meal_ids)
    print(f"Deleted {cur.rowcount} rows from homely_meal_tags")
    
    # 3. Delete from homely_meals table
    cur.execute(f"DELETE FROM homely_meals WHERE id IN ({id_placeholders})", meal_ids)
    print(f"Deleted {cur.rowcount} rows from homely_meals")
    
    conn.commit()
    conn.close()
    print("Cleanup completed successfully.")

if __name__ == '__main__':
    delete_target_homely_meals()
