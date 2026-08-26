import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app import models
from app.services.classification_engine import ClassificationEngine
from app.services.recommendation_engine import RecommendationEngine

class TestDietaryClassifier(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_safe_compounds_no_false_positives(self):
        """Verify that compound terms like eggplant, coconut milk, oatmeal, peanut butter do not trigger false exclusions."""
        # 1. Eggplant is not egg
        res = ClassificationEngine.classify_ingredients(["Eggplant", "Spinach", "Olive Oil"])
        self.assertTrue(res["is_vegan"], "Eggplant must not be flagged as containing egg")
        self.assertTrue(res["is_vegetarian"])
        self.assertTrue(res["is_jain"], "Eggplant is not a root vegetable")

        # 2. Oatmeal is not meat
        res_oat = ClassificationEngine.classify_ingredients(["Oatmeal", "Almond Milk", "Blueberries"])
        self.assertTrue(res_oat["is_vegan"], "Oatmeal and almond milk must be vegan")
        self.assertTrue(res_oat["is_vegetarian"], "Oatmeal must not be flagged as containing meat")

        # 3. Peanut butter and cocoa butter are not dairy butter
        res_pb = ClassificationEngine.classify_ingredients(["Peanut Butter", "Cocoa Butter", "Banana"])
        self.assertTrue(res_pb["is_vegan"], "Peanut butter and cocoa butter are dairy-free plant butters")
        self.assertTrue(res_pb["is_dairy_free"])
        self.assertIn("Peanuts", res_pb["allergens"])

        # 4. Coconut milk and cashew cream are not dairy
        res_cm = ClassificationEngine.classify_ingredients(["Coconut Milk", "Cashew Cream", "Curry Powder"])
        self.assertTrue(res_cm["is_vegan"])
        self.assertTrue(res_cm["is_dairy_free"])

        # 5. Nutmeg is a spice, not a tree nut allergen
        res_sp = ClassificationEngine.classify_ingredients(["Nutmeg", "Cinnamon", "Cardamom", "Rice"])
        self.assertTrue(res_sp["is_nut_free"])

        # 6. Bean curd / Tofu is vegan and not dairy curd
        res_tofu = ClassificationEngine.classify_ingredients(["Bean Curd", "Broccoli", "Sesame Oil"])
        self.assertTrue(res_tofu["is_vegan"])
        self.assertTrue(res_tofu["is_dairy_free"])

    def test_jain_classification_precision(self):
        """Verify precision of Jain rule checks (roots, alliums, mushrooms, honey, dairy)."""
        # Jain Vegetarian dish (Dairy allowed, no roots/alliums)
        jain_veg = ClassificationEngine.classify_ingredients(["Paneer", "Tomato", "Capsicum", "Jeera", "Ghee"])
        self.assertTrue(jain_veg["is_jain"], "Paneer + tomato + capsicum + ghee is valid Jain food")
        self.assertTrue(jain_veg["is_vegetarian"])
        self.assertFalse(jain_veg["is_vegan"], "Ghee and paneer are dairy, so not vegan")
        self.assertEqual(jain_veg["dietary_tag"], "Jain")

        # Jain Vegan dish
        jain_vegan = ClassificationEngine.classify_ingredients(["Tofu", "Tomato", "Capsicum", "Jeera", "Mustard Oil"])
        self.assertTrue(jain_vegan["is_jain"])
        self.assertTrue(jain_vegan["is_vegan"])

        # Allium exclusion (Onion, Garlic, Pyaz, Lehsun, Spring Onion)
        res_onion = ClassificationEngine.classify_ingredients(["Tomato", "Pyaaz", "Salt"])
        self.assertFalse(res_onion["is_jain"], "Pyaaz must exclude Jain")
        self.assertTrue(res_onion["is_vegan"])

        res_garlic = ClassificationEngine.classify_ingredients(["Spinach", "Lehsun", "Mustard Oil"])
        self.assertFalse(res_garlic["is_jain"], "Lehsun must exclude Jain")
        self.assertTrue(res_garlic["is_vegan"])

        # Root vegetable exclusions (Aloo, Adrak, Gajar, Mooli, Beetroot, Suran)
        res_aloo = ClassificationEngine.classify_ingredients(["Aloo", "Jeera", "Oil"])
        self.assertFalse(res_aloo["is_jain"], "Aloo (potato) must exclude Jain")

        res_adrak = ClassificationEngine.classify_ingredients(["Ginger", "Cardamom", "Tea"])
        self.assertFalse(res_adrak["is_jain"], "Ginger (adrak) must exclude Jain")

        res_gajar = ClassificationEngine.classify_ingredients(["Gajar", "Capsicum", "Oil"])
        self.assertFalse(res_gajar["is_gajar"] if "is_gajar" in res_gajar else res_gajar["is_jain"], "Gajar must exclude Jain")

        # Mushroom & Honey exclusions in Jain
        res_mush = ClassificationEngine.classify_ingredients(["Mushroom", "Peas", "Tomato"])
        self.assertFalse(res_mush["is_jain"], "Mushrooms must exclude Jain")
        self.assertTrue(res_mush["is_vegan"])

        res_honey = ClassificationEngine.classify_ingredients(["Lemon", "Honey", "Water"])
        self.assertFalse(res_honey["is_jain"], "Honey must exclude Jain")
        self.assertFalse(res_honey["is_vegan"], "Honey must exclude Vegan")

    def test_vegan_classification_precision(self):
        """Verify that all animal derivatives exclude veganism."""
        # Dairy exclusions
        for item in ["Milk", "Cheese", "Butter", "Curd", "Dahi", "Ghee", "Paneer", "Malai", "Whey Protein", "Casein"]:
            res = ClassificationEngine.classify_ingredients([item, "Rice"])
            self.assertFalse(res["is_vegan"], f"{item} must exclude Vegan")
            self.assertTrue(res["is_vegetarian"], f"{item} is vegetarian")

        # Gelatin & Carmine
        res_gel = ClassificationEngine.classify_ingredients(["Gelatin", "Sugar", "Water"])
        self.assertFalse(res_gel["is_vegan"])
        self.assertFalse(res_gel["is_vegetarian"])

    def test_eggetarian_and_pescatarian(self):
        """Verify Eggetarian and Pescatarian boundaries."""
        # Eggetarian
        res_egg = ClassificationEngine.classify_ingredients(["Boiled Egg", "Black Pepper", "Toast"])
        self.assertTrue(res_egg["is_eggetarian"])
        self.assertFalse(res_egg["is_vegetarian"])
        self.assertFalse(res_egg["is_vegan"])
        self.assertEqual(res_egg["dietary_tag"], "Eggetarian")

        res_anda = ClassificationEngine.classify_ingredients(["Anda Bhurji", "Butter"])
        self.assertTrue(res_anda["is_eggetarian"])
        self.assertFalse(res_anda["is_vegetarian"])

        # Pescatarian
        res_fish = ClassificationEngine.classify_ingredients(["Salmon", "Steamed Rice", "Lemon"])
        self.assertTrue(res_fish["is_pescatarian"])
        self.assertFalse(res_fish["is_eggetarian"])
        self.assertFalse(res_fish["is_vegetarian"])
        self.assertEqual(res_fish["dietary_tag"], "Pescatarian")

        # Meat (Non-Veg)
        res_chicken = ClassificationEngine.classify_ingredients(["Chicken Tikka", "Roti"])
        self.assertFalse(res_chicken["is_pescatarian"])
        self.assertFalse(res_chicken["is_eggetarian"])
        self.assertFalse(res_chicken["is_vegetarian"])
        self.assertEqual(res_chicken["dietary_tag"], "Non-Vegetarian")

    def test_gluten_and_allergens(self):
        """Verify accurate detection of allergens."""
        res = ClassificationEngine.classify_ingredients(["Atta", "Paneer", "Cashews", "Shrimp", "Soy Sauce"])
        self.assertFalse(res["is_gluten_free"])
        self.assertFalse(res["is_dairy_free"])
        self.assertFalse(res["is_nut_free"])
        self.assertIn("Gluten / Wheat", res["allergens"])
        self.assertIn("Dairy", res["allergens"])
        self.assertIn("Tree Nuts", res["allergens"])
        self.assertIn("Fish / Shellfish", res["allergens"])
        self.assertIn("Soy", res["allergens"])

    def test_special_gluten_free_grains(self):
        """Verify that pseudocereals & grains like buckwheat (kuttu) and glutinous rice are recognized as gluten-free."""
        # Glutinous rice is 100% gluten-free despite the name
        res_gr = ClassificationEngine.classify_ingredients(["Glutinous Rice", "Coconut Milk", "Mango"])
        self.assertTrue(res_gr["is_gluten_free"], "Glutinous rice contains amylopectin, not gluten")

        # Buckwheat / Kuttu is a gluten-free pseudocereal
        res_bw = ClassificationEngine.classify_ingredients(["Buckwheat Flour", "Potatoes", "Rock Salt"])
        self.assertTrue(res_bw["is_gluten_free"], "Buckwheat is gluten-free")

        res_kuttu = ClassificationEngine.classify_ingredients(["Kuttu Ka Atta", "Ghee", "Singhare Ka Atta"])
        self.assertTrue(res_kuttu["is_gluten_free"], "Kuttu and Singhara flours are gluten-free")

    def test_extended_diets_keto_paleo_sattvic_clean_label(self):
        """Verify classification of Keto, Paleo, Low-FODMAP, Sattvic, and Clean Label."""
        # 1. Keto Compliant vs Non-Keto
        keto_meal = ClassificationEngine.classify_ingredients(["Chicken", "Butter", "Spinach", "Heavy Cream"])
        self.assertTrue(keto_meal["is_keto"], "Chicken + butter + spinach is keto-friendly")
        self.assertFalse(keto_meal["is_vegetarian"])

        non_keto_meal = ClassificationEngine.classify_ingredients(["White Rice", "Sugar", "Mango"])
        self.assertFalse(non_keto_meal["is_keto"], "Rice and sugar are high carb")

        # 2. Paleo Compliant vs Non-Paleo
        paleo_meal = ClassificationEngine.classify_ingredients(["Salmon", "Spinach", "Avocado", "Walnuts"])
        self.assertTrue(paleo_meal["is_paleo"], "Salmon + greens + avocado is paleo compliant")

        non_paleo_meal = ClassificationEngine.classify_ingredients(["Atta", "Paneer", "Rajma"])
        self.assertFalse(non_paleo_meal["is_paleo"], "Grains, dairy, and legumes violate Paleo")

        # 3. Sattvic Compliant vs Non-Sattvic
        sattvic_meal = ClassificationEngine.classify_ingredients(["Rice", "Moong Dal", "Ghee", "Turmeric", "Jeera"])
        self.assertTrue(sattvic_meal["is_sattvic"], "Khichdi with ghee and mild spices is Sattvic")

        non_sattvic_meal = ClassificationEngine.classify_ingredients(["Paneer", "Pyaaz", "Lehsun", "Mushroom"])
        self.assertFalse(non_sattvic_meal["is_sattvic"], "Onion, garlic, mushroom violate Sattvic diet")

        # 4. Clean Label (No artificial additives / MSG / artificial sweeteners)
        clean_meal = ClassificationEngine.classify_ingredients(["Tomato", "Cucumber", "Olive Oil", "Salt"])
        self.assertTrue(clean_meal["is_clean_label"])

        unclean_meal = ClassificationEngine.classify_ingredients(["Noodles", "Monosodium Glutamate", "Red 40", "Aspartame", "Sodium Benzoate"])
        self.assertFalse(unclean_meal["is_clean_label"])

    def test_smart_substitutions_engine(self):
        """Verify culinary authentic substitutions generation."""
        # Jain substitutions for onion, garlic, potato
        subs_jain = ClassificationEngine.get_substitutions(["Onion", "Garlic", "Potato", "Tomato"], target_diet="jain")
        triggers = [s["detected_trigger"] for s in subs_jain]
        self.assertIn("onion", triggers)
        self.assertIn("garlic", triggers)
        self.assertIn("potato", triggers)
        
        # Verify specific culinary tips exist
        onion_sub = next(s for s in subs_jain if s["detected_trigger"] == "onion")
        self.assertTrue(any("Hing" in x for x in onion_sub["recommended_substitutes"]))

        # Vegan substitutions for paneer and dairy ghee
        subs_vegan = ClassificationEngine.get_substitutions(["Paneer", "Desi Ghee", "Milk"], target_diet="vegan")
        v_triggers = [s["detected_trigger"] for s in subs_vegan]
        self.assertIn("paneer", v_triggers)
        self.assertIn("ghee", v_triggers)
        self.assertIn("milk", v_triggers)

        # Gluten-free substitutions for wheat flour and maida
        subs_gf = ClassificationEngine.get_substitutions(["Wheat Atta", "Maida", "Sooji"], target_diet="gluten_free")
        gf_triggers = [s["detected_trigger"] for s in subs_gf]
        self.assertIn("wheat", gf_triggers)

    def test_recommendation_engine_integration(self):
        """Verify RecommendationEngine methods use enhanced ClassificationEngine."""
        # Recipe with eggplant and coconut milk
        r = models.Recipe(recipe_code="R_TEST_VEG", recipe_name="Eggplant Coconut Curry", category="Lunch/Dinner")
        self.db.add(r)
        self.db.flush()
        self.db.add(models.RecipeIngredient(recipe_code="R_TEST_VEG", food_name="Eggplant"))
        self.db.add(models.RecipeIngredient(recipe_code="R_TEST_VEG", food_name="Coconut Milk"))
        self.db.add(models.RecipeIngredient(recipe_code="R_TEST_VEG", food_name="Turmeric"))
        self.db.commit()

        self.assertTrue(RecommendationEngine.is_vegan(r))
        self.assertTrue(RecommendationEngine.is_vegetarian(r))
        self.assertEqual(RecommendationEngine.get_dietary_tag(r), "Jain") # No roots/alliums/meat/dairy

if __name__ == "__main__":
    unittest.main()

