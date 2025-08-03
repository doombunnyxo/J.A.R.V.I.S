"""
Context management for AI conversations
Handles permanent context, conversation history, and context filtering
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque
from ..data.persistence import data_manager
from ..config import config


class ContextManager:
    """Manages conversation context and permanent user data"""
    
    def __init__(self, groq_client=None):
        self.groq_client = groq_client
        
        # Unified conversation context shared between AIs
        self.unified_conversations: Dict[str, deque] = defaultdict(lambda: deque(maxlen=12))
        self.last_activity: Dict[str, datetime] = {}
        self.context_expiry_minutes = 30
    
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
    
    def get_conversation_context(self, user_id: int, channel_id: int) -> List[dict]:
        """Get conversation context if fresh"""
        if not self.is_context_fresh(user_id, channel_id):
            return []
        
        key = self.get_conversation_key(user_id, channel_id)
        return list(self.unified_conversations.get(key, []))
    
    async def filter_conversation_context(self, query: str, conversation_context: List[dict], user_name: str) -> str:
        """Filter conversation context for relevance using Groq"""
        if not self.groq_client or not config.has_groq_api():
            # Fallback to basic context if Groq unavailable
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
            
            completion = self.groq_client.chat.completions.create(
                messages=filter_messages,
                model=config.AI_MODEL,
                max_tokens=300,
                temperature=0.1
            )
            
            filtered_context = completion.choices[0].message.content.strip()
            
            # Ensure we always return at least the user name
            if not filtered_context or "no relevant context" in filtered_context.lower():
                return f"User: {user_name}" if user_name else ""
            
            return filtered_context
            
        except Exception as e:
            print(f"DEBUG: Context filtering failed: {e}")
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
        """Filter permanent context for relevance to current query"""
        if not self.groq_client or not config.has_groq_api() or not permanent_context:
            return permanent_context or []
        
        try:
            # Resolve user mentions in permanent context
            resolved_context = []
            for item in permanent_context:
                if message:
                    resolved_item = await self._resolve_user_mentions(item, message)
                    resolved_context.append(resolved_item)
                    if resolved_item != item:
                        print(f"DEBUG: Resolved mention '{item}' -> '{resolved_item}'")
                else:
                    resolved_context.append(item)
            
            context_text = "\\n".join([f"- {item}" for item in resolved_context])
            
            filter_messages = [
                {
                    "role": "system",
                    "content": """You are a context relevance filter. Identify which permanent context items are relevant to the user's current query.

INSTRUCTIONS:
1. Review each permanent context item carefully
2. You are given BOTH the resolved names AND original mentions (like <@123456>)
3. Match users by BOTH their name AND their Discord ID when provided
4. Include items that mention the CURRENT USER (by name OR by their Discord ID)
5. Include items with instructions for responding to the CURRENT USER
6. EXCLUDE items about other users UNLESS they're general rules that apply to everyone
7. EXCLUDE items completely unrelated to the query topic
8. Be SELECTIVE - only include items that would help answer this specific query
9. If an item says "when UserA talks to UserB", include it ONLY if current user is UserA OR UserB

Return only relevant permanent context items from the RESOLVED list, one per line, in the exact same format. If no items are relevant, return "No relevant permanent context"."""
                },
                {
                    "role": "user",
                    "content": f"CURRENT USER: {user_name} (ID: {message.author.id if message else 'unknown'})\\n\\nCURRENT QUERY: {query}\\n\\nPERMANENT CONTEXT ITEMS (mentions resolved to names):\\n{context_text}\\n\\nORIGINAL CONTEXT ITEMS (with mentions):\\n" + "\\n".join([f"- {item}" for item in permanent_context]) + "\\n\\nReturn only relevant permanent context items:"
                }
            ]
            
            completion = self.groq_client.chat.completions.create(
                messages=filter_messages,
                model=config.AI_MODEL,
                max_tokens=400,
                temperature=0.1
            )
            
            filtered_response = completion.choices[0].message.content.strip()
            
            print(f"DEBUG: Permanent context filter for user '{user_name}' (ID: {message.author.id if message else 'unknown'})")
            print(f"DEBUG: Original items: {len(permanent_context)}")
            print(f"DEBUG: Query: '{query}'")
            print(f"DEBUG: Filter response: {filtered_response[:200]}...")
            
            if "no relevant permanent context" in filtered_response.lower():
                print(f"DEBUG: No relevant permanent context found")
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
            print(f"DEBUG: Permanent context filtering failed: {e}")
            return resolved_context if 'resolved_context' in locals() else permanent_context
    
    async def build_full_context(self, query: str, user_id: int, channel_id: int, user_name: str, message=None) -> str:
        """Build complete filtered context for AI"""
        user_key = data_manager.get_user_key(message.author) if message else None
        
        # Get conversation context
        conversation_context = self.get_conversation_context(user_id, channel_id)
        filtered_conversation = await self.filter_conversation_context(
            query, conversation_context, user_name
        )
        
        context_parts = []
        
        # Add filtered conversation context
        if filtered_conversation and filtered_conversation.strip():
            context_parts.append(filtered_conversation)
        elif user_name:
            context_parts.append(f"User: {user_name}")
        
        # Add unfiltered permanent context (always included)
        if user_key:
            unfiltered_items = data_manager.get_unfiltered_permanent_context(user_key)
            if unfiltered_items:
                resolved_unfiltered = []
                for item in unfiltered_items:
                    if message:
                        resolved_item = await self._resolve_user_mentions(item, message)
                        resolved_unfiltered.append(resolved_item)
                    else:
                        resolved_unfiltered.append(item)
                
                context_parts.append("User preferences (always apply):\\n" + "\\n".join([
                    f"- {item}" for item in resolved_unfiltered
                ]))
        
        # Add filtered permanent context
        if user_key:
            permanent_items = data_manager.get_permanent_context(user_key)
            if permanent_items:
                relevant_permanent = await self.filter_permanent_context(
                    query, permanent_items, user_name, message
                )
                
                if relevant_permanent:
                    context_parts.append("Stored information about user:\\n" + "\\n".join([
                        f"- {item}" for item in relevant_permanent
                    ]))
        
        return "\\n\\n".join(context_parts)
    
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
                print(f"DEBUG: Failed to resolve user mention <@{user_id}>: {e}")
                continue
        
        return resolved_text