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
    
    @commands.command(name="vectordb_status", aliases=["vdb_status", "vdb"])
    async def vectordb_status(self, ctx):
        """Check the status of the vector database"""
        
        try:
            if not self.vector_enhancer.initialized:
                embed = discord.Embed(
                    title="Vector Database Status",
                    description="❌ Vector database is not initialized",
                    color=discord.Color.red()
                )
                embed.add_field(
                    name="Impact",
                    value="Semantic search and enhanced context features are disabled",
                    inline=False
                )
                await ctx.send(embed=embed)
                return
            
            # Get statistics
            stats = self.vector_enhancer.get_stats()
            
            embed = discord.Embed(
                title="Vector Database Status",
                description="✅ Vector database is active",
                color=discord.Color.green()
            )
            
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
            
            embed.add_field(
                name="Embedding Model",
                value=embedding_info,
                inline=False
            )
            
            # Add collection stats
            for collection_name, count in stats.items():
                if collection_name != "status":
                    embed.add_field(
                        name=collection_name.replace("_", " ").title(),
                        value=f"{count:,} entries",
                        inline=True
                    )
            
            embed.add_field(
                name="Features Enabled",
                value="• Semantic conversation search\n• Context-aware responses\n• Search result caching\n• Enhanced context retrieval",
                inline=False
            )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error checking vector database status: {e}")
            await ctx.send("Failed to check vector database status")
    
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
            
            embed = discord.Embed(
                title="Semantic Search Results",
                description=f"Query: **{query}**",
                color=discord.Color.blue()
            )
            
            if conv_results:
                conv_text = "\n".join([f"• {r[:100]}..." for r in conv_results])
                embed.add_field(
                    name="Related Conversations",
                    value=conv_text[:1024],
                    inline=False
                )
            else:
                embed.add_field(
                    name="Related Conversations",
                    value="No relevant conversations found",
                    inline=False
                )
            
            if channel_results:
                channel_text = "\n".join([f"• {r[:100]}..." for r in channel_results])
                embed.add_field(
                    name="Related Channel Messages",
                    value=channel_text[:1024],
                    inline=False
                )
            else:
                embed.add_field(
                    name="Related Channel Messages",
                    value="No relevant channel messages found",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error during vector database search: {e}")
            await ctx.send("Failed to perform semantic search")


async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(VectorDBCommands(bot))