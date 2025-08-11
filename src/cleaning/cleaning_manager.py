"""
Cleaning Roster Management System
Manages cleaning rosters, tasks, and user points tracking
"""

import json
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timedelta
from ..utils.logging import get_logger

logger = get_logger(__name__)


class CleaningManager:
    """Manages cleaning rosters, tasks, and points"""
    
    def __init__(self, data_file: str = "data/cleaning_rosters.json"):
        self.data_file = Path(data_file)
        self.data = {}
        self.lock = asyncio.Lock()
        logger.info(f"Initializing CleaningManager with file: {self.data_file}")
        self._load_data()
        logger.info(f"CleaningManager initialized with {len(self.data)} rosters")
    
    def _load_data(self):
        """Load cleaning roster data from file"""
        try:
            if self.data_file.exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    
                if isinstance(loaded_data, dict):
                    self.data = loaded_data
                    logger.info(f"Loaded {len(self.data)} cleaning rosters")
                else:
                    logger.error(f"Invalid data structure in {self.data_file}, expected dict")
                    self.data = {}
            else:
                self.data_file.parent.mkdir(parents=True, exist_ok=True)
                self.data = {}
                logger.info("No existing cleaning roster data file, starting fresh")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            self.data = {}
            
        except Exception as e:
            logger.error(f"Error loading cleaning roster data: {e}")
            self.data = {}
    
    def _save_data(self):
        """Save cleaning roster data to file"""
        return self._save_data_to_file(self.data)
    
    def _save_data_to_file(self, data_to_save: Dict[str, Any]) -> bool:
        """Save cleaning roster data to file"""
        try:
            if not isinstance(data_to_save, dict):
                logger.error(f"Invalid data type for save: {type(data_to_save)}")
                return False
            
            # Ensure directory exists
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to temp file first, then atomic move
            temp_file = self.data_file.with_suffix(f'.tmp_{id(self)}')
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data_to_save, f, indent=2, ensure_ascii=False)
                
                # Atomic commit
                temp_file.replace(self.data_file)
                logger.debug(f"Saved cleaning roster data: {len(data_to_save)} rosters")
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
            logger.error(f"Error saving cleaning roster data: {e}")
            return False

    def _get_current_week_start(self) -> str:
        """Get the start of the current week (Monday) as ISO string"""
        today = datetime.now()
        # Find Monday of current week (weekday() returns 0=Monday, 6=Sunday)
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)
        # Set to start of day
        monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        return monday.isoformat()

    async def create_roster(self, roster_name: str, creator_id: str, guild_id: str) -> Dict[str, Any]:
        """Create a new cleaning roster"""
        async with self.lock:
            roster_key = f"{guild_id}_{roster_name.lower()}"
            
            if roster_key in self.data:
                return {
                    "success": False,
                    "message": f"Roster **{roster_name}** already exists in this server"
                }
            
            current_week = self._get_current_week_start()
            
            self.data[roster_key] = {
                "name": roster_name,
                "guild_id": guild_id,
                "creator_id": creator_id,
                "created_at": datetime.now().isoformat(),
                "channel_id": None,  # Will be set when channel is created
                "members": [creator_id],
                "base_tasks": {
                    "personal": [],
                    "household": []
                },
                "lifetime_points": {creator_id: 0},  # Track lifetime points per user
                "weekly_data": {
                    current_week: {
                        "remaining_tasks": {"personal": [], "household": []},
                        "completed_tasks": [],
                        "user_points": {creator_id: 0}
                    }
                },
                "current_week": current_week
            }
            
            try:
                self._save_data()
            except Exception as e:
                # Rollback the in-memory change if save fails
                del self.data[roster_key]
                return {
                    "success": False,
                    "message": f"❌ Failed to save roster data: {str(e)}"
                }
            
            return {
                "success": True,
                "message": f"✅ Created cleaning roster **{roster_name}**",
                "roster_key": roster_key
            }

    async def add_member(self, roster_name: str, user_id: str, guild_id: str) -> Dict[str, Any]:
        """Add a member to a cleaning roster"""
        async with self.lock:
            roster_key = f"{guild_id}_{roster_name.lower()}"
            
            if roster_key not in self.data:
                return {
                    "success": False,
                    "message": f"Roster **{roster_name}** not found"
                }
            
            if user_id in self.data[roster_key]["members"]:
                return {
                    "success": False,
                    "message": f"User is already a member of **{roster_name}**"
                }
            
            # Store original members for rollback
            original_members = self.data[roster_key]["members"].copy()
            original_lifetime_points = self.data[roster_key]["lifetime_points"].copy()
            
            self.data[roster_key]["members"].append(user_id)
            # Initialize lifetime points for new member
            if user_id not in self.data[roster_key]["lifetime_points"]:
                self.data[roster_key]["lifetime_points"][user_id] = 0
            
            try:
                self._save_data()
            except Exception as e:
                # Rollback the in-memory change if save fails
                self.data[roster_key]["members"] = original_members
                self.data[roster_key]["lifetime_points"] = original_lifetime_points
                return {
                    "success": False,
                    "message": f"❌ Failed to save roster data: {str(e)}"
                }
            
            return {
                "success": True,
                "message": f"✅ Added user to **{roster_name}**",
                "member_count": len(self.data[roster_key]["members"])
            }

    async def set_channel(self, roster_name: str, channel_id: str, guild_id: str) -> Dict[str, Any]:
        """Set the Discord channel for a roster"""
        async with self.lock:
            roster_key = f"{guild_id}_{roster_name.lower()}"
            
            if roster_key not in self.data:
                return {
                    "success": False,
                    "message": f"Roster **{roster_name}** not found"
                }
            
            original_channel_id = self.data[roster_key]["channel_id"]
            self.data[roster_key]["channel_id"] = channel_id
            
            try:
                self._save_data()
            except Exception as e:
                # Rollback the in-memory change if save fails
                self.data[roster_key]["channel_id"] = original_channel_id
                return {
                    "success": False,
                    "message": f"❌ Failed to save roster data: {str(e)}"
                }
            
            return {
                "success": True,
                "message": f"✅ Set channel for **{roster_name}**"
            }

    async def add_task(self, roster_name: str, guild_id: str, task_name: str, 
                      category: str, points: int, user_id: str) -> Dict[str, Any]:
        """Add a cleaning task to a roster"""
        async with self.lock:
            roster_key = f"{guild_id}_{roster_name.lower()}"
            
            if roster_key not in self.data:
                return {
                    "success": False,
                    "message": f"Roster **{roster_name}** not found"
                }
            
            if user_id not in self.data[roster_key]["members"]:
                return {
                    "success": False,
                    "message": "Only roster members can add tasks"
                }
            
            if category not in ["personal", "household"]:
                return {
                    "success": False,
                    "message": "Category must be 'personal' or 'household'"
                }
            
            if points < 1 or points > 10:
                return {
                    "success": False,
                    "message": "Points must be between 1 and 10"
                }
            
            # Check if task already exists
            for task in self.data[roster_key]["base_tasks"][category]:
                if task["name"].lower() == task_name.lower():
                    return {
                        "success": False,
                        "message": f"Task **{task_name}** already exists in {category} category"
                    }
            
            task_data = {
                "name": task_name,
                "points": points,
                "added_by": user_id,
                "added_at": datetime.now().isoformat()
            }
            
            # Store original tasks for rollback
            original_base_tasks = self.data[roster_key]["base_tasks"][category].copy()
            self.data[roster_key]["base_tasks"][category].append(task_data)
            
            # Add to current week's remaining tasks
            current_week = self._get_current_week_start()
            self._ensure_current_week_data(roster_key, current_week)
            
            original_remaining = self.data[roster_key]["weekly_data"][current_week]["remaining_tasks"][category].copy()
            self.data[roster_key]["weekly_data"][current_week]["remaining_tasks"][category].append(task_data)
            
            try:
                self._save_data()
            except Exception as e:
                # Rollback the in-memory changes if save fails
                self.data[roster_key]["base_tasks"][category] = original_base_tasks
                self.data[roster_key]["weekly_data"][current_week]["remaining_tasks"][category] = original_remaining
                return {
                    "success": False,
                    "message": f"❌ Failed to save roster data: {str(e)}"
                }
            
            return {
                "success": True,
                "message": f"✅ Added {category} task **{task_name}** ({points} points)",
                "task_count": len(self.data[roster_key]["base_tasks"][category])
            }

    def _ensure_current_week_data(self, roster_key: str, current_week: str):
        """Ensure current week data exists and is up to date"""
        roster = self.data[roster_key]
        
        if current_week not in roster["weekly_data"]:
            # Create new week data by copying all base tasks as remaining
            roster["weekly_data"][current_week] = {
                "remaining_tasks": {
                    "personal": roster["base_tasks"]["personal"].copy(),
                    "household": roster["base_tasks"]["household"].copy()
                },
                "completed_tasks": [],
                "user_points": {member_id: 0 for member_id in roster["members"]}
            }
            
            # Add any undone tasks from previous week with double points
            if len(roster["weekly_data"]) > 1:
                previous_weeks = sorted([w for w in roster["weekly_data"].keys() if w != current_week])
                if previous_weeks:
                    last_week = previous_weeks[-1]
                    last_week_data = roster["weekly_data"][last_week]
                    
                    # Add undone tasks with doubled points
                    for category in ["personal", "household"]:
                        for task in last_week_data["remaining_tasks"][category]:
                            doubled_task = task.copy()
                            doubled_task["points"] = task["points"] * 2
                            doubled_task["doubled_from_previous"] = True
                            roster["weekly_data"][current_week]["remaining_tasks"][category].append(doubled_task)
        
        # Update current week pointer
        roster["current_week"] = current_week

    async def complete_task(self, roster_name: str, guild_id: str, task_name: str, 
                          category: str, user_id: str) -> Dict[str, Any]:
        """Mark a task as completed by a user"""
        async with self.lock:
            roster_key = f"{guild_id}_{roster_name.lower()}"
            
            if roster_key not in self.data:
                return {
                    "success": False,
                    "message": f"Roster **{roster_name}** not found"
                }
            
            if user_id not in self.data[roster_key]["members"]:
                return {
                    "success": False,
                    "message": "Only roster members can complete tasks"
                }
            
            current_week = self._get_current_week_start()
            self._ensure_current_week_data(roster_key, current_week)
            
            weekly_data = self.data[roster_key]["weekly_data"][current_week]
            remaining_tasks = weekly_data["remaining_tasks"][category]
            
            # Find the task
            task_to_complete = None
            task_index = -1
            for i, task in enumerate(remaining_tasks):
                if task["name"].lower() == task_name.lower():
                    task_to_complete = task
                    task_index = i
                    break
            
            if not task_to_complete:
                return {
                    "success": False,
                    "message": f"Task **{task_name}** not found in {category} remaining tasks"
                }
            
            # Store originals for rollback
            original_remaining = remaining_tasks.copy()
            original_completed = weekly_data["completed_tasks"].copy()
            original_points = weekly_data["user_points"].copy()
            original_lifetime_points = self.data[roster_key]["lifetime_points"].copy()
            
            # Remove from remaining tasks
            remaining_tasks.pop(task_index)
            
            # Add to completed tasks
            completed_task = task_to_complete.copy()
            completed_task["completed_by"] = user_id
            completed_task["completed_at"] = datetime.now().isoformat()
            completed_task["category"] = category
            weekly_data["completed_tasks"].append(completed_task)
            
            # Add points to user (both weekly and lifetime)
            if user_id not in weekly_data["user_points"]:
                weekly_data["user_points"][user_id] = 0
            if user_id not in self.data[roster_key]["lifetime_points"]:
                self.data[roster_key]["lifetime_points"][user_id] = 0
            
            points_earned = task_to_complete["points"]
            weekly_data["user_points"][user_id] += points_earned
            self.data[roster_key]["lifetime_points"][user_id] += points_earned
            
            try:
                self._save_data()
            except Exception as e:
                # Rollback the in-memory changes if save fails
                self.data[roster_key]["weekly_data"][current_week]["remaining_tasks"][category] = original_remaining
                self.data[roster_key]["weekly_data"][current_week]["completed_tasks"] = original_completed
                self.data[roster_key]["weekly_data"][current_week]["user_points"] = original_points
                self.data[roster_key]["lifetime_points"] = original_lifetime_points
                return {
                    "success": False,
                    "message": f"❌ Failed to save roster data: {str(e)}"
                }
            
            weekly_points = weekly_data["user_points"][user_id]
            lifetime_points = self.data[roster_key]["lifetime_points"][user_id]
            return {
                "success": True,
                "message": f"✅ **{task_name}** completed! +{points_earned} points (Weekly: {weekly_points}/4, Lifetime: {lifetime_points})",
                "points_earned": points_earned,
                "weekly_points": weekly_points,
                "lifetime_points": lifetime_points
            }

    async def get_roster_info(self, roster_name: str, guild_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a cleaning roster"""
        roster_key = f"{guild_id}_{roster_name.lower()}"
        
        if roster_key not in self.data:
            return None
        
        current_week = self._get_current_week_start()
        self._ensure_current_week_data(roster_key, current_week)
        
        return self.data[roster_key]

    async def get_remaining_tasks(self, roster_name: str, guild_id: str) -> Optional[Dict[str, Any]]:
        """Get remaining tasks for the current week"""
        roster_info = await self.get_roster_info(roster_name, guild_id)
        if not roster_info:
            return None
        
        current_week = roster_info["current_week"]
        weekly_data = roster_info["weekly_data"][current_week]
        
        return {
            "personal": weekly_data["remaining_tasks"]["personal"],
            "household": weekly_data["remaining_tasks"]["household"],
            "total_remaining": (len(weekly_data["remaining_tasks"]["personal"]) + 
                              len(weekly_data["remaining_tasks"]["household"]))
        }

    async def get_completed_tasks(self, roster_name: str, guild_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get completed tasks for the current week"""
        roster_info = await self.get_roster_info(roster_name, guild_id)
        if not roster_info:
            return None
        
        current_week = roster_info["current_week"]
        return roster_info["weekly_data"][current_week]["completed_tasks"]

    async def get_user_points(self, roster_name: str, guild_id: str) -> Optional[Dict[str, int]]:
        """Get user points for the current week"""
        roster_info = await self.get_roster_info(roster_name, guild_id)
        if not roster_info:
            return None
        
        current_week = roster_info["current_week"]
        return roster_info["weekly_data"][current_week]["user_points"]

    async def get_lifetime_points(self, roster_name: str, guild_id: str) -> Optional[Dict[str, int]]:
        """Get lifetime points for all users"""
        roster_info = await self.get_roster_info(roster_name, guild_id)
        if not roster_info:
            return None
        
        return roster_info["lifetime_points"]

    async def get_guild_rosters(self, guild_id: str) -> List[Dict[str, Any]]:
        """Get all rosters for a guild"""
        rosters = []
        for roster_key, roster_data in self.data.items():
            if roster_data["guild_id"] == guild_id:
                rosters.append(roster_data)
        return rosters


# Global cleaning manager instance
cleaning_manager = CleaningManager()