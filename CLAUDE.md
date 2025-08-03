# Discord Bot - CLAUDE.md

## Project Overview
This is a Discord bot with hybrid AI functionality that combines Groq and Claude APIs for intelligent routing of queries. The bot provides chat capabilities, web search integration, admin tools, crafting systems, and comprehensive conversation context management.

## Architecture Overview

### Core Philosophy
- **Hybrid AI Routing**: Intelligent selection between Groq (chat/admin) and Claude (web search)  
- **Shared Context**: Unified conversation context across both AI providers
- **Modular Design**: Clean separation of concerns across modules
- **Discord-Optimized**: Responses formatted specifically for Discord markdown

### Main Entry Point
- **main.py** - Bot initialization, cog loading, and startup sequence
- Uses asyncio for async/await operations
- Loads configuration, initializes handlers, and starts the Discord bot

### Core Configuration
- **src/config.py** - Centralized configuration management with environment validation
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
- **Rate Limiting**: 10 requests per 60 seconds per user
- **Context Management**: Unified conversation context shared between both AIs
- **Admin Action Detection**: Parses admin intents and handles confirmations

#### Routing System (routing.py)
**Core functionality**: Intelligent query routing logic
- **Search Indicators**: Keywords that trigger Claude routing (current, latest, news, etc.)
- **Admin Keywords**: Commands that trigger Claude routing (kick, ban, timeout, etc.)
- **Force Provider Syntax**: 
  - `groq:` or `g:` - Force Groq processing
  - `claude:` or `perplexity:` - Force Claude processing
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

### 2. Search Integration (src/search/)

#### Unified Search Pipeline (search_pipeline.py)
**Core functionality**: Generic search flow that works with any AI provider
- **Protocol-Based Design**: Uses SearchProvider protocol for extensibility
- **Standard Flow**: Optimize query → Google search → analyze results
- **Provider Agnostic**: Works with Claude, Perplexity, or any future providers

#### Hybrid Search Provider (hybrid_search_provider.py)
**Core functionality**: Optimal cost/quality balance combining Claude and Perplexity
- **Claude Query Optimization**: Fast, cheap query refinement with Claude Haiku
- **Perplexity Result Analysis**: High-quality summarization with Perplexity Sonar
- **Cost Optimization**: Minimizes expensive operations while maximizing response quality
- **Default Search Method**: Used automatically for all search queries

#### Claude Adapter (claude_adapter.py)
**Core functionality**: Pure Claude integration for the unified search pipeline
- **Complete Claude Pipeline**: Both optimization and analysis with Claude
- **Model Support**: Haiku (default), Sonnet, Opus for admin users
- **Force Provider Support**: Accessible via `pure-claude:` and `claude-only:` prefixes
- **Fallback Option**: Used when Perplexity is unavailable in hybrid mode

#### Perplexity Adapter (perplexity_adapter.py)
**Core functionality**: Pure Perplexity integration for the unified search pipeline
- **Complete Perplexity Pipeline**: Both optimization and analysis with Sonar model
- **High-Quality Results**: Premium analysis but higher cost per request
- **Force Provider Support**: Accessible via `pure-perplexity:` and `perplexity-only:` prefixes

#### Google Search (google.py)
**Core functionality**: Google Custom Search Engine integration
- **Web Search**: Retrieves current information from the web
- **Result Formatting**: Formats results for AI provider processing
- **Cog Commands**: Direct `!search` command for users
- **Pipeline Integration**: Provides search data for unified pipeline

### 3. Data Persistence (src/data/persistence.py)
**Core functionality**: Manages persistent data storage across bot restarts
- **Conversation History**: Per-user conversation tracking
- **User Settings**: Individual user preferences (channel context, etc.)
- **Permanent Context**: Long-term user context storage with filtering
- **Unfiltered Context**: Critical user settings that bypass filtering
- **File Storage**: JSON files in `data/` directory
- **Async Operations**: Thread-safe data operations with locks

### 4. Admin System (src/admin/)
**Core functionality**: Comprehensive Discord server administration
- **Permissions** (permissions.py): Admin user validation
- **Actions** (actions.py): Execute admin commands (kick, ban, timeout, roles, channels)
- **Parser** (parser.py): Natural language admin intent parsing
- **Reaction Confirmations**: ✅/❌ reactions for admin action approval
- **Safety Features**: All admin actions require explicit confirmation

