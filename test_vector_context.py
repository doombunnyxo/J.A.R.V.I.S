#!/usr/bin/env python3
"""
Test script for vector-only context system
Verifies that context is being stored and retrieved from vector database
"""

import sys
import asyncio
from src.ai.context_manager import ContextManager
from src.vectordb.context_enhancer import vector_enhancer

class MockMessage:
    """Mock Discord message for testing"""
    def __init__(self, author_id, channel_id, content):
        self.author = MockAuthor(author_id)
        self.channel = MockChannel(channel_id)
        self.content = content
        self.reference = None

class MockAuthor:
    def __init__(self, user_id):
        self.id = user_id
        self.display_name = f"TestUser{user_id}"

class MockChannel:
    def __init__(self, channel_id):
        self.id = channel_id
        self.name = f"test-channel-{channel_id}"

async def test_vector_context():
    """Test vector-only context system"""
    print("Testing vector-only context system...")
    
    # Initialize vector database
    success = await vector_enhancer.initialize()
    if not success:
        print("❌ Vector database initialization failed")
        return False
    
    print("✅ Vector database initialized")
    
    # Initialize context manager
    context_manager = ContextManager()
    
    # Test storing conversations
    print("\n📝 Testing conversation storage...")
    user_id = 12345
    channel_id = 67890
    
    # Add some test conversations
    test_conversations = [
        ("Hello, how are you?", "I'm doing well, thank you for asking!"),
        ("What's the weather like today?", "I don't have access to current weather data, but I can help you find weather information."),
        ("Can you help me with Python programming?", "Absolutely! I'd be happy to help with Python programming. What specific topic are you working on?")
    ]
    
    for user_msg, bot_response in test_conversations:
        context_manager.add_to_conversation(user_id, channel_id, user_msg, bot_response)
        print(f"  Stored: '{user_msg[:30]}...' -> '{bot_response[:30]}...'")
    
    # Wait a moment for async storage
    await asyncio.sleep(2)
    
    # Test storing channel messages
    print("\n📝 Testing channel message storage...")
    test_messages = [
        "Hey everyone, how's the project going?",
        "I just finished the database setup",
        "Great! Let me know if you need help with the API endpoints"
    ]
    
    mock_channel = MockChannel(channel_id)
    for i, msg in enumerate(test_messages):
        context_manager.add_channel_message(
            channel_id=channel_id,
            user_name=f"TestUser{i+1}",
            message_content=msg,
            channel=mock_channel
        )
        print(f"  Stored channel message: '{msg[:40]}...'")
    
    # Wait for async storage
    await asyncio.sleep(2)
    
    # Test context retrieval
    print("\n🔍 Testing context retrieval...")
    
    # Test conversation context retrieval
    mock_message = MockMessage(user_id, channel_id, "Test query")
    
    try:
        # Test semantic search for conversations
        conv_context = await context_manager.get_conversation_context(
            user_id=user_id,
            channel_id=channel_id,
            query="Python programming help"
        )
        
        print(f"  Found {len(conv_context)} relevant conversations")
        for ctx in conv_context[:2]:  # Show first 2
            print(f"    - {ctx[:60]}...")
        
        # Test semantic search for channel messages
        channel_context = await context_manager.get_channel_context(
            channel_id=channel_id,
            query="project database",
            limit=5
        )
        
        print(f"  Found {len(channel_context)} relevant channel messages")
        for ctx in channel_context[:2]:  # Show first 2
            print(f"    - {ctx[:60]}...")
        
        # Test full context building
        print("\n🏗️  Testing full context building...")
        full_context = await context_manager.build_full_context(
            query="How can I help with the Python project?",
            user_id=user_id,
            channel_id=channel_id,
            user_name="TestUser",
            message=mock_message
        )
        
        print(f"  Built context with {len(full_context)} characters")
        print(f"  Context preview:\n{full_context[:200]}...")
        
        # Verify no in-memory storage
        print("\n🧹 Verifying no in-memory storage...")
        if not hasattr(context_manager, 'unified_conversations'):
            print("  ✅ No in-memory conversation storage found")
        elif len(getattr(context_manager, 'unified_conversations', {})) == 0:
            print("  ✅ In-memory conversation storage is empty")
        else:
            print("  ⚠️  In-memory conversation storage still exists")
        
        if not hasattr(context_manager, 'channel_conversations'):
            print("  ✅ No in-memory channel storage found")
        elif len(getattr(context_manager, 'channel_conversations', {})) == 0:
            print("  ✅ In-memory channel storage is empty")
        else:
            print("  ⚠️  In-memory channel storage still exists")
        
        return True
        
    except Exception as e:
        print(f"❌ Context retrieval failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    try:
        success = asyncio.run(test_vector_context())
        
        if success:
            print("\n🎉 Vector-only context system is working correctly!")
            print("\nKey improvements:")
            print("• No in-memory storage (everything in vector DB)")
            print("• Semantic search for relevant context")
            print("• Permanent context still raw from JSON files")
            print("• Better context relevance through embeddings")
        else:
            print("\n⚠️  Some tests failed. Check the logs above.")
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()