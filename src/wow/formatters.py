"""
RaiderIO Data Formatters
Handles formatting of RaiderIO data into Discord embeds and messages
"""

import discord
from typing import Dict, List, Any, Optional
from ..utils.logging import get_logger

logger = get_logger(__name__)


class RaiderIOFormatters:
    """Handles formatting of RaiderIO data for Discord"""
    
    @staticmethod
    def get_class_color(char_class: str) -> int:
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
    
    @staticmethod
    def format_time_duration(time_ms: int) -> str:
        """Format time in milliseconds to readable duration"""
        if time_ms <= 0:
            return "Unknown"
        
        minutes = time_ms // 60000
        seconds = (time_ms % 60000) // 1000
        return f"{minutes}:{seconds:02d}"
    
    @staticmethod
    def get_completion_status(run_data: Dict[str, Any]) -> str:
        """Get run completion status emoji"""
        # Check if run was completed (even if depleted) vs abandoned
        if run_data.get("score", 0) > 0 or run_data.get("clear_time_ms", 0) > 0:
            return "✅" if run_data.get("num_chests", 0) >= 1 else "⏱️"  # Timed vs Depleted
        return "❌"  # Abandoned/Failed
    
    @staticmethod
    def safe_field_value(value: str, max_length: int = 1024) -> str:
        """Ensure field value doesn't exceed Discord limits"""
        if len(value) > max_length:
            return value[:max_length-3] + "..."
        return value
    
    @staticmethod
    def safe_title(title: str, max_length: int = 256) -> str:
        """Ensure title doesn't exceed Discord limits"""
        if len(title) > max_length:
            return title[:max_length-3] + "..."
        return title
    
    @staticmethod
    def create_character_embed(data: Dict[str, Any]) -> discord.Embed:
        """Create embed for character profile"""
        if "error" in data:
            return discord.Embed(
                title="❌ Error",
                description=data["error"],
                color=0xe74c3c
            )
        
        name = data.get("name", "Unknown")
        realm = data.get("realm", "Unknown")
        region = data.get("region", "Unknown").upper()
        
        embed = discord.Embed(
            title=f"🏆 {name} - {realm} ({region})",
            color=RaiderIOFormatters.get_class_color(data.get("class", "Unknown"))
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
        RaiderIOFormatters._add_raid_progression(embed, data)
        
        # Profile URL
        profile_url = data.get("profile_url", "")
        if profile_url:
            embed.url = profile_url
        
        return embed
    
    @staticmethod
    def _add_raid_progression(embed: discord.Embed, data: Dict[str, Any]):
        """Add raid progression to character embed"""
        raid_prog = data.get("raid_progression", {})
        if not raid_prog:
            return
        
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
    
    @staticmethod
    def create_affixes_embed(data: Dict[str, Any], region: str) -> discord.Embed:
        """Create embed for current affixes"""
        embed = discord.Embed(
            title=f"⚡ Weekly Mythic+ Affixes ({region.upper()})",
            color=0xe74c3c
        )
        
        if "error" in data:
            embed.description = data["error"]
            return embed
        
        affixes = data.get("affix_details", [])
        if affixes:
            for affix in affixes:
                name = affix.get("name", "Unknown")
                description = affix.get("description", "No description available")
                
                embed.add_field(
                    name=f"🔥 {name}",
                    value=RaiderIOFormatters.safe_field_value(description[:200] + ("..." if len(description) > 200 else "")),
                    inline=False
                )
        else:
            embed.description = "No affix information available"
        
        return embed
    
    @staticmethod
    def create_cutoffs_embed(data: Dict[str, Any], region: str, season: str) -> discord.Embed:
        """Create embed for season cutoffs"""
        embed = discord.Embed(
            title=f"📊 Mythic+ Season Cutoffs ({region.upper()})",
            description=f"Rating thresholds for {season} season",
            color=0xf39c12
        )
        
        if "error" in data:
            embed.description = data["error"]
            return embed
        
        # Check if we have cutoff data
        cutoffs = data.get("cutoffs", {})
        if not cutoffs:
            embed.description = "No cutoff data available for this region/season"
            return embed
        
        # Common percentiles to display
        percentile_labels = {
            "p999": "Top 0.1% (99.9th)",
            "p99": "Top 1% (99th)", 
            "p95": "Top 5% (95th)",
            "p90": "Top 10% (90th)",
            "p75": "Top 25% (75th)",
            "p50": "Top 50% (50th)"
        }
        
        # Display overall cutoffs if available
        if "all" in cutoffs:
            all_cutoffs = cutoffs["all"]
            cutoff_text = ""
            
            for percentile, label in percentile_labels.items():
                if percentile in all_cutoffs:
                    rating = all_cutoffs[percentile]
                    cutoff_text += f"**{label}**: {rating:,}\n"
            
            if cutoff_text:
                embed.add_field(
                    name="🏆 Overall Ratings",
                    value=cutoff_text.strip(),
                    inline=True
                )
        
        # Display role-specific cutoffs
        RaiderIOFormatters._add_role_cutoffs(embed, cutoffs, percentile_labels)
        
        # Add footer info
        season_info = data.get("season", {})
        if season_info:
            season_name = season_info.get("name", season)
            embed.set_footer(text=f"Season: {season_name} | Region: {region.upper()}")
        else:
            embed.set_footer(text=f"Region: {region.upper()} | Season: {season}")
        
        return embed
    
    @staticmethod
    def _add_role_cutoffs(embed: discord.Embed, cutoffs: Dict[str, Any], percentile_labels: Dict[str, str]):
        """Add role-specific cutoffs to embed"""
        role_icons = {"dps": "⚔️", "healer": "💚", "tank": "🛡️"}
        role_names = {"dps": "DPS", "healer": "Healer", "tank": "Tank"}
        
        for role, icon in role_icons.items():
            if role in cutoffs:
                role_cutoffs = cutoffs[role]
                role_text = ""
                
                # Show top percentiles for each role
                for percentile in ["p99", "p95", "p90", "p75", "p50"]:
                    if percentile in role_cutoffs:
                        rating = role_cutoffs[percentile]
                        percentage = percentile.replace("p", "").replace("999", "99.9")
                        role_text += f"**{percentage}th**: {rating:,}\n"
                
                if role_text:
                    embed.add_field(
                        name=f"{icon} {role_names[role]}",
                        value=role_text.strip(),
                        inline=True
                    )