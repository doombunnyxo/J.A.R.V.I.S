"""
Unified Crafting Module for AI Handler

This module contains all crafting-related functionality extracted from the main AI handler
to improve maintainability and organization while preserving all features.
"""

import re
import logging
from typing import Tuple, List, Dict, Optional
from ..utils.logging import get_logger

logger = get_logger(__name__)


class CraftingProcessor:
    """Handles all crafting-related processing and interpretation"""
    
    def __init__(self):
        pass
    
    async def handle_crafting_request(self, message, query: str) -> str:
        """Main entry point for crafting requests"""
        try:
            # Handle special list commands
            query_lower = query.lower().strip()
            if query_lower in ['list', 'categories', 'help']:
                return await self._handle_crafting_list()
            elif query_lower in ['weapons', 'list weapons']:
                return await self._handle_crafting_category_list('weapons')
            elif query_lower in ['vehicles', 'list vehicles']:
                return await self._handle_crafting_category_list('vehicles')
            elif query_lower in ['tools', 'list tools']:
                return await self._handle_crafting_category_list('tools')
            
            # Use Claude to interpret the crafting request with context
            result = await self._interpret_recipe_request(query, message)
            
            if isinstance(result, tuple) and len(result) == 2:
                item_name, quantity = result
                
                # Import crafting functions
                from dune_crafting import calculate_materials, get_recipe_info, format_materials_list, format_materials_tree, list_craftable_items
                
                try:
                    # Check if this is a vehicle assembly request (VEHICLE_PARTS or VEHICLE_ASSEMBLY)
                    if item_name.startswith('VEHICLE_PARTS|') or item_name.startswith('VEHICLE_ASSEMBLY|'):
                        # Use our consolidated vehicle assembly handler
                        return await self._handle_vehicle_assembly_request(item_name, quantity, query)
                    
                    # Get the recipe information for individual items
                    recipe_info = get_recipe_info(item_name)
                    if not recipe_info:
                        return f"❌ **Recipe not found for:** {item_name}\n\nThe LLM should have matched this to a valid recipe. Use `@bot craft: list` to see available categories.\n\n**Debug:** Interpreted query '{query}' as item '{item_name}'"
                    
                    # Check if this is a non-craftable item (no ingredients field or raw_material category)
                    if 'ingredients' not in recipe_info or recipe_info.get('category') == 'raw_material':
                        response = f"🚫 **{item_name.replace('_', ' ').title()}**\n\n"
                        response += f"**Status:** Found Only - Cannot Be Crafted\n\n"
                        response += f"**Description:** {recipe_info.get('description', 'This item cannot be crafted.')}\n\n"
                        response += "💡 **How to obtain:** This item can only be found as loot from enemies, structures, or containers in the world."
                        return response
                    
                    # Calculate total materials needed
                    total_materials = calculate_materials(item_name, quantity)
                    
                    # Format the response
                    response = f"🔧 **Crafting Recipe: {item_name}**\n\n"
                    
                    if quantity > 1:
                        response += f"**Quantity:** {quantity}\n\n"
                    
                    # Add recipe details
                    station = recipe_info.get('station', 'Unknown')
                    response += f"**Station:** {station}\n\n"
                    
                    # Add materials breakdown
                    if isinstance(total_materials, dict):
                        response += f"**Materials Required:**\n"
                        response += format_materials_list(total_materials)
                    else:
                        response += f"**Error:** Could not calculate materials\n"
                    
                    return response
                    
                except Exception as e:
                    return f"❌ **Error processing recipe:** {str(e)}"
                    
            else:
                return f"❌ **Could not parse crafting request:** {query}\n\nExample: `@bot craft: sandbike mk3 with boost`"
                
        except Exception as e:
            return f"❌ **Crafting system error:** {str(e)}"

    async def _handle_crafting_list(self) -> str:
        """Handle crafting list command"""
        try:
            from dune_crafting import get_categories, get_items_by_category
            
            categories = get_categories()
            
            response = "🏗️ **Dune Awakening Crafting Categories**\n\n"
            
            category_display_names = {
                'weapon': '⚔️ **Weapons**',
                'vehicle_part': '🚗 **Vehicle Parts**', 
                'consumable': '💊 **Consumables**',
                'tool': '🔧 **Tools**',
                'material': '📦 **Materials**'
            }
            
            for category in categories:
                display_name = category_display_names.get(category, f"**{category.title()}**")
                items = get_items_by_category(category)
                item_count = len(items)
                
                response += f"{display_name}: {item_count} items\n"
                
                # Show a few examples
                examples = items[:3]
                if examples:
                    example_text = ", ".join([item.replace('_', ' ').title() for item in examples])
                    response += f"  *Examples: {example_text}*\n"
                response += "\n"
            
            response += "💡 **Tip:** You can use natural language! Try: `@bot craft: I need 3 mark 2 heal kits`"
            return response
            
        except Exception as e:
            return f"Error generating category list: {str(e)}"

    async def _handle_crafting_category_list(self, category: str) -> str:
        """Handle specific category listing"""
        try:
            from dune_crafting import get_items_by_category
            
            # Map user-friendly names to database categories
            category_mapping = {
                'weapons': 'weapon',
                'vehicles': 'vehicle_part',
                'tools': 'tool'
            }
            
            db_category = category_mapping.get(category.lower(), category.lower())
            items = get_items_by_category(db_category)
            
            if not items:
                return f"❌ **No items found in category:** {category}"
            
            category_display = {
                'weapons': '⚔️ **Weapons**',
                'vehicles': '🚗 **Vehicle Parts**',
                'tools': '🔧 **Tools**'
            }
            
            display_name = category_display.get(category.lower(), f"**{category.title()}**")
            response = f"{display_name}\n\n"
            
            # Group items by type for better organization
            if category.lower() == 'weapons':
                response += "• **Example:** `craft: karpov 38 plastanium`\n"
                response += "• **Example:** `craft: sandbike mk3`\n"
                response += "• **Example:** `craft: cutteray mk6`\n\n"
                
                response += "**Weapon Types:**\n"
                response += "• Karpov 38, Maula Pistol, Disruptor M11\n"
                response += "• Drillshot FK7, GRDA 44, JABAL Spitdart\n"
                response += "• Sword, Rapier, Dirk, Kindjal\n\n"
                
                response += "**Material Tiers:** Salvage, Copper, Iron, Steel, Aluminum, Duraluminum, Plastanium\n"
                
            elif category.lower() == 'vehicles':
                response += "**Example:** `craft: sandbike mk3 with night rider boost mk6`\n"
                response += "**Example:** `craft: assault ornithopter mk5 with rocket launcher`\n\n"
                
                response += "**Vehicle Types:**\n"
                response += "• Sandbike (mk1-mk5)\n"
                response += "• Buggy (mk3-mk6)\n"
                response += "• Scout Ornithopter (mk4-mk6)\n"
                response += "• Assault Ornithopter (mk5-mk6)\n"
                response += "• Carrier Ornithopter (mk6)\n"
                response += "• Sandcrawler (mk6)\n\n"
                
            elif category.lower() == 'tools':
                response += "**Example:** `craft: cutteray mk6`\n\n"
                response += "**Tool Types:**\n"
                response += "• Cutteray, Construction Tool\n"
                response += "• Survey Tool, Binoculars\n\n"
            
            response += f"**Total Items:** {len(items)}\n\n"
            response += "• Use `craft:` or `cr:` as shortcuts\n"
            response += "• Mix and match vehicle parts and tiers!\n"
            response += "• Natural language works: 'I need 5 healing kits'"
            
            return response
            
        except Exception as e:
            return f"Error generating {category} list: {str(e)}"

    async def _handle_vehicle_assembly_request(self, assembly_request: str, quantity: int, original_query: str) -> str:
        """Handle flexible vehicle assembly requests with full mode support"""
        try:
            # Parse assembly request - can be VEHICLE_ASSEMBLY or VEHICLE_PARTS format
            parts = assembly_request.split('|')
            
            # Check if user wants full breakdown or by parts
            query_lower = original_query.lower()
            full_breakdown = any(keyword in query_lower for keyword in [
                'full breakdown', 'complete breakdown', 'detailed breakdown', 
                'full materials', 'raw materials', 'all materials',
                'break down', 'breakdown'
            ])
            
            by_parts = any(keyword in query_lower for keyword in [
                'by parts', 'each part', 'part breakdown', 'per part',
                'part by part', 'individual parts', 'materials by part',
                'show parts', 'list parts'
            ])

            # Determine mode for display
            if by_parts and full_breakdown:
                mode_text = "**📊 MODE 4:** By Parts + Full Breakdown (Complete trees for each part)"
            elif by_parts:
                mode_text = "**📊 MODE 3:** By Parts (Direct materials for each part)"
            elif full_breakdown:
                mode_text = "**📊 MODE 2:** Full Breakdown (Summary + complete trees)"
            else:
                mode_text = "**📊 MODE 1:** Default (Parts list + total materials summary)"
            
            # Handle VEHICLE_PARTS format (flexible mixed-tier builds)
            if parts[0] == 'VEHICLE_PARTS' and len(parts) >= 3:
                return await self._handle_flexible_vehicle_parts(parts, quantity, original_query, full_breakdown, by_parts, mode_text)
            
            # Handle VEHICLE_ASSEMBLY format (convert to flexible format)
            elif parts[0] == 'VEHICLE_ASSEMBLY' and len(parts) >= 4:
                vehicle_type = parts[1]
                tier = parts[2]
                # Convert to flexible format by generating standard parts list
                standard_parts = self._get_standard_vehicle_parts(vehicle_type, tier)
                if standard_parts:
                    parts_list_str = ','.join(standard_parts)
                    flexible_parts = ['VEHICLE_PARTS', vehicle_type, parts_list_str]
                    return await self._handle_flexible_vehicle_parts(flexible_parts, quantity, original_query, full_breakdown, by_parts, mode_text)
                else:
                    return f"❌ **Unknown vehicle type:** {vehicle_type}"
            
            else:
                return f"❌ **Invalid vehicle assembly format:** {assembly_request}"
        except Exception as e:
            return f"❌ **Error processing vehicle assembly:** {str(e)}\n\n**Original request:** {original_query}"

    def _get_standard_vehicle_parts(self, vehicle_type: str, tier: str) -> list:
        """Get standard parts list for a vehicle type and tier"""
        # Map vehicle types to their standard required parts
        vehicle_parts_map = {
            "sandbike": ["engine", "chassis", "hull", "psu", "tread"],
            "buggy": ["engine", "chassis", "psu", "tread", "rear"],
            "scout_ornithopter": ["engine", "chassis", "cockpit", "generator", "hull", "wing"],
            "assault_ornithopter": ["engine", "chassis", "cockpit", "cabin", "generator", "tail", "wing"],
            "carrier_ornithopter": ["engine", "chassis", "generator", "main_hull", "side_hull", "tail_hull", "wing"],
            "sandcrawler": ["engine", "chassis", "cabin", "tread", "vacuum", "centrifuge", "psu"]
        }
        
        if vehicle_type not in vehicle_parts_map:
            return []
        
        # Generate part names with tier
        parts = []
        for part in vehicle_parts_map[vehicle_type]:
            parts.append(f"{part}_{tier}")
        
        return parts

    async def _handle_flexible_vehicle_parts(self, parts_data: list, quantity: int, original_query: str, full_breakdown: bool, by_parts: bool, mode_text: str) -> str:
        """Handle flexible vehicle parts assembly requests"""
        try:
            # Import crafting functions
            from dune_crafting import get_recipe_info, calculate_materials, calculate_direct_materials, format_materials_tree, format_materials_list, list_craftable_items
            
            if len(parts_data) < 3:
                return "❌ **Invalid vehicle parts format**"
            
            vehicle_type = parts_data[1].strip()
            parts_list_str = parts_data[2].strip()
            
            # Parse the parts list: "engine_mk2,chassis_mk3,hull_mk3,tread_mk1,booster_mk5"
            requested_parts = [part.strip() for part in parts_list_str.split(',') if part.strip()]
            
            # Convert to full database keys: "engine_mk2" -> "sandbike_engine_mk2"
            full_part_keys = []
            missing_parts = []
            available_items = list_craftable_items()
            
            for part in requested_parts:
                # Build the full key: vehicle_type + "_" + part
                if part.startswith(vehicle_type + "_"):
                    full_key = part
                else:
                    full_key = f"{vehicle_type}_{part}"
                
                if full_key in available_items:
                    full_part_keys.append(full_key)
                else:
                    missing_parts.append(part)
            
            if missing_parts:
                missing_str = ", ".join(missing_parts)
                return f"❌ **Some parts not found in database:**\n{missing_str}\n\n**Available parts found:** {len(full_part_keys)}"
            
            if not full_part_keys:
                return "❌ **No valid parts found for this vehicle configuration**"
            
            # Define part quantity display (for UI purposes - recipes already account for actual quantities)
            part_display_quantities = {
                'sandbike_tread': 3,
                'buggy_tread': 4, 
                'scout_ornithopter_wing': 4,
                'assault_ornithopter_wing': 6,
                'carrier_ornithopter_wing': 8,
                'carrier_ornithopter_side_hull': 2,
                'carrier_ornithopter_tail_hull': 2,
                'sandcrawler_tread': 2,
                'dampened_sandcrawler_treads': 2
            }
            
            total_materials = {}
            part_details = []
            
            for part_key in full_part_keys:
                recipe = get_recipe_info(part_key)
                if recipe:
                    # Get display quantity for UI (recipes already contain correct quantities)
                    display_multiplier = 1
                    for part_pattern, multiplier in part_display_quantities.items():
                        if part_pattern in part_key:
                            display_multiplier = multiplier
                            break
                    
                    # Calculate materials (recipes already account for multiple parts)
                    if full_breakdown:
                        part_materials, error = calculate_materials(part_key, quantity)
                    else:
                        part_materials, error = calculate_direct_materials(part_key, quantity)
                    
                    if error is None and isinstance(part_materials, dict):
                        for material, amount in part_materials.items():
                            total_materials[material] = total_materials.get(material, 0) + amount
                        part_details.append((part_key, recipe, display_multiplier))
                    else:
                        missing_parts.append(part_key)
                else:
                    missing_parts.append(part_key)
            
            if not total_materials:
                return f"❌ **Could not calculate materials for {vehicle_type} parts**"
            
            # Format response
            response = f"🚗 **Custom {vehicle_type.replace('_', ' ').title()} Assembly**\n\n"
            response += f"{mode_text}\n\n"
            if quantity > 1:
                response += f"**Quantity:** {quantity}\n\n"
            
            # Show configuration
            response += f"**Configuration:** Mixed-tier build\n\n"
            
            # List all parts with their tiers and quantities
            response += f"**Parts Required ({len(part_details)}):**\n"
            for part_key, recipe, part_multiplier in part_details:
                # Extract tier from part name for display
                part_display = part_key.replace(f"{vehicle_type}_", "").replace("_", " ").title()
                station = recipe.get('station', 'Unknown')
                if part_multiplier > 1:
                    response += f"- {part_display} x{part_multiplier} (Station: {station})\n"
                else:
                    response += f"- {part_display} (Station: {station})\n"
            
            if full_breakdown:
                response += f"\n**📦 Raw Materials Breakdown:**\n"
            else:
                response += f"\n**📦 Direct Materials Required:**\n"
            response += format_materials_list(total_materials)
            
            # Add detailed breakdown based on mode
            if full_breakdown and not by_parts:
                # Mode 2: Full breakdown - show how to craft the raw materials
                # Build a crafting tree showing the intermediate steps
                response += f"\n\n**🔧 Crafting Process:**\n"
                
                # Group materials by tier/type for better organization
                material_tiers = {
                    'Basic': ['Salvage', 'Scrap Metal', 'Plastic Scrap', 'Electronics Scrap'],
                    'Ores': ['Copper Ore', 'Iron Ore', 'Carbon Ore', 'Aluminum Ore', 'Cobalt Ore', 'Nickel Ore'],
                    'Refined': ['Copper Ingot', 'Iron Ingot', 'Steel Ingot', 'Aluminum Ingot', 'Cobalt Ingot', 'Nickel Ingot'],
                    'Advanced': ['Plastanium', 'Duraluminum', 'Advanced Alloy', 'Carbon Fiber'],
                    'Components': ['Servoks', 'Advanced Servoks', 'Gears', 'Springs', 'Wiring', 'Circuit Board', 'Power Cell']
                }
                
                # Show which materials can be crafted from others
                crafting_relationships = {
                    'Copper Ingot': 'Crafted from: Copper Ore',
                    'Iron Ingot': 'Crafted from: Iron Ore',
                    'Steel Ingot': 'Crafted from: Iron Ingot + Carbon Ore',
                    'Aluminum Ingot': 'Crafted from: Aluminum Ore',
                    'Duraluminum': 'Crafted from: Aluminum Ingot + Copper Ingot',
                    'Plastanium': 'Crafted from: Plastic Scrap + Aluminum Ingot',
                    'Advanced Servoks': 'Crafted from: Servoks + Electronics'
                }
                
                # Display materials by tier with crafting info
                materials_shown = set()
                for tier, tier_materials in material_tiers.items():
                    tier_items = []
                    for mat in tier_materials:
                        if mat in total_materials:
                            amount = total_materials[mat]
                            if mat in crafting_relationships:
                                tier_items.append(f"  - {mat}: {amount} ({crafting_relationships[mat]})")
                            else:
                                tier_items.append(f"  - {mat}: {amount}")
                            materials_shown.add(mat)
                    
                    if tier_items:
                        response += f"\n**{tier} Materials:**\n" + "\n".join(tier_items)
                
                # Show any remaining materials not in predefined tiers
                remaining = []
                for mat, amount in total_materials.items():
                    if mat not in materials_shown:
                        remaining.append(f"  - {mat}: {amount}")
                
                if remaining:
                    response += f"\n**Other Materials:**\n" + "\n".join(remaining)
            
            elif by_parts:
                # Mode 3 or 4: Show materials for each part individually
                response += f"\n**🔧 Materials by Part:**\n"
                for part_key, recipe, part_multiplier in part_details:
                    part_display = part_key.replace(f"{vehicle_type}_", "").replace("_", " ").title()
                    
                    if full_breakdown:
                        # Mode 4: By parts + full breakdown (complete crafting trees for each part)
                        if part_multiplier > 1:
                            response += f"\n**{part_display} (x{part_multiplier}):**\n"
                        else:
                            response += f"\n**{part_display}:**\n"
                        response += format_materials_tree(part_key, part_multiplier)
                    else:
                        # Mode 3: By parts only (direct materials for each part)
                        part_materials, _ = calculate_direct_materials(part_key, 1)
                        # Multiply by vehicle quantity if needed
                        if quantity > 1 and part_materials:
                            part_materials = {mat: qty * quantity for mat, qty in part_materials.items()}
                        
                        if part_multiplier > 1:
                            response += f"\n**{part_display} (x{part_multiplier}):**\n"
                        else:
                            response += f"\n**{part_display}:**\n"
                        if part_materials:
                            response += format_materials_list(part_materials)
                        else:
                            response += "- No materials needed\n"
            
            # Add final notes
            if quantity > 1:
                response += f"\n💡 **Note:** Building {quantity} vehicles requires {len(part_details)} different crafting operations per vehicle."
            response += f"\n✨ **Flexibility:** You can mix and match any tier parts within the same vehicle type!"
            
            return response
            
        except Exception as e:
            return f"❌ **Error processing vehicle assembly:** {str(e)}\n\n**Original request:** {original_query}"

    async def _interpret_recipe_request(self, user_query: str, message=None) -> Tuple[str, int]:
        """Use OpenAI GPT-4o mini to interpret natural language recipe requests and match to JSON structure"""
        try:
            from src.config import config
            from dune_crafting import list_craftable_items
            import aiohttp
            import json
            
            if not config.has_openai_api():
                return self._fallback_parse(user_query)
            
            # Get all available items for accurate matching
            available_items = list_craftable_items()
            
            # Create strategic samples to show OpenAI the naming patterns
            pattern_samples = {
                "weapons": [item for item in available_items if any(w in item for w in ['karpov_38', 'maula_pistol', 'drillshot_fk7', 'grda_44', 'jabal_spitdart', 'disruptor_m11', 'sword', 'rapier', 'dirk', 'kindjal']) and not any(part in item for part in ['engine', 'chassis', 'hull'])],
                "vehicles": [item for item in available_items if any(v in item for v in ['sandbike_', 'buggy_', 'ornithopter_']) and any(part in item for part in ['engine', 'chassis', 'hull', 'wing', 'tread'])],
                "tools": [item for item in available_items if any(t in item for t in ['cutteray', 'construction', 'survey', 'binoculars'])],
                "consumables": [item for item in available_items if any(c in item for c in ['healkit', 'pill', 'beer', 'coffee'])]
            }
            
            # Build focused sample based on query type
            samples = []
            query_lower = user_query.lower()
            
            if any(weapon in query_lower for weapon in ['karpov', '38', 'maula', 'sword', 'rifle', 'pistol', 'blade', 'drillshot', 'fk7', 'grda', '44', 'spitdart', 'disruptor']):
                samples.extend(pattern_samples["weapons"][:15])
            elif any(vehicle in query_lower for vehicle in ['sandbike', 'buggy', 'ornithopter', 'vehicle']):
                samples.extend(pattern_samples["vehicles"][:20])
            elif any(tool in query_lower for tool in ['tool', 'cutteray', 'survey', 'binoculars']):
                samples.extend(pattern_samples["tools"][:8])
            else:
                # General sample from all categories
                for category_items in pattern_samples.values():
                    samples.extend(category_items[:5])
            
            sample_text = "\n".join([f"- {item}" for item in samples[:25]])
            
            system_message = """You are a Dune Awakening crafting interpreter. Parse complex user requests and determine what they want to craft.

CRITICAL RULE: When a user mentions a vehicle type followed by parts, ALL parts mentioned afterward belong to that vehicle unless explicitly stated otherwise.

RESPONSE FORMATS:
1. Single item: "exact_key|quantity"
2. Vehicle assembly: "VEHICLE_ASSEMBLY|vehicle_type|tier|modules|quantity"
3. Vehicle parts: "VEHICLE_PARTS|vehicle_type|parts_list|quantity"

SPECIAL MODIFIERS (add to end of any format above):
- If user mentions "by parts", "each part", "part breakdown", "per part", "part by part", "individual parts", "materials by part": add "|BY_PARTS"
- If user mentions "full breakdown", "complete breakdown", "detailed breakdown", "raw materials", "all materials", "break down", "breakdown": add "|FULL_BREAKDOWN"
- Both can be combined: "|BY_PARTS|FULL_BREAKDOWN"

CONTEXT AWARENESS:
- If user says "assault ornithopter mk6 with engine mk6, wings mk5" - the engine and wings are ASSAULT ORNITHOPTER parts
- If user says "sandbike mk3 with engine mk2" - the engine is a SANDBIKE engine
- Always prefix parts with the vehicle type mentioned in the same request

VEHICLE PARSING RULES:
1. When a vehicle is mentioned, ALL subsequent parts in that request belong to that vehicle
2. "assault ornithopter mk6 with engine mk6" means assault_ornithopter_engine_mk6, NOT generic engine_mk6
3. Default tier for unspecified parts = the main vehicle tier mentioned
4. Parse "wings" as "wing" (singular) for database matching

VEHICLE EXAMPLES (FLEXIBLE MIXING):
COMPLETE VEHICLES:
- "assault ornithopter mk6" -> "VEHICLE_PARTS|assault_ornithopter|engine_mk6,chassis_mk6,cockpit_mk6,cabin_mk6,generator_mk6,tail_mk6,wing_mk6|1"
- "assault ornithopter mk6 with engine mk6, wings mk5" -> "VEHICLE_PARTS|assault_ornithopter|engine_mk6,chassis_mk6,cockpit_mk6,cabin_mk6,generator_mk6,tail_mk6,wing_mk5|1"
- "assault ornithopter mk6 with engine mk5 and wings mk5" -> "VEHICLE_PARTS|assault_ornithopter|engine_mk5,chassis_mk6,cockpit_mk6,cabin_mk6,generator_mk6,tail_mk6,wing_mk5|1"
- "sandbike mk3 with mk2 engine, mk5 booster and mk1 treads" -> "VEHICLE_PARTS|sandbike|engine_mk2,chassis_mk3,hull_mk3,psu_mk3,tread_mk1,booster_mk5|1"

INDIVIDUAL PARTS (must include vehicle prefix):
- "engine mk6" (after mentioning assault ornithopter) -> "assault_ornithopter_engine_mk6|1"
- "wings mk5" (after mentioning assault ornithopter) -> "assault_ornithopter_wing_mk5|1"
- "assault ornithopter thruster mk6" -> "assault_ornithopter_thruster_mk6|1"
- "sandbike engine mk3" -> "sandbike_engine_mk3|1"

Return ONLY the specified format with NO explanations."""
            
            user_message = f"""User request: "{user_query}"

Available items (sample):
{sample_text}

Match this request to an exact database key. Remember: if a vehicle type was mentioned, all parts in the request belong to that vehicle."""
            
            # Call OpenAI API directly
            headers = {
                "Authorization": f"Bearer {config.OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                "max_tokens": 150,
                "temperature": 0.0
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as api_response:
                    if api_response.status != 200:
                        logger.error(f"OpenAI API error: {api_response.status}")
                        return self._fallback_parse(user_query)
                    
                    api_result = await api_response.json()
                    response = api_result['choices'][0]['message']['content']
            
            result = response.strip()
            # Clean up any quotes or extra formatting
            if result.startswith('"') and result.endswith('"'):
                result = result[1:-1]
            elif result.startswith('"'):
                result = result[1:]
            
            # Parse OpenAI's response
            if '|' in result:
                parts = result.split('|')
                
                # Extract modifiers from the end
                modifiers = []
                while len(parts) > 0 and parts[-1].strip() in ['BY_PARTS', 'FULL_BREAKDOWN']:
                    modifiers.append(parts[-1].strip())
                    parts = parts[:-1]
                
                # Check if this is a flexible vehicle parts request
                if parts[0].strip() == 'VEHICLE_PARTS' and len(parts) >= 3:
                    vehicle_type = parts[1].strip()
                    parts_list = parts[2].strip()
                    try:
                        quantity = int(parts[3].strip()) if len(parts) > 3 else 1
                    except (ValueError, IndexError):
                        quantity = 1
                    
                    # Add modifiers to the return format
                    base_format = f"VEHICLE_PARTS|{vehicle_type}|{parts_list}"
                    if modifiers:
                        base_format += "|" + "|".join(modifiers)
                    
                    return base_format, quantity
                
                # Check if this is a legacy vehicle assembly request
                elif parts[0].strip() == 'VEHICLE_ASSEMBLY' and len(parts) >= 4:
                    vehicle_type = parts[1].strip()
                    tier = parts[2].strip()
                    modules = parts[3].strip()
                    
                    # Find quantity from remaining parts (skip modifiers)
                    quantity = 1
                    for part in parts[4:]:
                        if part.strip() not in ['BY_PARTS', 'FULL_BREAKDOWN']:
                            try:
                                quantity = int(part.strip())
                                break
                            except ValueError:
                                continue
                    
                    # Add modifiers to the return format
                    base_format = f"VEHICLE_ASSEMBLY|{vehicle_type}|{tier}|{modules}"
                    if modifiers:
                        base_format += "|" + "|".join(modifiers)
                    
                    return base_format, quantity
                
                # Regular single item format
                else:
                    item_name = parts[0].strip().lower()
                    
                    # Try to parse quantity from remaining parts (skip modifiers)
                    quantity = 1
                    for part in parts[1:]:
                        if part.strip() not in ['BY_PARTS', 'FULL_BREAKDOWN']:
                            try:
                                quantity = int(part.strip())
                                break
                            except ValueError:
                                continue
                    
                    # Add modifiers to single items
                    if modifiers:
                        item_name += "|" + "|".join(modifiers)
                    
                    # Validate that the base item exists (without modifiers)
                    base_item = item_name.split('|')[0]
                    if base_item in available_items:
                        return item_name, quantity
                    else:
                        logger.debug(f"Claude suggested non-existent item: {base_item}")
                        return self._smart_fallback_match(user_query, available_items)
            else:
                return self._smart_fallback_match(user_query, available_items)
                
        except Exception as e:
            logger.debug(f"OpenAI recipe interpretation failed: {e}")
            return self._fallback_parse(user_query)
    
    def _fallback_parse(self, query: str) -> Tuple[str, int]:
        """Simple fallback parsing when OpenAI is unavailable"""
        parts = query.split()
        item_name = parts[0].lower() if parts else ""
        quantity = 1
        
        # Try to extract quantity from anywhere in the query
        for part in parts:
            if part.isdigit():
                quantity = int(part)
                break
        
        return item_name, quantity
    
    def _smart_fallback_match(self, query: str, available_items: List[str]) -> Tuple[str, int]:
        """Intelligent fallback matching using string similarity"""
        query_lower = query.lower()
        quantity = 1
        
        # Extract quantity if present
        quantity_match = re.search(r'\b(\d+)\b', query)
        if quantity_match:
            quantity = int(quantity_match.group(1))
        
        # Try exact substring matching first
        best_matches = []
        
        for item in available_items:
            # Score based on how many words match
            score = 0
            item_words = item.replace('_', ' ').split()
            query_words = query_lower.replace('mk', 'mk').split()
            
            for query_word in query_words:
                if query_word.isdigit():
                    continue
                for item_word in item_words:
                    if query_word in item_word or item_word in query_word:
                        score += 1
            
            if score > 0:
                best_matches.append((item, score))
        
        if best_matches:
            # Sort by score and return best match
            best_matches.sort(key=lambda x: x[1], reverse=True)
            return best_matches[0][0], quantity
        
        return "no_match", quantity