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
import os
from datetime import datetime
import threading
import time
from ..utils.logging import get_logger

logger = get_logger(__name__)


class FileMonitor:
    """Monitor file changes to track who's writing to the character file"""
    
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.monitoring = True
        self.last_size = None
        self.last_mtime = None
        
    def start_monitoring(self):
        """Start monitoring the file in a background thread"""
        def monitor():
            logger.critical(f"🔍 FILE MONITOR STARTED for {self.file_path}")
            while self.monitoring:
                try:
                    if self.file_path.exists():
                        stat = self.file_path.stat()
                        current_size = stat.st_size
                        current_mtime = stat.st_mtime
                        
                        if self.last_size is not None:
                            # Check for size changes
                            if current_size != self.last_size:
                                logger.critical(f"🚨 FILE SIZE CHANGE DETECTED!")
                                logger.critical(f"   File: {self.file_path}")
                                logger.critical(f"   Old size: {self.last_size} bytes")  
                                logger.critical(f"   New size: {current_size} bytes")
                                logger.critical(f"   Time: {datetime.fromtimestamp(current_mtime)}")
                                
                                # If file became 2 bytes, this is the reset we're looking for
                                if current_size == 2:
                                    logger.critical(f"🚨🚨🚨 FOUND THE RESET! File is now 2 bytes!")
                                    
                                    # Try to read the content
                                    try:
                                        with open(self.file_path, 'r') as f:
                                            content = f.read()
                                        logger.critical(f"🚨 FILE CONTENT: '{content}'")
                                    except Exception as e:
                                        logger.critical(f"🚨 Could not read file content: {e}")
                                    
                                    # Log ALL threads and their stacks
                                    import sys
                                    logger.critical(f"🚨 ALL THREAD STACK TRACES:")
                                    for thread_id, frame in sys._current_frames().items():
                                        logger.critical(f"🚨 THREAD {thread_id}:")
                                        stack = traceback.format_stack(frame)
                                        for line in stack[-10:]:  # Last 10 stack frames
                                            logger.critical(f"🚨   {line.strip()}")
                                        logger.critical(f"🚨 --- END THREAD {thread_id} ---")
                                    
                                    # Try to identify what process wrote to the file
                                    logger.critical(f"🚨 CHECKING FOR EXTERNAL PROCESSES:")
                                    try:
                                        import subprocess
                                        # Check lsof for file access
                                        result = subprocess.run(['lsof', str(self.file_path)], 
                                                              capture_output=True, text=True, timeout=5)
                                        if result.stdout:
                                            logger.critical(f"🚨 PROCESSES ACCESSING FILE: {result.stdout}")
                                        else:
                                            logger.critical(f"🚨 NO PROCESSES CURRENTLY ACCESSING FILE")
                                    except Exception as e:
                                        logger.critical(f"🚨 Could not check file access: {e}")
                        
                        self.last_size = current_size
                        self.last_mtime = current_mtime
                    else:
                        if self.last_size is not None:
                            logger.critical(f"🚨 FILE DELETED: {self.file_path}")
                        self.last_size = None
                        self.last_mtime = None
                
                except Exception as e:
                    logger.error(f"File monitor error: {e}")
                
                time.sleep(0.1)  # Check every 100ms
            
            logger.critical(f"🔍 FILE MONITOR STOPPED for {self.file_path}")
        
        # Start monitoring in background thread
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False


