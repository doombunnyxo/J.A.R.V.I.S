#!/usr/bin/env python3
"""
Script to check ChromaDB population and contents
"""

import asyncio
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

async def check_chromadb_status():
    """Check ChromaDB collections and their contents"""
    try:
        from src.vectordb.chroma_client import ChromaDBClient
        from src.config import config
        
        # Initialize ChromaDB client
        print("🔍 Initializing ChromaDB client...")
        client = ChromaDBClient()
        
        if not client.initialized:
            print("❌ ChromaDB not initialized")
            return
        
        print("✅ ChromaDB client initialized successfully")
        print(f"📍 Database path: {client.persist_directory}")
        
        # Check all collections
        collections = ['conversations', 'channel_context', 'search_results', 'bot_responses', 'thread_context']
        
        print("\n📊 Collection Status:")
        print("-" * 50)
        
        total_items = 0
        for collection_name in collections:
            try:
                collection = client.collections.get(collection_name)
                if collection:
                    count = collection.count()
                    total_items += count
                    print(f"📁 {collection_name:<20} : {count:>6} items")
                    
                    # Show sample data if exists
                    if count > 0:
                        try:
                            sample = collection.peek(limit=3)
                            if sample and 'documents' in sample and sample['documents']:
                                print(f"   📄 Sample: {sample['documents'][0][:100]}...")
                        except Exception as e:
                            print(f"   ⚠️  Could not peek: {e}")
                else:
                    print(f"❌ {collection_name:<20} : Not found")
            except Exception as e:
                print(f"❌ {collection_name:<20} : Error - {e}")
        
        print("-" * 50)
        print(f"📈 Total items across all collections: {total_items}")
        
        # Check recent activity
        print("\n🕒 Recent Activity Check:")
        try:
            conv_collection = client.collections.get('conversations')
            if conv_collection and conv_collection.count() > 0:
                # Get recent conversations
                recent = conv_collection.query(
                    query_texts=["recent conversation"],
                    n_results=min(5, conv_collection.count())
                )
                
                if recent and 'metadatas' in recent and recent['metadatas'][0]:
                    print("✅ Recent conversations found:")
                    for i, metadata in enumerate(recent['metadatas'][0][:3]):
                        timestamp = metadata.get('timestamp', 'Unknown')
                        user_id = metadata.get('user_id', 'Unknown')
                        channel_id = metadata.get('channel_id', 'Unknown')
                        print(f"   🔹 {timestamp} | User: {user_id} | Channel: {channel_id}")
                else:
                    print("📝 Conversations exist but no metadata found")
            else:
                print("📭 No conversations found")
                
        except Exception as e:
            print(f"❌ Could not check recent activity: {e}")
            
        # Check Ollama embedding status
        print("\n🤖 Embedding Model Status:")
        try:
            embedding_fn = client._get_embedding_function()
            if hasattr(embedding_fn, 'model_name'):
                print(f"✅ Using Ollama model: {embedding_fn.model_name}")
            else:
                print("🔄 Using fallback embedding function")
        except Exception as e:
            print(f"❌ Embedding function error: {e}")
            
        return total_items > 0
        
    except Exception as e:
        print(f"❌ Error checking ChromaDB: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(check_chromadb_status())
    if result:
        print("\n✅ ChromaDB appears to be working and populated!")
    else:
        print("\n⚠️  ChromaDB may not be populated or working correctly")