"""
RaiderIO Discord commands
World of Warcraft Mythic+ and character lookup functionality
"""

import discord
from discord.ext import commands
from typing import Dict
from ..wow.raiderio_client import raiderio_client
from ..utils.logging import get_logger

logger = get_logger(__name__)


class RaiderIOCommands(commands.Cog):
    """RaiderIO integration commands for World of Warcraft data"""
    
    def __init__(self, bot):
        self.bot = bot
        self._executing_commands = set()
    
    @commands.command(name='rio')
    async def raiderio_lookup(self, ctx, *, args: str = None):
        """
        Look up World of Warcraft character information from RaiderIO
        
        Usage:
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
            if not args:
                await self._show_help(ctx)
                return
            
            # Parse arguments
            parts = args.strip().split()
            
            if len(parts) == 1 and parts[0].lower() == 'help':
                await self._show_help(ctx)
                return
            
            if len(parts) < 2:
                await ctx.send("❌ **Usage**: `!rio <character> <realm> [region]`\nExample: `!rio Thrall Mal'Ganis us`")
                return
            
            character = parts[0]
            realm = parts[1]
            region = parts[2].lower() if len(parts) > 2 else "us"
            
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
        !rio_runs <character> <realm> [region]
        Default region is US if not specified
        """
        command_key = f"rio_runs_{ctx.author.id}"
        if command_key in self._executing_commands:
            return
        
        self._executing_commands.add(command_key)
        
        try:
            if not args:
                await ctx.send("❌ **Usage**: `!rio_runs <character> <realm> [region]`")
                return
            
            parts = args.strip().split()
            if len(parts) < 2:
                await ctx.send("❌ **Usage**: `!rio_runs <character> <realm> [region]`")
                return
            
            character = parts[0]
            realm = parts[1]
            region = parts[2].lower() if len(parts) > 2 else "us"
            
            loading_msg = await ctx.send(f"🔍 Fetching Mythic+ runs for **{character}**...")
            
            # Get character profile with recent runs
            char_data = await raiderio_client.get_character_profile(
                region, realm, character, 
                fields=["mythic_plus_recent_runs", "mythic_plus_best_runs"]
            )
            
            if "error" in char_data:
                await loading_msg.edit(content=f"❌ **Error**: {char_data['error']}")
            else:
                embed = await self._create_runs_embed(char_data)
                await loading_msg.edit(content=None, embed=embed)
                
        except Exception as e:
            logger.error(f"RaiderIO runs command error: {e}")
            await ctx.send(f"❌ **Error**: Failed to fetch runs data")
        finally:
            self._executing_commands.discard(command_key)
    
    @commands.command(name='rio_affixes')
    async def raiderio_affixes(self, ctx, region: str = "us"):
        """
        Show current Mythic+ affixes
        
        Usage:
        !rio_affixes [region]
        """
        command_key = f"rio_affixes_{ctx.author.id}"
        if command_key in self._executing_commands:
            return
        
        self._executing_commands.add(command_key)
        
        try:
            loading_msg = await ctx.send("🔍 Fetching current Mythic+ affixes...")
            
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
    
    async def _show_help(self, ctx):
        """Show RaiderIO command help"""
        embed = discord.Embed(
            title="🏆 RaiderIO Commands",
            description="World of Warcraft character and Mythic+ lookup",
            color=0xf1c40f
        )
        
        embed.add_field(
            name="📊 Character Lookup",
            value=(
                "`!rio <character> <realm> [region]`\n"
                "Get character profile, M+ score, and raid progress\n"
                "Example: `!rio Thrall Mal'Ganis` (defaults to US)\n"
                "Example: `!rio Gandalf Stormrage eu`"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🏃 Recent Runs",
            value=(
                "`!rio_runs <character> <realm> [region]`\n"
                "Get recent and best Mythic+ runs\n"
                "Example: `!rio_runs Gandalf Stormrage` (defaults to US)"
            ),
            inline=False
        )
        
        embed.add_field(
            name="⚡ Weekly Affixes",
            value=(
                "`!rio_affixes [region]`\n"
                "Get current Mythic+ affixes\n"
                "Example: `!rio_affixes` (defaults to US)\n"
                "Example: `!rio_affixes eu`"
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
    
    async def _create_runs_embed(self, data: Dict) -> discord.Embed:
        """Create embed for Mythic+ runs"""
        name = data.get("name", "Unknown")
        realm = data.get("realm", "Unknown")
        region = data.get("region", "Unknown").upper()
        
        embed = discord.Embed(
            title=f"🏃 Mythic+ Runs - {name}",
            description=f"{realm} ({region})",
            color=0x9b59b6
        )
        
        # Recent runs
        recent_runs = data.get("mythic_plus_recent_runs", [])[:5]
        if recent_runs:
            recent_text = ""
            for run in recent_runs:
                dungeon = run.get("dungeon", "Unknown")
                level = run.get("mythic_level", 0)
                score = run.get("score", 0)
                completed = "✅" if run.get("num_chests", 0) >= 1 else "❌"
                
                recent_text += f"{completed} +{level} {dungeon} - {score:.0f}\n"
            
            embed.add_field(
                name="📅 Recent Runs",
                value=recent_text.strip() or "No recent runs",
                inline=False
            )
        
        # Best runs
        best_runs = data.get("mythic_plus_best_runs", [])[:5]
        if best_runs:
            best_text = ""
            for run in best_runs:
                dungeon = run.get("dungeon", "Unknown")
                level = run.get("mythic_level", 0)
                score = run.get("score", 0)
                
                best_text += f"⭐ +{level} {dungeon} - {score:.0f}\n"
            
            embed.add_field(
                name="🌟 Best Runs",
                value=best_text.strip() or "No best runs",
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


async def setup(bot):
    await bot.add_cog(RaiderIOCommands(bot))