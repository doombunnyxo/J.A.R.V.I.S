"""
RaiderIO Discord commands
World of Warcraft Mythic+ and character lookup functionality
"""

import discord
from discord.ext import commands
import asyncio
from typing import Dict, Optional, Any
from ..wow.command_handlers import CommandHandlers
from ..wow.character_manager import character_manager
from ..wow.run_manager import run_manager
from ..wow.season_manager import season_manager
from ..config import config
from ..utils.logging import get_logger

logger = get_logger(__name__)

logger.info("RaiderIO module loading...")

class RaiderIOCommands(commands.Cog):
    """RaiderIO integration commands for World of Warcraft data"""
    
    def __init__(self, bot):
        logger.info("Initializing RaiderIOCommands cog...")
        self.bot = bot
        self._executing_commands = set()
        logger.info("RaiderIOCommands cog initialized successfully")
    
    @commands.command(name='rio')
    async def raiderio_lookup(self, ctx, *, args: str = None):
        """
        Look up World of Warcraft character information from RaiderIO
        
        Usage:
        !rio                        # Uses your main character
        !rio 2                      # Uses your character #2
        !rio <character> <realm> [region]
        !rio Thrall Mal'Ganis      # defaults to US
        !rio Gandalf Stormrage eu   # specify EU region
        !rio help
        """
        # Prevent duplicate execution
        command_key = f"rio_{ctx.author.id}"
        if command_key in self._executing_commands:
            return
        
        self._executing_commands.add(command_key)
        
        try:
            # Handle stored characters
            character_data = await CommandHandlers.parse_character_args(ctx, args)
            if character_data is None:
                return  # Error message already sent
            
            if character_data.get('show_help'):
                await self._show_help(ctx)
                return
            
            character = character_data['name']
            realm = character_data['realm']
            region = character_data['region']
            
            # Validate region
            if not CommandHandlers.validate_region(region):
                await ctx.send(f"❌ **Invalid region**: `{region}`. Valid regions: us, eu, kr, tw, cn")
                return
            
            # Send loading message
            loading_msg = await ctx.send(f"🔍 Looking up **{character}** on **{realm}** ({region.upper()})...")
            
            # Handle character lookup
            success, result = await CommandHandlers.handle_character_lookup(region, realm, character)
            
            if success:
                await loading_msg.edit(content=None, embed=result)
            else:
                await loading_msg.edit(content=result)
                
        except Exception as e:
            logger.error(f"RaiderIO command error: {e}")
            await ctx.send(f"❌ **Error**: Failed to lookup character data")
        finally:
            self._executing_commands.discard(command_key)
    
    @commands.command(name='rio_runs')
    async def raiderio_runs(self, ctx, *, args: str = None):
        """
        Look up recent Mythic+ runs for a character
        
        Usage:
        !rio_runs                    # Uses your main character
        !rio_runs 2                  # Uses your character #2
        !rio_runs <character> <realm> [region]
        Default region is US if not specified
        """
        command_key = f"rio_runs_{ctx.author.id}"
        if command_key in self._executing_commands:
            return
        
        self._executing_commands.add(command_key)
        
        try:
            # Handle stored characters
            character_data = await CommandHandlers.parse_character_args(ctx, args)
            if character_data is None:
                return  # Error message already sent
            
            if character_data.get('show_help'):
                await self._show_help(ctx)
                return
            
            character = character_data['name']
            realm = character_data['realm']
            region = character_data['region']
            
            loading_msg = await ctx.send(f"🔍 Fetching Mythic+ runs for **{character}**...")
            
            # Handle runs lookup
            success, result = await CommandHandlers.handle_runs_lookup(character, realm, region, ctx)
            
            if success:
                await loading_msg.edit(content=None, embed=result)
            else:
                await loading_msg.edit(content=result)
                
        except Exception as e:
            logger.error(f"RaiderIO runs command error: {e}")
            await ctx.send(f"❌ **Error**: Failed to fetch runs data")
        finally:
            self._executing_commands.discard(command_key)
    
    @commands.command(name='rio_affixes')
    async def raiderio_affixes(self, ctx, *, args: str = None):
        """
        Show current Mythic+ affixes
        
        Usage:
        !rio_affixes                 # Uses US region (default)
        !rio_affixes eu              # Specify region
        !rio_affixes 2               # Uses your character #2's region
        """
        command_key = f"rio_affixes_{ctx.author.id}"
        if command_key in self._executing_commands:
            return
        
        self._executing_commands.add(command_key)
        
        try:
            # Determine region
            region = await self._parse_region_from_args(ctx, args)
            if region is None:
                return  # Error already sent
            
            loading_msg = await ctx.send(f"🔍 Fetching current Mythic+ affixes for {region.upper()}...")
            
            # Handle affixes lookup
            success, result = await CommandHandlers.handle_affixes_lookup(region)
            
            if success:
                await loading_msg.edit(content=None, embed=result)
            else:
                await loading_msg.edit(content=result)
                
        except Exception as e:
            logger.error(f"RaiderIO affixes command error: {e}")
            await ctx.send(f"❌ **Error**: Failed to fetch affixes data")
        finally:
            self._executing_commands.discard(command_key)
    
    @commands.command(name='rio_details')
    async def raiderio_details(self, ctx, *, args: str = None):
        """
        Get detailed information about a specific Mythic+ run
        
        Usage:
        !rio_details 1                   # Details for recent run #1 from your main character
        !rio_details 2 3                 # Details for recent run #3 from your character #2
        !rio_details <run_id> [season]   # Manual run ID lookup
        !rio_details 12345678
        """
        command_key = f"rio_details_{ctx.author.id}"
        if command_key in self._executing_commands:
            return
        
        self._executing_commands.add(command_key)
        
        try:
            if not args:
                await ctx.send("❌ **Usage**: `!rio_details <run_number>` or `!rio_details <run_id>`\nExample: `!rio_details 1` (first recent run from main character)")
                return
            
            parts = args.strip().split()
            
            # Check if it's a simple number (global sequential run ID)
            if len(parts) == 1 and parts[0].isdigit():
                sequential_id = int(parts[0])
                loading_msg = await ctx.send(f"🔍 Fetching details for run #{sequential_id}...")
                
                success, result = await CommandHandlers.handle_run_details_lookup(sequential_id)
                
                if success:
                    await loading_msg.edit(content=None, embed=result)
                else:
                    await loading_msg.edit(content=result)
                
            # Manual run ID lookup
            else:
                try:
                    run_id = int(parts[0])
                    season = parts[1] if len(parts) > 1 else None
                    
                    loading_msg = await ctx.send(f"🔍 Fetching run details for ID: {run_id}...")
                    
                    success, result = await CommandHandlers.handle_manual_run_details_lookup(run_id, season)
                    
                    if success:
                        await loading_msg.edit(content=None, embed=result)
                    else:
                        await loading_msg.edit(content=result)
                        
                except ValueError:
                    await ctx.send("❌ **Usage**: `!rio_details <run_number>` or `!rio_details <run_id>`")
                    return
                
        except Exception as e:
            logger.error(f"RaiderIO run details command error: {e}", exc_info=True)
            import traceback
            error_details = traceback.format_exc()
            
            # Send detailed error to Discord for debugging
            error_msg = f"❌ **Error**: Failed to fetch run details\n"
            error_msg += f"**Error Type**: {type(e).__name__}\n"
            error_msg += f"**Error Message**: {str(e)}\n"
            
            # If it's a specific error we can handle better
            if "loading_msg" not in locals():
                await ctx.send(error_msg)
            else:
                await loading_msg.edit(content=error_msg)
        finally:
            self._executing_commands.discard(command_key)
    
    @commands.command(name='rio_list')
    async def list_all_runs(self, ctx, limit: int = 20):
        """
        List all stored runs from all characters
        
        Usage:
        !rio_list           # Show last 20 runs
        !rio_list 50        # Show last 50 runs
        """
        command_key = f"rio_list_{ctx.author.id}"
        if command_key in self._executing_commands:
            return
        
        self._executing_commands.add(command_key)
        
        try:
            # Validate limit
            if limit < 1 or limit > 100:
                await ctx.send("❌ Limit must be between 1 and 100")
                return
            
            # Get recent runs from global database
            recent_runs = await run_manager.get_recent_runs(limit)
            
            if not recent_runs:
                await ctx.send("❌ No runs stored in database yet. Use `!rio_runs` to load runs first.")
                return
            
            # Create paginated embed
            embed = discord.Embed(
                title="🗂️ All Stored Runs",
                description=f"Showing last {len(recent_runs)} run(s)",
                color=0x3498db
            )
            
            runs_text = ""
            for run_entry in recent_runs:
                seq_id = run_entry["sequential_id"]
                run_data = run_entry["data"]
                character_info = run_entry.get("character", {})
                
                # Extract run information
                dungeon = run_data.get("dungeon", "Unknown")
                level = run_data.get("mythic_level", 0)
                # Check if run was completed (even if depleted) vs abandoned
                # Runs with score > 0 or clear_time_ms > 0 were completed
                if run_data.get("score", 0) > 0 or run_data.get("clear_time_ms", 0) > 0:
                    completed = "✅" if run_data.get("num_chests", 0) >= 1 else "⏱️"  # Timed vs Depleted
                else:
                    completed = "❌"  # Abandoned/Failed
                
                # Character information
                char_name = character_info.get("name", "Unknown")
                char_realm = character_info.get("realm", "Unknown")
                char_region = character_info.get("region", "us").upper()
                
                # Date information
                completed_at = run_data.get("completed_at", "")
                if completed_at:
                    date_str = completed_at.split('T')[0] if 'T' in completed_at else completed_at
                else:
                    date_str = "Unknown"
                
                runs_text += f"**#{seq_id}** {completed} +{level} {dungeon}\n"
                runs_text += f"   {char_name}-{char_realm} ({char_region}) - {date_str}\n\n"
            
            embed.description = f"Showing last {len(recent_runs)} run(s)\nUse `!rio_details <#number>` for details"
            embed.add_field(
                name="📋 Runs List",
                value=runs_text.strip() or "No runs available",
                inline=False
            )
            
            # Add stats
            stats = await run_manager.get_stats()
            embed.set_footer(text=f"Total runs in database: {stats['total_runs']}")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"List runs command error: {e}")
            await ctx.send("❌ **Error**: Failed to list runs")
        finally:
            self._executing_commands.discard(command_key)
    
    @commands.command(name='rio_cutoff')
    async def raiderio_cutoffs(self, ctx, *, args: str = None):
        """
        Show Mythic+ season cutoffs for different percentiles
        
        Usage:
        !rio_cutoff                  # US region (default)
        !rio_cutoff eu               # EU region cutoffs  
        !rio_cutoff 2                # Uses your character #2's region
        !rio_cutoff eu season-tww-3  # Specific region and season
        """
        command_key = f"rio_cutoff_{ctx.author.id}"
        if command_key in self._executing_commands:
            return
        
        self._executing_commands.add(command_key)
        
        try:
            # Parse region and season from arguments
            region, season = await self._parse_region_and_season_from_args(ctx, args)
            if region is None:
                return  # Error already sent
            
            loading_msg = await ctx.send(f"🔍 Fetching Mythic+ cutoffs for {region.upper()}...")
            
            # Handle cutoffs lookup
            success, result = await CommandHandlers.handle_cutoffs_lookup(region, season)
            
            if success:
                await loading_msg.edit(content=None, embed=result)
            else:
                await loading_msg.edit(content=result)
                
        except Exception as e:
            logger.error(f"RaiderIO cutoffs command error: {e}")
            await ctx.send(f"❌ **Error**: Failed to fetch cutoffs data")
        finally:
            self._executing_commands.discard(command_key)
    
    @commands.command(name='rio_prefetch')
    async def prefetch_all_runs(self, ctx):
        """
        Pre-fetch runs for all stored characters (Admin only)
        
        Usage:
        !rio_prefetch    # Load runs for all characters
        """
        # Check if user is admin
        if str(ctx.author.id) != str(config.AUTHORIZED_USER_ID):
            await ctx.send("❌ This command is admin-only")
            return
        
        command_key = f"rio_prefetch_{ctx.author.id}"
        if command_key in self._executing_commands:
            return
        
        self._executing_commands.add(command_key)
        
        try:
            from ..wow.startup_loader import startup_loader
            
            loading_msg = await ctx.send("🔄 Pre-fetching runs for all stored characters...")
            
            # Reset loader state
            startup_loader.loaded_characters = 0
            startup_loader.loaded_runs = 0
            startup_loader.failed_characters = []
            
            # Run the pre-fetch
            stats = await startup_loader.load_all_character_runs(enabled=True)
            
            if stats.get("status") == "no_characters":
                await loading_msg.edit(content="❌ No characters stored to pre-fetch")
            elif stats.get("status") == "completed":
                embed = discord.Embed(
                    title="✅ Pre-fetch Complete",
                    color=0x2ecc71
                )
                embed.add_field(
                    name="📊 Statistics",
                    value=(
                        f"**Characters processed**: {stats['characters_processed']}\n"
                        f"**Characters failed**: {stats['characters_failed']}\n"
                        f"**Runs loaded**: {stats['runs_loaded']}\n"
                        f"**Total runs in DB**: {stats['total_runs_in_db']}\n"
                        f"**Time elapsed**: {stats['time_elapsed']}"
                    ),
                    inline=False
                )
                
                if startup_loader.failed_characters:
                    failed_list = "\n".join(startup_loader.failed_characters[:10])
                    if len(startup_loader.failed_characters) > 10:
                        failed_list += f"\n... and {len(startup_loader.failed_characters) - 10} more"
                    embed.add_field(
                        name="❌ Failed Characters",
                        value=failed_list,
                        inline=False
                    )
                
                await loading_msg.edit(content=None, embed=embed)
            else:
                await loading_msg.edit(content="❌ Pre-fetch failed or was disabled")
                
        except Exception as e:
            logger.error(f"Pre-fetch command error: {e}")
            await ctx.send(f"❌ **Error**: Failed to pre-fetch runs")
        finally:
            self._executing_commands.discard(command_key)
    
    @commands.command(name='rio_season')
    async def raiderio_season(self, ctx, *, season: str = None):
        """
        Set or view the current season for RaiderIO commands
        
        Usage:
        !rio_season                     # View current season
        !rio_season current             # Set to current season
        !rio_season season-tww-3        # Set to current season
        !rio_season season-tww-2        # Set to previous season
        !rio_season reset               # Reset to 'current'
        """
        command_key = f"rio_season_{ctx.author.id}"
        if command_key in self._executing_commands:
            return
        
        self._executing_commands.add(command_key)
        
        try:
            # If no season provided, show current season
            if not season:
                current_season = await season_manager.get_current_season()
                stats = await season_manager.get_stats()
                
                embed = discord.Embed(
                    title="⚙️ RaiderIO Season Settings",
                    color=0x3498db
                )
                
                embed.add_field(
                    name="📅 Current Season",
                    value=f"**{current_season}**",
                    inline=True
                )
                
                if stats["known_seasons"] > 0:
                    seasons_list = ", ".join(stats["seasons_list"][-5:])  # Show last 5
                    embed.add_field(
                        name="🗄️ Known Seasons",
                        value=seasons_list,
                        inline=True
                    )
                
                embed.add_field(
                    name="💡 Usage",
                    value="`!rio_season season-tww-3` - Set season\n"
                          "`!rio_season current` - Use current season\n"
                          "`!rio_season reset` - Reset to current",
                    inline=False
                )
                
                embed.set_footer(text="Season setting affects !rio_details and !rio_cutoff commands")
                await ctx.send(embed=embed)
                return
            
            # Handle special cases
            season = season.strip()
            if season.lower() == "reset":
                result = await season_manager.reset_to_current()
            else:
                result = await season_manager.set_current_season(season)
            
            await ctx.send(result["message"])
            
        except Exception as e:
            logger.error(f"RaiderIO season command error: {e}")
            await ctx.send("❌ **Error**: Failed to manage season settings")
        finally:
            self._executing_commands.discard(command_key)
    
    @commands.command(name='rio_reset_runs')
    @commands.has_permissions(administrator=True)
    async def reset_runs_database(self, ctx):
        """
        Reset the rio_runs database (Admin only)
        Clears all stored runs for a new season
        """
        # Send confirmation message
        confirm_msg = await ctx.send("⚠️ **Warning:** This will permanently delete all stored runs in the database. React with ✅ to confirm or ❌ to cancel.")
        await confirm_msg.add_reaction("✅")
        await confirm_msg.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirm_msg.id
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == "✅":
                # Reset the database
                result = await run_manager.reset_database()
                
                if result["success"]:
                    embed = discord.Embed(
                        title="🔄 Database Reset Complete",
                        description=result["message"],
                        color=0x00ff00
                    )
                    embed.add_field(
                        name="Runs Cleared",
                        value=f"{result['runs_cleared']} runs",
                        inline=True
                    )
                    embed.add_field(
                        name="New Season",
                        value="Database ready for Season 3",
                        inline=True
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(result["message"])
            else:
                await ctx.send("❌ Database reset cancelled.")
                
        except asyncio.TimeoutError:
            await ctx.send("❌ Reset cancelled - no response received within 30 seconds.")
    
    async def _show_help(self, ctx):
        """Show RaiderIO command help"""
        embed = discord.Embed(
            title="🏆 RaiderIO Commands",
            description="World of Warcraft character and Mythic+ lookup",
            color=0xf1c40f
        )
        
        embed.add_field(
            name="🎮 Character Management",
            value=(
                "`!add_char <character> <realm> [region]` - Add character\n"
                "`!set_main [number]` - Set main character\n"
                "`!list_chars` - List your characters"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📊 Character Lookup",
            value=(
                "`!rio` - Uses your main character\n"
                "`!rio 2` - Uses your character #2\n"
                "`!rio <character> <realm> [region]` - Manual lookup\n"
                "Example: `!rio Thrall Mal'Ganis` (defaults to US)\n"
                "Example: `!rio Gandalf Stormrage eu`"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🏃 Recent Runs",
            value=(
                "`!rio_runs` - Uses your main character\n"
                "`!rio_runs 2` - Uses your character #2\n"
                "`!rio_runs <character> <realm> [region]` - Manual lookup\n"
                "Example: `!rio_runs Gandalf Stormrage` (defaults to US)"
            ),
            inline=False
        )
        
        embed.add_field(
            name="⚡ Weekly Affixes",
            value=(
                "`!rio_affixes` - US region (default)\n"
                "`!rio_affixes 2` - Uses your character #2's region\n"
                "`!rio_affixes eu` - Specify region directly"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📊 Season Cutoffs",
            value=(
                "`!rio_cutoff` - Rating thresholds (US region)\n"
                "`!rio_cutoff 2` - Uses your character #2's region\n"
                "`!rio_cutoff eu` - EU region cutoffs\n"
                "`!rio_cutoff us season-tww-3` - Specific season"
            ),
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Season Management",
            value=(
                "`!rio_season` - View current season setting\n"
                "`!rio_season season-tww-3` - Set specific season\n"
                "`!rio_season current` - Use current season\n"
                "`!rio_season reset` - Reset to current"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🔍 Run Details & Database",
            value=(
                "`!rio_details <#number>` - View detailed run information\n"
                "`!rio_list [limit]` - List all stored runs from all characters\n"
                "`!rio_details <run_id>` - Manual RaiderIO run ID lookup\n"
                "Global run numbering: #1, #2, #3... (persistent across restarts)"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🌍 Regions",
            value="Valid regions: `us` (default), `eu`, `kr`, `tw`, `cn`",
            inline=False
        )
        
        embed.set_footer(text="Data provided by RaiderIO API")
        
        await ctx.send(embed=embed)
    
    # All formatting methods moved to separate modules

async def setup(bot):
    logger.info("Setting up RaiderIO cog...")
    try:
        await bot.add_cog(RaiderIOCommands(bot))
        logger.info("RaiderIO cog setup completed successfully")
    except Exception as e:
        logger.error(f"Failed to setup RaiderIO cog: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise