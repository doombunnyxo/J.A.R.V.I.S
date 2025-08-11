#!/usr/bin/env python3
"""
Discord Bot - Multi-AI System
Main entry point for the Discord bot with cross-AI functionality.

Features:
- Groq + OpenAI + Perplexity AI routing
- Cross-AI conversation context sharing
- Advanced admin action parsing
- Comprehensive command system
"""

import asyncio
import discord
from discord.ext import commands
from src.config import config
from src.data.persistence import data_manager
from src.ai.handler_refactored import AIHandler
from src.utils.logging import setup_logger

# Set up logging
logger = setup_logger("discord_bot", level="INFO")


async def setup_bot():
    """Setup and configure the bot"""
    try:
        # Initialize and validate configuration
        from src.config import config as imported_config, init_config
        
        if imported_config is None:
            logger.info("Attempting to reinitialize configuration...")
            config_instance = init_config()
        else:
            config_instance = imported_config
            
        logger.info("Configuration validated successfully")
        logger.info(f"Bot will use AI model: {config_instance.AI_MODEL}")
        logger.info(f"Rate limiting: {config_instance.AI_RATE_LIMIT_REQUESTS} requests per {config_instance.AI_RATE_LIMIT_WINDOW}s")
        
        # Load persistent data
        logger.info("Loading persistent data...")
        await data_manager.load_all_data()
        logger.info("Data loaded successfully")
        
        # Initialize WoW managers to load their data files
        logger.info("Loading WoW manager data...")
        from src.wow.character_manager import character_manager
        from src.wow.run_manager import run_manager
        from src.wow.season_manager import season_manager
        from src.wow.startup_loader import startup_loader
        
        # Log what was loaded
        total_chars = sum(len(user_data.get("characters", [])) for user_data in character_manager.data.values() if isinstance(user_data, dict))
        logger.info(f"Loaded character data: {len(character_manager.data)} users, {total_chars} total characters")
        logger.info(f"Loaded {len(run_manager.data['runs'])} run records")
        logger.info(f"Current season: {season_manager.data['current_season']}")
        
        # Pre-fetch runs for all characters if enabled
        # Set to False to disable startup loading
        ENABLE_STARTUP_LOADING = False  # Disabled by default to avoid slow startup
        if ENABLE_STARTUP_LOADING and config_instance.RAIDERIO_API_KEY:
            logger.info("Pre-fetching character runs on startup...")
            load_stats = await startup_loader.load_all_character_runs(enabled=True)
            if load_stats.get("status") == "completed":
                logger.info(f"Pre-fetch stats: {load_stats}")
        else:
            logger.info("Startup run loading is disabled (ENABLE_STARTUP_LOADING=False)")
        
        # Setup Discord bot
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True  # Required for admin commands that look up users
        
        bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
        
        # Store config reference on bot object
        bot._config = config_instance
        
        # Initialize handlers
        ai_handler = AIHandler(bot)
        bot._ai_handler = ai_handler  # Store reference for admin panel
        
        # Load all cogs
        cogs_to_load = [
            'src.commands.basic',
            'src.commands.history', 
            'src.commands.admin',
            'src.commands.search_context',
            'src.commands.help',
            'src.commands.raiderio',
            'src.commands.wow_characters',
            'src.commands.cleaning',
            'src.search.google',
            'src.events.handlers'
        ]
        
        for cog in cogs_to_load:
            try:
                await bot.load_extension(cog)
                logger.info(f"Loaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load {cog}: {e}")
        
        # Set up event handler references
        event_handler = bot.get_cog('EventHandlers')
        search_handler = bot.get_cog('GoogleSearch')
        
        if event_handler:
            event_handler.set_handlers(ai_handler, search_handler, None)
        
        return bot
        
    except ValueError as e:
        logger.error(f"Configuration Error: {e}")
        logger.error("Please check your environment variables and try again.")
        return None
    except Exception as e:
        logger.error(f"Setup Error: {e}")
        return None

async def main():
    """Main entry point"""
    logger.info("Starting Discord Bot...")
    
    bot = await setup_bot()
    if not bot:
        logger.error("Bot setup failed. Exiting.")
        return
    
    try:
        logger.info("Starting bot...")
        if hasattr(bot, '_config') and bot._config:
            await bot.start(bot._config.DISCORD_TOKEN)
        else:
            logger.error("No valid configuration found. Cannot start bot.")
            return
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        if bot:
            await bot.close()
            logger.info("Bot shutdown complete")
        

if __name__ == '__main__':
    asyncio.run(main())