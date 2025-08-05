"""
OpenAI GPT-4o mini integration for search result processing
Replaces Claude for search query optimization and result analysis
"""

import asyncio
import aiohttp
import json
from typing import Optional
from ..config import config

class OpenAIAPI:
    """Async client for OpenAI API"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1/chat/completions"
        # Map model names to API model IDs
        model_map = {
            "gpt-4o-mini": "gpt-4o-mini",
            "gpt-4o": "gpt-4o", 
            "gpt-4-turbo": "gpt-4-turbo",
            "gpt-4": "gpt-4",
            "mini": "gpt-4o-mini",
            "4o": "gpt-4o",
            "turbo": "gpt-4-turbo"
        }
        self.model = model_map.get(model, "gpt-4o-mini")
        
    async def create_completion(self, messages: list, max_tokens: int = 1000, temperature: float = 0.2) -> str:
        """Create a completion using OpenAI API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(self.base_url, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    error_text = await response.text()
                    raise Exception(f"OpenAI API error {response.status}: {error_text}")

async def openai_optimize_search_query(user_query: str, filtered_context: str = "", model: str = "gpt-4o-mini") -> str:
    """
    Use OpenAI to optimize a search query for better Google Search results
    """
    if not config.has_openai_api():
        return user_query  # Fallback to original query
    
    try:
        # Create OpenAI client with specified model
        openai_client = OpenAIAPI(config.OPENAI_API_KEY, model)
        
        # Build system message for search query optimization
        system_message = """You are a search query optimizer. Your job is to transform user questions into optimized Google search queries that will return the most relevant and current results. The results will be processed and formatted for Discord chat.

INSTRUCTIONS:
1. Convert conversational questions into effective search terms
2. Remove unnecessary words like "can you", "please", "I want to know"
3. Focus on the core information being sought
4. Add relevant keywords that would improve search results
5. Keep queries concise but comprehensive
6. Use current year (2025) for time-sensitive queries
7. Return ONLY the optimized search query, nothing else
8. Prioritize sources that provide clear, factual information suitable for Discord formatting

EXAMPLES:
- "What's the weather like today?" → "weather today [current location]"
- "Can you tell me about the latest iPhone?" → "iPhone 2025 latest model specs features"
- "I want to know how to cook pasta" → "how to cook pasta recipe instructions"
- "What are the best laptops for gaming?" → "best gaming laptops 2025 reviews comparison"

USER CONTEXT (if provided):
Use this context to make the search query more specific and personalized."""

        # Add user context if provided
        context_info = ""
        if filtered_context and filtered_context.strip():
            context_info = f"\n\nUSER CONTEXT:\n{filtered_context.strip()}\n\nUse this context to make the search query more specific and personalized."
        
        # Build user message
        user_message = f"""Optimize this search query: {user_query}{context_info}"""
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        # Call OpenAI API with lower token limit for optimization
        response = await openai_client.create_completion(
            messages=messages,
            max_tokens=100,
            temperature=0.1
        )
        
        # Clean up the response
        optimized_query = response.strip().strip('"\'')
        
        print(f"DEBUG: OpenAI query optimization:")
        print(f"DEBUG: Original: '{user_query}'")
        print(f"DEBUG: Optimized: '{optimized_query}'")
        
        return optimized_query
        
    except Exception as e:
        print(f"DEBUG: OpenAI search query optimization failed: {e}")
        return user_query  # Fallback to original query

async def openai_search_analysis(user_query: str, search_results: str, filtered_context: str = "", model: str = "gpt-4o-mini") -> str:
    """
    Use OpenAI to analyze search results and provide a comprehensive answer
    """
    if not config.has_openai_api():
        return "OpenAI API not configured - cannot process search results"
    
    try:
        # Create OpenAI client with specified model
        openai_client = OpenAIAPI(config.OPENAI_API_KEY, model)
        
        # Build system message for search result analysis
        system_message = """[Role]
You are an AI assistant that analyzes web search results to provide comprehensive, accurate answers to user questions. You are responding in a Discord chat environment.

[Thinking Process]
First, consider the user's intent.  
Then, analyze the relevant context.  
Finally, respond with a clear answer.

[Analysis Instructions]
1. **Analyze the provided search results** thoroughly
2. **Extract the most relevant and current information** to answer the user's question
3. **Synthesize information** from multiple sources when helpful
4. **Provide specific details** like dates, numbers, names when available
5. **Cite sources** when possible (mention website names)
6. **Be concise but comprehensive** - aim for helpful, actionable answers
7. **If search results are insufficient**, acknowledge limitations
8. **Use user context** to personalize the response when relevant

[Discord Formatting]
- Use **bold** for emphasis (not numbered lists)
- Use simple bullet points with • instead of 1., 2., 3.
- Keep paragraphs short (2-3 sentences max)
- Use line breaks between different topics
- Avoid complex nested lists or numbering
- Use Discord markdown: **bold**, *italic*, `code`, ```code blocks```
- When listing items, use • or - for bullets, never numbers

[Response Structure]
- Lead with a direct answer to the user's question
- Support with relevant details from search results
- Use Discord-friendly formatting (bullets, bold, line breaks)
- End with source attribution when applicable
- Keep tone conversational and helpful

[Context Note]
The user context below has been filtered and summarized to include only information relevant to the current query. It includes pertinent conversation history, related channel discussions, and applicable user preferences."""

        # Add user context if provided (context already has its own headers)
        context_info = ""
        if filtered_context and filtered_context.strip():
            context_info = f"\n\n{filtered_context.strip()}"
        
        # Build user message with search results
        user_message = f"""USER QUESTION: {user_query}

SEARCH RESULTS:
{search_results}
{context_info}

Please analyze these search results and provide a comprehensive answer to the user's question."""
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        # Use much higher token limits for GPT-4o when processing full page content
        max_tokens = 80000 if model == "gpt-4o" else 4000
        
        # Call OpenAI API
        response = await openai_client.create_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.2
        )
        
        # Add prompt debug info for curiosity
        system_content = messages[0]["content"]
        user_content = messages[1]["content"]
        
        prompt_debug = f"""```
SYSTEM PROMPT:
{system_content}

USER MESSAGE:
{user_content}
```"""
        
        print(f"DEBUG: OpenAI search analysis completed successfully")
        return f"{prompt_debug}\n\n**Analysis:** {response}"
        
    except Exception as e:
        print(f"DEBUG: OpenAI search analysis failed: {e}")
        return f"Error analyzing search results with OpenAI: {str(e)}"

async def test_openai_api() -> bool:
    """Test if OpenAI API is working properly"""
    if not config.has_openai_api():
        return False
    
    try:
        openai_client = OpenAIAPI(config.OPENAI_API_KEY)
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Respond with exactly 'API test successful'."},
            {"role": "user", "content": "Test the API"}
        ]
        response = await openai_client.create_completion(
            messages=messages,
            max_tokens=50
        )
        return "API test successful" in response
    except Exception as e:
        print(f"DEBUG: OpenAI API test failed: {e}")
        return False