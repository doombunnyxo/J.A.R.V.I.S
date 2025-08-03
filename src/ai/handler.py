import re
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import defaultdict, deque

from groq import Groq
from ..config import config
from ..data.persistence import data_manager
from ..admin.permissions import is_admin
from ..admin.actions import AdminActionHandler
from ..admin.parser import AdminIntentParser
from ..search.claude import claude_search_analysis
from ..utils.message_utils import smart_split_message

# Constants
CONTEXT_EXPIRY_MINUTES = 30
MAX_UNIFIED_CONTEXT = 12
MAX_PROCESSED_MESSAGES = 100
ADMIN_ACTION_CLEANUP_MINUTES = 5

# Search routing keywords
SEARCH_INDICATORS = [
    'current', 'latest', 'recent', 'today', 'now', 'this year', '2024', '2025',
    'news', 'update', 'new', 'what is', 'who is', 'where is', 'when is',
    'how to', 'best', 'top', 'price', 'cost', 'weather', 'stock',
    'search for', 'find', 'look up', 'tell me about',
    'happening', 'status', 'release date', 'version', 'tier list', 'tierlist',
    'can you search', 'search', 'google', 'browse', 'internet', 'online',
    'recommend', 'suggestion', 'review',
    'guide', 'tutorial', 'learn', 'help me find', 'show me', 'list of',
    'upcoming', 'schedule', 'event', 'concert', 'movie', 'game release',
    'patch notes', 'update notes', 'changelog', 'what happened',
    'statistics', 'stats', 'data', 'research', 'study', 'results'
]

COMPARISON_INDICATORS = [
    'compare', 'comparison', 'vs', 'versus', 'against',
    'better', 'worse', 'difference', 'differences', 'different',
    'which is better', 'which is best', 'which should i',
    'pros and cons', 'advantages', 'disadvantages',
    'similar', 'alternative', 'alternatives', 'options',
    'choose between', 'deciding between', 'pick between',
    'rather than', 'instead of', 'or should i',
    'what\'s better', 'whats better', 'which one',
    'head to head', 'side by side', 'face off',
    'more popular', 'less popular', 'most popular', 'popularity',
    'more common', 'less common', 'most common', 'commonly used',
    'more preferred', 'preferred', 'preference', 'favorite',
    'more reliable', 'less reliable', 'reliability', 'trustworthy',
    'more expensive', 'less expensive', 'cheaper', 'pricier',
    'faster', 'slower', 'quicker', 'performance',
    'larger', 'smaller', 'bigger', 'size comparison',
    'newer', 'older', 'latest version', 'outdated',
    'more secure', 'less secure', 'security comparison',
    'more features', 'fewer features', 'feature comparison',
    'higher quality', 'lower quality', 'quality comparison'
]

QUESTION_PATTERNS = [
    'what are the', 'what\'s the', 'which is', 'where can i',
    'how much', 'how many', 'when did', 'when will', 'when is',
    'who won', 'who is', 'why is', 'is there', 'are there',
    'should i choose', 'should i get', 'should i buy'
]

CURRENT_TOPICS = [
    'cryptocurrency', 'crypto', 'bitcoin', 'ethereum', 'nft',
    'stock market', 'stocks', 'trading', 'investment',
    'covid', 'pandemic', 'vaccine', 'politics', 'election',
    'war', 'conflict', 'ukraine', 'russia', 'china',
    'climate', 'global warming', 'environment',
    'tech news', 'technology', 'ai news', 'openai', 'chatgpt',
    'game', 'gaming', 'esports', 'tournament', 'championship',
    'movie', 'film', 'tv show', 'series', 'netflix', 'streaming',
    'music', 'album', 'artist', 'concert', 'tour',
    'sports', 'football', 'basketball', 'soccer', 'baseball',
    'meme', 'trending', 'viral', 'social media', 'twitter', 'reddit'
]

COMPARISON_TOPICS = [
    'laptop', 'computer', 'phone', 'smartphone', 'tablet', 'headphones',
    'car', 'vehicle', 'insurance', 'bank', 'credit card', 'loan',
    'software', 'app', 'service', 'platform', 'tool', 'website',
    'restaurant', 'hotel', 'vacation', 'university', 'college', 'course',
    'job', 'career', 'salary', 'investment', 'company', 'brand'
]

ADMIN_KEYWORDS = [
    # User moderation
    'kick', 'boot', 'eject', 'ban', 'unban', 'timeout', 'mute', 'silence', 'quiet', 'shush',
    'remove timeout', 'unmute', 'unsilence',
    # Message management
    'delete', 'remove', 'purge', 'clear', 'clean', 'wipe', 'my messages', 'i sent',
    'delete messages', 'remove messages', 'purge messages', 'clear messages',
    # Role management
    'role', 'add role', 'give role', 'remove role', 'take role', 'rename role', 
    'change role name', 'update role name', 'rename the role', 'reorganize roles',
    'fix role names', 'improve role names', 'make roles make sense', 'better role names',
    'clean up roles', 'rename roles to make sense', 'update all role names',
    'organize the roles better', 'fix our role structure', 'update roles based on',
    'organize roles like', 'make roles fit',
    # Channel management
    'create channel', 'delete channel', 'voice channel', 'text channel',
    # Nickname management
    'change nickname', 'set nickname', 'rename', 'nickname'
]

