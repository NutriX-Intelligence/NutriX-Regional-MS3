# NutriX — Complete Project Architecture

---

## 1. High-Level System Architecture

```mermaid
graph TD
    subgraph CLIENT["Client Layer"]
        SPA["Web Dashboard SPA<br/>Vanilla JS + CSS + Chart.js"]
        MOB["Mobile Web Client<br/>ngrok HTTPS Tunnel"]
    end

    subgraph GATEWAY["API & Security Layer"]
        API["FastAPI + Uvicorn<br/>app/main.py"]
        JWT["JWT Auth Guard<br/>auth_service.py"]
        SCHEMA["Pydantic V2 Schemas<br/>schemas.py + schemas_recipes.py"]
    end

    subgraph ENGINES["Domain Intelligence Engines"]
        NE["Nutrition Engine"]
        BC["Barcode Service"]
        HM["Homely Meals Engine"]
        IM["Ingredient Matcher"]
        RR["Recipe Ranker"]
        OE["Optimization Engine"]
        AP["Adaptive Planner"]
        AE["Analytics Engine"]
        RE["Recommendation Engine"]
        CE["Classification Engine"]
        HS["Health Scorer"]
        OCR["OCR Engine"]
        EE["Explanation Engine"]
        ML["ML Extension"]
    end

    subgraph DATA["Data & Storage Layer"]
        DB[("SQLite / PostgreSQL<br/>nutrition_master.db")]
        IDX["In-Memory Fuzzy Index<br/>RapidFuzz + Synonym Dict"]
    end

    subgraph EXTERNAL["External APIs & Fallbacks"]
        OFF["Open Food Facts API"]
        DDG["DuckDuckGo Scraper"]
        GEM["Google Gemini AI"]
        GAUTH["Google OAuth 2.0"]
    end

    SPA --> API
    MOB --> API
    API --> JWT
    JWT --> SCHEMA
    SCHEMA --> ENGINES

    NE --> DB
    HM --> DB
    RR --> DB
    OE --> DB
    AP --> DB
    AE --> DB
    RE --> DB
    IM --> IDX

    BC --> OFF
    BC -->|404 Fallback| DDG
    BC -->|AI Backup| GEM
    OCR --> GEM
    JWT --> GAUTH
```

---

## 2. Tech Stack

```mermaid
graph LR
    subgraph BACKEND["Backend"]
        PY["Python 3.10+"]
        FA["FastAPI"]
        UV["Uvicorn ASGI"]
        SA["SQLAlchemy 2.0 ORM"]
        PD["Pydantic V2"]
    end

    subgraph AI_ML["AI & ML"]
        ORT["Google OR-Tools<br/>Linear Programming Solver"]
        RF["RapidFuzz<br/>Fuzzy String Matching"]
        SK["scikit-learn<br/>ML Pipelines"]
        XG["XGBoost<br/>Gradient Boosting"]
        GAPI["Google Gemini API<br/>Vision + NLP"]
    end

    subgraph FRONTEND["Frontend"]
        HTML["HTML5 Semantic"]
        CSS["Vanilla CSS<br/>Glassmorphism + Dark Mode"]
        JS["Vanilla JavaScript ES6+"]
        CJ["Chart.js<br/>Analytics Graphs"]
    end

    subgraph INFRA["Infrastructure"]
        SQ["SQLite / PostgreSQL"]
        NG["ngrok<br/>HTTPS Tunnel"]
        GH["GitHub<br/>Version Control"]
        PT["pytest<br/>27 Unit Tests"]
    end

    subgraph LIBS["Supporting Libraries"]
        HTTPX["httpx<br/>Async HTTP Client"]
        PIL["Pillow<br/>Image Processing"]
        PANDAS["pandas + openpyxl<br/>Dataset ETL"]
        PASS["passlib + bcrypt<br/>Password Hashing"]
        PYJWT["PyJWT<br/>Token Encoding"]
    end
```

---

## 3. All 14 Domain Engine Modules

