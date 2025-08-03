import discord
from discord.ext import commands
from dune_crafting import calculate_materials, calculate_direct_materials, get_recipe_info, list_craftable_items, format_materials_list, format_materials_tree, get_items_by_category, get_categories
from ..config import config
from ..search.claude import AnthropicAPI

class CraftingHandler(commands.Cog):
    """Dune Awakening crafting calculator"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def _interpret_recipe_request(self, user_query: str) -> tuple[str, int]:
        """Use Claude Haiku to interpret natural language recipe requests and match to JSON structure"""
        try:
            if not config.has_anthropic_api():
                return self._fallback_parse(user_query)
            
            # Create Claude client
            claude = AnthropicAPI(config.ANTHROPIC_API_KEY)
            
            # Get all available items for accurate matching
            available_items = list_craftable_items()
            
            # Create strategic samples to show Claude the naming patterns
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

RESPONSE FORMATS:
1. Single item: "exact_key|quantity"
2. Vehicle assembly: "VEHICLE_ASSEMBLY|vehicle_type|tier|modules|quantity"
3. Vehicle parts: "VEHICLE_PARTS|vehicle_type|parts_list|quantity"

SPECIAL MODIFIERS (add to end of any format above):
- If user mentions "by parts", "each part", "part breakdown", "per part", "part by part", "individual parts", "materials by part": add "|BY_PARTS"
- If user mentions "full breakdown", "complete breakdown", "detailed breakdown", "raw materials", "all materials", "break down", "breakdown": add "|FULL_BREAKDOWN"
- Both can be combined: "|BY_PARTS|FULL_BREAKDOWN"

EXAMPLES WITH MODIFIERS:
- "assault ornithopter mk6 by parts" -> "VEHICLE_ASSEMBLY|assault_ornithopter|mk6|none|1|BY_PARTS"
- "assault ornithopter mk6 full breakdown" -> "VEHICLE_ASSEMBLY|assault_ornithopter|mk6|none|1|FULL_BREAKDOWN"  
- "assault ornithopter mk6 by parts raw materials" -> "VEHICLE_ASSEMBLY|assault_ornithopter|mk6|none|1|BY_PARTS|FULL_BREAKDOWN"
- "karpov 38 by parts" -> "karpov_38|1|BY_PARTS"

VEHICLE ASSEMBLY FORMAT:
- For complete vehicles, return: "VEHICLE_PARTS|vehicle_type|parts_list|quantity"
- Mix and match ANY tier parts within the same vehicle type
- Users can upgrade specific parts while keeping others at lower tiers

VEHICLE TYPES & PART AVAILABILITY:

SANDBIKE (mk1-mk5 available):
REQUIRED: engine(mk1-5), chassis(mk1-5), hull(mk1-5), psu(mk1-5), tread(mk1-5) [3x tread needed]
OPTIONAL: backseat(mk1 only), booster(mk2-5), storage(mk2 only)

BUGGY (mk3-mk6 available):  
REQUIRED: engine(mk3-6), chassis(mk3-6), psu(mk3-6), tread(mk3-6) [4x tread needed], rear(mk3-6) OR utility_rear(mk3-6), hull(mk4-6)
OPTIONAL: booster(mk3-6), cutteray(mk3-6, utility_rear only), storage(mk3-6, utility_rear only)

SCOUT_ORNITHOPTER (mk4-mk6 available):
REQUIRED: engine(mk4-6), chassis(mk4-6), cockpit(mk4-6), generator(mk4-6), hull(mk4-6), wing(mk4-6) [4x wing needed]
OPTIONAL: storage(mk4 only), rocket_launcher(mk5-6), thruster(mk4-6)

ASSAULT_ORNITHOPTER (mk5-mk6 available):
REQUIRED: engine(mk5-6), chassis(mk5-6), cockpit(mk5-6), cabin(mk5-6), generator(mk5-6), tail(mk5-6), wing(mk5-6) [6x wing needed]
OPTIONAL: storage(mk5 only), rocket_launcher(mk5-6), thruster(mk5-6)

CARRIER_ORNITHOPTER (mk6 only):
REQUIRED: engine(mk6), chassis(mk6), generator(mk6), main_hull(mk6), side_hull(mk6) [2x needed], tail_hull(mk6) [2x needed], wing(mk6) [8x needed]
OPTIONAL: thruster(mk6)

SANDCRAWLER (mk6 only):
REQUIRED: engine(mk6), chassis(mk6), cabin(mk6), tread(mk6) [2x tread needed], vacuum(mk6), centrifuge(mk6), psu(mk6)
VARIANTS: walker_engine(mk6), dampened_treads(mk6) [2x needed]

KEY PATTERNS:
- Weapons: "karpov_38", "maula_pistol", "sword" (add material tier if specified)
- Individual Parts: "sandbike_engine_mk3", "buggy_chassis_mk5"
- Consumables: "healkit_mk2", "iodine_pill"
- Tools: "cutteray_mk6", "construction_tool"

VEHICLE MODULES:
- Sandbike: "backseat" (mk1 only), "boost", "storage"
- Scout Ornithopter: "storage", "rocket_launcher", "scan" (scan is standalone)
- Assault Ornithopter: "storage", "rocket_launcher" (competing), "thruster" (standalone)
- Carrier Ornithopter: "thruster"
- Buggy: "rear"/"utility_rear", "boost", "cutteray", "storage"

INTERPRETATION RULES:
1. COMPLETE VEHICLE REQUESTS (use VEHICLE_PARTS format):
   - "assault ornithopter mk6" = complete vehicle with all required parts
   - "assault ornithopter mk6 with thruster" = complete vehicle + thruster module
   - "assault ornithopter mk6 with thruster and storage" = complete vehicle + both modules
   - Keywords: "complete", "full", vehicle type + tier + "with"

2. INDIVIDUAL PART REQUESTS (use single item format):
   - "assault ornithopter thruster mk6" = just the thruster part
   - "ornithopter wing mk5" = just the wing part
   - Keywords: no vehicle context, just part name + tier

3. MODULE RULES:
   - "without modules" or "no modules" = only required parts
   - "with X module" = required parts + specified modules
   - Extract quantity (default: 1)

CRITICAL: WEAPON NUMBERS ARE PART OF THE NAME, NOT QUANTITY!

WEAPON NAME EXAMPLES:
- "karpov 38" -> weapon name is "karpov_38" (NOT 38 quantity of karpov)
- "drillshot fk7" -> weapon name is "drillshot_fk7" 
- "grda 44" -> weapon name is "grda_44"
- "maula pistol" -> weapon name is "maula_pistol"

WEAPON TIER EXAMPLES:
- "karpov 38 plastanium" -> "karpov_38_plastanium|1"
- "karpov 38 steel" -> "karpov_38_steel|1"
- "maula pistol iron" -> "maula_pistol_iron|1"
- "5 karpov 38 plastanium" -> "karpov_38_plastanium|5"

VEHICLE EXAMPLES (FLEXIBLE MIXING):
COMPLETE VEHICLES:
- "sandbike mk5" -> "VEHICLE_PARTS|sandbike|engine_mk5,chassis_mk5,hull_mk5,psu_mk5,tread_mk5|1"
- "assault ornithopter mk6" -> "VEHICLE_PARTS|assault_ornithopter|engine_mk6,chassis_mk6,cockpit_mk6,cabin_mk6,generator_mk6,tail_mk6,wing_mk6|1"
- "assault ornithopter mk6 with thruster" -> "VEHICLE_PARTS|assault_ornithopter|engine_mk6,chassis_mk6,cockpit_mk6,cabin_mk6,generator_mk6,tail_mk6,wing_mk6,thruster_mk6|1"
- "assault ornithopter mk6 with thruster and storage" -> "VEHICLE_PARTS|assault_ornithopter|engine_mk6,chassis_mk6,cockpit_mk6,cabin_mk6,generator_mk6,tail_mk6,wing_mk6,thruster_mk6,storage_mk5|1"
- "buggy mk6 with utility rear and cutteray" -> "VEHICLE_PARTS|buggy|engine_mk6,chassis_mk6,hull_mk6,psu_mk6,tread_mk6,utility_rear_mk6,cutteray_mk6|1"
- "scout ornithopter mk5 with mk4 thruster" -> "VEHICLE_PARTS|scout_ornithopter|engine_mk5,chassis_mk5,cockpit_mk5,generator_mk5,hull_mk5,wing_mk5,thruster_mk4|1"

INDIVIDUAL PARTS:
- "assault ornithopter thruster mk6" -> "assault_ornithopter_thruster_mk6|1"
- "scout ornithopter wing mk5" -> "scout_ornithopter_wing_mk5|1"
- "sandbike engine mk3" -> "sandbike_engine_mk3|1"

PART EXAMPLES:
- "sandbike engine mk3" -> "sandbike_engine_mk3|1"

Return ONLY the specified format with NO explanations."""
            
            user_message = f"""User request: "{user_query}"

Available items (sample):
{sample_text}

Match this request to an exact database key:"""
            
            response = await claude.create_message(
                system_message=system_message,
                user_message=user_message,
                max_tokens=150
            )
            
            result = response.strip()
            # Clean up any quotes or extra formatting
            if result.startswith('"') and result.endswith('"'):
                result = result[1:-1]
            elif result.startswith('"'):
                result = result[1:]
            
            # Parse Claude's response
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
                        print(f"DEBUG: Claude suggested non-existent item: {base_item}")
                        return self._smart_fallback_match(user_query, available_items)
            else:
                return self._smart_fallback_match(user_query, available_items)
                
        except Exception as e:
            print(f"DEBUG: Claude recipe interpretation failed: {e}")
            return self._fallback_parse(user_query)
    
    def _fallback_parse(self, query: str) -> tuple[str, int]:
        """Simple fallback parsing when Claude is unavailable"""
        parts = query.split()
        item_name = parts[0].lower() if parts else ""
        quantity = 1
        
        # Try to extract quantity from anywhere in the query
        for part in parts:
            if part.isdigit():
                quantity = int(part)
                break
        
        return item_name, quantity
    
    def _smart_fallback_match(self, query: str, available_items: list) -> tuple[str, int]:
        """Intelligent fallback matching using string similarity"""
        query_lower = query.lower()
        quantity = 1
        
        # Extract quantity if present
        import re
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
    
    async def handle_craft_command(self, message, craft_query: str):
        """Handle crafting command when mentioned with 'craft:' prefix"""
        try:
            if not craft_query.strip():
                await message.channel.send("Please specify what to craft. Example: `@bot craft: I need 5 healing kits`")
                return
            
            # Check if user wants full breakdown
            query_lower = craft_query.lower()
            full_breakdown = any(keyword in query_lower for keyword in [
                'full breakdown', 'complete breakdown', 'detailed breakdown', 
                'full materials', 'raw materials', 'all materials',
                'break down', 'breakdown'
            ])
            
            # Check if user wants materials by parts
            by_parts = any(keyword in query_lower for keyword in [
                'by parts', 'each part', 'part breakdown', 'per part',
                'part by part', 'individual parts', 'materials by part',
                'show parts', 'list parts'
            ])
            
            
            # Handle list command
            if craft_query.lower().strip() in ["list", "show all", "what can i craft", "available items"]:
                response = "**🏗️ Available Dune Awakening Recipes:**\n"
                
                # Use the new category system from JSON
                category_display_names = {
                    "healing": "🏥 Healing & Medicine",
                    "medicine": "💊 Medicine",
                    "consumable": "🍺 Food & Beverages", 
                    "equipment": "🎽 Equipment & Gear",
                    "standard_weapon": "⚔️ Standard Weapons",
                    "advanced_weapon": "🚀 Advanced Weapons",
                    "unique_weapon": "✨ Unique Weapons",
                    "building": "🏗️ Building Materials",
                    "refinery": "🏭 Refineries",
                    "vehicle": "🚁 Vehicle Components",
                    "material": "🧱 Base Materials",
                    "component": "⚙️ Components",
                    "tool": "🔧 Tools"
                }
                
                categories = get_categories()
                for category in sorted(categories):
                    items_in_category = get_items_by_category(category)
                    if items_in_category:
                        display_name = category_display_names.get(category, f"📦 {category.title()}")
                        response += f"\n**{display_name}:**\n"
                        response += ", ".join([item.replace('_', ' ').title() for item in sorted(items_in_category)]) + "\n"
                
                response += f"\n📊 **Total Items:** {len(list_craftable_items())}"
                response += "\n💡 **Tip:** You can use natural language! Try: `@bot craft: I need 3 mark 2 heal kits`"
                await message.channel.send(response)
                return
            
            # Use intelligent interpretation with Claude Haiku
            print(f"DEBUG: Interpreting craft query: '{craft_query}'")
            item_name, quantity = await self._interpret_recipe_request(craft_query)
            
            if item_name == "no_match":
                await self._handle_no_match(message, craft_query)
                return
            
            # Check if AI detected modifiers and override local detection
            ai_full_breakdown = 'FULL_BREAKDOWN' in item_name
            ai_by_parts = 'BY_PARTS' in item_name
            
            if ai_full_breakdown:
                full_breakdown = True
            if ai_by_parts:
                by_parts = True
            
            # Clean the item_name of modifiers for further processing
            # Preserve vehicle assembly formats but remove modifiers
            if item_name.startswith('VEHICLE_PARTS|') or item_name.startswith('VEHICLE_ASSEMBLY|'):
                # Split and rebuild without modifier parts
                parts = item_name.split('|')
                clean_parts = []
                for part in parts:
                    if part not in ['BY_PARTS', 'FULL_BREAKDOWN']:
                        clean_parts.append(part)
                item_name = '|'.join(clean_parts)
            else:
                # For single items, just take the first part
                item_name = item_name.split('|')[0]
            
            # Check if this is a flexible vehicle parts request
            if item_name.startswith('VEHICLE_PARTS|'):
                await self._handle_flexible_vehicle_parts(message, item_name, quantity, craft_query, full_breakdown, by_parts)
                return
            # Check if this is a legacy vehicle assembly request
            elif item_name.startswith('VEHICLE_ASSEMBLY|'):
                await self._handle_vehicle_assembly_with_llm(message, item_name, quantity, craft_query, full_breakdown, by_parts)
                return
            elif await self._is_vehicle_assembly_request(craft_query, item_name):
                await self._handle_vehicle_assembly(message, craft_query, item_name, quantity, full_breakdown, by_parts)
                return
            
            # Get recipe info for individual item
            recipe = get_recipe_info(item_name)
            if not recipe:
                await self._handle_recipe_not_found(message, item_name, craft_query)
                return
            
            # Calculate materials needed based on user preference
            if full_breakdown:
                materials, error = calculate_materials(item_name, quantity)
                breakdown_type = "raw"
            else:
                materials, error = calculate_direct_materials(item_name, quantity)
                breakdown_type = "direct"
            
            if error:
                await message.channel.send(f"❌ {error}")
                return
            
            # Format and send response
            response = await self._format_crafting_response(item_name, quantity, recipe, materials, breakdown_type)
            await message.channel.send(response)
            
        except Exception as e:
            print(f"DEBUG: Crafting handler error: {e}")
            await message.channel.send(f'❌ Crafting calculation failed: {str(e)}')
    
    async def _is_vehicle_assembly_request(self, query: str, matched_item: str) -> bool:
        """Check if user wants complete vehicle assembly vs individual part"""
        query_lower = query.lower()
        
        # Keywords that indicate complete vehicle assembly
        assembly_keywords = ['complete', 'full', 'entire', 'whole', 'build', 'assemble']
        if any(keyword in query_lower for keyword in assembly_keywords):
            return True
            
        # If query mentions vehicle type without specific part, assume assembly
        vehicle_types = ['sandbike', 'buggy', 'ornithopter', 'sandcrawler']
        part_types = ['engine', 'chassis', 'hull', 'wing', 'tread', 'cabin', 'cockpit']
        
        has_vehicle = any(vehicle in query_lower for vehicle in vehicle_types)
        has_specific_part = any(part in query_lower for part in part_types)
        
        return has_vehicle and not has_specific_part
    
    async def _handle_vehicle_assembly(self, message, query: str, base_item: str, quantity: int, full_breakdown: bool = False, by_parts: bool = False):
        """Handle complete vehicle assembly requests"""
        # Extract vehicle type and tier from query
        query_lower = query.lower()
        
        # Determine vehicle type and tier
        vehicle_info = self._extract_vehicle_info(query_lower)
        if not vehicle_info:
            await message.channel.send(f"❌ Could not determine vehicle type and tier from: '{query}'")
            return
        
        vehicle_type, tier = vehicle_info
        
        # Get all parts needed for this vehicle
        parts_needed = self._get_vehicle_parts(vehicle_type, tier)
        if not parts_needed:
            await message.channel.send(f"❌ No vehicle assembly data for {vehicle_type} {tier}")
            return
        
        # Calculate total materials for all parts
        total_materials = {}
        part_details = []
        
        for part_key in parts_needed:
            recipe = get_recipe_info(part_key)
            if recipe:
                if full_breakdown:
                    materials, _ = calculate_materials(part_key, quantity)
                else:
                    materials, _ = calculate_direct_materials(part_key, quantity)
                if materials:
                    for mat, qty in materials.items():
                        total_materials[mat] = total_materials.get(mat, 0) + qty
                    part_details.append((part_key, recipe))
        
        if not total_materials:
            await message.channel.send(f"❌ Could not calculate materials for {vehicle_type} {tier}")
            return
        
        # Determine mode for display
        if by_parts and full_breakdown:
            mode_text = "**📊 MODE 4:** By Parts + Full Breakdown (Complete trees for each part)"
        elif by_parts:
            mode_text = "**📊 MODE 3:** By Parts (Direct materials for each part)"
        elif full_breakdown:
            mode_text = "**📊 MODE 2:** Full Breakdown (Summary + complete trees)"
        else:
            mode_text = "**📊 MODE 1:** Default (Parts list + total materials summary)"
        
        # Format vehicle assembly response
        response = f"🚗 **Complete {vehicle_type.title()} {tier.upper()} Assembly**\n\n"
        response += f"{mode_text}\n\n"
        response += f"**Quantity:** {quantity}\n\n"
        
        response += f"**Required Parts ({len(part_details)}):**\n"
        for part_key, recipe in part_details:
            part_name = part_key.replace('_', ' ').title()
            response += f"- {part_name} (Station: {recipe.get('station', 'Unknown')})\n"
        
        if full_breakdown:
            response += f"\n**📦 Raw Materials Breakdown:**\n"
        else:
            response += f"\n**📦 Direct Materials Required:**\n"
        response += format_materials_list(total_materials)
        
        # Determine which mode to use based on user request
        if by_parts:
            # Mode 3 or 4: Show materials for each part individually
            messages_to_send = []
            current_message = response
            current_message += f"\n**🔧 Materials by Part:**\n"
            
            for part_key, recipe in part_details:
                part_display = part_key.replace('_', ' ').title()
                
                if full_breakdown:
                    # Mode 4: By parts + full breakdown (complete crafting trees for each part)
                    part_content = f"\n**{part_display}:**\n"
                    part_content += format_materials_tree(part_key, 1)
                else:
                    # Mode 3: By parts only (direct materials for each part)
                    part_materials, _ = calculate_direct_materials(part_key, 1)
                    # Multiply by vehicle quantity if needed
                    if quantity > 1 and part_materials:
                        part_materials = {mat: qty * quantity for mat, qty in part_materials.items()}
                    
                    part_content = f"\n**{part_display}:**\n"
                    if part_materials:
                        part_content += format_materials_list(part_materials)
                    else:
                        part_content += "- No materials needed\n"
                
                # Check if adding this part would exceed message limit
                if len(current_message + part_content) > 1900:  # Small buffer for Discord's 2000 char limit
                    # Send current message and start a new one
                    messages_to_send.append(current_message)
                    current_message = f"**🔧 Materials by Part (continued):**\n" + part_content
                else:
                    # Add to current message
                    current_message += part_content
            
            # Add final notes to the last message
            if quantity > 1:
                current_message += f"\n💡 Building {quantity} complete vehicles requires {len(part_details)} different crafting operations per vehicle."
            
            # Add the final message
            messages_to_send.append(current_message)
        elif full_breakdown:
            # Mode 2: Full breakdown (summary + complete crafting tree for each part)
            messages_to_send = []
            current_message = response
            current_message += f"\n\n**🔧 Complete Crafting Trees:**\n"
            
            for part_key, recipe in part_details:
                part_display = part_key.replace('_', ' ').title()
                
                # Build the complete part tree using raw materials
                part_content = f"\n**{part_display}:**\n"
                part_content += format_materials_tree(part_key, 1)
                
                # Check if adding this part would exceed message limit
                if len(current_message + part_content) > 1900:  # Small buffer for Discord's 2000 char limit
                    # Send current message and start a new one
                    messages_to_send.append(current_message)
                    current_message = f"**🔧 Complete Crafting Trees (continued):**\n" + part_content
                else:
                    # Add to current message
                    current_message += part_content
            
            # Add final notes to the last message
            if quantity > 1:
                current_message += f"\n💡 Building {quantity} complete vehicles requires {len(part_details)} different crafting operations per vehicle."
            
            # Add the final message
            messages_to_send.append(current_message)
        else:
            # Mode 1: Default (parts list + total materials summary only)
            messages_to_send = [response]
            if quantity > 1:
                messages_to_send[0] += f"\n💡 Building {quantity} complete vehicles requires {len(part_details)} different crafting operations per vehicle."
        
        # Send all messages
        for message_content in messages_to_send:
            await message.channel.send(message_content)
    
    async def _handle_flexible_vehicle_parts(self, message, parts_data: str, quantity: int, original_query: str, full_breakdown: bool = False, by_parts: bool = False):
        """Handle flexible vehicle parts assembly requests"""
        try:
            # Parse the parts data: VEHICLE_PARTS|vehicle_type|parts_list
            parts = parts_data.split('|')
            if len(parts) < 3:
                await message.channel.send("Error: Invalid vehicle parts format")
                return
            
            vehicle_type = parts[1].strip()
            parts_list_str = parts[2].strip()
            
            print(f"DEBUG: Flexible vehicle parts - {vehicle_type} with parts: {parts_list_str}")
            
            # Parse the parts list: "engine_mk6,chassis_mk3,hull_mk6,psu_mk6,tread_mk6"
            requested_parts = [part.strip() for part in parts_list_str.split(',') if part.strip()]
            
            # Convert to full database keys: "engine_mk6" -> "sandbike_engine_mk6"
            full_part_keys = []
            missing_parts = []
            
            from dune_crafting import list_craftable_items
            available_items = list_craftable_items()
            
            for part in requested_parts:
                # Build the full key: vehicle_type + "_" + part
                if part.startswith(vehicle_type + "_"):
                    # Already has vehicle prefix
                    full_key = part
                else:
                    # Add vehicle prefix
                    full_key = f"{vehicle_type}_{part}"
                
                if full_key in available_items:
                    full_part_keys.append(full_key)
                else:
                    print(f"DEBUG: Missing part: {full_key}")
                    missing_parts.append(part)
            
            if missing_parts:
                missing_str = ", ".join(missing_parts)
                await message.channel.send(f"❌ **Some parts not found in database:**\n{missing_str}\n\n**Available parts found:** {len(full_part_keys)}")
                return
            
            if not full_part_keys:
                await message.channel.send("❌ No valid parts found for this vehicle configuration")
                return
            
            # Calculate materials for all parts
            from dune_crafting import calculate_direct_materials, get_recipe_info, format_materials_list
            
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
                    
                    if isinstance(part_materials, dict):
                        for material, amount in part_materials.items():
                            total_materials[material] = total_materials.get(material, 0) + amount
                        part_details.append((part_key, recipe, display_multiplier))
                    else:
                        print(f"DEBUG: calculate_materials failed for {part_key}, returned: {part_materials}")
                        missing_parts.append(part_key)
                else:
                    missing_parts.append(part_key)
            
            if not total_materials:
                await message.channel.send(f"❌ Could not calculate materials for {vehicle_type} parts")
                return
            
            # Determine mode for display
            if by_parts and full_breakdown:
                mode_text = "**📊 MODE 4:** By Parts + Full Breakdown (Complete trees for each part)"
            elif by_parts:
                mode_text = "**📊 MODE 3:** By Parts (Direct materials for each part)"
            elif full_breakdown:
                mode_text = "**📊 MODE 2:** Full Breakdown (Summary + complete trees)"
            else:
                mode_text = "**📊 MODE 1:** Default (Parts list + total materials summary)"
            
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
            
            # Determine which mode to use based on user request
            if by_parts:
                # Mode 3 or 4: Show materials for each part individually
                messages_to_send = []
                current_message = response
                current_message += f"\n**🔧 Materials by Part:**\n"
                
                for i, (part_key, recipe, part_multiplier) in enumerate(part_details):
                    part_display = part_key.replace(f"{vehicle_type}_", "").replace("_", " ").title()
                    
                    if full_breakdown:
                        # Mode 4: By parts + full breakdown (complete crafting trees for each part)
                        if part_multiplier > 1:
                            part_content = f"\n**{part_display} (x{part_multiplier}):**\n"
                        else:
                            part_content = f"\n**{part_display}:**\n"
                        part_content += format_materials_tree(part_key, 1 if part_multiplier == 1 else part_multiplier)
                    else:
                        # Mode 3: By parts only (direct materials for each part)
                        part_materials, _ = calculate_direct_materials(part_key, 1)
                        # Multiply by vehicle quantity if needed
                        if quantity > 1 and part_materials:
                            part_materials = {mat: qty * quantity for mat, qty in part_materials.items()}
                        
                        if part_multiplier > 1:
                            part_content = f"\n**{part_display} (x{part_multiplier}):**\n"
                        else:
                            part_content = f"\n**{part_display}:**\n"
                        if part_materials:
                            part_content += format_materials_list(part_materials)
                        else:
                            part_content += "- No materials needed\n"
                    
                    # Check if adding this part would exceed message limit
                    if len(current_message + part_content) > 1900:  # Small buffer for Discord's 2000 char limit
                        # Send current message and start a new one
                        messages_to_send.append(current_message)
                        current_message = f"**🔧 Materials by Part (continued):**\n" + part_content
                    else:
                        # Add to current message
                        current_message += part_content
                
                # Add final notes to the last message
                if quantity > 1:
                    current_message += f"\n💡 **Note:** Building {quantity} vehicles requires {len(part_details)} different crafting operations per vehicle."
                current_message += f"\n✨ **Flexibility:** You can mix and match any tier parts within the same vehicle type!"
                
                # Add the final message
                messages_to_send.append(current_message)
            elif full_breakdown:
                # Mode 2: Full breakdown (summary + complete crafting tree for each part)
                messages_to_send = []
                current_message = response
                current_message += f"\n\n**🔧 Complete Crafting Trees:**\n"
                
                for i, (part_key, recipe, part_multiplier) in enumerate(part_details):
                    part_display = part_key.replace(f"{vehicle_type}_", "").replace("_", " ").title()
                    
                    # Build the complete part tree using raw materials
                    if part_multiplier > 1:
                        part_content = f"\n**{part_display} (x{part_multiplier}):**\n"
                    else:
                        part_content = f"\n**{part_display}:**\n"
                    part_content += format_materials_tree(part_key, 1 if part_multiplier == 1 else part_multiplier)
                    
                    # Check if adding this part would exceed message limit
                    if len(current_message + part_content) > 1900:  # Small buffer for Discord's 2000 char limit
                        # Send current message and start a new one
                        messages_to_send.append(current_message)
                        current_message = f"**🔧 Complete Crafting Trees (continued):**\n" + part_content
                    else:
                        # Add to current message
                        current_message += part_content
                
                # Add final notes to the last message
                if quantity > 1:
                    current_message += f"\n💡 **Note:** Building {quantity} vehicles requires {len(part_details)} different crafting operations per vehicle."
                current_message += f"\n✨ **Flexibility:** You can mix and match any tier parts within the same vehicle type!"
                
                # Add the final message
                messages_to_send.append(current_message)
            else:
                # Mode 1: Default (parts list + total materials summary only)
                messages_to_send = [response]
                if quantity > 1:
                    messages_to_send[0] += f"\n💡 **Note:** Building {quantity} vehicles requires {len(part_details)} different crafting operations per vehicle."
                messages_to_send[0] += f"\n✨ **Flexibility:** You can mix and match any tier parts within the same vehicle type!"
            
            # Send all messages
            for message_content in messages_to_send:
                await message.channel.send(message_content)
            
        except Exception as e:
            print(f"DEBUG: Flexible vehicle parts error: {e}")
            await message.channel.send(f"Error processing flexible vehicle parts: {str(e)}")

    async def _handle_vehicle_assembly_with_llm(self, message, assembly_data: str, quantity: int, original_query: str, full_breakdown: bool = False, by_parts: bool = False):
        """Use LLM to determine exact parts needed from JSON database"""
        try:
            # Parse the assembly intent
            parts = assembly_data.split('|')
            if len(parts) < 4:
                await message.channel.send("Error: Invalid vehicle assembly format")
                return
            
            vehicle_type = parts[1]
            tier = parts[2] 
            modules_str = parts[3]
            
            print(f"DEBUG: LLM vehicle assembly - {vehicle_type} {tier} with modules: {modules_str}")
            
            # Get all available items for the LLM to choose from
            available_items = list_craftable_items()
            
            # Filter items relevant to this vehicle type and tier
            relevant_items = [item for item in available_items 
                            if vehicle_type.replace('_', ' ') in item.replace('_', ' ') 
                            and tier in item]
            
            # Create a focused list for the LLM
            items_text = "\\n".join([f"- {item}" for item in relevant_items])
            
            if not config.has_anthropic_api():
                await message.channel.send("Claude API not available for vehicle assembly analysis")
                return
            
            # Create Claude client
            claude = AnthropicAPI(config.ANTHROPIC_API_KEY)
            
            system_message = """You are a Dune Awakening vehicle assembly expert. Given a user's vehicle request and available parts from our database, determine exactly which parts are needed.

TASK: Return a pipe-separated list of exact database keys for the parts needed.

RULES:
1. Use ONLY the exact keys from the provided available items list
2. Include all required parts for the vehicle to function
3. Add optional parts based on user's module specifications
4. Return format: "part1|part2|part3|..."
5. If modules are "none", include only required parts
6. If modules are "all_optional", include all available optional parts
7. For specific modules, include only those requested

VEHICLE KNOWLEDGE:
- Sandbikes need: engine, chassis, hull, psu, tread (x3 quantity)
- Ornithopters need: engine, chassis, cockpit/cabin, generator, wing(s), tail (assault/carrier)
- Buggies need: engine, chassis, psu, tread (x4), rear system
- Sandcrawlers need: engine, chassis, cabin, tread (x2), vacuum, centrifuge, psu

Return ONLY the pipe-separated list of exact database keys."""
            
            user_message = f"""User request: "{original_query}"
Vehicle type: {vehicle_type}
Tier: {tier}
Modules: {modules_str}

Available parts for this vehicle:
{items_text}

Determine the exact parts needed and return as pipe-separated list:"""
            
            response = await claude.create_message(
                system_message=system_message,
                user_message=user_message,
                max_tokens=200
            )
            
            # Parse the LLM response to get part list
            parts_list = [part.strip() for part in response.strip().split('|') if part.strip()]
            
            print(f"DEBUG: LLM determined parts: {parts_list}")
            
            if not parts_list:
                await message.channel.send("Error: Could not determine parts for vehicle assembly")
                return
            
            # Calculate materials for all parts
            total_materials = {}
            part_details = []
            missing_parts = []
            
            for part_key in parts_list:
                if part_key in available_items:
                    recipe = get_recipe_info(part_key)
                    if recipe:
                        if full_breakdown:
                            materials, _ = calculate_materials(part_key, quantity)
                        else:
                            materials, _ = calculate_direct_materials(part_key, quantity)
                        if materials:
                            for mat, qty in materials.items():
                                total_materials[mat] = total_materials.get(mat, 0) + qty
                            part_details.append((part_key, recipe))
                    else:
                        missing_parts.append(part_key)
                else:
                    print(f"DEBUG: LLM suggested non-existent part: {part_key}")
                    missing_parts.append(part_key)
            
            if not total_materials:
                await message.channel.send(f"Error: Could not calculate materials for {vehicle_type} {tier}")
                return
            
            # Format response
            response = f"**{vehicle_type.replace('_', ' ').title()} {tier.upper()} Assembly**\\n\\n"
            if quantity > 1:
                response += f"**Quantity:** {quantity}\\n\\n"
            
            # Show configuration
            if modules_str.lower() == 'none':
                response += "**Configuration:** Base vehicle (no optional modules)\\n\\n"
            elif modules_str.lower() == 'all_optional':
                response += "**Configuration:** Complete vehicle (all optional modules)\\n\\n"
            else:
                response += f"**Configuration:** With modules: {modules_str}\\n\\n"
            
            # List all parts
            response += f"**Parts Required ({len(part_details)}):**\\n"
            for part_key, recipe in part_details:
                part_name = part_key.replace('_', ' ').title()
                station = recipe.get('station', 'Unknown')
                response += f"- {part_name} (Station: {station})\\n"
            
            if full_breakdown:
                response += f"\\n**📦 Raw Materials Breakdown:**\\n"
            else:
                response += f"\\n**📦 Direct Materials Required:**\\n"
            response += format_materials_list(total_materials)
            
            # Determine which mode to use based on user request
            if by_parts:
                # Mode 3 or 4: Show materials for each part individually
                messages_to_send = []
                current_message = response
                current_message += f"\\n**🔧 Materials by Part:**\\n"
                
                for part_key, recipe in part_details:
                    part_display = part_key.replace('_', ' ').title()
                    
                    if full_breakdown:
                        # Mode 4: By parts + full breakdown (complete crafting trees for each part)
                        part_content = f"\\n**{part_display}:**\\n"
                        part_content += format_materials_tree(part_key, 1)
                    else:
                        # Mode 3: By parts only (direct materials for each part)
                        part_materials, _ = calculate_direct_materials(part_key, 1)
                        # Multiply by vehicle quantity if needed
                        if quantity > 1 and part_materials:
                            part_materials = {mat: qty * quantity for mat, qty in part_materials.items()}
                        part_content = f"\\n**{part_display}:**\\n"
                        if part_materials:
                            part_content += format_materials_list(part_materials)
                        else:
                            part_content += "- No materials needed\\n"
                    
                    # Check if adding this part would exceed message limit
                    if len(current_message + part_content) > 1900:  # Small buffer for Discord's 2000 char limit
                        # Send current message and start a new one
                        messages_to_send.append(current_message)
                        current_message = f"**🔧 Materials by Part (continued):**\\n" + part_content
                    else:
                        # Add to current message
                        current_message += part_content
                
                # Add final notes to the last message
                if missing_parts:
                    current_message += f"\\n**Note:** Some parts not found in database: {', '.join(missing_parts)}"
                if quantity > 1:
                    current_message += f"\\n**Note:** Building {quantity} vehicles requires {len(part_details)} different crafting operations per vehicle."
                
                # Add the final message
                messages_to_send.append(current_message)
            elif full_breakdown:
                # Mode 2: Full breakdown (summary + complete crafting tree for each part)
                messages_to_send = []
                current_message = response
                current_message += f"\\n\\n**🔧 Complete Crafting Trees:**\\n"
                
                for part_key, recipe in part_details:
                    part_display = part_key.replace('_', ' ').title()
                    
                    # Build the complete part tree using raw materials
                    part_content = f"\\n**{part_display}:**\\n"
                    part_content += format_materials_tree(part_key, 1)
                    
                    # Check if adding this part would exceed message limit
                    if len(current_message + part_content) > 1900:  # Small buffer for Discord's 2000 char limit
                        # Send current message and start a new one
                        messages_to_send.append(current_message)
                        current_message = f"**🔧 Complete Crafting Trees (continued):**\\n" + part_content
                    else:
                        # Add to current message
                        current_message += part_content
                
                # Add final notes to the last message
                if missing_parts:
                    current_message += f"\\n**Note:** Some parts not found in database: {', '.join(missing_parts)}"
                if quantity > 1:
                    current_message += f"\\n**Note:** Building {quantity} vehicles requires {len(part_details)} different crafting operations per vehicle."
                
                # Add the final message
                messages_to_send.append(current_message)
            else:
                # Mode 1: Default (parts list + total materials summary only)
                messages_to_send = [response]
                if missing_parts:
                    messages_to_send[0] += f"\\n**Note:** Some parts not found in database: {', '.join(missing_parts)}"
                if quantity > 1:
                    messages_to_send[0] += f"\\n**Note:** Building {quantity} vehicles requires {len(part_details)} different crafting operations per vehicle."
            
            # Send all messages
            for message_content in messages_to_send:
                await message.channel.send(message_content)
            
        except Exception as e:
            print(f"DEBUG: LLM vehicle assembly error: {e}")
            await message.channel.send(f"Error processing vehicle assembly: {str(e)}")
    
    async def _handle_vehicle_assembly_with_modules(self, message, assembly_data: str, quantity: int, full_breakdown: bool = False, by_parts: bool = False):
        """Handle vehicle assembly requests with specific module requirements from Claude"""
        try:
            # Parse the assembly data: VEHICLE_ASSEMBLY|vehicle_type|tier|modules
            parts = assembly_data.split('|')
            if len(parts) < 4:
                await message.channel.send("Error: Invalid vehicle assembly format from AI")
                return
            
            vehicle_type = parts[1]
            tier = parts[2] 
            modules_str = parts[3]
            
            print(f"DEBUG: Vehicle assembly - {vehicle_type} {tier} with modules: {modules_str}")
            
            # Get required parts for this vehicle
            required_parts = self._get_vehicle_parts(vehicle_type, tier)
            if not required_parts:
                await message.channel.send(f"Error: No parts found for {vehicle_type} {tier}")
                return
            
            # Parse module requirements
            if modules_str.lower() == 'none':
                optional_parts = []
            elif modules_str.lower() == 'all_optional':
                optional_parts = self._get_all_optional_parts(vehicle_type, tier)
            else:
                # Parse specific modules
                module_names = [m.strip() for m in modules_str.split(',') if m.strip()]
                optional_parts = self._get_specific_optional_parts(vehicle_type, tier, module_names)
            
            # Combine all parts needed
            all_parts = required_parts + optional_parts
            
            # Calculate total materials
            total_materials = {}
            part_details = []
            missing_parts = []
            
            for part_key in all_parts:
                recipe = get_recipe_info(part_key)
                if recipe:
                    if full_breakdown:
                        materials, _ = calculate_materials(part_key, quantity)
                    else:
                        materials, _ = calculate_direct_materials(part_key, quantity)
                    if materials:
                        for mat, qty in materials.items():
                            total_materials[mat] = total_materials.get(mat, 0) + qty
                        part_details.append((part_key, recipe, 'required' if part_key in required_parts else 'optional'))
                else:
                    missing_parts.append(part_key)
            
            if not total_materials:
                await message.channel.send(f"Error: Could not calculate materials for {vehicle_type} {tier}")
                return
            
            # Format response
            response = f"** {vehicle_type.replace('_', ' ').title()} {tier.upper()} Assembly**\\n\\n"
            if quantity > 1:
                response += f"**Quantity:** {quantity}\\n\\n"
            
            # Show module configuration
            if modules_str.lower() == 'none':
                response += "**Configuration:** Base vehicle (no optional modules)\\n\\n"
            elif modules_str.lower() == 'all_optional':
                response += "**Configuration:** Complete vehicle (all optional modules)\\n\\n"
            else:
                response += f"**Configuration:** With modules: {modules_str}\\n\\n"
            
            # List required parts
            required_count = len([p for p in part_details if p[2] == 'required'])
            optional_count = len([p for p in part_details if p[2] == 'optional'])
            
            response += f"**Required Parts ({required_count}):**\\n"
            for part_key, recipe, part_type in part_details:
                if part_type == 'required':
                    part_name = part_key.replace('_', ' ').title()
                    response += f"- {part_name}\\n"
            
            if optional_count > 0:
                response += f"\\n**Optional Parts ({optional_count}):**\\n"
                for part_key, recipe, part_type in part_details:
                    if part_type == 'optional':
                        part_name = part_key.replace('_', ' ').title()
                        response += f"- {part_name}\\n"
            
            if full_breakdown:
                response += f"\\n**📦 Raw Materials Breakdown:**\\n"
            else:
                response += f"\\n**📦 Direct Materials Required:**\\n"
            response += format_materials_list(total_materials)
            
            # Determine which mode to use based on user request
            if by_parts:
                # Mode 3 or 4: Show materials for each part individually
                messages_to_send = []
                current_message = response
                current_message += f"\\n**🔧 Materials by Part:**\\n"
                
                for part_key, recipe, part_type in part_details:
                    part_display = part_key.replace('_', ' ').title()
                    
                    if full_breakdown:
                        # Mode 4: By parts + full breakdown (complete crafting trees for each part)
                        part_content = f"\\n**{part_display}:**\\n"
                        part_content += format_materials_tree(part_key, 1)
                    else:
                        # Mode 3: By parts only (direct materials for each part)
                        part_materials, _ = calculate_direct_materials(part_key, 1)
                        # Multiply by vehicle quantity if needed
                        if quantity > 1 and part_materials:
                            part_materials = {mat: qty * quantity for mat, qty in part_materials.items()}
                        part_content = f"\\n**{part_display}:**\\n"
                        if part_materials:
                            part_content += format_materials_list(part_materials)
                        else:
                            part_content += "- No materials needed\\n"
                    
                    # Check if adding this part would exceed message limit
                    if len(current_message + part_content) > 1900:  # Small buffer for Discord's 2000 char limit
                        # Send current message and start a new one
                        messages_to_send.append(current_message)
                        current_message = f"**🔧 Materials by Part (continued):**\\n" + part_content
                    else:
                        # Add to current message
                        current_message += part_content
                
                # Add final notes to the last message
                if missing_parts:
                    current_message += f"\\n**Missing recipes:** {', '.join(missing_parts)}"
                if quantity > 1:
                    current_message += f"\\n**Note:** Building {quantity} vehicles requires {len(part_details)} different crafting operations per vehicle."
                
                # Add the final message
                messages_to_send.append(current_message)
            elif full_breakdown:
                # Mode 2: Full breakdown (summary + complete crafting tree for each part)
                messages_to_send = []
                current_message = response
                current_message += f"\\n\\n**🔧 Complete Crafting Trees:**\\n"
                
                for part_key, recipe, part_type in part_details:
                    part_display = part_key.replace('_', ' ').title()
                    
                    # Build the complete part tree using raw materials
                    part_content = f"\\n**{part_display}:**\\n"
                    part_content += format_materials_tree(part_key, 1)
                    
                    # Check if adding this part would exceed message limit
                    if len(current_message + part_content) > 1900:  # Small buffer for Discord's 2000 char limit
                        # Send current message and start a new one
                        messages_to_send.append(current_message)
                        current_message = f"**🔧 Complete Crafting Trees (continued):**\\n" + part_content
                    else:
                        # Add to current message
                        current_message += part_content
                
                # Add final notes to the last message
                if missing_parts:
                    current_message += f"\\n**Missing recipes:** {', '.join(missing_parts)}"
                if quantity > 1:
                    current_message += f"\\n**Note:** Building {quantity} vehicles requires {len(part_details)} different crafting operations per vehicle."
                
                # Add the final message
                messages_to_send.append(current_message)
            else:
                # Mode 1: Default (parts list + total materials summary only)
                messages_to_send = [response]
                if missing_parts:
                    messages_to_send[0] += f"\\n**Missing recipes:** {', '.join(missing_parts)}"
                if quantity > 1:
                    messages_to_send[0] += f"\\n**Note:** Building {quantity} vehicles requires {len(part_details)} different crafting operations per vehicle."
            
            # Send all messages
            for message_content in messages_to_send:
                await message.channel.send(message_content)
            
        except Exception as e:
            print(f"DEBUG: Vehicle assembly with modules error: {e}")
            await message.channel.send(f"Error processing vehicle assembly: {str(e)}")
    
    def _get_all_optional_parts(self, vehicle_type: str, tier: str) -> list:
        """Get all available optional parts for a vehicle type and tier"""
        available_items = list_craftable_items()
        optional_parts = []
        
        # Define optional parts by vehicle type
        optional_templates = {
            'sandbike': {
                'mk1': ['backseat'],
                'mk2+': ['booster', 'storage']
            },
            'buggy': {
                'all': ['booster']  # Note: rear variants handled separately
            },
            'scout_ornithopter': {
                'mk4+': ['storage', 'rocket_launcher'],
                'standalone': ['scan']  # Can always be added
            },
            'assault_ornithopter': {
                'mk5+': ['storage', 'rocket_launcher', 'thruster']
            },
            'carrier_ornithopter': {
                'mk6': ['thruster']
            }
        }
        
        if vehicle_type in optional_templates:
            templates = optional_templates[vehicle_type]
            
            # Add tier-specific parts
            for tier_key, parts in templates.items():
                if tier_key == 'all' or tier_key == f'{tier}' or (tier_key.endswith('+') and self._tier_meets_requirement(tier, tier_key)):
                    for part in parts:
                        part_key = f"{vehicle_type}_{part}_{tier}"
                        if part_key in available_items:
                            optional_parts.append(part_key)
            
            # Add standalone parts
            if 'standalone' in templates:
                for part in templates['standalone']:
                    part_key = f"{vehicle_type}_{part}_{tier}"
                    if part_key in available_items:
                        optional_parts.append(part_key)
        
        return optional_parts
    
    def _get_specific_optional_parts(self, vehicle_type: str, tier: str, module_names: list) -> list:
        """Get specific optional parts based on module names"""
        available_items = list_craftable_items()
        optional_parts = []
        
        for module_name in module_names:
            # Normalize module name
            module_name = module_name.lower().replace(' ', '_')
            
            # Try exact match first
            part_key = f"{vehicle_type}_{module_name}_{tier}"
            if part_key in available_items:
                optional_parts.append(part_key)
                continue
            
            # Try common variations
            variations = [
                f"{vehicle_type}_{module_name}_module_{tier}",
                f"{vehicle_type}_{module_name}s_{tier}",  # plural
            ]
            
            found = False
            for variation in variations:
                if variation in available_items:
                    optional_parts.append(variation)
                    found = True
                    break
            
            if not found:
                print(f"DEBUG: Could not find optional part for {vehicle_type} {module_name} {tier}")
        
        return optional_parts
    
    def _tier_meets_requirement(self, tier: str, requirement: str) -> bool:
        """Check if tier meets a requirement like 'mk4+' """
        if not requirement.endswith('+'):
            return tier == requirement
        
        required_num = int(requirement.replace('mk', '').replace('+', ''))
        tier_num = int(tier.replace('mk', ''))
        
        return tier_num >= required_num
    
    def _extract_vehicle_info(self, query: str) -> tuple[str, str] or None:
        """Extract vehicle type and tier from query"""
        import re
        
        # Extract tier (mk1, mk2, etc.)
        tier_match = re.search(r'mk\s*(\d+)', query)
        tier = f"mk{tier_match.group(1)}" if tier_match else None
        
        # Determine vehicle type
        if 'sandbike' in query:
            return ('sandbike', tier or 'mk1')
        elif 'scout ornithopter' in query or ('scout' in query and 'ornithopter' in query):
            return ('scout_ornithopter', tier or 'mk4')
        elif 'assault ornithopter' in query or ('assault' in query and 'ornithopter' in query):
            return ('assault_ornithopter', tier or 'mk5')
        elif 'carrier ornithopter' in query or ('carrier' in query and 'ornithopter' in query):
            return ('carrier_ornithopter', 'mk6')
        elif 'buggy' in query:
            return ('buggy', tier or 'mk3')
        elif 'sandcrawler' in query:
            return ('sandcrawler', 'mk6')
        
        return None
    
    def _get_vehicle_parts(self, vehicle_type: str, tier: str) -> list:
        """Get all required parts for a vehicle type and tier"""
        available_items = list_craftable_items()
        
        # Define required parts by vehicle type
        part_templates = {
            'sandbike': ['engine', 'chassis', 'hull', 'psu', 'tread'],
            'buggy': ['engine', 'chassis', 'psu', 'tread', 'rear'],  # Note: rear has variants
            'scout_ornithopter': ['engine', 'chassis', 'cockpit', 'generator', 'hull', 'wing'],
            'assault_ornithopter': ['engine', 'chassis', 'cockpit', 'cabin', 'generator', 'tail', 'wing'],
            'carrier_ornithopter': ['engine', 'chassis', 'generator', 'wing'],
            'sandcrawler': ['engine', 'chassis', 'cabin', 'tread', 'vacuum', 'centrifuge', 'psu']
        }
        
        if vehicle_type not in part_templates:
            return []
        
        # Build part keys and verify they exist
        parts = []
        for part in part_templates[vehicle_type]:
            part_key = f"{vehicle_type}_{part}_{tier}"
            if part_key in available_items:
                parts.append(part_key)
        
        # Handle special cases
        if vehicle_type == 'sandbike' and tier == 'mk1':
            # Add backseat for mk1
            backseat_key = f"sandbike_backseat_{tier}"
            if backseat_key in available_items:
                parts.append(backseat_key)
        
        return parts
    
    async def _handle_no_match(self, message, query: str):
        """Handle when no recipe match is found"""
        # Try to find similar items
        available_items = list_craftable_items()
        suggestions = self._find_similar_items(query, available_items)
        
        response = f"❌ **No exact match found for:** \"{query}\"\n\n"
        
        if suggestions:
            response += "**Similar items:**\n"
            for item in suggestions[:5]:
                display_name = item.replace('_', ' ').title()
                response += f"- {display_name}\n"
            response += "\n"
        
        response += "**💡 Tips:**\n"
        response += "- Use `craft: list` to see all categories\n"
        response += "- Try `craft: karpov 38 plastanium` for weapons\n"
        response += "- Try `craft: sandbike mk3` for vehicles\n"
        response += "- Include tier level (mk1, mk2, etc.)\n"
        
        await message.channel.send(response)
    
    def _find_similar_items(self, query: str, available_items: list) -> list:
        """Find items similar to the query"""
        query_words = set(query.lower().replace('mk', 'mk').split())
        
        scored_items = []
        for item in available_items:
            item_words = set(item.replace('_', ' ').split())
            
            # Calculate similarity score
            common_words = query_words.intersection(item_words)
            if common_words:
                score = len(common_words) / len(query_words)
                scored_items.append((item, score))
        
        # Sort by score and return top matches
        scored_items.sort(key=lambda x: x[1], reverse=True)
        return [item for item, score in scored_items if score > 0.3]
    
    async def _handle_recipe_not_found(self, message, item_name: str, original_query: str):
        """Handle when matched item has no recipe"""
        suggestions = self._find_similar_items(original_query, list_craftable_items())
        
        response = f"❌ **Recipe not found for:** {item_name.replace('_', ' ').title()}\n\n"
        
        if suggestions:
            response += "**Did you mean:**\n"
            for item in suggestions[:3]:
                display_name = item.replace('_', ' ').title()
                response += f"- {display_name}\n"
        
        response += f"\n**Debug:** Matched '{original_query}' to '{item_name}' but no recipe exists."
        await message.channel.send(response)
    
    async def _format_crafting_response(self, item_name: str, quantity: int, recipe: dict, materials: dict, breakdown_type: str = "direct") -> str:
        """Format the crafting response with proper styling"""
        station = recipe.get('station', 'Unknown')
        item_display = item_name.replace('_', ' ').title()
        
        # Determine mode for display
        if breakdown_type == "raw":
            mode_text = "**📊 MODE 2:** Full Breakdown (Complete crafting tree)"
        else:
            mode_text = "**📊 MODE 1:** Default (Direct materials only)"
        
        response = f"🔧 **Dune Awakening - Crafting Recipe**\n\n"
        response += f"{mode_text}\n\n"
        response += f"**Item:** {item_display}\n"
        
        if quantity > 1:
            response += f"**Quantity:** {quantity:,}\n"
        
        response += f"**Station:** {station}\n"
        
        # Add intel requirements if present
        if 'intel_requirement' in recipe:
            intel = recipe['intel_requirement']
            response += f"**Intel:** {intel.get('points', 0)} points"
            if intel.get('total_spent', 0) > 0:
                response += f" ({intel['total_spent']} total required)"
            response += "\n"
        
        # Add direct ingredients
        if recipe.get('ingredients'):
            response += f"\n**Direct Ingredients:**\n"
            for ingredient, qty in recipe['ingredients'].items():
                response += f"- {ingredient.replace('_', ' ').title()}: {qty * quantity:,}\n"
        
        if breakdown_type == "raw":
            response += f"\n**📦 Raw Materials Breakdown:**\n"
            response += format_materials_list(materials)
            response += f"\n**🔧 Complete Crafting Tree:**\n"
            response += format_materials_tree(item_name, quantity)
        else:
            response += f"\n**📦 Direct Materials Required:**\n"
            response += format_materials_list(materials)
        
        # Add description if available
        if 'description' in recipe:
            response += f"\n**Description:** {recipe['description']}"
        
        # Add tips for large quantities
        if quantity > 10:
            response += f"\n\n💡 **Tip:** Crafting {quantity:,} {item_display} requires significant resources!"
        
        return response

async def setup(bot):
    await bot.add_cog(CraftingHandler(bot))