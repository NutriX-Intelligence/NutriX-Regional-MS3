# NutriX System Modules & Component Documentation

## Executive Overview
**NutriX** is an intelligent, multimodal AI ecosystem designed for personalized dietary recommendation, real-time nutritional tracking, and clinical diet planning. The architecture blends computer vision, barcode processing, Optical Character Recognition (OCR), Retrieval-Augmented Generation (RAG), local Large Language Models (LLMs), integer optimization (Google OR-Tools), and a 4-Tier Multi-Agent System (MAS) overlay.

Below is the complete reference of all system modules across the application architecture.

---

## 1. Multimodal Data Ingestion & Computer Vision Modules

### 1.1 `barcode_service.py` — UPC/EAN Barcode Processing Engine
* **Purpose:** Provides instantaneous, zero-hallucination nutritional lookup for packaged food products using standard 1D and 2D barcodes.
* **Key Functionality:**
  * Uses OpenCV to decode standard UPC-A, UPC-E, EAN-8, and EAN-13 barcodes from camera video frames or uploaded images.
  * Queries local PostgreSQL master food tables for instant exact nutritional matching.
  * Integrates external fallback APIs (OpenFoodFacts API and USDA FoodData Central) when an item is missing from local databases.
  * Caches retrieved barcode nutrition vectors into Redis for fast subsequent access.

### 1.2 `classification_engine.py` — Vision & YOLOv8 Object Detection Engine
* **Purpose:** Handles physical food item recognition from camera JPEG frames when no barcode is present.
* **Key Functionality:**
  * Executes a custom-trained **YOLOv8n** model (`calcount_yolo_custom.pt`) fine-tuned on **123 food classes** (fruits, raw ingredients, and regional prepared dishes).
  * Measures bounding boxes and calculates class probability scores.
  * Applies an **80% Confidence Threshold ($C \ge 0.80$)**:
    * **$C \ge 0.80$ (Optimistic Path):** Class identification is accepted automatically, and nutritional mass calculations are triggered.
    * **$C < 0.80$ (HitL Path):** Image frame is diverted to the Human-in-the-Loop active learning queue.

### 1.3 `hitl_engine.py` & `retrain_yolo.py` — Active Learning & Self-Healing Vision Loop
* **Purpose:** Enables continuous, autonomous improvement of the computer vision model without manual retraining intervention.
* **Key Functionality:**
  * Low-confidence frames ($C < 0.80$) are saved under `/dataset/pending/`.
  * Upon user confirmation/correction in the mobile UI, `hitl_engine.py` automatically generates normalized YOLO format `.txt` bounding-box annotations.
  * Stages approved image-annotation pairs under `/dataset/trained/`.
  * Triggers background execution of `retrain_yolo.py`, running **3 fine-tuning epochs** (~10s on GPU) to produce updated model weights (`yolov8_retrained.pt`).

### 1.4 `ocr_engine.py` — Optical Character Recognition & Label Parser
* **Purpose:** Extracts structured nutritional tables directly from printed physical packaging labels.
* **Key Functionality:**
  * **Primary Extractor:** Uses **EasyOCR** to extract raw text lines from label photos.
  * Applies a custom regular expression (Regex) parser to extract caloric content, macronutrients (protein, carbohydrates, total fat), and micronutrients (sodium, sugar, dietary fibre).
  * **Vision LLM Fallback:** If EasyOCR text extraction fails (due to surface glare, label curvature, or non-standard formatting), the image is routed to the **Gemini Vision API** as a multimodal fallback to output clean, structured JSON.

---

## 2. Core AI & Recommendation Engines

### 2.1 `recommendation_engine.py` — Personalized Nutrition & Meal Generator
* **Purpose:** Core engine for generating daily meal plans tailored to individual metabolic targets, dietary constraints, and clinical goals.
* **Key Functionality:**
  * Computes personalized macro targets based on age, gender, height, mass, activity level, and medical conditions (e.g., Type 2 Diabetes, Hypertension).
  * Synthesizes meal suggestions across 4 daily slots (Breakfast, Lunch, Snack, Dinner).
  * Ensures compliance with user dietary preferences (e.g., Vegetarian, Vegan, Jain, Gluten-Free, Keto).

