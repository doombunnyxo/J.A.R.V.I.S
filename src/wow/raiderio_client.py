"""
RaiderIO API Client
Provides access to World of Warcraft Mythic+ scores, runs, and character data
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from urllib.parse import quote
from ..utils.logging import get_logger

logger = get_logger(__name__)


class RaiderIOClient:
    """Client for interacting with the RaiderIO API"""
    
    BASE_URL = "https://raider.io/api/v1"
    
    def __init__(self):
        self.session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a request to the RaiderIO API"""
        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/{endpoint}"
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_msg = self._get_error_message(response.status)
                    logger.warning(f"RaiderIO API error {response.status}: {error_msg}")
                    return {"error": error_msg}
                    
        except Exception as e:
            logger.error(f"RaiderIO API request failed: {e}")
            return {"error": f"Request failed: {str(e)}"}
    
    def _get_error_message(self, status_code: int) -> str:
        """Get appropriate error message for HTTP status code"""
        error_messages = {
            400: "Invalid parameters",
            404: "Character not found",
            429: "Rate limit exceeded",
            500: "RaiderIO server error",
            503: "RaiderIO service unavailable"
        }
        return error_messages.get(status_code, f"API error: {status_code}")
    
    async def get_character_profile(
        self, 
        region: str, 
        realm: str, 
        name: str,
        fields: List[str] = None,
        access_key: str = None
    ) -> Dict[str, Any]:
        """
        Get character profile information
        
        Args:
            region: Region code (us, eu, kr, tw, cn)
            realm: Realm/server name (can be slug or title format)
            name: Character name (not case sensitive)
            fields: List of fields to include (see API docs for full list)
            access_key: Optional API key for higher rate limits
            
        Available fields:
            General: gear, talents, talents:categorized, guild, covenant
            Raiding: raid_progression, raid_progression:current-tier
            Mythic+: mythic_plus_scores_by_season:current, mythic_plus_ranks,
                    mythic_plus_recent_runs, mythic_plus_best_runs,
                    mythic_plus_alternate_runs, mythic_plus_highest_level_runs
            Other: raid_achievement_meta, raid_achievement_curve
            
        Returns:
            Character profile data
        """
        if fields is None:
            fields = [
                "gear",
                "guild", 
                "talents:categorized",
                "mythic_plus_scores_by_season:current",
                "mythic_plus_recent_runs", 
                "mythic_plus_best_runs",
                "mythic_plus_ranks",
                "raid_progression:current-tier"
            ]
        
        params = {
            "region": region.lower(),
            "realm": realm,
            "name": name,
            "fields": ",".join(fields)
        }
        
        if access_key:
            params["access_key"] = access_key
        
        return await self._make_request("characters/profile", params)
    
    async def get_mythic_plus_runs(
        self, 
        region: str, 
        realm: str, 
        name: str, 
        season: str = "current"
    ) -> Dict[str, Any]:
        """
        Get character's Mythic+ runs
        
        Args:
            region: Region code
            realm: Realm name
            name: Character name
            season: Season identifier (current, previous, or season-X)
            
        Returns:
            Mythic+ runs data
        """
        params = {
            "region": region.lower(),
            "realm": realm,
            "name": name,
            "season": season
        }
        
        return await self._make_request("characters/mythic-plus-runs", params)
    
    async def get_mythic_plus_run_details(
        self, 
        run_id: int, 
        season: str = "current",
        access_key: str = None
    ) -> Dict[str, Any]:
        """
        Get detailed information about a specific Mythic+ run
        
        Args:
            run_id: ID of the run to get details for
            season: Season identifier (current, previous, or season-X)
            access_key: Optional API key for higher rate limits
            
        Returns:
            Detailed run information including affixes, team composition, etc.
        """
        params = {
            "id": run_id,
            "season": season
        }
        
        logger.debug(f"Making run-details request with params: {params}")
        
        if access_key:
            params["access_key"] = access_key
        
        return await self._make_request("mythic-plus/run-details", params)
    
    async def get_guild_profile(
        self, 
        region: str, 
        realm: str, 
        name: str,
        fields: List[str] = None
    ) -> Dict[str, Any]:
        """
        Get guild profile information
        
        Args:
            region: Region code
            realm: Realm name
            name: Guild name
            fields: List of fields to include
            
        Returns:
            Guild profile data
        """
        if fields is None:
            fields = ["raid_progression", "raid_rankings"]
        
        params = {
            "region": region.lower(),
            "realm": realm,
            "name": name,
            "fields": ",".join(fields)
        }
        
        return await self._make_request("guilds/profile", params)
    
    async def get_mythic_plus_affixes(self, region: str = "us") -> Dict[str, Any]:
        """
        Get current Mythic+ affixes
        
        Args:
            region: Region code
            
        Returns:
            Current affixes data
        """
        params = {"region": region.lower()}
        return await self._make_request("mythic-plus/affixes", params)
    
    async def get_mythic_plus_season_cutoffs(
        self, 
        region: str,
        season: str = None,
        access_key: str = None
    ) -> Dict[str, Any]:
        """
        Get Mythic+ season cutoffs for different percentiles
        
        Args:
            region: Region code (us, eu, kr, tw, cn)
            season: Optional season identifier (if None, API uses current season)
            access_key: Optional API key for higher rate limits
            
        Returns:
            Season cutoffs data with percentile breakdowns
        """
        params = {
            "region": region.lower()
        }
        
        # Only add season parameter if specified
        if season:
            params["season"] = season
        
        if access_key:
            params["access_key"] = access_key
        
        logger.debug(f"Making season-cutoffs request with params: {params}")
        return await self._make_request("mythic-plus/season-cutoffs", params)
    
    def extract_run_id(self, run_data: Dict[str, Any]) -> Optional[int]:
        """Extract RaiderIO run ID from run data"""
        # Try direct ID field first
        if 'id' in run_data and run_data['id']:
            try:
                return int(run_data['id'])
            except (ValueError, TypeError):
                logger.warning(f"Failed to convert 'id' field to int: {run_data['id']}")
        
        # Try extracting from URL
        if 'url' in run_data and run_data['url']:
            try:
                url_parts = str(run_data['url']).split('/')
                if url_parts and url_parts[-1].isdigit():
                    return int(url_parts[-1])
            except (ValueError, TypeError):
                logger.warning(f"Failed to extract ID from URL: {run_data['url']}")
        
        # Try other potential fields
        for field in ['run_id', 'keystone_run_id', 'mythic_plus_run_id']:
            if field in run_data and run_data[field]:
                try:
                    return int(run_data[field])
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def format_time_duration(self, time_ms: int) -> str:
        """Format time in milliseconds to readable duration"""
        if time_ms <= 0:
            return "Unknown"
        
        minutes = time_ms // 60000
        seconds = (time_ms % 60000) // 1000
        return f"{minutes}:{seconds:02d}"
    
    def get_completion_status(self, run_data: Dict[str, Any]) -> str:
        """Get run completion status emoji"""
        # Check if run was completed (even if depleted) vs abandoned
        if run_data.get("score", 0) > 0 or run_data.get("clear_time_ms", 0) > 0:
            return "✅" if run_data.get("num_chests", 0) >= 1 else "⏱️"  # Timed vs Depleted
        return "❌"  # Abandoned/Failed


# Global client instance
raiderio_client = RaiderIOClient()