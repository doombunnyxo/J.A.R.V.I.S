#!/usr/bin/env python3
"""
Simple script to check ChromaDB status on VM
Run this on your VM where the bot is deployed
"""

import os
import sys

def check_chromadb_files():
    """Check for ChromaDB files and directories"""
    print("🔍 Checking for ChromaDB files...")
    
    # Common ChromaDB directory locations
    possible_paths = [
        './chroma_db',
        './data/chroma_db', 
        './chromadb',
        './data/chromadb'
    ]
    
    found_any = False
    for path in possible_paths:
        if os.path.exists(path):
            found_any = True
            print(f"✅ Found ChromaDB directory: {path}")
            
            # Check size
            total_size = 0
            file_count = 0
            for root, dirs, files in os.walk(path):
                for file in files:
                    filepath = os.path.join(root, file)
                    if os.path.exists(filepath):
                        size = os.path.getsize(filepath)
                        total_size += size
                        file_count += 1
            
            print(f"   📁 Files: {file_count}")
            print(f"   💾 Total size: {total_size} bytes ({total_size/1024/1024:.2f} MB)")
            
            # List some files
            try:
                files = os.listdir(path)[:5]  # First 5 files
                print(f"   📄 Sample files: {files}")
            except:
                pass
    
    if not found_any:
        print("❌ No ChromaDB directories found")
        print("   Check these locations manually:")
        for path in possible_paths:
            print(f"   - {os.path.abspath(path)}")

def check_bot_imports():
    """Check if bot can import ChromaDB modules"""
    print("\n🔍 Checking bot imports...")
    
    try:
        # Add current directory to path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # Try importing ChromaDB
        import chromadb
        print("✅ chromadb module imported successfully")
        print(f"   Version: {chromadb.__version__}")
        
        # Try importing bot's vector modules
        try:
            from src.vectordb.chroma_client import ChromaDBClient
            print("✅ Bot's ChromaDBClient imported successfully")
            
            # Try initializing (without connecting)
            print("🔍 Testing ChromaDB initialization...")
            client = ChromaDBClient()
            if hasattr(client, 'initialized'):
                print(f"   Initialization status: {client.initialized}")
            if hasattr(client, 'persist_directory'):
                print(f"   Persist directory: {client.persist_directory}")
                
        except Exception as e:
            print(f"❌ Bot ChromaDB import failed: {e}")
            
    except ImportError as e:
        print(f"❌ chromadb module not found: {e}")
        print("   Install with: pip install chromadb==1.0.20")

if __name__ == "__main__":
    print("ChromaDB Debug Check")
    print("=" * 40)
    
    check_chromadb_files()
    check_bot_imports()
    
    print("\nHow to check if it's working:")
    print("1. Run the bot and use @bot commands")
    print("2. Check bot logs for 'Vector database' messages")
    print("3. Look for 'store.*vector' in logs")
    print("4. Re-run this script to see if files grow")