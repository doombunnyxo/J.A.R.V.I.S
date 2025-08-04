# Discord Bot - CLAUDE.md

## Project Overview
This is a Discord bot with hybrid AI functionality that combines Groq, Claude, and Perplexity APIs for intelligent routing of queries. The bot provides chat capabilities, web search integration, comprehensive admin tools with natural language processing, Dune Awakening crafting system, and conversation context management.

**📅 Last Updated**: January 2025

## Architecture Overview

### Core Components
- **Hybrid AI Routing**: Groq (chat) + Claude (admin/optimization) + Perplexity (search analysis)
- **Admin System**: Two-phase parsing with natural language processing for 13 action types
- **Crafting System**: 250+ recipes from Dune Awakening with material calculation
- **Context Management**: Claude Haiku-powered filtering with multiple context types
- **Centralized Logging**: Professional logging system throughout codebase

### File Structure
```
src/
├── config.py                 # Configuration management
├── admin/                    # Admin system (refactored 2025)
│   ├── parser.py            # Two-phase parsing orchestrator
│   ├── extractors.py        # Parameter extractors for 13 admin actions
│   ├── utils.py             # Utility functions
│   ├── actions.py           # Admin action execution
│   └── permissions.py       # Permission checking
├── ai/
│   ├── handler_refactored.py # Main AI handler
│   ├── context_manager.py   # Context management with Claude filtering
│   ├── routing.py           # Query routing logic
│   └── crafting_module.py   # Crafting system integration
├── commands/                # Discord slash commands
│   ├── admin.py
│   ├── basic.py
│   ├── help.py
│   ├── history.py
│   └── search_context.py
├── events/
│   └── handlers.py          # Discord event handlers
├── search/                  # Search architecture
│   ├── search_pipeline.py   # Generic search pipeline
│   ├── hybrid_search_provider.py # Claude+Perplexity (default)
│   ├── claude_adapter.py    # Pure Claude search provider
│   ├── perplexity_adapter.py # Pure Perplexity search provider
│   ├── claude.py            # Legacy Claude functions
│   ├── perplexity.py        # Legacy Perplexity functions
│   └── google.py            # Google Custom Search
├── data/
│   └── persistence.py       # Data storage management
├── utils/
│   ├── logging.py           # Centralized logging system  
│   └── message_utils.py     # Message handling utilities
└── scraping/
    └── web_scraper.py       # Web scraping utilities
```

## Configuration

### Required Environment Variables
- `DISCORD_TOKEN` - Discord bot token (required)
- `AUTHORIZED_USER_ID` - Admin user ID (required)

### Optional API Keys
- `GROQ_API_KEY` - Groq API key for chat functionality
- `ANTHROPIC_API_KEY` - Claude API key for admin/search
- `PERPLEXITY_API_KEY` - Perplexity API key for search analysis
- `GOOGLE_API_KEY` - Google Search API key
- `GOOGLE_SEARCH_ENGINE_ID` - Google Custom Search Engine ID

### Required Discord Intents
- **Message Content Intent** - Required for reading message content
- **Guild Members Intent** - Required for admin commands (user lookup, nickname changes)

## AI Models Used
- **Groq**: llama-3.1-8b-instant
- **Claude**: claude-3-5-haiku-20241022 (default), claude-3-5-sonnet, claude-3-opus
- **Perplexity**: sonar

## Admin System Architecture

### 13 Admin Action Types
1. `kick_user` - Remove user from server
2. `ban_user` - Permanently ban user
3. `unban_user` - Unban user by ID
4. `timeout_user` - Temporarily mute user
5. `remove_timeout` - Remove user timeout
6. `change_nickname` - Change user nicknames
7. `add_role` - Give role to user
8. `remove_role` - Remove role from user
9. `rename_role` - Rename existing role
10. `reorganize_roles` - AI-powered role organization
11. `bulk_delete` - Delete messages with user filtering
12. `create_channel` - Create text/voice channels
13. `delete_channel` - Delete existing channels

### Two-Phase Parsing
- **Phase 1**: Action identification (`_identify_action_type`)
- **Phase 2**: Parameter extraction (`_extract_parameters` via extractors.py)

## Context Management

### Context Types
1. **Conversation Context**: 12 message exchanges per user/channel, 30-minute expiry
2. **Channel Context**: 50 messages per channel (loaded from Discord history on startup)
3. **Permanent Context**: User-specific information, filtered per query
4. **Settings**: Unfiltered global preferences (commands: `!add_setting`, `!list_settings`, `!remove_setting`, `!clear_settings`)

### Context Filtering
- All context filtering uses Claude Haiku for relevance determination
- Separate filtering for conversation, permanent, and channel context
- Settings bypass all filtering and appear in every query

## Crafting System

### Database Details
- **250+ recipes** in `data/dune_recipes.json` (version 6.3)
- **Material tiers**: Copper → Iron → Steel → Aluminum → Duraluminum → Plastanium
- **Vehicle types**: Ornithopters, Sandbikes, Buggies, Sandcrawlers
- **Weapon series**: Karpov 38, Maula Pistol, Disruptor M11, Sword, Rapier, JABAL Spitdart, etc.

### Capabilities
- Natural language processing for complex requests
- Material calculation and breakdown
- Mixed component tier support
- Optional parts handling

## Search Architecture

### Hybrid Search (Default)
- Claude Haiku for query optimization (fast, cost-effective)
- Perplexity for result analysis (high-quality)
- Fallback to pure Claude if Perplexity unavailable

### Force Provider Options
- `groq:` or `g:` - Force Groq
- `claude:` - Hybrid search (default)
- `pure-claude:` or `claude-only:` - Pure Claude
- `perplexity:` or `p:` - Pure Perplexity
- `search:` - Direct Google search

## Rate Limiting
- 10 requests per 60 seconds per user across all AI providers

## Common Issues & Solutions

### "Command not recognized as admin action"
- **Cause**: Missing Guild Members Intent
- **Solution**: Enable "Server Members Intent" in Discord Developer Portal and restart bot

### Admin commands failing
- Verify bot has necessary Discord permissions
- Check that `AUTHORIZED_USER_ID` is set correctly
- Ensure user is in the authorized user list

### Search not working
- Verify API keys are configured for Claude/Perplexity/Google
- Check rate limiting (10 requests/60 seconds per user)

## Development Notes

### Recent Major Changes (January 2025)
- Split monolithic admin parser (532 lines) into focused modules
- Migrated context filtering from Groq to Claude Haiku
- Expanded crafting database from 79+ to 250+ recipes
- Added Guild Members Intent requirement for admin commands
- Renamed settings commands from `unfiltered_permanent_context` to `add_setting` etc.
- Removed debug print statements from admin system

### Key Architectural Decisions
- Two-phase admin parsing for better maintainability and performance
- Claude Haiku for all context filtering (consistent, cost-effective)
- Hybrid search combining Claude optimization with Perplexity analysis
- Unified conversation context shared between all AI providers
- Graceful fallback when API keys are unavailable