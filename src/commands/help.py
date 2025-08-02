import discord
from discord.ext import commands
from ..admin.permissions import is_admin

class HelpCommands(commands.Cog):
    """Help and information commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self._executing_commands = set()  # Track commands being executed to prevent duplicates
    
    @commands.command(name='help', aliases=['commands', 'h'])
    async def help_command(self, ctx, category: str = None):
        """Show all available commands or commands in a specific category"""
        # Prevent duplicate execution
        command_key = f"help_{ctx.author.id}_{category}"
        if command_key in self._executing_commands:
            print(f"DEBUG: Duplicate help command detected, ignoring")
            return
        
        self._executing_commands.add(command_key)
        try:
            if category:
                # Show specific category
                await self._show_category_help(ctx, category.lower())
            else:
                # Show main help menu
                await self._show_main_help(ctx)
        
        finally:
            # Clean up execution tracker
            self._executing_commands.discard(command_key)
    
    async def _show_main_help(self, ctx):
        """Show the main help menu with all categories"""
        user_is_admin = is_admin(ctx.author.id)
        
        embed = discord.Embed(
            title="🤖 Discord Bot Commands",
            description="Use `!help <category>` for detailed commands in each category.",
            color=0x5865f2
        )
        
        # AI & Search Commands
        embed.add_field(
            name="🧠 AI & Search",
            value="`!help ai` - AI interaction and web search commands",
            inline=False
        )
        
        # Context Management
        embed.add_field(
            name="🔄 Context Management", 
            value="`!help context` - Conversation context commands",
            inline=False
        )
        
        # Basic Commands
        embed.add_field(
            name="⚙️ Basic Commands",
            value="`!help basic` - User settings and basic utilities",
            inline=False
        )
        
        # History Commands
        embed.add_field(
            name="📚 History",
            value="`!help history` - Message and conversation history",
            inline=False
        )
        
        # Crafting Commands
        embed.add_field(
            name="🔨 Crafting",
            value="`!help crafting` - Game crafting system commands",
            inline=False
        )
        
        # Admin Commands (only show if user is admin)
        if user_is_admin:
            embed.add_field(
                name="🛡️ Admin Commands",
                value="`!help admin` - Administrative commands",
                inline=False
            )
        
        embed.add_field(
            name="💡 AI Interaction",
            value="Simply **@mention the bot** to chat or ask questions!\n" +
                  "The bot automatically routes to web search or chat based on your question.",
            inline=False
        )
        
        embed.set_footer(text="Use !help <category> for detailed information")
        await ctx.send(embed=embed)
    
    async def _show_category_help(self, ctx, category):
        """Show help for a specific category"""
        user_is_admin = is_admin(ctx.author.id)
        
        if category in ['ai', 'search']:
            embed = discord.Embed(
                title="🧠 AI & Search Commands",
                color=0x00ff7f
            )
            embed.add_field(
                name="@mention the bot + your message",
                value="Automatically routes to appropriate AI:\n" +
                      "• **Web Search** (Perplexity): Current info, comparisons, research\n" +
                      "• **Chat/Admin** (Groq): Conversations, admin actions, analysis",
                inline=False
            )
            embed.add_field(
                name="Force Specific AI Provider",
                value="• `@bot groq: your question` or `@bot g: question` - Force Groq (chat/admin)\n" +
                      "• `@bot perplexity: your question` or `@bot p: question` - Force Perplexity (web search)",
                inline=False
            )
            embed.add_field(
                name="Examples",
                value="• `@bot What are the best laptops in 2024?` (→ Auto: Web Search)\n" +
                      "• `@bot g: Tell me a joke` (→ Forced: Groq)\n" +
                      "• `@bot p: What's the weather?` (→ Forced: Perplexity)\n" +
                      "• `@bot Delete 5 messages from John` (→ Auto: Admin)",
                inline=False
            )
            
            # Add Perplexity model switching info for admins
            if user_is_admin:
                embed.add_field(
                    name="🔧 Perplexity Model Switching [Admin Only]",
                    value="**Available Models:**\n" +
                          "• `sonar` - Lightweight, cost-effective (default)\n" +
                          "• `sonar-pro` - Advanced search with more citations\n" +
                          "• `sonar-reasoning` - Fast reasoning with search\n" +
                          "• `sonar-reasoning-pro` - Advanced reasoning model\n" +
                          "• `sonar-deep-research` - Expert-level research\n\n" +
                          "**Usage Examples:**\n" +
                          "• `@bot use pro to find crypto trends`\n" +
                          "• `@bot with reasoning model analyze this problem`\n" +
                          "• `@bot model: deep-research - comprehensive AI report`\n" +
                          "• `@bot [reasoning-pro] what are the implications...`",
                    inline=False
                )
        
        elif category == 'context':
            embed = discord.Embed(
                title="🔄 Context Management Commands",
                color=0xff6b6b
            )
            embed.add_field(
                name="!clear_context (aliases: !clear_search_context, !reset_search)",
                value="Clear your conversation context for both AI providers",
                inline=False
            )
            embed.add_field(
                name="!context_info (alias: !search_context_info)",
                value="Show your current conversation context status",
                inline=False
            )
            if user_is_admin:
                embed.add_field(
                    name="!clear_all_search_contexts [Admin]",
                    value="Clear all conversation contexts for all users",
                    inline=False
                )
            embed.add_field(
                name="💡 Cross-AI Context",
                value="Context is shared between both AIs! You can search with Perplexity then ask Groq to analyze the results.",
                inline=False
            )
        
        elif category == 'basic':
            embed = discord.Embed(
                title="⚙️ Basic Commands",
                color=0x4ecdc4
            )
            embed.add_field(
                name="!ping",
                value="Check if the bot is responsive",
                inline=False
            )
            embed.add_field(
                name="!permanent_context",
                value="Add permanent context that the AI will always remember",
                inline=False
            )
            embed.add_field(
                name="!list_permanent_context",
                value="View your current permanent context items",
                inline=False
            )
            embed.add_field(
                name="!remove_permanent_context <index>",
                value="Remove a specific permanent context item",
                inline=False
            )
            embed.add_field(
                name="!toggle_channel_context",
                value="Enable/disable using recent channel messages as context",
                inline=False
            )
        
        elif category == 'history':
            embed = discord.Embed(
                title="📚 History Commands",
                color=0xffb347
            )
            embed.add_field(
                name="!conversation_history",
                value="View your recent conversation history with the AI",
                inline=False
            )
            embed.add_field(
                name="!export_conversation",
                value="Export your conversation history to a file",
                inline=False
            )
            embed.add_field(
                name="!clear_conversation_history",
                value="Clear your conversation history",
                inline=False
            )
        
        elif category == 'crafting':
            embed = discord.Embed(
                title="🔨 Crafting Commands",
                color=0x9b59b6
            )
            embed.add_field(
                name="@mention the bot + craft: <item>",
                value="Use the crafting system to create items",
                inline=False
            )
            embed.add_field(
                name="Examples",
                value="• `@bot craft: iron sword`\n• `@bot craft: health potion`",
                inline=False
            )
        
        elif category == 'admin' and user_is_admin:
            embed = discord.Embed(
                title="🛡️ Admin Commands",
                color=0xe74c3c
            )
            embed.add_field(
                name="Admin Actions via AI",
                value="Use natural language with @mention:\n" +
                      "• `@bot delete 10 messages from @user`\n" +
                      "• `@bot ban @troublemaker`\n" +
                      "• `@bot kick @spammer`\n" +
                      "• `@bot timeout @user for 1 hour`\n" +
                      "• `@bot rename role @Moderator to \"Super Mod\"`\n" +
                      "• `@bot reorganize roles for gaming server`",
                inline=False
            )
            embed.add_field(
                name="Direct Admin Commands",
                value="!admin_panel - Open administrative control panel",
                inline=False
            )
            embed.add_field(
                name="💡 Admin System",
                value="Admin actions require confirmation via ✅/❌ reactions for safety.",
                inline=False
            )
        
        else:
            embed = discord.Embed(
                title="❌ Unknown Category",
                description=f"Category '{category}' not found. Use `!help` to see available categories.",
                color=0x95a5a6
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpCommands(bot))