"""
WoW Character Management System
Stores and manages user's WoW characters and main character selection
"""

import json
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
import traceback
import shutil
from datetime import datetime
from ..utils.logging import get_logger

logger = get_logger(__name__)


class CharacterManager:
    """Manages stored WoW characters for Discord users"""
    
    def __init__(self, data_file: str = "data/wow_characters.json"):
        self.data_file = Path(data_file)
        self.data = {}
        self.lock = asyncio.Lock()
        self.startup_errors = []  # Store errors to report to Discord later
        self.discord_channel = None  # Will be set by the bot later
        self._last_known_good_data = {}  # Store last known good data
        logger.info(f"Initializing CharacterManager with file: {self.data_file}")
        self._load_data()
        logger.info(f"CharacterManager initialized with {len(self.data)} users")
    
    def _load_data(self):
        """Load character data from file with extensive debugging"""
        try:
            if self.data_file.exists():
                file_size = self.data_file.stat().st_size
                logger.info(f"Loading character file: {self.data_file} (size: {file_size} bytes)")
                
                # Check if file is suspiciously small
                if file_size <= 2:
                    error_msg = f"⚠️ Character file is suspiciously small ({file_size} bytes)!"
                    logger.warning(error_msg)
                    self.startup_errors.append(error_msg)
                    
                    # Look for backups
                    backup_files = list(self.data_file.parent.glob("wow_characters*.backup"))
                    if backup_files:
                        latest_backup = max(backup_files, key=lambda f: f.stat().st_mtime)
                        backup_size = latest_backup.stat().st_size
                        if backup_size > file_size:
                            self.startup_errors.append(f"📁 Found larger backup: {latest_backup.name} ({backup_size} bytes)")
                            logger.info(f"Loading from backup: {latest_backup}")
                            with open(latest_backup, 'r', encoding='utf-8') as f:
                                loaded_data = json.load(f)
                                if isinstance(loaded_data, dict) and loaded_data:
                                    self.data = loaded_data
                                    self.startup_errors.append(f"✅ Restored {len(self.data)} users from backup")
                                    # Save the restored data
                                    self._save_data()
                                    return
                
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                    logger.debug(f"Raw file content (first 200 chars): {file_content[:200]}")
                    
                    if not file_content or file_content.strip() in ['{}', '[]', '']:
                        error_msg = f"⚠️ Character file is empty or contains only empty structure!"
                        logger.warning(error_msg)
                        self.startup_errors.append(error_msg)
                        self.data = {}
                        return
                    
                    loaded_data = json.loads(file_content)
                    
                    # Validate the loaded data structure
                    if isinstance(loaded_data, dict):
                        self.data = loaded_data
                        total_chars = sum(len(u.get("characters", [])) for u in self.data.values() if isinstance(u, dict))
                        logger.info(f"Successfully loaded {len(self.data)} users with {total_chars} total characters")
                        if len(self.data) == 0:
                            self.startup_errors.append("⚠️ Loaded file but found 0 users")
                        else:
                            # Store as last known good data
                            self._last_known_good_data = self.data.copy()
                    else:
                        logger.error(f"Invalid data structure in {self.data_file}, expected dict but got {type(loaded_data)}")
                        self.startup_errors.append(f"❌ Invalid data structure: expected dict, got {type(loaded_data).__name__}")
                        self.data = {}
            else:
                # Create data directory if it doesn't exist
                self.data_file.parent.mkdir(parents=True, exist_ok=True)
                self.data = {}
                logger.info("No existing character data file, starting fresh")
                self.startup_errors.append("📝 No character file found, starting fresh")
                
        except json.JSONDecodeError as e:
            error_msg = f"JSON decode error at line {e.lineno}, column {e.colno}: {e.msg}"
            logger.error(f"Full JSON error: {error_msg}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            self.startup_errors.append(f"❌ **JSON Error**: {error_msg}")
            
            # Try to backup the corrupted file
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = self.data_file.parent / f"wow_characters_{timestamp}.backup"
                shutil.copy2(self.data_file, backup_file)
                logger.warning(f"Backed up corrupted file to {backup_file}")
                self.startup_errors.append(f"💾 Backed up corrupted file to {backup_file.name}")
            except Exception as backup_error:
                logger.error(f"Failed to backup: {backup_error}")
            
            self.data = {}
            
        except Exception as e:
            error_msg = f"Unexpected error: {type(e).__name__}: {str(e)}"
            logger.error(f"Full error: {error_msg}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            self.startup_errors.append(f"❌ **Unexpected Error**: {error_msg}")
            self.data = {}
    
    def _save_data(self):
        """Save character data to file with error handling and debugging"""
        try:
            # CRITICAL: Don't save empty data if we had data before
            if not self.data and self.data_file.exists():
                file_size = self.data_file.stat().st_size
                error_msg = f"CRITICAL: Attempted to save empty data! Current file size: {file_size} bytes"
                logger.error(error_msg)
                logger.error(f"Stack trace of save attempt: {traceback.format_stack()}")
                self.startup_errors.append(f"🛡️ **Data Protection**: Blocked saving empty data (file: {file_size} bytes)")
                
                # Check if file has data
                try:
                    with open(self.data_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                        if existing_data:
                            protection_msg = f"File has {len(existing_data)} users, blocking empty save!"
                            logger.error(protection_msg)
                            self.startup_errors.append(f"🛡️ **Protected**: {len(existing_data)} user(s) preserved")
                            return  # Abort save
                except Exception as check_error:
                    logger.error(f"Error checking existing file: {check_error}")
                    # Still abort save to be safe
                    return
            
            # Ensure directory exists
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            
            # EXTRA PROTECTION: Never save if we're about to destroy data
            if len(self.data) == 0 and len(self._last_known_good_data) > 0:
                error_msg = f"CRITICAL: Refusing to save! Memory has 0 users but last known good had {len(self._last_known_good_data)} users"
                logger.error(error_msg)
                self.startup_errors.append(f"🚫 **Save Blocked**: Protected {len(self._last_known_good_data)} users from deletion")
                # Restore from last known good
                self.data = self._last_known_good_data.copy()
                logger.info("Restored data from last known good state")
                return
            
            # Create backup before saving if file exists and has data
            if self.data_file.exists() and self.data_file.stat().st_size > 100:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = self.data_file.parent / f"wow_characters_{timestamp}.backup"
                try:
                    shutil.copy2(self.data_file, backup_file)
                    logger.debug(f"Created pre-save backup: {backup_file}")
                    # Clean up old backups (keep only last 5)
                    backups = sorted(self.data_file.parent.glob("wow_characters_*.backup"))
                    if len(backups) > 5:
                        for old_backup in backups[:-5]:
                            old_backup.unlink()
                            logger.debug(f"Deleted old backup: {old_backup}")
                except Exception as backup_error:
                    logger.warning(f"Failed to create backup: {backup_error}")
            
            # Log what we're about to save
            total_chars = sum(len(u.get("characters", [])) for u in self.data.values() if isinstance(u, dict))
            logger.info(f"Saving: {len(self.data)} users, {total_chars} chars to {self.data_file}")
            logger.debug(f"First 500 chars of data to save: {str(self.data)[:500]}")
            
            # Write to temporary file first to avoid corruption
            temp_file = self.data_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            
            # Verify temp file was written correctly
            temp_size = temp_file.stat().st_size
            logger.debug(f"Temp file written: {temp_file}, size: {temp_size} bytes")
            
            # Atomic move to final location
            temp_file.replace(self.data_file)
            logger.info(f"Character data saved successfully: {len(self.data)} users, {total_chars} characters")
            
            # Update last known good data after successful save
            if len(self.data) > 0:
                self._last_known_good_data = self.data.copy()
            
        except Exception as e:
            logger.error(f"Failed to save character data to {self.data_file}: {e}")
            # Try to clean up temp file if it exists
            try:
                temp_file = self.data_file.with_suffix('.tmp')
                if temp_file.exists():
                    temp_file.unlink()
            except:
                pass
            raise  # Re-raise to let caller know save failed
    
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
    
    def get_startup_errors(self) -> List[str]:
        """Get startup errors and clear them"""
        errors = self.startup_errors.copy()
        self.startup_errors.clear()
        return errors
    
    async def report_error_to_discord(self, error_msg: str):
        """Send error message to Discord channel if available"""
        if self.discord_channel:
            try:
                await self.discord_channel.send(f"🔴 **Character Manager Error**\n{error_msg}")
            except Exception as e:
                logger.error(f"Failed to send Discord error: {e}")
    
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