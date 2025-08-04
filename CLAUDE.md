# Discord Bot - Development Context

## Project Architecture

### Core System
- **Entry Point**: `main.py` - Bot initialization, cog loading, logging setup
- **Command Prefix**: `!` for slash commands
- **AI Routing**: Hybrid system using Groq (chat) + Claude (admin/optimization) + Perplexity (search analysis)
- **Context Management**: Claude Haiku-powered filtering across multiple context types

### File Structure
```
main.py                        # Entry point with bot setup
dune_crafting.py              # Standalone crafting module
data/dune_recipes.json        # 250+ recipes database (v6.3)
src/
├── config.py                 # Configuration with environment validation
├── admin/                    # Admin system (2-phase parsing)
│   ├── parser.py            # Action identification orchestrator  
│   ├── extractors.py        # 13 parameter extractors
│   ├── utils.py             # User/role/channel finding utilities
│   ├── actions.py           # Admin action execution
│   └── permissions.py       # Admin permission checking
├── ai/
│   ├── handler_refactored.py # Main AI routing and processing
│   ├── context_manager.py   # Context filtering with Claude Haiku
│   ├── routing.py           # Query routing keywords and logic
│   └── crafting_module.py   # Crafting system integration
├── commands/                # Discord slash commands
│   ├── basic.py            # hello, ping
│   ├── history.py          # Context management commands  
│   ├── admin.py            # Admin panel commands
│   ├── help.py             # Help system
│   └── search_context.py   # Context search utilities
├── events/
│   └── handlers.py         # Discord event processing
├── search/                 # Search system architecture
│   ├── search_pipeline.py  # Generic search interface
│   ├── hybrid_search_provider.py # Claude+Perplexity (default)
│   ├── claude_adapter.py   # Pure Claude search
│   ├── perplexity_adapter.py # Pure Perplexity search
│   ├── claude.py           # Legacy Claude functions
│   ├── perplexity.py       # Legacy Perplexity functions
│   └── google.py           # Google Custom Search
├── data/
│   └── persistence.py      # JSON data storage with async locks
└── utils/
    ├── logging.py          # Centralized logging system
    └── message_utils.py    # Message handling utilities
```

## Configuration

### Required Environment Variables
```
DISCORD_TOKEN               # Discord bot token
AUTHORIZED_USER_ID          # Admin user ID (integer)
```

### Optional API Keys
```
GROQ_API_KEY               # For chat functionality
ANTHROPIC_API_KEY          # For admin commands and search optimization  
PERPLEXITY_API_KEY         # For search result analysis
GOOGLE_API_KEY             # For web search
GOOGLE_SEARCH_ENGINE_ID    # Google Custom Search Engine ID
```

### AI Configuration Defaults
```python
AI_MODEL = "llama-3.1-8b-instant"  # Groq model
AI_MAX_TOKENS = 1000
AI_TEMPERATURE = 0.7                # Groq temperature
AI_RATE_LIMIT_REQUESTS = 10         # Per user per minute
AI_RATE_LIMIT_WINDOW = 60           # Seconds
CHANNEL_CONTEXT_LIMIT = 50          # Messages stored per channel
CHANNEL_CONTEXT_DISPLAY = 35        # Messages shown to AI
```

### Discord Intents Currently Set
```python
intents = discord.Intents.default()
intents.message_content = True
# NOTE: Guild Members Intent NOT set in code but required for admin commands
```

## AI Models and Temperatures

### Groq Configuration
- **Model**: `llama-3.1-8b-instant`
- **Temperature**: 0.7 (configurable via AI_TEMPERATURE)
- **Max Tokens**: 1000
- **Use**: General chat, conversations

### Claude Configuration  
- **Models**: `claude-3-5-haiku-20241022` (default), `claude-3-5-sonnet`, `claude-3-opus`
- **Temperature**: 0.2 (hardcoded for search tasks)
- **Use**: Admin commands, search optimization, context filtering

### Perplexity Configuration
- **Model**: `sonar`
- **Temperature**: 0.1-0.2 (varies by function)
- **Use**: Search result analysis and summarization

## Admin System Architecture

### 13 Admin Action Types
```python
extractor_map = {
    'kick_user': extract_kick_params,
    'ban_user': extract_ban_params, 
    'unban_user': extract_unban_params,
    'timeout_user': extract_timeout_params,
    'remove_timeout': extract_remove_timeout_params,
    'change_nickname': extract_nickname_params,
    'add_role': extract_add_role_params,
    'remove_role': extract_remove_role_params,
    'rename_role': extract_rename_role_params,
    'reorganize_roles': extract_reorganize_roles_params,
    'bulk_delete': extract_bulk_delete_params,
    'create_channel': extract_create_channel_params,
    'delete_channel': extract_delete_channel_params,
}
```

### Two-Phase Parsing Process
1. **Action Identification** (`parser.py`): Determines which admin action type
2. **Parameter Extraction** (`extractors.py`): Extracts specific parameters for that action

### Admin Permission System
- Checks user ID against `AUTHORIZED_USER_ID` in config
- All admin actions require reaction-based confirmation (✅/❌)

## Context Management System

### Context Storage Limits
```python
# Conversation context (shared between all AIs)
unified_conversations: deque(maxlen=12)  # 6 exchanges (user+assistant pairs)
context_expiry_minutes = 30

# Channel context (for situational awareness)  
channel_conversations: deque(maxlen=50)  # 50 messages per channel
# Displayed to AI: 35 messages (CHANNEL_CONTEXT_DISPLAY)
```

