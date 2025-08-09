"""
Global Run ID Management System
Maps sequential run IDs to RaiderIO run IDs for consistent numbering
"""

import json
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from ..utils.logging import get_logger

logger = get_logger(__name__)


class RunManager:
    """Manages global run ID mapping and storage"""
    
    def __init__(self, data_file: str = "data/wow_runs.json"):
        self.data_file = Path(data_file)
        self.lock = asyncio.Lock()
        # Structure: {"runs": [{"id": raiderio_id, "data": run_data}, ...], "next_id": 1}
        self.data = {"runs": [], "next_id": 1}
        self._load_data()
    
    def _load_data(self):
        """Load run data from file"""
        try:
            if self.data_file.exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    # Ensure structure integrity
                    self.data = {
                        "runs": loaded_data.get("runs", []),
                        "next_id": loaded_data.get("next_id", 1)
                    }
                    logger.debug(f"Loaded {len(self.data['runs'])} runs from storage")
            else:
                # Create data directory if it doesn't exist
                self.data_file.parent.mkdir(parents=True, exist_ok=True)
                self.data = {"runs": [], "next_id": 1}
        except Exception as e:
            logger.error(f"Failed to load run data: {e}")
            self.data = {"runs": [], "next_id": 1}
    
    def _save_data(self):
        """Save run data to file with error handling"""
        try:
            # Ensure directory exists
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to temporary file first to avoid corruption
            temp_file = self.data_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            
            # Atomic move to final location
            temp_file.replace(self.data_file)
            logger.debug(f"Run data saved successfully to {self.data_file}")
            
        except Exception as e:
            logger.error(f"Failed to save run data to {self.data_file}: {e}")
            # Try to clean up temp file if it exists
            try:
                temp_file = self.data_file.with_suffix('.tmp')
                if temp_file.exists():
                    temp_file.unlink()
            except:
                pass
            raise
    
    async def add_runs_with_errors(self, runs_data: List[Dict[str, Any]], character_info: Optional[Dict[str, str]] = None) -> Tuple[List[int], List[Dict]]:
        """
        Add runs to the global database and return their sequential IDs plus any errors
        
        Args:
            runs_data: List of run data dicts from RaiderIO API
            character_info: Optional dict with character info (name, realm, region)
            
        Returns:
            Tuple of (List of sequential run IDs, List of error dicts)
        """
        async with self.lock:
            assigned_ids = []
            errors = []
            
            for run_data in runs_data:
                # Extract RaiderIO run ID
                raiderio_id = self._extract_raiderio_id(run_data)
                
                if not raiderio_id:
                    # Track the error for reporting
                    dungeon = run_data.get('dungeon', 'Unknown')
                    level = run_data.get('mythic_level', 0)
                    available_fields = list(run_data.keys())
                    
                    # Determine what's missing
                    missing_reason = "No 'id' or 'url' field"
                    if 'id' in run_data:
                        missing_reason = f"'id' field is empty/null: {run_data['id']}"
                    elif 'url' in run_data:
                        missing_reason = f"Could not extract ID from URL: {run_data['url']}"
                    
                    errors.append({
                        'dungeon': dungeon,
                        'level': level,
                        'reason': missing_reason,
                        'fields': available_fields
                    })
                    
                    logger.error(f"No RaiderIO ID found for run: {dungeon} +{level}")
                    logger.error(f"Available fields in run data: {available_fields}")
                    
                    # Still assign a sequential ID but mark it as missing RaiderIO ID
                    sequential_id = self.data["next_id"]
                    run_entry = {
                        "id": None,  # No RaiderIO ID available
                        "sequential_id": sequential_id,
                        "data": run_data,
                        "missing_raiderio_id": True
                    }
                    if character_info:
                        run_entry["character"] = character_info
                    self.data["runs"].append(run_entry)
                    self.data["next_id"] += 1
                    assigned_ids.append(sequential_id)
                    continue
                
                # Check if we already have this run
                existing_sequential_id = self._find_existing_run(raiderio_id)
                if existing_sequential_id:
                    assigned_ids.append(existing_sequential_id)
                    continue
                
                # Add new run with character information
                sequential_id = self.data["next_id"]
                run_entry = {
                    "id": raiderio_id,
                    "sequential_id": sequential_id,
                    "data": run_data
                }
                
                # Add character information if provided
                if character_info:
                    run_entry["character"] = character_info
                
                self.data["runs"].append(run_entry)
                self.data["next_id"] += 1
                assigned_ids.append(sequential_id)
                
                logger.debug(f"Added run #{sequential_id} -> RaiderIO ID {raiderio_id}")
            
            # Save after all runs processed
            try:
                self._save_data()
            except Exception as e:
                # Rollback all additions if save fails
                self.data["runs"] = self.data["runs"][:-len(runs_data)]
                self.data["next_id"] -= len(runs_data)
                raise
            
            return assigned_ids, errors
    
    async def add_runs(self, runs_data: List[Dict[str, Any]], character_info: Optional[Dict[str, str]] = None) -> List[int]:
        """
        Add runs to the global database and return their sequential IDs
        
        Args:
            runs_data: List of run data dicts from RaiderIO API
            character_info: Optional dict with character info (name, realm, region)
            
        Returns:
            List of sequential run IDs assigned to these runs
        """
        async with self.lock:
            assigned_ids = []
            
            for run_data in runs_data:
                # Extract RaiderIO run ID
                raiderio_id = self._extract_raiderio_id(run_data)
                
                if not raiderio_id:
                    logger.error(f"No RaiderIO ID found for run: {run_data.get('dungeon', 'Unknown')} +{run_data.get('mythic_level', 0)}")
                    logger.error(f"Available fields in run data: {list(run_data.keys())}")
                    # Still assign a sequential ID but mark it as missing RaiderIO ID
                    # This ensures the numbering stays consistent in the display
                    sequential_id = self.data["next_id"]
                    run_entry = {
                        "id": None,  # No RaiderIO ID available
                        "sequential_id": sequential_id,
                        "data": run_data,
                        "missing_raiderio_id": True
                    }
                    if character_info:
                        run_entry["character"] = character_info
                    self.data["runs"].append(run_entry)
                    self.data["next_id"] += 1
                    assigned_ids.append(sequential_id)
                    logger.warning(f"Assigned sequential ID #{sequential_id} despite missing RaiderIO ID")
                    continue
                
                # Check if we already have this run
                existing_sequential_id = self._find_existing_run(raiderio_id)
                if existing_sequential_id:
                    assigned_ids.append(existing_sequential_id)
                    continue
                
                # Add new run with character information
                sequential_id = self.data["next_id"]
                run_entry = {
                    "id": raiderio_id,
                    "sequential_id": sequential_id,
                    "data": run_data
                }
                
                # Add character information if provided
                if character_info:
                    run_entry["character"] = character_info
                
                self.data["runs"].append(run_entry)
                self.data["next_id"] += 1
                assigned_ids.append(sequential_id)
                
                logger.debug(f"Added run #{sequential_id} -> RaiderIO ID {raiderio_id}")
            
            # Save after all runs processed
            try:
                self._save_data()
            except Exception as e:
                # Rollback all additions if save fails
                self.data["runs"] = self.data["runs"][:-len(runs_data)]
                self.data["next_id"] -= len(runs_data)
                raise
            
            return assigned_ids
    
    def _extract_raiderio_id(self, run_data: Dict[str, Any]) -> Optional[int]:
        """Extract RaiderIO run ID from run data"""
        # Log available fields for debugging
        if logger.level <= 10:  # DEBUG level
            available_fields = list(run_data.keys())
            logger.debug(f"Run data fields: {available_fields}")
            if 'dungeon' in run_data and 'mythic_level' in run_data:
                logger.debug(f"Processing run: {run_data.get('dungeon')} +{run_data.get('mythic_level')}")
        
        # Try direct ID field first
        if 'id' in run_data and run_data['id']:
            try:
                run_id = int(run_data['id'])
                logger.debug(f"Found ID in 'id' field: {run_id}")
                return run_id
            except (ValueError, TypeError):
                logger.warning(f"Failed to convert 'id' field to int: {run_data['id']}")
        
        # Try extracting from URL
        if 'url' in run_data and run_data['url']:
            try:
                url_parts = str(run_data['url']).split('/')
                if url_parts and url_parts[-1].isdigit():
                    run_id = int(url_parts[-1])
                    logger.debug(f"Extracted ID from URL: {run_id} from {run_data['url']}")
                    return run_id
            except (ValueError, TypeError):
                logger.warning(f"Failed to extract ID from URL: {run_data['url']}")
        
        # Try other potential fields
        for field in ['run_id', 'keystone_run_id', 'mythic_plus_run_id']:
            if field in run_data and run_data[field]:
                try:
                    run_id = int(run_data[field])
                    logger.debug(f"Found ID in '{field}' field: {run_id}")
                    return run_id
                except (ValueError, TypeError):
                    logger.warning(f"Failed to convert '{field}' field to int: {run_data[field]}")
        
        logger.error(f"Could not extract RaiderIO ID from run: {run_data.get('dungeon', 'Unknown')} +{run_data.get('mythic_level', 0)}")
        return None
    
    def _find_existing_run(self, raiderio_id: int) -> Optional[int]:
        """Find existing run by RaiderIO ID, return sequential ID if found"""
        if raiderio_id is None:
            return None
        for run in self.data["runs"]:
            if run.get("id") == raiderio_id:
                return run.get("sequential_id")
        return None
    
    async def get_run_by_sequential_id(self, sequential_id: int) -> Optional[Dict[str, Any]]:
        """
        Get run data by sequential ID
        
        Args:
            sequential_id: Sequential run ID (1, 2, 3...)
            
        Returns:
            Dict containing raiderio_id and original run data, or None if not found
        """
        for run in self.data["runs"]:
            if run.get("sequential_id") == sequential_id:
                result = {
                    "raiderio_id": run.get("id"),  # May be None for runs without IDs
                    "sequential_id": run.get("sequential_id"),
                    "data": run.get("data", {}),
                    "missing_raiderio_id": run.get("missing_raiderio_id", False)
                }
                # Add character info if available
                if "character" in run:
                    result["character"] = run["character"]
                return result
        return None
    
    async def get_recent_runs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get most recently added runs"""
        recent_runs = sorted(self.data["runs"], key=lambda x: x["sequential_id"], reverse=True)
        return recent_runs[:limit]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about stored runs"""
        return {
            "total_runs": len(self.data["runs"]),
            "next_sequential_id": self.data["next_id"],
            "latest_run_id": max([r["sequential_id"] for r in self.data["runs"]]) if self.data["runs"] else 0
        }


# Global run manager instance
run_manager = RunManager()