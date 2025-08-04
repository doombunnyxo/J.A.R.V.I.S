# Discord Bot - CLAUDE.md

## Project Overview
This is a Discord bot with hybrid AI functionality that combines Groq and Claude APIs for intelligent routing of queries. The bot provides chat capabilities, web search integration, admin tools, crafting systems, and comprehensive conversation context management.

**📅 Last Updated**: January 2025 (Major Refactoring Complete)

## Architecture Overview

### Core Philosophy
- **Hybrid AI Routing**: Intelligent selection between Groq (chat/admin) and Claude (web search)  
- **Shared Context**: Unified conversation context across both AI providers
- **Modular Design**: Clean separation of concerns across modules
- **Discord-Optimized**: Responses formatted specifically for Discord markdown
- **Production Ready**: Professional logging, error handling, and type safety

### Main Entry Point
- **main.py** - Bot initialization, cog loading, and startup sequence with centralized logging
- Uses asyncio for async/await operations
- Loads configuration, initializes handlers, and starts the Discord bot
- **NEW**: Comprehensive logging system with structured output

### Core Configuration
- **src/config.py** - Centralized configuration management with environment validation and logging
- **Environment Variables Required:**
  - `DISCORD_TOKEN` - Discord bot token (required)
  - `AUTHORIZED_USER_ID` - Admin user ID (required)
  - `GROQ_API_KEY` - Groq API key (optional)
  - `ANTHROPIC_API_KEY` - Claude API key (optional)
  - `GOOGLE_API_KEY` - Google Search API key (optional)
  - `GOOGLE_SEARCH_ENGINE_ID` - Google Custom Search Engine ID (optional)

## Key Features

### 1. Hybrid AI System (src/ai/)

#### AI Handler (handler_refactored.py)
**Core functionality**: Hybrid AI routing system with intelligent query distribution
- **Claude**: Used for web search queries, current events, comparisons, research, and admin commands
- **Groq**: Used for general chat processing, personal interactions, explanations
- **Rate Limiting**: 10 requests per 60 seconds per user with automatic reset tracking
- **Context Management**: Unified conversation context shared between both AIs
- **Admin Action Detection**: Parses admin intents and handles confirmations
- **NEW**: Comprehensive logging with debug tracing and error handling
- **NEW**: Consolidated architecture - removed all legacy code

#### Routing System (routing.py)
**Core functionality**: Intelligent query routing logic
- **Search Indicators**: Keywords that trigger Claude routing (current, latest, news, etc.)
- **Admin Keywords**: Commands that trigger Claude routing (kick, ban, timeout, etc.)
- **Force Provider Syntax**: 
  - `groq:` or `g:` - Force Groq processing
  - `claude:` or `perplexity:` - Force Claude processing (hybrid)
  - `pure-claude:` or `claude-only:` - Pure Claude only
  - `pure-perplexity:` or `perplexity-only:` - Pure Perplexity only
  - `search:` - Direct Google search
- **Model Selection**: Admin users can specify Claude models (haiku, sonnet, opus)

#### Context Manager (context_manager.py)
**Core functionality**: Sophisticated context management across AI providers
- **Unified Context**: Shared conversation history between all AI providers
- **Context Filtering**: Uses Claude Haiku to filter context for relevance to each query
- **Context Types**:
  - **Conversation Context**: Recent chat history (expires after 30 minutes)
  - **Permanent Context**: User preferences and info (filtered per query)
  - **Unfiltered Context**: Critical settings (always included, never filtered)
- **User Mention Resolution**: Converts Discord mentions to usernames in context
- **NEW**: Integrated logging for all context operations

### 2. Enhanced Search Integration (src/search/)

#### Unified Search Pipeline (search_pipeline.py)
**Core functionality**: Generic search flow that works with any AI provider
- **Protocol-Based Design**: Uses SearchProvider protocol for extensibility
- **Standard Flow**: Optimize query → Google search → analyze results
- **Provider Agnostic**: Works with Claude, Perplexity, or any future providers
- **NEW**: Comprehensive error handling and logging

