# Discord Bot - CLAUDE.md

## Project Overview
This is a Discord bot with hybrid AI functionality that combines Groq and Perplexity APIs for intelligent routing of queries. The bot provides chat capabilities, web search integration, admin tools, crafting systems, and comprehensive conversation context management.

## Architecture

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
  - `OPENAI_API_KEY` - OpenAI API key (optional) 
  - `PERPLEXITY_API_KEY` - Perplexity API key (optional)
  - `GOOGLE_API_KEY` - Google Search API key (optional)
  - `GOOGLE_SEARCH_ENGINE_ID` - Google Custom Search Engine ID (optional)

### Key Features

#### 1. AI Handler (src/ai/handler.py)
**Core functionality**: Hybrid AI routing system that intelligently routes queries between Groq and Perplexity
- **Groq**: Used for admin commands, chat processing, personal interactions
- **Perplexity**: Used for web search queries, current events, comparisons
- **Search Indicators**: Keywords that trigger Perplexity routing (current, latest, news, etc.)
- **Rate Limiting**: 10 requests per 60 seconds per user
- **Context Management**: Unified conversation context shared between both AIs
- **Admin Action Detection**: Parses admin intents and handles confirmations

#### 2. Data Persistence (src/data/persistence.py)
**Core functionality**: Manages persistent data storage across bot restarts
- **Conversation History**: Per-user conversation tracking
- **User Settings**: Individual user preferences
- **Permanent Context**: Long-term user context storage
- **File Storage**: JSON files in `data/` directory
- **Async Operations**: Thread-safe data operations with locks

#### 3. Admin System (src/admin/)
**Core functionality**: Comprehensive Discord server administration
- **Permissions** (permissions.py): Admin user validation
- **Actions** (actions.py): Execute admin commands (kick, ban, timeout, roles, channels)
- **Parser** (parser.py): Natural language admin intent parsing
- **Reaction Confirmations**: ✅/❌ reactions for admin action approval

#### 4. Commands System (src/commands/)
- **Basic Commands** (basic.py): Hello, ping commands
- **Admin Commands** (admin.py): Admin panel and controls
- **History Management** (history.py): Conversation history commands
- **Help System** (help.py): Dynamic help generation
- **Search Context** (search_context.py): Context search functionality

#### 5. Search Integration (src/search/)
- **Google Search** (google.py): Custom search engine integration
- **Perplexity Search** (perplexity.py): AI-powered web search

#### 6. Event Handling (src/events/handlers.py)
**Core functionality**: Discord event processing and message routing
- **Message Processing**: Routes mentions to appropriate handlers
- **Force Provider Syntax**: 
  - `groq:` or `g:` - Force Groq processing
  - `perplexity:` or `p:` - Force Perplexity processing
  - `search:` - Direct Google search
  - `craft:` - Crafting system
- **Admin Confirmations**: Handles reaction-based admin confirmations

#### 7. Crafting System (src/crafting/)
- **Handler** (handler.py): Dune-themed crafting mechanics
- **Integration**: Links with dune_crafting.py module

### File Structure
```
discord-bot/
├── main.py                    # Bot entry point
├── requirements.txt           # Python dependencies
├── dune_crafting.py          # Crafting system module
├── data/                     # Persistent data storage
│   ├── conversation_history.json
│   ├── permanent_context.json
│   └── user_settings.json
└── src/
    ├── config.py             # Configuration management
    ├── admin/                # Admin system
    │   ├── actions.py        # Admin action execution
    │   ├── parser.py         # Intent parsing
    │   └── permissions.py    # Permission checking
    ├── ai/
    │   └── handler.py        # AI routing and processing
    ├── commands/             # Discord commands
    │   ├── basic.py          # Basic commands
    │   ├── admin.py          # Admin commands
    │   ├── history.py        # History management
    │   ├── help.py           # Help system
    │   └── search_context.py # Context search
    ├── data/
    │   └── persistence.py    # Data storage management
    ├── events/
    │   └── handlers.py       # Discord event handlers
    ├── search/               # Search integrations
    │   ├── google.py         # Google Custom Search
    │   └── perplexity.py     # Perplexity API
    ├── crafting/
    │   └── handler.py        # Crafting system
    ├── scraping/
    │   └── web_scraper.py    # Web scraping utilities
    └── utils/
        └── message_utils.py  # Message handling utilities
```