### Context Types
1. **Conversation Context**: Recent AI interactions per user/channel (12 messages, 30min expiry)
2. **Channel Context**: General channel messages (50 stored, 35 shown, loaded from Discord history on startup)
3. **Permanent Context**: User-specific info, filtered per query by Claude Haiku
4. **Settings (Unfiltered)**: Global preferences, bypass all filtering

### Context Filtering
- **All filtering uses Claude Haiku** (`claude-3-5-haiku-20241022`)
- **Temperature**: 0.1 for context filtering tasks
- **Max Tokens**: 300-600 depending on task
- **Filtering Types**: Conversation, permanent, and unified context filtering

## Search System Architecture

### Hybrid Search (Default)
```python
class HybridSearchProvider:
    # Claude Haiku: Fast, cost-effective query optimization
    # Perplexity Sonar: High-quality result analysis
```

### Search Routing Keywords
**Triggers Claude/Perplexity search:**
- Current events: `current`, `latest`, `recent`, `today`, `2025`
- Questions: `what is`, `who is`, `how to`, `when will`
- Comparisons: `vs`, `versus`, `better`, `compare`
- Research: `search for`, `find`, `tell me about`

### Force Provider Syntax
- `groq:` or `g:` - Force Groq
- `claude:` - Hybrid search (default)
- `pure-claude:` - Claude only
- `perplexity:` or `p:` - Perplexity only  
- `search:` - Direct Google search

## Command System

### Slash Commands Available
```python
# Basic Commands (basic.py)
!hello                        # Greeting
!ping                         # Response time check

# Context Management (history.py)  
!add_setting <text>          # Add unfiltered setting
!list_settings               # View all settings
!remove_setting <index>      # Remove specific setting
!clear_settings              # Clear all settings
!history                     # Show conversation history
!context                     # Show context information

# Admin Commands (admin.py)
!admin_panel                 # Administrative interface
!stats                       # Bot statistics
!remember <text>             # Add permanent context  
!memories                    # List permanent context
!forget <index>              # Remove permanent context

# Search Context (search_context.py)
!clear_search_context        # Clear context
!search_context_info         # Context status
!clear_all_search_contexts   # Admin: clear all contexts

# Help System (help.py)
!help [category]             # Comprehensive help
```

### Primary Interface: @mentions
- Main bot interaction through Discord mentions
- Natural language admin commands with AI parsing
- Crafting requests: `@bot craft: <request>`

## Data Persistence

### JSON Files
```python
# File locations (configurable)
SETTINGS_FILE = 'data/user_settings.json'
PERMANENT_CONTEXT_FILE = 'data/permanent_context.json' 
UNFILTERED_PERMANENT_CONTEXT_FILE = 'data/unfiltered_permanent_context.json'
HISTORY_FILE = 'data/conversation_history.json'
```

### Data Structure
- **Conversation History**: Per-user conversation tracking
- **User Settings**: Individual preferences  
- **Permanent Context**: User-specific information, filtered per query
- **Unfiltered Context**: Global settings, always applied
- **Thread Safety**: Async locks for concurrent access

## Crafting System

### Database Details
- **File**: `data/dune_recipes.json` 
- **Version**: 6.3 (last updated 2025-01-03)
- **Total Recipes**: 250+
- **Material Tiers**: Copper → Iron → Steel → Aluminum → Duraluminum → Plastanium
- **Categories**: Weapons, vehicles, tools, equipment

### Integration
- **Module**: `dune_crafting.py` (standalone)
- **AI Integration**: `src/ai/crafting_module.py`
- **Natural Language**: AI-powered request interpretation
- **Functions**: Material calculation, recipe lookup, crafting trees

## Rate Limiting
- **Global Limit**: 10 requests per 60 seconds per user
- **Applies To**: All AI providers (Groq, Claude, Perplexity)
- **Reset**: Automatic after window expires

## Common Development Issues

### "Command not recognized as admin action"
- **Cause**: Missing Guild Members Intent in Discord Developer Portal
- **Code Issue**: Bot can only see itself in `guild.members`
- **Solution**: Enable "Server Members Intent" in Discord portal + restart bot

### Missing Admin Functionality  
- **Required Intent**: Guild Members Intent (not set in code)
- **Current Code**: Only sets `message_content = True`
- **Impact**: Admin commands requiring user lookup will fail

### Context Filtering Failures
- **Dependency**: Requires `ANTHROPIC_API_KEY` for Claude Haiku
- **Fallback**: Basic context without filtering if Claude unavailable
- **Debug**: Check API key configuration and rate limits

### Search System Issues
- **Hybrid Search**: Requires both Claude and Perplexity API keys for optimal function
- **Fallbacks**: Pure Claude if Perplexity unavailable
- **Google Search**: Requires both `GOOGLE_API_KEY` and `GOOGLE_SEARCH_ENGINE_ID`

## Development Notes

### Recent Architecture Changes
- **Admin System**: Split from monolithic parser to modular 2-phase system
- **Context Filtering**: Migrated from Groq to Claude Haiku for consistency
- **Crafting Database**: Expanded from 79+ to 250+ recipes
- **Command Naming**: Settings commands changed from `unfiltered_permanent_context` to `add_setting` etc.

### Code Quality
- **Logging**: Centralized system with proper levels
- **Type Hints**: Comprehensive annotations  
- **Async**: Full async/await implementation
- **Error Handling**: Graceful fallbacks and user-friendly messages
- **Debug Cleanup**: Print statements removed from admin system