#### Hybrid Search Provider (hybrid_search_provider.py)
**Core functionality**: Optimal cost/quality balance combining Claude and Perplexity
- **Claude Query Optimization**: Fast, cheap query refinement with Claude Haiku
- **Perplexity Result Analysis**: High-quality summarization with Perplexity Sonar
- **Cost Optimization**: Minimizes expensive operations while maximizing response quality (~$0.002 vs $5+)
- **Default Search Method**: Used automatically for all search queries
- **NEW**: Enhanced error recovery and fallback mechanisms

#### Claude Adapter (claude_adapter.py)
**Core functionality**: Pure Claude integration for the unified search pipeline
- **Complete Claude Pipeline**: Both optimization and analysis with Claude
- **Model Support**: Haiku (default), Sonnet, Opus for admin users
- **Force Provider Support**: Accessible via `pure-claude:` and `claude-only:` prefixes
- **Fallback Option**: Used when Perplexity is unavailable in hybrid mode
- **NEW**: Direct Claude API integration with proper async handling

#### Perplexity Adapter (perplexity_adapter.py)
**Core functionality**: Pure Perplexity integration for the unified search pipeline
- **Complete Perplexity Pipeline**: Both optimization and analysis with Sonar model
- **High-Quality Results**: Premium analysis but higher cost per request
- **Force Provider Support**: Accessible via `pure-perplexity:` and `perplexity-only:` prefixes
- **NEW**: Enhanced timeout handling and error recovery

#### Google Search (google.py)
**Core functionality**: Google Custom Search Engine integration
- **Web Search**: Retrieves current information from the web
- **Result Formatting**: Formats results for AI provider processing
- **Cog Commands**: Direct `!search` command for users
- **Pipeline Integration**: Provides search data for unified pipeline

### 3. Enhanced Data Persistence (src/data/persistence.py)
**Core functionality**: Manages persistent data storage across bot restarts
- **Conversation History**: Per-user conversation tracking
- **User Settings**: Individual user preferences (channel context, etc.)
- **Permanent Context**: Long-term user context storage with filtering
- **Unfiltered Context**: Critical user settings that bypass filtering
- **File Storage**: JSON files in `data/` directory
- **Async Operations**: Thread-safe data operations with locks
- **NEW**: Comprehensive error logging and data integrity checks
- **NEW**: Graceful handling of corrupted data with recovery

### 4. Enhanced Admin System (src/admin/)

#### Permissions (permissions.py)
**Core functionality**: Admin user validation
- **User ID Checking**: Validates admin permissions
- **Role-Based Access**: Future extensibility for role-based admin

#### Actions (actions.py)
**Core functionality**: Execute admin commands with proper error handling
- **User Moderation**: Kick, ban, timeout with proper permission checks
- **Role Management**: Create, delete, rename roles with hierarchy validation
- **Channel Management**: Create, delete, modify channels
- **Message Management**: Bulk delete with user filtering
- **NEW**: Fixed discord.User vs discord.Member handling for nickname changes
- **NEW**: Enhanced error messages for permission issues
- **NEW**: Proper reason logging for all actions

#### Parser (parser.py)
**Core functionality**: Natural language admin intent parsing
- **User Detection**: Handles mentions, pronouns, and name matching
- **Action Classification**: Identifies admin intentions from natural language
- **Parameter Extraction**: Extracts targets, durations, reasons from text
- **NEW**: Only returns discord.Member objects for server operations
- **NEW**: Clear error handling when users not found in server
- **NEW**: Enhanced logging for debugging parsing issues

#### Safety Features
- **Reaction Confirmations**: ✅/❌ reactions for admin action approval
- **Permission Validation**: All admin actions require explicit confirmation
- **Error Recovery**: Graceful handling of permission and API errors

### 5. Enhanced Commands System (src/commands/)

#### Basic Commands (basic.py)
**Core functionality**: Essential bot commands
- **Hello/Ping**: Basic interaction commands
- **NEW**: Type hints and proper error handling

#### Admin Commands (admin.py)
**Core functionality**: Admin panel and controls
- **Admin Panel**: Comprehensive administrative interface
- **Pending Actions**: View and manage pending admin actions
- **NEW**: Enhanced error handling and logging

