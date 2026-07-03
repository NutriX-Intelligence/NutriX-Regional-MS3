from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "Dataset" / "raw"
print("Dataset Path:", DATA_DIR)
print("Exists:", DATA_DIR.exists())

files = [
    "INDB.xlsx",
    "Indian_Food_Nutrition_Processed.csv",
    "indian_food_nutrition_dataset.csv",
    "recipes.xlsx",
    "recipe_links.xlsx",
    "recipes_names.xlsx",
    "recipes_servingsize.xlsx"
]

for file in files:
    path = DATA_DIR / file

    print("\n" + "="*80)
    print(f"FILE: {file}")

    try:
        if file.endswith(".csv"):
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)

        print(f"Rows: {len(df)}")
        print(f"Columns: {len(df.columns)}")

        print("\nCOLUMN NAMES:")
        print(df.columns.tolist())

        print("\nSAMPLE:")
        print(df.head(3))

    except Exception as e:
        print("ERROR:", e)