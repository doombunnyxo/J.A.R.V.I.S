import discord
from discord.ext import commands
from ..data.persistence import data_manager

class HistoryCommands(commands.Cog):
    """Commands for managing conversation history"""
    
    def __init__(self, bot):
        self.bot = bot
        self._executing_commands = set()  # Track commands being executed to prevent duplicates
    
    @commands.command(name='clear')
    async def clear_history(self, ctx):
        """Clear your conversation history with the AI"""
        command_key = f"clear_{ctx.author.id}"
        if command_key in self._executing_commands:
            return
        
        self._executing_commands.add(command_key)
        try:
            user_key = data_manager.get_user_key(ctx.author)
            if data_manager.clear_user_history(user_key):
                await data_manager.save_conversation_history()
                await ctx.send('✅ Your conversation history has been cleared!')
            else:
                await ctx.send('No conversation history to clear.')
        finally:
            self._executing_commands.discard(command_key)
    
    @commands.command(name='history')
    async def show_history(self, ctx):
        """Show your recent conversation history"""
        command_key = f"history_{ctx.author.id}"
        if command_key in self._executing_commands:
            return
        
        self._executing_commands.add(command_key)
        try:
            user_key = data_manager.get_user_key(ctx.author)
            history = data_manager.get_user_history(user_key)
            
            if not history:
                await ctx.send('No conversation history found.')
                return
            
            # Show last 6 messages
            recent_history = history[-6:]
            response = "**Recent conversation history:**\n"
            
            for msg in recent_history:
                role = "You" if msg["role"] == "user" else "AI"
                content = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
                response += f"**{role}:** {content}\n"
            
            await ctx.send(response)
        finally:
            self._executing_commands.discard(command_key)
    
    @commands.command(name='context')
    async def toggle_context(self, ctx, setting=None):
        """Toggle or check channel context usage for AI responses"""
        command_key = f"context_{ctx.author.id}_{setting}"
        if command_key in self._executing_commands:
            return
        
        self._executing_commands.add(command_key)
        try:
            user_key = data_manager.get_user_key(ctx.author)
            user_settings = data_manager.get_user_settings(user_key)
            
            if setting is None:
                # Show current setting
                current = user_settings.get("use_channel_context", True)
                status = "enabled" if current else "disabled"
                await ctx.send(f"Channel context is currently **{status}** for you.\nUse `!context on` or `!context off` to change.")
                return
            
            if setting.lower() in ['on', 'true', 'enable', 'yes']:
                data_manager.update_user_setting(user_key, "use_channel_context", True)
                await data_manager.save_user_settings()
                await ctx.send("✅ Channel context **enabled**! The AI will now read recent channel messages for better context.")
            elif setting.lower() in ['off', 'false', 'disable', 'no']:
                data_manager.update_user_setting(user_key, "use_channel_context", False)
                await data_manager.save_user_settings()
                await ctx.send("❌ Channel context **disabled**! The AI will only use your personal conversation history.")
            else:
                await ctx.send("Please use `!context on` or `!context off` to toggle channel context.")
        finally:
            self._executing_commands.discard(command_key)
    
    @commands.command(name='add_setting')
    async def add_unfiltered_setting(self, ctx, *, setting_text):
        """Add an unfiltered permanent setting that applies to ALL queries"""
        command_key = f"add_setting_{ctx.author.id}"
        if command_key in self._executing_commands:
            return
        
        self._executing_commands.add(command_key)
        try:
            user_key = data_manager.get_user_key(ctx.author)
            
            # Resolve Discord mentions to usernames before saving
            import re
            resolved_text = setting_text
            mention_pattern = r'<@!?(\d+)>'
            mentions = re.findall(mention_pattern, setting_text)
            
            for user_id in mentions:
                try:
                    user = ctx.guild.get_member(int(user_id)) or self.bot.get_user(int(user_id))
                    if user:
                        mention_formats = [f'<@{user_id}>', f'<@!{user_id}>']
                        for mention_format in mention_formats:
                            resolved_text = resolved_text.replace(mention_format, user.display_name)
                except Exception as e:
                    pass
            
            data_manager.add_unfiltered_permanent_context(resolved_text)
            await data_manager.save_unfiltered_permanent_context()
            await ctx.send(f'✅ **Global setting added!** This will apply to ALL users and queries:\n> {resolved_text}')
        finally:
            self._executing_commands.discard(command_key)
    
    @commands.command(name='list_settings')
    async def list_unfiltered_settings(self, ctx):
        """List all your unfiltered permanent settings"""
        command_key = f"list_settings_{ctx.author.id}"
        if command_key in self._executing_commands:
            return
        
        self._executing_commands.add(command_key)
        try:
            settings = data_manager.get_unfiltered_permanent_context()
            
            if not settings:
                await ctx.send('No global settings found.')
                return
            
            response = "**Global settings** (applied to ALL users and queries):\n"
            for i, setting in enumerate(settings, 1):
                # Truncate long settings for display
                display_setting = setting[:150] + "..." if len(setting) > 150 else setting
                response += f"{i}. {display_setting}\n"
            
            await ctx.send(response)
        finally:
            self._executing_commands.discard(command_key)
    
    @commands.command(name='remove_setting')
    async def remove_unfiltered_setting(self, ctx, index: int):
        """Remove an unfiltered permanent setting by its number (use !list_settings to see numbers)"""
        command_key = f"remove_setting_{ctx.author.id}_{index}"
        if command_key in self._executing_commands:
            return
        
        self._executing_commands.add(command_key)
        try:
            # Validate index
            if index < 1:
                await ctx.send(f'❌ Setting number must be 1 or higher. Use `!list_settings` to see valid numbers.')
                return
            
            # Get current settings to show count
            current_settings = data_manager.get_unfiltered_permanent_context()
            if not current_settings:
                await ctx.send('❌ No global settings found to remove.')
                return
            
            if index > len(current_settings):
                await ctx.send(f'❌ Invalid setting number: {index}. There are only {len(current_settings)} settings. Use `!list_settings` to see valid numbers.')
                return
            
            # Convert to 0-based index and remove
            removed_setting = data_manager.remove_unfiltered_permanent_context(index - 1)
            
            if removed_setting:
                await data_manager.save_unfiltered_permanent_context()
                # Truncate long settings for display
                display_setting = removed_setting[:100] + "..." if len(removed_setting) > 100 else removed_setting
                await ctx.send(f'✅ **Global setting removed:**\n> {display_setting}')
            else:
                await ctx.send(f'❌ Failed to remove setting {index}. Use `!list_settings` to see valid numbers.')
                
        except Exception as e:
            await ctx.send(f'❌ Error removing setting: {str(e)}')
        finally:
            self._executing_commands.discard(command_key)
    
    @commands.command(name='clear_settings')
    async def clear_unfiltered_settings(self, ctx):
        """Clear ALL your unfiltered permanent settings"""
        command_key = f"clear_settings_{ctx.author.id}"
        if command_key in self._executing_commands:
            return
        
        self._executing_commands.add(command_key)
        try:
            count = data_manager.clear_unfiltered_permanent_context()
            
            if count > 0:
                await data_manager.save_unfiltered_permanent_context()
                await ctx.send(f'✅ **Cleared {count} global setting(s)!**')
            else:
                await ctx.send('No global settings to clear.')
        finally:
            self._executing_commands.discard(command_key)

async def setup(bot):
    await bot.add_cog(HistoryCommands(bot))