### 2.2 `optimization_engine.py` — Deterministic Integer Linear Programming (ILP) Solver
* **Purpose:** Guarantees mathematically optimal meal recommendations while eliminating LLM hallucination risks.
* **Key Functionality:**
  * Uses **Google OR-Tools** to solve daily meal selection as an Integer Linear Programming (ILP) problem.
  * Formulates binary decision variables $x_r \in \{0, 1\}$ for each candidate recipe $r$.
  * Minimizes weighted absolute deviations between planned macros and target macros:
    $$\min \sum_{m \in \mathcal{M}} w_m \cdot \left| \sum_{r \in \mathcal{R}} x_r \cdot M_{r,m} - T_m \right|$$
  * Enforces hard clinical constraints:
    * **Caloric Window:** $0.95 T_{\text{kcal}} \le \sum_r x_r \cdot \text{kcal}_r \le 1.05 T_{\text{kcal}}$ ($\pm 5\%$)
    * **Protein Floor:** $\sum_r x_r \cdot \text{prot}_r \ge 0.90 T_{\text{prot}}$ (at least $90\%$)
    * **NOVA-4 Cap:** $\sum_{r \in \mathcal{R}_{\text{NOVA4}}} x_r \le 1$ (max 1 ultra-processed food per day)
    * **Meal Slot Budget:** Exactly 1 recipe per meal slot.

### 2.3 `adaptive_planner.py` — Intra-Day Dynamic Recalibration Engine
* **Purpose:** Recalculates remaining meal targets dynamically when a user strays from their scheduled plan during the day.
* **Key Functionality:**
  * Monitors intake telemetry throughout the day.
  * If a user over-consumes calories or carbohydrates at lunch, `adaptive_planner.py` automatically adjusts targets for dinner and snacks to maintain daily balance.

### 2.4 `homely_meals_engine.py` — Regional & Home-Cooked Recipe Engine
* **Purpose:** Tailors meal plans to regional Indian dietary habits and home-cooked recipes.
* **Key Functionality:**
  * Maps raw household ingredients to standardized regional recipes (e.g., North Indian, South Indian, Maharashtrian).
  * Computes accurate portion sizes and cooking method adjustments (e.g., boiling vs. deep frying macro impacts).

### 2.5 `health_scorer.py` — Health Index & NOVA Classification Engine
* **Purpose:** Evaluates the overall health quality of consumed food items and full daily menus.
* **Key Functionality:**
  * Categorizes foods according to the **NOVA Food Processing Classification System** (Group 1: Unprocessed, Group 2: Processed Ingredients, Group 3: Processed Foods, Group 4: Ultra-Processed Foods).
  * Calculates a normalized Health Score ($0 - 100$) by penalizing ultra-processed foods, high sodium, added sugars, and saturated fats, while rewarding dietary fibre and micronutrients.

### 2.6 `ingredient_matcher.py` — Ingredient Normalization & Allergen Filter
* **Purpose:** Normalizes ingredient naming variations and enforces absolute allergy exclusions.
* **Key Functionality:**
  * Uses fuzzy text matching and semantic embedding distance to map regional ingredient names (e.g., *"brinjal"* vs. *"eggplant"*) to master canonical database records.
  * Enforces hard allergen exclusion filters (e.g., Peanuts, Tree Nuts, Lactose, Shellfish) before recipes are passed to the meal optimizer.

### 2.7 `recipe_ranker.py` — Multi-Criteria Recipe Scorer
* **Purpose:** Ranks candidate recipes prior to final meal assembly.
* **Key Functionality:**
  * Multiplies composite score factors:
    $$\text{Score} = \text{HealthScore} \times \text{MacroFit} \times \text{UserPreferenceFit}$$
  * Ensures top-ranked candidate recipes align with both clinical guidelines and user taste preferences.

### 2.8 `explanation_engine.py` — Explainable AI (XAI) Rationale Engine
* **Purpose:** Generates transparent, human-understandable explanations for why specific meals were recommended or flagged.
* **Key Functionality:**
  * Translates mathematical ILP outputs and health scoring factors into concise natural language summaries.
  * Explains clinical rationales (e.g., *"Recommended high-spinach dinner to meet your remaining 15mg Iron target while keeping carbs below 30g"*).

### 2.9 `analytics_engine.py` — Longitudinal Analysis & Anomaly Detector
* **Purpose:** Analyzes user dietary habits over time and detects physiological risk anomalies.
* **Key Functionality:**
  * Tracks weekly and monthly nutritional trends, weight velocity, and macro ratios.
  * Flags repetitive dangerous dietary patterns (e.g., 3 consecutive days of severe sodium overflow in hypertensive users).

