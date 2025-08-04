"""
Context management for AI conversations
Handles permanent context, conversation history, and context filtering
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque
from ..data.persistence import data_manager
from ..config import config
from ..utils.logging import get_logger

logger = get_logger(__name__)


class ContextManager:
    """Manages conversation context and permanent user data"""
    
    def __init__(self):
        # No need for groq_client - we'll use OpenAI GPT-4o mini for context filtering
        
        # Unified conversation context shared between AIs
        self.unified_conversations: Dict[str, deque] = defaultdict(lambda: deque(maxlen=12))
        self.last_activity: Dict[str, datetime] = {}
        self.context_expiry_minutes = 30
        
        # Channel conversation storage - keyed by channel_id
        self.channel_conversations: Dict[int, deque] = defaultdict(lambda: deque(maxlen=50))
        self.channel_last_activity: Dict[int, datetime] = {}
    
    async def _call_openai_gpt4o_mini(self, messages: List[dict], max_tokens: int = 300) -> str:
        """Helper method to call OpenAI GPT-4o mini for context filtering"""
        import aiohttp
        
        headers = {
            "Authorization": f"Bearer {config.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4o-mini", 
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "messages": messages
        }
        
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post("https://api.openai.com/v1/chat/completions", 
                                   headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"].strip()
                else:
                    raise Exception(f"OpenAI API error {response.status}: {await response.text()}")
    
    def get_conversation_key(self, user_id: int, channel_id: int) -> str:
        """Generate conversation key for tracking"""
        return f"{user_id}_{channel_id}"
    
    def is_context_fresh(self, user_id: int, channel_id: int) -> bool:
        """Check if conversation context is still fresh"""
        key = self.get_conversation_key(user_id, channel_id)
        last_activity = self.last_activity.get(key)
        
        if not last_activity:
            return False
            
        return datetime.now() - last_activity < timedelta(minutes=self.context_expiry_minutes)
    
    def add_to_conversation(self, user_id: int, channel_id: int, user_message: str, ai_response: str):
        """Add exchange to conversation context"""
        key = self.get_conversation_key(user_id, channel_id)
        context = self.unified_conversations[key]
        
        context.append({"role": "user", "content": user_message})
        context.append({"role": "assistant", "content": ai_response})
        self.last_activity[key] = datetime.now()
    
    def clear_conversation(self, user_id: int, channel_id: int):
        """Clear conversation context for user in channel"""
        key = self.get_conversation_key(user_id, channel_id)
        self.unified_conversations.pop(key, None)
        self.last_activity.pop(key, None)
    
    def add_channel_message(self, channel_id: int, user_name: str, message_content: str):
        """Add message to channel conversation history"""
        channel_messages = self.channel_conversations[channel_id]
        
        # Format message as "Username: content"
        formatted_message = f"{user_name}: {message_content[:100]}"
        channel_messages.append(formatted_message)
        self.channel_last_activity[channel_id] = datetime.now()
    
    def get_channel_context(self, channel_id: int, limit: int = 35) -> List[str]:
        """Get recent channel messages for context"""
        channel_messages = self.channel_conversations.get(channel_id, deque())
        
        # Return most recent messages up to limit
        recent_messages = list(channel_messages)[-limit:] if len(channel_messages) > limit else list(channel_messages)
        return recent_messages
    
    def get_conversation_context(self, user_id: int, channel_id: int) -> List[dict]:
        """Get conversation context if fresh"""
        if not self.is_context_fresh(user_id, channel_id):
            return []
        
        key = self.get_conversation_key(user_id, channel_id)
        return list(self.unified_conversations.get(key, []))
    
    async def filter_conversation_context(self, query: str, conversation_context: List[dict], user_name: str) -> str:
        """Filter conversation context for relevance using OpenAI GPT-4o mini"""
        if not config.has_openai_api():
            # Fallback to basic context if OpenAI unavailable
            if not conversation_context:
                return f"User: {user_name}" if user_name else ""
            
            context_parts = [f"User: {user_name}"] if user_name else []
            context_parts.append("Previous messages (context only):\\n" + "\\n".join([
                f"[Previous] {msg['role']}: {msg['content'][:200]}..." 
                for msg in conversation_context[-4:]
            ]))
            return "\\n\\n".join(context_parts)
        
        try:
            if not conversation_context:
                return f"User: {user_name}" if user_name else ""
            
            context_parts = []
            if user_name:
                context_parts.append(f"USER: {user_name}")
            
            context_parts.append("PREVIOUS MESSAGES (NOT part of current request):\\n" + "\\n".join([
                f"[Previous] {msg['role']}: {msg['content']}" 
                for msg in conversation_context[-6:]
            ]))
            
            full_context = "\\n\\n".join(context_parts)
            
            filter_messages = [
                {
                    "role": "system",
                    "content": """You are a context filter. Extract information from PREVIOUS conversations that is relevant to the user's current query.

