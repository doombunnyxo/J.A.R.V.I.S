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
from src.ai.context_manager import ContextManager
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
        
        # Rate limiting
        self.rate_limiter = RateLimiter(
            max_requests=config.AI_RATE_LIMIT_REQUESTS,
            window_seconds=config.AI_RATE_LIMIT_WINDOW
        )
        
        # Track processed messages to prevent duplicates
        self.processed_messages: Set[int] = set()
        self.admin_actions: Dict[str, dict] = {}
        
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
                # Admin command path - route to Perplexity-based admin handler
                return await self._handle_admin_with_openai(message, query)
            else:
                # Search command path  
                return await self._handle_search_with_openai(message, query)
            
        except Exception as e:
            logger.debug(f"OpenAI handler failed: {e}")
            return f"❌ Error with OpenAI processing: {str(e)}"
    
    async def _handle_admin_with_openai(self, message, query: str) -> str:
        """Handle admin commands - new Perplexity-based flow"""
        try:
            # Route all admin commands to new Perplexity-based system
            return await self._handle_admin_with_perplexity(message, query)
                
        except Exception as e:
            logger.debug(f"Admin processing failed: {e}")
            return f"❌ Error with admin processing: {str(e)}"
    
    async def _handle_admin_with_perplexity(self, message, query: str) -> str:
        """Handle admin commands using Perplexity for analysis and execution"""
        try:
            if not config.has_perplexity_api():
                return "❌ Perplexity API not configured for admin commands."
            
            # Step 1: Use Groq to analyze the admin command and detect if it needs research
            admin_analysis = await self._groq_analyze_admin_command(message, query)
            
            # Program-level fallback: Force search for role reorganization patterns
            force_search = self._should_force_search_for_roles(query)
            if force_search and not admin_analysis.get('needs_search'):
                admin_analysis = {
                    "needs_search": True,
                    "theme": self._extract_theme_from_query(query),
                    "search_query": f"{self._extract_theme_from_query(query)} hierarchy factions groups roles characters"
                }
            
            if admin_analysis.get('needs_search'):
                # Step 2: If it needs research, get search results
                search_results = await self._perform_google_search_for_admin(admin_analysis['search_query'])
                
                # Step 3: Use Perplexity to process search results and generate role list  
                role_list = await self._perplexity_generate_role_list(query, search_results, admin_analysis['theme'])
                
                if role_list and not role_list.startswith("❌"):
                    # Step 4: Create confirmation message with the role list
                    return await self._create_admin_confirmation_with_roles(message, query, role_list, admin_analysis)
                else:
                    return role_list or "❌ Failed to generate role list"
            else:
                # Handle non-search admin commands through existing system
                return await self._handle_standard_admin_command(message, query)
                
        except Exception as e:
            logger.debug(f"Perplexity admin processing failed: {e}")
            return f"❌ Error with Perplexity admin processing: {str(e)}"
    
    def _should_force_search_for_roles(self, query: str) -> bool:
        """Program-level detection of role reorganization patterns that need search"""
        query_lower = query.lower()
        
        # Patterns that definitely need search
        role_reorganization_patterns = [
            'rename roles to match',
            'rename all roles to',
            'rename server roles to',
            'reorganize roles based on',
            'make roles fit',
            'roles like',
            'rename roles to',
            'update roles to match',
            'change roles to match',
            'set roles to match'
        ]
        
        # Theme indicators
        theme_indicators = [
            'factions from',
            'characters from', 
            'based on',
            'to match',
            'from the',
            'like in',
            'similar to'
        ]
        
        has_role_pattern = any(pattern in query_lower for pattern in role_reorganization_patterns)
        has_theme_indicator = any(indicator in query_lower for indicator in theme_indicators)
        
        return has_role_pattern or (has_theme_indicator and 'role' in query_lower)
    
    def _extract_theme_from_query(self, query: str) -> str:
        """Extract theme name from role reorganization query"""
        query_lower = query.lower()
        
        # Look for common patterns
        import re
        
        # Pattern: "match factions from the [THEME]"
        match = re.search(r'(?:from|based on|like|match|to)\s+(?:the\s+)?([^,.!?]+?)(?:\s|$)', query_lower)
        if match:
            theme = match.group(1).strip()
            # Clean up common words
            theme = re.sub(r'\b(?:factions|characters|hierarchy|roles|groups)\b', '', theme).strip()
            if theme:
                return theme.title()
        
        # Fallback: look for quoted content
        quoted_matches = re.findall(r'["\']([^"\']+)["\']', query)
        if quoted_matches:
            return quoted_matches[0].title()
        
        return "Custom Theme"
    
    async def _groq_analyze_admin_command(self, message, query: str) -> dict:
        """Use Groq to analyze admin command and detect if it needs internet search"""
        try:
            if not config.has_groq_api():
                return {"needs_search": False, "action_type": "error", "error": "Groq not configured"}
            
            system_message = """You are analyzing Discord admin commands to determine if they need internet research.

You must respond with valid JSON in one of these two formats ONLY:

FORMAT 1 - For role reorganization (ALWAYS needs search):
{
  "needs_search": true,
  "theme": "detected theme name",
  "search_query": "optimized search query"
}

FORMAT 2 - For basic admin commands (no search needed):
{
  "needs_search": false,
  "action_type": "standard_admin"  
}

CRITICAL RULES:
1. ANY command about renaming/reorganizing roles = FORMAT 1 (needs_search: true)
2. Commands with themes/franchises/shows = FORMAT 1 (needs_search: true)  
3. Only basic commands (kick, ban, timeout) = FORMAT 2 (needs_search: false)

Role reorganization keywords that ALWAYS use FORMAT 1:
- rename, reorganize, change, update, fix + roles
- roles + match, like, based on, fit
- factions, characters, hierarchy

Examples:
- "rename all server roles to match factions from the winx club" → {"needs_search": true, "theme": "Winx Club", "search_query": "Winx Club factions groups hierarchy characters roles"}
- "kick that spammer" → {"needs_search": false, "action_type": "standard_admin"}
- "reorganize roles like Star Wars" → {"needs_search": true, "theme": "Star Wars", "search_query": "Star Wars hierarchy ranks roles imperial rebel alliance"}"""
            
            # Use the existing Groq client
            completion = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Analyze this admin command: {query}"}
                ],
                max_tokens=200,
                temperature=0.1
            )
            
            groq_response = completion.choices[0].message.content.strip()
            
            # Parse JSON response
            import json
            try:
                return json.loads(groq_response)
            except json.JSONDecodeError:
                return {"needs_search": False, "action_type": "error", "error": f"Invalid JSON: {groq_response}"}
                
        except Exception as e:
            return {"needs_search": False, "action_type": "error", "error": str(e)}
    
    async def _perplexity_analyze_admin_command(self, message, query: str) -> dict:
        """Use Perplexity to analyze admin command and detect if it needs internet search"""
        try:
            import aiohttp
            
            headers = {
                "Authorization": f"Bearer {config.PERPLEXITY_API_KEY}",
                "Content-Type": "application/json"
            }
            
            system_message = """You are analyzing Discord admin commands to determine if they need internet research.

You must respond with valid JSON in one of these two formats ONLY:

FORMAT 1 - For role reorganization (ALWAYS needs search):
{
  "needs_search": true,
  "theme": "detected theme name",
  "search_query": "optimized search query"
}

FORMAT 2 - For basic admin commands (no search needed):
{
  "needs_search": false,
  "action_type": "standard_admin"  
}

CRITICAL RULES:
1. ANY command about renaming/reorganizing roles = FORMAT 1 (needs_search: true)
2. Commands with themes/franchises/shows = FORMAT 1 (needs_search: true)  
3. Only basic commands (kick, ban, timeout) = FORMAT 2 (needs_search: false)

Role reorganization keywords that ALWAYS use FORMAT 1:
- rename, reorganize, change, update, fix + roles
- roles + match, like, based on, fit
- factions, characters, hierarchy

Valid admin actions include:
- Role management (rename, reorganize, add, remove roles)
- User moderation (kick, ban, timeout, mute)
- Message management (delete, purge, clear)
- Channel management (create, delete channels)

Examples:
- "rename all server roles to match factions from the winx club" → {"needs_search": true, "theme": "Winx Club", "search_query": "Winx Club factions groups hierarchy characters roles"}
- "kick that spammer" → {"needs_search": false, "action_type": "standard_admin"}
- "reorganize roles like Star Wars" → {"needs_search": true, "theme": "Star Wars", "search_query": "Star Wars hierarchy ranks roles imperial rebel alliance"}"""
            
            payload = {
                "model": "sonar",  # Correct Perplexity model name
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Analyze this admin command: {query}"}
                ],
                "max_tokens": 200,
                "temperature": 0.1
            }
            
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post("https://api.perplexity.ai/chat/completions",
                                       headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        perplexity_response = result["choices"][0]["message"]["content"].strip()
                        
                        # Parse JSON response
                        import json
                        try:
                            return json.loads(perplexity_response)
                        except json.JSONDecodeError:
                            return {"needs_search": False, "action_type": "parse_error"}
                    else:
                        raise Exception(f"Perplexity API error {response.status}")
                        
        except Exception as e:
            logger.debug(f"Perplexity admin analysis failed: {e}")
            return {"needs_search": False, "action_type": "error"}
    
    async def _perform_google_search_for_admin(self, search_query: str) -> str:
        """Perform Google search and return results for admin processing"""
        try:
            if not config.has_google_search():
                return "Google search not configured"
            
            from googleapiclient.discovery import build
            
            service = build("customsearch", "v1", developerKey=config.GOOGLE_API_KEY)
            result = service.cse().list(q=search_query, cx=config.GOOGLE_SEARCH_ENGINE_ID, num=10).execute()
            
            if 'items' not in result:
                return f"No search results found for: {search_query}"
            
            search_results = f"Search results for '{search_query}':\n\n"
            
            for i, item in enumerate(result['items'][:10], 1):
                title = item['title']
                snippet = item.get('snippet', 'No description available')
                search_results += f"{i}. {title}\n{snippet[:300]}...\n\n"
            
            return search_results
            
        except Exception as e:
            return f"Search failed: {str(e)}"
    
    async def _perplexity_generate_role_list(self, original_query: str, search_results: str, theme: str) -> str:
        """Use Perplexity to generate a clean list of role names from search results"""
        try:
            import aiohttp
            
            headers = {
                "Authorization": f"Bearer {config.PERPLEXITY_API_KEY}",
                "Content-Type": "application/json"
            }
            
            system_message = """You are generating Discord server role names based on search results about a specific theme.

Based on the search results provided, generate a list of suitable role names for a Discord server. The roles should reflect the hierarchy and terminology from the theme.

CRITICAL: Respond with ONLY a simple list format, one role per line, no other text, explanations, or formatting:

Role Name 1
Role Name 2  
Role Name 3
etc.

Make the roles hierarchical (from highest to lowest authority) and appropriate for Discord server management."""
            
            payload = {
                "model": "sonar",  # Correct Perplexity model name
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Original request: {original_query}\nTheme: {theme}\n\nSearch Results:\n{search_results[:5000]}\n\nGenerate role list:"}  # Truncate search results
                ],
                "max_tokens": 300,
                "temperature": 0.2
            }
            
            # Debug: Check payload size
            import json
            payload_size = len(json.dumps(payload))
            logger.debug(f"Perplexity payload size: {payload_size} characters")
            logger.debug(f"Search results size: {len(search_results)} characters")
            
            timeout = aiohttp.ClientTimeout(total=20)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post("https://api.perplexity.ai/chat/completions",
                                       headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        role_list = result["choices"][0]["message"]["content"].strip()
                        return role_list
                    else:
                        # Get error details
                        try:
                            error_body = await response.text()
                            logger.debug(f"Perplexity 400 error body: {error_body}")
                        except Exception:
                            pass
                        raise Exception(f"Perplexity API error {response.status}: {error_body if 'error_body' in locals() else 'Unknown error'}")
                        
        except Exception as e:
            logger.debug(f"Perplexity role generation failed: {e}")
            return f"❌ Error generating role list: {str(e)}"
    
    async def _create_admin_confirmation_with_roles(self, message, original_query: str, role_list: str, admin_analysis: dict) -> str:
        """Create Discord confirmation message with role list and reactions"""
        try:
            import uuid
            import time
            
            # Generate unique action ID
            action_id = str(uuid.uuid4())[:8]
            
            # Build confirmation message showing the role list
            confirmation_text = f"⚠️ **ADMIN ACTION: Role Reorganization**\n\n"
            confirmation_text += f"**Theme**: {admin_analysis.get('theme', 'Custom Theme')}\n"
            confirmation_text += f"**Action**: Rename all server roles to match this theme\n\n"
            confirmation_text += "**Proposed Role Names** (from highest to lowest):\n"
            confirmation_text += f"```\n{role_list}\n```\n\n"
            confirmation_text += "⚠️ **WARNING**: This will rename ALL existing server roles!\n\n"
            confirmation_text += "React with ✅ to confirm or ❌ to cancel this action.\n"
            confirmation_text += f"*Action ID: {action_id}*"
            
            # Store action data for reaction handling
            self.admin_actions[action_id] = {
                'action_type': 'role_reorganization_list',
                'role_list': role_list.strip().split('\n'),  # Convert to list
                'theme': admin_analysis.get('theme', 'Custom Theme'),
                'message': message,
                'timestamp': time.time(),
                'original_query': original_query
            }
            
            # Send confirmation message
            confirmation_msg = await message.channel.send(confirmation_text)
            await confirmation_msg.add_reaction("✅")
            await confirmation_msg.add_reaction("❌")
            
            return ""  # No additional response needed
            
        except Exception as e:
            logger.debug(f"Admin confirmation creation failed: {e}")
            return f"❌ Error creating admin confirmation: {str(e)}"
    
    async def _handle_standard_admin_command(self, message, query: str) -> str:
        """Handle non-search admin commands through admin parser with confirmation"""
        try:
            # Use admin parser to interpret command and extract parameters
            from ..admin.parser import AdminIntentParser
            
            parser = AdminIntentParser(self.bot, message.channel)
            
            # Parse the admin command
            action_type, parameters = await parser.parse_admin_intent(
                query, message.guild, message.author
            )
            
            # Debug info will come from the parser itself
            
            if action_type:
                # Create confirmation message for admin action
                return await self._create_standard_admin_confirmation(message, query, action_type, parameters)
            else:
                return "❌ **Command not recognized as admin action**"
                
        except Exception as e:
            return f"❌ Error with standard admin command: {str(e)}"
    
    async def _create_standard_admin_confirmation(self, message, original_query: str, action_type: str, parameters: dict) -> str:
        """Create confirmation message for standard admin actions"""
        try:
            import uuid
            import time
            
            # Generate unique action ID
            action_id = str(uuid.uuid4())[:8]
            
            # Build confirmation message based on action type
            confirmation_text = f"⚠️ **ADMIN ACTION: {action_type.replace('_', ' ').title()}**\n\n"
            confirmation_text += f"**Command**: {original_query}\n"
            confirmation_text += f"**Action**: {self._describe_admin_action(action_type, parameters)}\n\n"
            confirmation_text += "⚠️ **WARNING**: This action cannot be undone!\n\n"
            confirmation_text += "React with ✅ to confirm or ❌ to cancel this action.\n"
            confirmation_text += f"*Action ID: {action_id}*"
            
            # Store action data for reaction handling
            self.admin_actions[action_id] = {
                'action_type': 'standard_admin',
                'intent': {
                    'action_type': action_type,
                    'parameters': parameters
                },
                'message': message,
                'timestamp': time.time(),
                'original_query': original_query
            }
            
            # Send confirmation message
            confirmation_msg = await message.channel.send(confirmation_text)
            await confirmation_msg.add_reaction("✅")
            await confirmation_msg.add_reaction("❌")
            
            return ""  # No additional response needed
            
        except Exception as e:
            return f"❌ Error creating admin confirmation: {str(e)}"
    
    def _describe_admin_action(self, action_type: str, parameters: dict) -> str:
        """Generate human-readable description of admin action"""
        if action_type == "kick_user":
            user = parameters.get('user')
            return f"Kick {user.display_name if user else 'user'} from the server"
        elif action_type == "ban_user":
            user = parameters.get('user')
            return f"Ban {user.display_name if user else 'user'} from the server"
        elif action_type == "timeout_user":
            user = parameters.get('user')
            duration = parameters.get('duration', 60)
            return f"Timeout {user.display_name if user else 'user'} for {duration} minutes"
        elif action_type == "bulk_delete":
            limit = parameters.get('limit', 1)
            user_filter = parameters.get('user_filter')
            channel = parameters.get('channel')
            desc = f"Delete {limit} messages"
            if user_filter:
                desc += f" from {user_filter.display_name}"
            if channel:
                desc += f" in #{channel.name}"
            else:
                desc += " in this channel"
            return desc
        elif action_type == "add_role":
            user = parameters.get('user')
            role = parameters.get('role')
            return f"Add role '{role.name if role else 'unknown'}' to {user.display_name if user else 'user'}"
        elif action_type == "remove_role":
            user = parameters.get('user')
            role = parameters.get('role')
            return f"Remove role '{role.name if role else 'unknown'}' from {user.display_name if user else 'user'}"
        elif action_type == "rename_role":
            role = parameters.get('role')
            new_name = parameters.get('new_name')
            return f"Rename role '{role.name if role else 'unknown'}' to '{new_name}'"
        else:
            return f"Execute {action_type.replace('_', ' ')}"
    
    def _detect_research_needed(self, query: str) -> bool:
        """Detect if an admin command needs research before execution"""
        query_lower = query.lower()
        
        # Keywords that indicate research is needed
        research_indicators = [
            # Theme-based reorganization
            'fit a theme', 'based on theme', 'themed', 'theme of', 'style of',
            'like star wars', 'like harry potter', 'like marvel', 'like disney',
            'like lotr', 'like lord of the rings', 'like game of thrones',
            'like minecraft', 'like pokemon', 'like anime', 'like fantasy',
            'medieval style', 'sci-fi style', 'cyberpunk style', 'steampunk style',
            'military style', 'corporate style', 'academic style', 'gaming style',
            # Context-based commands that need research
            'organize roles based on', 'rename roles to match', 'make roles fit',
            'structure roles like', 'model roles after', 'base roles on',
            'appropriate for a', 'suitable for a', 'fitting for a',
            # Commands that reference external knowledge
            'research and', 'find out about', 'look up information',
            'based on what you find', 'according to', 'using information about'
        ]
        
        # Role reorganization with thematic context
        role_reorganize_themes = [
            'reorganize roles', 'fix role names', 'improve role names',
            'rename all roles', 'update all roles', 'change all roles'
        ]
        
        # Check if it's a role reorganization command with thematic elements
        has_role_command = any(keyword in query_lower for keyword in role_reorganize_themes)
        has_research_indicator = any(indicator in query_lower for indicator in research_indicators)
        
        # Also check for specific franchise/theme mentions
        theme_keywords = [
            'star wars', 'harry potter', 'marvel', 'dc comics', 'disney',
            'lord of the rings', 'lotr', 'hobbit', 'game of thrones', 'got',
            'minecraft', 'pokemon', 'anime', 'fantasy', 'sci-fi', 'cyberpunk',
            'steampunk', 'medieval', 'military', 'corporate', 'academic',
            'gaming', 'esports', 'twitch', 'youtube', 'streaming'
        ]
        
        has_theme_mention = any(theme in query_lower for theme in theme_keywords)
        
        needs_research = (has_role_command and (has_research_indicator or has_theme_mention))
        
        logger.debug(f"Research detection - has_role_command: {has_role_command}, has_research_indicator: {has_research_indicator}, has_theme_mention: {has_theme_mention}, needs_research: {needs_research}")
        
        return needs_research
    
    async def _handle_multi_step_admin_action(self, message, query: str) -> str:
        """Handle multi-step admin actions that require research"""
        try:
            logger.debug(f"Handling multi-step admin action: {query}")
            
            # Step 1: Extract the theme/context that needs research
            research_query = self._extract_research_query(query)
            logger.debug(f"Extracted research query: {research_query}")
            
            # Step 2: Use the search pipeline to gather information
            research_context = await self._perform_research(message, research_query)
            logger.debug(f"Research context length: {len(research_context) if research_context else 0}")
            
            # Step 3: Process the original admin command with the research context
            return await self._execute_admin_with_research(message, query, research_context)
            
        except Exception as e:
            logger.debug(f"Multi-step admin action failed: {e}")
            return f"❌ Error with multi-step admin processing: {str(e)}"
    
    def _extract_research_query(self, query: str) -> str:
        """Extract what needs to be researched from the admin query"""
        query_lower = query.lower()
        
        # Look for specific themes/topics mentioned
        theme_patterns = [
            r'(?:like|based on|fit(?:ting)? (?:a |the )?|themed (?:around |after )?|style of |model(?:ed)? after )([^,.!?]+)',
            r'(?:star wars|harry potter|marvel|dc comics|disney|lord of the rings|lotr|hobbit|game of thrones|got|minecraft|pokemon|anime|fantasy|sci-fi|cyberpunk|steampunk|medieval|military|corporate|academic|gaming|esports)',
            r'(?:organize|structure|model) roles (?:like|after|based on) ([^,.!?]+)',
            r'(?:appropriate|suitable|fitting) for (?:a |an )?([^,.!?]+) (?:server|community|guild)'
        ]
        
        import re
        for pattern in theme_patterns:
            match = re.search(pattern, query_lower)
            if match:
                if len(match.groups()) > 0:
                    theme = match.group(1).strip()
                else:
                    theme = match.group(0).strip()
                
                # Clean up the extracted theme
                theme = re.sub(r'\b(?:the|a|an|for|like|based|on|fit|fitting|style|of|model|after)\b', '', theme).strip()
                theme = re.sub(r'\s+', ' ', theme).strip()
                
                if len(theme) > 3:  # Valid theme found
                    if 'role' in theme:
                        # If "role" appears in theme, it's likely the full context
                        return f"{theme} hierarchy and terminology"
                    else:
                        return f"{theme} hierarchy roles and organizational structure"
        
        # Fallback: look for quoted content or key terms
        quoted_matches = re.findall(r'["\']([^"\']+)["\']', query)
        for quoted in quoted_matches:
            if len(quoted) > 5 and 'role' not in quoted.lower():
                return f"{quoted} hierarchy and organizational structure"
        
        # Default fallback
        return "organizational hierarchy and role structure for community management"
    
    async def _perform_research(self, message, research_query: str) -> str:
        """Use the existing hybrid search pipeline to research the topic for admin purposes"""
        try:
            from ..search.search_pipeline import SearchPipeline
            from ..search.hybrid_search_provider import HybridSearchProvider
            
            logger.debug(f"Performing admin research using hybrid search for: {research_query}")
            
            # Build admin-specific research context (simpler than user context)
            admin_research_context = f"""ADMIN RESEARCH CONTEXT:
This search is being performed to gather information for Discord server role reorganization.
Focus on organizational hierarchy, ranks, titles, and terminology that would be appropriate for Discord server roles.
The goal is to find authentic terminology and structure that can be adapted for server administration."""
            
            # Create hybrid provider for research
            hybrid_provider = HybridSearchProvider()
            pipeline = SearchPipeline(hybrid_provider)
            
            # Execute search using the existing hybrid pipeline
            research_results = await pipeline.search_and_respond(research_query, admin_research_context)
            
            logger.debug(f"Admin research completed using hybrid search, results length: {len(research_results) if research_results else 0}")
            return research_results
            
        except Exception as e:
            logger.debug(f"Admin research via hybrid search failed: {e}")
            return f"Error researching {research_query}: {str(e)}"
    
    async def _execute_admin_with_research(self, message, original_query: str, research_context: str) -> str:
        """Execute the admin command with research context - direct confirmation approach"""
        try:
            logger.debug(f"Using direct confirmation approach for research-enhanced admin action")
            
            # Step 1: Use OpenAI to analyze research and create confirmation message
            confirmation_info = await self._openai_analyze_research_for_confirmation(message, original_query, research_context)
            
            if not confirmation_info or confirmation_info.get('error'):
                return confirmation_info.get('error', "❌ Failed to analyze research for confirmation")
            
            logger.debug(f"OpenAI analyzed research, creating direct confirmation")
            
            # Step 2: Send confirmation message directly to Discord (no LLM generation)
            return await self._send_direct_admin_confirmation(message, original_query, confirmation_info, research_context)
            
        except Exception as e:
            logger.debug(f"Direct confirmation admin execution failed: {e}")
            return f"❌ Error with direct confirmation admin processing: {str(e)}"
    
    async def _openai_analyze_research_for_confirmation(self, message, original_query: str, research_context: str) -> dict:
        """Use OpenAI to analyze research and create confirmation info (not LLM-generated message)"""
        try:
            if not config.has_openai_api():
                return {"error": "❌ OpenAI API not configured"}
            
            # Build context for OpenAI's analysis
            user_context = await self.context_manager.build_full_context(
                original_query, message.author.id, message.channel.id,
                message.author.display_name, message
            )
            
            import aiohttp
            
            headers = {
                "Authorization": f"Bearer {config.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            }
            
            # System message for research analysis and confirmation planning
            system_message = f"""You are Claude, analyzing research results to plan a Discord admin action confirmation.

USER CONTEXT:
{user_context}

RESEARCH CONTEXT:
{research_context}

Your task is to analyze the research and provide structured information for a confirmation message.

Based on the user's request and research context, provide:
1. ACTION_TYPE: The type of admin action (e.g., "reorganize_roles")
2. ACTION_DESCRIPTION: Brief description of what will happen
3. RESEARCH_SUMMARY: Key findings from research (2-3 bullet points)
4. THEME_NAME: The theme/context name for the action

FORMAT your response as JSON:
{{
  "action_type": "reorganize_roles",
  "action_description": "Reorganize all server roles based on Dune universe factions",
  "research_summary": [
    "House Atreides: Noble leadership house",
    "House Harkonnen: Rival political house", 
    "Fremen: Desert warriors and survivors"
  ],
  "theme_name": "Dune Universe Factions"
}}

Respond with ONLY the JSON, no other text."""
            
            payload = {
                "model": "gpt-4o-mini",
                "max_tokens": 300,
                "temperature": 0.1,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"User request: {original_query}\n\nAnalyze the research and create confirmation info."}
                ]
            }
            
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post("https://api.openai.com/v1/chat/completions", 
                                       headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        openai_response = result["choices"][0]["message"]["content"].strip()
                        
                        # Parse JSON response
                        import json
                        try:
                            confirmation_info = json.loads(openai_response)
                            return confirmation_info
                        except json.JSONDecodeError as e:
                            return {"error": f"❌ Failed to parse OpenAI response as JSON: {str(e)}"}
                    else:
                        raise Exception(f"OpenAI API error {response.status}: {await response.text()}")
                        
        except Exception as e:
            logger.debug(f"Claude research analysis failed: {e}")
            return {"error": f"❌ Error analyzing research: {str(e)}"}
    
    async def _send_direct_admin_confirmation(self, message, original_query: str, confirmation_info: dict, research_context: str) -> str:
        """Send admin confirmation directly to Discord and set up reaction handling"""
        try:
            # Generate unique action ID
            import uuid
            action_id = str(uuid.uuid4())[:8]
            
            # Build confirmation message (not LLM generated)
            confirmation_text = f"🔧 **Admin Action: {confirmation_info['theme_name']}**\n\n"
            confirmation_text += f"**Action**: {confirmation_info['action_description']}\n\n"
            
            if confirmation_info.get('research_summary'):
                confirmation_text += "**Based on research findings**:\n"
                for bullet in confirmation_info['research_summary']:
                    confirmation_text += f"• {bullet}\n"
                confirmation_text += "\n"
            
            confirmation_text += "React with ✅ to confirm or ❌ to cancel this action.\n"
            confirmation_text += f"*Action ID: {action_id}*"
            
            # Store action data for when user reacts
            self.admin_actions[action_id] = {
                'intent': {
                    'action_type': confirmation_info['action_type'],
                    'parameters': {
                        'context': confirmation_info['theme_name'],
                        'guild': message.guild,
                        'research_context': research_context
                    }
                },
                'message': message,
                'timestamp': time.time(),
                'original_query': original_query,
                'research_context': research_context
            }
            
            # Send confirmation message directly
            confirmation_msg = await message.channel.send(confirmation_text)
            await confirmation_msg.add_reaction("✅")
            await confirmation_msg.add_reaction("❌")
            
            # Also send a visible confirmation that the system is working
            await message.channel.send("✅ **Admin confirmation sent above** - react to proceed or cancel.")
            
            return ""  # No additional response needed
            
        except Exception as e:
            logger.debug(f"Direct confirmation sending failed: {e}")
            return f"❌ Error sending confirmation: {str(e)}"
    
    async def _claude_generate_specific_admin_command(self, message, original_query: str, research_context: str) -> str:
        """Use Claude to generate a specific admin command text that the parser can interpret"""
        try:
            if not config.has_openai_api():
                return "❌ OpenAI API not configured"
            
            # This method is called AFTER user clicks ✅, so we generate a specific command
            user_context = await self.context_manager.build_full_context(
                original_query, message.author.id, message.channel.id,
                message.author.display_name, message
            )
            
            import aiohttp
            
            headers = {
                "Authorization": f"Bearer {config.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            }
            
            # System message for generating specific admin commands
            system_message = f"""You are Claude, generating a specific admin command that the program can parse and execute.

USER CONTEXT:
{user_context}

RESEARCH CONTEXT:
{research_context}

The user has CONFIRMED they want to proceed with this admin action. Your task is to generate a specific command text that the admin parser can interpret.

Based on the original request and research context, generate a command that follows this pattern:
"reorganize roles [description based on research]"

The description should incorporate key findings from the research context to guide the role reorganization.

EXAMPLES:
- "reorganize roles Dune universe factions"
- "reorganize roles Star Wars Imperial hierarchy" 
- "reorganize roles medieval guild structure"

The parser will detect "reorganize roles" and use the description to understand the context.

Respond with ONLY the specific command, no other text."""
            
            payload = {
                "model": "gpt-4o-mini",
                "max_tokens": 100,
                "temperature": 0.1,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"User confirmed request: {original_query}\n\nGenerate specific admin command based on research."}
                ]
            }
            
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post("https://api.openai.com/v1/chat/completions", 
                                       headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        command = result["choices"][0]["message"]["content"].strip()
                        return command
                    else:
                        raise Exception(f"OpenAI API error {response.status}: {await response.text()}")
                        
        except Exception as e:
            logger.debug(f"Claude command generation failed: {e}")
            return f"❌ Error generating command: {str(e)}"
    
    async def _claude_generate_admin_commands(self, message, original_query: str, research_context: str) -> str:
        """Use Claude to analyze research and generate specific admin commands for Groq"""
        try:
            if not config.has_openai_api():
                return "❌ OpenAI API not configured"
            
            # Build context for Claude's command generation
            user_context = await self.context_manager.build_full_context(
                original_query, message.author.id, message.channel.id,
                message.author.display_name, message
            )
            
            import aiohttp
            
            headers = {
                "Authorization": f"Bearer {config.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            }
            
            # Specialized system message for command generation
            system_message = f"""You are Claude, an AI assistant that analyzes research and generates specific Discord admin commands.

USER CONTEXT:
{user_context}

RESEARCH CONTEXT:
{research_context}

Your task is to analyze the research context and generate a specific admin command that Groq can execute. Based on the user's request and the research provided, create a clear reorganize_roles command.

INSTRUCTIONS:
1. Analyze the research context to understand the hierarchy and terminology
2. Generate a single, specific admin command that captures the user's intent
3. ALWAYS start with exactly "reorganize roles" 
4. Include a brief description that incorporates the research findings
5. Keep it concise but informative

COMMAND FORMAT: "reorganize roles [brief description based on research]"

EXAMPLES:
- "reorganize roles Star Wars Imperial hierarchy"
- "reorganize roles Dune universe factions"  
- "reorganize roles medieval guild structure"
- "reorganize roles corporate hierarchy"

IMPORTANT: Start with exactly "reorganize roles" followed by a space, then the theme description.

Respond with ONLY the specific admin command, nothing else."""
            
            payload = {
                "model": "gpt-4o-mini",
                "max_tokens": 200,
                "temperature": 0.1,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"User request: {original_query}\n\nGenerate a specific admin command based on the research context provided above."}
                ]
            }
            
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post("https://api.openai.com/v1/chat/completions", 
                                       headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        command = result["choices"][0]["message"]["content"].strip()
                        return command
                    else:
                        raise Exception(f"OpenAI API error {response.status}: {await response.text()}")
                        
        except Exception as e:
            logger.debug(f"Claude command generation failed: {e}")
            return f"❌ Error generating admin commands: {str(e)}"
    
    
    
    async def _handle_search_with_openai(self, message, query: str) -> str:
        """Handle search queries using the existing hybrid search pipeline"""
        try:
            from ..search.search_pipeline import SearchPipeline
            from ..search.hybrid_search_provider import HybridSearchProvider
            
            # Build context for search
            context = await self.context_manager.build_full_context(
                query, message.author.id, message.channel.id,
                message.author.display_name, message
            )
            
            # Use the existing hybrid provider (OpenAI optimization + Perplexity analysis)
            hybrid_provider = HybridSearchProvider()
            pipeline = SearchPipeline(hybrid_provider)
            
            # Execute the existing unified search pipeline
            response = await pipeline.search_and_respond(query, context)
            
            return response
            
        except Exception as e:
            logger.debug(f"Hybrid search pipeline failed: {e}")
            return f"❌ Error with hybrid search: {str(e)}"

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
            rate_msg = f"⏰ **Rate limit exceeded!** You can make {config.AI_RATE_LIMIT_REQUESTS} requests per {config.AI_RATE_LIMIT_WINDOW} seconds.\n\nTry again after {reset_str}."
        else:
            rate_msg = f"⏰ **Rate limit exceeded!** You can make {config.AI_RATE_LIMIT_REQUESTS} requests per {config.AI_RATE_LIMIT_WINDOW} seconds."
        
        await message.channel.send(rate_msg)
    
    async def handle_admin_reaction(self, reaction, user):
        """Handle admin action confirmation reactions"""
        # Check that the person reacting is an admin
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