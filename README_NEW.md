# Discord Bot - Refactored

A modular Discord bot with AI integration, admin capabilities, and crafting system for Dune Awakening.

## ✨ New Features & Improvements

### 🏗️ Modular Architecture
- **Separated concerns**: Each feature is now in its own module
- **Easier maintenance**: Find and modify code faster
- **Better testing**: Each module can be tested independently
- **Cleaner code**: Reduced from 1265 lines to manageable modules

### 🔒 Security Improvements
- **Environment validation**: All config validated on startup
- **No hardcoded secrets**: All sensitive data moved to environment variables
- **Rate limiting**: Prevents API abuse with per-user limits

### ⚡ Performance Enhancements
- **Async data operations**: Improved file I/O performance
- **Connection pooling**: Better API response times
- **Memory optimization**: Conversation history automatically trimmed

## 🚀 Quick Start

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt

# For development
pip install -r requirements-dev.txt
```

### Environment Setup
Create a `.env` file with:
```env
# Required
DISCORD_TOKEN=your_discord_bot_token
AUTHORIZED_USER_ID=your_discord_user_id

# Optional - AI Features
GROQ_API_KEY=your_groq_api_key

# Optional - Search Features  
GOOGLE_API_KEY=your_google_api_key
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id
```

### Running the Bot
```bash
# New recommended way
python main.py

# Legacy compatibility (will redirect to main.py)
python bot.py
```

## 📁 Project Structure

```
discord-bot/
├── main.py                    # New entry point
├── bot_legacy.py             # Backward compatibility
├── dune_crafting.py          # Crafting system (unchanged)
├── requirements.txt          # Core dependencies
├── requirements-dev.txt      # Development dependencies
├── src/                      # Source code modules
│   ├── config.py            # Configuration management
│   ├── data/
│   │   └── persistence.py   # Data storage operations
│   ├── admin/
│   │   ├── actions.py       # Admin action handlers
│   │   ├── parser.py        # Intent parsing
│   │   └── permissions.py   # Permission management
│   ├── ai/
│   │   └── handler.py       # AI integration + rate limiting
│   ├── commands/
│   │   ├── basic.py         # Basic commands (!ping, !hello)
│   │   ├── history.py       # History management
│   │   └── admin.py         # Admin commands
│   ├── search/
│   │   └── google.py        # Google search integration
│   ├── crafting/
│   │   └── handler.py       # Dune crafting commands
│   └── events/
│       └── handlers.py      # Discord event handlers
└── data/                     # Runtime data (created automatically)
    ├── conversation_history.json
    ├── user_settings.json
    └── permanent_context.json
```

## 🔧 Configuration Options

### Environment Variables
| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `DISCORD_TOKEN` | ✅ | Discord bot token | - |
| `AUTHORIZED_USER_ID` | ✅ | Admin user ID | - |
| `GROQ_API_KEY` | ❌ | AI features | - |
| `GOOGLE_API_KEY` | ❌ | Search features | - |
| `GOOGLE_SEARCH_ENGINE_ID` | ❌ | Search features | - |
| `AI_MODEL` | ❌ | AI model name | `llama3-8b-8192` |
| `AI_MAX_TOKENS` | ❌ | Max AI response tokens | `1000` |
| `AI_TEMPERATURE` | ❌ | AI creativity (0.0-2.0) | `0.7` |

### Rate Limiting
- **AI Requests**: 10 requests per minute per user
- **Bulk Operations**: 1 second delay between actions
- **File Operations**: Async with proper locking

## 📊 Features

### 🤖 AI Integration
- Natural language processing with Groq
- Conversation history per user
- Channel context awareness
- Admin action detection and confirmation

### 🛡️ Admin Commands
- User moderation (kick, ban, timeout)
- Role management
- Channel management  
- Bulk message deletion
- Nickname changes

### 🔍 Search & Utilities
- Google search integration
- Dune Awakening crafting calculator
- Conversation history management
- Bot statistics

## 🧪 Development

### Code Quality
```bash
# Format code
black src/

# Check style
flake8 src/

# Type checking
mypy src/
```

### Testing
```bash
# Run tests (when implemented)
pytest

# Run with coverage
pytest --cov=src/
```

## 🔄 Migration from Legacy Bot

The refactored bot is **100% backward compatible**:

1. **Data**: All existing JSON files work unchanged
2. **Commands**: All existing commands work identically  
3. **Features**: No functionality was removed
4. **Environment**: Same environment variables (with new optional ones)

### What Changed
- ✅ **Better**: Modular code structure
- ✅ **Better**: Rate limiting and security
- ✅ **Better**: Performance improvements
- ✅ **Better**: Configuration validation
- ➡️ **Same**: All user-facing functionality
- ➡️ **Same**: Data storage format
- ➡️ **Same**: Command syntax

## 🆘 Troubleshooting

### Configuration Errors
If you see configuration errors on startup, check:
1. `.env` file exists and contains required variables
2. `AUTHORIZED_USER_ID` is a valid Discord user ID number
3. API keys are correctly formatted

### Import Errors
If you see import errors:
```bash
# Make sure you're running from project root
cd discord-bot/
python main.py

# Check Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Performance Issues
- Check rate limiting settings in `src/config.py`
- Monitor file sizes in `data/` directory
- Use `!stats` command to check storage usage

## 📈 Benefits of Refactoring

| Aspect | Before | After |
|--------|--------|-------|
| **Main file size** | 1,265 lines | ~50 lines |
| **Modularity** | Monolithic | 12+ focused modules |
| **Configuration** | Hardcoded values | Environment validation |
| **Rate limiting** | None | Per-user AI limits |
| **Error handling** | Basic | Comprehensive |
| **Security** | Hardcoded admin ID | Environment-based auth |
| **Performance** | Synchronous I/O | Async operations |
| **Maintainability** | Difficult | Easy to modify |