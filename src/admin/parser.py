"""
Main admin intent parser - handles action identification and delegates parameter extraction
"""
import re
from typing import Optional, Tuple, Dict, Any

from .utils import AdminUtils
from .extractors import AdminParameterExtractors


class AdminIntentParser:
    """Two-phase admin parser: identify action type, then extract parameters"""
    
    def __init__(self, bot, debug_channel=None):
        self.bot = bot
        self.debug_channel = debug_channel
        self.utils = AdminUtils(bot)
        self.extractors = AdminParameterExtractors(self.utils)
    
    async def parse_admin_intent(self, message_content: str, guild, message_author=None) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Parse user message to detect admin intentions and extract parameters"""
        content = message_content.lower()
        
        from ..utils.logging import get_logger
        logger = get_logger(__name__)
        logger.info(f"Parsing admin intent from: '{message_content}'")
        
        # Phase 1: Quickly identify action type
        action_type = self._identify_action_type(content)
        logger.info(f"🎯 ADMIN PARSER DEBUG: Action type identified: {action_type} for content: '{content}'")
        
        if not action_type:
            return None, None
        
        # Phase 2: Extract parameters for the specific action type
        try:
            parameters = await self._extract_parameters(action_type, content, message_content, guild, message_author)
            
            if parameters is not None:
                return action_type, parameters
            else:
                return None, None
                
        except Exception as e:
            return None, None
    
    def _identify_action_type(self, content: str) -> Optional[str]:
        """Phase 1: Quickly identify what type of admin action this is"""
        
        # Check for specific action keywords (order matters - more specific first)
        action_patterns = {
            # User moderation
            'kick_user': ['kick', 'boot', 'eject'],
            'ban_user': ['ban'],
            'unban_user': ['unban'],
            'timeout_user': ['timeout', 'mute', 'silence', 'quiet', 'shush'],
            'remove_timeout': ['remove timeout', 'unmute', 'unsilence'],
            
            # Nickname changes
            'change_nickname': ['nickname', 'nick', 'rename user', 'rename member', 'change name of', 'change nickname', 'set nickname', 'update nickname', 'rename'],
            
            # Role management
            'add_role': ['add role', 'give role'],
            'remove_role': ['remove role', 'take role'],
            'rename_role': ['rename role', 'change role name', 'update role name', 'update the role name'],
            'reorganize_roles': ['reorganize roles', 'fix role names', 'improve role names', 'clean up roles'],
            
            # Message management
            'bulk_delete': ['delete', 'remove', 'purge', 'clear', 'clean', 'wipe'],
            
            # Channel management
            'create_channel': ['create channel'],
            'delete_channel': ['delete channel'],
        }
        
        # Check each action type
        for action_type, keywords in action_patterns.items():
            for keyword in keywords:
                if keyword in content:
                    # Additional validation for some ambiguous cases
                    if action_type == 'ban_user' and 'unban' in content:
                        continue  # This is actually an unban
                    if action_type == 'bulk_delete' and not any(msg_word in content for msg_word in ['message', 'messages', 'msg', 'msgs']):
                        continue  # Delete without message context might not be bulk delete
                    
                    return action_type
        
        return None
    
    async def _extract_parameters(self, action_type: str, content: str, original_content: str, guild, message_author) -> Optional[Dict[str, Any]]:
        """Phase 2: Extract parameters for the specific action type"""
        
        # Map action types to their parameter extractors
        extractor_map = {
            'kick_user': self.extractors.extract_kick_params,
            'ban_user': self.extractors.extract_ban_params,
            'unban_user': self.extractors.extract_unban_params,
            'timeout_user': self.extractors.extract_timeout_params,
            'remove_timeout': self.extractors.extract_remove_timeout_params,
            'change_nickname': self.extractors.extract_nickname_params,
            'add_role': self.extractors.extract_add_role_params,
            'remove_role': self.extractors.extract_remove_role_params,
            'rename_role': self.extractors.extract_rename_role_params,
            'reorganize_roles': self.extractors.extract_reorganize_roles_params,
            'bulk_delete': self.extractors.extract_bulk_delete_params,
            'create_channel': self.extractors.extract_create_channel_params,
            'delete_channel': self.extractors.extract_delete_channel_params,
        }
        
        extractor = extractor_map.get(action_type)
        if extractor:
            return await extractor(content, original_content, guild, message_author)
        
        return None