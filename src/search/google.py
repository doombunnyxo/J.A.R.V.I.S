import discord
from discord.ext import commands
from googleapiclient.discovery import build
from ..config import config

class GoogleSearch(commands.Cog):
    """Google search functionality"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='search')
    async def search(self, ctx, *, query):
        """Search Google and return top 3 results"""
        try:
            if not config.has_google_search():
                await ctx.send('Google search is not configured. Please set GOOGLE_API_KEY and GOOGLE_SEARCH_ENGINE_ID.')
                return
            
            service = build("customsearch", "v1", developerKey=config.GOOGLE_API_KEY)
            result = service.cse().list(q=query, cx=config.GOOGLE_SEARCH_ENGINE_ID, num=3).execute()
            
            if 'items' not in result:
                await ctx.send('No search results found.')
                return
            
            embed = discord.Embed(title=f'Search results for: {query}', color=0x4285f4)
            
            for item in result['items'][:3]:
                title = item['title']
                link = item['link']
                snippet = item.get('snippet', 'No description available')
                
                embed.add_field(
                    name=title,
                    value=f'{snippet[:150]}...\n[Read more](<{link}>)',
                    inline=False
                )
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            await ctx.send(f'Search failed: {str(e)}')
    
    async def perform_search(self, message, query: str):
        """Perform search when mentioned with 'search:' prefix"""
        try:
            if not config.has_google_search():
                await message.channel.send('Google search is not configured.')
                return
            
            service = build("customsearch", "v1", developerKey=config.GOOGLE_API_KEY)
            result = service.cse().list(q=query, cx=config.GOOGLE_SEARCH_ENGINE_ID, num=3).execute()
            
            if 'items' not in result:
                await message.channel.send('No search results found.')
                return
            
            response = f"**Search results for: {query}**\n\n"
            
            for i, item in enumerate(result['items'][:3], 1):
                title = item['title']
                link = item['link']
                snippet = item.get('snippet', 'No description available')
                
                response += f"**{i}. {title}**\n{snippet[:200]}...\n<{link}>\n\n"
            
            await message.channel.send(response)
            
        except Exception as e:
            await message.channel.send(f'Search failed: {str(e)}')
    
    async def search_for_ai(self, query: str, num_results: int = 3) -> str:
        """Perform search and return results as text for AI processing"""
        try:
            if not config.has_google_search():
                return "Google search is not configured."
            
            service = build("customsearch", "v1", developerKey=config.GOOGLE_API_KEY)
            result = service.cse().list(q=query, cx=config.GOOGLE_SEARCH_ENGINE_ID, num=num_results).execute()
            
            if 'items' not in result:
                return f"No search results found for: {query}"
            
            search_results = f"Search results for '{query}':\n\n"
            
            for i, item in enumerate(result['items'][:num_results], 1):
                title = item['title']
                link = item['link']
                snippet = item.get('snippet', 'No description available')
                
                search_results += f"{i}. **{title}**\n"
                search_results += f"   {snippet[:300]}...\n"
                search_results += f"   Source: <{link}>\n\n"
            
            return search_results
            
        except Exception as e:
            return f"Search failed: {str(e)}"

async def setup(bot):
    await bot.add_cog(GoogleSearch(bot))