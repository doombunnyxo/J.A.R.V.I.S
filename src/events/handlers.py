import discord
from discord.ext import commands

class EventHandlers(commands.Cog):
    """Discord event handlers"""
    
    _instance_count = 0
    
    def __init__(self, bot):
        EventHandlers._instance_count += 1
        self.instance_id = EventHandlers._instance_count
        print(f"DEBUG: Creating EventHandlers instance #{self.instance_id}")
        
        self.bot = bot
        self.ai_handler = None
        self.search_handler = None
        self.crafting_handler = None
    
    def set_handlers(self, ai_handler, search_handler, crafting_handler):
        """Set handler references after bot initialization"""
        self.ai_handler = ai_handler
        self.search_handler = search_handler
        self.crafting_handler = crafting_handler
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Called when the bot is ready"""
        print(f'{self.bot.user} has connected to Discord!')
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle admin action confirmations via reactions"""
        if user.bot:
            return
        
        if self.ai_handler:
            await self.ai_handler.handle_admin_confirmation(reaction, user)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle incoming messages"""
        if message.author == self.bot.user:
            return
        
        print(f'[{message.channel}] {message.author}: {message.content} (msg_id: {message.id})')
        
        # Check if bot is mentioned and message contains "search:"
        if self.bot.user.mentioned_in(message) and "search:" in message.content.lower():
            content = message.content.lower()
            search_index = content.find("search:")
            if search_index != -1:
                query = message.content[search_index + 7:].strip()
                if query and self.search_handler:
                    await self.search_handler.perform_search(message, query)
        
        # Check if bot is mentioned and message contains "craft:" or crafting shorthand
        elif self.bot.user.mentioned_in(message):
            content = message.content.lower()
            craft_query = None
            
            # Check for craft: pattern
            if "craft:" in content:
                craft_index = content.find("craft:")
                craft_query = message.content[craft_index + 6:].strip()
            
            # Check for cr: pattern (crafting shorthand)
            elif " cr:" in content:
                cr_index = content.find(" cr:")
                craft_query = message.content[cr_index + 4:].strip()
            
            # Route to crafting if we found a craft pattern
            if craft_query:
                print(f"DEBUG: [EventHandler-{self.instance_id}] Routing to crafting system: {craft_query}")
                await self.ai_handler.handle_ai_command(message, f"craft: {craft_query}", "crafting")
                return
            
            # Check for groq: or g: patterns
            elif "groq:" in content or " g:" in content:
                if "groq:" in content:
                    groq_index = content.find("groq:")
                    query = message.content[groq_index + 5:].strip()
                else:  # " g:" case
                    g_index = content.find(" g:")
                    query = message.content[g_index + 3:].strip()
                
                if query and self.ai_handler:
                    print(f"DEBUG: [EventHandler-{self.instance_id}] Forcing Groq for: {query}")
                    await self.ai_handler.handle_ai_command(message, query, force_provider="groq")
                return
            
            # Check for perplexity: or p: patterns
            elif "perplexity:" in content or " p:" in content:
                if "perplexity:" in content:
                    perplexity_index = content.find("perplexity:")
                    query = message.content[perplexity_index + 11:].strip()
                else:  # " p:" case
                    p_index = content.find(" p:")
                    query = message.content[p_index + 3:].strip()
                
                if query and self.ai_handler:
                    print(f"DEBUG: [EventHandler-{self.instance_id}] Forcing Perplexity for: {query}")
                    await self.ai_handler.handle_ai_command(message, query, force_provider="perplexity")
                return
            
            # Default AI processing
            else:
                ai_query = message.content
                print(f"Debug: ai query: {ai_query}")
                
                if ai_query and self.ai_handler:
                    print(f"DEBUG: [EventHandler-{self.instance_id}] Calling AI handler for message {message.id}")
                    await self.ai_handler.handle_ai_command(message, ai_query)
        
        # Direct search command (legacy support)
        elif self.bot.user.mentioned_in(message) and "search:" in message.content.lower():
            content = message.content.lower()
            search_index = content.find("search:")
            if search_index != -1:
                query = message.content[search_index + 7:].strip()
                if query and self.search_handler:
                    await self.search_handler.perform_search(message, query)
        
        # Process commands
        await self.bot.process_commands(message)

async def setup(bot):
    await bot.add_cog(EventHandlers(bot))