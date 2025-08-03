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
            title="🤖 Discord Bot - Hybrid AI System",
            description="**Primary Interaction**: @mention the bot + your message\n" +
                       "The bot uses **Groq + Claude** for intelligent routing of your queries.",
            color=0x5865f2
        )
        
        # Main AI Interaction
        embed.add_field(
            name="🧠 AI Interaction (Primary)",
            value="**@mention the bot** + your message\n" +
                  "• Automatically routes to Claude (web search) or Groq (chat/admin)\n" +
                  "• Use `!help ai` for detailed AI commands",
            inline=False
        )
        
        # Force Provider Options
        embed.add_field(
            name="🔀 Force Specific AI Provider",
            value="• `@bot groq:` or `@bot g:` - Force Groq processing\n" +
                  "• `@bot claude:` or `@bot perplexity:` - Force Claude web search\n" +
                  "• `@bot search:` - Direct Google search\n" +
                  "• `@bot craft:` - Dune Awakening crafting system",
            inline=False
        )
        
        # Command Categories
        embed.add_field(
            name="📚 Command Categories",
            value="`!help basic` - Basic utility commands\n" +
                  "`!help context` - Permanent context management\n" +
                  "`!help history` - Conversation history\n" +
                  "`!help crafting` - Dune Awakening crafting system",
            inline=False
        )
        
        # Admin Commands (only show if user is admin)
        if user_is_admin:
            embed.add_field(
                name="🛡️ Admin Commands",
                value="`!help admin` - Administrative commands\n" +
                      "• Natural language admin actions via @mention\n" +
                      "• Reaction-based confirmations for safety",
                inline=False
            )
        
        embed.add_field(
            name="💡 Examples",
            value="• `@bot What's the latest news about AI?` (→ Claude web search)\n" +
                  "• `@bot Tell me a joke` (→ Groq chat)\n" +
                  "• `@bot kick @spammer` (→ Groq admin action)\n" +
                  "• `@bot craft: I need 5 healing kits` (→ Crafting system)",
            inline=False
        )
        
        embed.set_footer(text="Use !help <category> for detailed information")
        await ctx.send(embed=embed)
    
    async def _show_category_help(self, ctx, category):
        """Show help for a specific category"""
        user_is_admin = is_admin(ctx.author.id)
        
        if category in ['ai', 'search', 'claude', 'groq']:
            embed = discord.Embed(
                title="🧠 AI System - Hybrid Groq + Claude",
                description="The bot intelligently routes your queries to the best AI provider",
                color=0x00ff7f
            )
            
            embed.add_field(
                name="🎯 Automatic Routing",
                value="**@mention the bot + your message**\n\n" +
                      "**Claude** (Web Search) triggers:\n" +
                      "• Current events, news, latest information\n" +
                      "• Research questions, comparisons\n" +
                      "• \"What's the latest...\", \"Current price of...\", \"Best...\" etc.\n\n" +
                      "**Groq** (Chat/Admin) triggers:\n" +
                      "• Personal conversations, jokes, explanations\n" +
                      "• Admin actions (kick, ban, timeout, roles, channels)\n" +
                      "• General knowledge that doesn't need web search",
                inline=False
            )
            
            embed.add_field(
                name="🔀 Force Specific Provider",
                value="• `@bot groq: your question` or `@bot g: question`\n" +
                      "• `@bot claude: your question` or `@bot perplexity: question`\n" +
                      "• `@bot search: direct google search`",
                inline=False
            )
            
            embed.add_field(
                name="📋 Examples by Provider",
                value="**Claude (Web Search):**\n" +
                      "• `@bot What are the best laptops in 2025?`\n" +
                      "• `@bot Latest Bitcoin price`\n" +
                      "• `@bot Current weather in New York`\n\n" +
                      "**Groq (Chat/Admin):**\n" +
                      "• `@bot Tell me a programming joke`\n" +
                      "• `@bot Explain quantum computing`\n" +
                      "• `@bot Ban @troublemaker for spamming`",
                inline=False
            )
            
            # Add Claude model switching info for admins
            if user_is_admin:
                embed.add_field(
                    name="🔧 Claude Model Control [Admin Only]",
                    value="**Available Models:**\n" +
                          "• `haiku` - Fast, cost-effective (default)\n" +
                          "• `sonnet` - Balanced performance\n" +
                          "• `opus` - Most capable model\n\n" +
                          "**Usage Examples:**\n" +
                          "• `@bot use haiku to find crypto trends`\n" +
                          "• `@bot with sonnet analyze this data`\n" +
                          "• `@bot model: opus - comprehensive research`",
                    inline=False
                )
        
        elif category in ['context', 'permanent']:
            embed = discord.Embed(
                title="🔄 Permanent Context Management",
                description="Manage information that the AI always remembers about you",
                color=0xff6b6b
            )
            
            embed.add_field(
                name="📝 Basic Context Commands",
                value="• `!permanent_context <text>` - Add permanent context\n" +
                      "• `!list_permanent_context` - View your context items\n" +
                      "• `!remove_permanent_context <index>` - Remove specific item\n" +
                      "• `!clear_permanent_context` - Remove all context",
                inline=False
            )
            
            embed.add_field(
                name="🔓 Unfiltered Context Commands",
                value="• `!unfiltered_permanent_context <text>` - Add unfiltered context\n" +
                      "• `!list_unfiltered_permanent_context` - View unfiltered items\n" +
                      "• `!remove_unfiltered_permanent_context <index>` - Remove item\n" +
                      "• `!clear_unfiltered_permanent_context` - Clear all unfiltered",
                inline=False
            )
            
            embed.add_field(
                name="🔍 Context Search & Info",
                value="• `!search_context <query>` - Search your context items\n" +
                      "• `!clear_context` - Clear conversation context\n" +
                      "• `!context_info` - Show context status\n" +
                      "• `!toggle_channel_context` - Enable/disable channel context",
                inline=False
            )
            
            embed.add_field(
                name="💡 Context Types",
                value="**Regular Context:** Filtered for relevance to each query\n" +
                      "**Unfiltered Context:** Always included, never filtered\n" +
                      "**Conversation Context:** Recent chat history (auto-expires)",
                inline=False
            )
        
        elif category == 'basic':
            embed = discord.Embed(
                title="⚙️ Basic Commands",
                color=0x4ecdc4
            )
            
            embed.add_field(
                name="🏓 Utility Commands",
                value="• `!ping` - Check bot responsiveness\n" +
                      "• `!hello` - Greet the bot",
                inline=False
            )
            
            embed.add_field(
                name="⚙️ Settings Commands",
                value="• `!toggle_channel_context` - Use recent channel messages as context\n" +
                      "• `!context_info` - View your current settings",
                inline=False
            )
        
        elif category == 'history':
            embed = discord.Embed(
                title="📚 History Commands",
                color=0xffb347
            )
            
            embed.add_field(
                name="📖 Conversation History",
                value="• `!conversation_history` - View recent AI conversations\n" +
                      "• `!export_conversation` - Export history to file\n" +
                      "• `!clear_conversation_history` - Clear your history",
                inline=False
            )
            
            embed.add_field(
                name="🔄 Context Management",
                value="• `!clear_context` - Clear active conversation context\n" +
                      "• `!context_info` - Show current context status",
                inline=False
            )
        
        elif category in ['crafting', 'dune']:
            embed = discord.Embed(
                title="🔨 Dune Awakening Crafting System",
                description="Comprehensive crafting calculator with 79+ recipes",
                color=0x9b59b6
            )
            
            embed.add_field(
                name="🎯 Basic Usage",
                value="**@bot craft: <item request>**\n\n" +
                      "Examples:\n" +
                      "• `@bot craft: I need 5 healing kits`\n" +
                      "• `@bot craft: iron sword`\n" +
                      "• `@bot craft: house karpov rifle`\n" +
                      "• `@bot craft: list` - Show all available recipes",
                inline=False
            )
            
            embed.add_field(
                name="⚔️ Weapon Categories",
                value="**Standard Weapons (7 tiers):**\n" +
                      "• Rifles: Karpov 38, JABAL Spitdart\n" +
                      "• Sidearms: Maula Pistol, Disruptor M11\n" +
                      "• Long Blades: Sword, Rapier\n" +
                      "• Short Blades: Dirk, Kindjal\n" +
                      "• Scatterguns: Drillshot FK7, GRDA 44\n\n" +
                      "**Unique Weapons:** Piters Disruptor, The Tapper, Eviscerator, etc.",
                inline=False
            )
            
            embed.add_field(
                name="🏗️ Other Categories",
                value="• **Equipment:** Stillsuits, Spice Masks, Desert Garb\n" +
                      "• **Healing:** Healkit series (MK2, MK4, MK6)\n" +
                      "• **Materials:** Ingots, components, refined materials\n" +
                      "• **Buildings:** Foundations, walls, refineries\n" +
                      "• **Vehicles:** Ornithopter engines and parts",
                inline=False
            )
            
            embed.add_field(
                name="🎮 Natural Language",
                value="The system uses AI to understand natural requests:\n" +
                      "• \"craft me a mark 2 heal kit\" → healkit_mk2\n" +
                      "• \"I need steel weapons\" → finds steel tier items\n" +
                      "• \"house vulcan weapon\" → house_vulcan_gau_92",
                inline=False
            )
        
        elif category == 'admin' and user_is_admin:
            embed = discord.Embed(
                title="🛡️ Admin Commands",
                description="Natural language admin actions with safety confirmations",
                color=0xe74c3c
            )
            
            embed.add_field(
                name="👥 User Moderation",
                value="**@bot + natural language:**\n" +
                      "• `@bot kick @spammer` - Remove user from server\n" +
                      "• `@bot ban @troublemaker for harassment` - Permanent ban\n" +
                      "• `@bot timeout @user for 1 hour` - Temporary mute\n" +
                      "• `@bot remove timeout from @user` - Remove mute",
                inline=False
            )
            
            embed.add_field(
                name="📝 Message Management",
                value="• `@bot delete 10 messages` - Bulk delete recent messages\n" +
                      "• `@bot delete messages from @user` - Remove user's messages\n" +
                      "• `@bot purge 50 messages from this channel`",
                inline=False
            )
            
            embed.add_field(
                name="🏷️ Role Management",
                value="• `@bot add role Moderator to @user`\n" +
                      "• `@bot remove role Member from @user`\n" +
                      "• `@bot rename role Moderator to Super Mod`\n" +
                      "• `@bot reorganize roles for gaming server`",
                inline=False
            )
            
            embed.add_field(
                name="📢 Channel Management",
                value="• `@bot create text channel general-chat`\n" +
                      "• `@bot create voice channel Voice Chat`\n" +
                      "• `@bot delete channel old-announcements`",
                inline=False
            )
            
            embed.add_field(
                name="🎭 Nickname Management",
                value="• `@bot change @user nickname to NewName`\n" +
                      "• `@bot set my nickname to AdminName`",
                inline=False
            )
            
            embed.add_field(
                name="⚠️ Safety System",
                value="All admin actions require confirmation:\n" +
                      "• React ✅ to proceed\n" +
                      "• React ❌ to cancel\n" +
                      "• Actions auto-expire after 5 minutes",
                inline=False
            )
            
            embed.add_field(
                name="🎛️ Direct Admin Panel",
                value="`!admin_panel` - Open administrative control interface",
                inline=False
            )
        
        else:
            embed = discord.Embed(
                title="❌ Unknown Category",
                description=f"Category '{category}' not found.\n\n**Available categories:**\n" +
                           "• `ai` - AI system and providers\n" +
                           "• `context` - Permanent context management\n" +
                           "• `basic` - Basic utility commands\n" +
                           "• `history` - Conversation history\n" +
                           "• `crafting` - Dune Awakening crafting\n" +
                           ("• `admin` - Administrative commands\n" if user_is_admin else ""),
                color=0x95a5a6
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpCommands(bot))