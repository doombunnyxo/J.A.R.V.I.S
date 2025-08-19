"""
AI Handler - Refactored and Modularized

Main AI handler that coordinates OpenAI services and routes requests
appropriately. Uses centralized OpenAI client and modular architecture.
"""

import asyncio
import re
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Set, Tuple

from discord.ext import commands
import discord

from src.config import config
from src.data.persistence import data_manager
from src.admin.permissions import is_admin
from src.admin.admin_processor import AdminProcessor
from src.ai.context_manager import ContextManager
from src.ai.openai_client import openai_client
from . import routing
from ..utils.logging import get_logger

logger = get_logger(__name__)


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
        self.context_manager = ContextManager()
        
        # Initialize admin processor
        self.admin_processor = AdminProcessor(bot, self)
        
        # Rate limiting
        self.rate_limiter = RateLimiter(
            max_requests=config.AI_RATE_LIMIT_REQUESTS,
            window_seconds=config.AI_RATE_LIMIT_WINDOW
        )
        
        # Track processed messages to prevent duplicates
        self.processed_messages: Set[int] = set()
        
        # Track admin actions (delegated to admin processor)
        self.admin_actions: Dict[str, Dict] = {}
        
        # Cleanup tasks will be started when bot is ready
        self._cleanup_tasks_started = False
        
        logger.info("AIHandler initialized")
    
    
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
            
            # Clean up legacy admin actions
            stale_actions = [action_id for action_id, action_data in self.admin_actions.items() 
                           if current_time - action_data.get('timestamp', 0) > 600]
            
            for action_id in stale_actions:
                del self.admin_actions[action_id]
            
            # Also clean up admin processor actions if available
            if hasattr(self.admin_processor, 'pending_admin_actions'):
                for action_id, action_data in list(self.admin_processor.pending_admin_actions.items()):
                    if current_time - action_data.get('timestamp', datetime.now()).timestamp() > 600:
                        del self.admin_processor.pending_admin_actions[action_id]
    
    def _start_cleanup_tasks(self):
        """Start cleanup tasks if not already started"""
        if not self._cleanup_tasks_started:
            try:
                asyncio.create_task(self._cleanup_processed_messages())
                asyncio.create_task(self._cleanup_stale_admin_actions())
                self._cleanup_tasks_started = True
            except RuntimeError:
                # Event loop not running yet, will be started later
                pass
    
    async def handle_ai_command(self, message, ai_query: str, force_provider: str = None):
        """
        Main entry point for AI command processing
        
        Args:
            message: Discord message object
            ai_query: User's query string  
            force_provider: Optional forced provider ("openai", "crafting", "full-search", or "direct-ai")
        """
        try:
            print(f"DEBUG: handle_ai_command called with query: '{ai_query[:50]}...'")
            
            # Prevent duplicate processing
            if message.id in self.processed_messages:
                logger.debug(f"Message {message.id} already processed")
                return
            
            self.processed_messages.add(message.id)
            
            # Start cleanup tasks if not already started
            self._start_cleanup_tasks()
            
            # Check rate limit
            if not self.rate_limiter.is_allowed(message.author.id):
                await self._handle_rate_limit(message)
                return
            
            # Determine routing and get cleaned query
            provider, cleaned_query = await self._determine_provider_and_query(ai_query, force_provider)
            
            # Route to appropriate handler
            if provider == "openai":
                response = await self._handle_with_openai(message, cleaned_query)
            elif provider == "direct-ai":
                response = await self._handle_direct_ai(message, cleaned_query)
            elif provider == "full-search":
                # Full search uses GPT-4o directly (no two-stage summarization)
                response = await self._handle_full_search(message, cleaned_query)
            elif provider == "crafting":
                response = await self._handle_with_crafting(message, cleaned_query)
            else:  # Default to OpenAI
                response = await self._handle_with_openai(message, cleaned_query)
            
            # Store conversation context (background task - don't block response)
            if response and not response.startswith("Error"):
                # Store in vector database asynchronously
                asyncio.create_task(self._store_conversation_async(
                    user_id=message.author.id,
                    channel_id=message.channel.id,
                    user_message=ai_query,
                    ai_response=response,
                    provider=provider
                ))
            
            # Send response if not already sent (admin actions send their own)
            if response and response.strip():
                await self._send_response(message, response)
        
        except Exception as e:
            logger.error(f"AIHandler.handle_ai_command failed: {e}")
            error_msg = f"❌ An error occurred processing your request: {str(e)}"
            await message.channel.send(error_msg)
    
    async def _determine_provider_and_query(self, query: str, force_provider: str) -> tuple[str, str]:
        """Determine which provider to use and clean the query"""
        # If provider is forced, return as-is
        if force_provider:
            return force_provider, query
        
        # Use routing logic to determine provider
        from .routing import should_use_openai_for_search, extract_forced_provider
        
        # Check for forced provider first
        extracted_provider, cleaned_query = extract_forced_provider(query)
        if extracted_provider:
            return extracted_provider, cleaned_query
        
        # Check if query should use OpenAI for search (async)
        try:
            should_use_search = await should_use_openai_for_search(query)
            
            if should_use_search:
                print(f"DEBUG: Routing to SEARCH mode for: '{query[:30]}...'")
                return "openai", query
            else:
                print(f"DEBUG: Routing to CHAT mode for: '{query[:30]}...'")  
                return "direct-ai", query
        except Exception as e:
            print(f"DEBUG: Routing failed, defaulting to OpenAI: {e}")
            # Fallback to OpenAI on any error
            return "openai", query
    
    async def _handle_with_openai(self, message, query: str) -> str:
        """Handle query using OpenAI - either admin actions or search"""
        try:
            # Check if this is an admin command
            if self._is_admin_command(query):
                return await self._handle_admin_command(message, query)
            else:
                # Search command path  
                return await self._handle_search_with_openai(message, query)
            
        except Exception as e:
            logger.error(f"OpenAI handler failed: {e}")
            return f"❌ Error with OpenAI processing: {str(e)}"
    
    async def _handle_search_with_openai(self, message, query: str) -> str:
        """Handle search queries using two-stage parallel summarization with GPT-4o mini"""
        try:
            from ..search.search_pipeline import SearchPipeline
            from ..search.openai_adapter import OpenAISearchProvider
            
            # Build context for search
            context = await self.context_manager.build_full_context(
                query, message.author.id, message.channel.id,
                message.author.display_name, message
            )
            
            # Use GPT-4o mini with full page extraction for two-stage summarization
            openai_provider = OpenAISearchProvider(model="gpt-4o-mini")
            pipeline = SearchPipeline(openai_provider, enable_full_extraction=True)
            
            # Execute search pipeline - this will trigger two-stage summarization
            return await pipeline.search_and_respond(query, context, message.channel)
            
        except Exception as e:
            logger.error(f"Search pipeline failed: {e}")
            return f"❌ Error with search: {str(e)}"
    
    async def _handle_full_search(self, message, query: str) -> str:
        """Handle full page search using GPT-4o directly (single-stage, no summarization)"""
        try:
            from ..search.search_pipeline import SearchPipeline
            from ..search.openai_adapter import OpenAISearchProvider
            
            # Build context for search
            context = await self.context_manager.build_full_context(
                query, message.author.id, message.channel.id,
                message.author.display_name, message
            )
            
            # Use GPT-4o provider with full page extraction but no two-stage summarization
            openai_provider = OpenAISearchProvider(model="gpt-4o")
            pipeline = SearchPipeline(openai_provider, enable_full_extraction=True, debug_channel=None)
            
            # Execute search pipeline - GPT-4o will handle full content directly
            return await pipeline.search_and_respond(query, context, message.channel)
            
        except Exception as e:
            logger.error(f"Full search pipeline failed: {e}")
            return f"❌ Error with full search: {str(e)}"

    async def _handle_direct_ai(self, message, query: str) -> str:
        """Handle direct AI chat without search routing"""
        try:
            print(f"DEBUG: _handle_direct_ai called with query: '{query[:50]}...'")
            
            if not config.has_openai_api():
                return "❌ OpenAI API not configured. Please contact an administrator."
            
            # Build unfiltered context for casual conversation
            print(f"DEBUG: Building context for direct AI...")
            context = await self.context_manager.build_unfiltered_context(
                message.author.id, message.channel.id,
                message.author.display_name, message
            )
            print(f"DEBUG: Context built, length: {len(context)}")
            
            messages = self._build_direct_ai_messages(context, query)
            
            response = await openai_client.create_completion(
                messages=messages,
                model="gpt-4o-mini",
                max_tokens=1000,
                temperature=0.8  # Higher temperature for more creative, fun conversation
            )
            
            # Estimate total prompt tokens
            total_estimated_tokens = self._estimate_tokens(context, query)
            
            return f"**OpenAI GPT-4o Mini AI Response** (~{total_estimated_tokens} tokens):\n\n{response}"
            
        except Exception as e:
            logger.error(f"Direct AI failed: {e}")
            return f"❌ Error with direct AI: {str(e)}"

    async def _handle_with_crafting(self, message, query: str) -> str:
        """Handle query with crafting system using the dedicated crafting module"""
        try:
            from .crafting_module import CraftingProcessor
            
            crafting_processor = CraftingProcessor()
            return await crafting_processor.handle_crafting_request(message, query)
            
        except Exception as e:
            logger.error(f"Crafting system error: {e}")
            return f"❌ **Crafting system error:** {str(e)}"
    
    
    async def _handle_admin_actions(self, message, query: str, response: str, research_context: str = None) -> bool:
        """Handle admin action detection and confirmation"""
        if not is_admin(message.author.id) or not message.guild:
            return False
        
        # Import admin modules
        from ..admin.parser import AdminIntentParser
        from ..admin.actions import AdminActionHandler
        
        parser = AdminIntentParser(self.bot)
        executor = AdminActionHandler(self.bot)
        
        # Parse admin intent from both query and response
        action_type, parameters = await parser.parse_admin_intent(query, message.guild, message.author)
        
        if not action_type:
            return False
        
        # Add research context to parameters if available (for multi-step actions)
        if research_context and action_type == "reorganize_roles":
            parameters["research_context"] = research_context
            logger.debug(f"Added research context to reorganize_roles parameters")
        
        admin_intent = {
            "action_type": action_type,
            "parameters": parameters
        }
        
        
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
        confirmation_text = f"🔧 **Admin Action Detected**\n\n{response}\n\n"
        confirmation_text += "React with ✅ to confirm or ❌ to cancel this action."
        confirmation_text += f"\n\n*Action ID: {action_id}*"
        
        confirmation_msg = await message.channel.send(confirmation_text)
        await confirmation_msg.add_reaction("✅")
        await confirmation_msg.add_reaction("❌")
        
        return True
    
    async def _send_response(self, message, response: str):
        """Send response, handling Discord's message limits and suppressing link previews"""
        from ..utils.message_utils import suppress_link_previews
        
        # Suppress link previews first
        response = suppress_link_previews(response)
        
        if len(response) <= 2000:
            await message.channel.send(response)
        else:
            # Use smart message splitting that preserves formatting
            from ..utils.message_utils import smart_split_message
            import asyncio
            
            chunks = smart_split_message(response, max_length=2000)
            
            # Send chunks with small delays
            for i, chunk in enumerate(chunks):
                if i > 0:
                    await asyncio.sleep(0.5)  # Small delay between chunks
                await message.channel.send(chunk)
    
    async def _handle_rate_limit(self, message):
        """Handle rate limit exceeded"""
        reset_time = self.rate_limiter.get_reset_time(message.author.id)
        if reset_time:
            reset_str = reset_time.strftime("%H:%M:%S")
            rate_msg = f"⏰ **Rate limit exceeded!** You can make {config.AI_RATE_LIMIT_REQUESTS} requests per {config.AI_RATE_LIMIT_WINDOW} seconds.\n\nTry again after {reset_str}."
        else:
            rate_msg = f"⏰ **Rate limit exceeded!** You can make {config.AI_RATE_LIMIT_REQUESTS} requests per {config.AI_RATE_LIMIT_WINDOW} seconds."
        
        await message.channel.send(rate_msg)
    
    async def handle_admin_reaction(self, reaction, user):
        """Handle admin action confirmation reactions"""
        # Delegate to admin processor
        await self.admin_processor.handle_admin_reaction(reaction, user)
        
        # Extract action ID from message
        message_content = reaction.message.content
        if "*Action ID:" not in message_content:
            return
        
        action_id = message_content.split("*Action ID: ")[1].split("*")[0].strip()
        
        if action_id not in self.admin_actions:
            await reaction.message.channel.send("❌ **Admin action expired or not found.**")
            return
        
        action_data = self.admin_actions[action_id]
        original_requester = action_data['message'].author
        
        # Check that the original requester was also an admin
        if not is_admin(original_requester.id):
            await reaction.message.channel.send("❌ **Security Error:** Original command was not from an admin user.")
            return
        
        executor = action_data.get('executor')
        intent = action_data.get('intent')
        
        if str(reaction.emoji) == "✅":
            # Execute the admin action
            try:
                # Handle role reorganization with pre-generated list
                if action_data.get('action_type') == 'role_reorganization_list':
                    role_list = action_data.get('role_list', [])
                    guild = action_data['message'].guild
                    
                    if role_list and guild:
                        await self._execute_role_list_reorganization(reaction.message, guild, role_list, action_data.get('theme', 'Custom Theme'))
                    else:
                        await reaction.message.channel.send("❌ **Error:** No role list or guild found")
                    return
                
                # Handle standard admin actions (delete, kick, ban, timeout, etc.)
                elif action_data.get('action_type') == 'standard_admin' and intent:
                    from ..admin.actions import AdminActionHandler
                    executor = AdminActionHandler(self.bot)
                    
                    result = await executor.execute_admin_action(
                        action_data['message'], 
                        intent['action_type'], 
                        intent['parameters']
                    )
                    await reaction.message.channel.send(f"✅ **Action completed:** {result}")
                
                else:
                    # Fallback for other admin action types
                    if not executor:
                        from ..admin.actions import AdminActionHandler
                        executor = AdminActionHandler(self.bot)
                    
                    if intent:
                        result = await executor.execute_admin_action(
                            action_data['message'], 
                            intent['action_type'], 
                            intent['parameters']
                        )
                        await reaction.message.channel.send(f"✅ **Action completed:** {result}")
                    else:
                        await reaction.message.channel.send("❌ **Error:** No action intent found")
            except Exception as e:
                await reaction.message.channel.send(f"❌ **Action failed:** {str(e)}")
        elif str(reaction.emoji) == "❌":
            await reaction.message.channel.send("❌ **Admin action cancelled.**")
        
        # Clean up
        del self.admin_actions[action_id]
        try:
            await reaction.message.delete()
        except Exception:
            pass
    
    async def _execute_role_list_reorganization(self, message, guild, role_list: list, theme: str):
        """Execute role reorganization by renaming roles one by one from the generated list"""
        try:
            cleaned_roles = self._clean_role_list(role_list)
            if not cleaned_roles:
                await message.channel.send("❌ **Error:** No valid role names found in the generated list")
                return
            
            server_roles = self._get_renameable_roles(guild)
            if not server_roles:
                await message.channel.send("❌ **Error:** No renameable roles found on the server")
                return
            
            await self._perform_role_renaming(message, server_roles, cleaned_roles, theme)
                
        except Exception as e:
            await message.channel.send(f"❌ **Role reorganization failed**: {str(e)}")
            logger.error(f"Role list reorganization error: {e}")
    
    def _is_admin_command(self, query: str) -> bool:
        """Check if query contains admin keywords"""
        from .routing import ADMIN_KEYWORDS
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in ADMIN_KEYWORDS)
    
    async def _handle_admin_command(self, message, query: str) -> str:
        """Handle admin command processing"""
        logger.info(f"Detected admin command, routing to admin processor: {query}")
        admin_response = await self.admin_processor.process_admin_command(message, query)
        
        # Admin processor returns None if no valid admin action found
        if admin_response:
            return admin_response
        else:
            # Admin keywords detected but no valid action - handle as AI response
            response = await self._handle_search_with_openai(message, query)
            # Don't double-label if it already has a label
            if response and not response.startswith("**"):
                return f"**AI Response:** {response}"
            return response
    
    def _build_direct_ai_messages(self, context: str, query: str) -> list:
        """Build message list for direct AI chat"""
        return [
            {"role": "system", "content": f"""[Role]
You are a helpful AI assistant in a Discord server.

[Context Information]
{context}

[Thinking Process]
First, consider the user's intent.  
Then, analyze the relevant context.  
Finally, respond with a clear answer.

[Response Guidelines]
- Use the channel and user context to provide helpful, relevant responses
- Be aware of ongoing conversations and reference them when appropriate
- Apply any global settings consistently
- If replying to a specific message, make sure to address what was asked
- Keep responses concise and conversational"""},
            {"role": "user", "content": f"[Current Message]\n{query}"}
        ]
    
    def _estimate_tokens(self, context: str, query: str) -> int:
        """Estimate total prompt tokens (rough estimation: 4 characters per token)"""
        context_tokens = len(context) // 4
        system_prompt_tokens = 150  # Estimated system prompt structure size
        user_message_tokens = len(query) // 4
        return context_tokens + system_prompt_tokens + user_message_tokens
    
    def _clean_role_list(self, role_list: list) -> list:
        """Clean and validate role names from generated list"""
        cleaned_roles = []
        for role_name in role_list:
            if isinstance(role_name, str):
                cleaned_name = role_name.strip()
                # Remove numbering, bullets, or formatting
                cleaned_name = re.sub(r'^\d+[\.\)\-\s]*', '', cleaned_name)  # Remove "1. " or "1) " etc
                cleaned_name = re.sub(r'^[\-\*\•\s]+', '', cleaned_name)     # Remove bullets
                cleaned_name = cleaned_name.strip()
                
                if cleaned_name and len(cleaned_name) <= 100:  # Discord role name limit
                    cleaned_roles.append(cleaned_name)
        return cleaned_roles
    
    def _get_renameable_roles(self, guild):
        """Get server roles that can be renamed (excluding @everyone and managed roles)"""
        server_roles = [role for role in guild.roles if role.name != "@everyone" and not role.managed]
        server_roles.sort(key=lambda r: r.position, reverse=True)  # Highest position first
        return server_roles
    
    async def _perform_role_renaming(self, message, server_roles: list, cleaned_roles: list, theme: str):
        """Perform the actual role renaming process"""
        # Start the renaming process
        progress_msg = await message.channel.send(
            f"🔄 **Starting role reorganization for {theme}**\n"
            f"Renaming {min(len(server_roles), len(cleaned_roles))} roles..."
        )
        
        renamed_count = 0
        errors = []
        
        # Rename roles one by one
        for i, server_role in enumerate(server_roles):
            if i >= len(cleaned_roles):
                break  # No more names in the list
            
            new_name = cleaned_roles[i]
            old_name = server_role.name
            
            try:
                await server_role.edit(name=new_name, reason=f"Role reorganization: {theme}")
                renamed_count += 1
                
                # Update progress every few renames to avoid spam
                if renamed_count % 3 == 0 or renamed_count == len(cleaned_roles):
                    await progress_msg.edit(content=
                        f"🔄 **Role Reorganization Progress**\n"
                        f"Renamed {renamed_count}/{min(len(server_roles), len(cleaned_roles))} roles\n"
                        f"Latest: `{old_name}` → `{new_name}`"
                    )
                
                # Brief delay to avoid rate limits
                await asyncio.sleep(0.5)
                
            except Exception as e:
                errors.append(f"`{old_name}` → `{new_name}`: {str(e)}")
                logger.error(f"Failed to rename role {old_name} to {new_name}: {e}")
        
        # Send final status
        await self._send_role_reorganization_status(progress_msg, renamed_count, len(server_roles), 
                                                   len(cleaned_roles), errors, theme)
    
    async def _send_role_reorganization_status(self, progress_msg, renamed_count: int, 
                                              total_server_roles: int, total_cleaned_roles: int, 
                                              errors: list, theme: str):
        """Send final status message for role reorganization"""
        if renamed_count > 0:
            status_msg = f"✅ **Role Reorganization Complete**\n"
            status_msg += f"**Theme**: {theme}\n"
            status_msg += f"**Successfully renamed**: {renamed_count} roles\n"
            
            if errors:
                status_msg += f"**Errors**: {len(errors)} roles failed\n"
                # Show first few errors
                error_sample = errors[:3]
                status_msg += "**Sample errors**:\n" + "\n".join(f"• {err}" for err in error_sample)
                if len(errors) > 3:
                    status_msg += f"\n• ... and {len(errors) - 3} more"
            
            await progress_msg.edit(content=status_msg)
        else:
            await progress_msg.edit(content=
                f"❌ **Role reorganization failed**: No roles could be renamed\n"
                f"**Errors**: {len(errors)}"
            )
    
    async def _store_conversation_async(self, user_id: int, channel_id: int, 
                                       user_message: str, ai_response: str, provider: str):
        """Store conversation in vector database asynchronously (background task)"""
        try:
            # Store conversation using context manager
            self.context_manager.add_to_conversation(user_id, channel_id, user_message, ai_response)
            
            # Store bot response in vector database
            if hasattr(self.context_manager, 'vector_enhancer') and self.context_manager.vector_enhancer:
                await self.context_manager.vector_enhancer.vector_db.add_bot_response(
                    channel_id=channel_id,
                    user_id=user_id,
                    response=ai_response,
                    response_type=provider,
                    metadata={"query": user_message[:500]}
                )
        except Exception as e:
            logger.debug(f"Failed to store conversation in background: {e}")