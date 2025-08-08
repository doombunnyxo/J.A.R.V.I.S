"""
RaiderIO Discord commands
World of Warcraft Mythic+ and character lookup functionality
"""

import discord
from discord.ext import commands
from typing import Dict, Optional
from ..wow.raiderio_client import raiderio_client
from ..wow.character_manager import character_manager
from ..utils.logging import get_logger

logger = get_logger(__name__)


class RaiderIOCommands(commands.Cog):
    """RaiderIO integration commands for World of Warcraft data"""
    
    def __init__(self, bot):
        self.bot = bot
        self._executing_commands = set()
        # Store recent run data for quick access: {user_id: {character_key: [run_data]}}
        self._cached_runs = {}
    
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
            character_data = await self._parse_character_args(ctx, args)
            if character_data is None:
                return  # Error message already sent
            
            if character_data.get('show_help'):
                await self._show_help(ctx)
                return
            
            character = character_data['name']
            realm = character_data['realm']
            region = character_data['region']
            
            # Validate region
            valid_regions = ["us", "eu", "kr", "tw", "cn"]
            if region.lower() not in valid_regions:
                await ctx.send(f"❌ **Invalid region**: `{region}`. Valid regions: {', '.join(valid_regions)}")
                return
            
            # Send loading message
            loading_msg = await ctx.send(f"🔍 Looking up **{character}** on **{realm}** ({region.upper()})...")
            
            # Fetch character data
            char_data = await raiderio_client.get_character_profile(region, realm, character)
            
            # Format and send response
            if "error" in char_data:
                await loading_msg.edit(content=f"❌ **Error**: {char_data['error']}")
            else:
                # Create embed with character information
                embed = await self._create_character_embed(char_data)
                await loading_msg.edit(content=None, embed=embed)
                
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
            character_data = await self._parse_character_args(ctx, args)
            if character_data is None:
                return  # Error message already sent
            
            if character_data.get('show_help'):
                await self._show_help(ctx)
                return
            
            character = character_data['name']
            realm = character_data['realm']
            region = character_data['region']
            
            loading_msg = await ctx.send(f"🔍 Fetching Mythic+ runs for **{character}**...")
            
            # Get character profile with recent runs
            char_data = await raiderio_client.get_character_profile(
                region, realm, character, 
                fields=["mythic_plus_recent_runs", "mythic_plus_best_runs"]
            )
            
            if "error" in char_data:
                await loading_msg.edit(content=f"❌ **Error**: {char_data['error']}")
            else:
                embed = await self._create_runs_embed(char_data, ctx.author.id)
                await loading_msg.edit(content=None, embed=embed)
                
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
            region = "us"  # Default
            
            if args:
                parts = args.strip().split()
                
                # Check if it's a number (character selection for region)
                if len(parts) == 1 and parts[0].isdigit():
                    char_index = int(parts[0]) - 1
                    character_data = await character_manager.get_character(ctx.author.id, char_index)
                    if character_data:
                        region = character_data['region']
                    else:
                        chars = await character_manager.get_all_characters(ctx.author.id)
                        await ctx.send(f"❌ Invalid character number. You have {len(chars)} character(s)")
                        return
                # Otherwise treat as region
                elif len(parts) == 1:
                    region = parts[0].lower()
                    # Validate region
                    valid_regions = ["us", "eu", "kr", "tw", "cn"]
                    if region not in valid_regions:
                        await ctx.send(f"❌ **Invalid region**: `{region}`. Valid regions: {', '.join(valid_regions)}")
                        return
            
            loading_msg = await ctx.send(f"🔍 Fetching current Mythic+ affixes for {region.upper()}...")
            
            affixes_data = await raiderio_client.get_mythic_plus_affixes(region)
            
            if "error" in affixes_data:
                await loading_msg.edit(content=f"❌ **Error**: {affixes_data['error']}")
            else:
                embed = await self._create_affixes_embed(affixes_data, region)
                await loading_msg.edit(content=None, embed=embed)
                
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
            
            # Check if it's a simple number (recent run selection)
            if len(parts) == 1 and parts[0].isdigit():
                run_number = int(parts[0])
                character_data = await character_manager.get_character(ctx.author.id)
                if not character_data:
                    await ctx.send("❌ You have no main character set. Use `!add_char` to add characters")
                    return
                
                # Get cached runs for this character
                user_id = str(ctx.author.id)
                char_key = f"{character_data['name']}-{character_data['realm']}-{character_data['region']}"
                
                if user_id not in self._cached_runs or char_key not in self._cached_runs[user_id]:
                    await ctx.send("❌ No cached runs found. Use `!rio_runs` first to load recent runs")
                    return
                
                cached_runs = self._cached_runs[user_id][char_key]
                if run_number < 1 or run_number > len(cached_runs):
                    await ctx.send(f"❌ Invalid run number. Available runs: 1-{len(cached_runs)}")
                    return
                
                # Get the specific run data
                selected_run = cached_runs[run_number - 1]
                run_id = self._extract_run_id(selected_run)
                
                if not run_id:
                    await ctx.send("❌ Unable to find run ID for this run. The run may not have detailed data available.")
                    return
                
                loading_msg = await ctx.send(f"🔍 Fetching details for run #{run_number}...")
                run_data = await raiderio_client.get_mythic_plus_run_details(run_id)
                
            # Check if it's character number + run number (e.g., "2 3" for char #2, run #3)
            elif len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                char_number = int(parts[0])
                run_number = int(parts[1])
                
                character_data = await character_manager.get_character(ctx.author.id, char_number - 1)
                if not character_data:
                    chars = await character_manager.get_all_characters(ctx.author.id)
                    await ctx.send(f"❌ Invalid character number. You have {len(chars)} character(s)")
                    return
                
                # Get cached runs for this character
                user_id = str(ctx.author.id)
                char_key = f"{character_data['name']}-{character_data['realm']}-{character_data['region']}"
                
                if user_id not in self._cached_runs or char_key not in self._cached_runs[user_id]:
                    await ctx.send(f"❌ No cached runs found for {character_data['name']}. Use `!rio_runs {char_number}` first")
                    return
                
                cached_runs = self._cached_runs[user_id][char_key]
                if run_number < 1 or run_number > len(cached_runs):
                    await ctx.send(f"❌ Invalid run number. Available runs for {character_data['name']}: 1-{len(cached_runs)}")
                    return
                
                selected_run = cached_runs[run_number - 1]
                run_id = self._extract_run_id(selected_run)
                
                if not run_id:
                    await ctx.send(f"❌ Unable to find run ID for {character_data['name']} run #{run_number}. The run may not have detailed data available.")
                    return
                
                loading_msg = await ctx.send(f"🔍 Fetching details for {character_data['name']} run #{run_number}...")
                run_data = await raiderio_client.get_mythic_plus_run_details(run_id)
                
            # Manual run ID lookup
            else:
                try:
                    run_id = int(parts[0])
                    season = parts[1] if len(parts) > 1 else "current"
                    loading_msg = await ctx.send(f"🔍 Fetching run details for ID: {run_id}...")
                    run_data = await raiderio_client.get_mythic_plus_run_details(run_id, season)
                except ValueError:
                    await ctx.send("❌ **Usage**: `!rio_details <run_number>` or `!rio_details <run_id>`")
                    return
            
            if "error" in run_data:
                await loading_msg.edit(content=f"❌ **Error**: {run_data['error']}")
            else:
                embed = await self._create_run_details_embed(run_data)
                await loading_msg.edit(content=None, embed=embed)
                
        except Exception as e:
            logger.error(f"RaiderIO run details command error: {e}")
            await ctx.send(f"❌ **Error**: Failed to fetch run details")
        finally:
            self._executing_commands.discard(command_key)
    
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
            name="🔍 Run Details",
            value=(
                "`!rio_details <number>` - View run details from recent runs\n"
                "`!rio_details 2 3` - View run #3 from character #2\n"
                "`!rio_details <run_id>` - Manual run ID lookup\n"
                "Use `!rio_runs` first to see numbered run lists"
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
    
    async def _create_character_embed(self, data: Dict) -> discord.Embed:
        """Create embed for character profile"""
        name = data.get("name", "Unknown")
        realm = data.get("realm", "Unknown")
        region = data.get("region", "Unknown").upper()
        
        embed = discord.Embed(
            title=f"🏆 {name} - {realm} ({region})",
            color=self._get_class_color(data.get("class", "Unknown"))
        )
        
        # Character info
        race = data.get("race", "Unknown")
        char_class = data.get("class", "Unknown")
        spec = data.get("active_spec_name", "Unknown")
        level = data.get("level", "Unknown")
        
        embed.add_field(
            name="👤 Character",
            value=f"{level} {race} {char_class}\n**Spec**: {spec}",
            inline=True
        )
        
        # Mythic+ scores
        mp_scores = data.get("mythic_plus_scores_by_season", [])
        if mp_scores:
            current_season = mp_scores[0]
            all_score = current_season.get("scores", {}).get("all", 0)
            dps_score = current_season.get("scores", {}).get("dps", 0)
            healer_score = current_season.get("scores", {}).get("healer", 0)
            tank_score = current_season.get("scores", {}).get("tank", 0)
            
            embed.add_field(
                name="⚡ Mythic+ Score",
                value=(
                    f"**Overall**: {all_score}\n"
                    f"DPS: {dps_score} | Heal: {healer_score} | Tank: {tank_score}"
                ),
                inline=True
            )
        
        # Recent high run
        recent_runs = data.get("mythic_plus_recent_runs", [])
        if recent_runs:
            highest = max(recent_runs, key=lambda x: x.get("mythic_level", 0))
            embed.add_field(
                name="🏃 Recent High",
                value=f"+{highest.get('mythic_level', 0)} {highest.get('dungeon', 'Unknown')}",
                inline=True
            )
        
        # Raid progression
        raid_prog = data.get("raid_progression", {})
        if raid_prog:
            raid_text = ""
            for raid_name, prog in list(raid_prog.items())[-2:]:  # Show last 2 raids
                normal = prog.get("normal_bosses_killed", 0)
                heroic = prog.get("heroic_bosses_killed", 0)
                mythic = prog.get("mythic_bosses_killed", 0)
                total = prog.get("total_bosses", 0)
                
                if mythic > 0:
                    raid_text += f"**{raid_name}**: {mythic}/{total}M\n"
                elif heroic > 0:
                    raid_text += f"**{raid_name}**: {heroic}/{total}H\n"
                elif normal > 0:
                    raid_text += f"**{raid_name}**: {normal}/{total}N\n"
            
            if raid_text:
                embed.add_field(
                    name="🏰 Raid Progress",
                    value=raid_text.strip(),
                    inline=False
                )
        
        # Profile URL
        profile_url = data.get("profile_url", "")
        if profile_url:
            embed.set_footer(text="Click for full profile", icon_url="https://raider.io/images/warcraft/icons/class_icons/medium/warrior.jpg")
            embed.url = profile_url
        
        return embed
    
    async def _create_runs_embed(self, data: Dict, user_id: int) -> discord.Embed:
        """Create embed for Mythic+ runs"""
        name = data.get("name", "Unknown")
        realm = data.get("realm", "Unknown")
        region = data.get("region", "Unknown").upper()
        
        embed = discord.Embed(
            title=f"🏃 Mythic+ Runs - {name}",
            description=f"{realm} ({region})",
            color=0x9b59b6
        )
        
        # Cache runs for quick access and create numbered lists
        user_id_str = str(user_id)
        char_key = f"{name}-{realm}-{region.lower()}"
        
        if user_id_str not in self._cached_runs:
            self._cached_runs[user_id_str] = {}
        
        # Recent runs with enhanced details and numbering
        recent_runs = data.get("mythic_plus_recent_runs", [])[:10]  # Store more for selection
        if recent_runs:
            # Cache the runs for quick access
            self._cached_runs[user_id_str][char_key] = recent_runs
            
            # Debug: Log available fields in first run to understand structure
            if recent_runs and logger.level <= 10:  # DEBUG level
                first_run = recent_runs[0]
                available_fields = list(first_run.keys())
                logger.debug(f"Run data fields available: {available_fields}")
                if 'id' in first_run:
                    logger.debug(f"Direct run ID found: {first_run['id']}")
                elif 'url' in first_run:
                    logger.debug(f"Run URL found: {first_run['url']}")
            
            recent_text = ""
            for i, run in enumerate(recent_runs[:5], 1):  # Show top 5 with numbers
                dungeon = run.get("dungeon", "Unknown")
                level = run.get("mythic_level", 0)
                score = run.get("score", 0)
                completed = "✅" if run.get("num_chests", 0) >= 1 else "❌"
                
                # Try to get completion time if available
                clear_time_ms = run.get("clear_time_ms", 0)
                if clear_time_ms > 0:
                    minutes = clear_time_ms // 60000
                    seconds = (clear_time_ms % 60000) // 1000
                    time_str = f" ({minutes}:{seconds:02d})"
                else:
                    time_str = ""
                
                # Format date if available
                completed_at = run.get("completed_at", "")
                if completed_at:
                    # Extract just the date part
                    date_str = completed_at.split('T')[0] if 'T' in completed_at else completed_at
                    date_str = f" - {date_str}"
                else:
                    date_str = ""
                
                recent_text += f"**{i}.** {completed} **+{level} {dungeon}**{time_str}\n{score:.0f} score{date_str}\n\n"
            
            embed.add_field(
                name=f"📅 Recent Runs (Use `!rio_details <number>` for details)",
                value=recent_text.strip() or "No recent runs",
                inline=False
            )
        
        # Best runs this season (no numbers, these are achievements)
        best_runs = data.get("mythic_plus_best_runs", [])[:5]
        if best_runs:
            best_text = ""
            for run in best_runs:
                dungeon = run.get("dungeon", "Unknown")
                level = run.get("mythic_level", 0)
                score = run.get("score", 0)
                
                # Try to get completion time
                clear_time_ms = run.get("clear_time_ms", 0)
                if clear_time_ms > 0:
                    minutes = clear_time_ms // 60000
                    seconds = (clear_time_ms % 60000) // 1000
                    time_str = f" ({minutes}:{seconds:02d})"
                else:
                    time_str = ""
                
                best_text += f"⭐ **+{level} {dungeon}**{time_str} - {score:.0f}\n"
            
            embed.add_field(
                name="🌟 Season Best Runs",
                value=best_text.strip() or "No best runs",
                inline=False
            )
        
        # Add footer with instructions
        total_cached = len(self._cached_runs[user_id_str].get(char_key, []))
        embed.set_footer(text=f"💡 Use !rio_details <1-{total_cached}> to view detailed run information")
        
        return embed
    
    def _extract_run_id(self, run_data: Dict) -> Optional[int]:
        """
        Extract run ID from run data, trying multiple sources
        
        Args:
            run_data: Run data dict from RaiderIO API
            
        Returns:
            Run ID as integer, or None if not found
        """
        # Try direct ID field first
        if 'id' in run_data and run_data['id']:
            try:
                return int(run_data['id'])
            except (ValueError, TypeError):
                pass
        
        # Try extracting from URL
        if 'url' in run_data and run_data['url']:
            try:
                url_parts = str(run_data['url']).split('/')
                if url_parts and url_parts[-1].isdigit():
                    return int(url_parts[-1])
            except (ValueError, TypeError):
                pass
        
        # Try other potential fields
        for field in ['run_id', 'keystone_run_id', 'mythic_plus_run_id']:
            if field in run_data and run_data[field]:
                try:
                    return int(run_data[field])
                except (ValueError, TypeError):
                    pass
        
        return None
    
    async def _create_run_details_embed(self, data: Dict) -> discord.Embed:
        """Create embed for detailed run information"""
        embed = discord.Embed(
            title="🏃 Mythic+ Run Details",
            color=0xe67e22
        )
        
        # Basic run info
        dungeon = data.get("dungeon", "Unknown")
        level = data.get("mythic_level", 0)
        score = data.get("score", 0)
        completed = "✅ Completed" if data.get("num_chests", 0) >= 1 else "❌ Depleted"
        
        embed.add_field(
            name="📋 Run Info",
            value=f"**+{level} {dungeon}**\n{completed}\n{score:.1f} score",
            inline=True
        )
        
        # Timing information
        clear_time_ms = data.get("clear_time_ms", 0)
        if clear_time_ms > 0:
            minutes = clear_time_ms // 60000
            seconds = (clear_time_ms % 60000) // 1000
            time_str = f"{minutes}:{seconds:02d}"
            
            # Calculate time limit if available
            par_time_ms = data.get("par_time_ms", 0)
            if par_time_ms > 0:
                par_minutes = par_time_ms // 60000
                par_seconds = (par_time_ms % 60000) // 1000
                par_str = f"{par_minutes}:{par_seconds:02d}"
                
                # Time remaining/over
                time_diff_ms = par_time_ms - clear_time_ms
                if time_diff_ms > 0:
                    diff_minutes = time_diff_ms // 60000
                    diff_seconds = (time_diff_ms % 60000) // 1000
                    time_comparison = f"+{diff_minutes}:{diff_seconds:02d} remaining"
                else:
                    diff_minutes = abs(time_diff_ms) // 60000
                    diff_seconds = (abs(time_diff_ms) % 60000) // 1000
                    time_comparison = f"-{diff_minutes}:{diff_seconds:02d} overtime"
                
                embed.add_field(
                    name="⏱️ Timing",
                    value=f"**Clear Time**: {time_str}\n**Par Time**: {par_str}\n{time_comparison}",
                    inline=True
                )
            else:
                embed.add_field(
                    name="⏱️ Clear Time",
                    value=time_str,
                    inline=True
                )
        
        # Date completed
        completed_at = data.get("completed_at", "")
        if completed_at:
            date_str = completed_at.split('T')[0] if 'T' in completed_at else completed_at
            embed.add_field(
                name="📅 Completed",
                value=date_str,
                inline=True
            )
        
        # Team composition
        roster = data.get("roster", [])
        if roster:
            team_text = ""
            for player in roster:
                name = player.get("character", {}).get("name", "Unknown")
                spec = player.get("character", {}).get("spec", {}).get("name", "Unknown")
                char_class = player.get("character", {}).get("class", {}).get("name", "Unknown")
                
                team_text += f"**{name}** - {spec} {char_class}\n"
            
            embed.add_field(
                name="👥 Team Composition",
                value=team_text.strip(),
                inline=False
            )
        
        # Affixes
        affixes = data.get("affixes", [])
        if affixes:
            affix_text = ""
            for affix in affixes:
                name = affix.get("name", "Unknown")
                affix_text += f"• {name}\n"
            
            embed.add_field(
                name="⚡ Affixes",
                value=affix_text.strip(),
                inline=False
            )
        
        return embed
    
    async def _create_affixes_embed(self, data: Dict, region: str) -> discord.Embed:
        """Create embed for current affixes"""
        embed = discord.Embed(
            title=f"⚡ Weekly Mythic+ Affixes ({region.upper()})",
            color=0xe74c3c
        )
        
        affixes = data.get("affix_details", [])
        if affixes:
            for affix in affixes:
                name = affix.get("name", "Unknown")
                description = affix.get("description", "No description available")
                
                embed.add_field(
                    name=f"🔥 {name}",
                    value=description[:200] + ("..." if len(description) > 200 else ""),
                    inline=False
                )
        else:
            embed.description = "No affix information available"
        
        return embed
    
    def _get_class_color(self, char_class: str) -> int:
        """Get Discord embed color for WoW class"""
        colors = {
            "Death Knight": 0xC41F3B,
            "Demon Hunter": 0xA330C9,
            "Druid": 0xFF7D0A,
            "Evoker": 0x33937F,
            "Hunter": 0xABD473,
            "Mage": 0x69CCF0,
            "Monk": 0x00FF96,
            "Paladin": 0xF58CBA,
            "Priest": 0xFFFFFF,
            "Rogue": 0xFFF569,
            "Shaman": 0x0070DE,
            "Warlock": 0x9482C9,
            "Warrior": 0xC79C6E
        }
        return colors.get(char_class, 0x5865F2)
    
    async def _parse_character_args(self, ctx, args: Optional[str]) -> Optional[Dict]:
        """
        Parse character arguments, supporting stored characters
        
        Returns character data dict or None if error
        """
        # No args - use main character
        if not args:
            main_char = await character_manager.get_character(ctx.author.id)
            if not main_char:
                await ctx.send("❌ You have no characters stored. Use `!add_char` to add characters or provide character details")
                return None
            return main_char
        
        parts = args.strip().split()
        
        # Check for help
        if len(parts) == 1 and parts[0].lower() == 'help':
            return {'show_help': True}
        
        # Check if it's a number (character selection)
        if len(parts) == 1 and parts[0].isdigit():
            char_index = int(parts[0]) - 1  # Convert to 0-based
            selected_char = await character_manager.get_character(ctx.author.id, char_index)
            if not selected_char:
                chars = await character_manager.get_all_characters(ctx.author.id)
                await ctx.send(f"❌ Invalid character number. You have {len(chars)} character(s)")
                return None
            return selected_char
        
        # Manual character specification
        if len(parts) < 2:
            await ctx.send("❌ **Usage**: `!rio <character> <realm> [region]` or `!rio` for main character")
            return None
        
        character = parts[0]
        realm = parts[1]
        region = parts[2].lower() if len(parts) > 2 else "us"
        
        # Validate region
        valid_regions = ["us", "eu", "kr", "tw", "cn"]
        if region not in valid_regions:
            await ctx.send(f"❌ **Invalid region**: `{region}`. Valid regions: {', '.join(valid_regions)}")
            return None
        
        return {
            'name': character,
            'realm': realm,
            'region': region
        }


async def setup(bot):
    await bot.add_cog(RaiderIOCommands(bot))