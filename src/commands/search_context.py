import discord
from discord.ext import commands
from datetime import datetime, timedelta
from ..search.perplexity import perplexity_search
from ..admin.permissions import is_admin

class SearchContextCommands(commands.Cog):
    """Commands for managing Perplexity search conversation context"""
    
    def __init__(self, bot):
        self.bot = bot
        self._executing_commands = set()  # Track commands being executed to prevent duplicates
    
    @commands.command(name='clear_search_context', aliases=['clear_context', 'reset_search'])
    async def clear_search_context(self, ctx):
        """Clear your conversation context for both AI providers"""
        command_key = f"clear_search_context_{ctx.author.id}"
        if command_key in self._executing_commands:
            print(f"DEBUG: Duplicate clear_search_context command detected, ignoring")
            return
        
        self._executing_commands.add(command_key)
        try:
            # Clear Perplexity context
            perplexity_search.clear_context(ctx.author.id, ctx.channel.id)
            
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
    async def search_context_info(self, ctx):
        """Show information about your current conversation context"""
        command_key = f"search_context_info_{ctx.author.id}"
        if command_key in self._executing_commands:
            print(f"DEBUG: Duplicate search_context_info command detected, ignoring")
            return
        
        self._executing_commands.add(command_key)
        try:
            # Get Perplexity context info
            perplexity_info = perplexity_search.get_context_info(ctx.author.id, ctx.channel.id)
            
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
                provider_name = "🌐 Perplexity (Web Search)" if provider == "perplexity" else "⚡ Groq (Chat/Admin)"
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
            
            # Legacy Perplexity context (for backwards compatibility)
            if perplexity_info["has_context"]:
                expires_str = perplexity_info["expires_at"].strftime("%H:%M:%S") if perplexity_info["expires_at"] else "Unknown"
                embed.add_field(
                    name="🌐 Legacy Perplexity Context", 
                    value=f"**{perplexity_info['message_count']}** messages\nExpires: {expires_str}",
                    inline=True
                )
                has_context = True
            
            if not has_context:
                embed.description = "No active conversation context. Your next message will start a new conversation that can switch between AIs while maintaining context."
            else:
                embed.description = "Active conversation context detected. You can switch between web search (Perplexity) and chat/admin (Groq) while maintaining full context."
            
            await ctx.send(embed=embed)
        finally:
            self._executing_commands.discard(command_key)
    
    @commands.command(name='clear_all_search_contexts')
    @commands.check(lambda ctx: is_admin(ctx.author.id))
    async def clear_all_search_contexts(self, ctx):
        """[Admin] Clear all conversation contexts for all users"""
        command_key = f"clear_all_search_contexts_{ctx.author.id}"
        if command_key in self._executing_commands:
            print(f"DEBUG: Duplicate clear_all_search_contexts command detected, ignoring")
            return
        
        self._executing_commands.add(command_key)
        try:
            # Clear all Perplexity contexts
            perplexity_search.clear_all_contexts()
            
            # Clear all unified contexts and provider tracking
            ai_handler = self.bot._ai_handler
            if ai_handler:
                ai_handler.unified_conversation_contexts.clear()
                ai_handler.unified_last_activity.clear()
                ai_handler.conversation_providers.clear()
            
            await ctx.send("🧹 **All conversation contexts cleared** - All users will start fresh conversations with cross-AI context support.")
        finally:
            self._executing_commands.discard(command_key)

async def setup(bot):
    await bot.add_cog(SearchContextCommands(bot))