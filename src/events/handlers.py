import discord
from discord.ext import commands
from typing import Optional, Any
from ..utils.logging import get_logger

logger = get_logger(__name__)

class EventHandlers(commands.Cog):
    """Discord event handlers"""
    
    _instance_count = 0
    
    def __init__(self, bot: commands.Bot) -> None:
        EventHandlers._instance_count += 1
        self.instance_id = EventHandlers._instance_count
        logger.debug(f"Creating EventHandlers instance #{self.instance_id}")
        
        self.bot = bot
        self.ai_handler = None
        self.search_handler = None
        self.crafting_handler = None
    
    def set_handlers(self, ai_handler: Any, search_handler: Any, crafting_handler: Any) -> None:
        """Set handler references after bot initialization"""
        self.ai_handler = ai_handler
        self.search_handler = search_handler
        self.crafting_handler = crafting_handler
    
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Called when the bot is ready"""
        logger.info(f'{self.bot.user} has connected to Discord!')
        
        # Initialize channel context from recent messages
        if self.ai_handler and hasattr(self.ai_handler, 'context_manager'):
            await self._initialize_channel_contexts()
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User) -> None:
        """Handle admin action confirmations via reactions"""
        if user.bot:
            return
        
        if self.ai_handler:
            await self.ai_handler.handle_admin_reaction(reaction, user)
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Handle incoming messages"""
        if message.author == self.bot.user:
            return
        
        logger.debug(f'[{message.channel}] {message.author}: {message.content} (msg_id: {message.id})')
        
        # Capture channel message for context (non-empty messages only)
        if message.content.strip() and self.ai_handler and hasattr(self.ai_handler, 'context_manager'):
            self.ai_handler.context_manager.add_channel_message(
                message.channel.id, 
                message.author.display_name, 
                message.content
            )
        
        # Check if bot is mentioned and message contains "craft:" or crafting shorthand
        if self.bot.user.mentioned_in(message):
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
                logger.debug(f"[EventHandler-{self.instance_id}] Routing to crafting system: {craft_query}")
                await self.ai_handler.handle_ai_command(message, craft_query, "crafting")
                return
            
            # Check for ai: pattern (direct AI chat)
            elif "ai:" in content:
                ai_index = content.find("ai:")
                query = message.content[ai_index + 3:].strip()
                
                if query and self.ai_handler:
                    logger.debug(f"[EventHandler-{self.instance_id}] Forcing direct AI for: {query}")
                    await self.ai_handler.handle_ai_command(message, query, force_provider="direct-ai")
                return
            
            # Default AI processing
            else:
                ai_query = message.content
                logger.debug(f"AI query: {ai_query}")
                
                if ai_query and self.ai_handler:
                    try:
                        logger.debug(f"[EventHandler-{self.instance_id}] Calling AI handler for message {message.id}")
                        await self.ai_handler.handle_ai_command(message, ai_query)
                    except Exception as e:
                        logger.error(f"[EventHandler-{self.instance_id}] AI handler failed for message {message.id}: {e}")
                        await message.channel.send(f"❌ Error processing your request: {str(e)}")
                        return
        
        
        # Process commands
        await self.bot.process_commands(message)
    
    async def _initialize_channel_contexts(self) -> None:
        """Initialize channel context from recent messages on startup"""
        try:
            logger.debug("Initializing channel contexts...")
            context_manager = self.ai_handler.context_manager
            channels_initialized = 0
            
            # Iterate through all text channels the bot can see
            for guild in self.bot.guilds:
                for channel in guild.text_channels:
                    try:
                        # Check if bot has permission to read message history
                        permissions = channel.permissions_for(guild.me)
                        if not permissions.read_message_history:
                            continue
                        
                        # Fetch last 50 messages and add to context
                        messages_added = 0
                        async for message in channel.history(limit=50):
                            # Skip bot messages and empty messages
                            if message.author.bot or not message.content.strip():
                                continue
                            
                            context_manager.add_channel_message(
                                channel.id,
                                message.author.display_name,
                                message.content
                            )
                            messages_added += 1
                        
                        if messages_added > 0:
                            channels_initialized += 1
                            logger.debug(f"Initialized {messages_added} messages for #{channel.name}")
                            
                    except Exception as e:
                        logger.debug(f"Failed to initialize context for #{channel.name}: {e}")
                        continue
            
            logger.info(f"Channel context initialization complete - {channels_initialized} channels initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize channel contexts: {e}")

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EventHandlers(bot))