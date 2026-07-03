import unittest
from app.services.nutrition_engine import NutritionEngine

class TestNutritionEngine(unittest.TestCase):
    def test_calculate_bmi(self):
        # Weight = 70kg, Height = 175cm
        # BMI = 70 / (1.75^2) = 22.86
        bmi = NutritionEngine.calculate_bmi(70, 175)
        self.assertAlmostEqual(bmi, 22.86, places=2)

        # Edge case
        self.assertEqual(NutritionEngine.calculate_bmi(70, 0), 0.0)

    def test_calculate_bmr(self):
        # Male: 10 * 70 + 6.25 * 175 - 5 * 30 + 5 = 700 + 1093.75 - 150 + 5 = 1648.75
        bmr_male = NutritionEngine.calculate_bmr(70, 175, 30, "male")
        self.assertAlmostEqual(bmr_male, 1648.75, places=2)

        # Female: 10 * 60 + 6.25 * 160 - 5 * 25 - 161 = 600 + 1000 - 125 - 161 = 1314.0
        bmr_female = NutritionEngine.calculate_bmr(60, 160, 25, "female")
        self.assertAlmostEqual(bmr_female, 1314.00, places=2)

    def test_calculate_tdee(self):
        bmr = 1500.0
        # Sedentary: 1500 * 1.2 = 1800
        self.assertEqual(NutritionEngine.calculate_tdee(bmr, "sedentary"), 1800.0)
        # Active: 1500 * 1.725 = 2587.5
        self.assertEqual(NutritionEngine.calculate_tdee(bmr, "active"), 2587.5)

    def test_calculate_targets_fat_loss(self):
        # Test targets for fat loss
        targets = NutritionEngine.calculate_targets(
            age=30,
            gender="male",
            height=175,
            weight=80,
            activity_level="moderately_active",
            goal="fat loss"
        )
        self.assertIn("target_calories", targets)
        self.assertIn("target_protein_g", targets)
        self.assertIn("target_carbs_g", targets)
        self.assertIn("target_fat_g", targets)
        
        # Verify macro proportions (Protein: 30%, Carbs: 40%, Fat: 30%)
        calories = targets["target_calories"]
        p_cals = targets["target_protein_g"] * 4.0
        c_cals = targets["target_carbs_g"] * 4.0
        f_cals = targets["target_fat_g"] * 9.0
        
        total_macro_cals = p_cals + c_cals + f_cals
        self.assertAlmostEqual(total_macro_cals / calories, 1.0, places=2)
        self.assertAlmostEqual(p_cals / total_macro_cals, 0.30, places=2)
        self.assertAlmostEqual(c_cals / total_macro_cals, 0.40, places=2)
        self.assertAlmostEqual(f_cals / total_macro_cals, 0.30, places=2)

if __name__ == "__main__":
    unittest.main()
