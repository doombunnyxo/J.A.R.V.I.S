"""
WoW Character Management System
Stores and manages user's WoW characters and main character selection
"""

import json
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
from ..utils.logging import get_logger

logger = get_logger(__name__)


class CharacterManager:
    """Manages stored WoW characters for Discord users"""
    
    def __init__(self, data_file: str = "data/wow_characters.json"):
        self.data_file = Path(data_file)
        self.data = {}
        self.lock = asyncio.Lock()
        self._load_data()
    
    def _load_data(self):
        """Load character data from file"""
        try:
            if self.data_file.exists():
                with open(self.data_file, 'r') as f:
                    self.data = json.load(f)
            else:
                # Create data directory if it doesn't exist
                self.data_file.parent.mkdir(parents=True, exist_ok=True)
                self.data = {}
                self._save_data()
        except Exception as e:
            logger.error(f"Failed to load character data: {e}")
            self.data = {}
    
    def _save_data(self):
        """Save character data to file"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save character data: {e}")
    
    async def add_character(
        self, 
        user_id: str, 
        character_name: str, 
        realm: str, 
        region: str = "us"
    ) -> Dict[str, Any]:
        """
        Add a character for a user
        
        Args:
            user_id: Discord user ID
            character_name: Character name
            realm: Realm/server name
            region: Region (us, eu, kr, tw, cn)
            
        Returns:
            Status dictionary with success and message
        """
        async with self.lock:
            user_id = str(user_id)
            
            # Initialize user data if not exists
            if user_id not in self.data:
                self.data[user_id] = {
                    "characters": [],
                    "main_character": None
                }
            
            # Check if character already exists
            for char in self.data[user_id]["characters"]:
                if (char["name"].lower() == character_name.lower() and 
                    char["realm"].lower() == realm.lower() and
                    char["region"].lower() == region.lower()):
                    return {
                        "success": False,
                        "message": f"Character **{character_name}** on **{realm}** ({region.upper()}) already exists"
                    }
            
            # Add character
            character_data = {
                "name": character_name,
                "realm": realm,
                "region": region.lower()
            }
            
            self.data[user_id]["characters"].append(character_data)
            
            # If this is the first character, set it as main
            if len(self.data[user_id]["characters"]) == 1:
                self.data[user_id]["main_character"] = 0
            
            self._save_data()
            
            char_count = len(self.data[user_id]["characters"])
            return {
                "success": True,
                "message": f"✅ Added **{character_name}** on **{realm}** ({region.upper()}) - Character #{char_count}",
                "character_index": char_count - 1
            }
    
    async def set_main_character(self, user_id: str, character_index: int) -> Dict[str, Any]:
        """
        Set a user's main character by index
        
        Args:
            user_id: Discord user ID
            character_index: Index of character in list (0-based)
            
        Returns:
            Status dictionary
        """
        async with self.lock:
            user_id = str(user_id)
            
            if user_id not in self.data:
                return {
                    "success": False,
                    "message": "You have no characters stored. Use `!add_char` first"
                }
            
            if character_index < 0 or character_index >= len(self.data[user_id]["characters"]):
                return {
                    "success": False,
                    "message": f"Invalid character number. You have {len(self.data[user_id]['characters'])} characters"
                }
            
            self.data[user_id]["main_character"] = character_index
            self._save_data()
            
            char = self.data[user_id]["characters"][character_index]
            return {
                "success": True,
                "message": f"✅ Set **{char['name']}** on **{char['realm']}** ({char['region'].upper()}) as your main character",
                "character": char
            }
    
    async def get_character(self, user_id: str, character_index: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get a specific character or the main character
        
        Args:
            user_id: Discord user ID
            character_index: Optional character index, defaults to main
            
        Returns:
            Character data or None
        """
        user_id = str(user_id)
        
        if user_id not in self.data:
            return None
        
        user_data = self.data[user_id]
        
        if not user_data["characters"]:
            return None
        
        # If no index specified, use main character
        if character_index is None:
            character_index = user_data.get("main_character", 0)
        
        # Validate index
        if character_index < 0 or character_index >= len(user_data["characters"]):
            return None
        
        return user_data["characters"][character_index]
    
    async def get_all_characters(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all characters for a user
        
        Args:
            user_id: Discord user ID
            
        Returns:
            List of character data
        """
        user_id = str(user_id)
        
        if user_id not in self.data:
            return []
        
        return self.data[user_id].get("characters", [])
    
    async def get_main_character_index(self, user_id: str) -> Optional[int]:
        """Get the index of the user's main character"""
        user_id = str(user_id)
        
        if user_id not in self.data:
            return None
        
        return self.data[user_id].get("main_character")
    
    async def remove_character(self, user_id: str, character_index: int) -> Dict[str, Any]:
        """
        Remove a character by index
        
        Args:
            user_id: Discord user ID
            character_index: Index of character to remove
            
        Returns:
            Status dictionary
        """
        async with self.lock:
            user_id = str(user_id)
            
            if user_id not in self.data:
                return {
                    "success": False,
                    "message": "You have no characters stored"
                }
            
            if character_index < 0 or character_index >= len(self.data[user_id]["characters"]):
                return {
                    "success": False,
                    "message": f"Invalid character number"
                }
            
            # Remove character
            removed_char = self.data[user_id]["characters"].pop(character_index)
            
            # Adjust main character index if needed
            main_idx = self.data[user_id].get("main_character", 0)
            if main_idx == character_index:
                # Removed the main, set first character as new main
                self.data[user_id]["main_character"] = 0 if self.data[user_id]["characters"] else None
            elif main_idx > character_index:
                # Adjust index down
                self.data[user_id]["main_character"] = main_idx - 1
            
            self._save_data()
            
            return {
                "success": True,
                "message": f"✅ Removed **{removed_char['name']}** on **{removed_char['realm']}** ({removed_char['region'].upper()})"
            }
    
    async def clear_all_characters(self, user_id: str) -> Dict[str, Any]:
        """Clear all characters for a user"""
        async with self.lock:
            user_id = str(user_id)
            
            if user_id not in self.data:
                return {
                    "success": False,
                    "message": "You have no characters stored"
                }
            
            char_count = len(self.data[user_id].get("characters", []))
            del self.data[user_id]
            self._save_data()
            
            return {
                "success": True,
                "message": f"✅ Cleared all {char_count} character(s)"
            }


# Global character manager instance
character_manager = CharacterManager()