INSTRUCTIONS:
1. ALWAYS include the user's name/identity
2. The conversation history shown is from PREVIOUS messages, not the current query
3. Extract only context from past messages that helps answer the CURRENT query
4. Format extracted context to clearly show it's from previous messages
5. Keep response under 300 tokens
6. If previous messages aren't relevant to current query, just return the user's name

Note: Permanent user context will be added separately.

Return only the filtered previous conversation context - no explanations."""
                },
                {
                    "role": "user", 
                    "content": f"CURRENT QUERY: {query}\\n\\nAVAILABLE CONTEXT:\\n{full_context}\\n\\nExtract and summarize context relevant to this query:"
                }
            ]
            
            # Use OpenAI GPT-4o mini for context filtering
            filtered_context = await self._call_openai_gpt4o_mini(filter_messages, max_tokens=300)
            
            # Ensure we always return at least the user name
            if not filtered_context or "no relevant context" in filtered_context.lower():
                return f"User: {user_name}" if user_name else ""
            
            return filtered_context
            
        except Exception as e:
            logger.debug(f"Context filtering failed: {e}")
            # Fallback to basic context
            context_parts = []
            if user_name:
                context_parts.append(f"User: {user_name}")
            if conversation_context:
                context_parts.append("Recent conversation:\\n" + "\\n".join([
                    f"{msg['role']}: {msg['content'][:200]}..." 
                    for msg in conversation_context[-4:]
                ]))
            return "\\n\\n".join(context_parts)
    
    async def filter_permanent_context(self, query: str, permanent_context: List[str], user_name: str, message=None) -> List[str]:
        """Filter permanent context for relevance to current query using OpenAI GPT-4o mini"""
        if not config.has_openai_api() or not permanent_context:
            return permanent_context or []
        
        try:
            # No need to resolve mentions anymore - they're already saved as usernames
            context_text = "\\n".join([f"- {item}" for item in permanent_context])
            
            filter_messages = [
                {
                    "role": "system",
                    "content": """You are a context relevance filter. Identify which permanent context items are relevant to the user's current query.

INSTRUCTIONS:
1. Review each permanent context item carefully
2. Context items now contain actual usernames (not Discord IDs)
3. Include items that mention the CURRENT USER by name
4. Include items with instructions for responding to the CURRENT USER
5. EXCLUDE items about other users UNLESS they're general rules that apply to everyone
6. EXCLUDE items completely unrelated to the query topic
7. Be SELECTIVE - only include items that would help answer this specific query
8. If an item says "when UserA talks to UserB", include it ONLY if current user is UserA OR UserB

