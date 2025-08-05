# J.A.R.V.I.S Discord Bot

A sophisticated Discord bot powered by OpenAI with comprehensive admin tools, Dune Awakening crafting system, and intelligent conversation management.

## ✨ Features

### 🤖 AI Integration
- **OpenAI GPT-4o Mini**: Primary AI for all chat, admin, and search functionality
- **Intelligent Routing**: Automatically routes admin commands vs general queries
- **Context Awareness**: Maintains conversation history and channel context
- **Model Selection**: Admin users can switch between GPT-4o, GPT-4o Mini, GPT-4 Turbo, and GPT-4

### 🛠️ Admin System
- **Natural Language Commands**: Process admin requests in plain English
- **Comprehensive Actions**: User moderation, role management, message bulk deletion, channel management
- **Confirmation System**: React with ✅/❌ to confirm admin actions
- **Permission System**: Restricted to authorized users only

### 🏗️ Dune Awakening Crafting
- **250+ Recipes**: Complete database of Dune Awakening crafting recipes
- **Material Calculator**: Automatic calculation of required materials
- **Vehicle Assembly**: Support for complex vehicle crafting trees
- **Natural Language**: AI-powered recipe interpretation and suggestions

### 💬 Conversation Management
- **Persistent Context**: Per-user conversation history with expiration
- **Channel Context**: Contextual awareness of channel conversations
- **User Preferences**: Customizable settings and permanent context
- **Rate Limiting**: Built-in protection against spam

### 🔍 Web Search
- **Google Integration**: Real-time web search with content extraction
- **Multiple Analysis**: Single-stage and two-stage content analysis
- **Smart Filtering**: Domain blacklisting for improved results
- **Force Commands**: Override search behavior with `full:` or `ai:` prefixes

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Discord bot token
- OpenAI API key (recommended)

### Installation
1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd J.A.R.V.I.S
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your tokens and API keys
   ```

4. **Run the bot**
   ```bash
   python main.py
   ```

## ⚙️ Configuration

### Required Environment Variables
```env
DISCORD_TOKEN=your_discord_bot_token
AUTHORIZED_USER_ID=your_discord_user_id
```

### Optional Environment Variables
```env
# AI Features
OPENAI_API_KEY=your_openai_api_key

# Search Features
GOOGLE_API_KEY=your_google_api_key
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id

# Advanced Configuration
AI_MODEL=gpt-4o-mini
AI_MAX_TOKENS=1000
AI_TEMPERATURE=0.7
```

## 📖 Usage

### Basic Interaction
```
@bot Hello! How are you?
@bot What's the weather like today?
@bot craft: How do I make a sandbike?
```

### Force Commands
```
@bot ai: Tell me a joke                    # Direct AI (no search)
@bot full: What's new in AI this year?     # Full page search with GPT-4o
```

### Admin Commands (Authorized Users Only)
```
@bot Change John's nickname to "Johnny"
@bot Ban @user for spamming
@bot Delete the last 10 messages
@bot Create a new channel called "general-chat"
```

### Slash Commands
- `!hello` - Greet the bot
- `!ping` - Check response time
- `!help` - Comprehensive help system
- `!context on/off` - Toggle channel context
- `!history` - View conversation history
- `!add_setting <text>` - Add global setting
- `!remember <text>` - Add permanent context (admin only)

## 🏗️ Architecture

### Core Components
```
src/
├── ai/
│   ├── handler_refactored.py    # Main AI routing and processing
│   ├── context_manager.py       # Conversation and context management
│   ├── openai_client.py         # Centralized OpenAI client
│   ├── routing.py              # Query routing logic
│   └── crafting_module.py      # Crafting system integration
├── admin/
│   ├── admin_processor.py      # Admin command processor
│   ├── parser.py              # Two-phase command parsing
│   ├── extractors.py          # Parameter extraction
│   ├── actions.py             # Admin action execution
│   └── permissions.py         # Permission checking
├── search/
│   ├── search_pipeline.py     # Search orchestration
│   ├── openai_adapter.py      # OpenAI search provider
│   ├── google.py             # Google Search integration
│   └── web_extractor.py      # Web content extraction
├── commands/                  # Discord slash commands
├── events/                   # Discord event handlers
├── data/                    # JSON data persistence
└── utils/                   # Utilities and logging
```

### Data Storage
- **JSON Files**: User settings, conversation history, permanent context
- **Async Locks**: Thread-safe concurrent access
- **Automatic Backup**: Data persistence with error recovery

## 🛠️ Development

### Dependencies
- **discord.py** (2.5.2) - Discord API wrapper
- **openai** (1.57.0) - OpenAI API client
- **google-api-python-client** (2.108.0) - Google Search API
- **aiohttp** (3.9.1) - HTTP client for web requests
- **beautifulsoup4** (4.13.4) - HTML parsing
- **python-dotenv** (1.0.0) - Environment variable management

### Code Quality
- **Centralized Logging**: Structured logging with multiple levels
- **Error Handling**: Graceful error recovery and user feedback
- **Rate Limiting**: Built-in protection against API abuse
- **Type Hints**: Comprehensive type annotations
- **Async Architecture**: Full async/await implementation

## 📋 Features Overview

| Feature | Status | Description |
|---------|--------|-------------|
| ✅ OpenAI Integration | Active | GPT-4o Mini, GPT-4o, GPT-4 Turbo, GPT-4 |
| ✅ Admin Commands | Active | 13 admin actions with natural language processing |
| ✅ Dune Crafting | Active | 250+ recipes with material calculations |
| ✅ Web Search | Active | Google Search with content extraction |
| ✅ Context Management | Active | Conversation history and channel context |
| ✅ Rate Limiting | Active | Per-user rate limiting with time windows |
| ✅ Slash Commands | Active | 12 slash commands for various features |
| ✅ Data Persistence | Active | JSON-based storage with async locks |

## 🔧 Troubleshooting

### Common Issues
- **"Command not recognized as admin action"**: Enable "Server Members Intent" in Discord Developer Portal
- **OpenAI API errors**: Check API key and rate limits
- **Google Search not working**: Verify both API key and Search Engine ID
- **Bot not responding**: Check Discord token and bot permissions

### Support
- Check logs in the console for detailed error information
- Verify all environment variables are set correctly
- Ensure the bot has necessary Discord permissions

## 📄 License

This project is open source. See the code for implementation details.

---

**J.A.R.V.I.S** - Just A Rather Very Intelligent System