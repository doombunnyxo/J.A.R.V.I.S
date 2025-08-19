"""
Command handlers for RaiderIO commands
Extracted logic from the main commands file for better organization
"""

from typing import Dict, Any, Optional, Tuple
import discord
from discord.ext import commands

from .raiderio_client import raiderio_client
from .character_manager import character_manager
from .run_manager import run_manager
from .season_manager import season_manager
from .formatters import RaiderIOFormatters
from .embed_factory import RunEmbedFactory
from ..config import config
from ..utils.logging import get_logger

logger = get_logger(__name__)


class CommandHandlers:
    """Handles the core logic for RaiderIO commands"""
    
    @staticmethod
    async def handle_character_lookup(
        character: str, 
        realm: str, 
        region: str
    ) -> Tuple[bool, Any]:
        """
        Handle character profile lookup
        
        Returns:
            Tuple of (success: bool, result: embed or error_message)
        """
        try:
            # Fetch character data
            char_data = await raiderio_client.get_character_profile(
                region, realm, character, 
                access_key=getattr(config, 'RAIDERIO_API_KEY', None)
            )
            
            if "error" in char_data:
                return False, f"❌ **Error**: {char_data['error']}"
            
            # Create and return embed
            embed = RaiderIOFormatters.create_character_embed(char_data)
            return True, embed
            
        except Exception as e:
            logger.error(f"Character lookup error: {e}")
            return False, "❌ **Error**: Failed to lookup character data"
    
    @staticmethod
    async def handle_runs_lookup(
        character: str, 
        realm: str, 
        region: str,
        ctx: commands.Context
    ) -> Tuple[bool, Any]:
        """
        Handle Mythic+ runs lookup
        
        Returns:
            Tuple of (success: bool, result: embed or error_message)
        """
        try:
            # Get character profile with runs
            char_data = await raiderio_client.get_character_profile(
                region, realm, character,
                fields=["mythic_plus_recent_runs", "mythic_plus_best_runs"],
                access_key=getattr(config, 'RAIDERIO_API_KEY', None)
            )
            
            if "error" in char_data:
                return False, f"❌ **Error**: {char_data['error']}"
            
            # Prepare character information
            character_info = {
                "name": character,
                "realm": realm,
                "region": region.lower()
            }
            
            # Add recent runs to database
            recent_runs = char_data.get("mythic_plus_recent_runs", [])[:10]
            recent_ids = []
            if recent_runs:
                recent_ids, errors = await run_manager.add_runs_with_errors(recent_runs, character_info)
                await CommandHandlers._report_run_errors(ctx, errors, "recent")
            
            # Add best runs to database
            best_runs = char_data.get("mythic_plus_best_runs", [])[:5]
            best_ids = []
            if best_runs:
                best_ids, best_errors = await run_manager.add_runs_with_errors(best_runs, character_info)
                await CommandHandlers._report_run_errors(ctx, best_errors, "best")
            
            # Create embed
            embed = RunEmbedFactory.create_runs_embed(
                char_data, 
                ctx.author.id, 
                character_info,
                recent_ids[:5],  # Show top 5 in embed
                char_data if best_runs else None,
                best_ids
            )
            
            return True, embed
            
        except Exception as e:
            logger.error(f"Runs lookup error: {e}")
            return False, "❌ **Error**: Failed to fetch runs data"
    
    @staticmethod
    async def _report_run_errors(ctx: commands.Context, errors: list, run_type: str):
        """Report run ID extraction errors to Discord"""
        if not errors:
            return
        
        error_msg = f"⚠️ **Warning**: Failed to extract RaiderIO IDs for {len(errors)} {run_type} run(s):\n"
        for error in errors[:3]:  # Show first 3 errors
            error_msg += f"• {error['dungeon']} +{error['level']}: {error['reason']}\n"
        
        if len(errors) > 3:
            error_msg += f"... and {len(errors) - 3} more\n"
        
        error_msg += "\nThese runs have been numbered but `!rio_details` may show limited information."
        await ctx.send(error_msg)
    
    @staticmethod
    async def handle_affixes_lookup(region: str) -> Tuple[bool, Any]:
        """
        Handle Mythic+ affixes lookup
        
        Returns:
            Tuple of (success: bool, result: embed or error_message)
        """
        try:
            affixes_data = await raiderio_client.get_mythic_plus_affixes(region)
            
            if "error" in affixes_data:
                return False, f"❌ **Error**: {affixes_data['error']}"
            
            embed = RaiderIOFormatters.create_affixes_embed(affixes_data, region)
            return True, embed
            
        except Exception as e:
            logger.error(f"Affixes lookup error: {e}")
            return False, "❌ **Error**: Failed to fetch affixes data"
    
    @staticmethod
    async def handle_cutoffs_lookup(region: str, season: Optional[str] = None) -> Tuple[bool, Any]:
        """
        Handle season cutoffs lookup
        
        Returns:
            Tuple of (success: bool, result: embed or error_message)
        """
        try:
            # Call API with or without season parameter
            if season:
                cutoffs_data = await raiderio_client.get_mythic_plus_season_cutoffs(
                    region, season, 
                    access_key=getattr(config, 'RAIDERIO_API_KEY', None)
                )
            else:
                cutoffs_data = await raiderio_client.get_mythic_plus_season_cutoffs(
                    region, 
                    access_key=getattr(config, 'RAIDERIO_API_KEY', None)
                )
            
            if "error" in cutoffs_data:
                return False, f"❌ **Error**: {cutoffs_data['error']}"
            
            embed = RaiderIOFormatters.create_cutoffs_embed(cutoffs_data, region, season or "current")
            return True, embed
            
        except Exception as e:
            logger.error(f"Cutoffs lookup error: {e}")
            return False, "❌ **Error**: Failed to fetch cutoffs data"
    
    @staticmethod
    async def handle_run_details_lookup(
        sequential_id: int
    ) -> Tuple[bool, Any]:
        """
        Handle detailed run lookup by sequential ID
        
        Returns:
            Tuple of (success: bool, result: embed or error_message)
        """
        try:
            # Get run data from global manager
            run_info = await run_manager.get_run_by_sequential_id(sequential_id)
            if not run_info:
                stats = await run_manager.get_stats()
                return False, f"❌ Run #{sequential_id} not found. Available runs: #1-#{stats['latest_run_id']}"
            
            # Check if we have the RaiderIO ID
            if not run_info.get('raiderio_id'):
                logger.warning(f"Run #{sequential_id} has no RaiderIO ID, showing cached data")
                
                # Create embed from cached data
                cached_data = run_info.get('data', {})
                embed = RunEmbedFactory.create_basic_run_embed(cached_data, sequential_id)
                return True, embed
            
            # Fetch detailed run data with season fallback
            current_season = await season_manager.get_current_season()
            run_data = await CommandHandlers._fetch_run_details_with_fallback(
                run_info['raiderio_id'], current_season
            )
            
            if "error" in run_data:
                return False, f"❌ **Error**: {run_data['error']}"
            
            embed = RunEmbedFactory.create_run_details_embed(run_data)
            return True, embed
            
        except Exception as e:
            logger.error(f"Run details lookup error: {e}")
            return False, "❌ **Error**: Failed to fetch run details"
    
    @staticmethod
    async def handle_manual_run_details_lookup(
        run_id: int, 
        season: Optional[str] = None
    ) -> Tuple[bool, Any]:
        """
        Handle manual run ID lookup
        
        Returns:
            Tuple of (success: bool, result: embed or error_message)
        """
        try:
            if not season:
                season = await season_manager.get_current_season()
            
            run_data = await CommandHandlers._fetch_run_details_with_fallback(run_id, season)
            
            if "error" in run_data:
                return False, f"❌ **Error**: {run_data['error']}"
            
            embed = RunEmbedFactory.create_run_details_embed(run_data)
            return True, embed
            
        except Exception as e:
            logger.error(f"Manual run details lookup error: {e}")
            return False, "❌ **Error**: Failed to fetch run details"
    
    @staticmethod
    async def _fetch_run_details_with_fallback(run_id: int, initial_season: str) -> Dict[str, Any]:
        """
        Fetch run details with season format fallback
        Tries different season formats if the initial one fails
        """
        # Season formats to try in order
        seasons_to_try = [
            initial_season,  # Try the requested season first
            "season-tww-3",  # Current season (Season 3)
            "season-tww-2",  # Previous season (Season 2)
            "season-tww-1"   # Older season (Season 1)
        ]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_seasons = []
        for season in seasons_to_try:
            if season not in seen:
                unique_seasons.append(season)
                seen.add(season)
        
        logger.debug(f"Trying run details for ID {run_id} with seasons: {unique_seasons}")
        
        for season in unique_seasons:
            try:
                run_data = await raiderio_client.get_mythic_plus_run_details(
                    run_id=run_id,
                    season=season,
                    access_key=getattr(config, 'RAIDERIO_API_KEY', None)
                )
                
                if "error" not in run_data:
                    logger.debug(f"Successfully fetched run details with season: {season}")
                    return run_data
                else:
                    logger.debug(f"Season {season} failed: {run_data.get('error', 'Unknown error')}")
                    
            except Exception as e:
                logger.debug(f"Exception with season {season}: {e}")
                continue
        
        # If all seasons failed, return the error from the original season
        logger.warning(f"All season formats failed for run ID {run_id}")
        return await raiderio_client.get_mythic_plus_run_details(
            run_id=run_id,
            season=initial_season,
            access_key=getattr(config, 'RAIDERIO_API_KEY', None)
        )
    
    @staticmethod
    async def parse_character_args(ctx: commands.Context, args: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Parse character arguments, supporting stored characters
        
        Returns character data dict or None if error (sends error message to ctx)
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
    
    @staticmethod
    def validate_region(region: str) -> bool:
        """Validate that the region is supported"""
        valid_regions = ["us", "eu", "kr", "tw", "cn"]
        return region.lower() in valid_regions