### 5. Commands System (src/commands/)
**Updated and comprehensive command structure**
- **Basic Commands** (basic.py): Hello, ping commands
- **Admin Commands** (admin.py): Admin panel and controls
- **History Management** (history.py): Conversation history commands
- **Help System** (help.py): **COMPLETELY REWRITTEN** - Accurate, comprehensive help
- **Context Commands** (search_context.py): Context search and management

### 6. Crafting System (src/crafting/ + data/dune_recipes.json)
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

### 7. Event Handling (src/events/handlers.py)
**Core functionality**: Discord event processing and message routing
- **Message Processing**: Routes mentions to appropriate handlers
- **Force Provider Detection**: Parses force syntax for AI routing
- **Admin Confirmations**: Handles reaction-based admin confirmations
- **Context Integration**: Manages conversation context across interactions

## File Structure
```
discord-bot/
├── main.py                    # Bot entry point
├── requirements.txt           # Python dependencies
├── CLAUDE.md                 # This documentation (UPDATED)
├── data/                     # Persistent data storage
│   ├── dune_recipes.json     # Crafting database (79+ recipes)
│   ├── conversation_history.json  # User conversations
│   ├── permanent_context.json     # User permanent context
│   ├── unfiltered_permanent_context.json  # Unfiltered user settings
│   └── user_settings.json    # User preferences
└── src/
    ├── config.py             # Configuration management
    ├── admin/                # Admin system
    │   ├── actions.py        # Admin action execution
    │   ├── parser.py         # Intent parsing
    │   └── permissions.py    # Permission checking
    ├── ai/                   # AI routing and processing
    │   ├── handler_refactored.py  # Main AI handler with unified search pipeline
    │   ├── routing.py        # Query routing logic 
    │   ├── context_manager.py    # Context management
    │   └── crafting_module.py    # Crafting system (extracted)
    ├── commands/             # Discord commands
    │   ├── basic.py          # Basic commands
    │   ├── admin.py          # Admin commands
    │   ├── history.py        # History management
    │   ├── help.py           # Help system (COMPLETELY REWRITTEN)
    │   └── search_context.py # Context search
    ├── data/
    │   └── persistence.py    # Data storage management
    ├── events/
    │   └── handlers.py       # Discord event handlers
    ├── search/               # Search integrations
    │   ├── search_pipeline.py    # Unified search pipeline
    │   ├── hybrid_search_provider.py # Hybrid Claude+Perplexity provider (default)
    │   ├── claude_adapter.py     # Pure Claude search provider
    │   ├── perplexity_adapter.py # Pure Perplexity search provider
    │   ├── claude.py         # Claude API functions
    │   └── google.py         # Google Custom Search
    ├── scraping/
    │   └── web_scraper.py    # Web scraping utilities
    └── utils/
        └── message_utils.py  # Message handling utilities
```

## Dependencies
- **discord.py** (2.3.2) - Discord API wrapper
- **groq** (0.30.0) - Groq API client
- **aiohttp** (3.9.1) - Async HTTP client for Claude
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

### Context Management Commands
- `!permanent_context <text>` - Add permanent context
- `!list_permanent_context` - View your context items
- `!remove_permanent_context <index>` - Remove specific item
- `!clear_permanent_context` - Remove all context
- `!unfiltered_permanent_context <text>` - Add unfiltered context
- `!list_unfiltered_permanent_context` - View unfiltered items
- `!clear_context` - Clear conversation context
- `!context_info` - Show context status
- `!search_context <query>` - Search your context items

### Basic Commands
- `!hello` - Greet the bot
- `!ping` - Check responsiveness
- `!help` - **UPDATED** comprehensive help system
- `!help <category>` - Detailed category help (ai, context, admin, crafting, etc.)

### Crafting Commands
- `@bot craft: I need 5 healing kits` - Natural language crafting
- `@bot craft: iron sword` - Direct item requests
- `@bot craft: list` - Show all available recipes

### Admin Commands (Admin Only)
**Natural language via @mention:**
- `@bot kick @spammer` - Remove user from server
- `@bot ban @troublemaker for harassment` - Permanent ban
- `@bot timeout @user for 1 hour` - Temporary mute
- `@bot delete 10 messages` - Bulk delete messages
- `@bot add role Moderator to @user` - Role management
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
- **Rate Limiting**: 10 requests per 60 seconds per user

