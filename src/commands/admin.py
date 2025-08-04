import discord
from discord.ext import commands
from ..admin.permissions import is_admin
from ..data.persistence import data_manager
from ..config import config

class AdminCommands(commands.Cog):
    """Admin-only commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self._executing_commands = set()  # Track commands being executed to prevent duplicates
    
    @commands.command(name='stats')
    async def show_stats(self, ctx):
        """Show bot storage statistics"""
        stats = data_manager.get_stats()
        
        response = f"""**Bot Storage Statistics:**
📊 **Users tracked:** {stats['total_users']}
💬 **Total messages stored:** {stats['total_messages']}
🧠 **Permanent context items:** {stats['total_permanent_items']}
📁 **History file size:** {stats['file_sizes']['history']} bytes  
⚙️ **Settings file size:** {stats['file_sizes']['settings']} bytes
🧠 **Permanent context file size:** {stats['file_sizes']['permanent_context']} bytes

*Data persists between bot restarts*"""
        
        await ctx.send(response)
    
    @commands.command(name='remember')
    async def add_permanent_context(self, ctx, *, context_text):
        """Add permanent context that will always be included in AI conversations"""
        # Prevent duplicate execution
        command_key = f"remember_{ctx.author.id}_{hash(context_text)}"
        if command_key in self._executing_commands:
            print(f"DEBUG: Duplicate remember command detected, ignoring")
            return
        
        self._executing_commands.add(command_key)
        try:
            print(f"DEBUG: add_permanent_context called by {ctx.author.id} with text: '{context_text[:50]}...'")
            
            if not is_admin(ctx.author.id):
                await ctx.send(f"❌ You don't have permission to use permanent context commands.\nYour ID: {ctx.author.id}\nAuthorized ID: {config.AUTHORIZED_USER_ID}")
                return
        
            user_key = data_manager.get_user_key(ctx.author)
            
            # Resolve Discord mentions to usernames before saving
            import re
            resolved_text = context_text
            mention_pattern = r'<@!?(\d+)>'
            mentions = re.findall(mention_pattern, context_text)
            
            for user_id in mentions:
                try:
                    user = ctx.guild.get_member(int(user_id)) or self.bot.get_user(int(user_id))
                    if user:
                        mention_formats = [f'<@{user_id}>', f'<@!{user_id}>']
                        for mention_format in mention_formats:
                            resolved_text = resolved_text.replace(mention_format, user.display_name)
                        print(f"DEBUG: Resolved mention <@{user_id}> to '{user.display_name}'")
                except Exception as e:
                    print(f"DEBUG: Failed to resolve mention <@{user_id}>: {e}")
            
            # Check if this exact context already exists to prevent duplicates
            existing_context = data_manager.get_permanent_context(user_key)
            if resolved_text in existing_context:
                await ctx.send(f"⚠️ **Context already exists!**\nThis exact text is already in your permanent context.\n\nYou have {len(existing_context)} permanent context item(s).")
                return
            
            print(f"DEBUG: Adding context for user {user_key}. Current count: {len(existing_context)}")
            data_manager.add_permanent_context(user_key, resolved_text)
            await data_manager.save_permanent_context()
            
            context_count = len(data_manager.get_permanent_context(user_key))
            print(f"DEBUG: After adding, context count: {context_count}")
            # Show what was saved (with mentions resolved)
            display_text = resolved_text[:100] + "..." if len(resolved_text) > 100 else resolved_text
            await ctx.send(f"✅ **Permanent context added!**\n**Saved as:** {display_text}\n\nYou now have {context_count} permanent context item(s).\n\n*This will always be included in your AI conversations.*")
        
        finally:
            # Clean up execution tracker
            self._executing_commands.discard(command_key)
    
    @commands.command(name='memories')
    async def view_permanent_context(self, ctx):
        """View your permanent context items"""
        # Prevent duplicate execution
        command_key = f"memories_{ctx.author.id}"
        if command_key in self._executing_commands:
            print(f"DEBUG: Duplicate memories command detected, ignoring")
            return
        
        self._executing_commands.add(command_key)
        try:
            if not is_admin(ctx.author.id):
                await ctx.send(f"❌ You don't have permission to use permanent context commands.\nYour ID: {ctx.author.id}\nAuthorized ID: {config.AUTHORIZED_USER_ID}")
                return
            
            user_key = data_manager.get_user_key(ctx.author)
            context_items = data_manager.get_permanent_context(user_key)
            
            if not context_items:
                await ctx.send("You have no permanent context items stored.\nUse `!remember <text>` to add some!")
                return
            
            response = "**Your Permanent Context Items:**\n"
            for i, context in enumerate(context_items, 1):
                # Truncate long context for display and escape mentions
                display_text = context[:100] + "..." if len(context) > 100 else context
                display_text = display_text.replace("<@", "<\\@").replace("@everyone", "@\\everyone").replace("@here", "@\\here")
                response += f"**{i}.** {display_text}\n"
            
            response += f"\n*Total: {len(context_items)} items*"
            await ctx.send(response)
        
        finally:
            # Clean up execution tracker
            self._executing_commands.discard(command_key)
    
    @commands.command(name='forget')
    async def remove_permanent_context(self, ctx, item_number=None):
        """Remove a permanent context item by number, or clear all"""
        # Prevent duplicate execution
        command_key = f"forget_{ctx.author.id}_{item_number}"
        if command_key in self._executing_commands:
            print(f"DEBUG: Duplicate forget command detected, ignoring")
            return
        
        self._executing_commands.add(command_key)
        try:
            if not is_admin(ctx.author.id):
                await ctx.send(f"❌ You don't have permission to use permanent context commands.\nYour ID: {ctx.author.id}\nAuthorized ID: {config.AUTHORIZED_USER_ID}")
                return
            
            user_key = data_manager.get_user_key(ctx.author)
            context_items = data_manager.get_permanent_context(user_key)
            
            if not context_items:
                await ctx.send("You have no permanent context items to remove.")
                return
            
            if item_number is None:
                await ctx.send("Please specify which item to remove: `!forget <number>` or `!forget all`")
                return
            
            if str(item_number).lower() == 'all':
                count = data_manager.clear_permanent_context(user_key)
                await data_manager.save_permanent_context()
                await ctx.send(f"🗑️ **All permanent context cleared!** ({count} items removed)")
                return
            
            try:
                item_num = int(item_number)
                if 1 <= item_num <= len(context_items):
                    removed_item = data_manager.remove_permanent_context(user_key, item_num - 1)
                    await data_manager.save_permanent_context()
                    
                    # Show truncated version and escape mentions
                    display_text = removed_item[:100] + "..." if len(removed_item) > 100 else removed_item
                    display_text = display_text.replace("<@", "<\\@").replace("@everyone", "@\\everyone").replace("@here", "@\\here")
                    await ctx.send(f"🗑️ **Removed permanent context item {item_num}:**\n`{display_text}`")
                else:
                    await ctx.send(f"Invalid item number. You have {len(context_items)} items. Use `!memories` to see them.")
            except ValueError:
                await ctx.send("Please provide a valid item number or 'all'. Example: `!forget 2` or `!forget all`")
        
        finally:
            # Clean up execution tracker
            self._executing_commands.discard(command_key)
    
    @commands.command(name='admin_panel')
    async def admin_panel(self, ctx):
        """Show pending admin actions awaiting confirmation"""
        if not is_admin(ctx.author.id):
            await ctx.send(f"❌ **Access Denied**: Admin panel restricted.\nYour ID: {ctx.author.id}\nAuthorized ID: {config.AUTHORIZED_USER_ID}")
            return
        
        # This will be populated by the AI handler's pending actions
        from ..ai.handler_refactored import AIHandler
        ai_handler = getattr(self.bot, '_ai_handler', None)
        
        if not ai_handler or not ai_handler.pending_admin_actions:
            await ctx.send("✅ **Admin Panel**: No pending admin actions.")
            return
        
        response = "🛡️ **Admin Panel - Pending Actions**\n\n"
        
        for user_id, action_data in ai_handler.pending_admin_actions.items():
            try:
                user = self.bot.get_user(user_id)
                user_name = user.name if user else f"User {user_id}"
                action_type = action_data["action_type"]
                
                # Format action description based on type
                action_desc = self._format_action_description(action_type, action_data.get("parameters", {}))
                
                response += f"**{user_name}**: {action_desc}\n"
                
                # Add message link if available
                if "confirmation_message" in action_data:
                    conf_msg = action_data["confirmation_message"]
                    try:
                        message_link = f"https://discord.com/channels/{conf_msg.guild.id}/{conf_msg.channel.id}/{conf_msg.id}"
                        response += f"[Jump to confirmation message]({message_link})\n"
                    except Exception:
                        pass
                
                response += "\n"
                
            except Exception as e:
                response += f"**Error loading action for user {user_id}**: {str(e)}\n\n"
        
        response += f"*Total pending actions: {len(ai_handler.pending_admin_actions)}*"
        
        # Use smart message splitting
        from ..utils.message_utils import smart_split_message
        message_chunks = smart_split_message(response)
        for chunk in message_chunks:
            await ctx.send(chunk)
    
    def _format_action_description(self, action_type: str, parameters: dict) -> str:
        """Format action description for display"""
        if action_type == "kick_user":
            target = parameters.get("user")
            return f"Kick {target.mention if target else 'user'}"
        elif action_type == "ban_user":
            target = parameters.get("user")
            delete_days = parameters.get("delete_days", 0)
            return f"Ban {target.mention if target else 'user'} (delete {delete_days} days)"
        elif action_type == "timeout_user":
            target = parameters.get("user")
            duration = parameters.get("duration", 60)
            return f"Timeout {target.mention if target else 'user'} for {duration}min"
        elif action_type == "bulk_delete":
            limit = parameters.get("limit", 100)
            user_filter = parameters.get("user_filter")
            if user_filter:
                return f"Delete {limit} messages from {user_filter.mention}"
            else:
                return f"Delete {limit} messages"
        else:
            return f"Unknown action: {action_type}"

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))