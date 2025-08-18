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
    
    async def analyze_results(self, query: str, search_results: str, context: str, channel=None) -> str:
        """Analyze search results and provide a response"""
        ...

class SearchPipeline:
    """Generalized search pipeline that works with any provider"""
    
    def __init__(self, provider: SearchProvider, enable_full_extraction: bool = False, debug_channel=None):
        self.provider = provider
        self.enable_full_extraction = enable_full_extraction
        self.debug_channel = debug_channel
    
    async def search_and_respond(self, query: str, context: str = "", channel=None) -> str:
        """
        Execute the full search pipeline:
        1. Check if context can answer the query
        2. If not, optimize the query using the AI provider
        3. Perform Google search
        4. Analyze results using the AI provider
        
        Args:
            query: User's search query
            context: User context for personalization
            
        Returns:
            AI-generated response based on search results
        """
            
        try:
            import time
            start_time = time.time()
            
            # First, check if we can answer from context alone
            context_response = await self._check_context_for_answer(query, context, channel)
            if context_response:
                return context_response
            
            # Simple approach: Optimize query first, then search
            context_size = len(context) if context else 0
            
            # Optimize the query
            opt_start = time.time()
            optimized_query = await self.provider.optimize_query(query, context)
            opt_time = time.time() - opt_start
            
            # Perform search with optimized query
            search_start = time.time()
            search_results = await self._perform_google_search(optimized_query, self.enable_full_extraction, context_size, channel)
            search_time = time.time() - search_start
            
            if not search_results or "Search failed" in search_results:
                return f"Web search unavailable: {search_results}"
            
            # Step 3: Analyze results with context
            analysis_start = time.time()
            response = await self.provider.analyze_results(query, search_results, context, channel)
            analysis_time = time.time() - analysis_start
            
            total_time = time.time() - start_time
            
            # Store search results in vector database (background task - don't block response)
            asyncio.create_task(self._store_search_result_async(query, optimized_query, response, channel))
            
            # Step 4: Update blacklist immediately after getting response
            if hasattr(self, '_tracking_data') and self._tracking_data:
                await self._update_blacklist_sync(self._tracking_data)
            
            return response
            
        except Exception as e:
            provider_name = self.provider.__class__.__name__
            return f"Error in {provider_name} search pipeline: {str(e)}"
    
    async def _check_context_for_answer(self, query: str, context: str, channel=None) -> Optional[str]:
        """
        Check if the query can be answered from the Discord channel conversation history
        before performing a web search. This saves API calls and provides faster responses
        when information was recently discussed in the channel.
        
        Args:
            query: User's search query
            context: The context including recent channel messages
            channel: Discord channel object
            
        Returns:
            Response string if channel history has the answer, None otherwise
        """
        try:
            # Skip if context is empty or too short (not enough conversation history)
            if not context or len(context.strip()) < 200:
                return None
            
            # Use OpenAI to analyze if the channel history contains the answer
            from ..ai.openai_client import get_openai_client
            from ..config import config
            
            if not config.has_openai_api():
                return None
            
            openai_client = get_openai_client()
            
            # Build prompt to check if channel history has the answer
            system_message = """You are analyzing a Discord channel's conversation history to see if it contains information that answers a user's question.

Review the recent channel messages and the user's question. If the conversation history contains relevant information that directly answers the question, respond with "ANSWER: " followed by a clear answer based on what was discussed.

If the channel history doesn't contain the information needed, or if the question requires current web information not in the chat, respond with "NEEDS_SEARCH".

Guidelines:
- Only answer if the information was explicitly discussed in the channel
- Reference who said what when relevant (e.g., "As mentioned by UserX earlier...")
- For questions about current events, prices, news, or external information not discussed in chat, respond "NEEDS_SEARCH"
- For questions about the ongoing conversation or recent discussions, provide the answer from context"""
            
            user_message = f"""User's Question: {query}

Recent Channel Conversation:
{context}

Decision:"""
            
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
            
            # Use GPT-4o mini for quick context analysis
            response = await openai_client.create_completion(
                messages=messages,
                model="gpt-4o-mini",
                max_tokens=500,
                temperature=0.1
            )
            
            # Check if channel history had the answer
            if response.startswith("ANSWER:"):
                answer = response[7:].strip()
                # Indicate this came from channel context, not web search
                return f"**OpenAI GPT-4o Mini (from channel context)**: {answer}"
            
            # Channel doesn't have the answer, proceed with Google web search
            return None
            
        except Exception as e:
            # On error, continue with web search
            return None
    
    async def _update_blacklist_sync(self, tracking_data: dict):
        """Update blacklist synchronously after search completion"""
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
                
        except Exception as e:
            pass  # Don't crash anything
    
    async def _perform_google_search(self, query: str, enable_full_extraction: bool = False, context_size: int = 0, channel=None) -> str:
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
                    
                    extractor = WebContentExtractor()
                    extracted_pages, tracking_data = await extractor.extract_multiple_pages(urls, channel)
                    
                    # Store tracking data for later blacklist updates
                    self._tracking_data = tracking_data
                    
                    # Build enhanced search results with full content
                    search_results = f"Web search results for '{query}':\n\n"
                    extracted_by_url = {page['url']: page for page in extracted_pages}
                    
                except Exception as e:
                    error_msg = f"Full page extraction failed: {str(e)}"
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
                    search_results += f"   Source: {link}\n\n"
            
            return search_results
        
        except Exception as e:
            return f"Search failed: {str(e)}"
    
    async def _store_search_result_async(self, query: str, optimized_query: str, response: str, channel):
        """Store search results in vector database asynchronously (background task)"""
        try:
            from ..vectordb.context_enhancer import vector_enhancer
            if vector_enhancer and vector_enhancer.initialized:
                # Extract user_id and channel_id from channel object if available
                user_id = None
                channel_id = None
                if channel:
                    channel_id = channel.id
                    # Try to get user_id from the last message in the channel
                    try:
                        async for msg in channel.history(limit=1):
                            if msg.author:
                                user_id = msg.author.id
                                break
                    except:
                        pass
                
                # Store the search result
                await vector_enhancer.vector_db.add_search_result(
                    query=query,
                    result=f"Optimized: {optimized_query}\n\nResponse: {response}",
                    source="google_search",
                    user_id=user_id,
                    channel_id=channel_id
                )
        except Exception as e:
            # Silently fail - vector DB is optional for search functionality
            from ..utils.logging import get_logger
            logger = get_logger(__name__)
            logger.debug(f"Failed to store search result in vector DB: {e}")