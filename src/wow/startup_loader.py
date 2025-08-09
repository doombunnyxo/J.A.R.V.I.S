"""
Startup loader for WoW data
Pre-fetches runs for all stored characters on bot startup
"""

import asyncio
from typing import Dict, List
from ..utils.logging import get_logger
from .character_manager import character_manager
from .run_manager import run_manager
from .raiderio_client import raiderio_client
from ..config import config

logger = get_logger(__name__)


class StartupLoader:
    """Handles pre-loading of WoW data on bot startup"""
    
    def __init__(self):
        self.loaded_characters = 0
        self.loaded_runs = 0
        self.failed_characters = []
    
    async def load_all_character_runs(self, enabled: bool = True, limit_per_char: int = 10) -> Dict:
        """
        Pre-fetch runs for all stored characters
        
        Args:
            enabled: Whether to actually fetch (can be disabled in config)
            limit_per_char: Max runs to fetch per character
            
        Returns:
            Stats about the loading process
        """
        if not enabled:
            logger.info("Startup run loading is disabled")
            return {"status": "disabled"}
        
        logger.info("Starting pre-fetch of character runs...")
        start_time = asyncio.get_event_loop().time()
        
        # Get all stored characters
        all_users_chars = character_manager.data
        total_characters = sum(len(chars) for chars in all_users_chars.values())
        
        if total_characters == 0:
            logger.info("No characters stored, skipping run pre-fetch")
            return {"status": "no_characters"}
        
        logger.info(f"Pre-fetching runs for {total_characters} character(s)...")
        
        # Process each user's characters
        for user_id, characters in all_users_chars.items():
            for char_data in characters:
                try:
                    name = char_data.get('name')
                    realm = char_data.get('realm')
                    region = char_data.get('region', 'us')
                    
                    if not name or not realm:
                        continue
                    
                    # Fetch character profile with runs
                    logger.debug(f"Fetching runs for {name}-{realm} ({region})")
                    
                    profile = await raiderio_client.get_character_profile(
                        region, realm, name,
                        fields=["mythic_plus_recent_runs", "mythic_plus_best_runs"],
                        access_key=config.RAIDERIO_API_KEY
                    )
                    
                    if "error" in profile:
                        logger.warning(f"Failed to fetch {name}-{realm}: {profile['error']}")
                        self.failed_characters.append(f"{name}-{realm}")
                        continue
                    
                    # Add runs to database
                    character_info = {
                        "name": name,
                        "realm": realm,
                        "region": region
                    }
                    
                    # Process recent runs
                    recent_runs = profile.get("mythic_plus_recent_runs", [])[:limit_per_char]
                    if recent_runs:
                        recent_ids = await run_manager.add_runs(recent_runs, character_info)
                        self.loaded_runs += len(recent_ids)
                        logger.debug(f"  Added {len(recent_ids)} recent runs for {name}")
                    
                    # Process best runs
                    best_runs = profile.get("mythic_plus_best_runs", [])[:5]
                    if best_runs:
                        best_ids = await run_manager.add_runs(best_runs, character_info)
                        self.loaded_runs += len(best_ids)
                        logger.debug(f"  Added {len(best_ids)} best runs for {name}")
                    
                    self.loaded_characters += 1
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error loading runs for {char_data}: {e}")
                    self.failed_characters.append(f"{char_data.get('name', 'Unknown')}-{char_data.get('realm', 'Unknown')}")
        
        # Calculate stats
        elapsed = asyncio.get_event_loop().time() - start_time
        stats = await run_manager.get_stats()
        
        result = {
            "status": "completed",
            "characters_processed": self.loaded_characters,
            "characters_failed": len(self.failed_characters),
            "runs_loaded": self.loaded_runs,
            "total_runs_in_db": stats['total_runs'],
            "time_elapsed": f"{elapsed:.1f}s"
        }
        
        # Log summary
        logger.info(f"Pre-fetch completed in {elapsed:.1f}s")
        logger.info(f"  Characters: {self.loaded_characters}/{total_characters} successful")
        logger.info(f"  Runs loaded: {self.loaded_runs}")
        logger.info(f"  Total runs in database: {stats['total_runs']}")
        
        if self.failed_characters:
            logger.warning(f"  Failed characters: {', '.join(self.failed_characters[:5])}")
        
        return result


# Global startup loader instance
startup_loader = StartupLoader()