```mermaid
graph TD
    subgraph SCAN["Barcode & Product Lookup"]
        E1["barcode_service.py<br/>11.6 KB<br/>Multi-tier barcode resolution:<br/>OFF API -> DDG Scraper -> DB Fuzzy -> Gemini AI"]
        E2["ocr_engine.py<br/>6.5 KB<br/>Nutrition label image extraction<br/>via Gemini Vision API"]
    end

    subgraph RECIPE["Recipe & Ingredient Intelligence"]
        E3["ingredient_matcher.py<br/>9.9 KB<br/>Regional dialect normalization<br/>adrak=ginger, nimbu=lemon<br/>Fuzzy set intersection matching"]
        E4["recipe_ranker.py<br/>3.9 KB<br/>Score recipes by ingredient coverage<br/>macro fit and dietary preference"]
        E5["nutrition_engine.py<br/>4.0 KB<br/>Core nutrient lookup and<br/>per-100g standardization"]
    end

    subgraph MEALS["Meal Planning & Optimization"]
        E6["homely_meals_engine.py<br/>9.6 KB<br/>Home cooking portion builder<br/>Unit conversion + cooking fat adjustment"]
        E7["optimization_engine.py<br/>14.0 KB<br/>Google OR-Tools LP solver<br/>4-meal daily plan generation"]
        E8["adaptive_planner.py<br/>7.1 KB<br/>Moving average trend analysis<br/>Dynamic target adjustment suggestions"]
    end

    subgraph SCORING["Scoring & Classification"]
        E9["health_scorer.py<br/>6.2 KB<br/>Composite 0-100 health score<br/>Sugar, sodium, fiber, processing markers"]
        E10["classification_engine.py<br/>4.4 KB<br/>NOVA processing levels 1-4<br/>Jain, Vegan, Gluten-Free compliance"]
    end

    subgraph ANALYTICS["Analytics & Recommendations"]
        E11["analytics_engine.py<br/>5.0 KB<br/>Daily, weekly, monthly aggregations<br/>Weight logs and goal compliance"]
        E12["recommendation_engine.py<br/>12.8 KB<br/>Budget-aware healthier alternatives<br/>Price-matched Amazon redirect links"]
        E13["explanation_engine.py<br/>5.5 KB<br/>Explainable AI reasoning<br/>Why a meal or substitute was recommended"]
        E14["ml_extension.py<br/>8.1 KB<br/>scikit-learn + XGBoost pipelines<br/>Predictive nutrition models"]
    end
```

---

## 4. Barcode Multi-Tier Fallback Sequence

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant SVC as Barcode Service
    participant OFF as Open Food Facts API
    participant DDG as DuckDuckGo Scraper
    participant DB as Master Database
    participant AI as Gemini AI API

    User->>SVC: Input barcode 8901719117972
    SVC->>OFF: GET product by barcode
    alt Product found
        OFF-->>SVC: 200 OK with nutrients
    else 404 Not Found
        SVC->>DDG: Scrape product title from search
        DDG-->>SVC: Extracted product name
        SVC->>DB: Fuzzy match name in local DB
        alt DB match found
            DB-->>SVC: Standardized nutrients
        else No DB match
            SVC->>AI: Estimate nutrients via Gemini
            AI-->>SVC: AI-estimated nutrients
        end
    end
    SVC->>SVC: Compute health score 0-100
    SVC->>SVC: Generate budget alternatives
    SVC-->>User: Product card with alternatives
```

---

## 5. Homely Meal Builder Pipeline

```mermaid
flowchart LR
    A["User Input<br/>2 katori dal + 1 tbsp ghee"] --> B["Ingredient Parser"]
    B --> C["Unit Normalizer<br/>Units.xlsx mapping"]
    C --> D["Gram Weight Converter<br/>katori=180g, tbsp=14g"]
    D --> E["Cooking Fat Absorber<br/>Oil retention % logic"]
    E --> F["Macro Calculator<br/>per-100g nutrient lookup"]
    F --> G["Total Nutrition Card<br/>Kcal + Protein + Carbs + Fat"]
    G --> H["Log to Meal History"]
