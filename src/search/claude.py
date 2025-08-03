"""
Claude 3.5 Haiku integration for search result processing
Replaces Perplexity for more cost-effective text summarization
"""

import asyncio
import aiohttp
import json
from typing import Optional
from ..config import config

class AnthropicAPI:
    """Async client for Anthropic Claude API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.model = "claude-3-5-haiku-20241022"
        
    async def create_message(self, system_message: str, user_message: str, max_tokens: int = 1000) -> str:
        """Create a message using Claude 3.5 Haiku"""
        headers = {
            "x-api-key": self.api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system_message,
            "messages": [
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        }
        
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(self.base_url, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["content"][0]["text"]
                else:
                    error_text = await response.text()
                    raise Exception(f"Claude API error {response.status}: {error_text}")

async def claude_search_analysis(user_query: str, search_results: str, filtered_context: str = "") -> str:
    """
    Use Claude 3.5 Haiku to analyze search results and provide a comprehensive answer
    Replaces Perplexity for more cost-effective processing
    """
    if not config.has_anthropic_api():
        return "Claude API not configured - cannot process search results"
    
    try:
        # Create Claude client
        claude = AnthropicAPI(config.ANTHROPIC_API_KEY)
        
        # Build system message for search result analysis
        system_message = """You are an AI assistant that analyzes web search results to provide comprehensive, accurate answers to user questions.

INSTRUCTIONS:
1. **Analyze the provided search results** thoroughly
2. **Extract the most relevant and current information** to answer the user's question
3. **Synthesize information** from multiple sources when helpful
4. **Provide specific details** like dates, numbers, names when available
5. **Cite sources** when possible (mention website names)
6. **Be concise but comprehensive** - aim for helpful, actionable answers
7. **If search results are insufficient**, acknowledge limitations
8. **Use user context** to personalize the response when relevant

RESPONSE FORMAT:
- Lead with a direct answer to the user's question
- Support with relevant details from search results
- End with source attribution when applicable
- Keep tone conversational and helpful

USER CONTEXT (if provided):
Use this context to make your response more personalized and relevant to the user's situation and interests."""

        # Add user context if provided
        context_info = ""
        if filtered_context and filtered_context.strip():
            context_info = f"\n\nUSER CONTEXT:\n{filtered_context.strip()}"
        
        # Build user message with search results
        user_message = f"""USER QUESTION: {user_query}

SEARCH RESULTS:
{search_results}
{context_info}

Please analyze these search results and provide a comprehensive answer to the user's question."""
        
        # Call Claude API
        response = await claude.create_message(
            system_message=system_message,
            user_message=user_message,
            max_tokens=1000
        )
        
        print(f"DEBUG: Claude search analysis completed successfully")
        return response
        
    except Exception as e:
        print(f"DEBUG: Claude search analysis failed: {e}")
        return f"Error analyzing search results with Claude: {str(e)}"

async def test_claude_api() -> bool:
    """Test if Claude API is working properly"""
    if not config.has_anthropic_api():
        return False
    
    try:
        claude = AnthropicAPI(config.ANTHROPIC_API_KEY)
        response = await claude.create_message(
            system_message="You are a helpful assistant. Respond with exactly 'API test successful'.",
            user_message="Test the API",
            max_tokens=50
        )
        return "API test successful" in response
    except Exception as e:
        print(f"DEBUG: Claude API test failed: {e}")
        return False