### 2.10 `nutrition_engine.py` — Metabolic & Energy Expenditure Calculator
* **Purpose:** Computes baseline metabolic benchmarks.
* **Key Functionality:**
  * Implements the **Mifflin-St Jeor Equation** to calculate Basal Metabolic Rate (BMR).
  * Multiplies by Physical Activity Levels (PAL) to determine Total Daily Energy Expenditure (TDEE).

### 2.11 `ml_extension.py` — ML Predictor & Collaborative Filtering
* **Purpose:** Predictive modeling module for user habit forecasting and collaborative recommendation.
* **Key Functionality:**
  * Employs collaborative filtering to suggest recipes enjoyed by users with similar biometric profiles and taste preferences.

---

## 3. Infrastructure, API & Data Persistence Modules

### 3.1 `main.py` — Microservice API Gateway & Router
* **Purpose:** Serves as the primary REST API application built with **FastAPI**.
* **Key Functionality:**
  * Exposes secure endpoints for image upload, barcode scanning, manual logging, meal plan generation, and user profile management.
  * Configures middleware (CORS, Request Logging, Rate Limiting).

### 3.2 `db.py` — Database Connection Manager
* **Purpose:** Controls database session pooling and ORM initialization.
* **Key Functionality:**
  * Manages connections to the **PostgreSQL** master relational database via SQLAlchemy.
  * Controls async connection sessions for high-concurrency request handling.

### 3.3 `models.py` — Database Schema Definitions
* **Purpose:** Defines PostgreSQL relational table structures using SQLAlchemy ORM.
* **Key Tables:**
  * `User`: User profiles, biometric stats, dietary preferences, and medical goals.
  * `FoodItem` & `Recipe`: Canonical food names, ingredients, NOVA classification, and macro/micronutrient profiles per 100g.
  * `MealLog`: Timestamped meal logs linked to mass ($W$), recognition source (Barcode/YOLO/OCR/LLM), and intake calculations.
  * `AuditTrace`: High-precision logs storing LLM prompts, raw outputs, confidence metrics, and agent self-healing history.

### 3.4 `schemas.py` & `schemas_recipes.py` — Pydantic Data Contracts
* **Purpose:** Defines input validation and response schemas for all REST API endpoints.
* **Key Functionality:**
  * Enforces strict type checking, non-negative nutrient values, and standardized JSON structures for client-server communication.

### 3.5 `auth_service.py` — Authentication & Authorization Module
* **Purpose:** Manages security, token generation, and user identity.
* **Key Functionality:**
  * Implements **JWT (JSON Web Tokens)** with SHA-256 password hashing.
  * Enforces Role-Based Access Control (RBAC) across patient, dietitian, and administrator access levels.

---

## 4. Four-Tier Multi-Agent System (MAS) Overlay

Beyond the standard microservice layer, NutriX deploys an event-driven **4-Tier Multi-Agent Overlay** that monitors data execution traces asynchronously over a **Redis Pub/Sub Event Stream** (`nutrix:user:{id}:macros`).

```
 +-----------------------------------------------------------------------+
 |                     Tier 3: Meta-Auditor Agent                        |
 |         (Autonomic Self-Healing, S_faith Score, Prompt Patching)      |
 +-----------------------------------------------------------------------+
                                     ^
                                     | Audit Traces
 +-----------------------------------------------------------------------+
 |            Tier 2B: Clinical Multidisciplinary Team (MDT)             |
 |    (Diagnostic Agent  ->  Intervention Agent  ->  Drafting Agent)     |
 +-----------------------------------------------------------------------+
                                     ^
                                     | High-Risk Escalation (L3)
 +-----------------------------------------------------------------------+
 |                  Tier 2A: Guardian Surveillance Agent                 |
 |        (Real-time Risk Evaluation \rho_t, Instant Outlier Push)       |
 +-----------------------------------------------------------------------+
                                     ^
                                     | Redis Pub/Sub Stream
 +-----------------------------------------------------------------------+
 |                  Tier 1: Perceptual Ingestion Agents                  |
 |       (ESP32 Load Cell Capture, Image Ingress, Barcode/YOLO/OCR)      |
 +-----------------------------------------------------------------------+
```

### 4.1 Tier 1: Perceptual Ingestion Agents
* **Role:** Interfaces directly with physical sensors (ESP32-S3 IoT scale, mobile cameras) to acquire telemetry, normalize weight readings, and extract preliminary visual features.

