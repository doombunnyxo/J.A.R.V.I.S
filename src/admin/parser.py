import re
from typing import Optional, Tuple, Dict, Any

class AdminIntentParser:
    """Parses user messages to detect admin intentions and extract parameters"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def parse_admin_intent(self, message_content: str, guild, message_author=None) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Parse user message to detect admin intentions and extract parameters"""
        content = message_content.lower()
        print(f"DEBUG: Parsing admin intent for: '{message_content}'")
        
        # Try each action type parser (order matters - more specific parsers first)
        parsers = [
            self._parse_kick_action,
            self._parse_ban_action,
            self._parse_unban_action,
            self._parse_timeout_action,
            self._parse_remove_timeout_action,
            self._parse_role_actions,  # Role actions before nickname to prevent conflicts
            self._parse_bulk_delete_action,
            self._parse_channel_actions,
            self._parse_nickname_action,  # Nickname last to avoid catching role "rename" commands
        ]
        
        for parser in parsers:
            result = await parser(content, message_content, guild, message_author)
            if result[0]:  # If action_type is not None
                return result
        
        print(f"DEBUG: No admin action detected")
        return None, None
    
    async def _find_user(self, text: str, guild, message_author=None) -> Optional:
        """Helper function to find user mentions or names"""
        print(f"DEBUG: Looking for user in text: '{text}'")
        
        # Check for first-person pronouns referring to the message author
        if message_author and any(pronoun in text.lower() for pronoun in ['i', 'my', 'me', 'myself', 'mine']):
            # Make sure it's in a context that suggests the user is the target
            user_action_contexts = ['my messages', 'my msg', 'i sent', 'i posted', 'i wrote', 'delete my', 'remove my', 'clear my']
            if any(context in text.lower() for context in user_action_contexts) or any(word in text.lower() for word in ['my', 'mine']):
                author_member = guild.get_member(message_author.id)
                if author_member:
                    print(f"DEBUG: Found message author by first-person pronoun: {author_member}")
                    return author_member
        
        # Check for pronouns referring to the bot
        if any(pronoun in text.lower() for pronoun in ['you', 'your', 'yours', 'yourself']):
            bot_member = guild.get_member(self.bot.user.id)
            if bot_member:
                print(f"DEBUG: Found bot by pronoun: {bot_member} (ID: {bot_member.id})")
                return bot_member
        
        # Check for mentions first
        if '<@' in text:
            user_ids = re.findall(r'<@!?(\d+)>', text)
            print(f"DEBUG: Found user IDs in message: {user_ids}")
            if user_ids:
                bot_id = str(self.bot.user.id)
                
                # Find the target user - prioritize non-bot users, but allow bot if it's the only/specific target
                target_user_id = None
                
                # First, try to find non-bot users
                non_bot_user_ids = [uid for uid in user_ids if uid != bot_id]
                if non_bot_user_ids:
                    # Use the last mentioned non-bot user (most likely the target)
                    target_user_id = int(non_bot_user_ids[-1])
                else:
                    # If only bot is mentioned, check if the context suggests targeting the bot
                    # Look for keywords that suggest bot actions (delete bot messages, etc.)
                    bot_action_keywords = ['delete', 'remove', 'purge', 'clear', 'clean', 'ban', 'kick', 'timeout']
                    if any(keyword in text.lower() for keyword in bot_action_keywords):
                        target_user_id = int(bot_id)
                        print(f"DEBUG: Bot targeted for admin action based on context (bot ID: {bot_id})")
                
                if target_user_id:
                    user = guild.get_member(target_user_id)
                    if user:
                        print(f"DEBUG: Found member by mention: {user}")
                        return user
                    else:
                        print(f"DEBUG: User {target_user_id} not found as member in guild {guild.name}")
                        # For admin actions, we need Member objects, not User objects
                        # Don't fall back to fetch_user as it returns User objects that can't be edited
                        return None
        
        # Check for username/display name matching
        words = text.split()
        for member in guild.members:
            member_name_lower = member.name.lower()
            member_display_lower = member.display_name.lower()
            
            for word in words:
                # Strip possessive forms and other punctuation
                clean_word = word.lower().rstrip("'s").rstrip("'").rstrip(",").rstrip(".")
                
                if (clean_word == member_name_lower or 
                    clean_word == member_display_lower or
                    clean_word in member_name_lower or 
                    clean_word in member_display_lower):
                    print(f"DEBUG: Found user by name match: {member}")
                    return member
        
        print(f"DEBUG: No user found in: {text}")
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
    
    async def _parse_kick_action(self, content: str, original_content: str, guild, message_author=None) -> Tuple[Optional[str], Optional[Dict]]:
        """Parse kick action"""
        kick_keywords = ['kick', 'boot', 'eject']
        if any(word in content for word in kick_keywords) and not any(word in content for word in ['ban', 'timeout', 'role']):
            user = await self._find_user(content, guild, message_author)
            if user:
                print(f"DEBUG: Detected kick action for user: {user}")
                return "kick_user", {"user": user, "reason": "Requested via AI"}
        return None, None
    
    async def _parse_ban_action(self, content: str, original_content: str, guild, message_author=None) -> Tuple[Optional[str], Optional[Dict]]:
        """Parse ban action"""
        if 'ban' in content and 'unban' not in content:
            user = await self._find_user(content, guild, message_author)
            if user:
                delete_days = 1 if 'delete messages' in content or 'clean' in content else 0
                print(f"DEBUG: Detected ban action for user: {user}")
                return "ban_user", {"user": user, "reason": "Requested via AI", "delete_days": delete_days}
        return None, None
    
    async def _parse_unban_action(self, content: str, original_content: str, guild, message_author=None) -> Tuple[Optional[str], Optional[Dict]]:
        """Parse unban action"""
        if 'unban' in content:
            user_ids = re.findall(r'\d{15,20}', original_content)
            if user_ids:
                return "unban_user", {"user_id": int(user_ids[0])}
        return None, None
    
    async def _parse_timeout_action(self, content: str, original_content: str, guild, message_author=None) -> Tuple[Optional[str], Optional[Dict]]:
        """Parse timeout action"""
        timeout_keywords = ['timeout', 'mute', 'silence', 'quiet', 'shush']
        if any(word in content for word in timeout_keywords):
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
                print(f"DEBUG: Detected timeout action for user: {user}, duration: {duration}")
                return "timeout_user", {"user": user, "duration": duration, "reason": "Requested via AI"}
        return None, None
    
    async def _parse_remove_timeout_action(self, content: str, original_content: str, guild, message_author=None) -> Tuple[Optional[str], Optional[Dict]]:
        """Parse remove timeout action"""
        if any(phrase in content for phrase in ['remove timeout', 'unmute', 'unsilence']):
            user = await self._find_user(content, guild, message_author)
            if user:
                return "remove_timeout", {"user": user}
        return None, None
    
    async def _parse_role_actions(self, content: str, original_content: str, guild, message_author=None) -> Tuple[Optional[str], Optional[Dict]]:
        """Parse role management actions"""
        if 'add role' in content or 'give role' in content:
            user = await self._find_user(content, guild, message_author)
            role = self._find_role(content, guild)
            if user and role:
                return "add_role", {"user": user, "role": role}
        
        if 'remove role' in content or 'take role' in content:
            user = await self._find_user(content, guild, message_author)
            role = self._find_role(content, guild)
            if user and role:
                return "remove_role", {"user": user, "role": role}
        
        # Parse role renaming
        rename_keywords = ['rename role', 'change role name', 'update role name', 'rename the role']
        if any(keyword in content for keyword in rename_keywords):
            role = self._find_role(content, guild)
            new_name = self._extract_new_role_name(content, original_content)
            if role and new_name:
                return "rename_role", {"role": role, "new_name": new_name}
        
        # Parse intelligent role reorganization
        reorganize_keywords = [
            'reorganize roles', 'fix role names', 'improve role names', 
            'make roles make sense', 'better role names', 'clean up roles',
            'rename roles to make sense', 'update all role names',
            'organize the roles better', 'fix our role structure',
            'update roles based on', 'organize roles like', 'make roles fit'
        ]
        if any(keyword in content for keyword in reorganize_keywords):
            # Extract custom context/description from user input
            context_description = self._extract_role_context_description(content, original_content)
            parameters = {"context": context_description, "guild": guild}
            
            # Check if this might be a multi-step action that will provide research context
            # The AI handler will determine if research is needed and add research_context later
            return "reorganize_roles", parameters
        
        return None, None
    
    async def _parse_bulk_delete_action(self, content: str, original_content: str, guild, message_author=None) -> Tuple[Optional[str], Optional[Dict]]:
        """Parse bulk delete action"""
        delete_keywords = ['delete', 'remove', 'purge', 'clear', 'clean', 'wipe']
        message_keywords = ['message', 'messages', 'msg', 'msgs']
        
        has_delete = any(word in content for word in delete_keywords)
        has_message = any(word in content for word in message_keywords)
        
        if has_delete and has_message:
            parameters = {}
            
            # Check if the command specifically targets a user
            user_targeting_phrases = [
                # Direct user keywords
                'from', 'by', 'sent by', 'posted by', 'written by',
                # Bot-targeting phrases
                'your messages', 'your msg', 'you sent', 'delete you', 'purge you',
                # Pronoun indicators that suggest user targeting
                'my messages', 'my msg', 'i sent'
            ]
            
            # Check for user mentions (excluding the initial bot mention for the command)
            user_mentions = re.findall(r'<@!?(\d+)>', content)
            bot_mention_count = user_mentions.count(str(self.bot.user.id))
            has_other_user_mentions = len(user_mentions) > bot_mention_count
            has_multiple_bot_mentions = bot_mention_count > 1  # Bot mentioned more than once
            
            print(f"DEBUG: Bulk delete mention analysis:")
            print(f"DEBUG: - All mentions: {user_mentions}")
            print(f"DEBUG: - Bot ID: {self.bot.user.id}")
            print(f"DEBUG: - Bot mentioned {bot_mention_count} times")
            print(f"DEBUG: - Has other user mentions: {has_other_user_mentions}")
            print(f"DEBUG: - Has multiple bot mentions: {has_multiple_bot_mentions}")
            
            has_targeting_phrase = any(phrase in content for phrase in user_targeting_phrases)
            has_pronouns = any(pronoun in content.split() for pronoun in ['you', 'your', 'yours', 'my', 'mine', 'i'])
            
            # Only apply user filtering if there's clear indication of targeting a specific user:
            # - Multiple bot mentions (command trigger + target)
            # - Other user mentions
            # - Targeting phrases or pronouns
            if has_multiple_bot_mentions or has_other_user_mentions or has_targeting_phrase or has_pronouns:
                user_filter = await self._find_user(content, guild, message_author)
                if user_filter:
                    print(f"DEBUG: Set user_filter to {user_filter.name} (ID: {user_filter.id}) for bulk delete")
                    parameters["user_filter"] = user_filter
                else:
                    print(f"DEBUG: User targeting detected but no user found - will delete all messages")
            else:
                print(f"DEBUG: No user targeting detected - will delete all messages")
            
            # Look for specific channel ONLY if explicitly mentioned with context indicators
            channel_indicators = ['in #', 'in channel', 'from #', 'from channel']
            has_channel_indicator = any(indicator in content for indicator in channel_indicators)
            has_channel_mention = '#' in content
            
            if has_channel_indicator or has_channel_mention:
                channel = self._find_channel(content, guild)
                if channel:
                    print(f"DEBUG: Set channel to {channel.name} for bulk delete")
                    parameters["channel"] = channel
                else:
                    print(f"DEBUG: Channel indicator found but no channel matched")
            else:
                print(f"DEBUG: No channel specified - using current channel")
            
            # Extract number of messages (avoid user IDs which are typically 15+ digits)
            # Look for reasonable message counts (1-1000) and avoid user IDs
            number_matches = re.findall(r'\b(\d+)\b', content)
            limit = 1  # default
            
            for match in number_matches:
                num = int(match)
                # Filter out user IDs (typically 15-20 digits) and keep reasonable message counts
                if 1 <= num <= 1000:
                    limit = num
                    break  # Use the first reasonable number found
            
            print(f"DEBUG: Found numbers in content: {number_matches}, selected limit: {limit}")
            parameters["limit"] = limit
            
            print(f"DEBUG: Detected bulk_delete action - limit: {limit}, parameters: {parameters}")
            return "bulk_delete", parameters
        
        return None, None
    
    async def _parse_channel_actions(self, content: str, original_content: str, guild, message_author=None) -> Tuple[Optional[str], Optional[Dict]]:
        """Parse channel management actions"""
        if 'create channel' in content:
            name_match = re.search(r'create.*channel.*["\']([^"\']+)["\']', content)
            if not name_match:
                name_match = re.search(r'channel.*called.*(\w+)', content)
            if name_match:
                name = name_match.group(1)
                channel_type = "voice" if "voice" in content else "text"
                return "create_channel", {"name": name, "type": channel_type}
        
        if 'delete channel' in content:
            channel = self._find_channel(content, guild)
            if channel:
                return "delete_channel", {"channel": channel}
        
        return None, None
    
    async def _parse_nickname_action(self, content: str, original_content: str, guild, message_author=None) -> Tuple[Optional[str], Optional[Dict]]:
        """Parse nickname change action"""
        # Exclude role-related commands to prevent conflicts
        if any(role_word in content for role_word in ['role', 'roles']):
            return None, None
            
        # Be more specific to avoid conflicts with role renaming
        nickname_patterns = [
            'change nickname', 'set nickname', 'nickname to',
            'rename user', 'rename member', 'change name of',
            'set user\'s nickname', 'set users nickname', 'user\'s nickname to'
        ]
        if any(phrase in content for phrase in nickname_patterns):
            user = await self._find_user(content, guild, message_author)
            if user:
                # Try to find nickname in quotes first
                nick_match = re.search(r'["\']([^"\']+)["\']', content)
                if nick_match:
                    nickname = nick_match.group(1)
                else:
                    # Try to extract nickname after "to" keyword
                    to_match = re.search(r'\bto\s+(\w+)', content, re.IGNORECASE)
                    nickname = to_match.group(1) if to_match else None
                
                return "change_nickname", {"user": user, "nickname": nickname}
        
        return None, None
    
    def _extract_new_role_name(self, content: str, original_content: str) -> Optional[str]:
        """Extract new role name from rename role command, preserving original capitalization"""
        print(f"DEBUG: Extracting new role name from: '{original_content}'")
        
        # Look for quoted strings for the new name (most reliable) - preserves exact capitalization
        quoted_matches = re.findall(r'["\']([^"\']+)["\']', original_content)
        if quoted_matches:
            # If multiple quoted strings, take the last one (likely the new name)
            new_name = quoted_matches[-1].strip()
            print(f"DEBUG: Found quoted new role name: '{new_name}'")
            return new_name
        
        # Look for patterns like "rename role X to Y" or "change role X to Y"
        # Use original_content (not lowercased content) to preserve capitalization
        to_patterns = [
            r'rename.*?role.*?to\s+([^\s]+(?:\s+[^\s]+)*?)(?:\s*$|[.!?])',
            r'change.*?role.*?to\s+([^\s]+(?:\s+[^\s]+)*?)(?:\s*$|[.!?])',
            r'update.*?role.*?to\s+([^\s]+(?:\s+[^\s]+)*?)(?:\s*$|[.!?])',
            r'role.*?to\s+([^\s]+(?:\s+[^\s]+)*?)(?:\s*$|[.!?])'
        ]
        
        for pattern in to_patterns:
            match = re.search(pattern, original_content, re.IGNORECASE)
            if match:
                new_name = match.group(1).strip()
                # Remove trailing punctuation if present
                new_name = re.sub(r'[.!?]+$', '', new_name).strip()
                print(f"DEBUG: Found new role name via 'to' pattern: '{new_name}'")
                return new_name
        
        # Look for "called" pattern like "rename role X called Y"
        called_patterns = [
            r'rename.*?role.*?called\s+([^\s]+(?:\s+[^\s]+)*?)(?:\s*$|[.!?])',
            r'role.*?called\s+([^\s]+(?:\s+[^\s]+)*?)(?:\s*$|[.!?])'
        ]
        
        for pattern in called_patterns:
            match = re.search(pattern, original_content, re.IGNORECASE)
            if match:
                new_name = match.group(1).strip()
                # Remove trailing punctuation if present
                new_name = re.sub(r'[.!?]+$', '', new_name).strip()
                print(f"DEBUG: Found new role name via 'called' pattern: '{new_name}'")
                return new_name
        
        print(f"DEBUG: No new role name found in: '{original_content}'")
        return None
    
    def _extract_role_context_description(self, content: str, original_content: str) -> str:
        """Extract custom context description for role reorganization"""
        print(f"DEBUG: Extracting role context description from: '{original_content}'")
        
        # Look for patterns that indicate custom context descriptions
        context_description_patterns = [
            # "organize roles based on [description]"
            r'(?:organize|fix|update|rename).*?roles.*?(?:based\s+on|according\s+to|using|with)\s+(.+?)(?:\.|$)',
            # "make roles like [description]" 
            r'(?:make|organize).*?roles.*?like\s+(.+?)(?:\.|$)',
            # "roles for [description]"
            r'roles.*?for\s+(.+?)(?:\.|$)',
            # "context: [description]" or "context is [description]"
            r'context(?:\s+is)?[:\s]+(.+?)(?:\.|$)',
            # Direct descriptions after reorganize keywords
            r'(?:reorganize|fix|improve|clean\s+up).*?roles[,\s]+(.+?)(?:\.|$)',
            # "based on what I found: [description]"
            r'based\s+on\s+(?:what\s+)?(?:i\s+)?(?:found|searched|learned)[:\s]+(.+?)(?:\.|$)',
            # "according to [description]"
            r'according\s+to\s+(.+?)(?:\.|$)',
            # After "using" or "with" keywords
            r'(?:using|with)\s+(?:the\s+)?(?:following\s+)?(?:info|information|context|description)[:\s]+(.+?)(?:\.|$)',
        ]
        
        # Try to extract custom context description
        for pattern in context_description_patterns:
            match = re.search(pattern, original_content, re.IGNORECASE | re.DOTALL)
            if match:
                description = match.group(1).strip()
                # Clean up the description
                description = re.sub(r'\s+', ' ', description)  # Normalize whitespace
                description = description.rstrip('.,!?')  # Remove trailing punctuation
                
                # Filter out very short or generic descriptions
                if len(description) > 10 and not self._is_generic_description(description):
                    print(f"DEBUG: Found custom context description: '{description}'")
                    return description
        
        # If no custom context found, look for quoted strings that might be context
        quoted_descriptions = re.findall(r'["\']([^"\']{15,})["\']', original_content)
        for desc in quoted_descriptions:
            if not self._is_generic_description(desc):
                print(f"DEBUG: Found quoted context description: '{desc}'")
                return desc
        
        # Look for longer descriptive phrases that follow reorganize keywords
        reorganize_pattern = r'(?:reorganize|fix|improve|clean\s+up|update|organize).*?roles(?:\s+to)?\s+(.{20,}?)(?:\.|$|\?|!)'
        match = re.search(reorganize_pattern, original_content, re.IGNORECASE | re.DOTALL)
        if match:
            description = match.group(1).strip()
            description = re.sub(r'\s+', ' ', description)
            if not self._is_generic_description(description):
                print(f"DEBUG: Found descriptive context: '{description}'")
                return description
        
        # Fallback: return the entire message if it seems descriptive enough
        if len(original_content) > 50 and ' ' in original_content:
            # Remove the reorganize command part and use the rest as context
            cleaned_content = original_content
            for keyword in ['reorganize roles', 'fix role names', 'improve role names', 'clean up roles']:
                cleaned_content = re.sub(rf'{re.escape(keyword)}\s*', '', cleaned_content, flags=re.IGNORECASE)
            
            if len(cleaned_content.strip()) > 20:
                print(f"DEBUG: Using remaining message as context: '{cleaned_content.strip()}'")
                return cleaned_content.strip()
        
        print(f"DEBUG: No specific context description found, using 'general community server'")
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
        
        # Only contains common words
        common_words = description_lower.split()
        if len(common_words) < 3:
            return True
        
        return False