#!/usr/bin/env python3
"""
Discord Bot - Hybrid AI System
Main entry point for the Discord bot with cross-AI functionality.

Features:
- Hybrid Groq + Perplexity AI routing
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

async def setup_bot():
    """Setup and configure the bot"""
    try:
        # Initialize and validate configuration
        from src.config import config as imported_config, init_config
        
        if imported_config is None:
            print("[INFO] Attempting to reinitialize configuration...")
            config_instance = init_config()
        else:
            config_instance = imported_config
            
        print("[OK] Configuration validated successfully")
        print(f"Bot will use AI model: {config_instance.AI_MODEL}")
        print(f"Rate limiting: {config_instance.AI_RATE_LIMIT_REQUESTS} requests per {config_instance.AI_RATE_LIMIT_WINDOW}s")
        
        # Load persistent data
        print("Loading persistent data...")
        await data_manager.load_all_data()
        print("[OK] Data loaded successfully")
        
        # Setup Discord bot
        intents = discord.Intents.default()
        intents.message_content = True
        
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
            'src.search.google',
            'src.events.handlers'
        ]
        
        for cog in cogs_to_load:
            try:
                await bot.load_extension(cog)
                print(f"[OK] Loaded {cog}")
            except Exception as e:
                print(f"[ERROR] Failed to load {cog}: {e}")
        
        # Set up event handler references
        event_handler = bot.get_cog('EventHandlers')
        search_handler = bot.get_cog('GoogleSearch')
        
        if event_handler:
            event_handler.set_handlers(ai_handler, search_handler, None)
        
        return bot
        
    except ValueError as e:
        print(f"[ERROR] Configuration Error: {e}")
        print("Please check your environment variables and try again.")
        return None
    except Exception as e:
        print(f"[ERROR] Setup Error: {e}")
        return None

async def main():
    """Main entry point"""
    print("[INFO] Starting Discord Bot...")
    
    bot = await setup_bot()
    if not bot:
        print("[ERROR] Bot setup failed. Exiting.")
        return
    
    try:
        print("[INFO] Starting bot...")
        if hasattr(bot, '_config') and bot._config:
            await bot.start(bot._config.DISCORD_TOKEN)
        else:
            print("[ERROR] No valid configuration found. Cannot start bot.")
            return
    except KeyboardInterrupt:
        print("\n[INFO] Bot stopped by user")
    except Exception as e:
        print(f"[ERROR] Bot error: {e}")
    finally:
        if bot:
            await bot.close()
            print("[OK] Bot shutdown complete")

if __name__ == '__main__':
    asyncio.run(main())