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
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        system_prompt = """You are a search query optimizer. Your task is to transform the user's query into an effective Google search query.

Rules:
1. Keep it concise (2-6 words ideal)
2. Include key terms that will find current information
3. Add year if asking about recent/current information
4. Remove unnecessary words
5. Use quotation marks for exact phrases if needed

Just output the optimized search query, nothing else."""
        
        user_message = f"User query: {query}"
        if context:
            user_message = f"Context: {context}\n\n{user_message}"
        
        payload = {
            "model": "sonar-small",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": 50,
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
                    return optimized
                else:
                    # Fallback to original query
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
            "model": "sonar-medium",
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