"""
AI routing logic for determining which provider to use
Separates routing concerns from the main AI handler
"""

import re

# Search routing keywords - triggers OpenAI web search
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

# Admin command keywords - triggers Groq
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
    'change nickname', 'set nickname', 'rename', 'nickname', 'nick',
    'user nickname', 'users nickname', 'user\'s nickname', 'set user', 'change user'
]

# Personal interaction keywords - triggers Groq
PERSONAL_KEYWORDS = [
    'remember', 'remind me', 'my name', 'my preference', 'about me',
    'tell me a joke', 'joke', 'funny', 'make me laugh',
    'how are you', 'hello', 'hi', 'thanks', 'thank you',
    'good morning', 'good night', 'goodbye'
]


def should_use_openai_for_search(query: str) -> bool:
    """
    Determine if query should be routed to OpenAI (always True now)
    Kept for compatibility but always returns True since Groq is removed
    
    Args:
        query: User's query string
        
    Returns:
        bool: Always True (OpenAI only system)
    """
    # Everything goes to OpenAI now
    return True


def extract_forced_provider(query: str) -> tuple[str, str]:
    """
    Extract forced provider from query if specified
    
    Args:
        query: User's query string
        
    Returns:
        tuple: (provider, cleaned_query) - provider is 'groq', 'openai', or None
    """
    query_lower = query.lower().strip()
    print(f"DEBUG: extract_forced_provider checking query: '{query_lower}'")
    
    # Check for force patterns
    force_patterns = [
        # Craft commands first to avoid conflicts
        (r'^craft:\s*(.+)', 'crafting'),
        (r'^cr:\s*(.+)', 'crafting'),
        # Full page search with GPT-4o
        (r'^full:\s*(.+)', 'full-search'),
        # Direct AI chat (bypasses search routing)
        (r'^ai:\s*(.+)', 'direct-ai'),
    ]
    
    for pattern, provider in force_patterns:
        match = re.match(pattern, query_lower)
        if match:
            cleaned_query = match.group(1).strip()
            print(f"DEBUG: Pattern '{pattern}' matched provider '{provider}' with query '{cleaned_query}'")
            return provider, cleaned_query
    
    return None, query


def extract_openai_model(query: str, user_id: int) -> tuple[str, str]:
    """
    Extract OpenAI model from admin user queries
    
    Args:
        query: User's query string
        user_id: Discord user ID
        
    Returns:
        tuple: (model, cleaned_query)
    """
    from ..admin.permissions import is_admin
    
    # Only admins can switch models
    if not is_admin(user_id):
        return "gpt-4o-mini", query
    
    # Available OpenAI models for search processing
    openai_models = {
        'gpt-4o-mini': 'gpt-4o-mini',
        '4o-mini': 'gpt-4o-mini',
        'mini': 'gpt-4o-mini',
        'fast': 'gpt-4o-mini',
        'quick': 'gpt-4o-mini',
        'gpt-4o': 'gpt-4o',
        '4o': 'gpt-4o',
        'balanced': 'gpt-4o',
        'gpt-4-turbo': 'gpt-4-turbo',
        '4-turbo': 'gpt-4-turbo',
        'turbo': 'gpt-4-turbo',
        'gpt-4': 'gpt-4',
        '4': 'gpt-4',
        'powerful': 'gpt-4',
        'best': 'gpt-4o'
    }
    
    # Model switching patterns
    model_patterns = [
        (r'use\s+(?:model\s+)?([a-z-]+)(?:\s+model)?\s+(?:to\s+)?(.+)', 2),
        (r'with\s+(?:model\s+)?([a-z-]+)(?:\s+model)?\s+(.+)', 2),
        (r'model\s*:\s*([a-z-]+)\s*[-\s]*(.+)', 2),
        (r'\[([a-z-]+)\]\s*(.+)', 2),
        (r'--model[=\s]+([a-z-]+)\s+(.+)', 2),
        (r'-m\s+([a-z-]+)\s+(.+)', 2),
        (r'([a-z-]+)\s+model\s+(.+)', 2),
        (r'^([a-z-]+)\s+(.+)', 2)
    ]
    
    query_lower = query.lower()
    
    for pattern, query_group in model_patterns:
        match = re.search(pattern, query_lower)
        if match:
            model_name = match.group(1).lower()
            
            if model_name in openai_models:
                cleaned_query = match.group(query_group).strip() if query_group else query
                cleaned_query = re.sub(r'\s+', ' ', cleaned_query)
                cleaned_query = re.sub(r'^[-\s]+', '', cleaned_query)
                cleaned_query = cleaned_query.strip()
                
                actual_model = openai_models[model_name]
                return actual_model, cleaned_query
    
    return "gpt-4o-mini", query