Return only relevant permanent context items, one per line, in the exact same format. If no items are relevant, return "No relevant permanent context"."""
                },
                {
                    "role": "user",
                    "content": f"CURRENT USER: {user_name}\\n\\nCURRENT QUERY: {query}\\n\\nPERMANENT CONTEXT ITEMS:\\n{context_text}\\n\\nReturn only relevant permanent context items:"
                }
            ]
            
            # Use OpenAI GPT-4o mini for permanent context filtering
            filtered_response = await self._call_openai_gpt4o_mini(filter_messages, max_tokens=400)
            
            logger.debug(f"Permanent context filter for user '{user_name}' (ID: {message.author.id if message else 'unknown'})")
            logger.debug(f"Original items: {len(permanent_context)}")
            logger.debug(f"Query: '{query}'")
            logger.debug(f"Filter response: {filtered_response[:200]}...")
            
            if "no relevant permanent context" in filtered_response.lower():
                logger.debug(f"No relevant permanent context found")
                return []
            
            # Parse response back into list
            filtered_items = []
            for line in filtered_response.split('\\n'):
                line = line.strip()
                if line.startswith('- '):
                    filtered_items.append(line[2:])
                elif line and not line.startswith('USER:') and not line.startswith('CURRENT QUERY:'):
                    filtered_items.append(line)
            
            return filtered_items
            
        except Exception as e:
            logger.debug(f"Permanent context filtering failed: {e}")
            return permanent_context
    
    async def build_unfiltered_context(self, user_id: int, channel_id: int, user_name: str, message=None) -> str:
        """Build complete unfiltered context for casual AI chat"""
        user_key = data_manager.get_user_key(message.author) if message else None
        
        # Gather all available context without filtering
        context_parts = []
        
        # Always include user name
        if user_name:
            context_parts.append(f"User: {user_name}")
        
        # Get conversation context (last 6 exchanges)
        conversation_context = self.get_conversation_context(user_id, channel_id)
        if conversation_context:
            conversation_text = "\n".join([
                f"[Previous] {msg['role']}: {msg['content']}" 
                for msg in conversation_context[-6:]
            ])
            context_parts.append(f"Previous conversation:\n{conversation_text}")
        
        # Get channel context if enabled
        if user_key:
            user_settings = data_manager.get_user_settings(user_key)
            if user_settings.get("use_channel_context", True):
                # Get context from current channel
                channel_messages = self.get_channel_context(channel_id, limit=35)
                if channel_messages:
                    channel_context_text = "\n".join(channel_messages)
                    current_channel_name = message.channel.name if message and hasattr(message.channel, 'name') else "current channel"
                    context_parts.append(f"Recent discussion in #{current_channel_name}:\n{channel_context_text}")
                
                # Check if user mentioned other channels and include their context
                if message and message.channel_mentions:
                    for mentioned_channel in message.channel_mentions:
                        if mentioned_channel.id != channel_id:  # Don't duplicate current channel
                            mentioned_messages = self.get_channel_context(mentioned_channel.id, limit=20)
                            if mentioned_messages:
                                mentioned_context_text = "\n".join(mentioned_messages)
                                context_parts.append(f"Recent discussion in #{mentioned_channel.name}:\n{mentioned_context_text}")
        
        # Get ALL permanent context without filtering
        if user_key:
            permanent_items = data_manager.get_permanent_context(user_key)
            if permanent_items:
                permanent_text = "\n".join([f"- {item}" for item in permanent_items])
                context_parts.append(f"Stored information about user:\n{permanent_text}")
        
        # Add global unfiltered permanent context
        unfiltered_items = data_manager.get_unfiltered_permanent_context()
        if unfiltered_items:
            unfiltered_context = "Global preferences (always apply):\n" + "\n".join([
                f"- [MANDATORY] {item}" for item in unfiltered_items
            ])
            context_parts.append(unfiltered_context)
        
        return "\n\n".join(context_parts) if context_parts else ""

    async def build_full_context(self, query: str, user_id: int, channel_id: int, user_name: str, message=None) -> str:
        """Build complete filtered context for AI (conversation + channel + permanent context filtered together)"""
        user_key = data_manager.get_user_key(message.author) if message else None
        
        # Gather all available context
        context_parts = []
        
        # Always include user name
        if user_name:
            context_parts.append(f"User: {user_name}")
        
        # Get conversation context
        conversation_context = self.get_conversation_context(user_id, channel_id)
        if conversation_context:
            conversation_text = "\n".join([
                f"[Previous] {msg['role']}: {msg['content']}" 
                for msg in conversation_context[-6:]
            ])
            context_parts.append(f"Previous conversation:\n{conversation_text}")
        
        # Get channel context if enabled
        if user_key:
            user_settings = data_manager.get_user_settings(user_key)
            if user_settings.get("use_channel_context", True):
                # Get context from current channel
                channel_messages = self.get_channel_context(channel_id, limit=35)
                if channel_messages:
                    channel_context_text = "\n".join(channel_messages)
                    current_channel_name = message.channel.name if message and hasattr(message.channel, 'name') else "current channel"
                    context_parts.append(f"Recent discussion in #{current_channel_name}:\n{channel_context_text}")
                
                # Check if user mentioned other channels and include their context
                if message and message.channel_mentions:
                    for mentioned_channel in message.channel_mentions:
                        if mentioned_channel.id != channel_id:  # Don't duplicate current channel
                            mentioned_messages = self.get_channel_context(mentioned_channel.id, limit=20)
                            if mentioned_messages:
                                mentioned_context_text = "\n".join(mentioned_messages)
                                context_parts.append(f"Recent discussion in #{mentioned_channel.name}:\n{mentioned_context_text}")
        
        # Get permanent context
        if user_key:
            permanent_items = data_manager.get_permanent_context(user_key)
            if permanent_items:
                permanent_text = "\n".join([f"- {item}" for item in permanent_items])
                context_parts.append(f"Stored information about user:\n{permanent_text}")
        
        # Filter all context together using OpenAI
        if context_parts and config.has_openai_api():
            try:
                full_context = "\n\n".join(context_parts)
                filtered_context = await self.filter_all_context(query, full_context, user_name)
                
                # Add global unfiltered permanent context after filtering
                unfiltered_items = data_manager.get_unfiltered_permanent_context()
                if unfiltered_items:
                    unfiltered_context = "Global preferences (always apply):\n" + "\n".join([
                        f"- [MANDATORY] {item}" for item in unfiltered_items
                    ])
                    return f"{filtered_context}\n\n{unfiltered_context}" if filtered_context else unfiltered_context
                
                return filtered_context
            except Exception as e:
                logger.debug(f"Context filtering failed: {e}")
                # Fallback to unfiltered context
                full_context = "\n\n".join(context_parts)
                unfiltered_items = data_manager.get_unfiltered_permanent_context()
                if unfiltered_items:
                    unfiltered_context = "Global preferences (always apply):\n" + "\n".join([
                        f"- [MANDATORY] {item}" for item in unfiltered_items
                    ])
                    return f"{full_context}\n\n{unfiltered_context}" if full_context else unfiltered_context
                return full_context
        
        # Return unfiltered context if no OpenAI API
        full_context = "\n\n".join(context_parts) if context_parts else f"User: {user_name}" if user_name else ""
        unfiltered_items = data_manager.get_unfiltered_permanent_context()
        if unfiltered_items:
            unfiltered_context = "Global preferences (always apply):\n" + "\n".join([
                f"- [MANDATORY] {item}" for item in unfiltered_items
            ])
            return f"{full_context}\n\n{unfiltered_context}" if full_context else unfiltered_context
        return full_context
    
    async def filter_all_context(self, query: str, full_context: str, user_name: str) -> str:
        """Filter all context types together for relevance using OpenAI GPT-4o mini"""
        try:
            filter_messages = [
                {
                    "role": "system",
                    "content": """You are a context filter. Extract information from ALL available context that is relevant to the user's current query.

