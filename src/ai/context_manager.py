"""
Context management for AI conversations
Handles permanent context, conversation history, and context filtering
"""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, NamedTuple
from collections import defaultdict, deque
from ..data.persistence import data_manager
from ..config import config
from ..utils.logging import get_logger

logger = get_logger(__name__)


class ChannelMessage(NamedTuple):
    """Structure for storing channel messages with timestamps"""
    content: str
    timestamp: datetime
    user_name: str


class ContextManager:
    """Manages conversation context and permanent user data"""
    
    def __init__(self):
        # We'll use OpenAI GPT-4o mini for context filtering
        
        # Vector database enhancer - primary context storage
        self.vector_enhancer = None
        self._init_vector_enhancer()
        
        # Note: All conversation and channel context is now stored in vector database
        # Only permanent context remains in JSON files for raw inclusion
    
    def _init_vector_enhancer(self):
        """Initialize vector database enhancer if available"""
        try:
            from ..vectordb.context_enhancer import vector_enhancer
            self.vector_enhancer = vector_enhancer
            logger.info("Vector database enhancer connected to context manager")
        except ImportError:
            logger.info("Vector database not available - using standard context management")
    
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
    
    def add_to_conversation(self, user_id: int, channel_id: int, user_message: str, ai_response: str):
        """Add exchange to conversation context (vector DB only)"""
        if self.vector_enhancer and self.vector_enhancer.initialized:
            try:
                import asyncio
                asyncio.create_task(self.vector_enhancer.store_conversation(
                    user_id=user_id,
                    channel_id=channel_id,
                    message=user_message,
                    response=ai_response
                ))
            except Exception as e:
                logger.debug(f"Failed to store conversation in vector DB: {e}")
        else:
            logger.warning("Vector database not available - conversation not stored")
    
    def clear_conversation(self, user_id: int, channel_id: int):
        """Clear conversation context - now a no-op since we use vector DB"""
        # Note: Vector DB handles its own cleanup based on age
        pass
    
    def add_channel_message(self, channel_id: int, user_name: str, message_content: str, channel=None):
        """Add message to channel conversation history (vector DB only)"""
        # Check if this is a thread
        is_thread = False
        parent_channel_id = None
        
        if channel and hasattr(channel, 'type'):
            channel_type = str(channel.type)
            if channel_type in ['public_thread', 'private_thread']:
                is_thread = True
                parent_channel_id = channel.parent_id if hasattr(channel, 'parent_id') else None
        
        if self.vector_enhancer and self.vector_enhancer.initialized:
            try:
                import asyncio
                message_id = getattr(channel, 'last_message_id', None) if channel else None
                
                if is_thread:
                    # Store thread message
                    asyncio.create_task(self.vector_enhancer.vector_db.add_thread_message(
                        thread_id=channel_id,
                        parent_channel_id=parent_channel_id or 0,
                        user_name=user_name,
                        message=message_content,
                        message_id=message_id
                    ))
                else:
                    # Store regular channel message
                    asyncio.create_task(self.vector_enhancer.store_channel_message(
                        channel_id=channel_id,
                        user_name=user_name,
                        message=message_content,
                        message_id=message_id
                    ))
            except Exception as e:
                logger.debug(f"Failed to store message in vector DB: {e}")
        else:
            logger.warning("Vector database not available - message not stored")
    
    async def get_conversation_context(self, user_id: int, channel_id: int, query: str = "") -> List[str]:
        """Get conversation context from vector database using semantic search"""
        if self.vector_enhancer and self.vector_enhancer.initialized:
            try:
                results = await self.vector_enhancer.get_semantic_conversation_context(
                    query=query or "recent conversation",
                    user_id=user_id,
                    channel_id=channel_id,
                    limit=5
                )
                return results
            except Exception as e:
                logger.debug(f"Failed to get conversation context from vector DB: {e}")
        return []
    
    async def get_channel_context(self, channel_id: int, query: str = "", limit: int = 10) -> List[str]:
        """Get channel messages from vector database using semantic search"""
        if self.vector_enhancer and self.vector_enhancer.initialized:
            try:
                results = await self.vector_enhancer.get_semantic_channel_context(
                    query=query or "recent channel discussion",
                    channel_id=channel_id,
                    limit=limit
                )
                return results
            except Exception as e:
                logger.debug(f"Failed to get channel context from vector DB: {e}")
        return []
    
    async def get_thread_context(self, thread_id: int, query: str = "", limit: int = 10) -> List[str]:
        """Get thread messages from vector database"""
        if self.vector_enhancer and self.vector_enhancer.initialized:
            try:
                # Search thread context collection specifically
                results = self.vector_enhancer.vector_db.collections['thread_context'].query(
                    query_texts=[query or "thread discussion"],
                    n_results=limit,
                    where={"thread_id": {"$eq": str(thread_id)}}
                )
                
                if results['documents'] and results['documents'][0]:
                    return results['documents'][0]
            except Exception as e:
                logger.debug(f"Failed to get thread context from vector DB: {e}")
        return []
    
    # Legacy compatibility methods
    def get_smart_channel_context(self, channel_id: int, limit: int = 35, include_weights: bool = False) -> List[str]:
        """Legacy method - now uses vector DB async call"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a task for later execution
                return []  # Return empty for now, will be handled by new context system
            else:
                return loop.run_until_complete(self.get_channel_context(channel_id, limit=limit))
        except:
            return []
    
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
    
    def extract_reply_context(self, message) -> str:
        """Extract the original message being replied to"""
        if not message or not message.reference:
            return ""
        
        try:
            original_message = message.reference.resolved
            if original_message and original_message.content:
                author_name = original_message.author.display_name
                return f"[REPLYING TO] {author_name}: {original_message.content}"
        except Exception as e:
            logger.debug(f"Failed to extract reply context: {e}")
        
        return ""

    async def build_unfiltered_context(self, user_id: int, channel_id: int, user_name: str, message=None) -> str:
        """Build complete unfiltered context for casual AI chat using vector database"""
        user_key = data_manager.get_user_key(message.author) if message else None
        
        # Build structured context using vector database
        structured_context = []
        
        # [Reply Context] - Always preserved
        reply_context = self.extract_reply_context(message)
        if reply_context:
            structured_context.append(f"[Reply Context]\n{reply_context}")
        
        # [Recent Conversations] - From vector database
        if self.vector_enhancer and self.vector_enhancer.initialized:
            try:
                recent_conversations = await self.get_conversation_context(user_id, channel_id, "recent conversation")
                if recent_conversations:
                    conv_text = "\n".join(recent_conversations)
                    structured_context.append(f"[Recent Conversations]\n{conv_text}")
                
                # [Channel Context] - From vector database
                channel_messages = await self.get_channel_context(channel_id, "recent discussion", limit=10)
                if channel_messages:
                    channel_text = "\n".join(channel_messages)
                    channel_name = message.channel.name if message and hasattr(message.channel, 'name') else "current channel"
                    structured_context.append(f"[Channel Summary - #{channel_name}]\n{channel_text}")
                
                # [Thread Context] if applicable
                if message and hasattr(message.channel, 'type') and str(message.channel.type) in ['public_thread', 'private_thread']:
                    thread_messages = await self.get_thread_context(channel_id, "thread discussion")
                    if thread_messages:
                        thread_text = "\n".join(thread_messages)
                        thread_name = message.channel.name if hasattr(message.channel, 'name') else "current thread"
                        structured_context.append(f"[Thread Summary - {thread_name}]\n{thread_text}")
            
            except Exception as e:
                logger.debug(f"Failed to get vector context for unfiltered build: {e}")
        
        # [User Context] - Always include user info and permanent context
        user_context_parts = []
        
        if user_name:
            user_context_parts.append(f"Current user: {user_name}")
        
        # Add permanent context about user (raw, unfiltered)
        if user_key:
            permanent_items = data_manager.get_permanent_context(user_key)
            if permanent_items:
                user_context_parts.append("Stored information about this user:")
                for item in permanent_items:
                    user_context_parts.append(f"- {item}")
        
        if user_context_parts:
            structured_context.append(f"[User Context]\n" + "\n".join(user_context_parts))
        
        # [Global Settings] - System-wide preferences (always unfiltered)
        unfiltered_items = data_manager.get_unfiltered_permanent_context()
        if unfiltered_items:
            settings_text = "\n".join([f"- {item}" for item in unfiltered_items])
            structured_context.append(f"[Global Settings]\nAlways apply these preferences:\n{settings_text}")
        
        return "\n\n".join(structured_context) if structured_context else ""

    async def build_full_context(self, query: str, user_id: int, channel_id: int, user_name: str, message=None) -> str:
        """Build complete context using vector database and raw permanent context"""
        user_key = data_manager.get_user_key(message.author) if message else None
        
        # TEMPORARILY DISABLE vector context to test if this is causing timeouts
        # TODO: Re-enable after testing
        if False and self.vector_enhancer and self.vector_enhancer.initialized:
            try:
                # Get semantically relevant context from existing vector DB data
                semantic_context = await self._get_fast_semantic_context(
                    query=query,
                    user_id=user_id,
                    channel_id=channel_id
                )
                
                # Build final context with all components
                context_parts = []
                
                # Add user identification
                if user_name:
                    context_parts.append(f"User: {user_name}")
                
                # Add reply context if exists (always preserved)
                reply_context = self.extract_reply_context(message)
                if reply_context:
                    context_parts.append(reply_context)
                
                # Add semantic search results
                if semantic_context:
                    context_parts.append(semantic_context)
                
                # Add permanent context raw (never filtered)
                if user_key:
                    permanent_items = data_manager.get_permanent_context(user_key)
                    if permanent_items:
                        permanent_text = "Permanent user context:\n" + "\n".join([
                            f"- {item}" for item in permanent_items
                        ])
                        context_parts.append(permanent_text)
                
                # Add global unfiltered context (always included)
                unfiltered_items = data_manager.get_unfiltered_permanent_context()
                if unfiltered_items:
                    unfiltered_context = "Global preferences (always apply):\n" + "\n".join([
                        f"- [MANDATORY] {item}" for item in unfiltered_items
                    ])
                    context_parts.append(unfiltered_context)
                
                final_context = "\n\n".join(context_parts)
                logger.debug("Using vector database context with raw permanent context")
                return final_context
                
            except Exception as e:
                logger.debug(f"Vector context building failed: {e}")
        
        # Fallback for when vector DB is not available
        logger.warning("Vector database not available - using minimal context")
        fallback_parts = []
        
        if user_name:
            fallback_parts.append(f"User: {user_name}")
        
        # Add reply context
        reply_context = self.extract_reply_context(message)
        if reply_context:
            fallback_parts.append(reply_context)
        
        # Add permanent context (still raw)
        if user_key:
            permanent_items = data_manager.get_permanent_context(user_key)
            if permanent_items:
                permanent_text = "Permanent user context:\n" + "\n".join([
                    f"- {item}" for item in permanent_items
                ])
                fallback_parts.append(permanent_text)
        
        # Add global context
        unfiltered_items = data_manager.get_unfiltered_permanent_context()
        if unfiltered_items:
            unfiltered_context = "Global preferences (always apply):\n" + "\n".join([
                f"- [MANDATORY] {item}" for item in unfiltered_items
            ])
            fallback_parts.append(unfiltered_context)
        
        return "\n\n".join(fallback_parts) if fallback_parts else f"User: {user_name}" if user_name else ""
    
    async def _get_fast_semantic_context(self, query: str, user_id: int, channel_id: int) -> str:
        """Get semantic context quickly from existing vector data (no new embeddings)"""
        try:
            context_parts = []
            
            # Get relevant conversations (fast - uses existing embeddings) - REDUCED limits
            conv_results = await self.vector_enhancer.get_semantic_conversation_context(
                query=query,
                user_id=user_id,
                channel_id=channel_id,
                limit=2  # Reduced from 3
            )
            if conv_results:
                context_parts.append("[Relevant Previous Conversations]")
                # Truncate long messages to prevent bloat
                truncated_results = [result[:200] + "..." if len(result) > 200 else result for result in conv_results[:2]]
                context_parts.extend(truncated_results)
            
            # Get relevant channel messages (fast - uses existing embeddings) - REDUCED limits  
            channel_results = await self.vector_enhancer.get_semantic_channel_context(
                query=query,
                channel_id=channel_id,
                limit=3  # Reduced from 5
            )
            if channel_results:
                context_parts.append("[Relevant Channel Discussion]")
                # Truncate long messages to prevent bloat
                truncated_results = [result[:150] + "..." if len(result) > 150 else result for result in channel_results[:3]]
                context_parts.extend(truncated_results)
            
            return "\n\n".join(context_parts) if context_parts else ""
            
        except Exception as e:
            logger.debug(f"Fast semantic context retrieval failed: {e}")
            return ""
    
    async def filter_all_context(self, query: str, full_context: str, user_name: str) -> str:
        """Filter all context types together for relevance using OpenAI GPT-4o mini"""
        try:
            filter_messages = [
                {
                    "role": "system",
                    "content": """You are a smart context filter assistant. Your task is to read the recent chat messages and previous user queries, then select and output only the messages or message clusters that are **most relevant** to the user's current query.

Instructions:
- Consider the user's current query and the entire conversation history.
- Understand that relevant context may be spread across multiple messages or implied by the topic.
- Group related messages that form a coherent context block.
- Exclude unrelated chit-chat, greetings, or redundant info.
- Preserve message order and clarity.
- Output a concise summary of the relevant context in natural language or as a list of key points."""
                },
                {
                    "role": "user", 
                    "content": f"""User's current query:  
{query}

Context to filter:
{full_context}

Filtered relevant context:"""
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