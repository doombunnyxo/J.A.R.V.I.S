"""
WoW Character Management Commands
Commands for managing stored WoW characters
"""

import discord
from discord.ext import commands
from typing import Optional
from ..wow.character_manager import character_manager
from ..utils.logging import get_logger

logger = get_logger(__name__)


class WoWCharacterCommands(commands.Cog):
    """Commands for managing WoW characters"""
    
    def __init__(self, bot):
        self.bot = bot
        self._executing_commands = set()
    
    @commands.command(name='add_char')
    async def add_character(self, ctx, *, args: str = None):
        """
        Add a WoW character to your list
        
        Usage:
        !add_char <character> <realm> [region]
        !add_char Thrall Mal'Ganis       # defaults to US
        !add_char Gandalf Stormrage eu
        """
        command_key = f"add_char_{ctx.author.id}"
        if command_key in self._executing_commands:
            return
        
        self._executing_commands.add(command_key)
        
        try:
            if not args:
                await ctx.send("❌ **Usage**: `!add_char <character> <realm> [region]`\nExample: `!add_char Thrall Mal'Ganis`")
                return
            
            parts = args.strip().split()
            
            if len(parts) < 2:
                await ctx.send("❌ **Usage**: `!add_char <character> <realm> [region]`")
                return
            
            character = parts[0]
            realm = parts[1]
            region = parts[2].lower() if len(parts) > 2 else "us"
            
            # Validate region
            valid_regions = ["us", "eu", "kr", "tw", "cn"]
            if region not in valid_regions:
                await ctx.send(f"❌ **Invalid region**: `{region}`. Valid regions: {', '.join(valid_regions)}")
                return
            
            # Add character
            result = await character_manager.add_character(
                ctx.author.id,
                character,
                realm,
                region
            )
            
            await ctx.send(result["message"])
            
        except Exception as e:
            logger.error(f"Add character command error: {e}")
            await ctx.send(f"❌ **Error**: Failed to add character")
        finally:
            self._executing_commands.discard(command_key)
    
    @commands.command(name='set_main')
    async def set_main_character(self, ctx, char_number: Optional[int] = None):
        """
        Set your main character from your character list
        
        Usage:
        !set_main       # Shows your character list
        !set_main 2     # Sets character #2 as your main
        """
        command_key = f"set_main_{ctx.author.id}"
        if command_key in self._executing_commands:
            return
        
        self._executing_commands.add(command_key)
        
        try:
            characters = await character_manager.get_all_characters(ctx.author.id)
            
            if not characters:
                await ctx.send("❌ You have no characters stored. Use `!add_char` to add characters first")
                return
            
            # If no number provided, show character list
            if char_number is None:
                main_idx = await character_manager.get_main_character_index(ctx.author.id)
                
                embed = discord.Embed(
                    title="🎮 Your WoW Characters",
                    description="Use `!set_main <number>` to set your main character",
                    color=0x3498db
                )
                
                for i, char in enumerate(characters):
                    is_main = "⭐ **MAIN**" if i == main_idx else ""
                    embed.add_field(
                        name=f"#{i + 1} - {char['name']}",
                        value=f"{char['realm']} ({char['region'].upper()}) {is_main}",
                        inline=False
                    )
                
                await ctx.send(embed=embed)
                return
            
            # Convert to 0-based index
            character_index = char_number - 1
            
            # Set main character
            result = await character_manager.set_main_character(ctx.author.id, character_index)
            await ctx.send(result["message"])
            
        except Exception as e:
            logger.error(f"Set main character command error: {e}")
            await ctx.send(f"❌ **Error**: Failed to set main character")
        finally:
            self._executing_commands.discard(command_key)
    
    @commands.command(name='list_chars')
    async def list_characters(self, ctx):
        """
        List all your WoW characters
        
        Usage:
        !list_chars
        """
        command_key = f"list_chars_{ctx.author.id}"
        if command_key in self._executing_commands:
            return
        
        self._executing_commands.add(command_key)
        
        try:
            characters = await character_manager.get_all_characters(ctx.author.id)
            
            if not characters:
                await ctx.send("❌ You have no characters stored. Use `!add_char` to add characters")
                return
            
            main_idx = await character_manager.get_main_character_index(ctx.author.id)
            
            embed = discord.Embed(
                title="🎮 Your WoW Characters",
                color=0x2ecc71
            )
            
            for i, char in enumerate(characters):
                is_main = "⭐" if i == main_idx else ""
                embed.add_field(
                    name=f"{is_main} #{i + 1} - {char['name']}",
                    value=f"{char['realm']} ({char['region'].upper()})",
                    inline=True
                )
            
            embed.set_footer(text=f"Total: {len(characters)} character(s) | Use !set_main to set your main")
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"List characters command error: {e}")
            await ctx.send(f"❌ **Error**: Failed to list characters")
        finally:
            self._executing_commands.discard(command_key)
    
    @commands.command(name='remove_char')
    async def remove_character(self, ctx, char_number: Optional[int] = None):
        """
        Remove a character from your list
        
        Usage:
        !remove_char 2    # Removes character #2
        """
        command_key = f"remove_char_{ctx.author.id}"
        if command_key in self._executing_commands:
            return
        
        self._executing_commands.add(command_key)
        
        try:
            if char_number is None:
                await ctx.send("❌ **Usage**: `!remove_char <number>`\nUse `!list_chars` to see your character numbers")
                return
            
            # Convert to 0-based index
            character_index = char_number - 1
            
            result = await character_manager.remove_character(ctx.author.id, character_index)
            await ctx.send(result["message"])
            
        except Exception as e:
            logger.error(f"Remove character command error: {e}")
            await ctx.send(f"❌ **Error**: Failed to remove character")
        finally:
            self._executing_commands.discard(command_key)
    
    @commands.command(name='clear_chars')
    async def clear_characters(self, ctx):
        """
        Clear all your WoW characters
        
        Usage:
        !clear_chars
        """
        command_key = f"clear_chars_{ctx.author.id}"
        if command_key in self._executing_commands:
            return
        
        self._executing_commands.add(command_key)
        
        try:
            # Add confirmation
            characters = await character_manager.get_all_characters(ctx.author.id)
            if not characters:
                await ctx.send("❌ You have no characters to clear")
                return
            
            embed = discord.Embed(
                title="⚠️ Confirm Clear All Characters",
                description=f"Are you sure you want to remove all {len(characters)} character(s)?",
                color=0xe74c3c
            )
            
            confirm_msg = await ctx.send(embed=embed)
            await confirm_msg.add_reaction('✅')
            await confirm_msg.add_reaction('❌')
            
            def check(reaction, user):
                return (user == ctx.author and 
                       str(reaction.emoji) in ['✅', '❌'] and 
                       reaction.message.id == confirm_msg.id)
            
            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
                
                if str(reaction.emoji) == '✅':
                    result = await character_manager.clear_all_characters(ctx.author.id)
                    await ctx.send(result["message"])
                else:
                    await ctx.send("❌ Clear cancelled")
                    
            except TimeoutError:
                await ctx.send("❌ Clear cancelled (timeout)")
            
        except Exception as e:
            logger.error(f"Clear characters command error: {e}")
            await ctx.send(f"❌ **Error**: Failed to clear characters")
        finally:
            self._executing_commands.discard(command_key)


async def setup(bot):
    await bot.add_cog(WoWCharacterCommands(bot))