```

---

## 6. Diet Plan Optimization Solver

```mermaid
flowchart TD
    INPUT["User Inputs"] --> CALS["Calorie Target<br/>e.g. 2000 kcal"]
    INPUT --> PREF["Priority Mode<br/>Balanced / High Protein<br/>Low Carb / High Fiber"]
    INPUT --> EXCL["Exclusion Rules<br/>Vegan / Jain / Allergies"]

    DB[("Recipe Database<br/>with per-serving macros")] --> SOLVER
    CALS --> SOLVER
    PREF --> SOLVER
    EXCL --> SOLVER

    SOLVER["Google OR-Tools<br/>Linear Programming Solver<br/>Minimize deviation from targets"] --> PLAN

    PLAN["Optimized 4-Slot Plan"]
    PLAN --> BF["Breakfast"]
    PLAN --> LN["Lunch"]
    PLAN --> SN["Snacks"]
    PLAN --> DN["Dinner"]
```

---

## 7. Datasets & Knowledge Base Inventory

```mermaid
graph TD
    subgraph CORE["Core Nutrition Datasets (Included in Git)"]
        D1["INDB.xlsx<br/>1.0 MB<br/>Indian Nutrient Database<br/>Comprehensive Indian food composition"]
        D2["Indian_Food_DF.csv<br/>174 KB<br/>Indian dishes with ingredients"]
        D3["Indian_Food_Nutrition_Processed.csv<br/>88 KB<br/>Processed Indian food nutrients"]
        D4["indian_food_nutrition_dataset.csv<br/>6 KB<br/>Supplementary Indian nutrients"]
        D5["recipes.xlsx<br/>714 KB<br/>Recipe database with macros"]
        D6["recipes_names.xlsx<br/>78 KB<br/>Recipe name index"]
        D7["recipes_servingsize.xlsx<br/>99 KB<br/>Serving size mappings"]
        D8["Units.xlsx<br/>28 KB<br/>Portion unit to gram conversions"]
        D9["recipe_links.xlsx<br/>17 KB<br/>Recipe source URLs"]
    end

    subgraph FDC["USDA FoodData Central (Included in Git)"]
        D10["food.csv<br/>Foundation food items"]
        D11["food_nutrient.csv<br/>Nutrient values per food"]
        D12["food_portion.csv<br/>Portion weight mappings"]
        D13["nutrient.csv<br/>Nutrient definitions"]
        D14["food_category.csv<br/>Food group classifications"]
    end

    subgraph INTL["International Food Tables (Included in Git)"]
        D15["UK_fct.xlsx<br/>52 KB<br/>UK Food Composition Table"]
        D16["US_fct.xlsx<br/>132 KB<br/>US Food Composition Table"]
        D17["USDA_nrf.xlsx<br/>42 KB<br/>USDA Nutrient Reference"]
    end

    subgraph LARGE["Large Raw Datasets (Git-Ignored, Local Only)"]
        D18["RecipeNLG_dataset.csv<br/>2.3 GB<br/>2.2M recipes with NER"]
        D19["RAW_recipes.csv<br/>295 MB<br/>Food.com raw recipes"]
        D20["RAW_interactions.csv<br/>349 MB<br/>Food.com user interactions"]
        D21["PP_recipes.csv<br/>205 MB<br/>Preprocessed recipes"]
        D22["epi_r.csv<br/>55 MB<br/>Epicurious recipe ratings"]
        D23["full_format_recipes.json<br/>35 MB<br/>Full recipe JSON corpus"]
    end
