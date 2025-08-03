"""
AI Handler - Refactored and Modularized

This is the main AI handler that coordinates between different AI providers
and routes requests appropriately. Crafting functionality has been extracted
to a separate module for better organization.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Set, Tuple
import uuid

from discord.ext import commands
import discord
from groq import Groq

from src.config import config
from src.data.persistence import data_manager
from src.admin.permissions import is_admin
from src.ai.context_manager import ContextManager


class RateLimiter:
    """Rate limiting for AI requests"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[int, list] = {}  # user_id -> list of timestamps
    
    def is_allowed(self, user_id: int) -> bool:
        """Check if user is allowed to make a request"""
        now = time.time()
        
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        # Remove old requests outside the window
        self.requests[user_id] = [req_time for req_time in self.requests[user_id] 
                                  if now - req_time < self.window_seconds]
        
        # Check if user has exceeded the limit
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        # Add current request
        self.requests[user_id].append(now)
        return True
    
    def get_reset_time(self, user_id: int) -> Optional[datetime]:
        """Get when the rate limit will reset for a user"""
        if user_id not in self.requests or not self.requests[user_id]:
            return None
        
        oldest_request = min(self.requests[user_id])
        reset_time = datetime.fromtimestamp(oldest_request + self.window_seconds)
        return reset_time


