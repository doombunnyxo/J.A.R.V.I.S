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
        
        # Cleanup tasks will be started when bot is ready
        self._cleanup_tasks_started = False
        
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
            force_provider: Optional forced provider ("groq", "claude", or "crafting")
        """
        try:
            # Prevent duplicate processing
            if message.id in self.processed_messages:
                print(f"DEBUG: Message {message.id} already processed")
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
            if provider == "claude":
                response = await self._handle_with_claude(message, cleaned_query)  # Hybrid by default
            elif provider == "pure-claude":
                response = await self._handle_with_pure_claude(message, cleaned_query)
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
            print(f"DEBUG: Force provider: {force_provider}")
            return force_provider, query
        
        # Use routing logic to determine provider
        from .routing import should_use_claude_for_search, extract_forced_provider
        
        # Check for forced provider first
        extracted_provider, cleaned_query = extract_forced_provider(query)
        if extracted_provider:
            print(f"DEBUG: Extracted provider: {extracted_provider}")
            return extracted_provider, cleaned_query
        
        # Check if query should use Claude for search
        should_use_claude = should_use_claude_for_search(query)
        print(f"DEBUG: Query: '{query[:50]}...' -> should_use_claude: {should_use_claude}")
        
        if should_use_claude:
            return "claude", query
        
        # Default to Groq
        return "groq", query
    
    async def _determine_provider(self, message, query: str, force_provider: str) -> str:
        """Determine which AI provider to use for the query"""
        if force_provider:
            return force_provider
        
        from .routing import should_use_claude_for_search, extract_forced_provider
        
        # Check for forced provider first
        extracted_provider, _ = extract_forced_provider(query)
        if extracted_provider:
            return extracted_provider
        
        # Check if query should use Claude for search
        if should_use_claude_for_search(query):
            return "claude"
        
        # Default to Groq
        return "groq"
    
    async def _handle_with_claude(self, message, query: str) -> str:
        """Handle query using Claude - either admin actions or hybrid search"""
        try:
            # Check if this is an admin command
            from .routing import ADMIN_KEYWORDS
            query_lower = query.lower()
            is_admin_command = any(keyword in query_lower for keyword in ADMIN_KEYWORDS)
            
            if is_admin_command:
                return await self._handle_admin_with_claude(message, query)
            else:
                return await self._handle_search_with_claude(message, query)
            
        except Exception as e:
            print(f"DEBUG: Claude handler failed: {e}")
            return f"❌ Error with Claude processing: {str(e)}"
    
    async def _handle_admin_with_claude(self, message, query: str) -> str:
        """Handle admin commands - Claude interprets, Groq executes"""
        try:
            if not config.has_anthropic_api():
                return "❌ Claude API not configured. Please contact an administrator."
            
            # Check if this admin command requires research/multi-step processing
            needs_research = self._detect_research_needed(query)
            
            if needs_research:
                # Multi-step: Research + Claude interpretation + Groq execution
                return await self._handle_multi_step_admin_action(message, query)
            else:
                # Single-step: Claude interpretation + Groq execution
                return await self._handle_single_step_admin_action_with_groq(message, query)
                
        except Exception as e:
            print(f"DEBUG: Claude admin processing failed: {e}")
            return f"❌ Error with Claude admin processing: {str(e)}"
    
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
        
        print(f"DEBUG: Research detection - has_role_command: {has_role_command}, has_research_indicator: {has_research_indicator}, has_theme_mention: {has_theme_mention}, needs_research: {needs_research}")
        
        return needs_research
    
    async def _handle_multi_step_admin_action(self, message, query: str) -> str:
        """Handle multi-step admin actions that require research"""
        try:
            print(f"DEBUG: Handling multi-step admin action: {query}")
            
            # Step 1: Extract the theme/context that needs research
            research_query = self._extract_research_query(query)
            print(f"DEBUG: Extracted research query: {research_query}")
            
            # Step 2: Use the search pipeline to gather information
            research_context = await self._perform_research(message, research_query)
            print(f"DEBUG: Research context length: {len(research_context) if research_context else 0}")
            
            # Step 3: Process the original admin command with the research context
            return await self._execute_admin_with_research(message, query, research_context)
            
        except Exception as e:
            print(f"DEBUG: Multi-step admin action failed: {e}")
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
            
            print(f"DEBUG: Performing admin research using hybrid search for: {research_query}")
            
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
            
            print(f"DEBUG: Admin research completed using hybrid search, results length: {len(research_results) if research_results else 0}")
            return research_results
            
        except Exception as e:
            print(f"DEBUG: Admin research via hybrid search failed: {e}")
            return f"Error researching {research_query}: {str(e)}"
    
    async def _execute_admin_with_research(self, message, original_query: str, research_context: str) -> str:
        """Execute the admin command with research context - Claude plans, Groq executes"""
        try:
            print(f"DEBUG: Using Claude+Groq hybrid approach for research-enhanced admin action")
            
            # Step 1: Use Claude to analyze research and generate specific admin commands
            admin_commands = await self._claude_generate_admin_commands(message, original_query, research_context)
            
            if not admin_commands or admin_commands.startswith("❌"):
                return admin_commands or "❌ Failed to generate admin commands from research"
            
            print(f"DEBUG: Claude generated admin commands: {admin_commands}")
            
            # Step 2: Use Groq to execute the specific admin commands
            return await self._groq_execute_admin_command(message, admin_commands, research_context)
            
        except Exception as e:
            print(f"DEBUG: Hybrid admin execution failed: {e}")
            return f"❌ Error with hybrid admin processing: {str(e)}"
    
    async def _claude_generate_admin_commands(self, message, original_query: str, research_context: str) -> str:
        """Use Claude to analyze research and generate specific admin commands for Groq"""
        try:
            if not config.has_anthropic_api():
                return "❌ Claude API not configured"
            
            # Build context for Claude's command generation
            user_context = await self.context_manager.build_full_context(
                original_query, message.author.id, message.channel.id,
                message.author.display_name, message
            )
            
            import aiohttp
            
            headers = {
                "x-api-key": config.ANTHROPIC_API_KEY,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
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
                "model": "claude-3-5-haiku-20241022",
                "max_tokens": 200,
                "temperature": 0.1,
                "messages": [
                    {"role": "user", "content": f"User request: {original_query}\n\nGenerate a specific admin command based on the research context provided above."}
                ]
            }
            
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post("https://api.anthropic.com/v1/messages", 
                                       headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        command = result["content"][0]["text"].strip()
                        return command
                    else:
                        raise Exception(f"Claude API error {response.status}: {await response.text()}")
                        
        except Exception as e:
            print(f"DEBUG: Claude command generation failed: {e}")
            return f"❌ Error generating admin commands: {str(e)}"
    
    
    async def _handle_single_step_admin_action_with_groq(self, message, query: str) -> str:
        """Handle single-step admin actions - Claude interprets, Groq executes"""
        try:
            print(f"DEBUG: Single-step admin action - Claude interprets, Groq executes")
            
            # Step 1: Use Claude to interpret and generate specific admin command
            admin_command = await self._claude_interpret_admin_request(message, query)
            
            if not admin_command or admin_command.startswith("❌"):
                return admin_command or "❌ Failed to interpret admin request"
            
            print(f"DEBUG: Claude interpreted command: {admin_command}")
            
            # Step 2: Use Groq to execute the admin command
            return await self._groq_execute_admin_command(message, admin_command)
            
        except Exception as e:
            print(f"DEBUG: Single-step admin processing failed: {e}")
            return f"❌ Error with single-step admin processing: {str(e)}"
    
    async def _claude_interpret_admin_request(self, message, query: str) -> str:
        """Use Claude to interpret admin requests and convert to specific commands"""
        try:
            if not config.has_anthropic_api():
                return "❌ Claude API not configured"
            
            # Build context for Claude's interpretation
            user_context = await self.context_manager.build_full_context(
                query, message.author.id, message.channel.id,
                message.author.display_name, message
            )
            
            import aiohttp
            
            headers = {
                "x-api-key": config.ANTHROPIC_API_KEY,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            # System message for interpreting admin requests
            system_message = f"""You are Claude, an AI assistant that interprets Discord admin requests and converts them to specific commands.

