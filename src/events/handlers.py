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
        # Capture ALL messages for context (both user and bot messages)
        if message.content.strip() and self.ai_handler and hasattr(self.ai_handler, 'context_manager'):
            # Use bot display name for bot messages, user display name for user messages
            display_name = "J.A.R.V.I.S" if message.author == self.bot.user else message.author.display_name
            self.ai_handler.context_manager.add_channel_message(
                message.channel.id, 
                display_name, 
                message.content,
                message.channel  # Pass channel object for thread detection
            )
        
        # Return early for bot messages (don't process them as commands)
        if message.author == self.bot.user:
            return
        
        logger.debug(f'[{message.channel}] {message.author}: {message.content} (msg_id: {message.id})')
        
        # Check if this is a reply to the bot, in a thread, or a direct mention
        is_reply_to_bot = (message.reference and 
                          message.reference.resolved and 
                          message.reference.resolved.author == self.bot.user)
        is_direct_mention = self.bot.user in message.mentions
        is_in_thread = hasattr(message.channel, 'type') and str(message.channel.type) in ['public_thread', 'private_thread']
        
        if is_reply_to_bot or is_direct_mention or is_in_thread:
            # Log the interaction type for debugging
            interaction_type = []
            if is_reply_to_bot:
                interaction_type.append("reply")
            if is_direct_mention:
                interaction_type.append("mention")
            if is_in_thread:
                interaction_type.append("thread")
            interaction_str = "+".join(interaction_type) if interaction_type else "unknown"
            logger.debug(f"[EventHandler-{self.instance_id}] Processing {interaction_str} from {message.author.display_name}")
            
            # Check for search: override in threads
            content = message.content.lower()
            if is_in_thread and "search:" in content:
                # Extract search query and force search mode
                search_index = content.find("search:")
                search_query = message.content[search_index + 7:].strip()
                if search_query and self.ai_handler:
                    logger.debug(f"[EventHandler-{self.instance_id}] Thread search override: {search_query}")
                    await self.ai_handler.handle_ai_command(message, search_query, force_provider="openai")
                return
            
            # Auto-route replies and threads to direct AI (conversational mode)
            if is_reply_to_bot or is_in_thread:
                logger.debug(f"[EventHandler-{self.instance_id}] Auto-routing {interaction_str} to direct AI: {message.content}")
                await self.ai_handler.handle_ai_command(message, message.content, force_provider="direct-ai")
                return
            
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
            
            # Check for full: pattern (full page search with GPT-4o)
            elif "full:" in content:
                full_index = content.find("full:")
                query = message.content[full_index + 5:].strip()
                
                if query and self.ai_handler:
                    logger.debug(f"[EventHandler-{self.instance_id}] Forcing full page search for: {query}")
                    await self.ai_handler.handle_ai_command(message, query, force_provider="full-search")
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
                # Clean bot mentions from the query
                ai_query = message.content
                for mention in message.mentions:
                    if mention == self.bot.user:
                        ai_query = ai_query.replace(f"<@{mention.id}>", "").replace(f"<@!{mention.id}>", "")
                ai_query = ai_query.strip()
                
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
                                message.content,
                                channel  # Pass channel object for thread detection
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