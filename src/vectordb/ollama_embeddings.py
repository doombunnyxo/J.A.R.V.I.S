"""
Ollama embedding function for Chroma vector database
Uses Nomic embeddings through Ollama
"""

import httpx
import json
from typing import List, Union, cast
from chromadb import EmbeddingFunction, Documents, Embeddings
from ..utils.logging import get_logger

logger = get_logger(__name__)


class OllamaEmbeddingFunction(EmbeddingFunction[Documents]):
    """
    Embedding function that uses Ollama with Nomic embeddings
    """
    
    def __init__(self, url: str = "http://localhost:11434", model_name: str = "nomic-embed-text"):
        """
        Initialize the Ollama embedding function
        
        Args:
            url: Ollama server URL
            model_name: Name of the embedding model to use
        """
        self.url = url.rstrip("/")
        self.model_name = model_name
        self._client = httpx.Client(timeout=30.0)
        
        # Test connection and pull model if needed
        self._ensure_model_available()
    
    def _ensure_model_available(self):
        """Ensure the embedding model is available in Ollama"""
        try:
            # Check if model exists
            response = self._client.post(
                f"{self.url}/api/show",
                json={"name": self.model_name}
            )
            
            if response.status_code == 404:
                logger.info(f"Model {self.model_name} not found, attempting to pull...")
                # Try to pull the model
                pull_response = self._client.post(
                    f"{self.url}/api/pull",
                    json={"name": self.model_name}
                )
                
                if pull_response.status_code == 200:
                    logger.info(f"Successfully pulled model {self.model_name}")
                else:
                    logger.warning(f"Failed to pull model {self.model_name}: {pull_response.status_code}")
            
            elif response.status_code == 200:
                logger.info(f"Model {self.model_name} is available")
            else:
                logger.warning(f"Unexpected response checking model: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Could not verify Ollama model availability: {e}")
    
    def __call__(self, input: Documents) -> Embeddings:
        """
        Generate embeddings for the given documents
        
        Args:
            input: List of document strings
            
        Returns:
            List of embeddings (list of floats for each document)
        """
        try:
            embeddings = []
            
            for doc in input:
                # Call Ollama embeddings API
                response = self._client.post(
                    f"{self.url}/api/embeddings",
                    json={
                        "model": self.model_name,
                        "prompt": doc
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    embedding = result.get("embedding", [])
                    if embedding:
                        embeddings.append(embedding)
                    else:
                        logger.warning(f"No embedding returned for document: {doc[:50]}...")
                        # Return zero vector as fallback
                        embeddings.append([0.0] * 768)  # Nomic embeddings are 768 dimensions
                else:
                    logger.error(f"Ollama embedding request failed: {response.status_code} - {response.text}")
                    # Return zero vector as fallback
                    embeddings.append([0.0] * 768)
            
            return cast(Embeddings, embeddings)
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            # Return zero vectors as fallback
            return cast(Embeddings, [[0.0] * 768 for _ in input])
    
    def __del__(self):
        """Clean up HTTP client"""
        try:
            self._client.close()
        except:
            pass


class OllamaEmbeddingFunctionAsync(EmbeddingFunction[Documents]):
    """
    Async version of Ollama embedding function
    """
    
    def __init__(self, url: str = "http://localhost:11434", model_name: str = "nomic-embed-text"):
        """
        Initialize the async Ollama embedding function
        
        Args:
            url: Ollama server URL
            model_name: Name of the embedding model to use
        """
        self.url = url.rstrip("/")
        self.model_name = model_name
    
    async def _get_embedding_async(self, text: str) -> List[float]:
        """Get embedding for a single text asynchronously"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.url}/api/embeddings",
                    json={
                        "model": self.model_name,
                        "prompt": text
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    embedding = result.get("embedding", [])
                    return embedding if embedding else [0.0] * 768
                else:
                    logger.error(f"Ollama embedding request failed: {response.status_code}")
                    return [0.0] * 768
                    
            except Exception as e:
                logger.error(f"Error getting embedding: {e}")
                return [0.0] * 768
    
    def __call__(self, input: Documents) -> Embeddings:
        """
        Generate embeddings for the given documents (sync interface for Chroma)
        """
        import asyncio
        
        async def get_all_embeddings():
            tasks = [self._get_embedding_async(doc) for doc in input]
            return await asyncio.gather(*tasks)
        
        try:
            # Run async operations in sync context
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're already in an async context, create a new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, get_all_embeddings())
                    embeddings = future.result()
            else:
                embeddings = loop.run_until_complete(get_all_embeddings())
            
            return cast(Embeddings, embeddings)
            
        except Exception as e:
            logger.error(f"Error in async embedding generation: {e}")
            return cast(Embeddings, [[0.0] * 768 for _ in input])