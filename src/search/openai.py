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
        system_message = """You are a search assistant. Your task is to take a user's question or request and rewrite it into a concise, highly effective search engine query that would return the most relevant and accurate results.

Rules:
- Focus on **keywords** and important concepts only.
- Remove filler words, pronouns, or vague modifiers.
- If the request is vague, **infer the likely intent**.
- Don't use quotes, punctuation, or special operators unless necessary.
- Output ONLY the search query. No explanations."""

        # Build user message in the specified format
        if filtered_context and filtered_context.strip():
            user_message = f"""User request: {user_query}

Context: {filtered_context.strip()}

Search query:"""
        else:
            user_message = f"""User request: {user_query}

Search query:"""
        
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
        system_message = """You are an expert assistant. Using all the information provided below—including the user's query, previous context, and a large set of website content—generate a clear, concise, and comprehensive answer.

Instructions:
- Consider all the provided text carefully.
- Focus only on information relevant to the user's query.
- Integrate prior context to maintain continuity.
- Avoid repeating information.
- If conflicting information exists, note it briefly.
- Write the answer clearly and in a well-organized manner.
- Format the answer using Discord markdown:
  - Use **bold** for key points.
  - Use bullet points or numbered lists to organize information.
  - Use inline code blocks (`code`) for technical terms or code snippets.
  - Keep paragraphs short for readability.
- Keep the answer focused and as concise as possible given the input size.
- Optionally, limit your answer length to 1000 tokens."""

        # Build user message in the specified format
        context_section = filtered_context.strip() if filtered_context and filtered_context.strip() else "No previous context available."
        
        user_message = f"""User Query:
{user_query}

Previous Context:
{context_section}

Website Content:
{search_results}

Discord-formatted Answer:"""
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        # Set reasonable output token limits based on model
        max_tokens = 2048 if model == "gpt-4o" else 1024
        
        # Call OpenAI API
        response = await openai_client.create_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.2
        )
        
        print(f"DEBUG: OpenAI search analysis completed successfully")
        return response
        
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