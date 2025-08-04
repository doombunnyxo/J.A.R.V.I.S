# Discord Bot - Hybrid AI System

A sophisticated Discord bot with hybrid AI functionality that intelligently routes queries between Groq, Claude, and Perplexity APIs using a unified search pipeline. Features comprehensive admin tools, crafting systems, conversation management, and advanced security.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Discord.py](https://img.shields.io/badge/discord.py-2.5.2-blue.svg)](https://discordpy.readthedocs.io/en/stable/)

## ✨ Key Features

### 🤖 **Hybrid AI System**
- **Intelligent Routing**: Automatically routes queries between Groq (chat) and Claude (admin + hybrid search)
- **Hybrid Search**: Claude for fast query optimization, Perplexity for high-quality result analysis
- **Unified Search Pipeline**: Generic search architecture with provider adapters
- **Cross-AI Context**: Unified conversation context shared between all AI providers
- **Force Provider Syntax**: Override routing with `groq:`, `claude:`, `pure-claude:`, `perplexity:`, `pure-perplexity:` prefixes
- **Model Switching**: Admin users can switch Claude models (haiku, sonnet, opus)

### 🛡️ **Enhanced Admin System**
- **Natural Language Commands**: "kick that spammer", "rename role Moderator to Super Mod"
- **Reaction Confirmations**: ✅/❌ reactions for admin action approval
- **Comprehensive Actions**: User moderation, role management, channel management, bulk delete
- **Smart User Detection**: Handles pronouns, mentions, and context-aware targeting
- **AI-Powered Role Organization**: Intelligent role renaming based on custom contexts
- **Member-Only Operations**: Fixed user/member object handling for nickname changes

### 💾 **Intelligent Data Management**
- **Persistent Conversations**: Per-user conversation tracking across restarts
- **Permanent Context**: Filtered relevant context for personalized responses
- **Unfiltered Settings**: Always-applied settings that appear in every query
- **User Settings**: Individual preferences and configurations
- **Context Filtering**: Claude Haiku-powered relevance filtering to optimize token usage

### 🔍 **Advanced Search Integration**
- **Hybrid Search (Default)**: Claude optimization + Perplexity analysis for optimal cost/quality balance
- **Unified Search Pipeline**: Generic search flow that works with any AI provider
- **Pure Provider Options**: Force pure Claude or pure Perplexity when needed
- **Google Custom Search**: Optimized query enhancement for better results
- **Context-Aware Results**: Search results combined with user context

### ⚔️ **Dune Awakening Crafting**
- **79+ Recipes**: Complete weapon database with 7-tier progression
- **Natural Language Processing**: AI-powered recipe interpretation
- **Resource Calculator**: Advanced crafting system integration
- **Material Optimization**: Find the best crafting combinations

### 🚀 **Modern Code Quality**
- **Centralized Logging**: Professional logging system with configurable levels
- **Type Hints**: Comprehensive type annotations for better IDE support
- **Error Handling**: Robust exception handling with user-friendly messages
- **Async Architecture**: Full async/await implementation for performance
- **Modular Design**: Clean separation of concerns across modules

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Discord bot token
- At least one AI API key (Groq recommended)

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
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Run the bot**
   ```bash
   python main.py
   ```

### Environment Variables

Create a `.env` file with the following configuration:

```env
# Required
DISCORD_TOKEN=your_discord_bot_token
AUTHORIZED_USER_ID=your_discord_user_id

# Optional - AI Features
GROQ_API_KEY=your_groq_api_key           # For chat and admin commands
ANTHROPIC_API_KEY=your_claude_api_key    # For web search (primary)
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
@bot claude: What happened in tech news today?         # Hybrid (default)
@bot pure-claude: Latest AI developments               # Claude only
@bot perplexity: Latest crypto trends                  # Perplexity only
@bot search: best programming tutorials 2025
```

#### Admin Commands (Admin Only)
```
@bot kick @spammer
@bot delete 10 messages from @user
@bot rename role "Old Name" to "New Name"
@bot reorganize roles based on gaming community context
@bot timeout @user 30 minutes for being rude
@bot change @user nickname to "NewName"
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
- `!unfiltered_permanent_context <text>` - Add unfiltered permanent setting
- `!list_unfiltered_permanent_context` - List unfiltered settings
- `!clear_context` - Clear conversation context
- `!context_info` - Show context status
- `!search_context <query>` - Search your context items

#### History Management
- `!history` - Show recent conversation history
- `!clear_history` - Clear your conversation history

#### Admin Commands (Admin Only)
- `!admin_panel` - Administrative control interface
- `!clear_all_search_contexts` - Clear all user contexts

### Advanced Features

#### Crafting System
```
@bot craft: I need 5 healing kits
@bot craft: iron sword
@bot craft: list weapons
@bot craft: sandbike chassis
```

#### Unfiltered Permanent Settings
Settings that apply to ALL AI queries without filtering:
```
!unfiltered_permanent_context Always respond in a friendly, casual tone
!unfiltered_permanent_context I prefer shorter responses when possible
!unfiltered_permanent_context Remember that I'm a developer working on Discord bots
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
├── dune_crafting.py           # Crafting system module
├── logs/                      # Log files (auto-created)
├── data/                      # Persistent data storage
│   ├── conversation_history.json
│   ├── permanent_context.json
│   ├── unfiltered_permanent_context.json
│   ├── user_settings.json
│   └── dune_recipes.json      # Crafting database (79+ recipes)
└── src/
    ├── config.py              # Configuration management with logging
    ├── admin/                 # Enhanced admin system
    │   ├── actions.py         # Admin action execution with proper error handling
    │   ├── parser.py          # Natural language parsing (Member vs User fix)
    │   └── permissions.py     # Permission checking
    ├── ai/
    │   ├── handler_refactored.py  # Main AI handler (consolidated, no legacy)
    │   ├── routing.py         # Query routing logic
    │   ├── context_manager.py # Context management with logging
    │   └── crafting_module.py # Crafting system (migrated to direct Claude API)
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
    │   ├── hybrid_search_provider.py # Hybrid Claude+Perplexity (default)
    │   ├── claude_adapter.py  # Pure Claude search provider
    │   ├── perplexity_adapter.py # Pure Perplexity search provider
    │   ├── claude.py          # Claude API functions (legacy compatibility)
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
- **Hybrid routing**: Intelligent selection between Groq, Claude, and Perplexity
- **Unified search pipeline**: Generic search architecture
- **Context management**: Shared context across all AI providers
- **Rate limiting**: 10 requests/60 seconds per user
- **Comprehensive logging**: Debug tracing and error handling

#### Search Architecture (`src/search/`)
- **Unified Pipeline**: Generic search flow with provider adapters
- **Hybrid Provider (Default)**: Claude optimization + Perplexity analysis
- **Pure Providers**: Claude-only and Perplexity-only options
- **Legacy Compatibility**: Maintained for specific use cases
- **Protocol-Based Design**: Extensible for future providers

#### Enhanced Admin System (`src/admin/`)
- **Fixed User/Member Handling**: Proper discord.Member vs discord.User distinction
- **Natural Language Processing**: Advanced command parsing
- **Reaction Confirmations**: ✅/❌ approval system
- **Comprehensive Actions**: User, role, channel management
- **Error Recovery**: Graceful handling of permission errors

#### Improved Data Management (`src/data/persistence.py`)
- **Thread-Safe Operations**: Async locks for concurrent access
- **Error Resilience**: Graceful handling of corrupted data
- **Backup and Recovery**: Automatic data integrity checks
- **Logging Integration**: Full operation tracing

## 🔧 Configuration

### AI Models
- **Groq Model**: llama-3.1-8b-instant
- **Claude Models**: 
  - claude-3-5-haiku-20241022 (default) - Fast, cost-effective
  - claude-3-5-sonnet - Balanced performance
  - claude-3-opus - Most capable
- **Max Tokens**: 1000
- **Temperature**: 0.7 (Groq), 0.2 (Claude search)
- **Rate Limiting**: 10 requests per 60 seconds per user

### Context Management
- **Channel Context Limit**: 50 messages
- **Display Limit**: 35 messages
- **Unified Context**: 12 message limit shared between AIs
- **Context Expiry**: 30 minutes

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
- ✅ **Migrated crafting module to direct Claude API**
- ✅ **Enhanced error handling with user-friendly messages**
- ✅ **Standardized coding patterns across modules**

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
- **aiohttp** (3.9.1) - Async HTTP for Claude and Perplexity
- **google-api-python-client** (2.108.0) - Google Search
- **python-dotenv** (1.0.0) - Environment management

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

#### User/Member Errors
The bot now properly distinguishes between `discord.User` and `discord.Member` objects:
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
- **Context Filtering**: Claude Haiku-powered relevance filtering reduces token usage
- **Connection Pooling**: Efficient HTTP connection management
- **Memory Management**: Automatic cleanup of old conversations and contexts
- **Centralized Logging**: Efficient logging with proper levels and rotation

### Monitoring
- **Structured Logging**: JSON-formatted logs for easy parsing
- **Performance Metrics**: Response times and API call tracking
- **Error Tracking**: Comprehensive exception logging with context
- **Rate Limiting Metrics**: Request tracking per user

### Cost Optimization
- **Hybrid Search**: ~$0.002 per Claude request vs $5+ Perplexity
- **Context Filtering**: Reduces token usage while maintaining quality
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
- Groq, Anthropic (Claude), and Perplexity for AI API access
- Google for Custom Search API
- Dune Awakening community for crafting system requirements

---

**Note**: This bot is designed for private server use. Ensure you comply with Discord's Terms of Service and API guidelines when using this bot.