class NutritionEngine:
    @staticmethod
    def calculate_bmi(weight: float, height: float) -> float:
        """Calculate Body Mass Index (BMI).
        weight: in kg
        height: in cm
        """
        if not height or height <= 0:
            return 0.0
        height_m = height / 100.0
        return round(weight / (height_m ** 2), 2)

    @staticmethod
    def calculate_bmr(weight: float, height: float, age: int, gender: str) -> float:
        """Calculate Basal Metabolic Rate (BMR) using Mifflin-St Jeor equation.
        weight: in kg
        height: in cm
        age: in years
        gender: 'male' or 'female'
        """
        # BMR = 10 * weight + 6.25 * height - 5 * age + s
        # s = +5 for men, -161 for women
        if gender.lower() == "male":
            s = 5
        else:
            s = -161
        return round(10.0 * weight + 6.25 * height - 5.0 * age + s, 2)

    @staticmethod
    def calculate_tdee(bmr: float, activity_level: str) -> float:
        """Calculate Total Daily Energy Expenditure (TDEE).
        activity_level: 'sedentary', 'lightly_active', 'moderately_active', 'active', 'very_active'
        """
        multipliers = {
            "sedentary": 1.2,
            "lightly_active": 1.375,
            "moderately_active": 1.55,
            "active": 1.725,
            "very_active": 1.9
        }
        multiplier = multipliers.get(activity_level.lower(), 1.2)
        return round(bmr * multiplier, 2)

    @classmethod
    def calculate_targets(cls, age: int, gender: str, height: float, weight: float, activity_level: str, goal: str) -> dict:
        """Calculate daily calorie and macronutrient targets.
        goal: 'fat loss', 'weight gain', 'muscle gain', 'maintenance'
        """
        bmi = cls.calculate_bmi(weight, height)
        bmr = cls.calculate_bmr(weight, height, age, gender)
        tdee = cls.calculate_tdee(bmr, activity_level)

        # Calorie offsets based on goals
        if goal.lower() == "fat loss":
            target_calories = tdee - 500.0
            # Safety floors
            min_calories = 1500.0 if gender.lower() == "male" else 1200.0
            if target_calories < min_calories:
                target_calories = min_calories
        elif goal.lower() == "weight gain":
            target_calories = tdee + 500.0
        elif goal.lower() == "muscle gain":
            target_calories = tdee + 300.0
        else: # maintenance
            target_calories = tdee

        target_calories = round(target_calories, 2)

        # Macronutrient splits
        # 'fat loss': 30% Protein / 40% Carbs / 30% Fat
        # 'weight gain': 25% Protein / 50% Carbs / 25% Fat
        # 'muscle gain': 30% Protein / 45% Carbs / 25% Fat
        # 'maintenance': 25% Protein / 45% Carbs / 30% Fat
        goal_lower = goal.lower()
        if goal_lower == "fat loss":
            p_pct, c_pct, f_pct = 0.30, 0.40, 0.30
        elif goal_lower == "weight gain":
            p_pct, c_pct, f_pct = 0.25, 0.50, 0.25
        elif goal_lower == "muscle gain":
            p_pct, c_pct, f_pct = 0.30, 0.45, 0.25
        else: # maintenance
            p_pct, c_pct, f_pct = 0.25, 0.45, 0.30

        # Calculate grams (Protein: 4 kcal/g, Carbs: 4 kcal/g, Fat: 9 kcal/g)
        protein_g = round((target_calories * p_pct) / 4.0, 2)
        carbs_g = round((target_calories * c_pct) / 4.0, 2)
        fat_g = round((target_calories * f_pct) / 9.0, 2)

        # Get BMI description
        if bmi < 18.5:
            bmi_status = "Underweight"
        elif 18.5 <= bmi < 25.0:
            bmi_status = "Normal weight"
        elif 25.0 <= bmi < 30.0:
            bmi_status = "Overweight"
        else:
            bmi_status = "Obese"

        return {
            "bmi": bmi,
            "bmi_status": bmi_status,
            "bmr": bmr,
            "tdee": tdee,
            "target_calories": target_calories,
            "target_protein_g": protein_g,
            "target_carbs_g": carbs_g,
            "target_fat_g": fat_g
        }
