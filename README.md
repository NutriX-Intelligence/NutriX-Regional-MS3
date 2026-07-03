# NutriX - AI Diet Planner & Recipe Intelligence

NutriX is a premium, production-grade web application for smart nutrition tracking, recipe search, homely meal calculations, and personalized diet plan optimizations. It combines custom heuristics, fuzzy ingredient matching, linear programming constraint solvers, and robust fallback lookups into a clean, modern startup dashboard.

---

## 🚀 Quick Start & Installation

### 1. Prerequisites
Ensure you have the following installed:
*   Python 3.10 or higher
*   Git

### 2. Setup Virtual Environment
Clone this repository (or copy the project files), open your terminal in the project root, and execute:
```bash
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Build & Seed the Nutrition Database
NutriX stores all standardized food metrics, portion conversions, recipe nutrition lists, and exclusion rules in a local SQLite database. Build and seed it by running:
```bash
# Build the master schema and load initial datasets
python scripts/build_nutrition_master_db.py

# Seed accuracy upgrades (Jain/Vegan rules, drinks/mocktails, homely meals supplement)
python scripts/seed_custom_data.py
```

### 4. Run the Server
Start the FastAPI server locally:
```bash
python run.py --host 0.0.0.0 --port 8080 --reload
```
*   **Web Dashboard:** [http://localhost:8080/](http://localhost:8080/)
*   **API Documentation:** [http://localhost:8080/docs](http://localhost:8080/docs)

---

## 🛠️ Core Feature Highlights & How to Test

### 1. Barcode Scan & Search Fallback
*   **OFF Lookup:** Scan or input a barcode (e.g., `8901719117972` for Paper Boat Coconut Water).
*   **Search Scraper Backup:** If a product is not listed on Open Food Facts (404), the backend automatically scrapes DuckDuckGo HTML search results, extracts the product name, matches it fuzzy-style to local database nutrients, and returns a verified product card.
*   **Price-Matched Alternatives:** Scanned products automatically show healthier snack/drink alternatives. Recommends budget-friendly choices (like spiced buttermilk) for low-cost scans and premium bars for premium scans, with working Amazon redirect links.

### 2. Recipe Intelligence (Ingredient Matcher)
*   **Synonym & Stem Matching:** Search recipes by listing ingredients in your fridge (e.g., `"Ginger, Lemon"`). The matcher normalizes dialect differences (like `"adrak"` or `"nimbu"`) and scores matches.
*   **Smart Scoring:** Recipes are sorted based on matching coverage and nutritional density.

### 3. Simplified Diet Planner
*   Configure your targets on the profile tab.
*   Select your preference priority: **Balanced**, **High Protein**, **Low Carb**, or **High Fiber**.
*   The solver engine (using Google OR-Tools) will dynamically compile a daily 4-slot meal plan matching your macro goals.

### 4. Homely Meals Builder
*   Create homemade dishes (e.g. "Paneer Tikka") by typing raw ingredients and portion units (e.g. `"1 katori dal"`, `"1 tbsp ghee"`). The builder standardizes these to gram weights and auto-calculates total calories.

---

## 🧪 Running Unit Tests
A full test suite of 27 unit tests is included. Run it to verify system integrity:
```bash
pytest -v
```
