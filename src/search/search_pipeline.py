"""
Generalized search pipeline for AI providers
Provides a common flow: optimize query → Google search → analyze results
"""

from typing import Optional, Protocol, runtime_checkable
from ..config import config
from .google import perform_google_search

@runtime_checkable
class SearchProvider(Protocol):
    """Protocol for search providers that can optimize queries and analyze results"""
    
    async def optimize_query(self, query: str, context: str) -> str:
        """Optimize the search query based on context"""
        ...
    
    async def analyze_results(self, query: str, search_results: str, context: str) -> str:
        """Analyze search results and provide a response"""
        ...

class SearchPipeline:
    """Generalized search pipeline that works with any provider"""
    
    def __init__(self, provider: SearchProvider):
        self.provider = provider
    
    async def search_and_respond(self, query: str, context: str = "") -> str:
        """
        Execute the full search pipeline:
        1. Optimize the query using the AI provider
        2. Perform Google search
        3. Analyze results using the AI provider
        
        Args:
            query: User's search query
            context: User context for personalization
            
        Returns:
            AI-generated response based on search results
        """
        try:
            # Step 1: Optimize the search query
            print(f"DEBUG: Optimizing query with {self.provider.__class__.__name__}")
            optimized_query = await self.provider.optimize_query(query, context)
            print(f"DEBUG: Optimized query: {optimized_query}")
            
            # Step 2: Perform Google search
            print(f"DEBUG: Performing Google search for: {optimized_query}")
            search_results = await self._perform_google_search(optimized_query)
            
            if not search_results or "Search failed" in search_results:
                return f"Web search unavailable: {search_results}"
            
            # Step 3: Analyze results with context
            print(f"DEBUG: Analyzing results with {self.provider.__class__.__name__}")
            response = await self.provider.analyze_results(query, search_results, context)
            
            return response
            
        except Exception as e:
            provider_name = self.provider.__class__.__name__
            return f"Error in {provider_name} search pipeline: {str(e)}"
    
    async def _perform_google_search(self, query: str) -> str:
        """Perform Google search"""
        try:
            if not config.has_google_search():
                return "Google search not configured"
            
            # Import here to avoid circular imports
            from googleapiclient.discovery import build
            
            service = build("customsearch", "v1", developerKey=config.GOOGLE_API_KEY)
            result = service.cse().list(q=query, cx=config.GOOGLE_SEARCH_ENGINE_ID, num=10).execute()
            
            if 'items' not in result:
                return f"No search results found for: {query}"
            
            search_results = f"Current web search results for '{query}':\n\n"
            
            for i, item in enumerate(result['items'][:10], 1):
                title = item['title']
                link = item['link']
                snippet = item.get('snippet', 'No description available')
                
                search_results += f"{i}. **{title}**\n"
                search_results += f"   {snippet[:400]}...\n"
                search_results += f"   Source: <{link}>\n\n"
            
            return search_results
        
        except Exception as e:
            return f"Search failed: {str(e)}"