INSTRUCTIONS:
1. ALWAYS include the user's name/identity
2. Extract only context that helps answer the CURRENT query
3. Be concise and factual, no frivolities
4. If no context is relevant to the query, just return the user's name

Return only the filtered context - no explanations."""
                },
                {
                    "role": "user", 
                    "content": f"CURRENT QUERY: {query}\n\nAVAILABLE CONTEXT:\n{full_context}\n\nExtract and summarize context relevant to this query:"
                }
            ]
            
            # Use OpenAI GPT-4o mini for unified context filtering
            filtered_context = await self._call_openai_gpt4o_mini(filter_messages, max_tokens=600)
            
            # Ensure we always return at least the user name
            if not filtered_context or "no relevant context" in filtered_context.lower():
                return f"User: {user_name}" if user_name else ""
            
            return filtered_context
            
        except Exception as e:
            logger.debug(f"Unified context filtering failed: {e}")
            # Fallback to basic context
            return f"User: {user_name}\n\n{full_context[:500]}..." if full_context else f"User: {user_name}" if user_name else ""
    
    async def _resolve_user_mentions(self, text: str, message) -> str:
        """Resolve Discord user mentions in text"""
        import re
        
        mention_pattern = r'<@!?(\\d+)>'
        mentions = re.findall(mention_pattern, text)
        
        resolved_text = text
        for user_id in mentions:
            try:
                user = None
                if message.guild:
                    user = message.guild.get_member(int(user_id))
                
                if not user:
                    user = message.bot.get_user(int(user_id))
                
                if not user:
                    user = await message.bot.fetch_user(int(user_id))
                
                if user:
                    mention_formats = [f'<@{user_id}>', f'<@!{user_id}>']
                    for mention_format in mention_formats:
                        resolved_text = resolved_text.replace(mention_format, user.display_name)
                
            except Exception as e:
                logger.debug(f"Failed to resolve user mention <@{user_id}>: {e}")
                continue
        
        return resolved_text