#### History Management (history.py)
**Core functionality**: Conversation history commands
- **History Display**: Show recent conversation history
- **History Clearing**: Clear user conversation history
- **NEW**: Improved error handling and user feedback

#### Help System (help.py)
**Core functionality**: Comprehensive help system
- **Dynamic Help**: Context-aware help with categories
- **Category-Specific**: Detailed help for AI, context, admin, crafting
- **Usage Examples**: Clear examples for all features
- **NEW**: Completely rewritten for accuracy and completeness

#### Context Commands (search_context.py)
**Core functionality**: Context search and management
- **Context Clearing**: Clear conversation context for all AI providers
- **Context Info**: Show current context status across providers
- **Admin Context Management**: Clear all user contexts (admin only)
- **NEW**: Migrated from legacy perplexity module to unified architecture
- **NEW**: Support for all AI providers (Groq, Claude, hybrid, etc.)
- **NEW**: Enhanced provider display with proper icons and descriptions

### 6. Enhanced Crafting System (src/crafting/ + data/dune_recipes.json)

#### Crafting Module (crafting_module.py)
**Core functionality**: Comprehensive Dune Awakening crafting calculator
- **79+ Recipes**: Complete weapon database with 7-tier progression
- **Weapon Categories**:
  - **Standard Weapons**: Karpov 38, Maula Pistol, Disruptor M11, Sword, Rapier, JABAL Spitdart, Drillshot FK7, GRDA 44, Dirk, Kindjal
  - **Unique Weapons**: Piters Disruptor, The Tapper, Eviscerator, Way of the Desert, etc.
  - **Equipment**: Stillsuits, Spice Masks, Desert Garb
  - **Materials**: Full progression from Salvage → Plastanium
- **Material Tiers**: Salvage (2 intel) → Copper (5) → Iron (10) → Steel (20) → Aluminum (30) → Duraluminum (40) → Plastanium (40)
- **Natural Language**: AI-powered recipe interpretation
- **JSON Database**: Separated recipe data for maintainability
- **NEW**: Migrated from legacy AnthropicAPI to direct Claude API calls
- **NEW**: Enhanced error handling and logging throughout
- **NEW**: Improved async performance with proper timeout handling

### 7. Enhanced Event Handling (src/events/handlers.py)
**Core functionality**: Discord event processing and message routing
- **Message Processing**: Routes mentions to appropriate handlers
- **Force Provider Detection**: Parses force syntax for AI routing
- **Admin Confirmations**: Handles reaction-based admin confirmations
- **Context Integration**: Manages conversation context across interactions
- **NEW**: Comprehensive type hints for all functions
- **NEW**: Enhanced error handling and logging
- **NEW**: Proper Discord object type validation

### 8. NEW: Centralized Logging System (src/utils/logging.py)
**Core functionality**: Professional logging infrastructure
- **Centralized Configuration**: Single point for all logging setup
- **File + Console Output**: Logs to both file (`logs/discord_bot.log`) and console
- **Configurable Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Module-Specific Loggers**: Each module gets its own logger with `get_logger(__name__)`
- **Structured Output**: Timestamp, module, level, and message formatting
- **Log Rotation**: Automatic log file management
- **Production Ready**: Suitable for systemd and production deployments

