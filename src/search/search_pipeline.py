"""
Generalized search pipeline for AI providers
Provides a common flow: optimize query → Google search → analyze results
"""

import asyncio
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
            # Parallel approach: Start query optimization and fallback search simultaneously
            print(f"DEBUG: Starting parallel query optimization and fallback search")
            context_size = len(context) if context else 0
            
            optimization_task = asyncio.create_task(
                self.provider.optimize_query(query, context)
            )
            fallback_search_task = asyncio.create_task(
                self._perform_google_search(query, self.enable_full_extraction, context_size)
            )
            
            try:
                # Wait for optimization with aggressive timeout
                optimized_query = await asyncio.wait_for(optimization_task, timeout=2.0)
                print(f"DEBUG: Query optimization completed: {optimized_query}")
                
                # Cancel fallback and use optimized query
                fallback_search_task.cancel()
                print(f"DEBUG: Performing Google search for optimized query: {optimized_query}")
                search_results = await self._perform_google_search(optimized_query, self.enable_full_extraction, context_size)
                
            except asyncio.TimeoutError:
                # Use fallback results if optimization is slow
                print(f"DEBUG: Query optimization timed out, using fallback search results")
                search_results = await fallback_search_task
            
            if not search_results or "Search failed" in search_results:
                return f"Web search unavailable: {search_results}"
            
            # Step 3: Analyze results with context
            print(f"DEBUG: Analyzing results with {self.provider.__class__.__name__}")
            response = await self.provider.analyze_results(query, search_results, context)
            
            # Step 4: Fire-and-forget blacklist updates AFTER getting response
            if hasattr(self, '_tracking_data') and self._tracking_data:
                # Don't await - let it run in background without blocking the response
                asyncio.create_task(self._update_blacklist_async(self._tracking_data))
            
            return response
            
        except Exception as e:
            provider_name = self.provider.__class__.__name__
            return f"Error in {provider_name} search pipeline: {str(e)}"
    
    async def _update_blacklist_async(self, tracking_data: dict):
        """Update blacklist in background after search completion"""
        try:
            from .domain_filter import get_domain_filter
            domain_filter = get_domain_filter()
            
            failed_sites = tracking_data.get('failed_sites', [])
            slow_sites = tracking_data.get('slow_sites', [])
            
            # Process failed sites
            for url, error in failed_sites:
                if url != 'unknown':
                    await domain_filter.record_failure(url, error)
            
            # Process slow sites
            for url, response_time in slow_sites:
                await domain_filter.record_slow_site(url, response_time)
                
            if failed_sites or slow_sites:
                print(f"DEBUG: Background blacklist update - {len(failed_sites)} failures, {len(slow_sites)} slow sites")
                
        except Exception as e:
            print(f"DEBUG: Background blacklist update failed: {e}")  # Don't crash anything
    
    async def _perform_google_search(self, query: str, enable_full_extraction: bool = False, context_size: int = 0) -> str:
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
            result = service.cse().list(q=enhanced_query, cx=config.GOOGLE_SEARCH_ENGINE_ID, num=10).execute()
            
            if 'items' not in result:
                return f"No search results found for: {query}"
            
            basic_results = []
            for i, item in enumerate(result['items'][:10], 1):
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
                    extracted_pages, tracking_data = await extractor.extract_multiple_pages(urls)
                    print(f"DEBUG: Successfully extracted {len(extracted_pages)} pages")
                    
                    # Store tracking data for later blacklist updates
                    self._tracking_data = tracking_data
                    
                    # Build enhanced search results with full content
                    search_results = f"Web search results for '{query}':\n\n"
                    extracted_by_url = {page['url']: page for page in extracted_pages}
                    
                except Exception as e:
                    error_msg = f"Full page extraction failed: {str(e)}"
                    print(f"DEBUG: {error_msg}")
                    # Fall back to snippet mode and include error info
                    search_results = f"⚠️ **Full extraction failed**: {str(e)}\n\nFalling back to snippet search for '{query}':\n\n"
                    enable_full_extraction = False
            
            if enable_full_extraction:
                # Build search results with dynamic token estimation
                # Estimate initial tokens: query + context + system prompt
                estimated_tokens = len(query) // 4  # Query tokens
                estimated_tokens += 500  # System prompt estimate (~2000 chars)
                estimated_tokens += context_size // 4  # Context tokens
                
                # Token limit with safety margin
                token_limit = 28000
                
                for basic_result in basic_results:
                    link = basic_result['link']
                    title = basic_result['title']
                    snippet = basic_result['snippet']
                    index = basic_result['index']
                    
                    # Build this result's content
                    result_content = f"{index}. **{title}**\n"
                    result_content += f"   Snippet: {snippet}\n"
                    
                    if link in extracted_by_url:
                        # Add full extracted content after snippet
                        page_data = extracted_by_url[link]
                        result_content += f"   Full Content ({page_data['length']} chars): {page_data['content']}\n"
                    else:
                        # Note extraction failure
                        result_content += f"   (Full content extraction failed)\n"
                    
                    result_content += f"   Source: {link}\n\n"
                    
                    # Estimate tokens for this result (roughly 4 chars per token)
                    result_tokens = len(result_content) // 4
                    
                    # Check if adding this result would exceed limit
                    if estimated_tokens + result_tokens > token_limit:
                        print(f"DEBUG: Stopping at {index-1} results to stay under token limit. Current: {estimated_tokens}, Would add: {result_tokens}")
                        search_results += f"\n(Limited to {index-1} results to stay within token limits)\n"
                        break
                    
                    # Add the result
                    search_results += result_content
                    estimated_tokens += result_tokens
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