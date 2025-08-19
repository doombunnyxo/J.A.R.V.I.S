"""
Enhanced context management using Chroma vector database
Integrates with existing ContextManager to provide semantic search capabilities
"""

from typing import List, Dict, Optional, Tuple
from ..utils.logging import get_logger

logger = get_logger(__name__)
logger.info("=== VectorDB context_enhancer module loading ===")

try:
    from .chroma_client import vector_db
    logger.info("ChromaDB client imported successfully")
except ImportError as e:
    logger.error(f"Failed to import ChromaDB client: {e}")
    vector_db = None
except Exception as e:
    logger.error(f"Unexpected error importing ChromaDB client: {e}")
    vector_db = None


class VectorContextEnhancer:
    """Enhances context management with vector database capabilities"""
    
    def __init__(self):
        self.vector_db = vector_db
        self.initialized = False
        
    async def initialize(self) -> bool:
        """
        Initialize the vector database
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.initialized = self.vector_db.initialize()
            if self.initialized:
                logger.info("Vector context enhancer initialized successfully")
            else:
                logger.warning("Vector context enhancer running in degraded mode")
            return self.initialized
        except Exception as e:
            logger.error(f"Failed to initialize vector context enhancer: {e}")
            self.initialized = False
            return False
    
    async def store_conversation(self, user_id: int, channel_id: int, 
                                message: str, response: str, 
                                user_name: Optional[str] = None) -> bool:
        """
        Store conversation in vector database for semantic retrieval
        
        Args:
            user_id: Discord user ID
            channel_id: Discord channel ID
            message: User's message
            response: Bot's response
            user_name: Optional user name for metadata
            
        Returns:
            True if stored successfully
        """
        if not self.initialized:
            return False
            
        metadata = {}
        if user_name:
            metadata['user_name'] = user_name
            
        return self.vector_db.add_conversation(
            user_id=user_id,
            channel_id=channel_id,
            message=message,
            response=response,
            metadata=metadata
        )
    
    async def store_channel_message(self, channel_id: int, user_name: str, 
                                   message: str, message_id: Optional[int] = None) -> bool:
        """
        Store channel message in vector database
        
        Args:
            channel_id: Discord channel ID
            user_name: Name of message author
            message: Message content
            message_id: Optional Discord message ID
            
        Returns:
            True if stored successfully
        """
        if not self.initialized:
            return False
            
        return self.vector_db.add_channel_message(
            channel_id=channel_id,
            user_name=user_name,
            message=message,
            message_id=message_id
        )
    
    async def get_semantic_conversation_context(self, query: str, user_id: int, 
                                               channel_id: Optional[int] = None,
                                               limit: int = 5) -> List[str]:
        """
        Get semantically relevant conversation history
        
        Args:
            query: Current user query
            user_id: Discord user ID
            channel_id: Optional channel ID filter
            limit: Maximum number of results
            
        Returns:
            List of relevant conversation snippets
        """
        if not self.initialized:
            return []
            
        results = self.vector_db.search_conversations(
            query=query,
            user_id=user_id,
            channel_id=channel_id,
            limit=limit
        )
        
        # Format results for context
        context_items = []
        for result in results:
            if result['distance'] < 0.7:  # Similarity threshold
                context_items.append(result['document'])
        
        return context_items
    
    async def get_semantic_channel_context(self, query: str, channel_id: int,
                                          limit: int = 10) -> List[str]:
        """
        Get semantically relevant channel messages
        
        Args:
            query: Current user query
            channel_id: Discord channel ID
            limit: Maximum number of results
            
        Returns:
            List of relevant channel messages
        """
        if not self.initialized:
            return []
            
        results = self.vector_db.search_channel_context(
            query=query,
            channel_id=channel_id,
            limit=limit
        )
        
        # Format results
        messages = []
        for result in results:
            if result['distance'] < 0.8:  # Slightly higher threshold for channel messages
                messages.append(result['document'])
        
        return messages
    
    
    async def enhance_context_with_semantic_search(self, query: str, user_id: int,
                                                  channel_id: int, 
                                                  existing_context: str) -> str:
        """
        Enhance existing context with semantically relevant information
        
        Args:
            query: Current user query
            user_id: Discord user ID
            channel_id: Discord channel ID
            existing_context: Already gathered context
            
        Returns:
            Enhanced context string
        """
        if not self.initialized:
            return existing_context
            
        try:
            enhanced_parts = [existing_context] if existing_context else []
            
            # Add semantic conversation history
            conv_context = await self.get_semantic_conversation_context(
                query=query,
                user_id=user_id,
                channel_id=channel_id,
                limit=3
            )
            if conv_context:
                enhanced_parts.append("[Relevant Previous Conversations]")
                enhanced_parts.extend(conv_context)
            
            # Add semantic channel context
            channel_context = await self.get_semantic_channel_context(
                query=query,
                channel_id=channel_id,
                limit=5
            )
            if channel_context:
                enhanced_parts.append("[Relevant Channel Discussion]")
                enhanced_parts.extend(channel_context)
            
            # Note: Permanent context is now handled separately from JSON files
            # and passed raw without semantic filtering
            
            return "\n\n".join(enhanced_parts)
            
        except Exception as e:
            logger.error(f"Failed to enhance context with semantic search: {e}")
            return existing_context
    
    async def check_search_cache(self, query: str) -> Optional[str]:
        """
        Check if we have a cached result for this search query
        
        Args:
            query: Search query
            
        Returns:
            Cached result if available and recent, None otherwise
        """
        if not self.initialized:
            return None
            
        return self.vector_db.get_cached_search(query, max_age_hours=24)
    
    async def cache_search_result(self, query: str, result: str, source: str = "web") -> bool:
        """
        Cache a search result for future use
        
        Args:
            query: The search query
            result: The search result
            source: Source of the result
            
        Returns:
            True if cached successfully
        """
        if not self.initialized:
            return False
            
        return self.vector_db.cache_search_result(query, result, source)
    
    async def cleanup_old_data(self, days: int = 30) -> bool:
        """
        Clean up old vector database entries
        
        Args:
            days: Delete data older than this many days
            
        Returns:
            True if cleanup successful
        """
        if not self.initialized:
            return False
            
        return self.vector_db.cleanup_old_data(days)
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get vector database statistics
        
        Returns:
            Dictionary with collection counts
        """
        if not self.initialized:
            return {"status": "not_initialized"}
            
        stats = self.vector_db.get_stats()
        stats["status"] = "active"
        return stats


# Global instance
vector_enhancer = VectorContextEnhancer()