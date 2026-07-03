"""
Migration script to add new columns to the recipes table
for the Recipe Intelligence Engine.

Adds: instructions, cooking_time_minutes, cuisine, difficulty
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "output" / "nutrix.db"

def migrate():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}. Skipping migration.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check existing columns
    cursor.execute("PRAGMA table_info(recipes)")
    columns = {row[1] for row in cursor.fetchall()}
    print(f"Existing columns: {columns}")

    migrations = [
        ("instructions", "TEXT"),
        ("cooking_time_minutes", "INTEGER"),
        ("cuisine", "TEXT"),
        ("difficulty", "TEXT"),
    ]

    for col_name, col_type in migrations:
        if col_name not in columns:
            print(f"Adding column '{col_name}' ({col_type})...")
            cursor.execute(f"ALTER TABLE recipes ADD COLUMN {col_name} {col_type}")
        else:
            print(f"Column '{col_name}' already exists.")

    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
