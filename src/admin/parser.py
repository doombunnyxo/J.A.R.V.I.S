import re
from typing import Optional, Tuple, Dict, Any

class AdminIntentParser:
    """Parses user messages to detect admin intentions and extract parameters"""
    
    def __init__(self, bot, debug_channel=None):
        self.bot = bot
        self.debug_channel = debug_channel
    
    async def parse_admin_intent(self, message_content: str, guild, message_author=None) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Parse user message to detect admin intentions and extract parameters"""
        content = message_content.lower()
        
        debug_msg = f"DEBUG: Parsing admin intent for: '{message_content}'"
        print(debug_msg)
        if self.debug_channel:
            await self.debug_channel.send(debug_msg)
        
        # Phase 1: Quickly identify action type
        action_type = self._identify_action_type(content)
        debug_msg = f"DEBUG: Identified action type: {action_type}"
        print(debug_msg)
        if self.debug_channel:
            await self.debug_channel.send(debug_msg)
        
        if not action_type:
            return None, None
        
        # Phase 2: Extract parameters for the specific action type
        try:
            parameters = await self._extract_parameters(action_type, content, message_content, guild, message_author)
            debug_msg = f"DEBUG: Extracted parameters: {parameters}"
            print(debug_msg)
            if self.debug_channel:
                await self.debug_channel.send(debug_msg)
            
            if parameters is not None:
                return action_type, parameters
            else:
                debug_msg = f"DEBUG: Failed to extract parameters for {action_type}"
                print(debug_msg)
                if self.debug_channel:
                    await self.debug_channel.send(debug_msg)
                return None, None
                
        except Exception as e:
            debug_msg = f"DEBUG: Error extracting parameters for {action_type}: {e}"
            print(debug_msg)
            if self.debug_channel:
                await self.debug_channel.send(debug_msg)
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
            'change_nickname': ['nickname', 'rename user', 'rename member', 'change name of'],
            
            # Role management
            'add_role': ['add role', 'give role'],
            'remove_role': ['remove role', 'take role'],
            'rename_role': ['rename role', 'change role name', 'update role name'],
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
        
        parameter_extractors = {
            'kick_user': self._extract_kick_params,
            'ban_user': self._extract_ban_params,
            'unban_user': self._extract_unban_params,
            'timeout_user': self._extract_timeout_params,
            'remove_timeout': self._extract_remove_timeout_params,
            'change_nickname': self._extract_nickname_params,
            'add_role': self._extract_add_role_params,
            'remove_role': self._extract_remove_role_params,
            'rename_role': self._extract_rename_role_params,
            'reorganize_roles': self._extract_reorganize_roles_params,
            'bulk_delete': self._extract_bulk_delete_params,
            'create_channel': self._extract_create_channel_params,
            'delete_channel': self._extract_delete_channel_params,
        }
        
        extractor = parameter_extractors.get(action_type)
        if extractor:
            return await extractor(content, original_content, guild, message_author)
        
        return None
    
    async def _extract_nickname_params(self, content: str, original_content: str, guild, message_author) -> Optional[Dict[str, Any]]:
        """Extract parameters for nickname change action"""
        
        # Find the user to rename
        user = await self._find_user(original_content, guild, message_author)
        if not user:
            return None
        
        # Extract the new nickname
        nickname = None
        
        # Try to find nickname in quotes first
        import re
        nick_match = re.search(r'["\']([^"\']+)["\']', original_content)
        if nick_match:
            nickname = nick_match.group(1)
            debug_msg = f"DEBUG: Found nickname in quotes: '{nickname}'"
        else:
            # Try to extract nickname after "to" keyword
            to_match = re.search(r'\bto\s+(\w+)', content, re.IGNORECASE)
            if to_match:
                nickname = to_match.group(1)
                debug_msg = f"DEBUG: Found nickname after 'to': '{nickname}'"
            else:
                debug_msg = f"DEBUG: No nickname found in content: '{content}' or original: '{original_content}'"
        
        print(debug_msg)
        if self.debug_channel:
            await self.debug_channel.send(debug_msg)
        
        result = {"user": user, "nickname": nickname}
        debug_msg = f"DEBUG: Nickname extraction result: {result}"
        print(debug_msg)
        if self.debug_channel:
            await self.debug_channel.send(debug_msg)
        
        return result
    
    # TODO: Add other parameter extractors for different action types
    async def _extract_kick_params(self, content, original_content, guild, message_author):
        """Extract parameters for kick action"""
        user = await self._find_user(content, guild, message_author)
        if user:
            return {"user": user, "reason": "Requested via AI"}
        return None
    
    async def _extract_ban_params(self, content, original_content, guild, message_author):
        """Extract parameters for ban action"""
        user = await self._find_user(content, guild, message_author)
        if user:
            delete_days = 1 if any(phrase in content for phrase in ['delete messages', 'clean']) else 0
            return {"user": user, "reason": "Requested via AI", "delete_days": delete_days}
        return None
    
    async def _extract_timeout_params(self, content, original_content, guild, message_author):
        """Extract parameters for timeout action"""
        user = await self._find_user(content, guild, message_author)
        if user:
            duration = 60  # default
            duration_match = re.search(r'(\d+)\s*(min|hour|day)', content)
            if duration_match:
                num, unit = duration_match.groups()
                if unit.startswith('hour'):
                    duration = int(num) * 60
                elif unit.startswith('day'):
                    duration = int(num) * 60 * 24
                else:
                    duration = int(num)
            return {"user": user, "duration": duration, "reason": "Requested via AI"}
        return None
    
    async def _extract_remove_timeout_params(self, content, original_content, guild, message_author):
        """Extract parameters for remove timeout action"""
        user = await self._find_user(content, guild, message_author)
        if user:
            return {"user": user}
        return None
    
    async def _extract_unban_params(self, content, original_content, guild, message_author):
        """Extract parameters for unban action"""
        user_ids = re.findall(r'\d{15,20}', original_content)
        if user_ids:
            return {"user_id": int(user_ids[0])}
        return None
    
    async def _extract_add_role_params(self, content, original_content, guild, message_author):
        """Extract parameters for add role action"""
        user = await self._find_user(content, guild, message_author)
        role = self._find_role(content, guild)
        if user and role:
            return {"user": user, "role": role}
        return None
    
    async def _extract_remove_role_params(self, content, original_content, guild, message_author):
        """Extract parameters for remove role action"""
        user = await self._find_user(content, guild, message_author)
        role = self._find_role(content, guild)
        if user and role:
            return {"user": user, "role": role}
        return None
    
    async def _extract_rename_role_params(self, content, original_content, guild, message_author):
        """Extract parameters for rename role action"""
        # TODO: Implement role renaming parameter extraction
        return None
    
    async def _extract_reorganize_roles_params(self, content, original_content, guild, message_author):
        """Extract parameters for reorganize roles action"""
        # TODO: Implement role reorganization parameter extraction
        return None
    
    async def _extract_bulk_delete_params(self, content, original_content, guild, message_author):
        """Extract parameters for bulk delete action"""
        parameters = {}
        
        # Extract number of messages (look for reasonable counts 1-1000)
        numbers = re.findall(r'\b(\d+)\b', content)
        limit = 1  # default
        for num_str in numbers:
            num = int(num_str)
            if 1 <= num <= 1000:  # Reasonable message count
                limit = num
                break
        parameters["limit"] = limit
        
        # Check if targeting a specific user (bot messages)
        if any(word in content for word in ['your', 'you', 'bot']):
            # Target the bot itself
            bot_member = guild.get_member(self.bot.user.id)
            if bot_member:
                parameters["user_filter"] = bot_member
        
        return parameters
    
    async def _extract_create_channel_params(self, content, original_content, guild, message_author):
        """Extract parameters for create channel action"""
        # TODO: Implement create channel parameter extraction
        return None
    
    async def _extract_delete_channel_params(self, content, original_content, guild, message_author):
        """Extract parameters for delete channel action"""
        # TODO: Implement delete channel parameter extraction
        return None
    
    async def _find_user(self, text: str, guild, message_author=None) -> Optional:
        """Fast user lookup - optimized for Discord mentions"""
        
        # Fast path: Discord mentions (<@123456789>) - most common case
        if '<@' in text:
            user_ids = re.findall(r'<@!?(\d+)>', text)
            if user_ids:
                bot_id = str(self.bot.user.id)
                # Get the last non-bot user mentioned (most likely the target)
                for user_id in reversed(user_ids):
                    if user_id != bot_id:
                        return guild.get_member(int(user_id))
        
        # Fallback: Self-reference (if author is targeting themselves)
        if message_author and any(word in text.lower() for word in ['my', 'me', 'i']):
            return message_author
        
        return None
    
    def _find_role(self, text: str, guild):
        """Find role by name with improved matching"""
        print(f"DEBUG: Looking for role in text: '{text}'")
        
        # Remove common words that aren't role names
        exclude_words = {'role', 'add', 'remove', 'give', 'take', 'to', 'from', 'the', 'a', 'an', 'and', 'or', 'with', 'for', 'rename', 'change', 'update', 'called'}
        text_lower = text.lower()
        
        # Look for quoted role names first (most specific)
        quoted_match = re.search(r'["\']([^"\']+)["\']', text)
        if quoted_match:
            role_name = quoted_match.group(1).strip()
            for role in guild.roles:
                if role.name.lower() == role_name.lower():
                    print(f"DEBUG: Found role by exact quoted match: {role}")
                    return role
        
        # Try exact role name matches
        for role in guild.roles:
            role_name_lower = role.name.lower()
            if role_name_lower in text_lower:
                # Make sure it's not a partial match within another word
                role_start = text_lower.find(role_name_lower)
                role_end = role_start + len(role_name_lower)
                
                # Check if the role name is surrounded by word boundaries or common separators
                is_word_boundary = True
                if role_start > 0:
                    prev_char = text_lower[role_start - 1]
                    if prev_char.isalnum():
                        is_word_boundary = False
                
                if role_end < len(text_lower):
                    next_char = text_lower[role_end]
                    if next_char.isalnum():
                        is_word_boundary = False
                
                if is_word_boundary:
                    print(f"DEBUG: Found role by exact name match: {role}")
                    return role
        
        # If no exact matches, try partial matches with better filtering
        words = [word.strip().lower() for word in text.split() if word.strip().lower() not in exclude_words and len(word.strip()) > 2]
        
        for role in guild.roles:
            role_name_lower = role.name.lower()
            
            # Skip system roles
            if role.name in ['@everyone'] or role.managed:
                continue
            
            # Check if any significant word matches the role name
            for word in words:
                if word == role_name_lower or (len(word) > 3 and word in role_name_lower):
                    print(f"DEBUG: Found role by partial match: {role}")
                    return role
        
        print(f"DEBUG: No role found in: {text}")
        return None
    
    def _find_channel(self, text: str, guild):
        """Find channel by name or mention"""
        print(f"DEBUG: Looking for channel in text: '{text}'")
        
        # First check for channel mentions like <#123456789>
        channel_mentions = re.findall(r'<#(\d+)>', text)
        if channel_mentions:
            channel_id = int(channel_mentions[0])
            channel = guild.get_channel(channel_id)
            if channel:
                print(f"DEBUG: Found channel by mention: #{channel.name}")
                return channel
        
        # Then check for #channel-name references
        hash_matches = re.findall(r'#([a-zA-Z0-9_-]+)', text)
        if hash_matches:
            for channel_name in hash_matches:
                for channel in guild.channels:
                    if channel.name.lower() == channel_name.lower():
                        print(f"DEBUG: Found channel by hash reference: #{channel.name}")
                        return channel
        
        # Finally check for exact channel name matches (only after "in" or "from")
        context_patterns = [
            r'(?:in|from)\s+(?:channel\s+)?([a-zA-Z0-9_-]+)',
            r'(?:in|from)\s+#([a-zA-Z0-9_-]+)'
        ]
        
        for pattern in context_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                for channel in guild.channels:
                    if channel.name.lower() == match.lower():
                        print(f"DEBUG: Found channel by context pattern: #{channel.name}")
                        return channel
        
        print(f"DEBUG: No channel found in: {text}")
        return None