class AIHandler:
    """Main AI handler for routing and processing requests"""
    
    def __init__(self, bot):
        self.bot = bot
        self.groq_client = self._initialize_groq()
        self.context_manager = ContextManager()
        
        # Rate limiting
        self.rate_limiter = RateLimiter(
            max_requests=config.AI_RATE_LIMIT_REQUESTS,
            window_seconds=config.AI_RATE_LIMIT_WINDOW
        )
        
        # Track processed messages to prevent duplicates
        self.processed_messages: Set[int] = set()
        self.admin_actions: Dict[str, dict] = {}
        
        # Cleanup tasks
        asyncio.create_task(self._cleanup_processed_messages())
        asyncio.create_task(self._cleanup_stale_admin_actions())
        
        # Instance ID for debugging
        self.instance_id = str(uuid.uuid4())[:8]
        print(f"[OK] AIHandler initialized with ID: {self.instance_id}")
    
    def _initialize_groq(self) -> Optional[Groq]:
        """Initialize Groq client if API key is available"""
        if config.has_groq_api():
            return Groq(api_key=config.GROQ_API_KEY)
        print("[WARN] No Groq API key found - Groq functionality disabled")
        return None
    
    async def _cleanup_processed_messages(self):
        """Periodically clean up processed message IDs"""
        while True:
            await asyncio.sleep(300)  # 5 minutes
            self.processed_messages.clear()
    
    async def _cleanup_stale_admin_actions(self):
        """Clean up stale admin actions that weren't confirmed"""
        while True:
            await asyncio.sleep(600)  # 10 minutes
            current_time = time.time()
            stale_actions = []
            
            for action_id, action_data in self.admin_actions.items():
                if current_time - action_data.get('timestamp', 0) > 600:  # 10 minutes
                    stale_actions.append(action_id)
            
            for action_id in stale_actions:
                del self.admin_actions[action_id]
    
    async def handle_ai_command(self, message, ai_query: str, force_provider: str = None):
        """
        Main entry point for AI command processing
        
        Args:
            message: Discord message object
            ai_query: User's query string  
            force_provider: Optional forced provider ("groq", "claude", or "crafting")
        """
        try:
            # Prevent duplicate processing
            if message.id in self.processed_messages:
                print(f"DEBUG: Message {message.id} already processed")
                return
            
            self.processed_messages.add(message.id)
            self._cleanup_processed_messages()
            
            # Check rate limit
            if not self.rate_limiter.is_allowed(message.author.id):
                await self._handle_rate_limit(message)
                return
            
            # Determine routing and get cleaned query
            provider, cleaned_query = await self._determine_provider_and_query(message, ai_query, force_provider)
            
            # Route to appropriate handler
            if provider == "claude":
                response = await self._handle_with_claude(message, cleaned_query)
            elif provider == "perplexity":
                response = await self._handle_with_perplexity(message, cleaned_query)
            elif provider == "crafting":
                response = await self._handle_with_crafting(message, cleaned_query)
            else:  # groq
                response = await self._handle_with_groq(message, cleaned_query)
            
            # Store conversation context
            if response and not response.startswith("Error"):
                self.context_manager.add_to_conversation(
                    message.author.id, message.channel.id, ai_query, response
                )
            
            # Send response if not already sent (admin actions send their own)
            if response:
                await self._send_response(message, response)
        
        except Exception as e:
            print(f"ERROR: [AIHandler-{self.instance_id}] handle_ai_command failed: {e}")
            error_msg = f"❌ An error occurred processing your request: {str(e)}"
            await message.channel.send(error_msg)
    
    async def _determine_provider_and_query(self, message, query: str, force_provider: str) -> tuple[str, str]:
        """Determine which provider to use and clean the query"""
        # If provider is forced, return as-is
        if force_provider:
            return force_provider, query
        
        # Use routing logic to determine provider
        from .routing import RoutingModule
        router = RoutingModule()
        
        provider = await router.determine_provider(message, query, None)
        cleaned_query = router.clean_query(query)
        
        return provider, cleaned_query
    
    async def _determine_provider(self, message, query: str, force_provider: str) -> str:
        """Determine which AI provider to use for the query"""
        if force_provider:
            return force_provider
        
        from .routing import RoutingModule
        router = RoutingModule()
        return await router.determine_provider(message, query, None)
    
    async def _handle_with_claude(self, message, query: str) -> str:
        """Handle query with Claude"""
        try:
            from ..search.claude import AnthropicAPI
            
            if not config.has_anthropic_api():
                return "❌ Claude API not configured. Please contact an administrator."
            
            # Create Claude client
            claude = AnthropicAPI(config.ANTHROPIC_API_KEY)
            
            # Build context for Claude
            context = await self.context_manager.build_full_context(
                query, message.author.id, message.channel.id,
                message.author.display_name, message
            )
            
            # Get response from Claude
            response = await claude.create_message(
                system_message=f"Context: {context}" if context else None,
                user_message=query,
                max_tokens=1000
            )
            
            return response
            
        except Exception as e:
            return f"❌ Error with Claude: {str(e)}"

    async def _handle_with_perplexity(self, message, query: str) -> str:
        """Handle query with Perplexity (deprecated - redirects to Claude)"""
        return await self._handle_with_claude(message, query)
    
    async def _handle_with_groq(self, message, query: str) -> str:
        """Handle query with Groq"""
        try:
            if not self.groq_client:
                return "❌ Groq API not configured. Please contact an administrator."
            
            # Build context for Groq
            context = await self._build_groq_context(message, query)
            system_message = self._build_groq_system_message(context, message.author.id)
            
            # Get response from Groq
            completion = self.groq_client.chat.completions.create(
                model=config.AI_MODEL,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": query}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            response = completion.choices[0].message.content.strip()
            
            # Handle admin actions if detected
            if await self._handle_admin_actions(message, query, response):
                return ""  # Admin action handled, no additional response needed
            
            return response
        
        except Exception as e:
            return f"Error processing with Groq: {str(e)}"
    
    async def _handle_with_crafting(self, message, query: str) -> str:
        """Handle query with crafting system using the dedicated crafting module"""
        print(f"DEBUG: _handle_with_crafting called with query: '{query}'")
        try:
            from .crafting_module import CraftingProcessor
            
            crafting_processor = CraftingProcessor()
            return await crafting_processor.handle_crafting_request(message, query)
            
        except Exception as e:
            return f"❌ **Crafting system error:** {str(e)}"
    
    async def _build_groq_context(self, message, query: str) -> str:
        """Build context for Groq queries"""
        user_key = data_manager.get_user_key(message.author)
        user_settings = data_manager.get_user_settings(user_key)
        
        # Get conversation context
        conversation_context = self.context_manager.get_conversation_context(
            message.author.id, message.channel.id
        )
        
        # Add channel context if no conversation and enabled
        if not conversation_context and user_settings.get("use_channel_context", True):
            channel_context = await self._get_channel_context(message.channel)
            if channel_context:
                conversation_context = [{"role": "system", "content": channel_context}]
        
        # Build full context
        return await self.context_manager.build_full_context(
            query, message.author.id, message.channel.id,
            message.author.display_name, message
        )
    
    def _build_groq_system_message(self, context: str, user_id: int) -> str:
        """Build system message for Groq"""
        parts = []
        
        if context:
            parts.append(f"RELEVANT CONTEXT:\\n{context}")
            parts.append("=" * 50)
        
        core_instructions = """You are a helpful AI assistant with the following capabilities:

1. **General Knowledge**: Answer questions using your training data and any relevant context provided above.

2. **Discord Server Management** (Admin only): Help with server administration including user moderation, role management, channel management, and message cleanup.

The relevant context section above contains only information pertinent to the current query. Use this context to provide more personalized and informed responses."""

        parts.append(core_instructions)
        
        # Add admin capabilities if user is admin
        if is_admin(user_id):
            admin_instructions = """Additional admin capabilities:

- User moderation (kick, ban, timeout/mute users)
- Role management (add/remove roles from users, rename roles)  
- Channel management (create/delete channels)
- Message cleanup (bulk delete messages, including from specific users)
- Nickname changes

When you detect an administrative request, respond by clearly stating what action you understood. DO NOT ask for text-based confirmation. The system will automatically handle confirmation.

Use this format:
I understand you want to [ACTION]. [Brief description of what will happen]

Examples:
- "kick that spammer" → I understand you want to kick [user]. They will be removed from the server.
- "delete John's messages" → I understand you want to delete messages from John. I'll remove their recent messages.
- "rename role Moderator to Super Mod" → I understand you want to rename the Moderator role to Super Mod.

Be concise and clear about what the action will do."""

            parts.append(admin_instructions)
        
        return "\\n\\n".join(parts)
    
    async def _handle_admin_actions(self, message, query: str, response: str) -> bool:
        """Handle admin action detection and confirmation"""
        if not is_admin(message.author.id) or not message.guild:
            return False
        
        # Import admin modules
        from ..admin.parser import AdminActionParser
        from ..admin.actions import AdminActionExecutor
        
        parser = AdminActionParser()
        executor = AdminActionExecutor(self.bot)
        
        # Parse admin intent from both query and response
        admin_intent = parser.parse_admin_intent(query, response)
        
        if not admin_intent:
            return False
        
        print(f"DEBUG: Admin intent detected: {admin_intent}")
        
        # Generate unique action ID
        action_id = str(uuid.uuid4())[:8]
        
        # Store action for confirmation
        self.admin_actions[action_id] = {
            'intent': admin_intent,
            'message': message,
            'timestamp': time.time(),
            'executor': executor
        }
        
        # Send confirmation message with reactions
        confirmation_text = f"🔧 **Admin Action Detected**\\n\\n{response}\\n\\n"
        confirmation_text += "React with ✅ to confirm or ❌ to cancel this action."
        confirmation_text += f"\\n\\n*Action ID: {action_id}*"
        
        confirmation_msg = await message.channel.send(confirmation_text)
        await confirmation_msg.add_reaction("✅")
        await confirmation_msg.add_reaction("❌")
        
        return True
    
    async def _get_channel_context(self, channel) -> Optional[str]:
        """Get recent channel context for queries"""
        try:
            # Get last 50 messages from channel
            messages = []
            async for msg in channel.history(limit=50):
                if not msg.author.bot and len(msg.content) > 0:
                    # Format: "Username: message content"
                    formatted_msg = f"{msg.author.display_name}: {msg.content[:100]}"
                    messages.append(formatted_msg)
            
            if not messages:
                return None
            
            # Reverse to chronological order and take last 35
            messages.reverse()
            recent_messages = messages[-35:] if len(messages) > 35 else messages
            
            context_text = "\\n".join(recent_messages)
            return f"Recent channel discussion:\\n{context_text}"
            
        except Exception as e:
            print(f"Error getting channel context: {e}")
            return None
    
    async def _send_response(self, message, response: str):
        """Send response, handling Discord's message limits"""
        if len(response) <= 2000:
            await message.channel.send(response)
        else:
            # Split long messages
            chunks = []
            current_chunk = ""
            
            for line in response.split('\\n'):
                if len(current_chunk + line + '\\n') > 1900:  # Leave buffer
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                        current_chunk = line + '\\n'
                    else:
                        # Line itself is too long, force split
                        chunks.append(line[:1900])
                        current_chunk = line[1900:] + '\\n'
                else:
                    current_chunk += line + '\\n'
            
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            
            # Send chunks
            for i, chunk in enumerate(chunks):
                if i > 0:
                    await asyncio.sleep(0.5)  # Small delay between chunks
                await message.channel.send(chunk)
    
    async def _handle_rate_limit(self, message):
        """Handle rate limit exceeded"""
        reset_time = self.rate_limiter.get_reset_time(message.author.id)
        if reset_time:
            reset_str = reset_time.strftime("%H:%M:%S")
            rate_msg = f"⏰ **Rate limit exceeded!** You can make {config.AI_RATE_LIMIT_REQUESTS} requests per {config.AI_RATE_LIMIT_WINDOW} seconds.\\n\\nTry again after {reset_str}."
        else:
            rate_msg = f"⏰ **Rate limit exceeded!** You can make {config.AI_RATE_LIMIT_REQUESTS} requests per {config.AI_RATE_LIMIT_WINDOW} seconds."
        
        await message.channel.send(rate_msg)
    
    async def handle_admin_reaction(self, reaction, user):
        """Handle admin action confirmation reactions"""
        if not is_admin(user.id):
            return
        
        # Extract action ID from message
        message_content = reaction.message.content
        if "*Action ID:" not in message_content:
            return
        
        action_id = message_content.split("*Action ID: ")[1].split("*")[0].strip()
        
        if action_id not in self.admin_actions:
            await reaction.message.channel.send("❌ **Admin action expired or not found.**")
            return
        
        action_data = self.admin_actions[action_id]
        executor = action_data['executor']
        intent = action_data['intent']
        
        if str(reaction.emoji) == "✅":
            # Execute the admin action
            try:
                result = await executor.execute_admin_action(intent, action_data['message'])
                await reaction.message.channel.send(f"✅ **Action completed:** {result}")
            except Exception as e:
                await reaction.message.channel.send(f"❌ **Action failed:** {str(e)}")
        elif str(reaction.emoji) == "❌":
            await reaction.message.channel.send("❌ **Admin action cancelled.**")
        
        # Clean up
        del self.admin_actions[action_id]
        try:
            await reaction.message.delete()
        except:
            pass