### 4.2 Tier 2A: Guardian Surveillance Agents
* **Role:** Subscribes continuously to live Redis intake streams. Evaluates real-time patient risk scores ($\rho_t$). If an intake outlier occurs (e.g., severe glycemic spike risk), it instantly pushes Level 1 alert warnings to the user's device.

### 4.3 Tier 2B: Clinical Multidisciplinary Team (MDT) Agents
* **Role:** Triggered during complex or high-risk patient scenarios.
  * **Diagnostic Agent:** Scans 30-day historical intake logs, identifying root causes of nutritional deficiencies.
  * **Intervention Agent:** Runs `optimization_engine.py` (Google OR-Tools ILP) to formulate corrective meal plans.
  * **Drafting Agent:** Generates clinical summary reports for dietitian sign-off.

### 4.4 Tier 3: Meta-Auditor Agent
* **Role:** The autonomic self-healing supervisor of NutriX.
  * Calculates the **Quantitative Faithfulness Score ($S_{\text{faith}}$)** for every AI inference:
    $$S_{\text{faith}} = \frac{\sum_{m \in \mathcal{M}} w_m \cdot \left(1 - \min\left(1, \frac{|\hat{M}_m - M_m^{\text{ground}}|}{M_m^{\text{ground}}}\right)\right)}{\sum_{m \in \mathcal{M}} w_m}$$
  * If $S_{\text{faith}} < 0.70$, the Meta-Auditor flags systemic failure and autonomously executes self-healing:
    * **Vision Failure:** Auto-annotates low-confidence frames and triggers 3-epoch YOLO fine-tuning (`retrain_yolo.py`).
    * **LLM Hallucination:** Appends corrective rule patches to the **System Prompt Patch Registry**.

---

## 5. Summary Matrix of System Modules

| Module Name | Primary File | Key Tech Stack | Category |
| :--- | :--- | :--- | :--- |
| **Barcode Service** | `barcode_service.py` | OpenCV, OpenFoodFacts API, PostgreSQL | Ingestion & Vision |
| **CV Classification** | `classification_engine.py` | YOLOv8n, PyTorch, OpenCV | Computer Vision |
| **HitL Active Learning** | `hitl_engine.py`, `retrain_yolo.py` | PyTorch, CUDA, Active Learning | Computer Vision / Self-Healing |
| **OCR Label Parser** | `ocr_engine.py` | EasyOCR, Gemini Vision API, Regex | Ingestion & Vision |
| **ILP Optimizer** | `optimization_engine.py` | Google OR-Tools (ILP), Python | Recommendation & Optimization |
| **Recommendation Engine** | `recommendation_engine.py` | Python, Algorithmic Nutrition | Recommendation & Optimization |
| **Adaptive Planner** | `adaptive_planner.py` | Python, Dynamic Recalibration | Clinical Interventions |
| **Homely Meals Engine** | `homely_meals_engine.py` | Regional Recipe Mapping, Python | Recipe Intelligence |
| **Health Scorer** | `health_scorer.py` | NOVA Classification System, Python | Clinical Quality |
| **Ingredient Matcher** | `ingredient_matcher.py` | Fuzzy Matching, Allergen Rules | Data Normalization |
| **Recipe Ranker** | `recipe_ranker.py` | Multi-Criteria Scoring | Recommendation |
| **Explanation Engine** | `explanation_engine.py` | Explainable AI (XAI), Natural Language | Transparency |
| **Analytics Engine** | `analytics_engine.py` | Time-Series Data, Anomaly Detection | Clinical Analytics |
| **Nutrition Engine** | `nutrition_engine.py` | Mifflin-St Jeor, TDEE Formulas | Metabolic Benchmarking |
| **ML Extension** | `ml_extension.py` | Collaborative Filtering, Scikit-learn | Predictive Analytics |
| **API Gateway** | `main.py` | FastAPI, Uvicorn, REST | Infrastructure |
| **Database Connector** | `db.py` | SQLAlchemy, PostgreSQL | Persistence |
| **Data Models** | `models.py` | SQLAlchemy ORM | Persistence |
| **API Schemas** | `schemas.py`, `schemas_recipes.py` | Pydantic | API Contracts |
| **Auth Service** | `auth_service.py` | JWT, Passlib, RBAC | Security |
| **4-Tier Agent Overlay** | MAS Infrastructure | Redis Pub/Sub, Asynchronous Workers | Multi-Agent System |