USER CONTEXT:
{user_context}

Your task is to interpret the user's admin request and convert it to a clear, specific command that can be executed.

INSTRUCTIONS:
1. Identify the admin action type from the user's request
2. Convert to a simple, direct command using exact parser keywords
3. Keep commands short and use the exact trigger phrases

COMMAND PATTERNS (use these exactly):
- "kick [target]" for removing users
- "ban [target]" for banning users  
- "timeout [target]" for muting users
- "delete messages" for message cleanup
- "rename role [old] to [new]" for single role renames
- "reorganize roles [theme]" for bulk role reorganization

EXAMPLES:
- "kick that spammer" → "kick spammer"
- "delete John's messages" → "delete messages from John"
- "rename moderator role to super mod" → "rename role Moderator to Super Mod"
- "reorganize all roles for Star Wars" → "reorganize roles Star Wars theme"

Respond with ONLY the specific admin command, nothing else."""
            
            payload = {
                "model": "claude-3-5-haiku-20241022",
                "max_tokens": 150,
                "temperature": 0.1,
                "messages": [
                    {"role": "user", "content": f"Admin request to interpret: {query}"}
                ]
            }
            
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post("https://api.anthropic.com/v1/messages", 
                                       headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        command = result["content"][0]["text"].strip()
                        return command
                    else:
                        raise Exception(f"Claude API error {response.status}: {await response.text()}")
                        
        except Exception as e:
            print(f"DEBUG: Claude admin interpretation failed: {e}")
            return f"❌ Error interpreting admin request: {str(e)}"
    
    async def _groq_execute_admin_command(self, message, admin_command: str, research_context: str = None) -> str:
        """Use Groq to execute admin commands (single method for both simple and research-enhanced)"""
        try:
            if not self.groq_client:
                return "❌ Groq API not configured"
            
            # Build context for Groq
            user_context = await self.context_manager.build_full_context(
                admin_command, message.author.id, message.channel.id,
                message.author.display_name, message
            )
            
            # Add research context if provided
            if research_context:
                enhanced_context = f"{user_context}\n\nRESEARCH CONTEXT FOR ROLE REORGANIZATION:\n{research_context}"
                print(f"DEBUG: Using enhanced context with research for Groq")
            else:
                enhanced_context = user_context
                print(f"DEBUG: Using standard context for Groq")
            
            # Build system message for Groq admin execution
            system_message = self._build_groq_system_message(enhanced_context, message.author.id)
            
            # Get response from Groq
            completion = self.groq_client.chat.completions.create(
                model=config.AI_MODEL,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": admin_command}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            response = completion.choices[0].message.content.strip()
            
            print(f"DEBUG: Groq admin response: {response}")
            
            # Handle admin actions using the existing Groq system (which works)
            print(f"DEBUG: About to call _handle_admin_actions with command: '{admin_command}'")
            if await self._handle_admin_actions(message, admin_command, response, research_context):
                print(f"DEBUG: Admin action WAS detected and handled")
                return ""  # Admin action handled, no additional response needed
            else:
                print(f"DEBUG: Admin action was NOT detected - returning response to user")
            
            return response
            
        except Exception as e:
            print(f"DEBUG: Groq admin execution failed: {e}")
            return f"❌ Error executing admin command with Groq: {str(e)}"
    
    async def _handle_search_with_claude(self, message, query: str) -> str:
        """Handle search queries using the existing hybrid search pipeline"""
        try:
            from ..search.search_pipeline import SearchPipeline
            from ..search.hybrid_search_provider import HybridSearchProvider
            
            # Build context for search
            context = await self.context_manager.build_full_context(
                query, message.author.id, message.channel.id,
                message.author.display_name, message
            )
            
            # Use the existing hybrid provider (Claude optimization + Perplexity analysis)
            hybrid_provider = HybridSearchProvider()
            pipeline = SearchPipeline(hybrid_provider)
            
            # Execute the existing unified search pipeline
            response = await pipeline.search_and_respond(query, context)
            
            return response
            
        except Exception as e:
            print(f"DEBUG: Hybrid search pipeline failed: {e}")
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
            print(f"DEBUG: Perplexity search pipeline failed: {e}")
            return f"❌ Error with Perplexity search: {str(e)}"
    
    async def _handle_with_pure_claude(self, message, query: str) -> str:
        """Handle query using pure Claude (not hybrid) search adapter"""
        try:
            from ..search.search_pipeline import SearchPipeline
            from ..search.claude_adapter import ClaudeSearchProvider
            
            if not config.has_anthropic_api():
                return "❌ Claude API not configured. Please contact an administrator."
            
            # Build context for Claude
            context = await self.context_manager.build_full_context(
                query, message.author.id, message.channel.id,
                message.author.display_name, message
            )
            
            # Create pure Claude provider and search pipeline
            claude_provider = ClaudeSearchProvider()
            pipeline = SearchPipeline(claude_provider)
            
            # Execute the unified search pipeline with pure Claude
            response = await pipeline.search_and_respond(query, context)
            
            return response
            
        except Exception as e:
            print(f"DEBUG: Pure Claude search pipeline failed: {e}")
            return f"❌ Error with pure Claude search: {str(e)}"

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
            print(f"DEBUG: Pure Perplexity search pipeline failed: {e}")
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
            print(f"DEBUG: Added research context to reorganize_roles parameters")
        
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
            rate_msg = f"⏰ **Rate limit exceeded!** You can make {config.AI_RATE_LIMIT_REQUESTS} requests per {config.AI_RATE_LIMIT_WINDOW} seconds.\n\nTry again after {reset_str}."
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
                result = await executor.execute_admin_action(
                    action_data['message'], 
                    intent['action_type'], 
                    intent['parameters']
                )
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