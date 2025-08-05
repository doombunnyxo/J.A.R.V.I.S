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
    
    def __init__(self, provider: SearchProvider, enable_full_extraction: bool = False, debug_channel=None):
        self.provider = provider
        self.enable_full_extraction = enable_full_extraction
        self.debug_channel = debug_channel
    
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
            search_results = await self._perform_google_search(optimized_query, self.enable_full_extraction)
            
            if not search_results or "Search failed" in search_results:
                return f"Web search unavailable: {search_results}"
            
            # Step 3: Analyze results with context
            print(f"DEBUG: Analyzing results with {self.provider.__class__.__name__}")
            response = await self.provider.analyze_results(query, search_results, context)
            
            return response
            
        except Exception as e:
            provider_name = self.provider.__class__.__name__
            return f"Error in {provider_name} search pipeline: {str(e)}"
    
    async def _perform_google_search(self, query: str, enable_full_extraction: bool = False) -> str:
        """Perform Google search with optional full page content extraction"""
        try:
            if not config.has_google_search():
                return "Google search not configured"
            
            # Add domain exclusions to search query
            from .domain_filter import get_domain_filter
            domain_filter = get_domain_filter()
            
            # Build exclusion string for blocked domains
            blocked_domains = [domain for domain in domain_filter.blocked_domains.keys()]
            exclusion_string = " ".join([f"-site:{domain}" for domain in blocked_domains])
            
            # Append exclusions to query
            enhanced_query = f"{query} {exclusion_string}".strip()
            
            
            # Import here to avoid circular imports
            from googleapiclient.discovery import build
            
            service = build("customsearch", "v1", developerKey=config.GOOGLE_API_KEY)
            result = service.cse().list(q=enhanced_query, cx=config.GOOGLE_SEARCH_ENGINE_ID, num=5).execute()
            
            if 'items' not in result:
                return f"No search results found for: {query}"
            
            basic_results = []
            for i, item in enumerate(result['items'][:5], 1):
                title = item['title']
                link = item['link']
                snippet = item.get('snippet', 'No description available')
                
                basic_results.append({
                    'title': title,
                    'link': link,
                    'snippet': snippet,
                    'index': i
                })
            
            if enable_full_extraction:
                # Full page extraction mode
                try:
                    from .web_extractor import WebContentExtractor
                    
                    urls = [result['link'] for result in basic_results]
                    print(f"DEBUG: Extracting full content from {len(urls)} pages...")
                    
                    extractor = WebContentExtractor()
                    extracted_pages = await extractor.extract_multiple_pages(urls)
                    print(f"DEBUG: Successfully extracted {len(extracted_pages)} pages")
                    
                    # Build enhanced search results with full content
                    search_results = f"Full page web search results for '{query}':\n\n"
                    extracted_by_url = {page['url']: page for page in extracted_pages}
                    
                except Exception as e:
                    error_msg = f"Full page extraction failed: {str(e)}"
                    print(f"DEBUG: {error_msg}")
                    # Fall back to snippet mode and include error info
                    search_results = f"⚠️ **Full extraction failed**: {str(e)}\n\nFalling back to snippet search for '{query}':\n\n"
                    enable_full_extraction = False
            
            if enable_full_extraction:
                # Continue with full extraction processing
                for basic_result in basic_results:
                    link = basic_result['link']
                    title = basic_result['title']
                    snippet = basic_result['snippet']
                    index = basic_result['index']
                    
                    search_results += f"{index}. **{title}**\n"
                    search_results += f"   Snippet: {snippet}\n"
                    
                    if link in extracted_by_url:
                        # Add full extracted content after snippet
                        page_data = extracted_by_url[link]
                        search_results += f"   Full Content ({page_data['length']} chars): {page_data['content']}\n"
                    else:
                        # Note extraction failure
                        search_results += f"   (Full content extraction failed)\n"
                    
                    search_results += f"   Source: <{link}>\n\n"
            else:
                # Snippet-only mode
                search_results = f"Web search results for '{query}':\n\n"
                
                for basic_result in basic_results:
                    title = basic_result['title']
                    link = basic_result['link']
                    snippet = basic_result['snippet']
                    index = basic_result['index']
                    
                    search_results += f"{index}. **{title}**\n"
                    search_results += f"   {snippet[:400]}...\n"
                    search_results += f"   Source: <{link}>\n\n"
            
            return search_results
        
        except Exception as e:
            return f"Search failed: {str(e)}"