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
                with open(self.data_file, 'r') as f:
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
                self._save_data()
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
            with open(temp_file, 'w') as f:
                json.dump(self.data, f, indent=2)
            
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
                    logger.warning(f"No RaiderIO ID found for run: {run_data.get('dungeon', 'Unknown')}")
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
        # Try direct ID field first
        if 'id' in run_data and run_data['id']:
            try:
                return int(run_data['id'])
            except (ValueError, TypeError):
                pass
        
        # Try extracting from URL
        if 'url' in run_data and run_data['url']:
            try:
                url_parts = str(run_data['url']).split('/')
                if url_parts and url_parts[-1].isdigit():
                    return int(url_parts[-1])
            except (ValueError, TypeError):
                pass
        
        # Try other potential fields
        for field in ['run_id', 'keystone_run_id', 'mythic_plus_run_id']:
            if field in run_data and run_data[field]:
                try:
                    return int(run_data[field])
                except (ValueError, TypeError):
                    pass
        
        return None
    
    def _find_existing_run(self, raiderio_id: int) -> Optional[int]:
        """Find existing run by RaiderIO ID, return sequential ID if found"""
        for run in self.data["runs"]:
            if run["id"] == raiderio_id:
                return run["sequential_id"]
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
            if run["sequential_id"] == sequential_id:
                return {
                    "raiderio_id": run["id"],
                    "sequential_id": run["sequential_id"],
                    "data": run["data"]
                }
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