"""
Parameter extractors for admin actions
"""
import re
from typing import Optional, Dict, Any


class AdminParameterExtractors:
    """Parameter extraction logic for each admin action type"""
    
    def __init__(self, utils):
        self.utils = utils
    
    async def extract_nickname_params(self, content: str, original_content: str, guild, message_author) -> Optional[Dict[str, Any]]:
        """Extract parameters for nickname change action"""
        
        from ..utils.logging import get_logger
        logger = get_logger(__name__)
        logger.info(f"👤 NICKNAME EXTRACTOR DEBUG: Extracting from '{original_content}'")
        
        # Send simple Discord debug - find any text channel to send to
        try:
            if guild and guild.text_channels:
                channel = guild.text_channels[0]
                await channel.send(f"🔧 **NICKNAME EXTRACTOR CALLED**\nOriginal: `{original_content}`")
        except Exception as e:
            logger.error(f"Debug message failed: {e}")
        
        # Find the user to rename
        user = await self.utils.find_user(original_content, guild, message_author)
        logger.info(f"👤 NICKNAME EXTRACTOR: Found user: {user} from content: {original_content}")
        
        # Debug user finding
        try:
            if guild and guild.text_channels:
                channel = guild.text_channels[0]
                await channel.send(f"👤 **USER LOOKUP**\nFound: `{user}`\nType: `{type(user)}`")
        except:
            pass
        
        if not user:
            try:
                if guild and guild.text_channels:
                    channel = guild.text_channels[0]
                    await channel.send(f"❌ **USER NOT FOUND**\nReturning None")
            except:
                pass
            return None
        
        # Extract the new nickname using multiple patterns
        nickname = None
        
        # Try to find nickname in quotes first (highest priority)
        nick_match = re.search(r'["\']([^"\']+)["\']', original_content)
        if nick_match:
            nickname = nick_match.group(1)
            logger.info(f"👤 NICKNAME EXTRACTOR: Found nickname in quotes: '{nickname}'")
        else:
            # Try various patterns for nickname extraction
            patterns = [
                r'\bto\s+([^\s]+(?:\s+[^\s]+)*?)(?:\s|$)',  # "change nick to NewName"
                r'\bas\s+([^\s]+(?:\s+[^\s]+)*?)(?:\s|$)',  # "set nick as NewName"  
                r'nickname\s+([^\s]+(?:\s+[^\s]+)*?)(?:\s|$)',  # "change John nickname NewName"
                r'nick\s+([^\s]+(?:\s+[^\s]+)*?)(?:\s|$)',      # "change John nick NewName"
                r'name\s+to\s+([^\s]+(?:\s+[^\s]+)*?)(?:\s|$)', # "change name to NewName"
            ]
            
            logger.info(f"👤 NICKNAME EXTRACTOR: Trying patterns on '{original_content}'")
            for i, pattern in enumerate(patterns):
                match = re.search(pattern, original_content, re.IGNORECASE)
                if match:
                    nickname = match.group(1).strip()
                    logger.info(f"👤 NICKNAME EXTRACTOR: Pattern {i} matched: '{nickname}'")
                    break
                else:
                    logger.info(f"👤 NICKNAME EXTRACTOR: Pattern {i} failed: {pattern}")
        
        # Log final result
        valid_result = nickname is not None and user is not None
        logger.info(f"👤 NICKNAME EXTRACTOR FINAL: User={user}, Nickname='{nickname}', Valid={valid_result}")
        
        # Debug final result
        try:
            if guild and guild.text_channels:
                channel = guild.text_channels[0]
                await channel.send(f"📋 **FINAL RESULT**\nUser: `{user}`\nNickname: `{nickname}`\nReturning: `{{'user': {user}, 'nickname': {nickname}}}`")
        except:
            pass
        
        return {"user": user, "nickname": nickname}
    
    async def extract_kick_params(self, content, original_content, guild, message_author):
        """Extract parameters for kick action"""
        user = await self.utils.find_user(content, guild, message_author)
        if user:
            return {"user": user, "reason": "Requested via AI"}
        return None
    
    async def extract_ban_params(self, content, original_content, guild, message_author):
        """Extract parameters for ban action"""
        user = await self.utils.find_user(content, guild, message_author)
        if user:
            delete_days = 1 if any(phrase in content for phrase in ['delete messages', 'clean']) else 0
            return {"user": user, "reason": "Requested via AI", "delete_days": delete_days}
        return None
    
    async def extract_timeout_params(self, content, original_content, guild, message_author):
        """Extract parameters for timeout action"""
        user = await self.utils.find_user(content, guild, message_author)
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
    
    async def extract_remove_timeout_params(self, content, original_content, guild, message_author):
        """Extract parameters for remove timeout action"""
        user = await self.utils.find_user(content, guild, message_author)
        if user:
            return {"user": user}
        return None
    
    async def extract_unban_params(self, content, original_content, guild, message_author):
        """Extract parameters for unban action"""
        user_ids = re.findall(r'\d{15,20}', original_content)
        if user_ids:
            return {"user_id": int(user_ids[0])}
        return None
    
    async def extract_add_role_params(self, content, original_content, guild, message_author):
        """Extract parameters for add role action"""
        user = await self.utils.find_user(content, guild, message_author)
        role = self.utils.find_role(content, guild)
        if user and role:
            return {"user": user, "role": role}
        return None
    
    async def extract_remove_role_params(self, content, original_content, guild, message_author):
        """Extract parameters for remove role action"""
        user = await self.utils.find_user(content, guild, message_author)
        role = self.utils.find_role(content, guild)
        if user and role:
            return {"user": user, "role": role}
        return None
    
    async def extract_rename_role_params(self, content, original_content, guild, message_author):
        """Extract parameters for rename role action"""
        
        # Find the role to rename
        role = self.utils.find_role(content, guild)
        if not role:
            return None
        
        # Extract the new name from various patterns
        new_name = None
        
        # Pattern 1: Look for quoted strings for the new name (most reliable)
        quoted_matches = re.findall(r'["\']([^"\']+)["\']', original_content)
        if len(quoted_matches) >= 2:
            # If there are 2+ quoted strings, the last one is likely the new name
            new_name = quoted_matches[-1].strip()
        elif len(quoted_matches) == 1:
            # Single quoted string might be the new name if role was found by other means
            new_name = quoted_matches[0].strip()
        
        # Pattern 2: Look for "to [new_name]" or "called [new_name]" patterns
        if not new_name:
            to_patterns = [
                r'(?:rename|change|update).*?role.*?to\s+([^\s]+(?:\s+[^\s]+)*?)(?:\s*$|[.!?])',
                r'role.*?to\s+([^\s]+(?:\s+[^\s]+)*?)(?:\s*$|[.!?])',
                r'(?:rename|change|update).*?role.*?called\s+([^\s]+(?:\s+[^\s]+)*?)(?:\s*$|[.!?])',
                r'role.*?called\s+([^\s]+(?:\s+[^\s]+)*?)(?:\s*$|[.!?])'
            ]
            
            for pattern in to_patterns:
                match = re.search(pattern, original_content, re.IGNORECASE)
                if match:
                    new_name = match.group(1).strip()
                    # Remove trailing punctuation
                    new_name = re.sub(r'[.!?]+$', '', new_name).strip()
                    break
        
        if not new_name:
            return None
            
        return {"role": role, "new_name": new_name}
    
    async def extract_reorganize_roles_params(self, content, original_content, guild, message_author):
        """Extract parameters for reorganize roles action"""
        
        # Extract custom context/description from user input
        context_description = self._extract_role_context_description(content, original_content)
        
        return {
            "context": context_description, 
            "guild": guild
        }
    
    def _extract_role_context_description(self, content: str, original_content: str) -> str:
        """Extract custom context description for role reorganization"""
        
        # Look for patterns that indicate custom context descriptions
        context_patterns = [
            r'(?:organize|fix|update|rename).*?roles.*?(?:based\s+on|according\s+to|using|with)\s+(.+?)(?:\.|$)',
            r'(?:make|organize).*?roles.*?like\s+(.+?)(?:\.|$)',
            r'roles.*?for\s+(.+?)(?:\.|$)',
            r'context(?:\s+is)?[:\s]+(.+?)(?:\.|$)',
            r'(?:reorganize|fix|improve|clean\s+up).*?roles[,\s]+(.+?)(?:\.|$)',
            r'based\s+on\s+(?:what\s+)?(?:i\s+)?(?:found|searched|learned)[:\s]+(.+?)(?:\.|$)',
            r'according\s+to\s+(.+?)(?:\.|$)',
            r'(?:using|with)\s+(?:the\s+)?(?:following\s+)?(?:info|information|context|description)[:\s]+(.+?)(?:\.|$)',
        ]
        
        # Try to extract custom context description
        for pattern in context_patterns:
            match = re.search(pattern, original_content, re.IGNORECASE | re.DOTALL)
            if match:
                description = match.group(1).strip()
                # Clean up the description
                description = re.sub(r'\s+', ' ', description)  # Normalize whitespace
                description = description.rstrip('.,!?')  # Remove trailing punctuation
                
                # Filter out very short or generic descriptions
                if len(description) > 10 and not self._is_generic_description(description):
                    return description
        
        # If no custom context found, look for quoted strings that might be context
        quoted_descriptions = re.findall(r'["\']([^"\']{15,})["\']', original_content)
        for desc in quoted_descriptions:
            if not self._is_generic_description(desc):
                return desc
        
        # Fallback: return generic context
        return "general community server"
    
    def _is_generic_description(self, description: str) -> bool:
        """Check if a description is too generic to be useful"""
        generic_phrases = [
            'make sense', 'better', 'good', 'appropriate', 'nice', 'proper', 'correct',
            'organized', 'clean', 'professional', 'clear', 'simple', 'basic'
        ]
        description_lower = description.lower()
        
        # Too short
        if len(description) < 10:
            return True
        
        # Only contains generic phrases
        if any(phrase in description_lower for phrase in generic_phrases) and len(description) < 30:
            return True
        
        return False
    
    async def extract_bulk_delete_params(self, content, original_content, guild, message_author):
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
        
        # Check if targeting a specific user
        user_filter = None
        
        # Check for bot-targeting pronouns (whole words only)
        if re.search(r'\b(your|you|bot)\b', content, re.IGNORECASE):
            user_filter = guild.get_member(self.utils.bot.user.id)
        
        # Check for self-targeting pronouns (user's own messages, whole words only)
        elif re.search(r'\b(my|me|i|mine)\b', content, re.IGNORECASE):
            if message_author:
                user_filter = message_author
        
        # Check for specific user mentions (only if there's a mention symbol)
        elif '<@' in content:
            user_filter = await self.utils.find_user(content, guild, message_author)
        
        if user_filter:
            parameters["user_filter"] = user_filter
        
        return parameters
    
    async def extract_create_channel_params(self, content, original_content, guild, message_author):
        """Extract parameters for create channel action"""
        
        # Determine channel type
        channel_type = "voice" if "voice" in content else "text"
        
        # Extract channel name from various patterns
        name = None
        
        # Pattern 1: Quoted channel name (most reliable)
        quoted_match = re.search(r'["\']([^"\']+)["\']', original_content)
        if quoted_match:
            name = quoted_match.group(1).strip()
        
        # Pattern 2: "channel called [name]" or "channel named [name]"
        if not name:
            called_match = re.search(r'channel.*?(?:called|named)\s+([^\s]+(?:\s+[^\s]+)*?)(?:\s*$|[.!?])', original_content, re.IGNORECASE)
            if called_match:
                name = called_match.group(1).strip()
                name = re.sub(r'[.!?]+$', '', name).strip()
        
        # Pattern 3: Extract from "create [type] channel [name]"
        if not name:
            create_match = re.search(r'create.*?channel\s+([^\s]+(?:\s+[^\s]+)*?)(?:\s*$|[.!?])', original_content, re.IGNORECASE)
            if create_match:
                name = create_match.group(1).strip()
                name = re.sub(r'[.!?]+$', '', name).strip()
        
        if not name:
            return None
            
        # Clean up channel name (Discord requirements)
        name = name.lower().replace(' ', '-').replace('_', '-')
        # Remove invalid characters
        name = re.sub(r'[^a-z0-9-]', '', name)
        # Ensure not empty after cleaning
        if not name:
            return None
            
        return {"name": name, "type": channel_type}
    
    async def extract_delete_channel_params(self, content, original_content, guild, message_author):
        """Extract parameters for delete channel action"""
        
        # Find the channel to delete
        channel = self.utils.find_channel(content, guild)
        if not channel:
            return None
            
        return {"channel": channel}