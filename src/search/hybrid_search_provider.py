"""
Hybrid search provider that uses Claude for query optimization and Perplexity for result analysis
This approach maximizes cost efficiency while maintaining high-quality responses
"""

from .claude_adapter import ClaudeSearchProvider
from .perplexity_adapter import PerplexitySearchProvider
from ..config import config

class HybridSearchProvider:
    """
    Hybrid search provider that combines the strengths of different AI providers:
    - Claude: Fast, cheap query optimization
    - Perplexity: High-quality result analysis and summarization
    """
    
    def __init__(self, claude_model: str = "haiku"):
        self.claude_provider = ClaudeSearchProvider(model=claude_model)
        self.perplexity_provider = PerplexitySearchProvider()
        self.display_name = f"Hybrid ({self.claude_provider.model_name} + Perplexity Sonar)"
    
    async def optimize_query(self, query: str, context: str) -> str:
        """Use Claude for fast, cost-effective query optimization"""
        if not config.has_anthropic_api():
            print("DEBUG: Claude not available for optimization, using original query")
            return query
        
        print(f"DEBUG: Using Claude {self.claude_provider.model} for query optimization")
        return await self.claude_provider.optimize_query(query, context)
    
    async def analyze_results(self, query: str, search_results: str, context: str) -> str:
        """Use Perplexity for high-quality result analysis and summarization"""
        if not config.has_perplexity_api():
            # Fallback to Claude if Perplexity not available
            print("DEBUG: Perplexity not available, falling back to Claude for analysis")
            if config.has_anthropic_api():
                claude_response = await self.claude_provider.analyze_results(query, search_results, context)
                return f"**{self.display_name} (Claude fallback):** {claude_response.replace('**Claude 3.5 Haiku:** ', '')}"
            else:
                return "❌ Neither Perplexity nor Claude available for result analysis"
        
        print(f"DEBUG: Using Perplexity Sonar for result analysis")
        perplexity_response = await self.perplexity_provider.analyze_results(query, search_results, context)
        
        # Remove the "Perplexity Sonar:" prefix and add our hybrid prefix
        clean_response = perplexity_response.replace("**Perplexity Sonar:** ", "")
        return f"**{self.display_name}:** {clean_response}"