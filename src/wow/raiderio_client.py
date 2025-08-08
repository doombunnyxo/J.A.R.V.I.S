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
                elif response.status == 400:
                    logger.warning(f"RaiderIO API bad request: {response.status}")
                    return {"error": "Invalid parameters"}
                elif response.status == 404:
                    logger.warning(f"RaiderIO API not found: {response.status}")
                    return {"error": "Character not found"}
                else:
                    logger.error(f"RaiderIO API error: {response.status}")
                    return {"error": f"API error: {response.status}"}
                    
        except Exception as e:
            logger.error(f"RaiderIO API request failed: {e}")
            return {"error": f"Request failed: {str(e)}"}
    
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
        season: str = "current",
        access_key: str = None
    ) -> Dict[str, Any]:
        """
        Get Mythic+ season cutoffs for different percentiles
        
        Args:
            region: Region code (us, eu, kr, tw, cn)
            season: Season identifier (current, previous, or season-X)
            access_key: Optional API key for higher rate limits
            
        Returns:
            Season cutoffs data with percentile breakdowns
        """
        params = {
            "region": region.lower(),
            "season": season
        }
        
        if access_key:
            params["access_key"] = access_key
        
        logger.debug(f"Making season-cutoffs request with params: {params}")
        return await self._make_request("mythic-plus/season-cutoffs", params)
    
    def format_character_summary(self, data: Dict[str, Any]) -> str:
        """Format character data into a readable summary"""
        if "error" in data:
            return f"❌ **Error**: {data['error']}"
        
        try:
            name = data.get("name", "Unknown")
            realm = data.get("realm", "Unknown")
            region = data.get("region", "Unknown").upper()
            race = data.get("race", "Unknown")
            character_class = data.get("class", "Unknown")
            spec = data.get("active_spec_name", "Unknown")
            level = data.get("level", "Unknown")
            
            # Mythic+ scores
            mp_scores = data.get("mythic_plus_scores_by_season", [])
            current_score = "N/A"
            if mp_scores:
                current_season = mp_scores[0]
                current_score = current_season.get("scores", {}).get("all", 0)
            
            # Recent runs
            recent_runs = data.get("mythic_plus_recent_runs", [])
            recent_run_summary = "No recent runs"
            if recent_runs:
                highest_recent = max(recent_runs, key=lambda x: x.get("mythic_level", 0))
                recent_run_summary = f"+{highest_recent.get('mythic_level', 0)} {highest_recent.get('dungeon', 'Unknown')}"
            
            # Raid progression
            raid_prog = data.get("raid_progression", {})
            raid_summary = "No raid progress"
            if raid_prog:
                current_raid = list(raid_prog.keys())[-1] if raid_prog else None
                if current_raid:
                    prog = raid_prog[current_raid]
                    normal_kills = prog.get("normal_bosses_killed", 0)
                    heroic_kills = prog.get("heroic_bosses_killed", 0)
                    mythic_kills = prog.get("mythic_bosses_killed", 0)
                    total = prog.get("total_bosses", 0)
                    
                    if mythic_kills > 0:
                        raid_summary = f"{current_raid}: {mythic_kills}/{total}M"
                    elif heroic_kills > 0:
                        raid_summary = f"{current_raid}: {heroic_kills}/{total}H"
                    elif normal_kills > 0:
                        raid_summary = f"{current_raid}: {normal_kills}/{total}N"
            
            summary = f"""**{name}** - {realm} ({region})
            
**Character**: {level} {race} {character_class} ({spec})
**Mythic+ Score**: {current_score}
**Recent High**: {recent_run_summary}
**Raid Progress**: {raid_summary}"""
            
            return summary
            
        except Exception as e:
            logger.error(f"Error formatting character summary: {e}")
            return f"❌ **Error**: Failed to format character data"
    
    def format_mythic_plus_runs(self, data: Dict[str, Any], limit: int = 5) -> str:
        """Format Mythic+ runs into a readable list"""
        if "error" in data:
            return f"❌ **Error**: {data['error']}"
        
        try:
            runs = data.get("runs", [])
            if not runs:
                return "No Mythic+ runs found"
            
            formatted_runs = []
            for run in runs[:limit]:
                dungeon = run.get("dungeon", "Unknown")
                level = run.get("mythic_level", 0)
                score = run.get("score", 0)
                completed = "✅" if run.get("num_chests", 0) >= 1 else "❌"
                time = run.get("clear_time_ms", 0) // 1000 // 60  # Convert to minutes
                
                formatted_runs.append(f"{completed} **+{level} {dungeon}** - {score:.1f} score ({time}m)")
            
            return "\n".join(formatted_runs)
            
        except Exception as e:
            logger.error(f"Error formatting mythic+ runs: {e}")
            return f"❌ **Error**: Failed to format runs data"


# Global client instance
raiderio_client = RaiderIOClient()