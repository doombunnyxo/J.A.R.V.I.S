"""
Hybrid search provider that uses OpenAI for query optimization and Perplexity for result analysis
This approach maximizes cost efficiency while maintaining high-quality responses
"""

from .openai_adapter import OpenAISearchProvider
from .perplexity_adapter import PerplexitySearchProvider
from ..config import config

class HybridSearchProvider:
    """
    Hybrid search provider that combines the strengths of different AI providers:
    - OpenAI: Fast, reliable query optimization
    - Perplexity: High-quality result analysis and summarization
    """
    
    def __init__(self, openai_model: str = "gpt-4o-mini"):
        self.openai_provider = OpenAISearchProvider(model=openai_model)
        self.perplexity_provider = PerplexitySearchProvider()
        self.display_name = f"Hybrid ({self.openai_provider.model_name} + Perplexity Sonar)"
    
    async def optimize_query(self, query: str, context: str) -> str:
        """Use OpenAI for fast, reliable query optimization"""
        if not config.has_openai_api():
            print("DEBUG: OpenAI not available for optimization, using original query")
            return query
        
        print(f"DEBUG: Using OpenAI {self.openai_provider.model} for query optimization")
        return await self.openai_provider.optimize_query(query, context)
    
    async def analyze_results(self, query: str, search_results: str, context: str) -> str:
        """Use Perplexity for high-quality result analysis and summarization"""
        if not config.has_perplexity_api():
            # Fallback to OpenAI if Perplexity not available
            print("DEBUG: Perplexity not available, falling back to OpenAI for analysis")
            if config.has_openai_api():
                openai_response = await self.openai_provider.analyze_results(query, search_results, context)
                return f"**{self.display_name} (OpenAI fallback):** {openai_response.replace(f'**{self.openai_provider.model_name}:** ', '')}"
            else:
                return "❌ Neither Perplexity nor OpenAI available for result analysis"
        
        print(f"DEBUG: Using Perplexity Sonar for result analysis")
        perplexity_response = await self.perplexity_provider.analyze_results(query, search_results, context)
        
        # Remove the "Perplexity Sonar:" prefix and add our hybrid prefix
        clean_response = perplexity_response.replace("**Perplexity Sonar:** ", "")
        return f"**{self.display_name}:** {clean_response}"