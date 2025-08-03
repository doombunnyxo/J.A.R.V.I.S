import discord
from discord.ext import commands
from dune_crafting import calculate_materials, get_recipe_info, list_craftable_items, format_materials_list, get_items_by_category, get_categories
from ..config import config
from groq import Groq

class CraftingHandler(commands.Cog):
    """Dune Awakening crafting calculator"""
    
    def __init__(self, bot):
        self.bot = bot
        self.groq_client = None
        self._initialize_groq()
    
    def _initialize_groq(self):
        """Initialize Groq client for recipe interpretation"""
        try:
            if config.has_groq_api():
                self.groq_client = Groq(api_key=config.GROQ_API_KEY)
                print("DEBUG: Groq client initialized for crafting system")
            else:
                print("Warning: Groq API not available for intelligent recipe parsing")
        except Exception as e:
            print(f"Failed to initialize Groq for crafting: {e}")
            self.groq_client = None
    
    async def _interpret_recipe_request(self, user_query: str) -> tuple[str, int]:
        """Use Groq to interpret natural language recipe requests"""
        if not self.groq_client:
            # Fallback to simple parsing if Groq not available
            parts = user_query.split()
            item_name = parts[0].lower() if parts else ""
            quantity = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
            return item_name, quantity
        
        try:
            # Get available recipes for context
            available_items = list_craftable_items()
            items_list = ", ".join([item.replace('_', ' ').title() for item in available_items])
            
            system_prompt = f"""You are a Dune Awakening crafting assistant. Your job is to interpret user requests for crafting recipes and return the exact item name and quantity.

AVAILABLE CRAFTABLE ITEMS:
{items_list}

INSTRUCTIONS:
1. Parse the user's request to identify what item they want to craft
2. Determine the quantity they want (default to 1 if not specified)
3. Match their request to the closest available item from the list above
4. Return ONLY in this exact format: "item_name|quantity"
5. Use the exact item_name format (lowercase with underscores, e.g., "healkit_mk2")
6. If no close match is found, return "unknown|1"

EXAMPLES:
- "I need 5 healing kits" → "healkit|5"
- "craft me a mark 2 heal kit" → "healkit_mk2|1"
- "spice beer please" → "melange_spiced_beer|1"
- "make 3 stillsuits" → "saturnine_stillsuit_garment|3"
- "foundation blocks" → "foundation_structure|1"
- "walls for my base" → "wall|1"
- "some aluminum ingots" → "aluminum_ingot|1"
- "glasser weapon" → "glasser|1"
- "piter's disruptor" → "piters_disruptor|1"
- "house vulcan weapon" → "house_vulcan_gau_92|1"
- "the tapper rifle" → "the_tapper|1"
- "eviscerator shotgun" → "eviscerator|1"
- "karpov rifle" → "karpov_38|1"
- "standard karpov" → "standard_karpov_38|1"
- "basic knife" → "scrap_metal_knife|1"
- "standard sword" → "standard_sword|1"
- "house sword" → "house_sword|1"
- "way of the desert" → "way_of_the_desert|1"
- "cope pistol" → "cope|1"
- "scrubber rifle" → "scrubber|1"
- "assassin's rifle" → "assassins_rifle|1"
- "shock sword" → "shock_sword|1"
- "steel ingots" → "steel_ingot|1"
- "gun parts" → "gun_parts|1"
- "blade parts" → "blade_parts|1"

Be flexible with variations like "mk2/mark 2", "heal kit/healkit", "spice beer/melange beer", etc."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Parse this crafting request: {user_query}"}
            ]
            
            completion = self.groq_client.chat.completions.create(
                messages=messages,
                model=config.AI_MODEL,
                max_tokens=50,
                temperature=0.1  # Low temperature for consistent parsing
            )
            
            response = completion.choices[0].message.content.strip()
            print(f"DEBUG: Groq recipe interpretation - '{user_query}' → '{response}'")
            
            # Parse the response
            if '|' in response:
                item_name, quantity_str = response.split('|', 1)
                try:
                    quantity = int(quantity_str)
                except ValueError:
                    quantity = 1
                return item_name.strip().lower(), quantity
            else:
                return "unknown", 1
                
        except Exception as e:
            print(f"DEBUG: Recipe interpretation failed: {e}")
            # Fallback to simple parsing
            parts = user_query.split()
            item_name = parts[0].lower() if parts else ""
            quantity = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
            return item_name, quantity
    
    async def handle_craft_command(self, message, craft_query: str):
        """Handle crafting command when mentioned with 'craft:' prefix"""
        try:
            if not craft_query.strip():
                await message.channel.send("Please specify what to craft. Example: `@bot craft: I need 5 healing kits`")
                return
            
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
            
            # Use intelligent interpretation
            print(f"DEBUG: Interpreting craft query: '{craft_query}'")
            item_name, quantity = await self._interpret_recipe_request(craft_query)
            
            if item_name == "unknown":
                await message.channel.send(f"❌ I couldn't understand what you want to craft from: '{craft_query}'\n\nTry being more specific, or use `@bot craft: list` to see available recipes.")
                return
            
            # Get recipe info
            recipe = get_recipe_info(item_name)
            if not recipe:
                # Try to suggest similar items
                available_items = list_craftable_items()
                suggestions = [item for item in available_items if item_name.lower() in item.lower() or item.lower() in item_name.lower()]
                
                suggestion_text = ""
                if suggestions:
                    suggestion_text = f"\n\n**Did you mean one of these?**\n" + ", ".join([item.replace('_', ' ').title() for item in suggestions[:5]])
                
                await message.channel.send(f"❌ Recipe for '{item_name.replace('_', ' ').title()}' not found.{suggestion_text}\n\nUse `@bot craft: list` to see all available recipes.")
                return
            
            # Calculate materials needed
            materials, error = calculate_materials(item_name, quantity)
            if error:
                await message.channel.send(f"❌ {error}")
                return
            
            # Format response with improved styling
            station = recipe.get('station', 'Unknown')
            item_display = item_name.replace('_', ' ').title()
            
            response = f"🏗️ **Dune Awakening - Crafting Calculator**\n"
            response += f"**Item:** {item_display}\n"
            response += f"**Quantity:** {quantity:,}\n"
            response += f"**Crafting Station:** {station}\n\n"
            response += "**📦 Raw Materials Needed:**\n"
            response += format_materials_list(materials)
            
            # Add helpful tip for large quantities
            if quantity > 10:
                response += f"\n💡 **Tip:** Crafting {quantity:,} {item_display} will require significant resources. Consider setting up automated production lines!"
            
            await message.channel.send(response)
            
        except Exception as e:
            await message.channel.send(f'❌ Crafting calculation failed: {str(e)}')

async def setup(bot):
    await bot.add_cog(CraftingHandler(bot))