# Dune Awakening Crafting Calculator
# Comprehensive crafting recipes based on official game data

CRAFTING_RECIPES = {
    # === HEALING ITEMS ===
    "healkit": {
        "ingredients": {"plant_fiber": 5},
        "quantity": 1,
        "station": "Inherent Knowledge"
    },
    "healkit_mk2": {
        "ingredients": {"plant_fiber": 10, "micro_sandwich_fabric": 2},
        "quantity": 1,
        "station": "Caves"
    },
    "healkit_mk4": {
        "ingredients": {"water": 85, "plant_fiber": 15, "micro_sandwich_fabric": 4, "off_world_medical_supplies": 1},
        "quantity": 1,
        "station": "Caves"
    },
    "healkit_mk6": {
        "ingredients": {"water": 188, "plant_fiber": 20, "micro_sandwich_fabric": 6, "off_world_medical_supplies": 2},
        "quantity": 1,
        "station": "Caves"
    },
    
    # === MEDICINE ===
    "iodine_pill": {
        "ingredients": {"water": 170, "agave_seeds": 10, "duraluminum_ingot": 1, "spice_ingot": 3},
        "quantity": 1,
        "station": "Arrakis"
    },
    
    # === FOOD & BEVERAGES ===
    "melange_spiced_beer": {
        "ingredients": {"water": 50, "plant_fiber": 10, "spice_sand": 16},
        "quantity": 1,
        "station": "Arrakis"
    },
    "melange_spiced_coffee": {
        "ingredients": {"water": 100, "plant_fiber": 20, "spice_sand": 20},
        "quantity": 1,
        "station": "Arrakis"
    },
    "melange_spiced_food": {
        "ingredients": {"plant_fiber": 10, "spice_sand": 2, "mouse_corpse": 1},
        "quantity": 1,
        "station": "Arrakis"
    },
    
    # === TOOLS ===
    "industrial_dew_scythe_mk4": {
        "ingredients": {"aluminum_ingot": 25, "emf_generator": 10, "silicone_block": 17, "cobalt_paste": 12, "industrial_pump": 5, "water": 225},
        "quantity": 1,
        "station": "Survival Fabricator"
    },
    
    # === ARMOR & GARMENTS ===
    "spice_mask": {
        "ingredients": {"aluminum_ingot": 9, "plant_fiber": 20, "silicone_block": 7, "sandtrout_leathers": 4, "water": 170},
        "quantity": 1,
        "station": "Garment Fabricator"
    },
    "saturnine_stillsuit_garment": {
        "ingredients": {"duraluminum_ingot": 40, "micro_sandwich_fabric": 50, "silicone_block": 90, "stillsuit_tubing": 12, "spice_infused_duraluminum_dust": 17, "water": 675},
        "quantity": 1,
        "station": "Garment Fabricator"
    },
    "desert_garb": {
        "ingredients": {"plastanium_ingot": 45, "plasteel_microflora_fiber": 28, "silicone_block": 41, "ballistic_weave_fabric": 7, "spice_melange": 83, "spice_infused_plastanium_dust": 14, "water": 700},
        "quantity": 1,
        "station": "Advanced Garment Fabricator"
    },
    
    # === ADVANCED WEAPONS ===
    "dunewatcher": {
        "ingredients": {"plastanium_ingot": 45, "mechanical_parts": 16, "silicone_block": 31, "plasteel_composite_gun_parts": 16, "fluted_heavy_caliber_compressor": 6, "spice_melange": 62, "spice_infused_plastanium_dust": 10, "water": 530},
        "quantity": 1,
        "station": "Advanced Weapons Fabricator"
    },
    "glasser": {
        "ingredients": {"plastanium_ingot": 85, "mechanical_parts": 16, "cobalt_paste": 33, "plasteel_composite_gun_parts": 21, "fluid_efficient_industrial_pump": 8, "spice_melange": 70, "spice_infused_plastanium_dust": 14, "water": 530},
        "quantity": 1,
        "station": "Advanced Weapons Fabricator"
    },
    
    # === VEHICLE COMPONENTS ===
    "carrier_ornithopter_engine_mk6": {
        "ingredients": {"plastanium_ingot": 60, "cobalt_paste": 45, "particle_capacitor": 18, "complex_machinery": 30, "spice_melange": 54, "tri_forged_hydraulic_piston": 9, "water": 1050},
        "quantity": 1,
        "station": "Advanced Vehicle Fabricator"
    },
    
    # === BUILDING MATERIALS ===
    "foundation_structure": {
        "ingredients": {"granite_stone": 15},
        "quantity": 1,
        "station": "Construction Tool"
    },
    "wall": {
        "ingredients": {"granite_stone": 8},
        "quantity": 1,
        "station": "Construction Tool"
    },
    
    # === REFINERIES ===
    "medium_spice_refinery": {
        "ingredients": {"plastanium_ingot": 285, "silicone_block": 225, "spice_melange": 135, "complex_machinery": 100, "cobalt_paste": 190},
        "quantity": 1,
        "station": "Construction"
    },
    "large_ore_refinery": {
        "ingredients": {"plastanium_ingot": 380, "silicone_block": 540, "spice_melange": 400, "complex_machinery": 200, "cobalt_paste": 745, "advanced_machinery": 40},
        "quantity": 1,
        "station": "Construction"
    },
    
    # === PROCESSED MATERIALS ===
    "plastanium_ingot": {
        "ingredients": {"titanium_ore": 1, "stravidium_fiber": 1, "water": 10},
        "quantity": 1,
        "station": "Medium/Large Refinery"
    },
    "spice_melange": {
        "ingredients": {"spice_sand": 3, "water": 15},
        "quantity": 1,
        "station": "Spice Refinery"
    },
    "aluminum_ingot": {
        "ingredients": {"aluminum_ore": 1, "water": 5},
        "quantity": 1,
        "station": "Ore Refinery"
    },
    "duraluminum_ingot": {
        "ingredients": {"aluminum_ore": 2, "cobalt_ore": 1, "water": 8},
        "quantity": 1,
        "station": "Medium/Large Refinery"
    },
    "spice_ingot": {
        "ingredients": {"spice_melange": 3, "water": 20},
        "quantity": 1,
        "station": "Spice Refinery"
    },
    "silicone_block": {
        "ingredients": {"silicate_ore": 1, "water": 3},
        "quantity": 1,
        "station": "Chemical Refinery"
    },
    "cobalt_paste": {
        "ingredients": {"cobalt_ore": 1, "water": 7},
        "quantity": 1,
        "station": "Chemical Refinery"
    }
}

