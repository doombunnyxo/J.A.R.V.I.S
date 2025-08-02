import discord
from discord.ext import commands
from dune_crafting import calculate_materials, get_recipe_info, list_craftable_items, format_materials_list

class CraftingHandler(commands.Cog):
    """Dune Awakening crafting calculator"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def handle_craft_command(self, message, craft_query: str):
        """Handle crafting command when mentioned with 'craft:' prefix"""
        try:
            parts = craft_query.split()
            if not parts:
                await message.channel.send("Please specify what to craft. Example: `@bot craft: stillsuit 2`")
                return
            
            if parts[0].lower() == "list":
                items = list_craftable_items()
                response = "**Available Crafting Recipes:**\n"
                response += ", ".join([item.replace('_', ' ').title() for item in items])
                await message.channel.send(response)
                return
            
            item_name = parts[0].lower()
            quantity = 1
            
            if len(parts) > 1 and parts[1].isdigit():
                quantity = int(parts[1])
            
            # Get recipe info
            recipe = get_recipe_info(item_name)
            if not recipe:
                await message.channel.send(f"Recipe for '{item_name.replace('_', ' ').title()}' not found. Use `@bot craft: list` to see available recipes.")
                return
            
            # Calculate materials needed
            materials, error = calculate_materials(item_name, quantity)
            if error:
                await message.channel.send(error)
                return
            
            # Format response
            station = recipe.get('station', 'Unknown')
            response = f"**Crafting Calculator - {item_name.replace('_', ' ').title()}**\n"
            response += f"Quantity: {quantity}\n"
            response += f"Crafting Station: {station}\n\n"
            response += "**Raw Materials Needed:**\n"
            response += format_materials_list(materials)
            
            await message.channel.send(response)
            
        except Exception as e:
            await message.channel.send(f'Crafting calculation failed: {str(e)}')

async def setup(bot):
    await bot.add_cog(CraftingHandler(bot))