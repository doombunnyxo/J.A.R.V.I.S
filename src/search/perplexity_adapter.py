"""
Perplexity adapter for the generalized search pipeline
"""

import aiohttp
from ..config import config

class PerplexitySearchProvider:
    """Adapter to make Perplexity work with the SearchProvider protocol"""
    
    def __init__(self):
        self.api_key = config.PERPLEXITY_API_KEY
        self.base_url = "https://api.perplexity.ai/chat/completions"
    
    async def optimize_query(self, query: str, context: str) -> str:
        """Use Perplexity to optimize the search query"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            system_prompt = """You are a search query optimizer. Transform the user's query into an effective Google search query that will return the most relevant current results.

Guidelines:
1. Convert conversational questions into search-friendly terms
2. Remove filler words like "can you", "please", "I want to know"
3. Include key terms that will find current information
4. Add year (2025) for time-sensitive or recent information queries
5. Keep queries focused but comprehensive (3-12 words optimal)
6. Use quotation marks for exact phrases when helpful
7. Include relevant keywords that improve search accuracy

Examples:
- "What's the best phone right now?" → "best smartphones 2025 reviews comparison"
- "How do I fix my wifi connection?" → "wifi connection troubleshooting fix guide"
- "Tell me about climate change" → "climate change 2025 latest research impacts"

Output only the optimized search query."""
            
            user_message = f"User query: {query}"
            if context:
                user_message = f"Context: {context}\n\n{user_message}"
            
            payload = {
                "model": "sonar",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "max_tokens": 100,
                "temperature": 0.1,
                "stream": False
            }
            
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(self.base_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        optimized = result["choices"][0]["message"]["content"].strip()
                        # Clean up the response
                        optimized = optimized.strip('"').strip()
                        
                        # Validate optimization - if too short or empty, use original
                        if len(optimized) < 2 or not optimized:
                            print(f"DEBUG: Perplexity optimization failed, using original query")
                            return query
                        
                        return optimized
                    else:
                        # Fallback to original query
                        print(f"DEBUG: Perplexity optimization API error, using original query")
                        return query
        except Exception as e:
            print(f"DEBUG: Perplexity optimization exception: {e}, using original query")
            return query
    
    async def analyze_results(self, query: str, search_results: str, context: str) -> str:
        """Use Perplexity to analyze search results"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        system_prompt = """You are a helpful search assistant. Analyze the provided search results and answer the user's query.

Guidelines:
- Provide comprehensive, accurate information based on the search results
- Cite sources when making specific claims
- Format your response for Discord with markdown
- If the search results don't contain relevant information, say so
- Be concise but thorough"""
        
        user_message = f"Query: {query}\n\n"
        if context:
            user_message += f"User Context: {context}\n\n"
        user_message += f"Search Results:\n{search_results}"
        
        payload = {
            "model": "sonar",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": 1000,
            "temperature": 0.2,
            "stream": False
        }
        
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(self.base_url, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    analysis = result["choices"][0]["message"]["content"]
                    return f"**Perplexity Sonar:** {analysis}"
                else:
                    error_text = await response.text()
                    raise Exception(f"Perplexity API error {response.status}: {error_text}")