def calculate_materials(item_name, quantity_needed=1):
    """
    Calculate total raw materials needed for crafting an item
    """
    if item_name.lower() not in CRAFTING_RECIPES:
        return None, f"Recipe for '{item_name}' not found"
    
    item_name = item_name.lower()
    recipe = CRAFTING_RECIPES[item_name]
    
    # Calculate how many crafting operations we need
    crafts_needed = (quantity_needed + recipe["quantity"] - 1) // recipe["quantity"]
    
    total_materials = {}
    
    def add_materials(ingredients, multiplier):
        for ingredient, amount in ingredients.items():
            if ingredient.lower() in CRAFTING_RECIPES:
                # This ingredient is also craftable, recurse
                sub_materials, _ = calculate_materials(ingredient, amount * multiplier)
                if sub_materials:
                    for mat, qty in sub_materials.items():
                        total_materials[mat] = total_materials.get(mat, 0) + qty
            else:
                # Raw material
                total_materials[ingredient] = total_materials.get(ingredient, 0) + (amount * multiplier)
    
    add_materials(recipe["ingredients"], crafts_needed)
    
    return total_materials, None

def get_recipe_info(item_name):
    """
    Get recipe information for an item
    """
    if item_name.lower() not in CRAFTING_RECIPES:
        return None
    
    return CRAFTING_RECIPES[item_name.lower()]

def list_craftable_items():
    """
    Return list of all craftable items
    """
    return list(CRAFTING_RECIPES.keys())

def format_materials_list(materials):
    """
    Format materials dictionary into readable string
    """
    if not materials:
        return "No materials needed"
    
    formatted = []
    for material, quantity in sorted(materials.items()):
        formatted.append(f"• {material.replace('_', ' ').title()}: {quantity}")
    
    return "\n".join(formatted)