class CharacterManager:
    """Manages stored WoW characters for Discord users"""
    
    def __init__(self, data_file: str = "data/wow_characters.json"):
        self.data_file = Path(data_file)
        self.data = {}
        self.lock = asyncio.Lock()
        self.startup_errors = []  # Store errors to report to Discord later
        self.discord_channel = None  # Will be set by the bot later
        self._last_known_good_data = {}  # Store last known good data
        self._shutdown_in_progress = False  # Track shutdown state
        
        # Start file monitoring IMMEDIATELY to catch any resets
        self.file_monitor = FileMonitor(self.data_file)
        self.file_monitor.start_monitoring()
        
        # Register shutdown handler to catch shutdown-time saves
        import signal
        import atexit
        signal.signal(signal.SIGTERM, self._shutdown_handler)
        signal.signal(signal.SIGINT, self._shutdown_handler)
        atexit.register(self._atexit_handler)
        
        logger.info(f"Initializing CharacterManager with file: {self.data_file}")
        self._load_data()
        logger.info(f"CharacterManager initialized with {len(self.data)} users")
    
    def _shutdown_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.critical(f"🚨 SHUTDOWN SIGNAL RECEIVED: {signum}")
        logger.critical(f"🚨 CURRENT DATA STATE: {len(self.data)} users")
        logger.critical(f"🚨 DATA PREVIEW: {str(self.data)[:200]}")
        self._shutdown_in_progress = True
        
        # DEPLOYMENT PROTECTION: If this looks like a deployment restart,
        # create a deployment lock to prevent the new instance from starting too early
        try:
            deployment_lock = Path("data/deployment.lock")
            with open(deployment_lock, 'w') as f:
                f.write(f"shutdown_in_progress:{os.getpid()}:{datetime.now().isoformat()}\n")
            logger.critical(f"🔒 Created deployment lock: {deployment_lock}")
        except Exception as e:
            logger.error(f"Failed to create deployment lock: {e}")
        
        # Don't save during shutdown - prevents race conditions!
        
    def _atexit_handler(self):
        """Handle Python exit"""
        logger.critical(f"🚨 PYTHON ATEXIT CALLED")
        logger.critical(f"🚨 CURRENT DATA STATE: {len(self.data)} users") 
        logger.critical(f"🚨 DATA PREVIEW: {str(self.data)[:200]}")
        self._shutdown_in_progress = True
        # Don't save during exit - this might be the cause!
    
    def _load_data(self):
        """Load character data from file with extensive debugging"""
        # Check file status BEFORE we do anything
        if self.data_file.exists():
            file_stats = self.data_file.stat()
            logger.critical(f"🔍 BEFORE LOAD: {self.data_file} exists, size: {file_stats.st_size} bytes, modified: {datetime.fromtimestamp(file_stats.st_mtime)}")
        else:
            logger.critical(f"🔍 BEFORE LOAD: {self.data_file} does not exist")
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
                                    save_result = self._save_data()
                                    if not save_result:
                                        logger.critical("🚨 RESTORE SAVE FAILED!")
                                        self.startup_errors.append("🚨 **CRITICAL**: Restore save failed!")
                                        return  # CRITICAL: Don't continue processing if restore save fails
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
                            logger.critical(f"🚨 LOADED EMPTY DATA! File contained valid JSON but 0 users. Content was: {file_content[:200]}")
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
        """CENTRALIZED SAVE METHOD - All character data saves go through here"""
        # CRITICAL: Prevent saves during shutdown
        if self._shutdown_in_progress:
            logger.critical(f"🚨 BLOCKED SAVE DURING SHUTDOWN! Data: {len(self.data)} users")
            return False
            
        # Log who called this save
        stack = traceback.format_stack()
        caller_info = stack[-2].strip() if len(stack) >= 2 else "unknown"
        logger.critical(f"🔄 SAVE TRIGGERED BY: {caller_info}")
        logger.critical(f"🔄 FULL SAVE STACK: {[line.strip() for line in stack[-4:]]}")
        return self._atomic_save(self.data)
    
    def _atomic_save(self, data_to_save: Dict[str, Any]) -> bool:
        """Atomic save operation that never corrupts existing files on error"""
        try:
            # CRITICAL: Validate data before any file operations
            if not isinstance(data_to_save, dict):
                error_msg = f"CRITICAL: Invalid data type for save: {type(data_to_save)}"
                logger.critical(error_msg)
                self.startup_errors.append(f"❌ **Save Blocked**: Invalid data type {type(data_to_save).__name__}")
                return False
            
            # CRITICAL: Don't save empty data if we had data before
            if not data_to_save and self.data_file.exists():
                file_size = self.data_file.stat().st_size
                error_msg = f"CRITICAL: Attempted to save empty data! Current file size: {file_size} bytes"
                logger.critical(error_msg)
                logger.critical(f"Stack trace of save attempt: {traceback.format_stack()[-5:]}")
                self.startup_errors.append(f"🛡️ **Data Protection**: Blocked saving empty data (file: {file_size} bytes)")
                
                # Check if file has data and report to Discord
                try:
                    with open(self.data_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                        if existing_data:
                            protection_msg = f"File has {len(existing_data)} users, blocking empty save!"
                            logger.critical(protection_msg)
                            self.startup_errors.append(f"🛡️ **Protected**: {len(existing_data)} user(s) preserved")
                            # Store critical error for Discord reporting
                            self.startup_errors.append(
                                f"🚨 **CRITICAL**: Blocked empty save! File has {len(existing_data)} users"
                            )
                            return False
                except Exception as check_error:
                    logger.critical(f"Error checking existing file: {check_error}")
                    self.startup_errors.append(f"❌ **File Check Failed**: {check_error}")
                    # Still abort save to be safe - NEVER risk data loss
                    return False
            
            # Ensure directory exists
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            
            # EXTRA PROTECTION: Never save if we're about to destroy data
            if len(data_to_save) == 0 and len(self._last_known_good_data) > 0:
                error_msg = f"CRITICAL: Refusing to save! Memory has 0 users but last known good had {len(self._last_known_good_data)} users"
                logger.critical(error_msg)
                self.startup_errors.append(f"🚫 **Save Blocked**: Protected {len(self._last_known_good_data)} users from deletion")
                # Store critical error for Discord reporting
                self.startup_errors.append(
                    f"🚨 **CRITICAL**: Blocked deletion of {len(self._last_known_good_data)} users! Data restored."
                )
                # Restore from last known good
                self.data = self._last_known_good_data.copy()
                logger.critical("Restored data from last known good state")
                return False
            
            # MANDATORY backup before any file operations
            backup_created = False
            if self.data_file.exists() and self.data_file.stat().st_size > 2:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = self.data_file.parent / f"wow_characters_{timestamp}.backup"
                try:
                    shutil.copy2(self.data_file, backup_file)
                    backup_created = True
                    logger.critical(f"📦 Created mandatory backup: {backup_file}")
                    # Clean up old backups (keep only last 10)
                    backups = sorted(self.data_file.parent.glob("wow_characters_*.backup"))
                    if len(backups) > 10:
                        for old_backup in backups[:-10]:
                            try:
                                old_backup.unlink()
                                logger.debug(f"Cleaned up old backup: {old_backup}")
                            except:
                                pass  # Don't fail save for cleanup issues
                except Exception as backup_error:
                    # CRITICAL: If we can't backup, we don't save
                    error_msg = f"CRITICAL: Cannot create backup before save: {backup_error}"
                    logger.critical(error_msg)
                    self.startup_errors.append(f"❌ **Backup Failed**: {backup_error}")
                    self.startup_errors.append(f"🚨 **CRITICAL**: Save aborted - backup failure!")
                    return False
            
            # Log what we're about to save
            total_chars = sum(len(u.get("characters", [])) for u in self.data.values() if isinstance(u, dict))
            logger.critical(f"💾 SAVING: {len(self.data)} users, {total_chars} chars to {self.data_file}")
            logger.critical(f"💾 SAVE DATA PREVIEW: {str(self.data)[:300]}")
            logger.critical(f"💾 SAVE STACK TRACE: {traceback.format_stack()[-3:]}")
            
            # ATOMIC SAVE: Write to temp file first, then atomic move
            temp_file = self.data_file.with_suffix(f'.tmp_{os.getpid()}')
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data_to_save, f, indent=2, ensure_ascii=False)
                
                # CRITICAL: Verify temp file was written correctly before committing
                temp_size = temp_file.stat().st_size
                logger.critical(f"📝 Temp file written: {temp_file}, size: {temp_size} bytes")
                
                # Sanity check: temp file should not be tiny
                if temp_size <= 2:
                    error_msg = f"CRITICAL: Temp file is only {temp_size} bytes - refusing to commit!"
                    logger.critical(error_msg)
                    temp_file.unlink()  # Clean up bad temp file
                    self.startup_errors.append(f"❌ **Temp File Error**: Only {temp_size} bytes written")
                    self.startup_errors.append(f"🚨 **CRITICAL**: Save corruption detected! Temp file only {temp_size} bytes!")
                    return False
                
                # Verify temp file can be loaded back as valid JSON
                try:
                    with open(temp_file, 'r', encoding='utf-8') as f:
                        verification_data = json.load(f)
                    if not isinstance(verification_data, dict):
                        raise ValueError(f"Temp file contains {type(verification_data)}, not dict")
                    logger.critical(f"✅ Temp file verification passed: {len(verification_data)} users")
                except Exception as verify_error:
                    error_msg = f"CRITICAL: Temp file verification failed: {verify_error}"
                    logger.critical(error_msg)
                    temp_file.unlink()  # Clean up corrupted temp file
                    self.startup_errors.append(f"❌ **Verification Failed**: {verify_error}")
                    self.startup_errors.append(f"🚨 **CRITICAL**: Temp file verification failed!")
                    return False
                
                # ATOMIC COMMIT: Move temp file to final location
                logger.critical(f"🔄 LEGITIMATE SAVE: About to commit {len(data_to_save)} users to {self.data_file}")
                logger.critical(f"🔄 LEGITIMATE SAVE THREAD: {threading.current_thread().name} (ID: {threading.get_ident()})")
                temp_file.replace(self.data_file)
                logger.critical(f"💾 ATOMIC SAVE COMPLETE: {len(data_to_save)} users, {total_chars} characters")
                
                # Final verification of committed file
                if self.data_file.exists():
                    final_size = self.data_file.stat().st_size
                    logger.critical(f"🔍 POST-COMMIT VERIFICATION: Final file size: {final_size} bytes")
                    if final_size <= 2:
                        error_msg = f"CRITICAL: File was committed but is only {final_size} bytes! External interference detected!"
                        logger.critical(error_msg)
                        self.startup_errors.append(f"🚨 **CRITICAL**: File corrupted after save! {final_size} bytes!")
                        return False
                
                # SUCCESS: Update last known good data
                if len(data_to_save) > 0:
                    self._last_known_good_data = data_to_save.copy()
                    logger.critical(f"✅ Last known good updated: {len(data_to_save)} users")
                
                return True
                
            except Exception as write_error:
                # Clean up temp file on any error
                try:
                    if temp_file.exists():
                        temp_file.unlink()
                except:
                    pass
                raise write_error
            
        except Exception as e:
            # CRITICAL ERROR HANDLING: Never corrupt or reset files on error
            error_msg = f"CRITICAL SAVE FAILURE: {type(e).__name__}: {str(e)}"
            logger.critical(error_msg)
            logger.critical(f"Save error stack trace: {traceback.format_exc()}")
            
            # Add to startup errors for Discord reporting
            self.startup_errors.append(
                f"❌ **Critical Save Error**: {type(e).__name__}: {str(e)[:100]}"
            )
            self.startup_errors.append(
                f"🚨 **CRITICAL**: Save system failure! Read-only mode active."
            )
            
            # Clean up any temp files but NEVER touch the original
            try:
                temp_files = list(self.data_file.parent.glob(f"{self.data_file.stem}.tmp*"))
                for temp_file in temp_files:
                    temp_file.unlink()
                    logger.debug(f"Cleaned up temp file: {temp_file}")
            except:
                pass  # Don't fail on cleanup
            
            # IMPORTANT: Do NOT raise exception - return False instead
            # This prevents cascading failures and keeps system stable
            return False
    
    async def _report_critical_error(self, error_msg: str):
        """Report critical errors that could cause data loss"""
        logger.critical(f"CRITICAL ERROR BEING REPORTED: {error_msg}")
        
        # Add to startup errors for immediate visibility
        self.startup_errors.append(f"🚨 {error_msg[:200]}")
        
        # Send to Discord if channel is available
        if self.discord_channel:
            try:
                import discord
                embed = discord.Embed(
                    title="🚨 CRITICAL CHARACTER MANAGER ERROR",
                    description=error_msg,
                    color=0xff0000  # Red
                )
                embed.add_field(
                    name="🔍 System Status",
                    value="Character manager in protective mode\nNo data will be modified until resolved",
                    inline=False
                )
                embed.set_footer(text="Immediate attention required")
                await self.discord_channel.send(embed=embed)
            except Exception as e:
                logger.critical(f"Failed to send critical error to Discord: {e}")
        else:
            # If no Discord channel available, store for later reporting
            logger.critical("No Discord channel available for critical error reporting")
    
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