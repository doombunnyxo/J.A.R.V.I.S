"""
Season Management System
Handles current season settings with persistent storage
"""

import json
import asyncio
from typing import Dict, Optional, Any
from pathlib import Path
from ..utils.logging import get_logger

logger = get_logger(__name__)


class SeasonManager:
    """Manages season settings for RaiderIO commands"""
    
    def __init__(self, data_file: str = "data/wow_seasons.json"):
        self.data_file = Path(data_file)
        self.lock = asyncio.Lock()
        # Structure: {"current_season": "season-tww-3", "seasons": {"season-tww-3": {"name": "...", "active": true}}}
        self.data = {"current_season": "season-tww-3", "seasons": {}}
        self._load_data()
    
    def _load_data(self):
        """Load season data from file"""
        try:
            if self.data_file.exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    self.data = {
                        "current_season": loaded_data.get("current_season", "season-tww-3"),
                        "seasons": loaded_data.get("seasons", {})
                    }
                    logger.debug(f"Loaded season data: current={self.data['current_season']}")
            else:
                # Create data directory if it doesn't exist
                self.data_file.parent.mkdir(parents=True, exist_ok=True)
                self.data = {"current_season": "season-tww-3", "seasons": {}}
        except Exception as e:
            logger.error(f"Failed to load season data: {e}")
            self.data = {"current_season": "season-tww-2", "seasons": {}}
    
    def _save_data(self):
        """Save season data to file with error handling"""
        try:
            # Ensure directory exists
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to temporary file first to avoid corruption
            temp_file = self.data_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            
            # Atomic move to final location
            temp_file.replace(self.data_file)
            logger.debug(f"Season data saved successfully to {self.data_file}")
            
        except Exception as e:
            logger.error(f"Failed to save season data to {self.data_file}: {e}")
            # Try to clean up temp file if it exists
            try:
                temp_file = self.data_file.with_suffix('.tmp')
                if temp_file.exists():
                    temp_file.unlink()
            except:
                pass
            raise
    
    async def set_current_season(self, season: str) -> Dict[str, Any]:
        """
        Set the current season for RaiderIO commands
        
        Args:
            season: Season identifier (e.g., "current", "season-tww-2", "season-tww-1")
            
        Returns:
            Status dictionary with success and message
        """
        async with self.lock:
            # Store original season for rollback
            original_season = self.data["current_season"]
            self.data["current_season"] = season
            
            try:
                self._save_data()
            except Exception as e:
                # Rollback on save failure
                self.data["current_season"] = original_season
                return {
                    "success": False,
                    "message": f"❌ Failed to save season setting: {str(e)}"
                }
            
            return {
                "success": True,
                "message": f"✅ Set current season to **{season}**"
            }
    
    async def get_current_season(self) -> str:
        """Get the current season setting"""
        return self.data["current_season"]
    
    async def add_known_season(self, season_id: str, season_data: Dict[str, Any]) -> None:
        """
        Add a known season to the database
        
        Args:
            season_id: Season identifier
            season_data: Season information (name, dates, etc.)
        """
        async with self.lock:
            self.data["seasons"][season_id] = season_data
            try:
                self._save_data()
            except Exception as e:
                # Remove from memory if save fails
                self.data["seasons"].pop(season_id, None)
                logger.error(f"Failed to save season {season_id}: {e}")
    
    async def get_known_seasons(self) -> Dict[str, Any]:
        """Get all known seasons"""
        return self.data["seasons"].copy()
    
    async def get_season_info(self, season_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific season"""
        return self.data["seasons"].get(season_id)
    
    async def reset_to_current(self) -> Dict[str, Any]:
        """Reset season setting back to 'current'"""
        return await self.set_current_season("current")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about season management"""
        return {
            "current_season": self.data["current_season"],
            "known_seasons": len(self.data["seasons"]),
            "seasons_list": list(self.data["seasons"].keys())
        }


# Global season manager instance
season_manager = SeasonManager()