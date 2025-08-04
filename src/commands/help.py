import discord
from discord.ext import commands
from ..admin.permissions import is_admin

class HelpCommands(commands.Cog):
    """Help and information commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='help', aliases=['commands', 'h'])
    async def help_command(self, ctx, category: str = None):
        """Show all available commands or commands in a specific category"""
        if category:
            await self._show_category_help(ctx, category.lower())
        else:
            await self._show_main_help(ctx)
    
    async def _show_main_help(self, ctx):
        """Show the main help menu with all categories"""
        user_is_admin = is_admin(ctx.author.id)
        
        embed = discord.Embed(
            title="🤖 J.A.R.V.I.S Discord Bot",
            description="**Primary Interaction**: @mention the bot + your message\n" +
                       "Hybrid AI system using Groq + Claude for intelligent query routing.",
            color=0x5865f2
        )
        
        # AI Interaction
        embed.add_field(
            name="🧠 AI Interaction",
            value="**@bot + message** - Auto-routes to appropriate AI\n" +
                  "**@bot groq:** or **@bot g:** - Force Groq\n" +
                  "**@bot claude:** - Force Claude web search\n" +
                  "**@bot perplexity:** or **@bot p:** - Force Perplexity search\n" +
                  "**@bot search:** - Direct Google search\n" +
                  "**@bot craft:** or **@bot cr:** - Crafting system",
            inline=False
        )
        
        # Regular Commands
        embed.add_field(
            name="📝 Commands",
            value="`!help <category>` - Show category help\n" +
                  "`!ping` - Check bot responsiveness\n" +
                  "`!hello` - Greet the bot\n" +
                  "`!search <query>` - Google search (top 3 results)",
            inline=False
        )
        
        # Context Commands
        embed.add_field(
            name="🔄 Context Management", 
            value="`!remember <text>` - Add permanent context\n" +
                  "`!memories` - View your permanent context\n" +
                  "`!forget <number/all>` - Remove context\n" +
                  "`!add_setting <text>` - Add unfiltered setting\n" +
                  "`!list_settings` - View unfiltered settings\n" +
                  "`!remove_setting <number>` - Remove setting",
            inline=False
        )
        
        # History Commands
        embed.add_field(
            name="📚 History & Settings",
            value="`!clear` - Clear conversation history\n" +
                  "`!history` - Show recent conversations\n" +
                  "`!context [on/off]` - Toggle channel context\n" +
                  "`!clear_settings` - Clear all unfiltered settings\n" +
                  "`!clear_search_context` - Clear conversation context\n" +
                  "`!search_context_info` - Show context info",
            inline=False
        )
        
        # Admin Commands (only show if user is admin)
        if user_is_admin:
            embed.add_field(
                name="🛡️ Admin Features",
                value="`!admin_panel` - Show pending admin actions\n" +
                      "`!stats` - Show bot storage statistics\n" +
                      "`!clear_all_search_contexts` - Clear all contexts\n" +
                      "**Natural language admin via @mention**",
                inline=False
            )
        
        embed.add_field(
            name="📖 Categories",
            value="`!help ai` - AI system details\n" +
                  "`!help context` - Context management\n" +
                  "`!help crafting` - Dune crafting system" +
                  ("\n`!help admin` - Admin commands" if user_is_admin else ""),
            inline=False
        )
        
        embed.set_footer(text="Use !help <category> for detailed information")
        await ctx.send(embed=embed)
    
    async def _show_category_help(self, ctx, category):
        """Show help for a specific category"""
        user_is_admin = is_admin(ctx.author.id)
        
        if category in ['ai', 'bot']:
            embed = discord.Embed(
                title="🧠 AI System Details",
                description="Hybrid AI routing between Groq and Claude",
                color=0x00ff7f
            )
            
            embed.add_field(
                name="🎯 Automatic Routing",
                value="**Claude/Perplexity (Web Search via Google):**\n" +
                      "• Both use: Query optimization → Google Search → AI analysis\n" +
                      "• Current events, news, latest information\n" +
                      "• Research questions, comparisons\n" +
                      "• Questions needing web data\n\n" +
                      "**Groq (Chat/Admin):**\n" +
                      "• Personal conversations, jokes\n" +
                      "• Admin actions (kick, ban, etc.)\n" +
                      "• General knowledge questions",
                inline=False
            )
            
            embed.add_field(
                name="🔀 Force Provider Syntax",
                value="• `@bot groq: message` or `@bot g: message`\n" +
                      "• `@bot claude: message` - Claude + Google search\n" +
                      "• `@bot perplexity: message` or `@bot p: message`\n" +
                      "• `@bot search: query` - Direct Google search\n" +
                      "• `@bot craft: item` or `@bot cr: item`",
                inline=False
            )
            
            if user_is_admin:
                embed.add_field(
                    name="🔧 Admin: OpenAI Models",
                    value="• `@bot use gpt-4o-mini to...` - Fast (default)\n" +
                          "• `@bot with gpt-4o...` - Balanced\n" +
                          "• `@bot model: gpt-4-turbo...` - Most capable",
                    inline=False
                )
        
        elif category == 'context':
            embed = discord.Embed(
                title="🔄 Context Management",
                description="Manage AI memory and settings",
                color=0xff6b6b
            )
            
            embed.add_field(
                name="📝 Permanent Context",
                value="`!remember <text>` - Add permanent context\n" +
                      "`!memories` - View all permanent context\n" +
                      "`!forget <number>` - Remove specific item\n" +
                      "`!forget all` - Clear all permanent context",
                inline=False
            )
            
            embed.add_field(
                name="⚙️ Unfiltered Settings",
                value="`!add_setting <text>` - Add unfiltered setting\n" +
                      "`!list_settings` - View all settings\n" +
                      "`!remove_setting <number>` - Remove by number\n" +
                      "`!clear_settings` - Clear all settings",
                inline=False
            )
            
            embed.add_field(
                name="🔍 Conversation Context",
                value="`!clear` - Clear conversation history\n" +
                      "`!history` - Show recent conversations\n" +
                      "`!context [on/off]` - Toggle channel context\n" +
                      "`!clear_search_context` - Clear current context\n" +
                      "`!search_context_info` - Show context info",
                inline=False
            )
            
            embed.add_field(
                name="💡 Context Types",
                value="**Permanent**: Always remembered, filtered by relevance\n" +
                      "**Unfiltered**: Always included, never filtered\n" +
                      "**Conversation**: Recent chat (expires after 30min)",
                inline=False
            )
        
        elif category in ['crafting', 'craft', 'dune']:
            embed = discord.Embed(
                title="🔨 Dune Awakening Crafting",
                description="Natural language crafting calculator",
                color=0x9b59b6
            )
            
            embed.add_field(
                name="🎯 Usage",
                value="`@bot craft: <item>` or `@bot cr: <item>`\n\n" +
                      "**Examples:**\n" +
                      "• `@bot craft: karpov 38 plastanium`\n" +
                      "• `@bot craft: sandbike mk3`\n" +
                      "• `@bot craft: 5 healing kits`\n" +
                      "• `@bot craft: list` - Show categories",
                inline=False
            )
            
            embed.add_field(
                name="📊 Database Stats",
                value="• **232 Total Recipes**\n" +
                      "• ~50 Weapons (7 material tiers)\n" +
                      "• ~150 Vehicles (sandbikes, buggies, ornithopters)\n" +
                      "• Tools, components, materials",
                inline=False
            )
            
            embed.add_field(
                name="⚔️ Material Tiers",
                value="Salvage → Copper → Iron → Steel →\n" +
                      "Aluminum → Duraluminum → Plastanium",
                inline=False
            )
        
        elif category == 'admin' and user_is_admin:
            embed = discord.Embed(
                title="🛡️ Admin Commands",
                description="Natural language admin with confirmations",
                color=0xe74c3c
            )
            
            embed.add_field(
                name="📊 Admin Commands",
                value="`!admin_panel` - Show pending actions\n" +
                      "`!stats` - Bot storage statistics\n" +
                      "`!clear_all_search_contexts` - Clear all user contexts",
                inline=False
            )
            
            embed.add_field(
                name="👥 Natural Language Admin",
                value="**User Management:**\n" +
                      "• `@bot kick @user`\n" +
                      "• `@bot ban @user for reason`\n" +
                      "• `@bot timeout @user for 1 hour`\n\n" +
                      "**Messages:**\n" +
                      "• `@bot delete 10 messages`\n" +
                      "• `@bot delete messages from @user`\n\n" +
                      "**Roles:**\n" +
                      "• `@bot add role RoleName to @user`\n" +
                      "• `@bot remove role RoleName from @user`\n" +
                      "• `@bot rename role OldName to NewName`",
                inline=False
            )
            
            embed.add_field(
                name="⚠️ Safety",
                value="All actions require confirmation:\n" +
                      "• React ✅ to confirm\n" +
                      "• React ❌ to cancel\n" +
                      "• Auto-expires after 5 minutes",
                inline=False
            )
        
        else:
            embed = discord.Embed(
                title="❌ Unknown Category",
                description=f"Category '{category}' not found.\n\n" +
                           "**Available categories:**\n" +
                           "• `ai` - AI system details\n" +
                           "• `context` - Context management\n" +
                           "• `crafting` - Dune crafting system" +
                           ("\n• `admin` - Admin commands" if user_is_admin else ""),
                color=0x95a5a6
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpCommands(bot))