### Dependencies
- **discord.py** (2.3.2) - Discord API wrapper
- **groq** (0.30.0) - Groq API client
- **openai** (1.57.0) - OpenAI API client
- **aiohttp** (3.9.1) - Async HTTP client for Perplexity
- **google-api-python-client** (2.108.0) - Google Search API
- **python-dotenv** (1.0.0) - Environment variable management

### Bot Commands

#### Basic Commands
- `!hello` - Greet the user
- `!ping` - Respond with pong

#### AI Interaction
- **Mention bot**: Triggers AI processing with hybrid routing
- **@bot groq: [query]** or **@bot g: [query]** - Force Groq processing
- **@bot perplexity: [query]** or **@bot p: [query]** - Force Perplexity processing
- **@bot search: [query]** - Direct Google search
- **@bot craft: [query]** - Crafting system interaction

#### Admin Commands (Admin only)
- Natural language admin commands (kick, ban, timeout, role management, channel management)
- Reaction-based confirmations (✅/❌)
- Bulk message deletion
- Role reorganization with AI suggestions

### Configuration Details

#### AI Models
- **Default Groq Model**: llama3-8b-8192
- **Max Tokens**: 1000
- **Temperature**: 0.7
- **Rate Limiting**: 10 requests per 60 seconds per user

#### Context Management
- **Channel Context Limit**: 50 messages
- **Display Limit**: 35 messages
- **Unified Context**: 12 message limit shared between AIs
- **Context Expiry**: 30 minutes

#### Data Storage
- **History File**: `data/conversation_history.json`
- **Settings File**: `data/user_settings.json`
- **Permanent Context File**: `data/permanent_context.json`

### Development Notes

#### Key Classes
- **AIHandler**: Main AI processing and routing logic
- **DataManager**: Persistent data management
- **AdminActionHandler**: Discord admin action execution
- **AdminIntentParser**: Natural language admin command parsing
- **EventHandlers**: Discord event processing

#### Design Patterns
- **Hybrid AI Routing**: Intelligent selection between Groq and Perplexity
- **Context Sharing**: Unified conversation context across AI providers
- **Rate Limiting**: Per-user request throttling
- **Confirmation System**: Reaction-based admin action approval
- **Cog Architecture**: Modular Discord.py extension system

#### Security Features
- **Admin Permission Checking**: Restricted admin functionality
- **Rate Limiting**: Prevents spam and abuse
- **Input Validation**: Validates user inputs and commands
- **Error Handling**: Comprehensive exception handling

### Troubleshooting

#### Common Setup Issues
1. **Missing Environment Variables**: Ensure all required env vars are set in `.env` file
2. **API Key Issues**: Verify API keys are valid and have proper permissions
3. **Discord Permissions**: Bot needs appropriate Discord server permissions
4. **Data Directory**: Ensure `data/` directory exists and is writable

#### Bot Behavior
- **Message Processing**: Bot only responds to mentions, not all messages
- **Context Sharing**: Conversations maintain context across AI providers
- **Admin Actions**: Require reaction confirmation before execution
- **Rate Limiting**: Users are throttled to prevent abuse

### Testing Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot
python main.py
```

### Best Practices
1. **Environment Variables**: Always use `.env` file for sensitive data
2. **Error Handling**: Bot gracefully handles API failures and missing configurations
3. **Context Management**: Automatic context cleanup prevents memory issues
4. **Admin Safety**: All admin actions require explicit confirmation
5. **Rate Limiting**: Built-in protection against spam and abuse