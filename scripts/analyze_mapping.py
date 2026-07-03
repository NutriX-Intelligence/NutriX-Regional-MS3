import pandas as pd

names = pd.read_excel("Dataset/raw/recipes_names.xlsx")

def categorize_recipe(name):
    name_lower = name.lower()
    
    # Check breakfast keywords
    breakfast_kws = [
        "sandwich", "toast", "pancake", "egg", "omelet", "paratha", "poha", "upma", 
        "idli", "dosa", "oats", "porridge", "muesli", "cereal", "dalia", "bhundia",
        "bhurji", "thepla", "cheela", "chilla", "puri", "poori", "chapati", "parotta",
        "appe", "dhokla", "khandvi", "uttapam"
    ]
    if any(kw in name_lower for kw in breakfast_kws):
        # Eggs can be in breakfast or dinner, but let's look at eggs specifically
        # Let's say if it contains curry or gravy, it's lunch/dinner
        if any(kw in name_lower for kw in ["curry", "gravy", "masala"]):
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
        "jalebi", "ice cream", "custard", "compote", "sherbet", "jam", "jelly"
    ]
    if any(kw in name_lower for kw in snack_kws):
        return "Snack"
        
    # Default is Lunch/Dinner
    return "Lunch/Dinner"

names['category'] = names['recipe_name'].apply(categorize_recipe)
print("Heuristic categorization distribution:")
print(names['category'].value_counts())

print("\nSample Breakfast recipes:")
print(names[names['category'] == 'Breakfast']['recipe_name'].head(15))

print("\nSample Snack recipes:")
print(names[names['category'] == 'Snack']['recipe_name'].head(15))

print("\nSample Lunch/Dinner recipes:")
print(names[names['category'] == 'Lunch/Dinner']['recipe_name'].head(15))