PERSONAL_KEYWORDS = [
    'remember', 'remind me', 'my name', 'my preference', 'about me',
    'tell me a joke', 'joke', 'funny', 'make me laugh',
    'how are you', 'hello', 'hi', 'thanks', 'thank you',
    'good morning', 'good night', 'goodbye'
]

class RateLimiter:
    """Rate limiter for AI requests"""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.user_requests: Dict[int, deque] = defaultdict(deque)
    
    def is_allowed(self, user_id: int) -> bool:
        """Check if user is allowed to make a request"""
        now = datetime.now()
        user_queue = self.user_requests[user_id]
        
        # Remove old requests outside the window
        while user_queue and user_queue[0] < now - timedelta(seconds=self.window_seconds):
            user_queue.popleft()
        
        # Check if under limit
        if len(user_queue) < self.max_requests:
            user_queue.append(now)
            return True
        
        return False
    
    def get_reset_time(self, user_id: int) -> Optional[datetime]:
        """Get when the user's rate limit will reset"""
        user_queue = self.user_requests[user_id]
        if user_queue:
            return user_queue[0] + timedelta(seconds=self.window_seconds)
        return None

class AIHandler:
    """Handles AI interactions with hybrid Groq+Claude approach"""
    
    _instance_count = 0
    
    def __init__(self, bot):
        AIHandler._instance_count += 1
        self.instance_id = AIHandler._instance_count
        print(f"DEBUG: Creating AIHandler instance #{self.instance_id}")
        
        self.bot = bot
        self.groq_client = None
        self.rate_limiter = RateLimiter(
            config.AI_RATE_LIMIT_REQUESTS, 
            config.AI_RATE_LIMIT_WINDOW
        )
        self.admin_handler = AdminActionHandler(bot)
        self.intent_parser = AdminIntentParser(bot)
        self.pending_admin_actions = {}
        self.processed_messages = set()
        
        # Track which AI provider was used for each user/channel conversation
        self.conversation_providers = {}  # key: "user_id_channel_id", value: "groq" or "claude"
        
        # Unified conversation context shared between both AIs
        self.unified_conversation_contexts = defaultdict(lambda: deque(maxlen=MAX_UNIFIED_CONTEXT))
        self.unified_last_activity = {}
        
        self._initialize_groq()
    
    def _cleanup_stale_actions(self):
        """Clean up stale pending actions (older than ADMIN_ACTION_CLEANUP_MINUTES)"""
        current_time = datetime.now()
        cleanup_threshold = ADMIN_ACTION_CLEANUP_MINUTES * 60  # Convert to seconds
        
        stale_users = [
            user_id for user_id, action_data in self.pending_admin_actions.items()
            if "timestamp" in action_data and 
            (current_time - action_data["timestamp"]).total_seconds() > cleanup_threshold
        ]
        
        for user_id in stale_users:
            print(f"DEBUG: Cleaning up stale admin action for user {user_id}")
            self.pending_admin_actions.pop(user_id, None)
    
    def _initialize_groq(self):
        """Initialize Groq client if API key is available"""
        try:
            if config.has_groq_api():
                print(f"DEBUG: Initializing Groq client with API key: {config.GROQ_API_KEY[:20]}...")
                self.groq_client = Groq(api_key=config.GROQ_API_KEY)
                print("DEBUG: Groq client initialized successfully")
            else:
                print("Warning: Groq API key not configured")
        except Exception as e:
            print(f"Groq client initialization failed: {e}")
            print(f"DEBUG: Exception type: {type(e).__name__}")
            self.groq_client = None
    
    def _needs_web_search(self, query: str) -> bool:
        """Determine if query needs web search via Claude (default to TRUE for most queries)"""
        query_lower = query.lower()
        
        # Check for admin commands or personal queries (should NOT use web search)
        is_admin_command = any(keyword in query_lower for keyword in ADMIN_KEYWORDS)
        is_personal_query = any(keyword in query_lower for keyword in PERSONAL_KEYWORDS)
        
        # Route to Groq only for admin commands and very personal interactions
        if is_admin_command:
            return False
        
        # Route very basic personal greetings to Groq
        if is_personal_query and len(query_lower.split()) <= 3:
            return False
        
        # Everything else goes to Claude for web-enhanced responses
        return True
    
    def _get_conversation_key(self, user_id: int, channel_id: int) -> str:
        """Generate conversation key for tracking AI provider"""
        return f"{user_id}_{channel_id}"
    
    
    async def _optimize_search_query(self, user_query: str, filtered_context: str = "") -> str:
        """Use Groq to create an optimized search query for better Google Search results"""
        if not self.groq_client or not config.has_groq_api():
            # Fallback: return the original query
            return user_query
        
        try:
            system_prompt = """You are a search query optimizer. Your job is to transform user questions into optimized Google search queries that will return the most relevant and current results.

INSTRUCTIONS:
1. Convert conversational questions into effective search terms
2. Remove unnecessary words like "can you", "please", "I want to know"
3. Focus on the core information being sought
4. Add relevant keywords that would improve search results
5. Keep queries concise but comprehensive
6. Use current year (2025) for time-sensitive queries
7. Return ONLY the optimized search query, nothing else

EXAMPLES:
- "What's the weather like today?" → "weather today [current location]"
- "Can you tell me about the latest iPhone?" → "iPhone 2025 latest model specs features"
- "I want to know how to cook pasta" → "how to cook pasta recipe instructions"
- "What are the best laptops for gaming?" → "best gaming laptops 2025 reviews comparison"
"""

            context_info = ""
            if filtered_context:
                context_info = f"\n\nRELEVANT USER CONTEXT:\n{filtered_context}\n\nUse this context to make the search query more specific and personalized."

            messages = [
                {
                    "role": "system", 
                    "content": system_prompt + context_info
                },
                {
                    "role": "user",
                    "content": f"Optimize this search query: {user_query}"
                }
            ]
            
            completion = self.groq_client.chat.completions.create(
                messages=messages,
                model=config.AI_MODEL,
                max_tokens=100,
                temperature=0.1  # Low temperature for consistent optimization
            )
            
            optimized_query = completion.choices[0].message.content.strip()
            
            # Remove quotes if they were added
            optimized_query = optimized_query.strip('"\'')
            
            print(f"DEBUG: [AIHandler-{self.instance_id}] Search query optimized:")
            print(f"DEBUG: Original: '{user_query}'")
            print(f"DEBUG: Optimized: '{optimized_query}'")
            
            return optimized_query
            
        except Exception as e:
            print(f"DEBUG: Search query optimization failed: {e}")
            return user_query
    
    async def _filter_context_for_relevance(self, query: str, conversation_context: list, user_name: str = None) -> str:
        """Use Groq to filter and summarize conversation context based on relevance to the current query (permanent context is preserved separately)"""
        if not self.groq_client or not config.has_groq_api():
            # Fallback: return raw context if Groq unavailable
            context_parts = []
            if user_name:
                context_parts.append(f"User: {user_name}")
            if conversation_context:
                context_parts.append("Recent conversation:\n" + "\n".join([f"{msg['role']}: {msg['content'][:200]}..." for msg in conversation_context[-4:]]))
            return "\n\n".join(context_parts)
        
        try:
            # Build context summary request (only for conversation context, not permanent context)
            context_parts = []
            if user_name:
                context_parts.append(f"USER: {user_name}")
            
            if conversation_context:
                context_parts.append("RECENT CONVERSATION:\n" + "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_context[-6:]]))
            
            if not conversation_context:
                return f"User: {user_name}" if user_name else ""
            
            full_context = "\n\n".join(context_parts)
            
            filter_messages = [
                {
                    "role": "system",
                    "content": """You are a context filter. Your job is to analyze the provided conversation context and extract information that is relevant to the user's current query.

INSTRUCTIONS:
1. ALWAYS include the user's name/identity in your response
2. Review the recent conversation history
3. Include conversation context that is relevant to the current query
4. Summarize and organize the information concisely
5. Keep your response under 300 tokens
6. Focus on recent conversation that would help answer the current query

Note: Permanent user context will be added separately and is not included in this filtering.

Return only the filtered conversation context - no explanations or metadata."""
                },
                {
                    "role": "user",
                    "content": f"CURRENT QUERY: {query}\n\nAVAILABLE CONTEXT:\n{full_context}\n\nPlease extract and summarize only the context relevant to answering this query:"
                }
            ]
            
            completion = self.groq_client.chat.completions.create(
                messages=filter_messages,
                model=config.AI_MODEL,
                max_tokens=300,
                temperature=0.1  # Low temperature for consistent filtering
            )
            
            filtered_context = completion.choices[0].message.content.strip()
            
            # Always return at least user name, even if context seems irrelevant
            if not filtered_context or "no relevant context" in filtered_context.lower():
                return f"User: {user_name}" if user_name else ""
            
            print(f"DEBUG: [AIHandler-{self.instance_id}] Context filtered from {len(full_context)} to {len(filtered_context)} chars")
            return filtered_context
            
        except Exception as e:
            print(f"DEBUG: Context filtering failed: {e}")
            # Fallback to raw context on error
            context_parts = []
            if user_name:
                context_parts.append(f"User: {user_name}")
            if conversation_context:
                context_parts.append("Recent conversation:\n" + "\n".join([f"{msg['role']}: {msg['content'][:200]}..." for msg in conversation_context[-4:]]))
            return "\n\n".join(context_parts)
    
    async def _filter_permanent_context_for_relevance(self, query: str, permanent_context: list, user_name: str, message = None) -> list:
        """Filter permanent context for relevance to the current query"""
        if not self.groq_client or not config.has_groq_api() or not permanent_context:
            return permanent_context or []
        
        try:
            # Resolve user mentions in permanent context first
            resolved_permanent_context = []
            for item in permanent_context:
                if message:
                    resolved_item = await self._resolve_user_mentions(item, message)
                    resolved_permanent_context.append(resolved_item)
                else:
                    resolved_permanent_context.append(item)
            
            permanent_context_text = "\n".join([f"- {item}" for item in resolved_permanent_context])
            
            filter_messages = [
                {
                    "role": "system",
                    "content": """You are a context relevance filter. Your job is to identify which permanent context items are relevant to the user's current query.

INSTRUCTIONS:
1. Review each permanent context item carefully
2. ONLY include items that are relevant to BOTH the current user AND the current query
3. Include items that contain preferences/background about the CURRENT USER asking the query
4. Include items that contain instructions for responding to the CURRENT USER specifically
5. EXCLUDE items that mention other users or contain instructions for responding to other users
6. EXCLUDE items that are completely unrelated to the query topic
7. Be SELECTIVE - only include items that would actually help answer this specific user's query
8. When an item mentions specific users, only include it if it's about the current user asking

CRITICAL: Do NOT include context items that are instructions for responding to other users. Only include items relevant to the current user and query.

Return only the relevant permanent context items, one per line, in the exact same format as provided. If no items are relevant, return "No relevant permanent context"."""
                },
                {
                    "role": "user",
                    "content": f"USER: {user_name}\n\nCURRENT QUERY: {query}\n\nPERMANENT CONTEXT ITEMS:\n{permanent_context_text}\n\nPlease return only the relevant permanent context items:"
                }
            ]
            
            completion = self.groq_client.chat.completions.create(
                messages=filter_messages,
                model=config.AI_MODEL,
                max_tokens=400,
                temperature=0.1
            )
            
            filtered_response = completion.choices[0].message.content.strip()
            
            if "no relevant permanent context" in filtered_response.lower():
                print(f"DEBUG: [AIHandler-{self.instance_id}] No relevant permanent context found for query")
                return []
            
            # Parse the filtered response back into a list
            filtered_items = []
            for line in filtered_response.split('\n'):
                line = line.strip()
                if line.startswith('- '):
                    filtered_items.append(line[2:])  # Remove the "- " prefix
                elif line and not line.startswith('USER:') and not line.startswith('CURRENT QUERY:'):
                    filtered_items.append(line)
            
            print(f"DEBUG: [AIHandler-{self.instance_id}] Filtered permanent context from {len(resolved_permanent_context)} to {len(filtered_items)} items")
            return filtered_items
            
        except Exception as e:
            print(f"DEBUG: Permanent context filtering failed: {e}")
            # Fallback: return all resolved permanent context
            resolved_permanent_context = []
            for item in permanent_context:
                if message:
                    resolved_item = await self._resolve_user_mentions(item, message)
                    resolved_permanent_context.append(resolved_item)
                else:
                    resolved_permanent_context.append(item)
            return resolved_permanent_context

    async def _add_permanent_context_to_filtered(self, filtered_conversation_context: str, permanent_context: list, user_name: str, query: str, message = None) -> str:
        """Add relevant permanent context to filtered conversation context"""
        context_parts = []
        
        # Start with filtered conversation context if available
        if filtered_conversation_context and filtered_conversation_context.strip():
            context_parts.append(filtered_conversation_context)
        elif user_name:
            context_parts.append(f"User: {user_name}")
        
        # Get user key for unfiltered permanent context
        user_key = data_manager.get_user_key(message.author) if message else None
        
        # Add unfiltered permanent context (always included, never filtered)
        if user_key:
            unfiltered_permanent_items = data_manager.get_unfiltered_permanent_context(user_key)
            if unfiltered_permanent_items:
                # Resolve user mentions in unfiltered context
                resolved_unfiltered_items = []
                for item in unfiltered_permanent_items:
                    if message:
                        resolved_item = await self._resolve_user_mentions(item, message)
                        resolved_unfiltered_items.append(resolved_item)
                    else:
                        resolved_unfiltered_items.append(item)
                
                context_parts.append("Always apply settings:\n" + "\n".join([f"- {item}" for item in resolved_unfiltered_items]))
        
        # Filter and add only relevant permanent context
        if permanent_context:
            relevant_permanent_context = await self._filter_permanent_context_for_relevance(
                query, permanent_context, user_name, message
            )
            
            if relevant_permanent_context:
                context_parts.append("Relevant context:\n" + "\n".join([f"- {item}" for item in relevant_permanent_context]))
        
        return "\n\n".join(context_parts)
    
    async def _resolve_user_mentions(self, text: str, message) -> str:
        """Resolve Discord user mentions <@123456789> to actual usernames in text"""
        import re
        
        # Find all user mentions in the text
        mention_pattern = r'<@!?(\d+)>'
        mentions = re.findall(mention_pattern, text)
        
        resolved_text = text
        for user_id in mentions:
            try:
                # Try to get the user from the current guild first
                user = None
                if message.guild:
                    user = message.guild.get_member(int(user_id))
                
                # If not found in guild, try to fetch from bot
                if not user:
                    user = self.bot.get_user(int(user_id))
                
                # If still not found, try to fetch from Discord API
                if not user:
                    user = await self.bot.fetch_user(int(user_id))
                
                if user:
                    # Replace the mention with the user's display name
                    mention_formats = [f'<@{user_id}>', f'<@!{user_id}>']
                    for mention_format in mention_formats:
                        resolved_text = resolved_text.replace(mention_format, user.display_name)
                    
                    print(f"DEBUG: [AIHandler-{self.instance_id}] Resolved <@{user_id}> to {user.display_name}")
                
            except Exception as e:
                print(f"DEBUG: Failed to resolve user mention <@{user_id}>: {e}")
                # Leave the mention as-is if we can't resolve it
                continue
        
        return resolved_text
    
    def _suppress_link_previews(self, text: str) -> str:
        """Wrap any unwrapped URLs in angle brackets to suppress Discord link previews"""
        import re
        
        # Pattern to match URLs that are NOT already wrapped in angle brackets
        # This matches http/https URLs that don't have < before them and > after them
        url_pattern = r'(?<!\<)(https?://[^\s\>]+)(?!\>)'
        
        # Replace unwrapped URLs with angle-bracket wrapped versions
        def replace_url(match):
            url = match.group(1)
            return f'<{url}>'
        
        return re.sub(url_pattern, replace_url, text)
    
    async def _perform_google_search(self, query: str) -> str:
        """Perform Google search and return results as text"""
        try:
            # Import here to avoid circular imports
            from googleapiclient.discovery import build
            
            if not config.has_google_search():
                return "Google search is not configured. Please set GOOGLE_API_KEY and GOOGLE_SEARCH_ENGINE_ID."
            
            service = build("customsearch", "v1", developerKey=config.GOOGLE_API_KEY)
            result = service.cse().list(q=query, cx=config.GOOGLE_SEARCH_ENGINE_ID, num=10).execute()
            
            if 'items' not in result:
                return f"No search results found for: {query}"
            
            search_results = f"Current web search results for '{query}':\n\n"
            
            for i, item in enumerate(result['items'][:10], 1):
                title = item['title']
                link = item['link']
                snippet = item.get('snippet', 'No description available')
                
                search_results += f"{i}. **{title}**\n"
                search_results += f"   {snippet[:400]}...\n"
                search_results += f"   Source: <{link}>\n\n"
            
            return search_results
            
        except Exception as e:
            return f"Search failed: {str(e)}"
    
    def _extract_claude_model(self, query: str, user_id: int) -> tuple[str, str]:
        """Extract Claude model from admin user queries and return (model, cleaned_query)"""
        # Only admins can switch models
        if not is_admin(user_id):
            return "haiku", query
        
        # Available Claude models for search processing
        claude_models = {
            'haiku': 'haiku',
            'claude-haiku': 'haiku',
            '3.5-haiku': 'haiku',
            'claude-3.5-haiku': 'haiku',
            'fast': 'haiku',
            'quick': 'haiku'
        }
        
        # Patterns to detect model switching - more comprehensive and precise
        model_patterns = [
            # "use <model> to <query>" or "use <model> <query>"
            (r'use\s+(?:model\s+)?([a-z-]+)(?:\s+model)?\s+(?:to\s+)?(.+)', 2),
            # "with <model> <query>" or "with <model> model <query>"  
            (r'with\s+(?:model\s+)?([a-z-]+)(?:\s+model)?\s+(.+)', 2),
            # "model: <model> <query>"
            (r'model\s*:\s*([a-z-]+)\s*[-\s]*(.+)', 2),
            # "[<model>] <query>"
            (r'\[([a-z-]+)\]\s*(.+)', 2),
            # "--model=<model> <query>" or "--model <model> <query>"
            (r'--model[=\s]+([a-z-]+)\s+(.+)', 2),
            # "-m <model> <query>"
            (r'-m\s+([a-z-]+)\s+(.+)', 2),
            # "<model> model <query>"
            (r'([a-z-]+)\s+model\s+(.+)', 2),
            # Just the model name at the start: "<model> <query>"
            (r'^([a-z-]+)\s+(.+)', 2)
        ]
        
        query_lower = query.lower()
        
        # Check each pattern
        for pattern, query_group in model_patterns:
            match = re.search(pattern, query_lower)
            if match:
                model_name = match.group(1).lower()
                
                # Check if it's a valid Claude model
                if model_name in claude_models:
                    # Extract the clean query from the appropriate group
                    cleaned_query = match.group(query_group).strip() if query_group else query
                    
                    # Clean up extra whitespace and punctuation
                    cleaned_query = re.sub(r'\s+', ' ', cleaned_query)
                    cleaned_query = re.sub(r'^[-\s]+', '', cleaned_query)  # Remove leading dashes/spaces
                    cleaned_query = cleaned_query.strip()
                    
                    actual_model = claude_models[model_name]
                    print(f"DEBUG: [AIHandler-{self.instance_id}] Admin {user_id} switching to Claude model: {actual_model}")
                    print(f"DEBUG: Original query: '{query}'")
                    print(f"DEBUG: Cleaned query: '{cleaned_query}'")
                    return actual_model, cleaned_query
        
        # Default to haiku if no model specified
        return "haiku", query

    def _is_followup_to_existing_conversation(self, query: str, user_id: int, channel_id: int) -> bool:
        """Check if this is a follow-up to an existing conversation"""
        conversation_key = self._get_conversation_key(user_id, channel_id)
        
        # Check unified conversation context
        unified_context = self.unified_conversation_contexts.get(conversation_key)
        last_activity = self.unified_last_activity.get(conversation_key)
        
        if unified_context and last_activity:
            # Check if context is still fresh
            if datetime.now() - last_activity < timedelta(minutes=CONTEXT_EXPIRY_MINUTES):
                return True
        
        # Note: Removed backwards compatibility check for old Perplexity context
        # as we now use unified context exclusively
        
        # If no recent context, clean up our provider tracking
        self.conversation_providers.pop(conversation_key, None)
        return False
    
    async def _add_admin_reactions(self, sent_msg, user_id: int):
        """Add admin confirmation reactions to a message"""
        await sent_msg.add_reaction('✅')
        await sent_msg.add_reaction('❌')
        if user_id in self.pending_admin_actions:
            self.pending_admin_actions[user_id]["confirmation_message"] = sent_msg
    
    async def handle_ai_command(self, message, ai_query: str, force_provider: str = None):
        """Handle AI command with hybrid Groq+Claude approach
        
        Args:
            message: Discord message object
            ai_query: User's query string
            force_provider: Force specific provider ("groq" or "claude")
        """
        try:
            # Prevent duplicate processing
            if message.id in self.processed_messages:
                print(f"DEBUG: [AIHandler-{self.instance_id}] Message {message.id} already processed")
                return
            
            self.processed_messages.add(message.id)
            print(f"DEBUG: [AIHandler-{self.instance_id}] Processing message {message.id}")
            
            # Clean up old processed message IDs (keep last MAX_PROCESSED_MESSAGES)
            if len(self.processed_messages) > MAX_PROCESSED_MESSAGES:
                old_messages = list(self.processed_messages)[:MAX_PROCESSED_MESSAGES//2]
                for msg_id in old_messages:
                    self.processed_messages.discard(msg_id)
            
            # Check rate limit
            if not self.rate_limiter.is_allowed(message.author.id):
                reset_time = self.rate_limiter.get_reset_time(message.author.id)
                wait_seconds = int((reset_time - datetime.now()).total_seconds()) if reset_time else 60
                await message.channel.send(f'⏰ **Rate Limited**: Please wait {wait_seconds} seconds before making another AI request.')
                return
            
            conversation_key = self._get_conversation_key(message.author.id, message.channel.id)
            
            # Check if this is a follow-up to an existing conversation
            is_followup = self._is_followup_to_existing_conversation(ai_query, message.author.id, message.channel.id)
            
            # Determine which AI to use
            use_claude = False
            
            if force_provider:
                # Force specific provider
                use_claude = (force_provider == "claude" or force_provider == "perplexity")  # Support both names for compatibility
                print(f"DEBUG: [AIHandler-{self.instance_id}] Forced to use {'claude' if use_claude else 'groq'}")
            elif is_followup:
                # For follow-ups, use routing logic but with shared context
                use_claude = self._needs_web_search(ai_query)
                previous_provider = self.conversation_providers.get(conversation_key)
                if use_claude:
                    if previous_provider != "claude":
                        print(f"DEBUG: [AIHandler-{self.instance_id}] Follow-up switching to Claude for web search (was {previous_provider})")
                    else:
                        print(f"DEBUG: [AIHandler-{self.instance_id}] Follow-up continuing with Claude")
                else:
                    if previous_provider != "groq":
                        print(f"DEBUG: [AIHandler-{self.instance_id}] Follow-up switching to Groq for chat/admin (was {previous_provider})")
                    else:
                        print(f"DEBUG: [AIHandler-{self.instance_id}] Follow-up continuing with Groq")
            else:
                # New conversation - use normal routing logic
                use_claude = self._needs_web_search(ai_query)
                if use_claude:
                    print(f"DEBUG: [AIHandler-{self.instance_id}] New conversation - routing to Claude for web search")
                else:
                    print(f"DEBUG: [AIHandler-{self.instance_id}] New conversation - routing to Groq for admin/chat processing")
            
            # ROUTE 1: Use Claude for web search queries
            if use_claude:
                if config.has_anthropic_api():
                    async with message.channel.typing():
                        # Check for admin model switching
                        claude_model, cleaned_query = self._extract_claude_model(ai_query, message.author.id)
                        # Use unified context for cross-AI awareness
                        response = await self._handle_with_claude(message, cleaned_query, claude_model)
                    # Track that we used Claude for this conversation
                    self.conversation_providers[conversation_key] = "claude"
                else:
                    response = "Web search is not available - Claude API not configured."
            
            # ROUTE 2: Use Groq for admin/chat processing
            else:
                if not config.has_groq_api() or self.groq_client is None:
                    await message.channel.send('Groq API is not configured or failed to initialize.')
                    return
                
                response = await self._handle_with_groq(message, ai_query)
                # Track that we used Groq for this conversation
                self.conversation_providers[conversation_key] = "groq"
            
            # Store conversation in unified context (shared between both AIs)
            if response and not response.startswith("Error") and not response.startswith("Web search is not available"):
                unified_context = self.unified_conversation_contexts[conversation_key]
                unified_context.append({"role": "user", "content": ai_query})
                unified_context.append({"role": "assistant", "content": response})
                self.unified_last_activity[conversation_key] = datetime.now()
                print(f"DEBUG: [AIHandler-{self.instance_id}] Stored unified context: {len(unified_context)} messages for {conversation_key}")
            
            # Ensure response is not None
            if not response:
                response = "I apologize, but I couldn't generate a response to your message."
            
            # Send response (only if we got one - Groq handler might have already sent admin messages)
            if response:
                # Use smart message splitting
                message_chunks = smart_split_message(response)
                for chunk in message_chunks:
                    await message.channel.send(chunk)
        
        except Exception as e:
            await message.channel.send(f'AI request failed: {str(e)}')
    
    async def _prepare_context_and_search(self, message, ai_query: str) -> tuple[str, str]:
        """Prepare filtered context and perform optimized search"""
        user_key = data_manager.get_user_key(message.author)
        conversation_key = self._get_conversation_key(message.author.id, message.channel.id)
        
        # Get available context
        permanent_items = data_manager.get_permanent_context(user_key)
        unified_context = self.unified_conversation_contexts.get(conversation_key)
        
        # Filter conversation context for relevance using Groq (permanent context preserved separately)
        filtered_conversation_context = await self._filter_context_for_relevance(
            ai_query, 
            list(unified_context) if unified_context else [],
            message.author.display_name
        )
        
        # Add relevant permanent context to filtered conversation context
        filtered_context = await self._add_permanent_context_to_filtered(
            filtered_conversation_context,
            permanent_items or [],
            message.author.display_name,
            ai_query,
            message
        )
        
        # Optimize search query using filtered context
        optimized_query = await self._optimize_search_query(ai_query, filtered_context)
        
        # Perform Google search with optimized query
        search_results = await self._perform_google_search(optimized_query)
        
        return filtered_context, search_results
    
    
    def _build_groq_system_message(self, filtered_context: str, user_id: int) -> str:
        """Build comprehensive system message for Groq"""
        parts = []
        
        # Add filtered relevant context if available
        if filtered_context:
            parts.append(f"RELEVANT CONTEXT:\n{filtered_context}")
            parts.append("=" * 50)
        
        # Core capabilities
        core_instructions = """You are a helpful AI assistant with the following capabilities:

1. **General Knowledge**: You can answer questions using your training data and any relevant context provided above.

2. **Discord Server Management** (Admin only): You can help with server administration including user moderation, role management, channel management, and message cleanup.

The relevant context section above contains only information that is pertinent to the current query. Use this context to provide more personalized and informed responses."""

        parts.append(core_instructions)
        
        # Add admin capabilities if user is admin
        if is_admin(user_id):
            admin_instructions = """Additional admin capabilities:

- User moderation (kick, ban, timeout/mute users)
- Role management (add/remove roles from users, rename roles)  
- Channel management (create/delete channels)
- Message cleanup (bulk delete messages, including from specific users)
- Nickname changes

When you detect an administrative request in the user's message, respond by clearly stating what action you understood. DO NOT ask for text-based confirmation like "reply yes/no". DO NOT mention reaction buttons or emojis. The system will automatically handle confirmation.

Use this format:
I understand you want to [ACTION]. [Brief description of what will happen]

IMPORTANT: Only mention the admin action ONCE in your response. Do not repeat or add additional confirmation text. Do not use quotation marks around your responses.

Examples:
- "kick that spammer" → I understand you want to kick [user]. They will be removed from the server.
- "delete John's messages" → I understand you want to delete messages from John. I'll remove their recent messages.
- "ban the troublemaker" → I understand you want to ban [user]. They will be permanently banned from the server.
- "timeout Sarah for being rude" → I understand you want to timeout Sarah. She will be muted temporarily.
- "rename role Moderator to Super Mod" → I understand you want to rename the Moderator role to Super Mod.

Be concise and clear about what the action will do. The confirmation system is handled automatically."""

            parts.append(admin_instructions)
        
        return "\n\n".join(parts)
    
    async def _call_groq_api(self, system_message: str, ai_query: str, message) -> str:
        """Make API call to Groq for chat/admin functionality"""
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": ai_query}
        ]
        
        # Debug logging
        print(f"DEBUG: [AIHandler-{self.instance_id}] Calling Groq API:")
        print(f"DEBUG: System message: {len(system_message)} chars")
        
        # Make Groq API call
        async with message.channel.typing():
            completion = self.groq_client.chat.completions.create(
                messages=messages,
                model=config.AI_MODEL,
                max_tokens=config.AI_MAX_TOKENS,
                temperature=config.AI_TEMPERATURE
            )
            
            response = completion.choices[0].message.content or "No response generated."
            
            # Check for admin actions
            admin_action_detected = False
            if is_admin(message.author.id) and message.guild and message.author.id not in self.pending_admin_actions:
                action_type, parameters = await self.intent_parser.parse_admin_intent(ai_query, message.guild, message.author)
                
                if action_type:
                    self._cleanup_stale_actions()
                    
                    self.pending_admin_actions[message.author.id] = {
                        "action_type": action_type,
                        "parameters": parameters,
                        "message_id": message.id,
                        "original_message": message,
                        "timestamp": datetime.now()
                    }
                    admin_action_detected = True
                    print(f"DEBUG: Admin action detected: {action_type}")
                    
                    # Add confirmation message if not already present
                    detection_keywords = ["Admin Action Detected", "admin action", "React with", "✅", "❌"]
                    if response and not any(keyword in response for keyword in detection_keywords):
                        response += f"\n\n[ADMIN] Action detected: {action_type}\nReact with ✅ to proceed or ❌ to cancel."
            
            # Handle admin reactions for response message
            if admin_action_detected:
                # We need to send the message here to add reactions
                message_chunks = smart_split_message(response)
                for i, chunk in enumerate(message_chunks):
                    sent_msg = await message.channel.send(chunk)
                    if i == 0:  # Only add reactions to first message
                        await self._add_admin_reactions(sent_msg, message.author.id)
                return ""  # Return empty since we already sent the message
            
            return response
    
    async def _handle_with_claude(self, message, ai_query: str, model: str = "haiku") -> str:
        """Handle query with Google search + Claude analysis"""
        try:
            # Prepare context and perform search
            filtered_context, search_results = await self._prepare_context_and_search(message, ai_query)
            
            if not search_results or "Search failed" in search_results or "not configured" in search_results:
                return f"Web search unavailable: {search_results}"
            
            # Debug logging
            print(f"DEBUG: [AIHandler-{self.instance_id}] Calling Claude API:")
            print(f"DEBUG: Model: {model}")
            print(f"DEBUG: Search results: {len(search_results)} chars")
            print(f"DEBUG: Filtered context: {len(filtered_context)} chars" if filtered_context else "DEBUG: No relevant context")
            
            # Call Claude search analysis directly
            response = await claude_search_analysis(ai_query, search_results, filtered_context)
            
            # Post-process to wrap any unwrapped URLs in angle brackets
            return self._suppress_link_previews(response)
        
        except Exception as e:
            return f"Error with Claude search: {str(e)}"
    
    async def _prepare_groq_context(self, message, ai_query: str) -> str:
        """Prepare filtered context for Groq"""
        user_key = data_manager.get_user_key(message.author)
        user_settings = data_manager.get_user_settings(user_key)
        conversation_key = self._get_conversation_key(message.author.id, message.channel.id)
        
        # Get available context
        permanent_items = data_manager.get_permanent_context(user_key)
        unified_context = self.unified_conversation_contexts.get(conversation_key)
        
        # Add channel context if no conversation context and enabled
        channel_context_list = []
        if not unified_context and user_settings.get("use_channel_context", True):
            channel_context = await self.get_channel_context(message.channel)
            if channel_context:
                channel_context_list = [{"role": "system", "content": channel_context}]
        
        # Filter conversation context for relevance using Groq (permanent context preserved separately)
        filtered_conversation_context = await self._filter_context_for_relevance(
            ai_query, 
            list(unified_context) if unified_context else channel_context_list,
            message.author.display_name
        )
        
        # Add relevant permanent context to filtered conversation context
        return await self._add_permanent_context_to_filtered(
            filtered_conversation_context,
            permanent_items or [],
            message.author.display_name,
            ai_query,
            message
        )
    
    async def _handle_with_groq(self, message, ai_query: str) -> str:
        """Handle query with Groq for admin/chat functionality"""
        try:
            # Prepare filtered context
            filtered_context = await self._prepare_groq_context(message, ai_query)
            
            # Build system message for Groq
            system_message = self._build_groq_system_message(filtered_context, message.author.id)
            
            # Call Groq API
            return await self._call_groq_api(system_message, ai_query, message)
        
        except Exception as e:
            return f"Error processing with Groq: {str(e)}"
    
    async def get_channel_context(self, channel, limit: int = None) -> str:
        """Fetch recent messages from channel for context"""
        if limit is None:
            limit = config.CHANNEL_CONTEXT_LIMIT
        
        try:
            messages = []
            async for message in channel.history(limit=limit, oldest_first=False):
                if message.author.bot:
                    continue  # Skip bot messages
                
                content = f"{message.author.display_name}: {message.content}"
                messages.append(content)
            
            # Reverse to get chronological order
            messages.reverse()
            
            if messages:
                display_limit = config.CHANNEL_CONTEXT_DISPLAY
                return "Recent channel messages:\n" + "\n".join(messages[-display_limit:])
            return ""
        except Exception as e:
            print(f"Error fetching channel context: {e}")
            return ""
    
    async def handle_admin_confirmation(self, reaction, user):
        """Handle admin action confirmations via reactions"""
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