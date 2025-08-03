# Dune Awakening Crafting Calculator
# Comprehensive crafting recipes loaded from external data file

import json
import os
from typing import Dict, Tuple, List, Optional

# Cache for loaded recipes
_CRAFTING_RECIPES = None

def _load_recipes() -> Dict:
    """Load crafting recipes from JSON file"""
    global _CRAFTING_RECIPES
    
    if _CRAFTING_RECIPES is not None:
        return _CRAFTING_RECIPES
    
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    recipes_file = os.path.join(script_dir, "data", "dune_recipes.json")
    
    try:
        with open(recipes_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            _CRAFTING_RECIPES = data.get("recipes", {})
            return _CRAFTING_RECIPES
    except FileNotFoundError:
        print(f"Warning: Recipe file not found at {recipes_file}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing recipe file: {e}")
        return {}

def get_recipes() -> Dict:
    """Get all crafting recipes"""
    return _load_recipes()

def calculate_materials(item_name: str, quantity_needed: int = 1) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Calculate total raw materials needed for crafting an item
    
    Args:
        item_name: Name of the item to craft
        quantity_needed: How many of the item to craft
        
    Returns:
        Tuple of (materials_dict, error_message)
    """
    recipes = get_recipes()
    
    if item_name.lower() not in recipes:
        return None, f"Recipe for '{item_name}' not found"
    
    item_name = item_name.lower()
    recipe = recipes[item_name]
    
    # Calculate how many crafting operations we need
    crafts_needed = (quantity_needed + recipe["quantity"] - 1) // recipe["quantity"]
    
    total_materials = {}
    
    def add_materials(ingredients: Dict, multiplier: int):
        for ingredient, amount in ingredients.items():
            if ingredient.lower() in recipes:
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

def get_recipe_info(item_name: str) -> Optional[Dict]:
    """
    Get recipe information for an item
    
    Args:
        item_name: Name of the item
        
    Returns:
        Recipe dictionary or None if not found
    """
    recipes = get_recipes()
    
    if item_name.lower() not in recipes:
        return None
    
    return recipes[item_name.lower()]

def list_craftable_items() -> List[str]:
    """
    Return list of all craftable items
    
    Returns:
        List of item names
    """
    recipes = get_recipes()
    return list(recipes.keys())

def get_items_by_category(category: str) -> List[str]:
    """
    Get all items in a specific category
    
    Args:
        category: Category name (e.g., 'weapon', 'material', 'consumable')
        
    Returns:
        List of item names in the category
    """
    recipes = get_recipes()
    return [name for name, recipe in recipes.items() 
            if recipe.get('category', '').lower() == category.lower()]

def get_categories() -> List[str]:
    """
    Get all available categories
    
    Returns:
        List of unique category names
    """
    recipes = get_recipes()
    categories = set()
    for recipe in recipes.values():
        if 'category' in recipe:
            categories.add(recipe['category'])
    return sorted(list(categories))

def format_materials_list(materials: Dict) -> str:
    """
    Format materials dictionary into readable string
    
    Args:
        materials: Dictionary of material names and quantities
        
    Returns:
        Formatted string representation
    """
    if not materials:
        return "No materials needed"
    
    formatted = []
    for material, quantity in sorted(materials.items()):
        formatted.append(f"- {material.replace('_', ' ').title()}: {quantity:,}")
    
    return "\n".join(formatted)

def get_recipe_count() -> int:
    """
    Get total number of recipes available
    
    Returns:
        Number of recipes
    """
    return len(get_recipes())

def search_recipes(search_term: str) -> List[str]:
    """
    Search for recipes by name or description
    
    Args:
        search_term: Term to search for
        
    Returns:
        List of matching item names
    """
    recipes = get_recipes()
    search_lower = search_term.lower()
    matches = []
    
    for name, recipe in recipes.items():
        # Check name
        if search_lower in name.lower():
            matches.append(name)
        # Check description
        elif 'description' in recipe and search_lower in recipe['description'].lower():
            matches.append(name)
    
    return matches

# Backwards compatibility
CRAFTING_RECIPES = property(lambda self: get_recipes())