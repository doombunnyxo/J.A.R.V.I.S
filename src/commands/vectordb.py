"""
Vector database management commands
"""

import discord
from discord.ext import commands
from ..utils.logging import get_logger
from ..vectordb.context_enhancer import vector_enhancer

logger = get_logger(__name__)


class VectorDBCommands(commands.Cog):
    """Commands for managing the vector database"""
    
    def __init__(self, bot):
        self.bot = bot
        self.vector_enhancer = vector_enhancer
        logger.info("VectorDBCommands cog initialized")
        
    @commands.Cog.listener()
    async def on_ready(self):
        """Log when the cog is ready"""
        logger.info(f"VectorDBCommands cog ready with {len(self.get_commands())} commands")
        for cmd in self.get_commands():
            logger.info(f"  - Command: !{cmd.name} (aliases: {cmd.aliases})")
    
    @commands.command(name="vdb_history")
    async def vdb_history(self, ctx, days: int = 7):
        """Show your conversation history from the past N days"""
        try:
            if not self.vector_enhancer.initialized:
                await ctx.send("Vector database is not initialized")
                return
            
            from datetime import datetime, timedelta
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Get user's recent conversations
            collection = self.vector_enhancer.vector_db.collections.get('conversations')
            if not collection:
                await ctx.send("Conversations collection not found")
                return
            
            results = collection.get(
                where={"$and": [
                    {"user_id": {"$eq": str(ctx.author.id)}},
                    {"timestamp": {"$gte": cutoff_date}}
                ]},
                limit=10
            )
            
            if not results or not results.get('documents'):
                await ctx.send(f"No conversations found in the past {days} days")
                return
            
            response = [f"**Your conversations from the past {days} days:**\n"]
            for i, (doc, meta) in enumerate(zip(results['documents'][:5], results['metadatas'][:5]), 1):
                timestamp = meta.get('timestamp', 'Unknown time')
                preview = doc[:200] + "..." if len(doc) > 200 else doc
                response.append(f"{i}. [{timestamp[:10]}] {preview}\n")
            
            message = "\n".join(response)
            if len(message) > 2000:
                message = message[:1997] + "..."
            await ctx.send(message)
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}", exc_info=True)
            await ctx.send("Failed to retrieve conversation history")
    
    @commands.command(name="vectordb_status", aliases=["vdb_status", "vdb"])
    async def vectordb_status(self, ctx):
        """Check the status of the vector database"""
        logger.info(f"vectordb_status command called by {ctx.author}")
        
        try:
            if not self.vector_enhancer.initialized:
                # Send simple text message instead of embed
                await ctx.send("❌ **Vector Database Status**\nVector database is not initialized.\nSemantic search and enhanced context features are disabled.")
                return
            
            # Get statistics
            stats = self.vector_enhancer.get_stats()
            
            # Build a simple text response instead of embed
            response = ["✅ **Vector Database Status**", "Vector database is active\n"]
            
            # Add embedding model info
            embedding_info = "Unknown"
            if hasattr(self.vector_enhancer.vector_db, 'embedding_function'):
                ef = self.vector_enhancer.vector_db.embedding_function
                if hasattr(ef, 'model_name'):
                    if hasattr(ef, 'url'):
                        embedding_info = f"Ollama: {ef.model_name}"
                    else:
                        embedding_info = f"SentenceTransformer: {ef.model_name}"
                else:
                    embedding_info = str(type(ef).__name__)
            
            response.append(f"**Embedding Model:** {embedding_info}")
            
            # Add collection stats
            response.append("\n**Collections:**")
            for collection_name, count in stats.items():
                if collection_name != "status":
                    name = collection_name.replace("_", " ").title()
                    response.append(f"• {name}: {count:,} entries")
            
            response.append("\n**Features:** Semantic search, Context awareness, Search caching")
            
            # Send as plain text message
            await ctx.send("\n".join(response))
            
        except Exception as e:
            logger.error(f"Error checking vector database status: {e}", exc_info=True)
            # Try the simplest possible response
            try:
                await ctx.send("Failed to check vector database status")
            except Exception as send_error:
                logger.error(f"Failed to send error message: {send_error}")
    
    @commands.command(name="vectordb_cleanup", aliases=["vdb_cleanup"])
    async def vectordb_cleanup(self, ctx, days: int = 30):
        """Clean up old vector database entries (Admin only)"""
        # Check if user is admin
        from ..config import config
        if ctx.author.id != config.AUTHORIZED_USER_ID:
            await ctx.send("❌ You don't have permission to use this command")
            return
        
        try:
            if not self.vector_enhancer.initialized:
                await ctx.send("Vector database is not initialized")
                return
            
            # Get stats before cleanup
            stats_before = self.vector_enhancer.get_stats()
            
            # Perform cleanup
            success = await self.vector_enhancer.cleanup_old_data(days=days)
            
            if success:
                # Get stats after cleanup
                stats_after = self.vector_enhancer.get_stats()
                
                embed = discord.Embed(
                    title="Vector Database Cleanup",
                    description=f"✅ Cleaned up entries older than {days} days",
                    color=discord.Color.green()
                )
                
                # Show changes
                for collection_name in stats_before:
                    if collection_name != "status":
                        before = stats_before.get(collection_name, 0)
                        after = stats_after.get(collection_name, 0)
                        removed = before - after
                        if removed > 0:
                            embed.add_field(
                                name=collection_name.replace("_", " ").title(),
                                value=f"Removed {removed:,} entries",
                                inline=True
                            )
                
                await ctx.send(embed=embed)
            else:
                await ctx.send("Failed to perform cleanup")
                
        except Exception as e:
            logger.error(f"Error during vector database cleanup: {e}")
            await ctx.send("Failed to clean up vector database")
    
    @commands.command(name="vectordb_search", aliases=["vdb_search"])
    async def vectordb_search(self, ctx, *, query: str):
        """Test semantic search functionality"""
        
        try:
            if not self.vector_enhancer.initialized:
                await ctx.send("Vector database is not initialized")
                return
            
            # Search conversations
            conv_results = await self.vector_enhancer.get_semantic_conversation_context(
                query=query,
                user_id=ctx.author.id,
                limit=3
            )
            
            # Search channel context
            channel_results = await self.vector_enhancer.get_semantic_channel_context(
                query=query,
                channel_id=ctx.channel.id,
                limit=3
            )
            
            # Build text response
            response = [f"🔍 **Semantic Search Results**", f"Query: **{query}**\n"]
            
            response.append("**Related Conversations:**")
            if conv_results:
                for r in conv_results[:3]:
                    response.append(f"• {r[:100]}...")
            else:
                response.append("No relevant conversations found")
            
            response.append("\n**Related Channel Messages:**")
            if channel_results:
                for r in channel_results[:3]:
                    response.append(f"• {r[:100]}...")
            else:
                response.append("No relevant channel messages found")
            
            # Send as text, limiting total length
            message = "\n".join(response)
            if len(message) > 2000:
                message = message[:1997] + "..."
            await ctx.send(message)
            
        except Exception as e:
            logger.error(f"Error during vector database search: {e}", exc_info=True)
            await ctx.send("Failed to perform semantic search")


async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(VectorDBCommands(bot))