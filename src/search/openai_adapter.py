"""
OpenAI adapter for the generalized search pipeline
"""

from .openai import openai_optimize_search_query, openai_search_analysis

class OpenAISearchProvider:
    """Adapter to make OpenAI work with the SearchProvider protocol"""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.model_name = self._get_model_display_name(model)
    
    def _get_model_display_name(self, model: str) -> str:
        """Get display name for the model"""
        model_names = {
            "gpt-4o-mini": "OpenAI GPT-4o Mini",
            "gpt-4o": "OpenAI GPT-4o", 
            "gpt-4-turbo": "OpenAI GPT-4 Turbo",
            "gpt-4": "OpenAI GPT-4",
            "mini": "OpenAI GPT-4o Mini",
            "4o": "OpenAI GPT-4o",
            "turbo": "OpenAI GPT-4 Turbo"
        }
        return model_names.get(model, "OpenAI GPT-4o Mini")
    
    async def optimize_query(self, query: str, context: str) -> str:
        """Use OpenAI to optimize the search query"""
        return await openai_optimize_search_query(query, context, self.model)
    
    async def analyze_results(self, query: str, search_results: str, context: str) -> str:
        """Use OpenAI to analyze search results"""
        # Use the model specified during initialization
        response = await openai_search_analysis(query, search_results, context, self.model)
        
        # Estimate total prompt tokens (context + system prompt + search results + user query)
        # Rough estimation: 4 characters per token
        context_tokens = len(context) // 4
        system_prompt_tokens = 200  # Estimated system prompt size
        search_results_tokens = len(search_results) // 4
        total_estimated_tokens = context_tokens + system_prompt_tokens + search_results_tokens
        
        # Prepend response type with model name and token count
        return f"**{self.model_name} Web Search** (~{total_estimated_tokens} tokens): {response}"