### Context Management
- **Conversation Context**: 12 message limit shared between AIs
- **Context Expiry**: 30 minutes of inactivity
- **Channel Context**: 50 messages max, 35 displayed
- **Permanent Context**: Unlimited, filtered per query
- **Unfiltered Context**: Always included, never filtered

### Data Storage
- **Recipes**: `data/dune_recipes.json` (79 items, 7 tiers, 10+ weapon series)
- **User Data**: `data/` directory with JSON files
- **Context Persistence**: Survives bot restarts
- **Git Integration**: Static data included, user data ignored

## Development Notes

### Key Classes
- **AIHandler**: Main AI processing and routing logic (handler_refactored.py)
- **SearchPipeline**: Generic search flow with provider adapters
- **ContextManager**: Unified context management across AIs
- **CraftingProcessor**: Dedicated crafting system with 4-mode support
- **DataManager**: Persistent data management

### Design Patterns
- **Unified Search Pipeline**: Generic search architecture with provider adapters
- **Protocol-Based Design**: SearchProvider protocol for extensibility
- **Hybrid AI Routing**: Intelligent selection between Groq, Claude, and Perplexity
- **Modular Architecture**: Clean separation of routing, context, search, and crafting
- **Rate Limiting**: Per-user request throttling with reset timers
- **Confirmation System**: Reaction-based admin action approval
- **Discord Optimization**: Responses formatted for Discord markdown

### Recent Major Updates
1. **Claude-Powered Admin Actions**: Migrated admin command processing from Groq to Claude for better natural language understanding
2. **Claude-Powered Context Filtering**: Migrated context filtering from Groq to Claude Haiku for better quality and consistency
3. **Hybrid Search Optimization**: Claude for query optimization + Perplexity for analysis (optimal cost/quality)
4. **Multi-Provider Options**: Hybrid (default), pure-claude, pure-perplexity modes available
5. **Unified Search Pipeline**: Generic search architecture with provider adapters
6. **Code Cleanup**: Removed old handler.py, consolidated to handler_refactored.py only

### Security Features
- **Admin Permission Checking**: Restricted admin functionality
- **Rate Limiting**: Prevents spam and abuse with per-user tracking
- **Input Validation**: Validates user inputs and commands
- **Confirmation System**: All admin actions require explicit approval
- **Context Filtering**: Prevents cross-user context leakage
- **Error Handling**: Comprehensive exception handling with fallbacks

## Troubleshooting

### API Configuration
1. **Groq API**: Set `GROQ_API_KEY` for chat/admin functionality
2. **Claude API**: Set `ANTHROPIC_API_KEY` for web search (replaces Perplexity)
3. **Google Search**: Set `GOOGLE_API_KEY` and `GOOGLE_SEARCH_ENGINE_ID`
4. **Discord Bot**: Set `DISCORD_TOKEN` and `AUTHORIZED_USER_ID`

### Common Issues
1. **Missing Context**: Check if context files exist in `data/` directory
2. **Search Failures**: Verify Google Search API configuration
3. **Admin Actions**: Ensure user ID is in `AUTHORIZED_USER_ID`
4. **Rate Limiting**: Users throttled after 10 requests/minute
5. **Memory Issues**: Context automatically expires after 30 minutes

### Testing Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Test syntax
python -m py_compile src/ai/handler_refactored.py
python -m py_compile src/search/search_pipeline.py
python -m py_compile src/search/hybrid_search_provider.py
python -m py_compile src/search/claude_adapter.py

# Run the bot
python main.py
```

### Performance Metrics
- **Response Time**: ~2-3 seconds for Claude search queries
- **Context Processing**: ~500ms for context filtering
- **Memory Usage**: Efficient with automatic context cleanup
- **Cost Efficiency**: ~$0.002 per Claude request vs $5 Perplexity
- **Rate Limits**: 10 requests/user/minute, auto-reset tracking

## Best Practices
1. **Environment Variables**: Use `.env` file for sensitive data
2. **Error Handling**: Bot gracefully handles API failures
3. **Context Management**: Automatic cleanup prevents memory issues
4. **Admin Safety**: All admin actions require explicit confirmation
5. **Rate Limiting**: Built-in protection against spam and abuse
6. **Modular Design**: Easy to extend and maintain
7. **Discord Optimization**: Responses formatted for best user experience