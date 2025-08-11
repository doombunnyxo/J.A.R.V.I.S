"""
WoW Character Management Commands
Commands for managing stored WoW characters
"""

import discord
from discord.ext import commands
from typing import Optional
import json
from pathlib import Path
from ..wow.character_manager import character_manager
from ..config import config
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
    
    @commands.command(name='debug_chars')
    async def debug_characters(self, ctx):
        """
        Debug command to check character data structure (Admin only)
        
        Usage:
        !debug_chars
        """
        # Prevent duplicate execution
        command_key = f"debug_chars_{ctx.author.id}"
        if command_key in self._executing_commands:
            return
        
        self._executing_commands.add(command_key)
        
        try:
            # Check if user is admin
            if str(ctx.author.id) != str(config.AUTHORIZED_USER_ID):
                await ctx.send("❌ This command is admin-only")
                return
            
            # Show raw data structure
            embed = discord.Embed(
                title="🔧 Character Manager Debug Info",
                color=0xe74c3c
            )
            
            # File info
            char_file = Path("data/wow_characters.json")
            file_exists = char_file.exists()
            file_size = char_file.stat().st_size if file_exists else 0
            
            embed.add_field(
                name="📁 File Status",
                value=f"**Exists**: {file_exists}\n**Size**: {file_size} bytes\n**Path**: {char_file.absolute()}",
                inline=False
            )
            
            # Data structure in memory
            total_users = len(character_manager.data)
            total_chars = 0
            sample_data = {}
            
            # Count all characters properly
            for user_id, user_data in character_manager.data.items():
                if isinstance(user_data, dict) and "characters" in user_data:
                    total_chars += len(user_data["characters"])
            
            # Get sample of first user (anonymized)
            if character_manager.data:
                first_user_id = list(character_manager.data.keys())[0]
                first_user_data = character_manager.data[first_user_id]
                sample_data = {
                    "user_id": first_user_id[:8] + "...",
                    "type": type(first_user_data).__name__,
                    "has_characters": "characters" in first_user_data if isinstance(first_user_data, dict) else False,
                    "char_count": len(first_user_data.get("characters", [])) if isinstance(first_user_data, dict) else 0,
                    "keys": list(first_user_data.keys()) if isinstance(first_user_data, dict) else []
                }
            
            embed.add_field(
                name="📊 In-Memory Data",
                value=f"**Total Users**: {total_users}\n**Total Characters**: {total_chars}\n**Data Type**: {type(character_manager.data).__name__}",
                inline=False
            )
            
            if sample_data:
                sample_text = "```json\n"
                sample_text += json.dumps(sample_data, indent=2)[:400]
                sample_text += "\n```"
                embed.add_field(
                    name="🔍 Sample Structure",
                    value=sample_text,
                    inline=False
                )
            
            # Try to load fresh from file
            if file_exists:
                try:
                    with open(char_file, 'r', encoding='utf-8') as f:
                        fresh_data = json.load(f)
                        fresh_users = len(fresh_data)
                        fresh_chars = 0
                        for user_data in fresh_data.values():
                            if isinstance(user_data, dict) and "characters" in user_data:
                                fresh_chars += len(user_data["characters"])
                        
                        embed.add_field(
                            name="✅ Fresh File Load",
                            value=f"**Users in file**: {fresh_users}\n**Characters in file**: {fresh_chars}\n**Matches memory**: {fresh_users == total_users}",
                            inline=False
                        )
                except Exception as e:
                    embed.add_field(
                        name="❌ File Load Error",
                        value=f"```{type(e).__name__}: {str(e)[:200]}```",
                        inline=False
                    )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Debug error: {type(e).__name__}: {str(e)}")
        finally:
            self._executing_commands.discard(command_key)
    
    @commands.command(name='reload_chars')
    async def reload_characters(self, ctx):
        """
        Reload character data from file (Admin only)
        
        Usage:
        !reload_chars
        """
        # Check if user is admin
        if str(ctx.author.id) != str(config.AUTHORIZED_USER_ID):
            await ctx.send("❌ This command is admin-only")
            return
        
        try:
            # Store current data as backup
            old_count = len(character_manager.data)
            
            # Reload data
            character_manager._load_data()
            
            new_count = len(character_manager.data)
            total_chars = 0
            for user_data in character_manager.data.values():
                if isinstance(user_data, dict) and "characters" in user_data:
                    total_chars += len(user_data["characters"])
            
            embed = discord.Embed(
                title="♻️ Character Data Reloaded",
                color=0x2ecc71
            )
            embed.add_field(
                name="📊 Results",
                value=f"**Old user count**: {old_count}\n**New user count**: {new_count}\n**Total characters**: {total_chars}",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Reload error: {type(e).__name__}: {str(e)}")
    
    @commands.command(name='char_errors')
    async def show_character_errors(self, ctx):
        """
        Show any character loading errors from startup (Admin only)
        
        Usage:
        !char_errors
        """
        # Check if user is admin
        if str(ctx.author.id) != str(config.AUTHORIZED_USER_ID):
            await ctx.send("❌ This command is admin-only")
            return
        
        try:
            errors = character_manager.get_startup_errors()
            
            if not errors:
                await ctx.send("✅ No character loading errors since startup")
                return
            
            embed = discord.Embed(
                title="⚠️ Character Loading Errors",
                description=f"Found {len(errors)} error(s) since startup:",
                color=0xe74c3c
            )
            
            error_text = "\n".join(errors)
            if len(error_text) > 4000:  # Discord field limit
                error_text = error_text[:4000] + "... (truncated)"
            
            embed.add_field(
                name="🔍 Error Details",
                value=error_text,
                inline=False
            )
            
            embed.set_footer(text="These errors have been cleared after showing")
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f"❌ Error checking character errors: {type(e).__name__}: {str(e)}")
    
    @commands.command(name='force_save_chars')
    async def force_save_characters(self, ctx):
        """
        Force save character data to file (Admin only)
        
        Usage:
        !force_save_chars
        """
        # Check if user is admin
        if str(ctx.author.id) != str(config.AUTHORIZED_USER_ID):
            await ctx.send("❌ This command is admin-only")
            return
        
        try:
            # Get current stats
            total_users = len(character_manager.data)
            total_chars = 0
            for user_data in character_manager.data.values():
                if isinstance(user_data, dict) and "characters" in user_data:
                    total_chars += len(user_data["characters"])
            
            # Try to force save
            try:
                character_manager._save_data()
                await ctx.send(f"✅ **Force save successful!**\n"
                              f"Saved {total_users} users with {total_chars} total characters\n"
                              f"File: `{character_manager.data_file}`")
            except Exception as save_error:
                await ctx.send(f"❌ **Force save failed!**\n"
                              f"Error: {type(save_error).__name__}: {str(save_error)}\n"
                              f"Data in memory: {total_users} users, {total_chars} characters")
                
        except Exception as e:
            await ctx.send(f"❌ Force save error: {type(e).__name__}: {str(e)}")
    
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