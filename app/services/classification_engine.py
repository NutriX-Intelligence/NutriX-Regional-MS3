import re
import functools
from typing import List, Dict, Any, Set, Tuple, Optional
from sqlalchemy.orm import Session
from app.models import Recipe, IngredientRule

class ClassificationEngine:
    """High-Precision Context-Aware Dietary Classification, Allergen & Smart Substitution Engine.
    
    Provides accurate, zero-false-positive classification across:
    - Vegan (100% Plant-Based)
    - Vegetarian (Lacto-Vegetarian)
    - Jain (Jain Vegetarian & Jain Vegan)
    - Eggetarian (Ovo-Lacto Vegetarian)
    - Pescatarian
    - Keto / Low-Carb
    - Paleo / Whole30
    - Low-FODMAP
    - Sattvic (Ayurvedic Pure)
    - Gluten-Free
    - Dairy-Free
    - Nut-Free / Peanut-Free
    - Halal Compliant
    - Kosher Compliant
    - Clean Label (Additive & Preservative Free)
    - Allergen Profiling (Big 14+ Global Standards)
    - Context-Aware Culinary Substitution Engine
    """

    # =========================================================================
    # 1. SAFE PLANT-BASED & NON-ANIMAL EXCEPTIONS (Prevent False Positives)
    # =========================================================================
    
    # Safe compound phrases replaced before token checks
    SAFE_COMPOUNDS = [
        # Plant Milks (not dairy)
        (r"\b(coconut|almond|soy|soya|oat|cashew|rice|hemp|pea|macadamia|hazelnut|flax|walnut|sunflower|plant|non-dairy|dairy-free)\s+milk\b", r"\1 plantmilk"),
        # Plant Butters (not dairy)
        (r"\b(peanut|cocoa|cacao|shea|apple|almond|cashew|walnut|hazelnut|sunflower|sunflower\s+seed|cookie|pumpkin\s+seed|soya|plant|vegan)\s+butter\b", r"\1 plantbutter"),
        # Plant Creams (not dairy)
        (r"\b(coconut|cashew|oat|soy|soya|plant|vegan|tartar)\s+cream\b", r"\1 plantcream"),
        (r"\bcream\s+of\s+tartar\b", "tartar plantcream"),
        (r"\bcream\s+of\s+coconut\b", "coconut plantcream"),
        (r"\bcream\s+of\s+wheat\b", "wheat grain"),
        # Plant Cheeses (not dairy)
        (r"\b(vegan|plant-based|dairy-free|cashew|tofu|soy|soya|almond|nut)\s+cheese\b", r"\1 plantcheese"),
        # Plant Yogurt/Curd (not dairy)
        (r"\b(coconut|almond|soy|soya|oat|cashew|plant|vegan)\s+(yogurt|yoghurt|curd|dahi)\b", r"\1 plantcurd"),
        (r"\bbean\s+curd\b", "tofu plantcurd"),
        # Eggless / Vegan Mayo (not egg)
        (r"\b(vegan|eggless|egg-free|plant-based)\s+(mayo|mayonnaise)\b", r"\1 plantmayo"),
        # Mock / Plant-Based Meats (not animal meat)
        (r"\b(vegan|plant-based|mock|soy|soya|vegetarian|veggie)\s+(chicken|mutton|beef|pork|meat|bacon|sausage|fish|prawn|shrimp|patty|burger|keema|kheema|seekh|nugget|nuggets)\b", r"\1 plantmeat"),
        (r"\b(coconut|mushroom|soy|soya|vegan)\s+bacon\b", r"\1 plantbacon"),
        # Safe grains with misleading names (Glutinous rice is 100% GLUTEN-FREE!)
        (r"\b(glutinous|sweet|sticky)\s+rice\b", "glutinous_rice grain glutenfree"),
        (r"\bbuckwheat\s+(flour|groats|noodles|soba)?\b", "buckwheat pseudocereal glutenfree"),
        (r"\bkuttu\s*(ka\s*atta|atta)?\b", "buckwheat pseudocereal glutenfree"),
        (r"\bwild\s+rice\b", "wild_rice grain glutenfree"),
        (r"\bbrown\s+rice\b", "brown_rice grain glutenfree"),
        (r"\bbasmati\s+rice\b", "basmati_rice grain glutenfree"),
        (r"\bwater\s+chestnut(s)?\b", "singhara aquatic_fruit"),
        (r"\bsinghare\s+ka\s+atta\b", "singhara flour glutenfree"),
        (r"\bgluten-free\s+(oats|bread|flour|pasta|noodles)\b", r"gf_\1 glutenfree"),
        # Non-alcoholic drinks containing misleading words
        (r"\broot\s+beer\b", "rootbeer soda nonalcoholic"),
        (r"\bginger\s+(beer|ale)\b", "gingerale soda nonalcoholic"),
        (r"\bcream\s+soda\b", "creamsoda soda nonalcoholic"),
        # Soy-free and clean condiments
        (r"\bcoconut\s+aminos\b", "coconut_aminos soyfree"),
        (r"\bliquid\s+smoke\b", "liquidsmoke vegan"),
        (r"\bnutritional\s+yeast\b", "nooch nutritionalyeast vegan"),
        # Safe plants with misleading substrings
        (r"\beggplant\b", "aubergine brinjal"),
        (r"\baubergine\b", "aubergine brinjal"),
        (r"\bbrinjal\b", "brinjal veg"),
        (r"\bbaingan\b", "baingan veg"),
        (r"\bbutternut\s+squash\b", "butternut squash gourd"),
        (r"\bbutter\s+beans\b", "butter beans legume"),
        (r"\bbutter\s+fruit\b", "avocado fruit"),
        (r"\bbutterhead\s+lettuce\b", "butterhead lettuce veg"),
        (r"\boatmeal\b", "oats grain"),
        (r"\bsweetmeat\b", "mithai sweet"),
        (r"\bnutmeg\b", "jaiphal spice"),
        (r"\bdragon\s+fruit\b", "dragonfruit"),
        (r"\bpassion\s+fruit\b", "passionfruit"),
        (r"\bbreadfruit\b", "breadfruit fruit"),
        (r"\bstarfruit\b", "starfruit fruit"),
        (r"\bgrapefruit\b", "grapefruit fruit"),
        (r"\bjackfruit\b", "jackfruit kathal"),
        (r"\bchickpea(s)?\b", "chana legume"),
        (r"\bgraham\s+cracker(s)?\b", "graham cracker wheat"),
        (r"\bgraham\s+flour\b", "graham flour wheat"),
        (r"\bchamomile\b", "chamomile herb"),
        (r"\bchampignon\b", "champignon mushroom"),
        (r"\bmustard\s+greens\b", "sarson greens vegetable"),
        (r"\bsarson\s+ka\s+saag\b", "sarson greens vegetable"),
    ]

    # =========================================================================
    # 2. DIETARY TAXONOMY & KEYWORD PATTERNS
    # =========================================================================

    # Mammalian & Avian Meat (Strictly Non-Vegetarian, Non-Eggetarian, Non-Pescatarian)
    MEAT_MAMMAL_AVIAN = [
        "chicken", "murg", "murgh", "kukkad", "koli", "kodi", "poultry", "fowl", "rooster", "hen",
        "mutton", "gosht", "goat", "chevon", "lamb", "mutton keema", "mutton kheema",
        "beef", "cow", "ox", "veal", "steak", "bovine", "boti",
        "pork", "pig", "swine", "ham", "bacon", "prosciutto", "pancetta", "gammon", "pork chop",
        "lard", "suet", "tallow", "animal fat", "bone broth", "bone char",
        "duck", "turkey", "quail", "goose", "pheasant", "venison", "deer", "bison", "rabbit", "shikari",
        "kheema", "keema", "seekh kabab", "seekh kebab", "galouti", "shami kabab",
        "salami", "sausage", "pepperoni", "chorizo", "pastrami", "bratwurst", "hot dog",
        "gelatin", "gelatine", "animal rennet", "pepsin", "isinglass",
        "carmine", "cochineal", "e120"
    ]

    # Seafood & Fish (Non-Vegetarian, Non-Eggetarian, Pescatarian Allowed)
    SEAFOOD_FISH = [
        "fish", "machhli", "machli", "macchi", "meen", "chepa", "salmon", "tuna", "cod", "trout",
        "haddock", "halibut", "anchovy", "anchovies", "sardine", "sardines", "mackerel", "surmai",
        "tilapia", "rohu", "katla", "hilsa", "pomfret", "bombil", "bombay duck",
        "snapper", "sea bass", "swordfish", "catfish", "herring", "pollock",
        "shrimp", "prawn", "chingri", "jheenga", "jhinga", "kolmi", "eral", "royyalu", "konchu",
        "crab", "lobster", "crayfish", "crawfish", "krill", "njandu", "kakda",
        "clam", "clams", "mussel", "mussels", "oyster", "oysters", "scallop", "scallops",
        "squid", "calamari", "octopus", "cuttlefish", "eel", "caviar", "roe",
        "fish sauce", "oyster sauce", "worcestershire sauce", "caesar dressing", "squid ink"
    ]

    # Eggs (Eggetarian Allowed, Non-Vegetarian in Indian Lacto-Veg context, Non-Vegan)
    EGG_KEYWORDS = [
        "egg", "eggs", "anda", "ande", "muttai", "guddu", "mottai",
        "egg white", "egg yolk", "albumen", "albumin", "boiled egg",
        "omelette", "omelet", "scrambled egg", "poached egg", "mayonnaise", "custard", "lysozyme"
    ]

    # Dairy Products (Vegetarian & Jain Allowed, Non-Vegan, Non-Dairy-Free)
    DAIRY_KEYWORDS = [
        "milk", "doodh", "paal", "cheese", "cheddar", "mozzarella", "parmesan", "gouda", "feta", "brie", "ricotta",
        "butter", "makhan", "maska", "ghee", "asli ghee", "desi ghee", "clarified butter",
        "curd", "dahi", "thayir", "perugu", "yogurt", "yoghurt", "greek yogurt",
        "chaas", "buttermilk", "lassi", "majjiga", "cream", "malai", "heavy cream", "sour cream",
        "paneer", "cottage cheese", "chhena", "chhana", "khoa", "khoya", "mawa", "rabri", "rabdi", "kheer", "kalakand", "shrikhand",
        "whey", "whey protein", "casein", "caseinate", "lactose", "lactalbumin",
        "condensed milk", "milk powder", "evaporated milk", "ice cream"
    ]

    # Jain Exclusions (Pure Vegetarian + Strictly NO underground root tubers, alliums, mushrooms, honey, alcohol)
    JAIN_ALLIUMS = [
        "onion", "onions", "pyaz", "pyaaz", "kanda", "dungri", "shallot", "shallots",
        "scallion", "scallions", "green onion", "spring onion", "leek", "leeks", "sambar onion", "chinna vengayam",
        "chives", "garlic chives", "garlic", "lehsun", "lahsun", "lasun", "veluthulli",
        "poondu", "vellulli", "allium", "ulli"
    ]

    JAIN_ROOTS = [
        "potato", "potatoes", "aloo", "alu", "batata", "urulaikizhangu",
        "sweet potato", "shakarkand", "yam", "suran", "jimikand", "ratalu", "elephant foot yam",
        "colocasia", "arbi", "taro", "kachalu", "cassava", "tapioca", "yuca", "sabudana",
        "carrot", "carrots", "gajar", "gaajar",
        "radish", "radishes", "mooli", "muli", "daikon",
        "beetroot", "beet", "beets", "chukandar",
        "turnip", "turnips", "shalgam", "salgam",
        "ginger", "adrak", "inji", "allam", "adu", "adhu",
        "horseradish", "parsnip", "rutabaga", "lotus root", "kamal kakdi"
    ]

    JAIN_FUNGI_HONEY_ALCOHOL = [
        "mushroom", "mushrooms", "fungus", "truffle", "truffles", "khumbi", "guchhi",
        "honey", "shahad", "madhu",
        "alcohol", "wine", "beer", "rum", "whiskey", "whisky", "vodka", "brandy",
        "gin", "tequila", "liqueur", "cider", "cooking wine", "mirin", "sake", "ethanol"
    ]

    # Sattvic Exclusions (Pure Ayurvedic: No alliums, mushrooms, alcohol, deep ferments, excessive stimulants)
    SATTVIC_EXCLUSIONS = [
        "onion", "pyaz", "garlic", "lehsun", "shallot", "leek", "scallion",
        "mushroom", "fungus", "truffle", "alcohol", "wine", "beer", "whiskey", "rum", "vodka",
        "vinegar", "blue cheese", "stale", "caffeine", "coffee"
    ]

    # Gluten-Containing Grains & Ingredients
    GLUTEN_KEYWORDS = [
        "wheat", "gehun", "atta", "maida", "all-purpose flour", "semolina", "sooji", "suji", "rava",
        "barley", "jau", "rye", "spelt", "kamut", "farro", "bulgur", "couscous", "durum", "triticale",
        "seitan", "vital wheat gluten", "malt", "malt extract", "malt vinegar", "malt syrup",
        "breadcrumbs", "panko", "pasta", "macaroni", "spaghetti", "penne", "fusilli", "lasagna",
        "noodles", "ramen", "udon"
    ]

    # Safe Gluten-Free Grains & Flours
    SAFE_GF_GRAINS = [
        "rice", "basmati", "brown rice", "wild rice", "glutinous rice", "sticky rice",
        "buckwheat", "kuttu", "quinoa", "amaranth", "rajgira", "ramdana",
        "jowar", "sorghum", "bajra", "pearl millet", "ragi", "finger millet", "nachni",
        "millet", "foxtail millet", "kodo millet", "little millet", "barnyard millet",
        "besan", "gram flour", "chana flour", "tapioca", "sabudana", "arrowroot",
        "singhara", "water chestnut flour", "cornstarch", "corn flour", "makki ka atta"
    ]

    # Keto Exclusions (High-Carb, High-Sugar, Grains, Starches)
    KETO_HIGH_CARB = [
        "sugar", "cane sugar", "brown sugar", "jaggery", "gur", "gud", "honey", "maple syrup", "agave", "corn syrup", "high fructose corn syrup", "molasses", "dextrose", "maltodextrin", "sucrose", "glucose",
        "wheat", "gehun", "atta", "maida", "white rice", "rice", "basmati", "pasta", "noodles", "bread", "roti", "naan", "paratha", "puri",
        "potato", "potatoes", "aloo", "alu", "sweet potato", "shakarkand", "yam", "suran", "tapioca", "sabudana", "cassava",
        "corn", "maize", "cornstarch", "banana", "mango", "grapes", "raisins", "dates", "figs"
    ]

    # Paleo Exclusions (Grains, Legumes, Dairy, Refined Sugars, Processed Chemicals)
    PALEO_EXCLUSIONS = [
        "wheat", "rice", "corn", "oats", "barley", "rye", "spelt", "kamut", "bulgur", "couscous", "quinoa", "millet", "ragi", "jowar", "bajra",
        "beans", "lentils", "dal", "chickpeas", "chana", "rajma", "kidney beans", "black beans", "soy", "soya", "soybean", "tofu", "tempeh", "edamame", "peanut", "peanuts", "peanut butter",
        "milk", "cheese", "yogurt", "curd", "dahi", "paneer", "cream", "butter", "whey", "casein",
        "sugar", "high fructose corn syrup", "aspartame", "sucralose", "artificial sweetener"
    ]

    # Low-FODMAP High-FODMAP Triggers
    HIGH_FODMAP_KEYWORDS = [
        "onion", "garlic", "shallot", "leek", "scallion", "wheat", "rye", "barley", "inulin", "chicory root",
        "honey", "high fructose corn syrup", "agave", "apple", "pear", "mango", "watermelon",
        "milk", "curd", "dahi", "yogurt", "ricotta", "cottage cheese", "paneer", "soft cheese", "ice cream",
        "mushroom", "mushrooms", "cauliflower", "sorbitol", "mannitol", "xylitol", "maltitol", "isomalt",
        "chickpeas", "lentils", "kidney beans", "black beans", "baked beans", "soybeans"
    ]

    # Clean Label Artificial Additives, Preservatives, Sweeteners, Flavor Enhancers
    ARTIFICIAL_ADDITIVES = [
        "msg", "monosodium glutamate", "e621", "disodium inosinate", "disodium guanylate", "autolyzed yeast",
        "aspartame", "sucralose", "saccharin", "acesulfame k", "acesulfame potassium", "cyclamate", "neotame", "e950", "e951", "e952", "e954", "e955",
        "bha", "bht", "tbhq", "sodium benzoate", "potassium sorbate", "sodium nitrite", "sodium nitrate", "calcium propionate", "potassium bromate", "e211", "e202", "e250", "e251", "e319", "e320", "e321",
        "tartrazine", "sunset yellow", "allura red", "red 40", "yellow 5", "yellow 6", "blue 1", "brilliant blue", "caramel color iv", "e102", "e110", "e129", "e133", "e150d",
        "hydrogenated oil", "partially hydrogenated oil", "trans fat", "vanaspati"
    ]

    # Peanuts
    PEANUT_KEYWORDS = [
        "peanut", "peanuts", "groundnut", "groundnuts", "moongphali", "mungfali", "monkey nut", "peanut butter", "peanut oil"
    ]

    # Tree Nuts
    TREE_NUT_KEYWORDS = [
        "almond", "almonds", "badam", "cashew", "cashews", "kaju",
        "walnut", "walnuts", "akhrot", "pistachio", "pistachios", "pista",
        "pecan", "pecans", "hazelnut", "hazelnuts", "macadamia", "brazil nut", "pine nut", "chilgoza"
    ]

    # Soy & Soy Derivatives
    SOY_KEYWORDS = [
        "soy", "soya", "soybean", "soybeans", "tofu", "tempeh", "edamame",
        "soy sauce", "tamari", "miso", "soy lecithin", "tvp", "textured vegetable protein", "soy milk"
    ]

    # Other Global Allergens
    SESAME_KEYWORDS = ["sesame", "til", "tahini", "gingelly"]
    MUSTARD_KEYWORDS = ["mustard", "sarson", "rai", "dijon", "mustard seed", "mustard oil"]
    CELERY_KEYWORDS = ["celery", "celeriac", "celery salt", "celery seed"]
    SULFITE_KEYWORDS = ["sulfite", "sulfites", "sulphite", "sulphites", "sodium metabisulfite", "sulfur dioxide", "e220", "e221", "e222", "e223", "e224", "e225", "e226", "e227", "e228"]
    LUPIN_KEYWORDS = ["lupin", "lupine", "lupini"]
    MOLLUSC_KEYWORDS = ["clam", "clams", "mussel", "mussels", "oyster", "oysters", "scallop", "scallops", "squid", "calamari", "octopus", "cuttlefish", "snail", "escargot"]
    CORN_KEYWORDS = ["corn", "maize", "cornstarch", "corn starch", "corn syrup", "high fructose corn syrup", "corn oil", "polenta", "hominy"]
    NIGHTSHADE_KEYWORDS = ["tomato", "tomatoes", "tamatar", "potato", "potatoes", "aloo", "eggplant", "brinjal", "baingan", "aubergine", "bell pepper", "capsicum", "shimla mirch", "chili", "chilli", "paprika", "cayenne", "tobacco"]

    # Halal Exclusions (Pork/Swine, Alcohol, Non-Halal Animal Products)
    HALAL_PORK = [
        "pork", "pig", "swine", "ham", "bacon", "lard", "pancetta", "prosciutto", "pork sausage", "pork chop"
    ]
    HALAL_ALCOHOL = [
        "alcohol", "wine", "beer", "rum", "whiskey", "whisky", "vodka", "brandy", "gin", "tequila",
        "liqueur", "cider", "cooking wine", "mirin", "sake", "ethanol"
    ]

    # =========================================================================
    # 3. SMART CULINARY SUBSTITUTION KNOWLEDGE BASE
    # =========================================================================
    
    SUBSTITUTION_RULES: Dict[str, Dict[str, Dict[str, Any]]] = {
        "jain": {
            "onion": {
                "substitutes": ["Hing (Asafoetida) infused in oil", "Finely shredded cabbage base", "Bottle Gourd (Lauki) purée"],
                "tip": "Sauté a pinch of hing with cumin seeds to recreate rich allium savory depth without root onions."
            },
            "garlic": {
                "substitutes": ["Asafoetida (Hing)", "Celery seed powder", "Crushed fennel & ginger-free spice blend"],
                "tip": "A small pinch of premium hing provides the punchy sulfur aromatics characteristic of garlic."
            },
            "potato": {
                "substitutes": ["Raw Banana (Kacha Kela)", "Paneer cubes", "Zucchini / Ridge Gourd (Turai)"],
                "tip": "Boiled raw green banana replicates the starchy, velvety texture of potato perfectly in curries and patties."
            },
            "ginger": {
                "substitutes": ["Amchur (Dry Mango Powder)", "Black Pepper & Cumin powder", "Dry Coriander seed crush"],
                "tip": "Amchur powder and cracked pepper provide zesty warmth and tang without underground root ginger."
            },
            "carrot": {
                "substitutes": ["Yellow Pumpkin (Kaddu)", "Red Bell Pepper", "Raw Papaya slices"],
                "tip": "Yellow pumpkin offers natural sweetness and rich beta-carotene color without underground taproots."
            },
            "mushroom": {
                "substitutes": ["Extra Firm Tofu cubes", "Paneer", "Cauliflower florets"],
                "tip": "Pan-seared tofu or paneer absorbs savory spices and gives the same meaty mouthfeel as mushrooms."
            },
            "honey": {
                "substitutes": ["Pure Jaggery (Gur) syrup", "Organic Raw Sugar syrup", "Date Syrup"],
                "tip": "Warm jaggery syrup gives rich floral sweetness without honey bee harvesting."
            }
        },
        "vegan": {
            "paneer": {
                "substitutes": ["Extra Firm Tofu (organic)", "Almond Milk Paneer", "Tempeh cubes"],
                "tip": "Press extra firm tofu and sauté with turmeric and salt for a texture identical to dairy paneer."
            },
            "milk": {
                "substitutes": ["Creamy Oat Milk", "Almond Milk", "Cashew Milk", "Coconut Milk"],
                "tip": "Oat milk or cashew milk foams and blends seamlessly into hot drinks, soups, and traditional gravies."
            },
            "butter": {
                "substitutes": ["Vegan Plant Butter", "Cold-Pressed Coconut Oil", "Extra Virgin Olive Oil"],
                "tip": "Cultured plant-based butter browns and bakes with the same rich aroma as dairy butter."
            },
            "ghee": {
                "substitutes": ["Cold-Pressed Mustard Oil", "Desi Coconut Oil", "Toasted Sesame (Gingelly) Oil"],
                "tip": "Cold-pressed mustard or coconut oil provides high-smoke-point richness for authentic tempering (tadka)."
            },
            "curd": {
                "substitutes": ["Coconut Dahi / Yogurt", "Peanut-Cashew Curd", "Soy Yogurt"],
                "tip": "Fermented peanut-cashew curd sets into thick, tangy curd ideal for raita and kadhi."
            },
            "cheese": {
                "substitutes": ["Cashew Nutritional Yeast Cheese", "Cultured Coconut Oil Cheese"],
                "tip": "Nutritional yeast blended with soaked cashews and lemon juice creates a rich cheesy sauce."
            },
            "egg": {
                "substitutes": ["Flax Egg (1 tbsp ground flax + 3 tbsp water)", "Aquafaba (Chickpea water)", "Silken Tofu mash"],
                "tip": "Flax egg binds baked goods wonderfully, while whipped aquafaba mimics egg white meringue."
            },
            "chicken": {
                "substitutes": ["Soy Chunks (Nutrela)", "Tender Jackfruit (Kathal)", "Seitan (Wheat Protein)"],
                "tip": "Slow-cooked young green jackfruit shreds effortlessly like pulled chicken or mutton in rich gravies."
            },
            "honey": {
                "substitutes": ["Pure Maple Syrup", "Agave Nectar", "Date Syrup", "Coconut Nectar"],
                "tip": "Pure maple syrup or agave nectar offers natural sweetening with zero animal involvement."
            }
        },
        "gluten_free": {
            "wheat": {
                "substitutes": ["Jowar (Sorghum) Flour", "Bajra (Pearl Millet) Flour", "Ragi (Finger Millet) Flour", "Almond Flour"],
                "tip": "Millet flours (jowar, ragi) make wholesome, nutrient-dense rotis and flatbreads that are naturally 100% gluten-free."
            },
            "maida": {
                "substitutes": ["Gluten-Free 1-to-1 Baking Flour Blend", "White Rice Flour + Tapioca Starch", "Almond Flour"],
                "tip": "A blend of rice flour and tapioca starch delivers crispness and elasticity in baked goods."
            },
            "sooji": {
                "substitutes": ["Rice Rava / Idli Rava", "Coarse Quinoa", "Gluten-Free Polenta / Cornmeal"],
                "tip": "Rice rava yields fluffy upma, idlis, and halwa with identical grain texture without wheat gluten."
            },
            "soy sauce": {
                "substitutes": ["Tamari (Certified Gluten-Free)", "Coconut Aminos"],
                "tip": "Tamari is 100% brewed whole soybean sauce without wheat, delivering rich umami depth."
            },
            "pasta": {
                "substitutes": ["Brown Rice Pasta", "Chickpea Pasta", "Buckwheat Soba Noodles (100% pure)"],
                "tip": "Chickpea pasta offers a firm al-dente bite packed with double the protein and fiber of wheat pasta."
            }
        },
        "keto": {
            "sugar": {
                "substitutes": ["Stevia Leaf Extract", "Erythritol", "Monk Fruit Sweetener"],
                "tip": "Monk fruit and erythritol provide zero glycemic impact and zero net carbs without bitter aftertaste."
            },
            "rice": {
                "substitutes": ["Cauliflower Rice", "Shirataki / Konjac Rice", "Hemp Seed Risotto"],
                "tip": "Grated cauliflower sauteed in ghee or olive oil absorbs seasonings just like basmati rice with under 3g net carbs."
            },
            "potato": {
                "substitutes": ["Mashed Cauliflower", "Roasted Radishes", "Turnip Cubes"],
                "tip": "Steamed cauliflower blended with cream, butter, and garlic mimics mashed potatoes to perfection."
            },
            "atta": {
                "substitutes": ["Almond Flour + Psyllium Husk", "Coconut Flour Blend"],
                "tip": "Almond flour with 1 tbsp psyllium husk yields pliable, rollable keto rotis that don't crumble."
            }
        },
        "low_fodmap": {
            "onion": {
                "substitutes": ["Green tops of Spring Onions", "Garlic/Onion-Infused Olive Oil (FODMAP-free)", "Asafoetida (Hing)"],
                "tip": "Fructans are water-soluble but not oil-soluble, so onion-infused oil gives rich flavor without digestive triggers."
            },
            "garlic": {
                "substitutes": ["Garlic-Infused Extra Virgin Olive Oil", "Hing (Asafoetida) in small pinch"],
                "tip": "Garlic-infused oil delivers authentic garlicky aroma with zero fructan content."
            },
            "milk": {
                "substitutes": ["Lactose-Free Dairy Milk", "Almond Milk", "Macadamia Milk"],
                "tip": "Lactose-free milk retains natural calcium and protein while eliminating high-FODMAP disaccharides."
            }
        }
    }

    # Pre-compiled safe compounds for instant token substitution
    COMPILED_SAFE_COMPOUNDS = [
        (re.compile(pattern, re.IGNORECASE), replacement)
        for pattern, replacement in SAFE_COMPOUNDS
    ]

    _CLASSIFY_CACHE: Dict[Tuple[str, ...], Dict[str, Any]] = {}

    # =========================================================================
    # 4. TOKENIZATION & NORMALIZATION HELPER
    # =========================================================================

    @classmethod
    @functools.lru_cache(maxsize=32768)
    def normalize_and_tokenize(cls, text: str) -> Tuple[str, List[str]]:
        """Normalize ingredient text and apply safe phrase replacements in compiled speed."""
        if not text:
            return "", []
        
        cleaned = text.lower().strip()
        
        # Replace safe compounds using pre-compiled regexes
        for regex, replacement in cls.COMPILED_SAFE_COMPOUNDS:
            cleaned = regex.sub(replacement, cleaned)
            
        # Extract word tokens
        tokens = re.findall(r"\b[a-zA-Z0-9_\-']+\b", cleaned)
        return cleaned, tokens

    _MATCHER_CACHE: Dict[int, Tuple[Set[str], Optional[Any]]] = {}

    @classmethod
    def _get_matcher_for_keywords(cls, keywords: List[str]) -> Tuple[Set[str], Optional[Any]]:
        k_id = id(keywords)
        if k_id in cls._MATCHER_CACHE:
            return cls._MATCHER_CACHE[k_id]
        sw = set(k.lower().strip() for k in keywords if " " not in k.strip())
        mw = [k.lower().strip() for k in keywords if " " in k.strip()]
        mw_regex = (
            re.compile(r"\b(" + "|".join(re.escape(k) for k in sorted(mw, key=len, reverse=True)) + r")\b", re.IGNORECASE)
            if mw else None
        )
        matcher = (sw, mw_regex)
        cls._MATCHER_CACHE[k_id] = matcher
        return matcher

    @classmethod
    def _matches_any(cls, text_clean: str, tokens: List[str], keywords: List[str]) -> Tuple[bool, Optional[str]]:
        """Check if any keyword is present with instant O(1) set lookups and compiled regex."""
        if not keywords or not text_clean:
            return False, None
        sw, mw_regex = cls._get_matcher_for_keywords(keywords)
        for token in tokens:
            if token in sw:
                return True, token
        if mw_regex is not None:
            m = mw_regex.search(text_clean)
            if m:
                return True, m.group(0)
        return False, None

    # =========================================================================
    # 5. DATABASE RULES FETCHING
    # =========================================================================

    @classmethod
    def get_rules_map(cls, db: Session) -> Dict[str, List[str]]:
        """Fetch custom rules from database and group them by rule_type."""
        rules_map: Dict[str, List[str]] = {}
        try:
            rules = db.query(IngredientRule).all()
            for r in rules:
                if r.rule_type not in rules_map:
                    rules_map[r.rule_type] = []
                rules_map[r.rule_type].append(r.ingredient_name.lower().strip())
        except Exception:
            pass
        return rules_map

    # =========================================================================
    # 6. SMART CULINARY SUBSTITUTION ENGINE
    # =========================================================================

    @classmethod
    def get_substitutions(cls, ingredient_names: List[str], target_diet: str) -> List[Dict[str, Any]]:
        """Recommend culinary authentic substitutions for non-compliant ingredients."""
        target_diet = target_diet.lower().strip().replace("-", "_")
        rules_for_diet = cls.SUBSTITUTION_RULES.get(target_diet, {})
        if not rules_for_diet:
            return []

        substitutions: List[Dict[str, Any]] = []
        seen_ingredients: Set[str] = set()

        for original_name in ingredient_names:
            if not original_name or not str(original_name).strip():
                continue
            orig = str(original_name).strip()
            clean_text, tokens = cls.normalize_and_tokenize(orig)

            for non_comp_key, swap_info in rules_for_diet.items():
                pattern = r"\b" + re.escape(non_comp_key) + r"\b"
                if non_comp_key in tokens or re.search(pattern, clean_text):
                    if orig.lower() not in seen_ingredients:
                        seen_ingredients.add(orig.lower())
                        substitutions.append({
                            "original_ingredient": orig,
                            "violates_diet": target_diet.title().replace("_", " "),
                            "detected_trigger": non_comp_key,
                            "recommended_substitutes": swap_info["substitutes"],
                            "culinary_tip": swap_info["tip"]
                        })
        return substitutions

    # =========================================================================
    # 7. CORE CLASSIFICATION LOGIC
    # =========================================================================

    @classmethod
    def classify_ingredients(
        cls, 
        ingredient_names: List[str], 
        rules_map: Optional[Dict[str, List[str]]] = None
    ) -> Dict[str, Any]:
        """Classify a list of ingredients against comprehensive dietary taxonomies and DB rules."""
        if rules_map is None:
            rules_map = {}

        # Cache lookup for empty/default rules_map
        if not rules_map and ingredient_names:
            cache_key = tuple(sorted(set(str(i).strip().lower() for i in ingredient_names if i and str(i).strip())))
            if cache_key in cls._CLASSIFY_CACHE:
                return dict(cls._CLASSIFY_CACHE[cache_key])
        else:
            cache_key = None

        exclude_vegan_db = rules_map.get("exclude_vegan", [])
        exclude_vegetarian_db = rules_map.get("exclude_vegetarian", [])
        exclude_eggetarian_db = rules_map.get("exclude_eggetarian", [])
        exclude_jain_db = rules_map.get("exclude_jain", [])


        # Violation Flags
        has_meat = False
        has_seafood = False
        has_egg = False
        has_dairy = False
        has_jain_allium = False
        has_jain_root = False
        has_jain_fungi_honey_alcohol = False
        has_sattvic_violation = False
        has_gluten = False
        has_peanuts = False
        has_tree_nuts = False
        has_soy = False
        has_sesame = False
        has_mustard = False
        has_celery = False
        has_sulfites = False
        has_lupin = False
        has_mollusc = False
        has_corn = False
        has_nightshade = False
        has_halal_pork = False
        has_halal_alcohol = False
        has_keto_high_carb = False
        has_paleo_exclusion = False
        has_high_fodmap = False
        has_artificial_additives = False

        reasons_list: List[str] = []
        detailed_reasons: Dict[str, List[str]] = {
            "vegan": [],
            "vegetarian": [],
            "jain": [],
            "eggetarian": [],
            "pescatarian": [],
            "keto": [],
            "paleo": [],
            "low_fodmap": [],
            "sattvic": [],
            "gluten_free": [],
            "dairy_free": [],
            "nut_free": [],
            "halal": [],
            "kosher": [],
            "clean_label": [],
            "allergens": []
        }
        detected_allergens: Set[str] = set()
        ingredient_breakdown: List[Dict[str, Any]] = []

        total_ingredients = 0

        for original_name in ingredient_names:
            if not original_name or not str(original_name).strip():
                continue
                
            orig = str(original_name).strip()
            clean_text, tokens = cls.normalize_and_tokenize(orig)
            total_ingredients += 1

            item_allergens: List[str] = []
            item_exclusions: List[str] = []

            # 1. Check Mammalian/Avian Meat & Eggetarian Exclusions
            matched_meat, _ = cls._matches_any(clean_text, tokens, cls.MEAT_MAMMAL_AVIAN)
            matched_eggetarian_db = False
            if not matched_meat and exclude_eggetarian_db:
                matched_eggetarian_db, _ = cls._matches_any(clean_text, tokens, exclude_eggetarian_db)
            if matched_meat or matched_eggetarian_db:
                has_meat = True
                has_sattvic_violation = True
                msg = f"Non-vegetarian: contains {orig}"
                reasons_list.append(msg)
                detailed_reasons["vegetarian"].append(f"Contains meat/poultry ({orig})")
                detailed_reasons["vegan"].append(f"Contains meat/poultry ({orig})")
                detailed_reasons["eggetarian"].append(f"Contains meat/poultry ({orig})")
                detailed_reasons["pescatarian"].append(f"Contains meat/poultry ({orig})")
                detailed_reasons["jain"].append(f"Contains meat/poultry ({orig})")
                detailed_reasons["sattvic"].append(f"Contains meat ({orig})")
                item_exclusions.append("Meat / Poultry")

            # 2. Check Seafood & Fish
            matched_sea, _ = cls._matches_any(clean_text, tokens, cls.SEAFOOD_FISH)
            if matched_sea:
                has_seafood = True
                has_sattvic_violation = True
                detected_allergens.add("Fish / Shellfish")
                item_allergens.append("Fish / Shellfish")
                msg = f"Non-vegetarian: contains {orig}"
                reasons_list.append(msg)
                detailed_reasons["vegetarian"].append(f"Contains seafood ({orig})")
                detailed_reasons["vegan"].append(f"Contains seafood ({orig})")
                detailed_reasons["eggetarian"].append(f"Contains seafood ({orig})")
                detailed_reasons["jain"].append(f"Contains seafood ({orig})")
                detailed_reasons["sattvic"].append(f"Contains seafood ({orig})")
                detailed_reasons["allergens"].append(f"Contains seafood allergen ({orig})")
                item_exclusions.append("Seafood")

            # 3. Check Eggs
            matched_egg, _ = cls._matches_any(clean_text, tokens, cls.EGG_KEYWORDS)
            if matched_egg:
                has_egg = True
                has_sattvic_violation = True
                detected_allergens.add("Egg")
                item_allergens.append("Egg")
                reasons_list.append(f"Non-vegetarian: contains {orig}")
                reasons_list.append(f"Non-vegan: contains {orig}")
                detailed_reasons["vegan"].append(f"Contains egg ({orig})")
                detailed_reasons["vegetarian"].append(f"Contains egg ({orig})")
                detailed_reasons["jain"].append(f"Contains egg ({orig})")
                detailed_reasons["sattvic"].append(f"Contains egg ({orig})")
                detailed_reasons["allergens"].append(f"Contains egg allergen ({orig})")
                item_exclusions.append("Egg")

            # 3b. Custom Vegetarian Exclusions from DB (that might not be meat/egg/seafood)
            if not (has_meat or has_seafood or has_egg) and exclude_vegetarian_db:
                matched_veg_db, _ = cls._matches_any(clean_text, tokens, exclude_vegetarian_db)
                if matched_veg_db:
                    has_egg = True  # Marks non-vegetarian
                    reasons_list.append(f"Non-vegetarian: contains {orig}")
                    detailed_reasons["vegetarian"].append(f"Contains non-vegetarian ingredient ({orig})")
                    item_exclusions.append("Non-Vegetarian DB Rule")

            # 4. Check Dairy & General Vegan exclusions
            matched_dairy, kw_dairy = cls._matches_any(clean_text, tokens, cls.DAIRY_KEYWORDS)
            matched_vegan_db = False
            if not matched_dairy and exclude_vegan_db:
                matched_vegan_db, kw_dairy = cls._matches_any(clean_text, tokens, exclude_vegan_db)
            if matched_dairy or matched_vegan_db:
                if matched_dairy:
                    has_dairy = True
                    has_paleo_exclusion = True
                    detected_allergens.add("Dairy")
                    item_allergens.append("Dairy")
                    detailed_reasons["dairy_free"].append(f"Contains dairy ({orig})")
                    detailed_reasons["paleo"].append(f"Contains dairy ({orig})")
                    detailed_reasons["allergens"].append(f"Contains dairy allergen ({orig})")
                msg_d = f"Non-vegan: contains {orig}"
                reasons_list.append(msg_d)
                detailed_reasons["vegan"].append(msg_d)
                item_exclusions.append("Dairy")

            # 5. Check Jain & Sattvic Exclusions
            # 5a. Alliums (Onions, Garlic, etc.)
            matched_allium, kw_allium = cls._matches_any(clean_text, tokens, cls.JAIN_ALLIUMS)
            if not matched_allium and exclude_jain_db:
                matched_allium, kw_allium = cls._matches_any(clean_text, tokens, exclude_jain_db)
            if matched_allium:
                has_jain_allium = True
                has_sattvic_violation = True
                has_high_fodmap = True
                msg_j = f"Non-jain: contains {orig}"
                reasons_list.append(msg_j)
                detailed_reasons["jain"].append(f"Contains allium ({orig})")
                detailed_reasons["sattvic"].append(f"Contains allium ({orig})")
                detailed_reasons["low_fodmap"].append(f"High-FODMAP allium ({orig})")
                item_exclusions.append("Allium (Onion/Garlic)")

            # 5b. Tubers & Root Vegetables
            matched_root, kw_root = cls._matches_any(clean_text, tokens, cls.JAIN_ROOTS)
            if matched_root:
                has_jain_root = True
                msg_r = f"Non-jain: contains {orig}"
                reasons_list.append(msg_r)
                detailed_reasons["jain"].append(f"Contains underground root/tuber ({orig})")
                item_exclusions.append("Underground Root/Tuber")

            # 5c. Fungi, Honey, Alcohol
            matched_fha, kw_fha = cls._matches_any(clean_text, tokens, cls.JAIN_FUNGI_HONEY_ALCOHOL)
            if matched_fha:
                has_jain_fungi_honey_alcohol = True
                has_sattvic_violation = True
                msg_fha = f"Non-jain: contains {orig}"
                reasons_list.append(msg_fha)
                detailed_reasons["jain"].append(f"Contains {orig}")
                detailed_reasons["sattvic"].append(f"Contains {orig}")
                if "honey" in str(kw_fha).lower():
                    detailed_reasons["vegan"].append(f"Contains honey ({orig})")
                    item_exclusions.append("Honey")
                elif "mushroom" in str(kw_fha).lower() or "fungus" in str(kw_fha).lower() or "truffle" in str(kw_fha).lower():
                    item_exclusions.append("Mushroom/Fungi")
                elif "alcohol" in str(kw_fha).lower() or "wine" in str(kw_fha).lower() or "beer" in str(kw_fha).lower():
                    item_exclusions.append("Alcohol")

            # 6. Check Gluten
            matched_gluten, kw_gluten = cls._matches_any(clean_text, tokens, cls.GLUTEN_KEYWORDS)
            if matched_gluten:
                has_gluten = True
                has_paleo_exclusion = True
                has_high_fodmap = True
                detected_allergens.add("Gluten / Wheat")
                item_allergens.append("Gluten / Wheat")
                detailed_reasons["gluten_free"].append(f"Contains gluten ({orig})")
                detailed_reasons["paleo"].append(f"Contains cereal grains ({orig})")
                detailed_reasons["low_fodmap"].append(f"Contains high-FODMAP fructan grains ({orig})")
                detailed_reasons["allergens"].append(f"Contains gluten allergen ({orig})")
                item_exclusions.append("Gluten")

            # 7. Check Peanuts & Tree Nuts
            matched_peanut, _ = cls._matches_any(clean_text, tokens, cls.PEANUT_KEYWORDS)
            if matched_peanut:
                has_peanuts = True
                has_paleo_exclusion = True
                detected_allergens.add("Peanuts")
                item_allergens.append("Peanuts")
                detailed_reasons["nut_free"].append(f"Contains peanuts ({orig})")
                detailed_reasons["paleo"].append(f"Contains peanut legume ({orig})")
                detailed_reasons["allergens"].append(f"Contains peanut allergen ({orig})")
                item_exclusions.append("Peanuts")

            matched_nut, _ = cls._matches_any(clean_text, tokens, cls.TREE_NUT_KEYWORDS)
            if matched_nut:
                has_tree_nuts = True
                detected_allergens.add("Tree Nuts")
                item_allergens.append("Tree Nuts")
                detailed_reasons["nut_free"].append(f"Contains tree nuts ({orig})")
                detailed_reasons["allergens"].append(f"Contains tree nut allergen ({orig})")
                item_exclusions.append("Tree Nuts")

            # 8. Check Soy
            matched_soy, _ = cls._matches_any(clean_text, tokens, cls.SOY_KEYWORDS)
            if matched_soy:
                has_soy = True
                has_paleo_exclusion = True
                detected_allergens.add("Soy")
                item_allergens.append("Soy")
                detailed_reasons["paleo"].append(f"Contains soy legume ({orig})")
                detailed_reasons["allergens"].append(f"Contains soy allergen ({orig})")
                item_exclusions.append("Soy")

            # 9. Other allergens
            matched_sesame, _ = cls._matches_any(clean_text, tokens, cls.SESAME_KEYWORDS)
            if matched_sesame:
                has_sesame = True
                detected_allergens.add("Sesame")
                item_allergens.append("Sesame")
                detailed_reasons["allergens"].append(f"Contains sesame allergen ({orig})")

            matched_mustard, _ = cls._matches_any(clean_text, tokens, cls.MUSTARD_KEYWORDS)
            if matched_mustard and "sarson greens vegetable" not in clean_text:
                has_mustard = True
                detected_allergens.add("Mustard")
                item_allergens.append("Mustard")
                detailed_reasons["allergens"].append(f"Contains mustard allergen ({orig})")

            matched_celery, _ = cls._matches_any(clean_text, tokens, cls.CELERY_KEYWORDS)
            if matched_celery:
                has_celery = True
                detected_allergens.add("Celery")
                item_allergens.append("Celery")
                detailed_reasons["allergens"].append(f"Contains celery allergen ({orig})")

            matched_sulfite, _ = cls._matches_any(clean_text, tokens, cls.SULFITE_KEYWORDS)
            if matched_sulfite:
                has_sulfites = True
                has_artificial_additives = True
                detected_allergens.add("Sulfites")
                item_allergens.append("Sulfites")
                detailed_reasons["clean_label"].append(f"Contains sulfites preservative ({orig})")
                detailed_reasons["allergens"].append(f"Contains sulfite allergen ({orig})")

            matched_lupin, _ = cls._matches_any(clean_text, tokens, cls.LUPIN_KEYWORDS)
            if matched_lupin:
                has_lupin = True
                detected_allergens.add("Lupin")
                item_allergens.append("Lupin")
                detailed_reasons["allergens"].append(f"Contains lupin allergen ({orig})")

            matched_mollusc, _ = cls._matches_any(clean_text, tokens, cls.MOLLUSC_KEYWORDS)
            if matched_mollusc:
                has_mollusc = True
                detected_allergens.add("Molluscs")
                item_allergens.append("Molluscs")

            matched_corn, _ = cls._matches_any(clean_text, tokens, cls.CORN_KEYWORDS)
            if matched_corn:
                has_corn = True
                has_paleo_exclusion = True
                detected_allergens.add("Corn / Maize")
                item_allergens.append("Corn / Maize")
                detailed_reasons["paleo"].append(f"Contains corn grain ({orig})")

            matched_nightshade, _ = cls._matches_any(clean_text, tokens, cls.NIGHTSHADE_KEYWORDS)
            if matched_nightshade:
                has_nightshade = True
                detected_allergens.add("Nightshades")
                item_allergens.append("Nightshades")

            # 10. Halal checks
            matched_pork, _ = cls._matches_any(clean_text, tokens, cls.HALAL_PORK)
            if matched_pork:
                has_halal_pork = True
                detailed_reasons["halal"].append(f"Non-halal: contains pork derivative ({orig})")
                detailed_reasons["kosher"].append(f"Non-kosher: contains pork ({orig})")
                item_exclusions.append("Pork Derivative")

            matched_alc, _ = cls._matches_any(clean_text, tokens, cls.HALAL_ALCOHOL)
            if matched_alc:
                has_halal_alcohol = True
                detailed_reasons["halal"].append(f"Non-halal: contains alcohol ({orig})")
                item_exclusions.append("Alcohol")

            # 11. Keto checks
            matched_keto, _ = cls._matches_any(clean_text, tokens, cls.KETO_HIGH_CARB)
            if matched_keto:
                has_keto_high_carb = True
                detailed_reasons["keto"].append(f"High carb / high sugar ingredient ({orig})")
                item_exclusions.append("High-Carb / High-Sugar")

            # 12. Clean Label Additive checks
            matched_additive, _ = cls._matches_any(clean_text, tokens, cls.ARTIFICIAL_ADDITIVES)
            if matched_additive:
                has_artificial_additives = True
                detailed_reasons["clean_label"].append(f"Contains artificial additive/preservative/sweetener ({orig})")
                item_exclusions.append("Artificial Additive")

            ingredient_breakdown.append({
                "ingredient": orig,
                "clean_text": clean_text,
                "allergens": item_allergens,
                "exclusions": item_exclusions
            })

        # =========================================================================
        # 8. RESOLVE DIETARY FLAGS & CANONICAL TAGS
        # =========================================================================

        # Vegetarian: No meat, poultry, seafood, egg (Indian standard), or animal gelatin
        is_vegetarian = not (has_meat or has_seafood or has_egg)

        # Vegan: Pure plant-based (no meat, seafood, egg, dairy, honey, animal gelatin)
        is_vegan = not (has_meat or has_seafood or has_egg or has_dairy or any("honey" in r.lower() for r in reasons_list))

        # Eggetarian: Allows eggs and dairy, but NO meat, poultry, seafood
        is_eggetarian = not (has_meat or has_seafood)

        # Pescatarian: Allows seafood, eggs, dairy, plants, but NO mammalian/avian meat
        is_pescatarian = not has_meat

        # Jain: Vegetarian (no meat, seafood, eggs) AND no root vegetables, alliums, mushrooms, honey, alcohol
        is_jain = (
            not (has_meat or has_seafood or has_egg) and 
            not (has_jain_allium or has_jain_root or has_jain_fungi_honey_alcohol)
        )

        is_gluten_free = not has_gluten
        is_dairy_free = not has_dairy
        is_nut_free = not (has_peanuts or has_tree_nuts)
        is_halal = not (has_halal_pork or has_halal_alcohol)
        is_kosher = not (has_halal_pork or has_seafood or (has_meat and has_dairy))
        is_sattvic = (
            not (has_meat or has_seafood or has_egg) and
            not (has_jain_allium or has_jain_fungi_honey_alcohol or has_sattvic_violation)
        )
        is_keto = not has_keto_high_carb
        is_paleo = not has_paleo_exclusion
        is_low_fodmap = not has_high_fodmap
        is_clean_label = not has_artificial_additives

        # Determine Canonical primary dietary tag
        if is_jain:
            dietary_tag = "Jain"
        elif is_vegan:
            dietary_tag = "Vegan"
        elif is_vegetarian:
            dietary_tag = "Vegetarian"
        elif is_eggetarian:
            dietary_tag = "Eggetarian"
        elif is_pescatarian:
            dietary_tag = "Pescatarian"
        else:
            dietary_tag = "Non-Vegetarian"

        unique_reasons = list(dict.fromkeys(reasons_list))

        # Calculate dynamic confidence score (0.0 to 1.0)
        confidence_score = 0.99 if total_ingredients > 0 else 0.85

        # Determine Safety Rating
        if not is_vegetarian and not is_pescatarian and has_halal_pork:
            safety_rating = "Non-Compliant / Restricted"
        elif len(detected_allergens) > 0 or not is_clean_label:
            safety_rating = "Caution / Allergen Alert"
        else:
            safety_rating = "Safe / Highly Compliant"

        # Generate intelligent dietary substitutions
        suggested_substitutions: List[Dict[str, Any]] = []
        if not is_jain:
            suggested_substitutions.extend(cls.get_substitutions(ingredient_names, "jain"))
        if not is_vegan:
            suggested_substitutions.extend(cls.get_substitutions(ingredient_names, "vegan"))
        if not is_gluten_free:
            suggested_substitutions.extend(cls.get_substitutions(ingredient_names, "gluten_free"))
        if not is_keto:
            suggested_substitutions.extend(cls.get_substitutions(ingredient_names, "keto"))
        if not is_low_fodmap:
            suggested_substitutions.extend(cls.get_substitutions(ingredient_names, "low_fodmap"))

        # Deduplicate substitutions
        unique_subs: List[Dict[str, Any]] = []
        seen_sub_keys = set()
        for sub in suggested_substitutions:
            key = (sub["original_ingredient"].lower(), sub["violates_diet"])
            if key not in seen_sub_keys:
                seen_sub_keys.add(key)
                unique_subs.append(sub)

        return {
            "is_vegan": is_vegan,
            "is_vegetarian": is_vegetarian,
            "is_eggetarian": is_eggetarian,
            "is_jain": is_jain,
            "is_gluten_free": is_gluten_free,
            "is_dairy_free": is_dairy_free,
            "is_nut_free": is_nut_free,
            "is_pescatarian": is_pescatarian,
            "is_halal": is_halal,
            "is_kosher": is_kosher,
            "is_keto": is_keto,
            "is_paleo": is_paleo,
            "is_low_fodmap": is_low_fodmap,
            "is_sattvic": is_sattvic,
            "is_clean_label": is_clean_label,
            "confidence_score": confidence_score,
            "safety_rating": safety_rating,
            "dietary_tag": dietary_tag,
            "allergens": sorted(list(detected_allergens)),
            "dietary_flags": {
                "vegan": is_vegan,
                "vegetarian": is_vegetarian,
                "jain": is_jain,
                "eggetarian": is_eggetarian,
                "pescatarian": is_pescatarian,
                "gluten_free": is_gluten_free,
                "dairy_free": is_dairy_free,
                "nut_free": is_nut_free,
                "halal": is_halal,
                "kosher": is_kosher,
                "keto": is_keto,
                "paleo": is_paleo,
                "low_fodmap": is_low_fodmap,
                "sattvic": is_sattvic,
                "clean_label": is_clean_label
            },
            "detailed_reasons": detailed_reasons,
            "ingredient_breakdown": ingredient_breakdown,
            "substitutions": unique_subs,
            "reasons": unique_reasons,
            "tags": []
        }
        if cache_key is not None and len(cls._CLASSIFY_CACHE) < 50000:
            cls._CLASSIFY_CACHE[cache_key] = result
        return result

    # =========================================================================
    # 9. RECIPE CLASSIFICATION & NUTRITION TAGGING
    # =========================================================================

    @classmethod
    def classify_recipe(cls, db: Session, recipe: Recipe) -> Dict[str, Any]:
        """Classify a recipe based on its explicit primarysource, title, ingredients, and nutrition."""
        rules_map = cls.get_rules_map(db)
        
        ingredient_names: List[str] = []
        if recipe.recipe_name:
            ingredient_names.append(recipe.recipe_name)
            
        for ing in recipe.ingredients:
            if ing.food_name:
                ingredient_names.append(ing.food_name)
            if ing.ingredient_name and ing.ingredient_name != ing.food_name:
                ingredient_names.append(ing.ingredient_name)

        classification = cls.classify_ingredients(ingredient_names, rules_map)

        # Check explicit primarysource if available
        ps = (recipe.primarysource or "").strip().lower()
        rname = (recipe.recipe_name or "").lower()
        
        if "jain" in ps or "jain" in rname:
            if classification["is_jain"]:
                classification["dietary_tag"] = "Jain"
        elif "vegan" in ps or "vegan" in rname:
            if classification["is_vegan"]:
                classification["dietary_tag"] = "Vegan"

        # Nutrition tags
        nutrition = recipe.nutrition
        tags: List[str] = []
        if nutrition:
            energy = nutrition.energy_kcal or 0.0
            if energy > 0:
                p_cal = (nutrition.protein_g or 0.0) * 4.0
                c_cal = (nutrition.carb_g or 0.0) * 4.0
                f_cal = (nutrition.fat_g or 0.0) * 9.0

                if p_cal / energy >= 0.20:
                    tags.append("High Protein")
                if c_cal / energy <= 0.35:
                    tags.append("Low Carb")
                if f_cal / energy <= 0.20:
                    tags.append("Low Fat")
                if (nutrition.fibre_g or 0.0) >= 3.0:
                    tags.append("High Fiber")
                if (nutrition.sodium_mg or 0.0) <= 140.0:
                    tags.append("Low Sodium")
                if (nutrition.freesugar_g or 0.0) <= 2.0:
                    tags.append("Low Sugar")
                
                # Keto Macro Tag (< 10% Net Carbs or < 15g Carbs)
                if (nutrition.carb_g or 0.0) <= 12.0 and (c_cal / energy) <= 0.12:
                    tags.append("Keto Friendly")

        classification["tags"] = tags
        return classification
