#!/usr/bin/env python3
"""
Test script for Ollama embedding integration
Run this to verify Ollama Nomic embeddings are working
"""

import sys
import asyncio
from src.vectordb.chroma_client import ChromaVectorDB
from src.config import config

async def test_ollama_embeddings():
    """Test Ollama embedding functionality"""
    print("Testing Ollama Nomic embeddings integration...")
    
    # Initialize vector database
    db = ChromaVectorDB()
    
    print(f"Ollama URL: {getattr(config, 'OLLAMA_BASE_URL', 'http://localhost:11434')}")
    print(f"Embedding Model: {getattr(config, 'OLLAMA_EMBEDDING_MODEL', 'nomic-embed-text')}")
    
    # Test initialization
    success = db.initialize()
    if not success:
        print("❌ Vector database initialization failed")
        return False
    
    print("✅ Vector database initialized successfully")
    
    # Test embedding function
    try:
        test_docs = [
            "Hello, how are you today?",
            "The weather is nice outside.",
            "I love programming with Python."
        ]
        
        print(f"\nTesting embeddings with {len(test_docs)} documents...")
        
        # This will internally call the embedding function
        result = db.add_conversation(
            user_id=12345,
            channel_id=67890,
            message="Test message",
            response="Test response"
        )
        
        if result:
            print("✅ Successfully stored conversation with embeddings")
        else:
            print("❌ Failed to store conversation")
            return False
        
        # Test search
        search_results = db.search_conversations(
            query="hello greeting",
            user_id=12345,
            limit=1
        )
        
        print(f"✅ Search returned {len(search_results)} results")
        
        # Get stats
        stats = db.get_stats()
        print(f"✅ Database stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing embeddings: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    try:
        success = asyncio.run(test_ollama_embeddings())
        
        if success:
            print("\n🎉 All tests passed! Ollama Nomic embeddings are working correctly.")
            print("\nSetup complete. Your bot will now use:")
            print("• Ollama for embeddings (Nomic model)")
            print("• Chroma for vector storage")
            print("• Semantic search for context enhancement")
        else:
            print("\n⚠️  Some tests failed. Check the logs above.")
            print("\nFallback behavior:")
            print("• Bot will use sentence transformer embeddings instead")
            print("• Vector database features will still work")
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()