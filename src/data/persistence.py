import json
import os
import asyncio
from typing import Dict, Any, Optional
from ..config import config

class DataManager:
    """Handles persistent data storage and retrieval"""
    
    def __init__(self):
        self.conversation_history: Dict[str, list] = {}
        self.user_settings: Dict[str, dict] = {}
        self.permanent_context: Dict[str, list] = {}
        self.unfiltered_permanent_context: Dict[str, list] = {}
        self._lock = asyncio.Lock()
    
    async def load_all_data(self):
        """Load all data from files asynchronously"""
        async with self._lock:
            await asyncio.gather(
                self._load_conversation_history(),
                self._load_user_settings(),
                self._load_permanent_context(),
                self._load_unfiltered_permanent_context()
            )
    
    async def _load_conversation_history(self):
        """Load conversation history from file"""
        try:
            if os.path.exists(config.HISTORY_FILE):
                with open(config.HISTORY_FILE, 'r', encoding='utf-8') as f:
                    self.conversation_history = json.load(f)
            else:
                self.conversation_history = {}
        except Exception as e:
            print(f"Error loading conversation history: {e}")
            self.conversation_history = {}
    
    async def _load_user_settings(self):
        """Load user settings from file"""
        try:
            if os.path.exists(config.SETTINGS_FILE):
                with open(config.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    self.user_settings = json.load(f)
            else:
                self.user_settings = {}
        except Exception as e:
            print(f"Error loading user settings: {e}")
            self.user_settings = {}
    
    async def _load_permanent_context(self):
        """Load permanent context from file"""
        try:
            if os.path.exists(config.PERMANENT_CONTEXT_FILE):
                with open(config.PERMANENT_CONTEXT_FILE, 'r', encoding='utf-8') as f:
                    self.permanent_context = json.load(f)
            else:
                self.permanent_context = {}
        except Exception as e:
            print(f"Error loading permanent context: {e}")
            self.permanent_context = {}
    
    async def _load_unfiltered_permanent_context(self):
        """Load unfiltered permanent context from file"""
        try:
            if os.path.exists(config.UNFILTERED_PERMANENT_CONTEXT_FILE):
                with open(config.UNFILTERED_PERMANENT_CONTEXT_FILE, 'r', encoding='utf-8') as f:
                    self.unfiltered_permanent_context = json.load(f)
            else:
                self.unfiltered_permanent_context = {}
        except Exception as e:
            print(f"Error loading unfiltered permanent context: {e}")
            self.unfiltered_permanent_context = {}
    
    async def save_conversation_history(self):
        """Save conversation history to file"""
        async with self._lock:
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(config.HISTORY_FILE), exist_ok=True)
                with open(config.HISTORY_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.conversation_history, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Error saving conversation history: {e}")
    
    async def save_user_settings(self):
        """Save user settings to file"""
        async with self._lock:
            try:
                os.makedirs(os.path.dirname(config.SETTINGS_FILE), exist_ok=True)
                with open(config.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.user_settings, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Error saving user settings: {e}")
    
    async def save_permanent_context(self):
        """Save permanent context to file"""
        async with self._lock:
            try:
                os.makedirs(os.path.dirname(config.PERMANENT_CONTEXT_FILE), exist_ok=True)
                with open(config.PERMANENT_CONTEXT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.permanent_context, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Error saving permanent context: {e}")
    
    async def save_unfiltered_permanent_context(self):
        """Save unfiltered permanent context to file"""
        async with self._lock:
            try:
                os.makedirs(os.path.dirname(config.UNFILTERED_PERMANENT_CONTEXT_FILE), exist_ok=True)
                with open(config.UNFILTERED_PERMANENT_CONTEXT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.unfiltered_permanent_context, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Error saving unfiltered permanent context: {e}")
    
    def get_user_key(self, user) -> str:
        """Generate consistent user key for data storage"""
        return f"{user.name}#{user.discriminator}" if user.discriminator != "0" else user.name
    
    def get_user_history(self, user_key: str) -> list:
        """Get conversation history for a user"""
        return self.conversation_history.get(user_key, [])
    
    def add_user_message(self, user_key: str, message: dict):
        """Add a message to user's conversation history"""
        if user_key not in self.conversation_history:
            self.conversation_history[user_key] = []
        
        self.conversation_history[user_key].append(message)
        
        # Keep only last N messages to avoid token limits
        if len(self.conversation_history[user_key]) > config.AI_MAX_HISTORY:
            self.conversation_history[user_key] = self.conversation_history[user_key][-config.AI_MAX_HISTORY:]
    
    def clear_user_history(self, user_key: str) -> bool:
        """Clear conversation history for a user"""
        if user_key in self.conversation_history:
            self.conversation_history[user_key] = []
            return True
        return False
    
    def get_user_settings(self, user_key: str) -> dict:
        """Get settings for a user"""
        if user_key not in self.user_settings:
            self.user_settings[user_key] = {"use_channel_context": True}
        return self.user_settings[user_key]
    
    def update_user_setting(self, user_key: str, setting: str, value: Any):
        """Update a specific setting for a user"""
        if user_key not in self.user_settings:
            self.user_settings[user_key] = {"use_channel_context": True}
        self.user_settings[user_key][setting] = value
    
    def get_permanent_context(self, user_key: str) -> list:
        """Get permanent context for a user"""
        return self.permanent_context.get(user_key, [])
    
    def add_permanent_context(self, user_key: str, context: str):
        """Add permanent context for a user"""
        if user_key not in self.permanent_context:
            self.permanent_context[user_key] = []
        self.permanent_context[user_key].append(context)
    
    def remove_permanent_context(self, user_key: str, index: int) -> Optional[str]:
        """Remove permanent context item by index"""
        if user_key in self.permanent_context and 0 <= index < len(self.permanent_context[user_key]):
            return self.permanent_context[user_key].pop(index)
        return None
    
    def clear_permanent_context(self, user_key: str) -> int:
        """Clear all permanent context for a user"""
        if user_key in self.permanent_context:
            count = len(self.permanent_context[user_key])
            self.permanent_context[user_key] = []
            return count
        return 0
    
    def get_unfiltered_permanent_context(self, user_key: str) -> list:
        """Get unfiltered permanent context for a user"""
        return self.unfiltered_permanent_context.get(user_key, [])
    
    def add_unfiltered_permanent_context(self, user_key: str, context: str):
        """Add unfiltered permanent context for a user"""
        if user_key not in self.unfiltered_permanent_context:
            self.unfiltered_permanent_context[user_key] = []
        self.unfiltered_permanent_context[user_key].append(context)
    
    def remove_unfiltered_permanent_context(self, user_key: str, index: int) -> Optional[str]:
        """Remove unfiltered permanent context item by index"""
        if user_key in self.unfiltered_permanent_context and 0 <= index < len(self.unfiltered_permanent_context[user_key]):
            return self.unfiltered_permanent_context[user_key].pop(index)
        return None
    
    def clear_unfiltered_permanent_context(self, user_key: str) -> int:
        """Clear all unfiltered permanent context for a user"""
        if user_key in self.unfiltered_permanent_context:
            count = len(self.unfiltered_permanent_context[user_key])
            self.unfiltered_permanent_context[user_key] = []
            return count
        return 0
    
    def get_stats(self) -> dict:
        """Get storage statistics"""
        total_users = len(self.conversation_history)
        total_messages = sum(len(history) for history in self.conversation_history.values())
        total_permanent_items = sum(len(items) for items in self.permanent_context.values())
        total_unfiltered_permanent_items = sum(len(items) for items in self.unfiltered_permanent_context.values())
        
        # File sizes
        file_sizes = {}
        for name, path in config.get_file_paths().items():
            if os.path.exists(path):
                file_sizes[name] = os.path.getsize(path)
            else:
                file_sizes[name] = 0
        
        return {
            'total_users': total_users,
            'total_messages': total_messages,
            'total_permanent_items': total_permanent_items,
            'total_unfiltered_permanent_items': total_unfiltered_permanent_items,
            'file_sizes': file_sizes
        }

# Global data manager instance
data_manager = DataManager()