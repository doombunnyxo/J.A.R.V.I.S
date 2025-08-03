# Discord Bot - Hybrid AI System

A sophisticated Discord bot with hybrid AI functionality that intelligently routes queries between Groq, Claude, and Perplexity APIs using a unified search pipeline. Features comprehensive admin tools, crafting systems, conversation management, and advanced security.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Discord.py](https://img.shields.io/badge/discord.py-2.3.2-blue.svg)](https://discordpy.readthedocs.io/en/stable/)

## ✨ Key Features

### 🤖 **Hybrid AI System**
- **Intelligent Routing**: Automatically routes queries between Groq (chat/admin), Claude (search), and Perplexity (backup search)
- **Unified Search Pipeline**: Generic search architecture with provider adapters
- **Cross-AI Context**: Unified conversation context shared between all AI providers
- **Force Provider Syntax**: Override routing with `groq:`, `claude:`, `perplexity:`, or `search:` prefixes
- **Model Switching**: Admin users can switch Claude models (haiku, sonnet, opus)

### 🛡️ **Advanced Admin System**
- **Natural Language Commands**: "kick that spammer", "rename role Moderator to Super Mod"
- **Reaction Confirmations**: ✅/❌ reactions for admin action approval
- **Comprehensive Actions**: User moderation, role management, channel management, bulk delete
- **Smart User Detection**: Handles pronouns, mentions, and context-aware targeting
- **AI-Powered Role Organization**: Intelligent role renaming based on custom contexts

### 💾 **Intelligent Data Management**
- **Persistent Conversations**: Per-user conversation tracking across restarts
- **Permanent Context**: Filtered relevant context for personalized responses
- **Unfiltered Settings**: Always-applied settings that appear in every query
- **User Settings**: Individual preferences and configurations
- **Context Filtering**: AI-powered relevance filtering to optimize token usage

### 🔍 **Search Integration**
- **Unified Search Pipeline**: Generic search flow that works with any AI provider
- **Claude Search**: Cost-effective search with Claude 3.5 Haiku (99.96% cheaper than Perplexity)
- **Perplexity Backup**: Alternative search provider using Sonar model
- **Google Custom Search**: Optimized query enhancement for better results
- **Context-Aware Results**: Search results combined with user context

### ⚔️ **Dune Awakening Crafting**
- **Resource Calculator**: Advanced crafting system integration
- **Material Optimization**: Find the best crafting combinations

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
AI_MODEL=llama3-8b-8192                  # Groq model name
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
@bot claude: What happened in tech news today?
@bot perplexity: Latest crypto trends
@bot search: best programming tutorials 2025
```

#### Admin Commands (Admin Only)
```
@bot kick @spammer
@bot delete 10 messages from @user
@bot rename role "Old Name" to "New Name"
@bot reorganize roles based on gaming community context
@bot timeout @user 30 minutes for being rude
```

### Bot Commands

#### Basic Commands
- `!hello` - Greet the user
- `!ping` - Check bot responsiveness

#### Context Management
- `!add_setting <text>` - Add unfiltered permanent setting
- `!list_settings` - List all permanent settings
- `!remove_setting <number>` - Remove a setting by number
- `!clear_settings` - Clear all permanent settings

#### History Management
- `!history` - Show recent conversation history
- `!clear` - Clear your conversation history
- `!context on/off` - Toggle channel context usage

### Advanced Features

#### Unfiltered Permanent Settings
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
├── main.py                     # Bot entry point
├── requirements.txt            # Dependencies
├── discord-bot.service         # Systemd service file
├── dune_crafting.py           # Crafting system module
├── data/                      # Persistent data storage
│   ├── conversation_history.json
│   ├── permanent_context.json
│   ├── unfiltered_permanent_context.json
│   └── user_settings.json
└── src/
    ├── config.py              # Configuration management
    ├── admin/                 # Admin system
    │   ├── actions.py         # Admin action execution
    │   ├── parser.py          # Natural language parsing
    │   └── permissions.py     # Permission checking
    ├── ai/
    │   ├── handler_refactored.py  # Main AI handler with unified search
    │   ├── routing.py         # Query routing logic
    │   ├── context_manager.py # Context management
    │   └── crafting_module.py # Crafting system
    ├── commands/              # Discord commands
    │   ├── basic.py           # Basic commands
    │   ├── admin.py           # Admin panel
    │   ├── history.py         # History management
    │   ├── help.py            # Dynamic help
    │   └── search_context.py  # Context search
    ├── data/
    │   └── persistence.py     # Data storage
    ├── events/
    │   └── handlers.py        # Discord events
    ├── search/                # Search integrations
    │   ├── search_pipeline.py # Unified search pipeline
    │   ├── claude_adapter.py  # Claude search provider
    │   ├── perplexity_adapter.py # Perplexity search provider
    │   ├── claude.py          # Claude API functions
    │   └── google.py          # Google Custom Search
    ├── scraping/
    │   └── web_scraper.py     # Web utilities
    └── utils/
        └── message_utils.py   # Message handling
```

### Key Components

#### AIHandler (`src/ai/handler_refactored.py`)
- Hybrid routing between Groq, Claude, and Perplexity
- Unified search pipeline with provider adapters
- Context management and filtering
- Rate limiting (10 requests/60 seconds per user)
- Admin action detection

#### SearchPipeline (`src/search/search_pipeline.py`)
- Generic search architecture with provider adapters
- Protocol-based design for extensibility
- Standard flow: optimize query → Google search → analyze results
- Works with Claude, Perplexity, or any future providers

#### AdminSystem (`src/admin/`)
- Natural language admin command parsing
- Discord action execution with confirmations
- Comprehensive user, role, and channel management

#### DataManager (`src/data/persistence.py`)
- Persistent storage with async operations
- User settings and conversation history
- Permanent context management (filtered and unfiltered)

## 🔧 Configuration

### AI Models
- **Default Groq Model**: llama3-8b-8192
- **Max Tokens**: 1000
- **Temperature**: 0.7
- **Rate Limiting**: 10 requests per 60 seconds per user

### Context Management
- **Channel Context Limit**: 50 messages
- **Display Limit**: 35 messages
- **Unified Context**: 12 message limit shared between AIs
- **Context Expiry**: 30 minutes

### Security Features
- **Admin Permission Checking**: Restricted admin functionality
- **Rate Limiting**: Prevents spam and abuse
- **Input Validation**: Validates user inputs and commands
- **Error Handling**: Comprehensive exception handling

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

## 🛠️ Development

### Code Quality
- Modular architecture with separation of concerns
- Async/await patterns for performance
- Comprehensive error handling
- Type hints and documentation

### Testing
```bash
# Run tests (when implemented)
pytest

# Check code style
flake8 src/

# Format code
black src/
```

## 📊 Dependencies

### Core Dependencies
- **discord.py** (2.3.2) - Discord API wrapper
- **groq** (0.30.0) - Groq API client
- **aiohttp** (3.9.1) - Async HTTP for Claude and Perplexity
- **google-api-python-client** (2.108.0) - Google Search
- **python-dotenv** (1.0.0) - Environment management

## 🆘 Troubleshooting

### Common Issues

#### Configuration Errors
```bash
# Check environment variables
cat .env

# Verify bot permissions in Discord
# Ensure API keys are valid
```

#### Rate Limiting
```bash
# Check rate limit settings in config.py
# Monitor with: journalctl -u discord-bot -f
```

#### Data Issues
```bash
# Check data directory permissions
ls -la data/

# Verify JSON file integrity
python -m json.tool data/conversation_history.json
```

### Bot Behavior
- **Message Processing**: Bot only responds to mentions
- **Context Sharing**: Conversations maintain context across AI providers
- **Admin Actions**: Require reaction confirmation before execution
- **Rate Limiting**: Users are throttled to prevent abuse

## 📈 Performance

### Optimizations
- **Async Operations**: All file I/O and API calls are asynchronous
- **Context Filtering**: AI-powered relevance filtering reduces token usage
- **Connection Pooling**: Efficient HTTP connection management
- **Memory Management**: Automatic cleanup of old conversations and contexts

### Monitoring
- Systemd journal logging
- Rate limiting metrics
- Error tracking and recovery

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes with proper testing
4. Follow the existing code style
5. Submit a pull request

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Discord.py community for excellent documentation
- Groq, Anthropic (Claude), and Perplexity for AI API access
- Google for Custom Search API
- Dune Awakening community for crafting system requirements

---

**Note**: This bot is designed for private server use. Ensure you comply with Discord's Terms of Service and API guidelines when using this bot.