## File Structure
```
discord-bot/
├── main.py                    # Bot entry point with centralized logging
├── requirements.txt           # Python dependencies (updated)
├── pyproject.toml            # Project configuration
├── CLAUDE.md                 # This documentation (COMPLETELY UPDATED)
├── README.md                 # User documentation (COMPLETELY UPDATED)
├── logs/                     # Log files (auto-created)
│   └── discord_bot.log       # Main log file with rotation
├── data/                     # Persistent data storage
│   ├── dune_recipes.json     # Crafting database (79+ recipes)
│   ├── conversation_history.json  # User conversations
│   ├── permanent_context.json     # User permanent context
│   ├── unfiltered_permanent_context.json  # Unfiltered user settings
│   └── user_settings.json    # User preferences
└── src/
    ├── config.py             # Configuration management (enhanced with logging)
    ├── admin/                # Enhanced admin system
    │   ├── actions.py        # Admin action execution (fixed User/Member handling)
    │   ├── parser.py         # Intent parsing (enhanced error handling)
    │   └── permissions.py    # Permission checking
    ├── ai/                   # AI routing and processing
    │   ├── handler_refactored.py  # Main AI handler (consolidated, no legacy)
    │   ├── routing.py        # Query routing logic 
    │   ├── context_manager.py    # Context management (enhanced logging)
    │   └── crafting_module.py    # Crafting system (migrated to direct Claude API)
    ├── commands/             # Discord commands (enhanced with type hints)
    │   ├── basic.py          # Basic commands
    │   ├── admin.py          # Admin commands
    │   ├── history.py        # History management
    │   ├── help.py           # Help system (COMPLETELY REWRITTEN)
    │   └── search_context.py # Context search (MIGRATED from legacy)
    ├── data/
    │   └── persistence.py    # Data storage management (enhanced logging)
    ├── events/
    │   └── handlers.py       # Discord event handlers (enhanced with type hints)
    ├── search/               # Unified search integrations
    │   ├── search_pipeline.py    # Unified search pipeline
    │   ├── hybrid_search_provider.py # Hybrid Claude+Perplexity provider (default)
    │   ├── claude_adapter.py     # Pure Claude search provider (enhanced)
    │   ├── perplexity_adapter.py # Pure Perplexity search provider (enhanced)
    │   ├── claude.py         # Claude API functions (legacy compatibility)
    │   ├── perplexity.py     # Perplexity API functions (legacy compatibility)
    │   └── google.py         # Google Custom Search
    ├── scraping/
    │   └── web_scraper.py    # Web scraping utilities
    └── utils/
        ├── message_utils.py  # Message handling utilities
        └── logging.py        # NEW: Centralized logging system
```

## Dependencies
- **discord.py** (2.5.2) - Discord API wrapper (updated)
- **groq** (0.30.0) - Groq API client
- **openai** (1.57.0) - OpenAI API client (for compatibility)
- **aiohttp** (3.9.1) - Async HTTP client for Claude and Perplexity
- **google-api-python-client** (2.108.0) - Google Search API
- **python-dotenv** (1.0.0) - Environment variable management

## Bot Commands

### AI Interaction (Primary Interface)
**Main Usage**: `@mention the bot + your message`

#### Automatic Routing
- **Claude (Search/Admin)** triggers:
  - Admin commands (kick, ban, timeout, role management)
  - Current events, news, latest information
  - Research questions, comparisons ("vs", "better")
  - Questions ("what are", "how much", "when will")
  - Current topics (crypto, tech, gaming, etc.)
- **Groq (Chat)** triggers:
  - Personal conversations, jokes, explanations
  - Short greetings and interactions
  - General Q&A and casual chat

#### Force Specific Provider
- `@bot groq: your question` or `@bot g: question` - Force Groq
- `@bot claude: your question` or `@bot hybrid: question` - Hybrid search (default)
- `@bot pure-claude: question` or `@bot claude-only: question` - Pure Claude only
- `@bot perplexity: question` or `@bot p: question` - Pure Perplexity
- `@bot pure-perplexity: question` - Pure Perplexity only
- `@bot search: query` - Direct Google search
- `@bot craft: item request` - Crafting system

#### Admin Model Control (Admin Only)
- `@bot use haiku to find crypto trends` - Fast, cost-effective
- `@bot with sonnet analyze this data` - Balanced performance  
- `@bot model: opus - comprehensive research` - Most capable

### Enhanced Context Management Commands
- `!permanent_context <text>` - Add permanent context (filtered)
- `!list_permanent_context` - View your permanent context items
- `!remove_permanent_context <index>` - Remove specific item by number
- `!clear_permanent_context` - Remove all permanent context
- `!unfiltered_permanent_context <text>` - Add unfiltered context (always applied)
- `!list_unfiltered_permanent_context` - View unfiltered items
- `!clear_context` - Clear conversation context
- `!context_info` - Show context status across all providers
- `!search_context <query>` - Search your context items

### Basic Commands
- `!hello` - Greet the bot
- `!ping` - Check responsiveness
- `!help` - **COMPLETELY REWRITTEN** comprehensive help system
- `!help <category>` - Detailed category help (ai, context, admin, crafting, etc.)

