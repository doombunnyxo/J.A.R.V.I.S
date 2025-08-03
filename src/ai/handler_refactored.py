"""
Refactored AI Handler - Clean and modular implementation
Handles hybrid Groq + Claude AI routing with improved structure
"""

import re
from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import defaultdict, deque

from groq import Groq
from ..config import config
from ..data.persistence import data_manager
from ..admin.permissions import is_admin
from ..admin.actions import AdminActionHandler
from ..admin.parser import AdminIntentParser
from ..search.claude import claude_search_analysis, claude_optimize_search_query
from ..search.google import perform_google_search
from ..utils.message_utils import smart_split_message
from .routing import should_use_claude_for_search, extract_forced_provider, extract_claude_model
from .context_manager import ContextManager
from ..crafting.handler import CraftingHandler


class RateLimiter:
    """Simple rate limiter for AI requests"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.user_requests: Dict[int, deque] = defaultdict(deque)
    
    def is_allowed(self, user_id: int) -> bool:
        """Check if user can make a request"""
        now = datetime.now()
        user_queue = self.user_requests[user_id]
        
        # Remove old requests
        while user_queue and user_queue[0] < now - timedelta(seconds=self.window_seconds):
            user_queue.popleft()
        
        # Check limit
        if len(user_queue) < self.max_requests:
            user_queue.append(now)
            return True
        
        return False
    
    def get_reset_time(self, user_id: int) -> Optional[datetime]:
        """Get when rate limit resets"""
        user_queue = self.user_requests[user_id]
        if user_queue:
            return user_queue[0] + timedelta(seconds=self.window_seconds)
        return None


class AIHandler:
    """
    Refactored AI Handler with clean separation of concerns
    
    Responsibilities:
    - Route queries to appropriate AI (Groq vs Claude)
    - Manage conversation context across AIs
    - Handle admin actions with confirmations
    - Rate limiting and error handling
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.groq_client = self._initialize_groq()
        
        # Rate limiting
        self.rate_limiter = RateLimiter(
            config.AI_RATE_LIMIT_REQUESTS,
            config.AI_RATE_LIMIT_WINDOW
        )
        
        # Admin handling
        self.admin_handler = AdminActionHandler(bot)
        self.intent_parser = AdminIntentParser(bot)
        self.pending_admin_actions = {}
        
        # Context management
        self.context_manager = ContextManager(self.groq_client)
        
        # Crafting system
        self.crafting_handler = CraftingHandler(bot)
        
        # Provider tracking
        self.conversation_providers = {}  # Track which AI was used per conversation
        
        # Message deduplication
        self.processed_messages = set()
        self.max_processed_messages = 100
        
        print(f"DEBUG: AIHandler initialized successfully")
    
    def _initialize_groq(self) -> Optional[Groq]:
        """Initialize Groq client"""
        try:
            if config.has_groq_api():
                client = Groq(api_key=config.GROQ_API_KEY)
                print("DEBUG: Groq client initialized successfully")
                return client
            else:
                print("WARNING: Groq API key not configured")
                return None
        except Exception as e:
            print(f"ERROR: Groq initialization failed: {e}")
            return None
    
    def _cleanup_processed_messages(self):
        """Clean up old processed message IDs"""
        if len(self.processed_messages) > self.max_processed_messages:
            old_messages = list(self.processed_messages)[:self.max_processed_messages // 2]
            for msg_id in old_messages:
                self.processed_messages.discard(msg_id)
    
    def _cleanup_stale_admin_actions(self):
        """Clean up expired admin actions"""
        current_time = datetime.now()
        cleanup_threshold = 5 * 60  # 5 minutes
        
        stale_users = [
            user_id for user_id, action_data in self.pending_admin_actions.items()
            if "timestamp" in action_data and 
            (current_time - action_data["timestamp"]).total_seconds() > cleanup_threshold
        ]
        
        for user_id in stale_users:
            print(f"DEBUG: Cleaning up stale admin action for user {user_id}")
            self.pending_admin_actions.pop(user_id, None)
    
    async def handle_ai_command(self, message, ai_query: str, force_provider: str = None):
        """
        Main entry point for AI command processing
        
        Args:
            message: Discord message object
            ai_query: User's query string  
            force_provider: Optional forced provider ("groq" or "claude")
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
            await message.channel.send(f'AI request failed: {str(e)}')
    
    async def _determine_provider_and_query(self, message, query: str, force_provider: str) -> tuple[str, str]:
        """Determine which provider to use and return cleaned query"""
        # Check for forced provider
        if force_provider:
            if force_provider in ["claude", "perplexity"]:
                provider = "claude"
            elif force_provider == "crafting":
                provider = "crafting"
            else:
                provider = "groq"
            print(f"DEBUG: Forced to use {provider}")
            return provider, query
        
        # Check for provider syntax in query
        forced_provider, cleaned_query = extract_forced_provider(query)
        if forced_provider:
            print(f"DEBUG: Extracted forced provider: {forced_provider}")
            return forced_provider, cleaned_query
        
        # Use original logic for automatic routing
        provider = await self._determine_provider(message, query, None)
        return provider, query
    
    async def _determine_provider(self, message, query: str, force_provider: str) -> str:
        """Determine which AI provider to use"""
        # Check for forced provider
        if force_provider:
            if force_provider in ["claude", "perplexity"]:
                provider = "claude"
            elif force_provider == "crafting":
                provider = "crafting"
            else:
                provider = "groq"
            print(f"DEBUG: Forced to use {provider}")
            return provider
        
        # Check for provider syntax in query
        forced_provider, cleaned_query = extract_forced_provider(query)
        if forced_provider:
            print(f"DEBUG: Extracted forced provider: {forced_provider}")
            return forced_provider
        
        # Check if this is a follow-up conversation
        conversation_key = self.context_manager.get_conversation_key(
            message.author.id, message.channel.id
        )
        
        is_followup = self.context_manager.is_context_fresh(
            message.author.id, message.channel.id
        )
        
        # Route based on query content
        use_claude = should_use_claude_for_search(query)
        
        if is_followup:
            previous_provider = self.conversation_providers.get(conversation_key)
            if use_claude:
                if previous_provider != "claude":
                    print(f"DEBUG: Follow-up switching to Claude (was {previous_provider})")
                else:
                    print(f"DEBUG: Follow-up continuing with Claude")
            else:
                if previous_provider != "groq":
                    print(f"DEBUG: Follow-up switching to Groq (was {previous_provider})")
                else:
                    print(f"DEBUG: Follow-up continuing with Groq")
        else:
            if use_claude:
                print(f"DEBUG: New conversation - routing to Claude for web search")
            else:
                print(f"DEBUG: New conversation - routing to Groq for chat/admin")
        
        # Track provider choice
        provider = "claude" if use_claude else "groq"
        self.conversation_providers[conversation_key] = provider
        
        return provider
    
    async def _handle_with_claude(self, message, query: str) -> str:
        """Handle query with Claude (web search)"""
        try:
            if not config.has_anthropic_api():
                return "Claude API not configured - web search unavailable"
            
            # Get user context
            context = await self.context_manager.build_full_context(
                query, message.author.id, message.channel.id, 
                message.author.display_name, message
            )
            
            # Extract model if admin specified one
            model, cleaned_query = extract_claude_model(query, message.author.id)
            
            # Optimize search query
            optimized_query = await claude_optimize_search_query(cleaned_query, context)
            
            # Perform Google search
            search_results = await self._perform_google_search(optimized_query)
            
            if not search_results or "Search failed" in search_results:
                return f"Web search unavailable: {search_results}"
            
            print(f"DEBUG: Calling Claude API with model: {model}")
            print(f"DEBUG: Context length: {len(context)} chars")
            
            # Call Claude for analysis
            response = await claude_search_analysis(cleaned_query, search_results, context)
            
            return self._suppress_link_previews(response)
        
        except Exception as e:
            return f"Error with Claude search: {str(e)}"
    
    async def _handle_with_groq(self, message, query: str) -> str:
        """Handle query with Groq (chat/admin)"""
        try:
            if not self.groq_client:
                return "Groq API not configured"
            
            # Get user context
            context = await self._build_groq_context(message, query)
            
            # Build system message
            system_message = self._build_groq_system_message(context, message.author.id)
            
            # Call Groq API
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": query}
            ]
            
            async with message.channel.typing():
                completion = self.groq_client.chat.completions.create(
                    messages=messages,
                    model=config.AI_MODEL,
                    max_tokens=config.AI_MAX_TOKENS,
                    temperature=config.AI_TEMPERATURE
                )
                
                response = completion.choices[0].message.content or "No response generated."
                
                # Check for admin actions
                admin_handled = await self._handle_admin_actions(message, query, response)
                if admin_handled:
                    return ""  # Admin handler sent its own message
                
                return response
        
        except Exception as e:
            return f"Error processing with Groq: {str(e)}"
    
    async def _handle_with_crafting(self, message, query: str) -> str:
        """Handle query with crafting system"""
        print(f"DEBUG: _handle_with_crafting called with query: '{query}'")
        try:
            # Use the existing crafting handler to process the query
            result = await self.crafting_handler._interpret_recipe_request(query)
            
            if isinstance(result, tuple) and len(result) == 2:
                item_name, quantity = result
                
                # Import crafting functions
                from dune_crafting import calculate_materials, get_recipe_info, format_materials_list
                
                try:
                    # Get the recipe information
                    recipe_info = get_recipe_info(item_name)
                    if not recipe_info:
                        return f"❌ **Recipe not found for:** {item_name}\n\nUse `@bot craft: list` to see available items."
                    
                    # Calculate total materials needed
                    total_materials = calculate_materials(item_name, quantity)
                    
                    # Format the response
                    response = f"🔧 **Crafting Recipe: {item_name}**\n\n"
                    
                    if quantity > 1:
                        response += f"**Quantity:** {quantity}\n\n"
                    
                    # Add recipe details
                    response += f"**Direct Recipe:**\n"
                    response += f"• **Station:** {recipe_info.get('station', 'Unknown')}\n"
                    
                    if 'intel_requirement' in recipe_info:
                        intel = recipe_info['intel_requirement']
                        response += f"• **Intel:** {intel.get('points', 0)} points"
                        if intel.get('total_spent', 0) > 0:
                            response += f" ({intel['total_spent']} total required)\n"
                        else:
                            response += "\n"
                    
                    if recipe_info.get('ingredients'):
                        response += f"• **Ingredients:** {', '.join([f'{qty}x {item}' for item, qty in recipe_info['ingredients'].items()])}\n\n"
                    
                    # Add total materials breakdown
                    response += f"**Total Materials Needed:**\n"
                    response += format_materials_list(total_materials)
                    
                    if 'description' in recipe_info:
                        response += f"\n**Description:** {recipe_info['description']}"
                    
                    return response
                    
                except Exception as crafting_error:
                    return f"❌ **Crafting Error:** {str(crafting_error)}"
            
            else:
                return f"❌ **Could not parse crafting request:** {query}\n\nExample: `@bot craft: sandbike mk3 with boost`"
            
        except Exception as e:
            return f"Error processing crafting request: {str(e)}"
    
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
        
        if message.author.id in self.pending_admin_actions:
            return False
        
        # Parse admin intent
        action_type, parameters = await self.intent_parser.parse_admin_intent(
            query, message.guild, message.author
        )
        
        if not action_type:
            return False
        
        self._cleanup_stale_admin_actions()
        
        # Store pending action
        self.pending_admin_actions[message.author.id] = {
            "action_type": action_type,
            "parameters": parameters,
            "message_id": message.id,
            "original_message": message,
            "timestamp": datetime.now()
        }
        
        print(f"DEBUG: Admin action detected: {action_type}")
        
        # Add confirmation to response
        if not any(keyword in response for keyword in ["Admin Action", "React with", "✅", "❌"]):
            response += f"\\n\\n[ADMIN] Action detected: {action_type}\\nReact with ✅ to proceed or ❌ to cancel."
        
        # Send message with reactions
        sent_msg = await message.channel.send(response)
        await sent_msg.add_reaction('✅')
        await sent_msg.add_reaction('❌')
        
        # Store confirmation message
        self.pending_admin_actions[message.author.id]["confirmation_message"] = sent_msg
        
        return True
    
    async def handle_admin_confirmation(self, reaction, user):
        """Handle admin reaction confirmations"""
        if user.bot or not is_admin(user.id):
            return
        
        # Find matching pending action
        for admin_user_id, action_data in self.pending_admin_actions.items():
            if (admin_user_id == user.id and 
                "confirmation_message" in action_data and 
                reaction.message.id == action_data["confirmation_message"].id):
                
                emoji = str(reaction.emoji)
                
                if emoji == '✅':
                    # Execute admin action
                    action_data = self.pending_admin_actions.pop(admin_user_id)
                    original_message = action_data.get("original_message", reaction.message)
                    
                    admin_response = await self.admin_handler.execute_admin_action(
                        original_message, action_data["action_type"], action_data["parameters"]
                    )
                    
                    await reaction.message.channel.send(admin_response)
                    
                elif emoji == '❌':
                    # Cancel admin action
                    self.pending_admin_actions.pop(admin_user_id, None)
                    await reaction.message.channel.send("❌ **Admin action cancelled.**")
                
                # Clear reactions
                try:
                    await reaction.message.clear_reactions()
                except:
                    pass
                
                break
    
    async def _perform_google_search(self, query: str) -> str:
        """Perform Google search"""
        try:
            if not config.has_google_search():
                return "Google search not configured"
            
            # Import here to avoid circular imports
            from googleapiclient.discovery import build
            
            service = build("customsearch", "v1", developerKey=config.GOOGLE_API_KEY)
            result = service.cse().list(q=query, cx=config.GOOGLE_SEARCH_ENGINE_ID, num=10).execute()
            
            if 'items' not in result:
                return f"No search results found for: {query}"
            
            search_results = f"Current web search results for '{query}':\\n\\n"
            
            for i, item in enumerate(result['items'][:10], 1):
                title = item['title']
                link = item['link']
                snippet = item.get('snippet', 'No description available')
                
                search_results += f"{i}. **{title}**\\n"
                search_results += f"   {snippet[:400]}...\\n"
                search_results += f"   Source: <{link}>\\n\\n"
            
            return search_results
        
        except Exception as e:
            return f"Search failed: {str(e)}"
    
    def _suppress_link_previews(self, text: str) -> str:
        """Wrap URLs in angle brackets to suppress Discord previews"""
        import re
        url_pattern = r'(?<!\\<)(https?://[^\\s\\>]+)(?!\\>)'
        return re.sub(url_pattern, r'<\\1>', text)
    
    async def _get_channel_context(self, channel, limit: int = None) -> str:
        """Get recent channel messages for context"""
        if limit is None:
            limit = config.CHANNEL_CONTEXT_LIMIT
        
        try:
            messages = []
            async for message in channel.history(limit=limit, oldest_first=False):
                if message.author.bot:
                    continue
                
                content = f"{message.author.display_name}: {message.content}"
                messages.append(content)
            
            messages.reverse()
            
            if messages:
                display_limit = config.CHANNEL_CONTEXT_DISPLAY
                return "Recent channel messages:\\n" + "\\n".join(messages[-display_limit:])
            return ""
        except Exception as e:
            print(f"Error fetching channel context: {e}")
            return ""
    
    async def _handle_rate_limit(self, message):
        """Handle rate limited users"""
        reset_time = self.rate_limiter.get_reset_time(message.author.id)
        wait_seconds = int((reset_time - datetime.now()).total_seconds()) if reset_time else 60
        await message.channel.send(
            f'⏰ **Rate Limited**: Please wait {wait_seconds} seconds before making another AI request.'
        )
    
    async def _send_response(self, message, response: str):
        """Send response with smart message splitting"""
        if not response:
            return
        
        message_chunks = smart_split_message(response)
        for chunk in message_chunks:
            await message.channel.send(chunk)