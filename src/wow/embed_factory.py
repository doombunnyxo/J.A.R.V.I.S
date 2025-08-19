"""
Embed Factory for RaiderIO Run Details
Handles creation of complex run detail embeds
"""

import discord
from typing import Dict, List, Any, Optional
from ..utils.logging import get_logger
from .formatters import RaiderIOFormatters

logger = get_logger(__name__)


class RunEmbedFactory:
    """Factory for creating run detail embeds"""
    
    @staticmethod
    def create_runs_embed(
        data: Dict[str, Any], 
        user_id: int, 
        character_info: Dict[str, str],
        sequential_ids: List[int],
        best_runs_data: Optional[Dict[str, Any]] = None,
        best_sequential_ids: Optional[List[int]] = None
    ) -> discord.Embed:
        """Create embed for Mythic+ runs with sequential IDs"""
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
        if recent_runs and sequential_ids:
            recent_text = RunEmbedFactory._format_runs_list(recent_runs, sequential_ids)
            embed.add_field(
                name="📅 Recent Runs (Use `!rio_details <number>` for details)",
                value=recent_text or "No recent runs",
                inline=False
            )
        
        # Best runs this season
        if best_runs_data and best_sequential_ids:
            best_runs = best_runs_data.get("mythic_plus_best_runs", [])[:5]
            if best_runs:
                best_text = RunEmbedFactory._format_runs_list(best_runs, best_sequential_ids, is_best=True)
                embed.add_field(
                    name="🌟 Season Best Runs (Use `!rio_details <number>` for details)",
                    value=best_text or "No best runs",
                    inline=False
                )
        
        # Add footer with ID range
        if sequential_ids:
            min_id = min(sequential_ids)
            max_id = max(sequential_ids)
            if min_id == max_id:
                embed.set_footer(text=f"💡 Use !rio_details #{min_id} to view detailed run information")
            else:
                embed.set_footer(text=f"💡 Use !rio_details <#{min_id}-#{max_id}> to view detailed run information")
        
        return embed
    
    @staticmethod
    def _format_runs_list(runs: List[Dict], sequential_ids: List[int], is_best: bool = False) -> str:
        """Format a list of runs with their sequential IDs"""
        formatted_runs = []
        
        for run, seq_id in zip(runs, sequential_ids):
            dungeon = run.get("dungeon", "Unknown")
            level = run.get("mythic_level", 0)
            score = run.get("score", 0)
            
            # Get completion status
            status = RaiderIOFormatters.get_completion_status(run)
            
            # Format time if available
            time_str = ""
            clear_time_ms = run.get("clear_time_ms", 0)
            if clear_time_ms > 0:
                time_str = f" ({RaiderIOFormatters.format_time_duration(clear_time_ms)})"
            
            # Format date if available and not best runs
            date_str = ""
            if not is_best:
                completed_at = run.get("completed_at", "")
                if completed_at:
                    date_str = f" - {completed_at.split('T')[0] if 'T' in completed_at else completed_at}"
            
            if is_best:
                formatted_runs.append(f"**#{seq_id}** ⭐ **+{level} {dungeon}**{time_str} - {score:.0f}")
            else:
                formatted_runs.append(f"**#{seq_id}** {status} **+{level} {dungeon}**{time_str}\n{score:.0f} score{date_str}\n")
        
        return "\n".join(formatted_runs)
    
    @staticmethod
    def create_run_details_embed(data: Dict[str, Any]) -> discord.Embed:
        """Create embed for detailed run information"""
        if "error" in data:
            return discord.Embed(
                title="❌ Error",
                description=data["error"],
                color=0xe74c3c
            )
        
        # Basic run info
        dungeon_data = data.get("dungeon", "Unknown")
        dungeon = dungeon_data.get("name", "Unknown") if isinstance(dungeon_data, dict) else dungeon_data
        level = data.get("mythic_level", 0)
        score = data.get("score", 0)
        
        # Create embed with safe title
        title = RaiderIOFormatters.safe_title(f"🏃 +{level} {dungeon}")
        embed = discord.Embed(
            title=title,
            color=0xe67e22 if data.get("num_chests", 0) >= 1 else 0xe74c3c
        )
        
        # Set thumbnail if available
        RunEmbedFactory._set_dungeon_thumbnail(embed, data, dungeon_data)
        
        # Basic run information
        RunEmbedFactory._add_run_status(embed, data, score)
        
        # Timing information
        RunEmbedFactory._add_timing_info(embed, data)
        
        # Date completed
        RunEmbedFactory._add_completion_date(embed, data)
        
        # Team composition
        RunEmbedFactory._add_team_composition(embed, data)
        
        # Affixes
        RunEmbedFactory._add_affixes(embed, data)
        
        return embed
    
    @staticmethod
    def _set_dungeon_thumbnail(embed: discord.Embed, data: Dict[str, Any], dungeon_data: Any):
        """Set dungeon icon as thumbnail"""
        icon_url = data.get("icon_url")
        if not icon_url and isinstance(dungeon_data, dict):
            icon_url = dungeon_data.get("icon_url")
        
        if icon_url and icon_url.startswith("/images/"):
            icon_url = f"https://cdn.raiderio.net{icon_url}"
        
        if icon_url:
            embed.set_thumbnail(url=icon_url)
    
    @staticmethod
    def _add_run_status(embed: discord.Embed, data: Dict[str, Any], score: float):
        """Add run status field"""
        completed = "✅ Completed" if data.get("num_chests", 0) >= 1 else "❌ Depleted"
        score_text = f"{score:.1f}" if score else "0.0"
        
        embed.add_field(
            name="📋 Run Status",
            value=f"{completed}\n**Score**: {score_text}",
            inline=True
        )
    
    @staticmethod
    def _add_timing_info(embed: discord.Embed, data: Dict[str, Any]):
        """Add timing information"""
        clear_time_ms = data.get("clear_time_ms", 0)
        if clear_time_ms <= 0:
            return
        
        time_str = RaiderIOFormatters.format_time_duration(clear_time_ms)
        par_time_ms = data.get("par_time_ms", 0)
        
        if par_time_ms > 0:
            par_str = RaiderIOFormatters.format_time_duration(par_time_ms)
            time_diff_ms = par_time_ms - clear_time_ms
            
            if time_diff_ms > 0:
                diff_time = RaiderIOFormatters.format_time_duration(time_diff_ms)
                time_comparison = f"+{diff_time} remaining"
            else:
                diff_time = RaiderIOFormatters.format_time_duration(abs(time_diff_ms))
                time_comparison = f"-{diff_time} overtime"
            
            timing_value = f"**Clear Time**: {time_str}\n**Par Time**: {par_str}\n{time_comparison}"
        else:
            timing_value = time_str
        
        embed.add_field(
            name="⏱️ Timing",
            value=RaiderIOFormatters.safe_field_value(timing_value),
            inline=True
        )
    
    @staticmethod
    def _add_completion_date(embed: discord.Embed, data: Dict[str, Any]):
        """Add completion date"""
        completed_at = data.get("completed_at", "")
        if completed_at:
            date_str = completed_at.split('T')[0] if 'T' in completed_at else completed_at
            embed.add_field(
                name="📅 Completed",
                value=RaiderIOFormatters.safe_field_value(date_str) or "Unknown",
                inline=True
            )
    
    @staticmethod
    def _add_team_composition(embed: discord.Embed, data: Dict[str, Any]):
        """Add team composition"""
        roster = data.get("roster", [])
        if not roster:
            return
        
        team_text = ""
        for player in roster:
            character = player.get("character", {})
            name = character.get("name", "Unknown")
            spec = character.get("spec", {}).get("name", "Unknown")
            char_class = character.get("class", {}).get("name", "Unknown")
            team_text += f"**{name}** - {spec} {char_class}\n"
        
        embed.add_field(
            name="👥 Team Composition",
            value=RaiderIOFormatters.safe_field_value(team_text.strip()) or "No team data",
            inline=False
        )
    
    @staticmethod
    def _add_affixes(embed: discord.Embed, data: Dict[str, Any]):
        """Add affixes information"""
        affixes = data.get("affixes", data.get("weekly_modifiers", []))
        if not affixes:
            return
        
        affix_text = ""
        for affix in affixes:
            name = affix.get("name", "Unknown")
            affix_text += f"• {name}\n"
        
        embed.add_field(
            name="⚡ Affixes",
            value=RaiderIOFormatters.safe_field_value(affix_text.strip()) or "No affix data",
            inline=False
        )
    
    @staticmethod
    def create_basic_run_embed(data: Dict[str, Any], sequential_id: int) -> discord.Embed:
        """Create a basic embed from cached run data when RaiderIO ID is missing"""
        dungeon = data.get("dungeon", "Unknown")
        level = data.get("mythic_level", 0)
        score = data.get("score", 0)
        
        title = RaiderIOFormatters.safe_title(f"🏃 +{level} {dungeon}")
        embed = discord.Embed(
            title=title,
            description=f"⚠️ Run #{sequential_id} - Limited information available (RaiderIO ID missing)",
            color=0xf39c12
        )
        
        # Basic information
        score_text = f"{score:.1f}" if score else "0.0"
        info_value = f"**Dungeon**: {dungeon}\n**Level**: +{level}\n**Score**: {score_text}"
        
        embed.add_field(
            name="📋 Basic Information",
            value=RaiderIOFormatters.safe_field_value(info_value),
            inline=True
        )
        
        # Timing if available
        clear_time_ms = data.get("clear_time_ms", 0)
        if clear_time_ms > 0:
            embed.add_field(
                name="⏱️ Clear Time",
                value=RaiderIOFormatters.format_time_duration(clear_time_ms),
                inline=True
            )
        
        # Date if available
        completed_at = data.get("completed_at", "")
        if completed_at:
            date_str = completed_at.split('T')[0] if 'T' in completed_at else completed_at
            embed.add_field(
                name="📅 Completed",
                value=date_str,
                inline=True
            )
        
        # Affixes if available
        affixes = data.get("affixes", [])
        if affixes:
            affix_names = [affix.get("name", "Unknown") for affix in affixes]
            affix_text = ", ".join(affix_names)
            
            embed.add_field(
                name="⚡ Affixes",
                value=RaiderIOFormatters.safe_field_value(affix_text) or "No affix data",
                inline=False
            )
        
        embed.set_footer(text="This run's full details cannot be fetched from RaiderIO")
        return embed