### Enhanced Crafting Commands
- `@bot craft: I need 5 healing kits` - Natural language crafting
- `@bot craft: iron sword` - Direct item requests
- `@bot craft: list weapons` - Show weapon categories
- `@bot craft: list vehicles` - Show vehicle components
- `@bot craft: list tools` - Show tool categories

### Enhanced Admin Commands (Admin Only)
**Natural language via @mention:**
- `@bot kick @spammer` - Remove user from server
- `@bot ban @troublemaker for harassment` - Permanent ban
- `@bot timeout @user for 1 hour` - Temporary mute
- `@bot delete 10 messages` - Bulk delete messages
- `@bot delete 5 messages from @user` - Delete specific user's messages
- `@bot add role Moderator to @user` - Role management
- `@bot rename role "Old Name" to "New Name"` - Role renaming
- `@bot change @user nickname to "NewName"` - Nickname changes (FIXED)
- `@bot create text channel general-chat` - Channel management
- `!admin_panel` - Administrative control interface

## Configuration Details

### AI Models and Routing
- **Groq Model**: llama-3.1-8b-instant
- **Claude Models**: 
  - claude-3-5-haiku-20241022 (default) - Fast, cost-effective
  - claude-3-5-sonnet - Balanced performance
  - claude-3-opus - Most capable
- **Max Tokens**: 1000 (Groq), 1000 (Claude)
- **Temperature**: 0.7 (Groq), 0.2 (Claude search)
- **Rate Limiting**: 10 requests per 60 seconds per user with automatic reset

### Enhanced Context Management
- **Conversation Context**: 12 message limit shared between AIs
- **Context Expiry**: 30 minutes of inactivity
- **Channel Context**: 50 messages max, 35 displayed
- **Permanent Context**: Unlimited, filtered per query using Claude Haiku
- **Unfiltered Context**: Always included, never filtered, critical settings only

### Data Storage
- **Recipes**: `data/dune_recipes.json` (79 items, 7 tiers, 10+ weapon series)
- **User Data**: `data/` directory with JSON files
- **Context Persistence**: Survives bot restarts
- **Logging**: `logs/discord_bot.log` with automatic rotation
- **Git Integration**: Static data included, user data and logs ignored

## Development Notes

### Key Classes
- **AIHandler**: Main AI processing and routing logic (handler_refactored.py) - CONSOLIDATED
- **SearchPipeline**: Generic search flow with provider adapters
- **ContextManager**: Unified context management across AIs with enhanced logging
- **CraftingProcessor**: Dedicated crafting system with direct Claude API integration
- **DataManager**: Persistent data management with comprehensive error handling
- **Logger**: Centralized logging system for all modules

### Design Patterns
- **Unified Search Pipeline**: Generic search architecture with provider adapters
- **Protocol-Based Design**: SearchProvider protocol for extensibility
- **Hybrid AI Routing**: Intelligent selection between Groq, Claude, and Perplexity
- **Modular Architecture**: Clean separation of routing, context, search, and crafting
- **Rate Limiting**: Per-user request throttling with automatic reset timers
- **Confirmation System**: Reaction-based admin action approval
- **Discord Optimization**: Responses formatted for Discord markdown
- **NEW**: Centralized logging with structured output and proper levels
- **NEW**: Type safety with comprehensive type hints throughout
- **NEW**: Proper async/await patterns for all I/O operations

### Recent Major Refactoring (January 2025)

#### 🔄 **Architecture Improvements**
1. **Consolidated AI Handler**: Removed all legacy code, single handler architecture
2. **Enhanced Search System**: Unified pipeline with provider adapters
3. **Fixed User/Member Handling**: Proper discord.Member vs discord.User distinction
4. **Migrated Legacy Modules**: search_context.py and crafting_module.py updated

#### 🚀 **Code Quality Enhancements**
1. **Centralized Logging**: Professional logging system replacing all print statements
2. **Type Hints**: Comprehensive type annotations for better IDE support and safety
3. **Error Handling**: User-friendly error messages with proper exception handling
4. **Async Architecture**: Full async/await implementation for performance
5. **Code Cleanup**: Removed duplicate files, unused imports, and bare except clauses

