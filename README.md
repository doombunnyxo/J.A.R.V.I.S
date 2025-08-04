# Discord Bot - Hybrid AI System

A sophisticated Discord bot with hybrid AI functionality that intelligently routes queries between Groq, OpenAI, and Perplexity APIs using a unified search pipeline. Features comprehensive admin tools with natural language processing, Dune Awakening crafting system, conversation management, and production-ready architecture with centralized logging.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Discord.py](https://img.shields.io/badge/discord.py-2.5.2-blue.svg)](https://discordpy.readthedocs.io/en/stable/)

## ✨ Key Features

### 🤖 **Hybrid AI System**
- **Intelligent Routing**: Automatically routes queries between Groq (chat) and OpenAI (admin + hybrid search)
- **Hybrid Search**: OpenAI for fast query optimization, Perplexity for high-quality result analysis
- **Unified Search Pipeline**: Generic search architecture with provider adapters
- **Cross-AI Context**: Unified conversation context shared between all AI providers
- **Force Provider Syntax**: Override routing with `groq:`, `openai:`, `pure-openai:`, `perplexity:`, `pure-perplexity:` prefixes
- **Model Switching**: Admin users can switch OpenAI models (gpt-4o-mini, gpt-4o, gpt-4-turbo)
- **Fallback Support**: Graceful degradation when API keys are unavailable

### 🛡️ **Enhanced Admin System**
- **Natural Language Commands**: "kick that spammer", "rename role Moderator to Super Mod"
- **Reaction Confirmations**: ✅/❌ reactions for admin action approval
- **Complete User Moderation**: Kick, ban, unban, timeout, remove timeout with flexible syntax
- **Advanced Role Management**: Add/remove roles, rename roles, AI-powered role organization
- **Nickname Control**: Change user nicknames with multiple syntax variations
- **Message Management**: Bulk delete with user filtering, pronoun support (my/bot messages)
- **Channel Operations**: Create/delete text and voice channels
- **Smart User Detection**: Handles pronouns, mentions, and context-aware targeting
- **AI-Powered Role Organization**: Intelligent role renaming based on custom contexts
- **Member-Only Operations**: Fixed user/member object handling for nickname changes

### 💾 **Intelligent Data Management**
- **Persistent Conversations**: Per-user conversation tracking across restarts
- **Permanent Context**: Filtered relevant context for personalized responses
- **Unfiltered Settings**: Always-applied settings that appear in every query
- **User Settings**: Individual preferences and configurations
- **Context Filtering**: OpenAI GPT-4o mini-powered relevance filtering to optimize token usage

### 🔍 **Advanced Search Integration**
- **Hybrid Search (Default)**: OpenAI optimization + Perplexity analysis for optimal cost/quality balance
- **Unified Search Pipeline**: Generic search flow that works with any AI provider
- **Pure Provider Options**: Force pure OpenAI or pure Perplexity when needed
- **Google Custom Search**: Real-time web search integration for current information
- **Context-Aware Results**: Search results combined with user conversation context
- **Query Optimization**: AI-enhanced search queries for better results

### ⚔️ **Dune Awakening Crafting**
- **250+ Recipes**: Complete database with weapons, tools, vehicles, and equipment (v6.3)
- **Comprehensive Vehicle System**: Full Ornithopter, Sandbike, Buggy, and Sandcrawler crafting
- **10+ Weapon Series**: Karpov 38, Maula Pistol, Disruptor M11, Sword, Rapier, JABAL Spitdart, and more
- **Professional Tools**: Construction tools, gathering equipment, cartography gear
- **6-Tier Progression**: Copper → Iron → Steel → Aluminum → Duraluminum → Plastanium
- **Natural Language Processing**: AI-powered recipe interpretation
- **Resource Calculator**: Advanced crafting system integration

### 🚀 **Modern Code Quality**
- **Centralized Logging**: Professional logging system with configurable levels
- **Type Hints**: Comprehensive type annotations for better IDE support
- **Error Handling**: Robust exception handling with user-friendly messages
- **Async Architecture**: Full async/await implementation for performance
- **Modular Design**: Clean separation of concerns across modules

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Discord bot token with required intents (see Discord Setup below)
- At least one AI API key (Groq recommended)

### Discord Bot Setup
Your Discord bot requires these privileged intents to be enabled in the Discord Developer Portal:

1. **Message Content Intent** - Required for reading message content
2. **Guild Members Intent** - Required for admin commands (user lookup, nickname changes)

To enable these:
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your bot application
3. Go to "Bot" section
4. Under "Privileged Gateway Intents", enable:
   - ✅ Message Content Intent
   - ✅ Server Members Intent
5. Save changes and restart your bot

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd discord-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment setup**
   ```bash
   # Create .env file with your API keys (see Environment Variables section below)
   touch .env
   # Edit .env with your configuration
   ```

4. **Run the bot**
   ```bash
   # Option 1: Direct execution
   python main.py
   
   # Option 2: Using automated setup script (Linux/macOS)
   chmod +x start.sh
   ./start.sh
   ```

### Environment Variables

Create a `.env` file with the following configuration:

```env
# Required
DISCORD_TOKEN=your_discord_bot_token
AUTHORIZED_USER_ID=your_discord_user_id

# Optional - AI Features
GROQ_API_KEY=your_groq_api_key           # For chat and admin commands
OPENAI_API_KEY=your_openai_api_key        # For web search (primary)
PERPLEXITY_API_KEY=your_perplexity_key   # For web search (backup)

# Optional - Search Features  
GOOGLE_API_KEY=your_google_api_key
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id

# Optional - AI Configuration
AI_MODEL=llama-3.1-8b-instant            # Groq model name
AI_MAX_TOKENS=1000                       # Max response tokens
AI_TEMPERATURE=0.7                       # AI creativity (0.0-2.0)
```

## 📖 Usage

### AI Interaction

#### Basic Usage
```
@bot What's the weather like today?
@bot Tell me about the latest AI developments
@bot How do I install Python?
```

#### Force Specific Provider
```
@bot groq: Explain quantum computing
@bot openai: What happened in tech news today?        # Hybrid (default)
@bot pure-openai: Latest AI developments              # OpenAI only
@bot perplexity: Latest crypto trends                  # Perplexity only
@bot search: best programming tutorials 2025
```

#### Admin Commands (Admin Only)

**User Moderation:**
```
@bot kick @spammer                           # Remove user from server
@bot ban @troublemaker for harassment        # Permanently ban user
@bot unban 123456789012345678               # Unban user by ID
@bot timeout @user 30 minutes for being rude # Temporarily mute user
@bot remove timeout from @user              # Remove user timeout
@bot unmute @user                           # Alternative remove timeout
```

**Nickname Management:**
```
@bot change @user nickname to "NewName"     # Change user's nickname
@bot rename member @user to "CoolName"      # Alternative nickname syntax
@bot set user's nickname to "DisplayName"   # Possessive form
```

**Role Management:**
```
@bot add role "Moderator" to @user          # Give role to user
@bot give role "Trusted" to @user           # Alternative add role syntax
@bot remove role "Muted" from @user         # Remove role from user
@bot take role "Temporary" from @user       # Alternative remove role syntax
@bot rename role "Old Name" to "New Name"   # Rename existing role
@bot reorganize roles based on gaming context # AI-powered role organization
@bot fix role names for community server    # Clean up role naming
```

**Message Management:**
```
@bot delete 10 messages                     # Delete recent messages
@bot delete 5 messages from @user          # Delete specific user's messages
@bot purge 20 messages                      # Alternative bulk delete
@bot clear my messages                      # Delete your own messages
@bot clean bot messages                     # Delete bot's messages
```

**Channel Management:**
```
@bot create channel "general-chat"          # Create text channel
@bot create voice channel "Voice Chat"      # Create voice channel
@bot delete channel #old-channel            # Delete existing channel
```

### Bot Commands

#### Basic Commands
- `!hello` - Greet the user
- `!ping` - Check bot responsiveness
- `!help` - Comprehensive help system with categories

#### Context Management
- `!permanent_context <text>` - Add filtered permanent context
- `!list_permanent_context` - List all permanent context items
- `!remove_permanent_context <index>` - Remove specific context item
- `!clear_permanent_context` - Clear all permanent context
- `!add_setting <text>` - Add unfiltered setting
- `!list_settings` - View all settings
- `!remove_setting <index>` - Remove specific setting
- `!clear_settings` - Clear all settings
- `!clear_context` - Clear conversation context
- `!context_info` - Show context status
- `!search_context <query>` - Search your context items

#### History Management
- `!history` - Show recent conversation history
- `!clear_history` - Clear your conversation history

#### Admin Commands (Admin Only)
- `!admin_panel` - Administrative control interface
- `!clear_all_search_contexts` - Clear all user contexts

**Note**: The primary admin interface is through natural language commands via @mentions (see Admin Commands section above). These slash commands provide additional administrative utilities.

### Advanced Features

#### Crafting System

**Basic Crafting:**
```
@bot craft: I need 5 healing kits
@bot craft: iron sword
@bot craft: scout ornithopter mk5
@bot craft: sandbike chassis
@bot craft: list weapons
```

**Complex Vehicle Assembly:**
```
@bot craft: Assault Ornithopter mk6 with mk5 engine and mk5 wings, storage and rocket launcher
@bot craft: Sandbike mk3 with booster, storage, and night rider boost
@bot craft: Buggy mk6 with utility rear, cutteray, and storage
@bot craft: Sandcrawler mk6 with walker engine and dampened treads
@bot craft: Carrier Ornithopter mk6 with side hull and main hull
```

**Material Calculation:**
```
@bot craft: What materials do I need for a plastanium JABAL Spitdart?
@bot craft: How much iron do I need for a complete sandbike mk2?
@bot craft: Show me the materials breakdown for 10 iron swords
```

The crafting system uses advanced natural language processing to understand complex vehicle specifications with mixed component tiers, optional parts, and provides detailed material breakdowns for crafting calculations.

#### Settings (Unfiltered)
Settings that apply to ALL AI queries without filtering:
```
!add_setting Always respond in a friendly, casual tone
!add_setting I prefer shorter responses when possible
!add_setting Remember that I'm a developer working on Discord bots
```

#### Context Filtering
The bot intelligently filters conversation context based on query relevance while preserving unfiltered settings.

## 🏗️ Architecture

### Project Structure
```
discord-bot/
├── main.py                     # Bot entry point with centralized logging
├── requirements.txt            # Dependencies
├── pyproject.toml             # Project configuration
├── discord-bot.service        # Systemd service file
├── dune_crafting.py           # Standalone crafting system module
├── logs/                      # Log files (auto-created)
├── data/                      # Persistent data storage
│   ├── conversation_history.json
│   ├── permanent_context.json
│   ├── unfiltered_permanent_context.json
│   ├── user_settings.json
│   └── dune_recipes.json      # Crafting database (250+ recipes)
└── src/
    ├── config.py              # Configuration management with logging
    ├── admin/                 # Enhanced admin system (refactored 2025)
    │   ├── actions.py         # Admin action execution with proper error handling
    │   ├── parser.py          # Two-phase parsing orchestrator (130 lines)
    │   ├── extractors.py      # Parameter extractors for all 13 admin actions (280 lines)
    │   ├── utils.py           # Utility functions (user/role/channel finding, 120 lines)
    │   └── permissions.py     # Permission checking
    ├── ai/
    │   ├── handler_refactored.py  # Main AI handler (consolidated, no legacy)
    │   ├── routing.py         # Query routing logic
    │   ├── context_manager.py # Context management with logging
    │   └── crafting_module.py # Crafting system (migrated to direct OpenAI API)
    ├── commands/              # Discord commands with type hints
    │   ├── basic.py           # Basic commands
    │   ├── admin.py           # Admin panel
    │   ├── history.py         # History management
    │   ├── help.py            # Comprehensive help system
    │   └── search_context.py  # Context search (migrated from legacy)
    ├── data/
    │   └── persistence.py     # Data storage with logging
    ├── events/
    │   └── handlers.py        # Discord events with type hints
    ├── search/                # Unified search architecture
    │   ├── search_pipeline.py # Generic search pipeline
    │   ├── hybrid_search_provider.py # Hybrid OpenAI+Perplexity (default)
    │   ├── claude_adapter.py  # Pure Claude search provider (legacy)
    │   ├── perplexity_adapter.py # Pure Perplexity search provider
    │   ├── claude.py          # Claude API functions (legacy compatibility)
    │   ├── openai.py          # OpenAI API functions (primary)
    │   ├── openai_adapter.py  # OpenAI search adapter (primary)
    │   ├── perplexity.py      # Perplexity API functions (legacy compatibility)
    │   └── google.py          # Google Custom Search
    ├── scraping/
    │   └── web_scraper.py     # Web utilities
    └── utils/
        ├── message_utils.py   # Message handling utilities
        └── logging.py         # Centralized logging system
```

### Key Components

#### Modern Logging System (`src/utils/logging.py`)
- **Centralized Configuration**: Single point for all logging setup
- **File + Console Output**: Logs to both file and console with rotation
- **Configurable Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Module-Specific Loggers**: Each module gets its own logger
- **Production Ready**: Structured logging with timestamps and context

#### Enhanced AIHandler (`src/ai/handler_refactored.py`)
- **Consolidated Architecture**: Single handler, no legacy code
- **Hybrid routing**: Intelligent selection between Groq, OpenAI, and Perplexity
- **Unified search pipeline**: Generic search architecture
- **Context management**: Shared context across all AI providers
- **Rate limiting**: 10 requests/60 seconds per user
- **Comprehensive logging**: Debug tracing and error handling

#### Search Architecture (`src/search/`)
- **Unified Pipeline**: Generic search flow with provider adapters
- **Hybrid Provider (Default)**: OpenAI optimization + Perplexity analysis
- **Pure Providers**: OpenAI-only and Perplexity-only options
- **Legacy Compatibility**: Maintained for specific use cases
- **Protocol-Based Design**: Extensible for future providers

#### Enhanced Admin System (`src/admin/`)
- **Two-Phase Architecture**: Action identification → parameter extraction for optimal performance
- **Modular Design**: Split into parser.py (orchestrator), extractors.py (13 action handlers), utils.py (helper functions)
- **Fixed User/Member Handling**: Proper discord.Member vs discord.User distinction
- **Natural Language Processing**: Advanced command parsing with flexible syntax
- **Reaction Confirmations**: ✅/❌ approval system for all admin actions
- **Comprehensive Actions**: User moderation, role management, nickname control, message management, channel operations
- **Performance Optimized**: User lookup optimized from 100ms to 1ms
- **Error Recovery**: Graceful handling of permission errors with user-friendly messages

#### Improved Data Management (`src/data/persistence.py`)
- **Thread-Safe Operations**: Async locks for concurrent access
- **Error Resilience**: Graceful handling of corrupted data
- **Backup and Recovery**: Automatic data integrity checks
- **Logging Integration**: Full operation tracing

## 🔧 Configuration

### AI Models
- **Groq Model**: llama-3.1-8b-instant
- **OpenAI Models**: 
  - gpt-4o-mini (default) - Fast, cost-effective
  - gpt-4o - Balanced performance
  - gpt-4-turbo - Most capable
- **Perplexity Model**: sonar - Real-time web search and analysis
- **Max Tokens**: 1000
- **Temperature**: 0.7 (Groq), 0.1-0.2 (OpenAI search), 0.2 (Perplexity search)
- **Rate Limiting**: 10 requests per 60 seconds per user

### Context Management
- **Channel Context Storage**: 50 messages per channel (loaded from Discord history on startup)
- **Channel Context Display**: 35 messages shown to AI
- **Unified Conversation Context**: 12 message limit shared between all AIs
- **Context Expiry**: 30 minutes of inactivity
- **Context Filtering**: OpenAI GPT-4o mini-powered relevance filtering for:
  - Conversation context (previous messages)
  - Permanent context (user-specific information)
  - Channel context (recent channel activity)
- **Unfiltered Settings**: Always-applied global preferences (bypass filtering)
- **Context Types**:
  - **Conversation**: Recent AI interactions per user/channel
  - **Channel**: General channel discussion for situational awareness
  - **Permanent**: Filtered user information and preferences
  - **Settings**: Unfiltered mandatory preferences

### Logging Configuration
```python
# In main.py or any module
from src.utils.logging import setup_logger, get_logger

# Setup with custom configuration
logger = setup_logger("discord_bot", level="INFO", log_file="logs/bot.log")

# Get logger in any module
logger = get_logger(__name__)
logger.info("This is a logged message")
```

### Security Features
- **Admin Permission Checking**: Restricted admin functionality
- **Rate Limiting**: Prevents spam and abuse with automatic reset
- **Input Validation**: Validates user inputs and commands
- **Error Handling**: Comprehensive exception handling with proper logging
- **Context Isolation**: Prevents cross-user context leakage

## 🐧 Systemd Service (Linux)

The bot includes a systemd service file for production deployment:

```bash
# Install service
sudo cp discord-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable discord-bot
sudo systemctl start discord-bot

# Check status
sudo systemctl status discord-bot
sudo journalctl -u discord-bot -f
```

See [SYSTEMD_SETUP.md](SYSTEMD_SETUP.md) for detailed setup instructions.

## 🔒 Security

### Environment Protection
- All sensitive data in environment variables
- Comprehensive .gitignore to prevent accidental commits
- No hardcoded API keys or tokens

### Service Hardening
- NoNewPrivileges and ProtectSystem enabled
- Private temp directories
- Resource limits and read-only system protection

### Input Validation
- User input sanitization
- Rate limiting on all AI requests
- Admin permission validation
- Discord Member vs User object validation

## 🛠️ Development

### Code Quality
- **Modern Python**: Type hints, async/await, proper exception handling
- **Modular Architecture**: Clean separation of concerns
- **Logging**: Comprehensive logging with structured output
- **Error Handling**: User-friendly error messages with proper recovery
- **Documentation**: Google-style docstrings throughout

### Recent Refactoring (2025)
- ✅ **Migrated from print() to logging framework**
- ✅ **Fixed bare except clauses** 
- ✅ **Added comprehensive type hints**
- ✅ **Consolidated search architecture**
- ✅ **Removed duplicate files and unused imports**
- ✅ **Fixed discord.User vs discord.Member handling**
- ✅ **Migrated crafting module to direct OpenAI API**
- ✅ **Enhanced error handling with user-friendly messages**
- ✅ **Standardized coding patterns across modules**
- ✅ **Admin system architecture refactor**: Split monolithic parser into focused modules
- ✅ **Two-phase admin parsing**: Identify action type → extract parameters approach  
- ✅ **Performance optimization**: User lookup optimized from 100ms to 1ms
- ✅ **Debug message cleanup**: Removed all debug print statements from admin system

### Testing
```bash
# Syntax validation
python -m py_compile main.py src/config.py
python -c "import src.utils.logging; print('Logging system works')"

# Check module imports
python -c "import main; print('Main module loads successfully')"

# Test specific functionality
python -c "from src.ai.handler_refactored import AIHandler; print('AI handler imports correctly')"
```

## 📊 Dependencies

### Core Dependencies
- **discord.py** (2.5.2) - Discord API wrapper
- **groq** (0.30.0) - Groq API client
- **openai** (1.57.0) - OpenAI API client (for compatibility)
- **aiohttp** (3.9.1) - Async HTTP client for OpenAI and Perplexity APIs
- **google-api-python-client** (2.108.0) - Google Custom Search integration
- **python-dotenv** (1.0.0) - Environment variable management

## 🆘 Troubleshooting

### Common Issues

#### Configuration Errors
```bash
# Check environment variables
cat .env

# Test configuration loading
python -c "from src.config import config; print('Config loaded:', config.is_valid())"

# Verify bot permissions in Discord
# Ensure API keys are valid
```

#### Admin Command Issues

**"Command not recognized as admin action"**
- **Cause**: Missing Guild Members Intent in Discord Developer Portal
- **Symptoms**: Bot can only see itself in guild.members, commands like "set user's nickname" fail
- **Fix**: Enable "Server Members Intent" in Discord Developer Portal and restart bot

**User/Member Errors**
The bot properly distinguishes between `discord.User` and `discord.Member` objects:
- **User objects**: Basic user info, cannot be edited
- **Member objects**: Server-specific, can change nicknames/roles  
- **Fix**: Bot will show clear error messages when operations require Member objects

#### Rate Limiting
```bash
# Check rate limit settings in config.py
# Monitor with: tail -f logs/discord_bot.log
```

#### Logging Issues
```bash
# Check log directory
ls -la logs/

# View recent logs
tail -f logs/discord_bot.log

# Test logging system
python -c "from src.utils.logging import get_logger; get_logger('test').info('Test message')"
```

### Bot Behavior
- **Message Processing**: Bot only responds to mentions
- **Context Sharing**: Conversations maintain context across AI providers
- **Admin Actions**: Require reaction confirmation before execution
- **Rate Limiting**: Users are throttled to prevent abuse
- **Error Recovery**: Bot provides helpful error messages instead of crashing

## 📈 Performance

### Optimizations
- **Async Operations**: All file I/O and API calls are asynchronous
- **Context Filtering**: OpenAI GPT-4o mini-powered relevance filtering reduces token usage
- **Connection Pooling**: Efficient HTTP connection management
- **Memory Management**: Automatic cleanup of old conversations and contexts
- **Centralized Logging**: Efficient logging with proper levels and rotation

### Monitoring
- **Structured Logging**: JSON-formatted logs for easy parsing
- **Performance Metrics**: Response times and API call tracking
- **Error Tracking**: Comprehensive exception logging with context
- **Rate Limiting Metrics**: Request tracking per user

### Cost Optimization
- **Hybrid Search**: Uses reliable OpenAI for query optimization, more expensive but comprehensive Perplexity for search result analysis
- **Context Filtering**: Reduces token usage while maintaining response quality
- **Smart Caching**: Efficient data storage and retrieval
- **Request Batching**: Optimized API usage patterns

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Follow the established patterns:
   - Use type hints for all functions
   - Add proper logging with `get_logger(__name__)`
   - Write Google-style docstrings
   - Handle errors gracefully with user-friendly messages
4. Test your changes thoroughly
5. Submit a pull request

### Code Style Guidelines
- **Type Hints**: All functions should have parameter and return type hints
- **Logging**: Use `logger.debug/info/warning/error()` instead of `print()`
- **Error Handling**: Catch specific exceptions and provide helpful messages
- **Docstrings**: Use Google-style with Args, Returns, and Raises sections
- **Async/Await**: Use async patterns for all I/O operations

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Discord.py community for excellent documentation
- Groq, OpenAI, and Perplexity for AI API access
- Google for Custom Search API
- Dune Awakening community for crafting system requirements

---

**Note**: This bot is designed for private server use. Ensure you comply with Discord's Terms of Service and API guidelines when using this bot.