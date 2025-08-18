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
                       "AI system using OpenAI for all functionality.",
            color=0x5865f2
        )
        
        # AI Interaction
        embed.add_field(
            name="🧠 AI Interaction",
            value="**@bot + message** - OpenAI with search/admin routing\n" +
                  "**@bot ai:** - Direct OpenAI chat (no search)\n" +
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
        
        # RaiderIO Commands
        embed.add_field(
            name="🏆 World of Warcraft",
            value="`!rio` - Character lookup (uses main character)\n" +
                  "`!rio_runs` - Recent Mythic+ runs\n" +
                  "`!rio_details <number>` - Detailed run information\n" +
                  "`!rio_list` - List all stored runs\n" +
                  "`!rio_affixes` - Current Mythic+ affixes\n" +
                  "`!add_char <name> <realm>` - Add WoW character",
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
                  "`!help crafting` - Dune crafting system\n" +
                  "`!help wow` - World of Warcraft commands" +
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
                description="AI features and routing",
                color=0x00ff7f
            )
            
            embed.add_field(
                name="🎯 Automatic Routing",
                value="**OpenAI (Default - Search & Admin):**\n" +
                      "• Query optimization → Google Search → AI analysis\n" +
                      "• Current events, news, latest information\n" +
                      "• Research questions, comparisons\n" +
                      "• Admin actions (kick, ban, etc.)\n" +
                      "• Questions needing web data\n\n" +
                      "**Direct AI (`ai:` prefix):**\n" +
                      "• Pure OpenAI chat without web search\n" +
                      "• Personal conversations, creative tasks\n" +
                      "• General knowledge questions",
                inline=False
            )
            
            embed.add_field(
                name="🔀 Force Provider Syntax",
                value="• `@bot ai: message` - Direct OpenAI chat\n" +
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
        
        elif category in ['wow', 'raiderio', 'warcraft']:
            embed = discord.Embed(
                title="🏆 World of Warcraft Commands",
                description="RaiderIO integration for Mythic+ and character data",
                color=0xf4c430
            )
            
            embed.add_field(
                name="🎮 Character Management",
                value="`!add_char <name> <realm> [region]` - Add character\n" +
                      "`!set_main [number]` - Set main character\n" +
                      "`!list_chars` - List your characters\n" +
                      "`!remove_char <number>` - Remove character\n" +
                      "`!clear_chars` - Clear all characters\n\n" +
                      "**Examples:**\n" +
                      "• `!add_char Thrall Mal'Ganis` (defaults to US)\n" +
                      "• `!add_char Gandalf Stormrage eu`",
                inline=False
            )
            
            embed.add_field(
                name="📊 Character Lookup",
                value="`!rio` - Profile for your main character\n" +
                      "`!rio 2` - Profile for your character #2\n" +
                      "`!rio <name> <realm> [region]` - Manual lookup\n\n" +
                      "**Shows:** Mythic+ score, recent high run, raid progress, gear",
                inline=False
            )
            
            embed.add_field(
                name="🏃 Mythic+ Runs",
                value="`!rio_runs` - Recent runs (main character)\n" +
                      "`!rio_runs 2` - Recent runs (character #2)\n" +
                      "`!rio_runs <name> <realm>` - Manual lookup\n" +
                      "`!rio_list [limit]` - List all stored runs (default: 20)\n\n" +
                      "**Shows:** Numbered list of recent runs with completion times and dates",
                inline=False
            )
            
            embed.add_field(
                name="🔍 Detailed Run Analysis",
                value="`!rio_details <number>` - Details for recent run\n" +
                      "`!rio_details 2 3` - Run #3 from character #2\n" +
                      "`!rio_details <run_id>` - Manual run ID lookup\n\n" +
                      "**Shows:** Team composition, affixes, precise timing, completion status",
                inline=False
            )
            
            embed.add_field(
                name="⚡ Weekly Affixes",
                value="`!rio_affixes` - Current affixes (US)\n" +
                      "`!rio_affixes 2` - Affixes for character #2's region\n" +
                      "`!rio_affixes eu` - Affixes for specific region\n\n" +
                      "**Shows:** Current week's Mythic+ modifiers with descriptions",
                inline=False
            )
            
            embed.add_field(
                name="📊 Season Cutoffs",
                value="`!rio_cutoff` - Rating thresholds (US, current season)\n" +
                      "`!rio_cutoff 2` - Cutoffs for character #2's region\n" +
                      "`!rio_cutoff eu` - EU region cutoffs\n" +
                      "`!rio_cutoff us season-tww-3` - Specific season\n\n" +
                      "**Shows:** Rating thresholds for top percentiles (99th, 95th, 90th, etc.)",
                inline=False
            )
            
            embed.add_field(
                name="⚙️ Season Management",
                value="`!rio_season` - View/set season for run details\n" +
                      "`!rio_season season-tww-3` - Set specific season\n" +
                      "`!rio_season current` - Use current season\n" +
                      "`!rio_season reset` - Reset to current\n\n" +
                      "**Affects:** !rio_details command (cutoffs always use current unless specified)",
                inline=False
            )
            
            embed.add_field(
                name="🌍 Supported Regions",
                value="• **US** (default)\n• **EU** (Europe)\n• **KR** (Korea)\n• **TW** (Taiwan)\n• **CN** (China)",
                inline=False
            )
            
            if user_is_admin:
                embed.add_field(
                    name="🛠️ Admin WoW Commands",
                    value="`!debug_chars` - Debug character data structure\n" +
                          "`!reload_chars` - Reload character data from file\n" +
                          "`!char_errors` - Show character loading errors\n" +
                          "`!force_save_chars` - Force save character data\n" +
                          "`!rio_prefetch` - Pre-fetch runs for all characters\n" +
                          "`!rio_reset_runs` - Reset runs database (new season)",
                    inline=False
                )
            
            embed.add_field(
                name="💡 Workflow Tips",
                value="1. Add your characters with `!add_char`\n" +
                      "2. Set your main with `!set_main`\n" +
                      "3. Use `!rio_runs` to see numbered recent runs\n" +
                      "4. Use `!rio_details <number>` for detailed analysis\n" +
                      "5. Use `!rio_list` to see all stored runs from all characters\n" +
                      "6. All commands work without stored characters too!",
                inline=False
            )
        
        else:
            embed = discord.Embed(
                title="❌ Unknown Category",
                description=f"Category '{category}' not found.\n\n" +
                           "**Available categories:**\n" +
                           "• `ai` - AI system details\n" +
                           "• `context` - Context management\n" +
                           "• `crafting` - Dune crafting system\n" +
                           "• `wow` - World of Warcraft commands" +
                           ("\n• `admin` - Admin commands" if user_is_admin else ""),
                color=0x95a5a6
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpCommands(bot))