#### 🛡️ **Error Handling & Security**
1. **Fixed Admin Actions**: Proper Member object handling for nickname changes
2. **Enhanced Error Messages**: Clear, user-friendly error descriptions
3. **Improved Validation**: Better input validation and permission checking
4. **Logging Integration**: All operations properly logged with context

#### 📁 **File Organization**
1. **Removed Duplicates**: Cleaned up duplicate JSON files from root directory
2. **Enhanced Documentation**: Completely updated README.md and CLAUDE.md
3. **Project Configuration**: Added pyproject.toml for modern Python packaging
4. **Log Management**: Auto-created logs directory with proper rotation

### Security Features
- **Admin Permission Checking**: Restricted admin functionality with proper validation
- **Rate Limiting**: Prevents spam and abuse with per-user tracking and automatic reset
- **Input Validation**: Validates user inputs and commands with type safety
- **Confirmation System**: All admin actions require explicit approval via reactions
- **Context Filtering**: Prevents cross-user context leakage with proper isolation
- **Error Handling**: Comprehensive exception handling with fallbacks and logging
- **Member Validation**: Proper Discord Member vs User object handling

## Troubleshooting

### API Configuration
1. **Groq API**: Set `GROQ_API_KEY` for chat/admin functionality
2. **Claude API**: Set `ANTHROPIC_API_KEY` for web search and crafting
3. **Google Search**: Set `GOOGLE_API_KEY` and `GOOGLE_SEARCH_ENGINE_ID`
4. **Discord Bot**: Set `DISCORD_TOKEN` and `AUTHORIZED_USER_ID`

### Common Issues
1. **Missing Context**: Check if context files exist in `data/` directory
2. **Search Failures**: Verify Google Search API configuration
3. **Admin Actions**: Ensure user ID is in `AUTHORIZED_USER_ID`
4. **Rate Limiting**: Users throttled after 10 requests/minute with automatic reset
5. **Memory Issues**: Context automatically expires after 30 minutes
6. **User/Member Errors**: Bot now shows clear messages when operations require server membership
7. **Logging Issues**: Check `logs/discord_bot.log` for detailed error information

### NEW: Enhanced Debugging
```bash
# Check logging system
python -c "from src.utils.logging import get_logger; get_logger('test').info('Test message')"

# Test configuration
python -c "from src.config import config; print('Config valid:', config.is_valid())"

# View recent logs
tail -f logs/discord_bot.log

# Test module imports
python -c "import main; print('Main module loads successfully')"
```

### Performance Metrics
- **Response Time**: ~2-3 seconds for Claude search queries
- **Context Processing**: ~500ms for context filtering with Claude Haiku
- **Memory Usage**: Efficient with automatic context cleanup
- **Cost Efficiency**: ~$0.002 per Claude request vs $5+ Perplexity
- **Rate Limits**: 10 requests/user/minute with automatic reset tracking
- **Logging Overhead**: Minimal performance impact with structured logging

## Best Practices
1. **Environment Variables**: Use `.env` file for sensitive data
2. **Error Handling**: Bot gracefully handles API failures with user-friendly messages
3. **Context Management**: Automatic cleanup prevents memory issues
4. **Admin Safety**: All admin actions require explicit confirmation via reactions
5. **Rate Limiting**: Built-in protection against spam and abuse with automatic reset
6. **Modular Design**: Easy to extend and maintain with proper separation of concerns
7. **Discord Optimization**: Responses formatted for best user experience
8. **NEW**: Proper logging for debugging and monitoring
9. **NEW**: Type safety for better code quality and IDE support
10. **NEW**: Async patterns for optimal performance

## Future Enhancements
- **Additional AI Providers**: Easy to add via SearchProvider protocol
- **Enhanced Admin Features**: More granular permission system
- **Advanced Context Management**: ML-powered context relevance scoring
- **Performance Monitoring**: Built-in metrics and monitoring dashboard
- **API Usage Analytics**: Detailed cost and usage tracking
- **Multi-Server Support**: Enhanced scalability for multiple Discord servers