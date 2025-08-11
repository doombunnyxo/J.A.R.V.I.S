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
            if category == "personal":
                # For personal tasks, check current week's tasks
                current_week = self._get_current_week_start()
                self._ensure_current_week_data(roster_key, current_week)
                existing_tasks = self.data[roster_key]["weekly_data"][current_week]["remaining_tasks"][category]
                location = "this week"
            else:
                # For household tasks, check base tasks
                existing_tasks = self.data[roster_key]["base_tasks"][category]
                location = "base tasks"
            
            for task in existing_tasks:
                if task["name"].lower() == task_name.lower():
                    return {
                        "success": False,
                        "message": f"Task **{task_name}** already exists in {category} {location}"
                    }
            
            task_data = {
                "name": task_name,
                "points": points,
                "added_by": user_id,
                "added_at": datetime.now().isoformat()
            }
            
            # Handle different task types based on what we already set up above
            if category == "personal":
                # Personal tasks are one-off: add only to current week, not base tasks
                original_remaining = self.data[roster_key]["weekly_data"][current_week]["remaining_tasks"][category].copy()
                self.data[roster_key]["weekly_data"][current_week]["remaining_tasks"][category].append(task_data)
                original_base_tasks = None  # No base tasks change for personal
            else:  # household
                # Household tasks are recurring: add to base tasks and current week
                original_base_tasks = self.data[roster_key]["base_tasks"][category].copy()
                self.data[roster_key]["base_tasks"][category].append(task_data)
                
                original_remaining = self.data[roster_key]["weekly_data"][current_week]["remaining_tasks"][category].copy()
                self.data[roster_key]["weekly_data"][current_week]["remaining_tasks"][category].append(task_data)
            
            try:
                self._save_data()
            except Exception as e:
                # Rollback the in-memory changes if save fails
                if original_base_tasks is not None:  # Only rollback base tasks if we changed them
                    self.data[roster_key]["base_tasks"][category] = original_base_tasks
                self.data[roster_key]["weekly_data"][current_week]["remaining_tasks"][category] = original_remaining
                return {
                    "success": False,
                    "message": f"❌ Failed to save roster data: {str(e)}"
                }
            
            if category == "personal":
                # For personal tasks, count current week's personal tasks
                task_count = len(self.data[roster_key]["weekly_data"][current_week]["remaining_tasks"]["personal"])
                message_suffix = " (one-time task)"
            else:
                # For household tasks, count base tasks
                task_count = len(self.data[roster_key]["base_tasks"][category])
                message_suffix = " (recurring weekly)"
            
            return {
                "success": True,
                "message": f"✅ Added {category} task **{task_name}** ({points} points){message_suffix}",
                "task_count": task_count
            }

    def _ensure_current_week_data(self, roster_key: str, current_week: str):
        """Ensure current week data exists and is up to date"""
        roster = self.data[roster_key]
        
        if current_week not in roster["weekly_data"]:
            # Create new week data
            roster["weekly_data"][current_week] = {
                "remaining_tasks": {
                    "personal": [],  # Personal tasks don't auto-refresh
                    "household": roster["base_tasks"]["household"].copy()  # Household tasks refresh weekly
                },
                "completed_tasks": [],
                "user_points": {member_id: 0 for member_id in roster["members"]},
                "weekly_goal": 4  # Default goal
            }
            
            # Handle carryover from previous week
            if len(roster["weekly_data"]) > 1:
                previous_weeks = sorted([w for w in roster["weekly_data"].keys() if w != current_week])
                if previous_weeks:
                    last_week = previous_weeks[-1]
                    last_week_data = roster["weekly_data"][last_week]
                    
                    # Calculate total point increase from incomplete tasks
                    total_point_increase = 0
                    all_incomplete_tasks = []
                    
                    # Add undone PERSONAL tasks with increased points (add base value only once)
                    for task in last_week_data["remaining_tasks"]["personal"]:
                        # Find original base point value (the value when first created)
                        original_points = task.get("original_points", task["points"])
                        
                        # Always increase by the original base amount only
                        increased_task = task.copy()
                        increased_task["points"] = original_points + original_points  # base + base = double
                        increased_task["original_points"] = original_points
                        increased_task["doubled_from_previous"] = True
                        
                        roster["weekly_data"][current_week]["remaining_tasks"]["personal"].append(increased_task)
                        all_incomplete_tasks.append(task)
                        total_point_increase += original_points
                    
                    # Add undone HOUSEHOLD tasks with increased points (these also refresh from base)
                    for task in last_week_data["remaining_tasks"]["household"]:
                        # Find if this task is still in base_tasks (it should be)
                        base_task_exists = any(
                            base_task["name"].lower() == task["name"].lower() 
                            for base_task in roster["base_tasks"]["household"]
                        )
                        
                        if base_task_exists:
                            # Find original base point value (the value when first created in base_tasks)
                            original_points = task.get("original_points")
                            if not original_points:
                                # Find from base tasks
                                for base_task in roster["base_tasks"]["household"]:
                                    if base_task["name"].lower() == task["name"].lower():
                                        original_points = base_task["points"]
                                        break
                            
                            # Always increase by the original base amount only
                            increased_task = task.copy()
                            increased_task["points"] = original_points + original_points  # base + base = double
                            increased_task["original_points"] = original_points
                            increased_task["doubled_from_previous"] = True
                            increased_task["name"] = f"{task['name']} (Overdue)"  # Mark as overdue
                            
                            roster["weekly_data"][current_week]["remaining_tasks"]["household"].append(increased_task)
                            all_incomplete_tasks.append(task)
                            total_point_increase += original_points
                    
                    # Calculate new weekly goal
                    if all_incomplete_tasks:
                        # Count total tasks this week (fresh + carried over)
                        total_personal_tasks = len(roster["weekly_data"][current_week]["remaining_tasks"]["personal"])
                        total_household_tasks = len(roster["weekly_data"][current_week]["remaining_tasks"]["household"])
                        total_tasks_this_week = total_personal_tasks + total_household_tasks
                        
                        # Calculate average point increase across ALL tasks this week and round up
                        average_increase = total_point_increase / total_tasks_this_week
                        goal_increase = int(average_increase) + (1 if average_increase > int(average_increase) else 0)
                        new_weekly_goal = 4 + goal_increase
                        
                        # Store the new goal for this week
                        roster["weekly_data"][current_week]["weekly_goal"] = new_weekly_goal
                        roster["weekly_data"][current_week]["goal_increase_reason"] = {
                            "incomplete_tasks": len(all_incomplete_tasks),
                            "total_tasks_this_week": total_tasks_this_week,
                            "total_point_increase": total_point_increase,
                            "average_increase": average_increase,
                            "goal_increase": goal_increase
                        }
                    else:
                        # No incomplete tasks, standard goal
                        roster["weekly_data"][current_week]["weekly_goal"] = 4
        
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
        
        roster_data = self.data[roster_key].copy()
        roster_data["roster_key"] = roster_key
        return roster_data

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

    async def get_weekly_goal(self, roster_name: str, guild_id: str) -> int:
        """Get the weekly goal for the current week"""
        roster_info = await self.get_roster_info(roster_name, guild_id)
        if not roster_info:
            return 4  # Default goal
        
        current_week = roster_info["current_week"]
        return roster_info["weekly_data"][current_week].get("weekly_goal", 4)

    async def get_roster_by_channel(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get roster associated with a specific channel"""
        for roster_key, roster_data in self.data.items():
            if roster_data.get("channel_id") == channel_id:
                roster_data["roster_key"] = roster_key
                return roster_data
        return None


# Global cleaning manager instance
cleaning_manager = CleaningManager()