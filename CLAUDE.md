# J.A.R.V.I.S Discord Bot - Development Context

## Project Architecture

### Core System
- **Entry Point**: `main.py` - Bot initialization, cog loading, logging setup
- **Command Prefix**: `!` for slash commands
- **AI System**: OpenAI-only system with intelligent routing
- **Context Management**: OpenAI GPT-4o mini-powered filtering and context awareness

### File Structure
```
main.py                        # Entry point with bot setup
dune_crafting.py              # Standalone crafting module
data/dune_recipes.json        # 250+ recipes database (v6.3)
src/
├── config.py                 # Configuration with environment validation
├── ai/
│   ├── handler_refactored.py # Main AI routing and processing
│   ├── context_manager.py    # Context filtering with OpenAI GPT-4o mini
│   ├── openai_client.py      # Centralized OpenAI client
│   ├── routing.py            # Query routing keywords and logic
│   └── crafting_module.py    # Crafting system integration
├── admin/
│   ├── admin_processor.py    # Admin command orchestrator
│   ├── parser.py             # Two-phase action identification
│   ├── extractors.py         # 13 parameter extractors
│   ├── actions.py            # Admin action execution
│   └── permissions.py        # Admin permission checking
├── search/
│   ├── search_pipeline.py    # Search orchestration
│   ├── openai_adapter.py     # OpenAI search provider
│   ├── google.py             # Google Custom Search
│   └── web_extractor.py      # Web content extraction
├── commands/                 # Discord slash commands
├── events/
│   └── handlers.py           # Discord event processing
├── data/
│   └── persistence.py        # JSON data storage with async locks
└── utils/
    ├── logging.py            # Centralized logging system
    └── message_utils.py      # Message handling utilities
```

## Configuration

### Required Environment Variables
```
DISCORD_TOKEN               # Discord bot token
AUTHORIZED_USER_ID          # Admin user ID (integer)
```

### Optional API Keys
```
OPENAI_API_KEY             # Primary AI provider for all functionality
ANTHROPIC_API_KEY          # Legacy support (mostly unused)
GOOGLE_API_KEY             # For web search
GOOGLE_SEARCH_ENGINE_ID    # Google Custom Search Engine ID
```

### AI Configuration Defaults
```python
# OpenAI is the primary and only AI provider
AI_MODEL = "gpt-4o-mini"           # Default OpenAI model
AI_RATE_LIMIT_REQUESTS = 10        # Per user per minute
AI_RATE_LIMIT_WINDOW = 60          # Seconds
CHANNEL_CONTEXT_LIMIT = 50         # Messages stored per channel
CHANNEL_CONTEXT_DISPLAY = 35       # Messages shown to AI
```

### Discord Intents Required
```python
intents = discord.Intents.default()
intents.message_content = True
# NOTE: Guild Members Intent required for admin commands (set in Discord Portal)
```

## AI System Architecture

### OpenAI Models and Usage
- **gpt-4o-mini** (default): Context filtering, query optimization, general chat
- **gpt-4o**: Full page search, complex analysis
- **gpt-4-turbo**: Alternative high-performance option
- **gpt-4**: Maximum capability option
- **Temperature**: 0.1-0.2 (search/admin), 0.7 (direct chat)

### Centralized OpenAI Client
- **Location**: `src/ai/openai_client.py`
- **Features**: Singleton pattern, error handling, retries
- **Usage**: Single client instance for all OpenAI interactions

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
1. **Action Identification** (`parser.py`): Determines admin action type
2. **Parameter Extraction** (`extractors.py`): Extracts specific parameters

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
2. **Channel Context**: General channel messages (50 stored, 35 shown)
3. **Permanent Context**: User-specific info, filtered per query by OpenAI GPT-4o mini
4. **Settings (Unfiltered)**: Global preferences, bypass all filtering

### Context Filtering
- **All filtering uses OpenAI GPT-4o mini** (`gpt-4o-mini`)
- **Temperature**: 0.1 for context filtering tasks
- **Max Tokens**: 300-600 depending on task

## Search System Architecture

### OpenAI Search (Primary)
```python
class OpenAISearchProvider:
    # OpenAI GPT-4o mini: Query optimization and web search
    # Direct Google search integration
```

### Search Routing Keywords
**Triggers OpenAI search:**
- Current events: `current`, `latest`, `recent`, `today`, `2025`
- Questions: `what is`, `who is`, `how to`, `when will`
- Comparisons: `vs`, `versus`, `better`, `compare`
- Research: `search for`, `find`, `tell me about`

### Force Provider Syntax
- `ai:` - Direct OpenAI chat (bypasses search routing)
- `full:` - Full page search with GPT-4o
- `craft:` - Crafting system

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
- Main bot interaction through Discord mentions (defaults to OpenAI with search)
- Natural language admin commands with AI parsing
- Direct chat: `@bot ai: <message>` (OpenAI without search)
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
- **Applies To**: All OpenAI requests (search and direct chat)
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
- **Dependency**: Requires `OPENAI_API_KEY` for GPT-4o mini
- **Fallback**: Basic context without filtering if OpenAI unavailable
- **Debug**: Check API key configuration and rate limits

### Search System Issues
- **OpenAI Search**: Requires OpenAI API key for search functionality
- **Google Search**: Requires both `GOOGLE_API_KEY` and `GOOGLE_SEARCH_ENGINE_ID`
- **Web Extraction**: May fail on some sites, blacklist system handles this

## Development Notes

### Recent Architecture Changes
- **AI System**: Migrated to OpenAI-only system (removed Groq)
- **Direct Chat**: Added `ai:` command for OpenAI without search routing
- **Admin System**: Split from monolithic parser to modular 2-phase system
- **Context Filtering**: Uses OpenAI GPT-4o mini for all filtering
- **Crafting Database**: Expanded from 79+ to 250+ recipes
- **Code Cleanup**: Removed dead code, simplified routing, standardized patterns
- **Centralized Client**: All OpenAI usage now goes through single client

### Code Quality
- **Logging**: Centralized system with proper levels
- **Type Hints**: Comprehensive annotations  
- **Async**: Full async/await implementation
- **Error Handling**: Graceful fallbacks and user-friendly messages
- **Refactored**: Clean, maintainable code with consistent patterns

### Important Instructions
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.