```

---

## 8. Database Schema (ER Diagram)

```mermaid
erDiagram
    USERS {
        int id PK
        string email UK
        string hashed_password
        string display_name
        string google_id
        string picture_url
        float height_cm
        float weight_kg
        int age
        string sex
        string activity_level
        float target_calories
        float target_protein
        float target_carbs
        float target_fat
        string dietary_preference
        datetime created_at
    }

    MEAL_LOGS {
        int id PK
        int user_id FK
        date log_date
        string meal_type
        string food_name
        float calories
        float protein
        float carbs
        float fat
        datetime created_at
    }

    WEIGHT_LOGS {
        int id PK
        int user_id FK
        date log_date
        float weight_kg
        datetime created_at
    }

    ANALYTICS_SNAPSHOTS {
        int id PK
        int user_id FK
        date snapshot_date
        string metric_name
        float metric_value
        datetime created_at
    }

    FOOD_ITEMS {
        int id PK
        string name
        string category
        float energy_kcal
        float protein_g
        float carb_g
        float fat_g
        float fiber_g
        float sugar_g
        float sodium_mg
    }

    HOMELY_MEALS {
        int id PK
        string name
        string cuisine
        string base_item
        string condiments_json
        float total_calories
        bool approved
    }

    USERS ||--o{ MEAL_LOGS : logs
    USERS ||--o{ WEIGHT_LOGS : tracks
    USERS ||--o{ ANALYTICS_SNAPSHOTS : generates
```

---

## 9. Build, Test & Deploy Pipeline

```mermaid
flowchart TD
    subgraph BUILD["Database Build Pipeline"]
        B1["Raw Excel + CSV Datasets"] --> B2["build_nutrition_master_db.py<br/>Schema creation + ETL ingestion"]
        B2 --> B3["seed_custom_data.py<br/>Jain/Vegan rules + Drinks<br/>+ Mocktails + Homely supplements"]
        B3 --> B4[("nutrition_master.db<br/>Production-ready SQLite")]
    end

    subgraph TEST["Testing Pipeline"]
        T1["pytest -v"] --> T2["test_api.py<br/>FastAPI endpoint tests"]
        T1 --> T3["test_nutrition.py<br/>Nutrient lookup accuracy"]
        T1 --> T4["test_homely_meals.py<br/>Portion conversion tests"]
        T1 --> T5["test_optimization.py<br/>OR-Tools solver tests"]
        T1 --> T6["test_recommendation.py<br/>Budget alternative tests"]
        T1 --> T7["test_adaptive.py<br/>Trend analysis tests"]
        T1 --> T8["test_accuracy_upgrades.py<br/>Dialect synonym tests"]
        T1 --> T9["test_new_engines.py<br/>Scorer + classifier tests"]
    end

    subgraph DEPLOY["Deployment"]
        S1["python run.py<br/>--host 0.0.0.0 --port 8080"] --> S2["Uvicorn ASGI Server<br/>localhost:8080"]
        S2 --> S3["ngrok HTTPS Tunnel<br/>Public mobile URL"]
        S2 --> S4["API Docs<br/>localhost:8080/docs"]
    end
```

---

## 10. Complete File Tree

```mermaid
graph TD
    ROOT["NutriX AI Diet Planner"] --> APP["app/"]
    ROOT --> DATASET["Dataset/"]
    ROOT --> SCRIPTS["scripts/"]
    ROOT --> TESTS["tests/"]
    ROOT --> CONF["Config Files"]

    APP --> A1["__init__.py"]
    APP --> A2["main.py (80 KB)<br/>All API routes + SPA template"]
    APP --> A3["models.py (23 KB)<br/>SQLAlchemy ORM models"]
    APP --> A4["db.py<br/>DB connection + fallback logic"]
    APP --> A5["schemas.py<br/>Pydantic request/response"]
    APP --> A6["schemas_recipes.py<br/>Recipe-specific schemas"]
    APP --> SVC["services/"]

    SVC --> S1["auth_service.py"]
    SVC --> S2["barcode_service.py"]
    SVC --> S3["nutrition_engine.py"]
    SVC --> S4["homely_meals_engine.py"]
    SVC --> S5["ingredient_matcher.py"]
    SVC --> S6["recipe_ranker.py"]
    SVC --> S7["optimization_engine.py"]
    SVC --> S8["adaptive_planner.py"]
    SVC --> S9["analytics_engine.py"]
    SVC --> S10["recommendation_engine.py"]
    SVC --> S11["classification_engine.py"]
    SVC --> S12["health_scorer.py"]
    SVC --> S13["ocr_engine.py"]
    SVC --> S14["explanation_engine.py"]
    SVC --> S15["ml_extension.py"]

    SCRIPTS --> SC1["build_nutrition_master_db.py"]
    SCRIPTS --> SC2["seed_custom_data.py"]
    SCRIPTS --> SC3["start_ngrok.py"]
    SCRIPTS --> SC4["migrate_models.py"]
    SCRIPTS --> SC5["analyze_mapping.py"]

    CONF --> C1[".env"]
    CONF --> C2[".gitignore"]
    CONF --> C3["requirements.txt"]
    CONF --> C4["run.py"]
    CONF --> C5["README.md"]
```
