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

## Memories
- **January 2025**: Major refactoring completed, consolidating AI handler architecture
- **Refactoring Highlights**:
  - Removed legacy code from search and crafting modules
  - Implemented centralized logging system
  - Added comprehensive type hints
  - Enhanced error handling and user feedback
  - Improved async performance with proper timeout handling
- **Key Architectural Improvements**:
  - Unified search pipeline with provider adapters
  - Fixed Discord User/Member object handling
  - Migrated legacy modules to new architecture
  - Improved security and input validation

[Rest of the existing content remains the same]