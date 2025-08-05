"""
Centralized OpenAI client management
Provides a single interface for all OpenAI API interactions
"""

import asyncio
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from ..config import config
from ..utils.logging import get_logger

logger = get_logger(__name__)


class OpenAIClient:
    """Singleton OpenAI client with built-in error handling and retries"""
    
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None and config.has_openai_api():
            self._client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
    
    @property
    def client(self) -> AsyncOpenAI:
        """Get the OpenAI client instance"""
        if not self._client:
            if not config.has_openai_api():
                raise ValueError("OpenAI API key not configured")
            self._client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        return self._client
    
    async def create_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Create a chat completion with error handling and retries
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: OpenAI model to use
            max_tokens: Maximum tokens in response
            temperature: Response randomness (0-2)
            **kwargs: Additional OpenAI API parameters
            
        Returns:
            str: The AI's response text
            
        Raises:
            Exception: If API call fails after retries
        """
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
                
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"OpenAI API attempt {attempt + 1} failed: {e}. Retrying...")
                    await asyncio.sleep(retry_delay * (attempt + 1))
                else:
                    logger.error(f"OpenAI API failed after {max_retries} attempts: {e}")
                    raise
    
    async def create_streaming_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs
    ):
        """
        Create a streaming chat completion
        
        Args:
            messages: List of message dicts
            model: OpenAI model to use
            max_tokens: Maximum tokens
            temperature: Response randomness
            **kwargs: Additional parameters
            
        Yields:
            str: Chunks of the response as they arrive
        """
        try:
            stream = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                **kwargs
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"OpenAI streaming failed: {e}")
            raise


# Global client instance
openai_client = OpenAIClient()


# Convenience functions for backward compatibility
async def create_completion(
    messages: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    max_tokens: int = 500,
    temperature: float = 0.7,
    **kwargs
) -> str:
    """Convenience function for creating completions"""
    return await openai_client.create_completion(
        messages=messages,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        **kwargs
    )


async def test_openai_connection() -> bool:
    """Test if OpenAI API is working"""
    try:
        messages = [
            {"role": "system", "content": "You are a test assistant. Reply with exactly 'API test successful'."},
            {"role": "user", "content": "Test the API"}
        ]
        response = await create_completion(messages, max_tokens=50)
        return "API test successful" in response
    except Exception as e:
        logger.error(f"OpenAI API test failed: {e}")
        return False