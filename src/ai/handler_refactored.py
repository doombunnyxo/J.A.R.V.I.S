"""
AI Handler - Refactored and Modularized

This is the main AI handler that coordinates between different AI providers
and routes requests appropriately. Crafting functionality has been extracted
to a separate module for better organization.
"""

import asyncio
import re
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Set, Tuple

from discord.ext import commands
import discord
from groq import Groq

from src.config import config
from src.data.persistence import data_manager
from src.admin.permissions import is_admin
from src.admin.admin_processor import AdminProcessor
from src.ai.context_manager import ContextManager
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
        self.groq_client = self._initialize_groq()
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
        
        # Cleanup tasks will be started when bot is ready
        self._cleanup_tasks_started = False
        
        # Instance ID for debugging
        self.instance_id = str(uuid.uuid4())[:8]
        logger.info(f"AIHandler initialized with ID: {self.instance_id}")
    
    def _initialize_groq(self) -> Optional[Groq]:
        """Initialize Groq client if API key is available"""
        if config.has_groq_api():
            return Groq(api_key=config.GROQ_API_KEY)
        logger.warning("No Groq API key found - Groq functionality disabled")
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
            force_provider: Optional forced provider ("groq", "openai", or "crafting")
        """
        try:
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
            provider, cleaned_query = await self._determine_provider_and_query(message, ai_query, force_provider)
            
            # Route to appropriate handler
            if provider == "openai":
                response = await self._handle_with_openai(message, cleaned_query)  # Hybrid by default
            elif provider == "pure-openai":
                response = await self._handle_with_pure_openai(message, cleaned_query)
            elif provider == "perplexity":
                response = await self._handle_with_perplexity(message, cleaned_query)
            elif provider == "pure-perplexity":
                response = await self._handle_with_pure_perplexity(message, cleaned_query)
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
            if response and response.strip():
                await self._send_response(message, response)
        
        except Exception as e:
            logger.error(f"[AIHandler-{self.instance_id}] handle_ai_command failed: {e}")
            error_msg = f"❌ An error occurred processing your request: {str(e)}"
            await message.channel.send(error_msg)
    
    async def _determine_provider_and_query(self, message, query: str, force_provider: str) -> tuple[str, str]:
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
        
        # Check if query should use OpenAI for search
        should_use_openai = should_use_openai_for_search(query)
        
        if should_use_openai:
            return "openai", query
        
        # Default to Groq
        return "groq", query
    
    async def _determine_provider(self, message, query: str, force_provider: str) -> str:
        """Determine which AI provider to use for the query"""
        if force_provider:
            return force_provider
        
        from .routing import should_use_openai_for_search, extract_forced_provider
        
        # Check for forced provider first
        extracted_provider, _ = extract_forced_provider(query)
        if extracted_provider:
            return extracted_provider
        
        # Check if query should use OpenAI for search
        if should_use_openai_for_search(query):
            return "openai"
        
        # Default to Groq
        return "groq"
    
    async def _handle_with_openai(self, message, query: str) -> str:
        """Handle query using OpenAI - either admin actions or hybrid search"""
        try:
            # Check if this is an admin command
            from .routing import ADMIN_KEYWORDS
            query_lower = query.lower()
            is_admin_command = any(keyword in query_lower for keyword in ADMIN_KEYWORDS)
            
            if is_admin_command:
                # Admin command path - use admin processor
                return await self.admin_processor.process_admin_command(message, query)
            else:
                # Search command path  
                return await self._handle_search_with_openai(message, query)
            
        except Exception as e:
            logger.debug(f"OpenAI handler failed: {e}")
            return f"❌ Error with OpenAI processing: {str(e)}"
    
    async def _handle_search_with_openai(self, message, query: str) -> str:
        """Handle search queries using pure OpenAI search pipeline"""
        try:
            from ..search.search_pipeline import SearchPipeline
            from ..search.openai_adapter import OpenAISearchProvider
            
            # Build context for search
            context = await self.context_manager.build_full_context(
                query, message.author.id, message.channel.id,
                message.author.display_name, message
            )
            
            # Use pure OpenAI provider with gpt-4o-mini
            openai_provider = OpenAISearchProvider(model="gpt-4o-mini")
            pipeline = SearchPipeline(openai_provider)
            
            # Execute search pipeline with OpenAI only
            response = await pipeline.search_and_respond(query, context)
            
            return response
            
        except Exception as e:
            logger.debug(f"Search pipeline failed: {e}")
            return f"❌ Error with search: {str(e)}"

    async def _handle_with_perplexity(self, message, query: str) -> str:
        """Handle query using Perplexity search adapter and unified pipeline"""
        try:
            from ..search.search_pipeline import SearchPipeline
            from ..search.perplexity_adapter import PerplexitySearchProvider
            
            if not config.has_perplexity_api():
                return "❌ Perplexity API not configured. Please contact an administrator."
            
            # Build context for Perplexity
            context = await self.context_manager.build_full_context(
                query, message.author.id, message.channel.id,
                message.author.display_name, message
            )
            
            # Create Perplexity provider and search pipeline
            perplexity_provider = PerplexitySearchProvider()
            pipeline = SearchPipeline(perplexity_provider)
            
            # Execute the unified search pipeline
            response = await pipeline.search_and_respond(query, context)
            
            return response
            
        except Exception as e:
            logger.debug(f"Perplexity search pipeline failed: {e}")
            return f"❌ Error with Perplexity search: {str(e)}"
    
    async def _handle_with_pure_openai(self, message, query: str) -> str:
        """Handle query using pure OpenAI (not hybrid) search adapter"""
        try:
            from ..search.search_pipeline import SearchPipeline
            from ..search.openai_adapter import OpenAISearchProvider
            
            if not config.has_openai_api():
                return "❌ OpenAI API not configured. Please contact an administrator."
            
            # Build context for OpenAI
            context = await self.context_manager.build_full_context(
                query, message.author.id, message.channel.id,
                message.author.display_name, message
            )
            
            # Create pure OpenAI provider and search pipeline
            openai_provider = OpenAISearchProvider()
            pipeline = SearchPipeline(openai_provider)
            
            # Execute the unified search pipeline with pure OpenAI
            response = await pipeline.search_and_respond(query, context)
            
            return response
            
        except Exception as e:
            logger.debug(f"Pure OpenAI search pipeline failed: {e}")
            return f"❌ Error with pure OpenAI search: {str(e)}"

    async def _handle_with_pure_perplexity(self, message, query: str) -> str:
        """Handle query using pure Perplexity (not hybrid) search adapter"""
        try:
            from ..search.search_pipeline import SearchPipeline
            from ..search.perplexity_adapter import PerplexitySearchProvider
            
            if not config.has_perplexity_api():
                return "❌ Perplexity API not configured. Please contact an administrator."
            
            # Build context for Perplexity
            context = await self.context_manager.build_full_context(
                query, message.author.id, message.channel.id,
                message.author.display_name, message
            )
            
            # Create pure Perplexity provider and search pipeline
            perplexity_provider = PerplexitySearchProvider()
            pipeline = SearchPipeline(perplexity_provider)
            
            # Execute the unified search pipeline with pure Perplexity
            response = await pipeline.search_and_respond(query, context)
            
            return response
            
        except Exception as e:
            logger.debug(f"Pure Perplexity search pipeline failed: {e}")
            return f"❌ Error with pure Perplexity search: {str(e)}"
    
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
        logger.debug(f"_handle_with_crafting called with query: '{query}'")
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
        
        # Build full context (includes conversation, channel, and permanent context)
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
- Role reorganization (reorganize all server roles based on themes/contexts)

IMPORTANT: When you receive ANY admin command (like "kick user", "delete messages", "reorganize roles", etc.), you MUST respond with the confirmation format below. This triggers the reaction-based confirmation system.

When you detect an administrative request, respond by clearly stating what action you understood. DO NOT ask for text-based confirmation. The system will automatically handle confirmation.

MANDATORY FORMAT for admin commands:
I understand you want to [ACTION]. [Brief description of what will happen]

Examples:
- "kick spammer" → I understand you want to kick the spammer. They will be removed from the server.
- "delete messages from John" → I understand you want to delete messages from John. I'll remove their recent messages.
- "rename role Moderator to Super Mod" → I understand you want to rename the Moderator role to Super Mod.
- "reorganize roles Dune theme" → I understand you want to reorganize all server roles based on Dune universe factions. I'll rename roles using appropriate faction names and hierarchy.

CRITICAL: Always use "I understand you want to [ACTION]" format for ANY admin command to trigger the confirmation system.

Be concise and clear about what the action will do."""

            parts.append(admin_instructions)
        
        return "\n\n".join(parts)
    
    def _build_claude_admin_system_message(self, context: str, user_id: int) -> str:
        """Build system message for Claude admin processing"""
        parts = []
        
        if context:
            parts.append(f"RELEVANT CONTEXT:\\n{context}")
            parts.append("=" * 50)
        
        core_instructions = """You are Claude, an AI assistant specialized in Discord server administration and general helpfulness.

Your capabilities include:

1. **General Knowledge**: Answer questions using your training data and any relevant context provided above.

2. **Discord Server Management** (Admin only): Help with server administration including user moderation, role management, channel management, and message cleanup.

The relevant context section above contains information pertinent to the current query, including any research results that should inform your admin actions. Use this context to provide more personalized and informed responses.

IMPORTANT: If the context includes research results about themes, organizations, or hierarchies, use that information to better understand and process admin requests that reference those topics."""

        parts.append(core_instructions)
        
        # Add admin capabilities if user is admin
        if is_admin(user_id):
            admin_instructions = """Additional admin capabilities:

- User moderation (kick, ban, timeout/mute users)
- Role management (add/remove roles from users, rename roles)  
- Channel management (create/delete channels)
- Message cleanup (bulk delete messages, including from specific users)
- Nickname changes
- Intelligent role reorganization using research context when provided

When you detect an administrative request, respond by clearly stating what action you understood. DO NOT ask for text-based confirmation. The system will automatically handle confirmation.

Use this format:
I understand you want to [ACTION]. [Brief description of what will happen]

Examples:
- "kick that spammer" → I understand you want to kick [user]. They will be removed from the server.
- "delete John's messages" → I understand you want to delete messages from John. I'll remove their recent messages.
- "rename role Moderator to Super Mod" → I understand you want to rename the Moderator role to Super Mod.
- "rename all roles to match Dune factions" → I understand you want to reorganize all server roles to match Dune universe factions. I'll rename roles using appropriate faction names and hierarchy.

RESEARCH-ENHANCED ACTIONS: When context includes research about themes, organizations, or hierarchies, use that information to understand and confirm thematic role reorganization requests. Always acknowledge that you can perform the action based on the research provided.

Be concise and clear about what the action will do."""

            parts.append(admin_instructions)
        
        return "\n\n".join(parts)
    
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
        intent = action_data.get('intent')  # Optional for new Perplexity flow
        
        if str(reaction.emoji) == "✅":
            # Execute the admin action
            try:
                # Handle Perplexity-based role reorganization with pre-generated list
                if action_data.get('action_type') == 'role_reorganization_list':
                    role_list = action_data.get('role_list', [])
                    guild = action_data['message'].guild
                    
                    if role_list and guild:
                        await self._execute_role_list_reorganization(reaction.message, guild, role_list, action_data.get('theme', 'Custom Theme'))
                    else:
                        await reaction.message.channel.send("❌ **Error:** No role list or guild found")
                    return
                
                # Check if this is a research-enhanced action that needs final command generation
                elif action_data.get('research_context') and action_data.get('original_query'):
                    # Step 1: Use Claude to generate specific admin command text
                    claude_command = await self._claude_generate_specific_admin_command(
                        action_data['message'], 
                        action_data['original_query'], 
                        action_data['research_context']
                    )
                    
                    if claude_command and not claude_command.startswith("❌"):
                        # Step 2: Pass Claude's command through the admin parser (same as if Groq generated it)
                        from ..admin.parser import AdminIntentParser
                        from ..admin.actions import AdminActionHandler
                        
                        parser = AdminIntentParser(self.bot)
                        executor = AdminActionHandler(self.bot)
                        
                        # Parse the command that Claude generated
                        parsed_action_type, parsed_parameters = await parser.parse_admin_intent(
                            claude_command, action_data['message'].guild, action_data['message'].author
                        )
                        
                        if parsed_action_type:
                            # Step 3: Add research context to parsed parameters
                            if parsed_parameters:
                                parsed_parameters['research_context'] = action_data['research_context']
                            
                            # Step 4: Execute through normal admin action flow
                            result = await executor.execute_admin_action(
                                action_data['message'], 
                                parsed_action_type, 
                                parsed_parameters
                            )
                            await reaction.message.channel.send(f"✅ **Action completed:** {result}")
                        else:
                            await reaction.message.channel.send(f"❌ **Command not recognized:** {claude_command}")
                    else:
                        await reaction.message.channel.send(f"❌ **Command generation failed:** {claude_command}")
                
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
            # Clean and validate the role list
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
            
            if not cleaned_roles:
                await message.channel.send("❌ **Error:** No valid role names found in the generated list")
                return
            
            # Get server roles (excluding @everyone and managed roles)
            server_roles = [role for role in guild.roles if role.name != "@everyone" and not role.managed]
            server_roles.sort(key=lambda r: r.position, reverse=True)  # Highest position first
            
            if not server_roles:
                await message.channel.send("❌ **Error:** No renameable roles found on the server")
                return
            
            # Start the renaming process
            progress_msg = await message.channel.send(f"🔄 **Starting role reorganization for {theme}**\n"
                                                    f"Renaming {min(len(server_roles), len(cleaned_roles))} roles...")
            
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
                        await progress_msg.edit(content=f"🔄 **Role Reorganization Progress**\n"
                                              f"Renamed {renamed_count}/{min(len(server_roles), len(cleaned_roles))} roles\n"
                                              f"Latest: `{old_name}` → `{new_name}`")
                    
                    # Brief delay to avoid rate limits
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    errors.append(f"`{old_name}` → `{new_name}`: {str(e)}")
                    logger.debug(f"Failed to rename role {old_name} to {new_name}: {e}")
            
            # Final status message
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
                await progress_msg.edit(content=f"❌ **Role reorganization failed**: No roles could be renamed\n"
                                              f"**Errors**: {len(errors)}")
                
        except Exception as e:
            await message.channel.send(f"❌ **Role reorganization failed**: {str(e)}")
            logger.debug(f"Role list reorganization error: {e}")