"""
Chroma vector database client for J.A.R.V.I.S
Handles automatic initialization and persistent storage
Uses Ollama Nomic embeddings for semantic search
"""

import os
import json
import hashlib
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from ..utils.logging import get_logger
from ..config import config

logger = get_logger(__name__)


class ChromaVectorDB:
    """Manages vector database operations with automatic initialization"""
    
    def __init__(self, persist_directory: str = "data/chroma_db"):
        """
        Initialize Chroma client with persistent storage and Ollama embeddings
        
        Args:
            persist_directory: Directory to store Chroma database files
        """
        self.persist_directory = persist_directory
        self.client = None
        self.collections = {}
        self._initialized = False
        
        # Try to use Ollama embeddings first, fallback to sentence transformer
        self.embedding_function = self._get_embedding_function()
    
    def _get_embedding_function(self):
        """
        Get the embedding function, preferring Ollama Nomic embeddings
        Falls back to sentence transformer if Ollama is not available
        """
        try:
            from .ollama_embeddings import OllamaEmbeddingFunction
            
            # Try to initialize Ollama embedding function
            ollama_url = getattr(config, 'OLLAMA_BASE_URL', 'http://localhost:11434')
            ollama_model = getattr(config, 'OLLAMA_EMBEDDING_MODEL', 'nomic-embed-text')
            
            embedding_fn = OllamaEmbeddingFunction(url=ollama_url, model_name=ollama_model)
            logger.info(f"Using Ollama embeddings with model: {ollama_model}")
            return embedding_fn
            
        except Exception as e:
            logger.warning(f"Failed to initialize Ollama embeddings: {e}")
            logger.info("Falling back to sentence transformer embeddings")
            
            try:
                # Fallback to sentence transformer
                return embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name="all-MiniLM-L6-v2"
                )
            except Exception as fallback_error:
                logger.error(f"Failed to initialize any embedding function: {fallback_error}")
                # Return a basic embedding function as last resort
                return embedding_functions.DefaultEmbeddingFunction()
        
    def initialize(self) -> bool:
        """
        Initialize Chroma database with automatic setup
        Returns True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            os.makedirs(self.persist_directory, exist_ok=True)
            
            # Initialize Chroma client with persistence
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Create or get collections
            self._setup_collections()
            
            self._initialized = True
            logger.info(f"Chroma database initialized at {self.persist_directory}")
            return True
            
        except ImportError as e:
            logger.warning(f"ChromaDB dependencies not available: {e}")
            logger.info("Bot will run without vector database features - install build tools and retry")
            self._initialized = False
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Chroma database: {e}")
            logger.info("Bot will run without vector database features")
            self._initialized = False
            return False
    
    def _setup_collections(self):
        """Setup required collections for the bot"""
        try:
            # Conversation memory collection
            self.collections['conversations'] = self.client.get_or_create_collection(
                name="conversations",
                embedding_function=self.embedding_function,
                metadata={"description": "User conversation history and context"}
            )
            
            # Channel context collection (includes threads)
            self.collections['channel_context'] = self.client.get_or_create_collection(
                name="channel_context",
                embedding_function=self.embedding_function,
                metadata={"description": "Channel and thread message history"}
            )
            
            # Search results collection
            self.collections['search_results'] = self.client.get_or_create_collection(
                name="search_results",
                embedding_function=self.embedding_function,
                metadata={"description": "Web search results and AI responses"}
            )
            
            # Bot responses collection
            self.collections['bot_responses'] = self.client.get_or_create_collection(
                name="bot_responses",
                embedding_function=self.embedding_function,
                metadata={"description": "All bot responses for learning and context"}
            )
            
            # Thread context collection
            self.collections['thread_context'] = self.client.get_or_create_collection(
                name="thread_context",
                embedding_function=self.embedding_function,
                metadata={"description": "Thread-specific conversations"}
            )
            
            logger.info(f"Created/loaded {len(self.collections)} Chroma collections")
            
        except Exception as e:
            logger.error(f"Failed to setup collections: {e}")
            raise
    
    def add_conversation(self, user_id: int, channel_id: int, message: str, response: str, 
                        metadata: Optional[Dict] = None) -> bool:
        """
        Add a conversation exchange to the vector database
        
        Args:
            user_id: Discord user ID
            channel_id: Discord channel ID
            message: User's message
            response: Bot's response
            metadata: Additional metadata to store
            
        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            return False
            
        try:
            # Create unique ID for this exchange
            exchange_id = f"{user_id}_{channel_id}_{datetime.now().timestamp()}"
            
            # Combine message and response for embedding
            document = f"User: {message}\nAssistant: {response}"
            
            # Prepare metadata
            meta = {
                "user_id": str(user_id),
                "channel_id": str(channel_id),
                "timestamp": datetime.now().isoformat(),
                "message": message[:500],  # Truncate for metadata
                "response": response[:500]
            }
            if metadata:
                meta.update(metadata)
            
            # Add to collection
            self.collections['conversations'].add(
                documents=[document],
                ids=[exchange_id],
                metadatas=[meta]
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add conversation to vector DB: {e}")
            return False
    
    def add_channel_message(self, channel_id: int, user_name: str, message: str,
                          message_id: Optional[int] = None) -> bool:
        """
        Add a channel message to the vector database for context
        
        Args:
            channel_id: Discord channel ID
            user_name: Name of the user who sent the message
            message: The message content
            message_id: Optional Discord message ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            return False
            
        try:
            # Create unique ID
            msg_id = str(message_id) if message_id else f"{channel_id}_{datetime.now().timestamp()}"
            
            # Format document
            document = f"{user_name}: {message}"
            
            # Prepare metadata
            meta = {
                "channel_id": str(channel_id),
                "user_name": user_name,
                "timestamp": datetime.now().isoformat(),
                "message": message[:1000]
            }
            
            # Add to collection
            self.collections['channel_context'].upsert(
                documents=[document],
                ids=[msg_id],
                metadatas=[meta]
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add channel message to vector DB: {e}")
            return False
    
    def search_conversations(self, query: str, user_id: Optional[int] = None, 
                            channel_id: Optional[int] = None, limit: int = 5) -> List[Dict]:
        """
        Search for relevant conversations using semantic similarity
        
        Args:
            query: Search query
            user_id: Optional filter by user ID
            channel_id: Optional filter by channel ID
            limit: Maximum number of results
            
        Returns:
            List of relevant conversation documents with metadata
        """
        if not self._initialized:
            return []
            
        try:
            # Build where clause for filtering (ChromaDB 1.0+ format)
            where_clause = None
            if user_id and channel_id:
                where_clause = {"$and": [
                    {"user_id": {"$eq": str(user_id)}},
                    {"channel_id": {"$eq": str(channel_id)}}
                ]}
            elif user_id:
                where_clause = {"user_id": {"$eq": str(user_id)}}
            elif channel_id:
                where_clause = {"channel_id": {"$eq": str(channel_id)}}
            
            # Perform semantic search
            results = self.collections['conversations'].query(
                query_texts=[query],
                n_results=limit,
                where=where_clause
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        'document': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to search conversations: {e}")
            return []
    
    def search_channel_context(self, query: str, channel_id: int, limit: int = 10) -> List[Dict]:
        """
        Search for relevant channel messages using semantic similarity
        
        Args:
            query: Search query
            channel_id: Channel to search in
            limit: Maximum number of results
            
        Returns:
            List of relevant messages with metadata
        """
        if not self._initialized:
            return []
            
        try:
            # Search with channel filter
            results = self.collections['channel_context'].query(
                query_texts=[query],
                n_results=limit,
                where={"channel_id": {"$eq": str(channel_id)}}
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        'document': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to search channel context: {e}")
            return []
    
    def add_bot_response(self, channel_id: int, user_id: int, response: str, 
                        response_type: str = "general", metadata: Optional[Dict] = None) -> bool:
        """
        Store all bot responses for learning and context
        
        Args:
            channel_id: Discord channel ID
            user_id: User the bot responded to
            response: The bot's response
            response_type: Type of response (general, search, admin, etc.)
            metadata: Additional metadata
            
        Returns:
            True if successful
        """
        if not self._initialized:
            return False
            
        try:
            response_id = f"{channel_id}_{user_id}_{datetime.now().timestamp()}"
            
            meta = {
                "channel_id": str(channel_id),
                "user_id": str(user_id),
                "response_type": response_type,
                "timestamp": datetime.now().isoformat(),
                "response_preview": response[:500]
            }
            if metadata:
                meta.update(metadata)
            
            self.collections['bot_responses'].add(
                documents=[response],
                ids=[response_id],
                metadatas=[meta]
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add bot response: {e}")
            return False
    
    def add_thread_message(self, thread_id: int, parent_channel_id: int, user_name: str, 
                          message: str, message_id: Optional[int] = None) -> bool:
        """
        Add thread message to vector database
        
        Args:
            thread_id: Discord thread ID
            parent_channel_id: Parent channel ID
            user_name: User who sent the message
            message: Message content
            message_id: Optional Discord message ID
            
        Returns:
            True if successful
        """
        if not self._initialized:
            return False
            
        try:
            msg_id = str(message_id) if message_id else f"{thread_id}_{datetime.now().timestamp()}"
            document = f"{user_name}: {message}"
            
            meta = {
                "thread_id": str(thread_id),
                "parent_channel_id": str(parent_channel_id),
                "user_name": user_name,
                "timestamp": datetime.now().isoformat(),
                "message": message[:1000]
            }
            
            self.collections['thread_context'].upsert(
                documents=[document],
                ids=[msg_id],
                metadatas=[meta]
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add thread message: {e}")
            return False
    
    def add_search_result(self, query: str, result: str, source: str, 
                         user_id: Optional[int] = None, channel_id: Optional[int] = None) -> bool:
        """
        Store search results for context and caching
        
        Args:
            query: The search query
            result: The search result
            source: Source of result (google, openai, perplexity, etc.)
            user_id: Optional user who made the query
            channel_id: Optional channel where query was made
            
        Returns:
            True if successful
        """
        if not self._initialized:
            return False
            
        try:
            result_id = hashlib.md5(f"{query}_{source}_{datetime.now().timestamp()}".encode()).hexdigest()
            
            document = f"Query: {query}\nSource: {source}\nResult: {result}"
            
            meta = {
                "query": query[:500],
                "source": source,
                "timestamp": datetime.now().isoformat(),
                "result_preview": result[:500]
            }
            if user_id:
                meta["user_id"] = str(user_id)
            if channel_id:
                meta["channel_id"] = str(channel_id)
            
            self.collections['search_results'].upsert(
                documents=[document],
                ids=[result_id],
                metadatas=[meta]
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add search result: {e}")
            return False
    
    def cache_search_result(self, query: str, result: str, source: str = "web") -> bool:
        """
        Cache a search result for faster retrieval (delegates to add_search_result)
        
        Args:
            query: The search query
            result: The search result
            source: Source of the result (web, openai, etc.)
            
        Returns:
            True if successful, False otherwise
        """
        return self.add_search_result(query, result, source)
    
    def get_cached_search(self, query: str, max_age_hours: int = 24) -> Optional[str]:
        """
        Get cached search result if available and recent
        
        Args:
            query: The search query
            max_age_hours: Maximum age of cache in hours
            
        Returns:
            Cached result if found and recent, None otherwise
        """
        if not self._initialized:
            return None
            
        try:
            # Search for exact or similar queries in search_results collection
            results = self.collections['search_results'].query(
                query_texts=[query],
                n_results=1
            )
            
            if results['documents'] and results['documents'][0]:
                # Check age of result
                metadata = results['metadatas'][0][0] if results['metadatas'] else {}
                if 'timestamp' in metadata:
                    timestamp = datetime.fromisoformat(metadata['timestamp'])
                    if datetime.now() - timestamp < timedelta(hours=max_age_hours):
                        # Extract result from document
                        doc = results['documents'][0][0]
                        if 'Result: ' in doc:
                            return doc.split('Result: ', 1)[1]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cached search: {e}")
            return None
    
    def cleanup_old_data(self, days: int = 30) -> bool:
        """
        Clean up old data from collections
        
        Args:
            days: Delete data older than this many days
            
        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            return False
            
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Clean up each collection
            for name, collection in self.collections.items():
                    
                # Get items older than cutoff date
                try:
                    old_items = collection.get(
                        where={"timestamp": {"$lt": cutoff_date}}
                    )
                    
                    if old_items['ids']:
                        # Delete old items
                        collection.delete(ids=old_items['ids'])
                        logger.info(f"Cleaned {len(old_items['ids'])} old items from {name}")
                        
                except Exception as e:
                    # Fallback to getting all items if timestamp query fails
                    logger.debug(f"Timestamp query failed, using fallback cleanup for {name}: {e}")
                    all_items = collection.get()
                    
                    if all_items['ids']:
                        # Find old items manually
                        old_ids = []
                        for i, metadata in enumerate(all_items['metadatas'] or []):
                            if 'timestamp' in metadata and metadata['timestamp'] < cutoff_date:
                                old_ids.append(all_items['ids'][i])
                        
                        # Delete old items
                        if old_ids:
                            collection.delete(ids=old_ids)
                            logger.info(f"Cleaned {len(old_ids)} old items from {name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return False
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about the vector database
        
        Returns:
            Dictionary with collection counts
        """
        if not self._initialized:
            return {}
            
        stats = {}
        try:
            for name, collection in self.collections.items():
                stats[name] = collection.count()
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            
        return stats


# Global instance
vector_db = ChromaVectorDB()