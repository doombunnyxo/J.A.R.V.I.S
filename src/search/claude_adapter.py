"""
Claude adapter for the generalized search pipeline
"""

from .claude import claude_optimize_search_query, claude_search_analysis

class ClaudeSearchProvider:
    """Adapter to make Claude work with the SearchProvider protocol"""
    
    def __init__(self, model: str = "haiku"):
        self.model = model
        self.model_name = self._get_model_display_name(model)
    
    def _get_model_display_name(self, model: str) -> str:
        """Get display name for the model"""
        model_names = {
            "haiku": "Claude Haiku",
            "sonnet": "Claude Sonnet", 
            "opus": "Claude Opus"
        }
        return model_names.get(model, "Claude")
    
    async def optimize_query(self, query: str, context: str) -> str:
        """Use Claude to optimize the search query"""
        return await claude_optimize_search_query(query, context)
    
    async def analyze_results(self, query: str, search_results: str, context: str) -> str:
        """Use Claude to analyze search results"""
        response = await claude_search_analysis(query, search_results, context)
        # Prepend model name to response
        return f"**{self.model_name}:** {response}"