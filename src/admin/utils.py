"""
Admin utility functions for finding users, roles, and channels
"""
import re
from typing import Optional


class AdminUtils:
    """Utility functions for admin operations"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def find_user(self, text: str, guild, message_author=None) -> Optional:
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
        
        # Fallback: Self-reference (if author is targeting themselves, whole words only)
        if message_author and re.search(r'\b(my|me|i)\b', text, re.IGNORECASE):
            return message_author
        
        return None
    
    def find_role(self, text: str, guild):
        """Find role by name with improved matching"""
        
        # Remove common words that aren't role names
        exclude_words = {'role', 'add', 'remove', 'give', 'take', 'to', 'from', 'the', 'a', 'an', 'and', 'or', 'with', 'for', 'rename', 'change', 'update', 'called'}
        text_lower = text.lower()
        
        # Look for quoted role names first (most specific)
        quoted_match = re.search(r'["\']([^"\']+)["\']', text)
        if quoted_match:
            role_name = quoted_match.group(1).strip()
            for role in guild.roles:
                if role.name.lower() == role_name.lower():
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
                    return role
        
        return None
    
    def find_channel(self, text: str, guild):
        """Find channel by name or mention"""
        
        # First check for channel mentions like <#123456789>
        channel_mentions = re.findall(r'<#(\d+)>', text)
        if channel_mentions:
            channel_id = int(channel_mentions[0])
            channel = guild.get_channel(channel_id)
            if channel:
                return channel
        
        # Then check for #channel-name references
        hash_matches = re.findall(r'#([a-zA-Z0-9_-]+)', text)
        if hash_matches:
            for channel_name in hash_matches:
                for channel in guild.channels:
                    if channel.name.lower() == channel_name.lower():
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
                        return channel
        
        return None