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
import fcntl
import os
import sys
import time
from pathlib import Path
from src.config import config
from src.data.persistence import data_manager
from src.ai.handler_refactored import AIHandler
from src.utils.logging import setup_logger

# Set up logging
logger = setup_logger("discord_bot", level="INFO")

def acquire_instance_lock():
    """Ensure only one bot instance runs at a time"""
    lock_file = Path("data/bot.lock")
    
    # Create data directory if it doesn't exist
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Open lock file
        lock_fd = os.open(str(lock_file), os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
        
        # Try to acquire exclusive lock (non-blocking)
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        
        # Write current PID to lock file
        os.write(lock_fd, f"{os.getpid()}\n".encode())
        os.fsync(lock_fd)
        
        logger.info(f"✅ Acquired instance lock (PID: {os.getpid()})")
        return lock_fd
        
    except OSError as e:
        logger.critical(f"❌ ANOTHER BOT INSTANCE IS ALREADY RUNNING!")
        logger.critical(f"Lock file: {lock_file}")
        logger.critical(f"Error: {e}")
        
        # Try to read PID from existing lock file
        try:
            with open(lock_file, 'r') as f:
                existing_pid = f.read().strip()
            logger.critical(f"Existing instance PID: {existing_pid}")
        except:
            pass
            
        logger.critical("This prevents file corruption from multiple instances!")
        logger.critical("Stop the other instance or wait for it to finish.")
        sys.exit(1)

def check_deployment_status():
    """Check if deployment/shutdown is in progress and wait if needed"""
    deployment_lock = Path("data/deployment.lock")
    
    if deployment_lock.exists():
        try:
            with open(deployment_lock, 'r') as f:
                lock_content = f.read().strip()
            
            logger.warning(f"🔒 Deployment lock detected: {lock_content}")
            logger.warning("Waiting for previous instance to shut down completely...")
            
            # Wait up to 30 seconds for clean shutdown
            for i in range(30):
                if not deployment_lock.exists():
                    logger.info("✅ Deployment lock cleared, proceeding with startup")
                    return
                time.sleep(1)
                
            # If still locked after 30 seconds, force removal
            logger.warning("⚠️ Timeout waiting for deployment lock, forcing removal")
            deployment_lock.unlink()
            
        except Exception as e:
            logger.warning(f"Error checking deployment lock: {e}")
            # Remove corrupted lock file
            try:
                deployment_lock.unlink()
            except:
                pass

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
            'src.search.google',
            'src.events.handlers'
        ]
        
        for cog in cogs_to_load:
            try:
                logger.critical(f"🔄 ABOUT TO LOAD COG: {cog}")
                await bot.load_extension(cog)
                logger.critical(f"✅ LOADED COG: {cog}")
            except Exception as e:
                logger.error(f"Failed to load {cog}: {e}")
        
        # Set up event handler references
        logger.critical(f"🔄 ABOUT TO GET EVENT HANDLER COG")
        event_handler = bot.get_cog('EventHandlers')
        logger.critical(f"✅ GOT EVENT HANDLER COG")
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
    
    # CRITICAL: Check for deployment in progress
    check_deployment_status()
    
    # CRITICAL: Acquire single instance lock to prevent race conditions
    lock_fd = acquire_instance_lock()
    
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
        
        # Release instance lock
        try:
            if 'lock_fd' in locals():
                os.close(lock_fd)
                logger.info("✅ Released instance lock")
        except:
            pass

if __name__ == '__main__':
    asyncio.run(main())