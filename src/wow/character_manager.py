"""
WoW Character Management System
Stores and manages user's WoW characters and main character selection
"""

import json
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
import os
from ..utils.logging import get_logger

logger = get_logger(__name__)


class CharacterManager:
    """Manages stored WoW characters for Discord users"""
    
    def __init__(self, data_file: str = "data/wow_characters.json"):
        self.data_file = Path(data_file)
        self.data = {}
        self.lock = asyncio.Lock()
        logger.info(f"Initializing CharacterManager with file: {self.data_file}")
        self._load_data()
        logger.info(f"CharacterManager initialized with {len(self.data)} users")
    
    def _load_data(self):
        """Load character data from file"""
        try:
            if self.data_file.exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    
                if isinstance(loaded_data, dict):
                    self.data = loaded_data
                    total_chars = sum(len(u.get("characters", [])) for u in self.data.values() if isinstance(u, dict))
                    logger.info(f"Loaded {len(self.data)} users with {total_chars} total characters")
                else:
                    logger.error(f"Invalid data structure in {self.data_file}, expected dict")
                    self.data = {}
            else:
                self.data_file.parent.mkdir(parents=True, exist_ok=True)
                self.data = {}
                logger.info("No existing character data file, starting fresh")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            self.data = {}
            
        except Exception as e:
            logger.error(f"Error loading character data: {e}")
            self.data = {}
    
    def _save_data(self):
        """Save character data to file"""
        return self._save_data_to_file(self.data)
    
    def _save_data_to_file(self, data_to_save: Dict[str, Any]) -> bool:
        """Save character data to file"""
        try:
            if not isinstance(data_to_save, dict):
                logger.error(f"Invalid data type for save: {type(data_to_save)}")
                return False
            
            # Ensure directory exists
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to temp file first, then atomic move
            temp_file = self.data_file.with_suffix(f'.tmp_{os.getpid()}')
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data_to_save, f, indent=2, ensure_ascii=False)
                
                # Atomic commit
                temp_file.replace(self.data_file)
                logger.debug(f"Saved character data: {len(data_to_save)} users")
                return True
                
            except Exception as write_error:
                # Clean up temp file on error
                try:
                    if temp_file.exists():
                        temp_file.unlink()
                except:
                    pass
                raise write_error
            
        except Exception as e:
            logger.error(f"Error saving character data: {e}")
            return False
    
    
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
            
            try:
                self._save_data()
            except Exception as e:
                # Rollback the in-memory change if save fails
                self.data[user_id]["characters"].pop()
                if len(self.data[user_id]["characters"]) == 0:
                    self.data[user_id]["main_character"] = None
                return {
                    "success": False,
                    "message": f"❌ Failed to save character data: {str(e)}"
                }
            
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
            
            # Store original main character for rollback
            original_main = self.data[user_id]["main_character"]
            self.data[user_id]["main_character"] = character_index
            
            try:
                self._save_data()
            except Exception as e:
                # Rollback the in-memory change if save fails
                self.data[user_id]["main_character"] = original_main
                return {
                    "success": False,
                    "message": f"❌ Failed to save main character selection: {str(e)}"
                }
            
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
            
            # Store original state for rollback
            original_characters = self.data[user_id]["characters"].copy()
            original_main = self.data[user_id].get("main_character")
            
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
            
            try:
                self._save_data()
            except Exception as e:
                # Rollback the in-memory changes if save fails
                self.data[user_id]["characters"] = original_characters
                self.data[user_id]["main_character"] = original_main
                return {
                    "success": False,
                    "message": f"❌ Failed to save after removing character: {str(e)}"
                }
            
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
            # Store original data for rollback
            original_data = self.data[user_id].copy()
            
            del self.data[user_id]
            
            try:
                self._save_data()
            except Exception as e:
                # Rollback the in-memory change if save fails
                self.data[user_id] = original_data
                return {
                    "success": False,
                    "message": f"❌ Failed to save after clearing characters: {str(e)}"
                }
            
            return {
                "success": True,
                "message": f"✅ Cleared all {char_count} character(s)"
            }


# Global character manager instance
character_manager = CharacterManager()