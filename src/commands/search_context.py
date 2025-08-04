import discord
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from ..admin.permissions import is_admin
from ..utils.logging import get_logger

logger = get_logger(__name__)

class SearchContextCommands(commands.Cog):
    """Commands for managing AI conversation context across providers."""
    
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._executing_commands: set[str] = set()  # Track commands being executed to prevent duplicates
    
    @commands.command(name='clear_search_context', aliases=['clear_context', 'reset_search'])
    async def clear_search_context(self, ctx: commands.Context) -> None:
        """Clear your conversation context for all AI providers.
        
        Args:
            ctx: Discord command context
        """
        command_key = f"clear_search_context_{ctx.author.id}"
        if command_key in self._executing_commands:
            logger.debug(f"Duplicate clear_search_context command detected for user {ctx.author.id}, ignoring")
            return
        
        self._executing_commands.add(command_key)
        try:
            # Clear unified context and provider tracking
            ai_handler = self.bot._ai_handler
            if ai_handler:
                conversation_key = f"{ctx.author.id}_{ctx.channel.id}"
                ai_handler.unified_conversation_contexts.pop(conversation_key, None)
                ai_handler.unified_last_activity.pop(conversation_key, None)
                ai_handler.conversation_providers.pop(conversation_key, None)
            
            await ctx.send("🧹 **All conversation context cleared** - Starting fresh conversation with cross-AI context support.")
        finally:
            self._executing_commands.discard(command_key)
    
    @commands.command(name='search_context_info', aliases=['context_info'])
    async def search_context_info(self, ctx: commands.Context) -> None:
        """Show information about your current conversation context.
        
        Args:
            ctx: Discord command context
        """
        command_key = f"search_context_info_{ctx.author.id}"
        if command_key in self._executing_commands:
            logger.debug(f"Duplicate search_context_info command detected for user {ctx.author.id}, ignoring")
            return
        
        self._executing_commands.add(command_key)
        try:
            # Initialize context info
            has_context = False
            
            # Get unified context info
            ai_handler = self.bot._ai_handler
            conversation_key = f"{ctx.author.id}_{ctx.channel.id}"
            unified_context = None
            unified_last_activity = None
            
            if ai_handler:
                unified_context = ai_handler.unified_conversation_contexts.get(conversation_key)
                unified_last_activity = ai_handler.unified_last_activity.get(conversation_key)
                current_provider = ai_handler.conversation_providers.get(conversation_key)
            
            embed = discord.Embed(title="🤖 Cross-AI Conversation Context", color=0x5865f2)
            
            # Current AI provider
            if ai_handler and conversation_key in ai_handler.conversation_providers:
                provider = ai_handler.conversation_providers[conversation_key]
                provider_names = {
                    "perplexity": "🌐 Perplexity (Web Search)",
                    "groq": "⚡ Groq (Chat/Admin)",
                    "claude": "🤖 Claude (Search/Admin)",
                    "hybrid": "🔄 Hybrid (Claude + Perplexity)"
                }
                provider_name = provider_names.get(provider, f"❓ {provider}")
                embed.add_field(name="Last Used AI", value=provider_name, inline=False)
            
            # Unified context (shared between both AIs)
            if unified_context and unified_last_activity:
                unified_expires = unified_last_activity + timedelta(minutes=30)
                if datetime.now() < unified_expires:
                    expires_str = unified_expires.strftime("%H:%M:%S")
                    embed.add_field(
                        name="🔄 Unified Context", 
                        value=f"**{len(unified_context)}** messages\nExpires: {expires_str}\nShared between both AIs",
                        inline=False
                    )
                    has_context = True
                else:
                    embed.add_field(name="🔄 Unified Context", value="No active context", inline=False)
                    has_context = False
            else:
                embed.add_field(name="🔄 Unified Context", value="No active context", inline=False)
                has_context = False
            
            # Provider info from conversation tracking
            if ai_handler and conversation_key in ai_handler.conversation_providers:
                provider_info = ai_handler.conversation_providers.get(conversation_key, "Unknown")
                embed.add_field(
                    name="🔄 Active Provider", 
                    value=f"Currently using: **{provider_info}**",
                    inline=True
                )
            
            if not has_context:
                embed.description = "No active conversation context. Your next message will start a new conversation that can switch between AIs while maintaining context."
            else:
                embed.description = "Active conversation context detected. You can switch between different AI providers while maintaining full context."
            
            await ctx.send(embed=embed)
        finally:
            self._executing_commands.discard(command_key)
    
    @commands.command(name='clear_all_search_contexts')
    @commands.check(lambda ctx: is_admin(ctx.author.id))
    async def clear_all_search_contexts(self, ctx: commands.Context) -> None:
        """[Admin] Clear all conversation contexts for all users.
        
        Args:
            ctx: Discord command context
        """
        command_key = f"clear_all_search_contexts_{ctx.author.id}"
        if command_key in self._executing_commands:
            logger.debug(f"Duplicate clear_all_search_contexts command detected from admin {ctx.author.id}, ignoring")
            return
        
        self._executing_commands.add(command_key)
        try:
            # Clear all unified contexts and provider tracking
            ai_handler = self.bot._ai_handler
            if ai_handler:
                ai_handler.unified_conversation_contexts.clear()
                ai_handler.unified_last_activity.clear()
                ai_handler.conversation_providers.clear()
            
            await ctx.send("🧹 **All conversation contexts cleared** - All users will start fresh conversations with cross-AI context support.")
        finally:
            self._executing_commands.discard(command_key)

async def setup(bot: commands.Bot) -> None:
    """Set up the search context commands cog.
    
    Args:
        bot: Discord bot instance
    """
    await bot.add_cog(SearchContextCommands(bot))