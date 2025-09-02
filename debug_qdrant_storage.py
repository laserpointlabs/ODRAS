#!/usr/bin/env python3
"""
Debug what's actually stored in Qdrant
"""
import sys
sys.path.append('/home/jdehart/working/ODRAS/backend')

from services.qdrant_service import get_qdrant_service
from services.config import Settings

def debug_qdrant_storage():
    print("🔍 Debug Qdrant Storage")
    print("=" * 40)
    
    try:
        qdrant_service = get_qdrant_service(Settings())
        
        # Check collections
        collections = qdrant_service.list_collections()
        print(f"📊 Collections: {collections}")
        
        # Check knowledge_chunks collection
        if "knowledge_chunks" in collections:
            print(f"\n🔍 Checking knowledge_chunks collection...")
            
            # Get collection info
            try:
                # Let's try to get some points from the collection
                import requests
                response = requests.get("http://localhost:6333/collections/knowledge_chunks")
                if response.status_code == 200:
                    collection_info = response.json()
                    print(f"📊 Collection info: {collection_info['result']}")
                
                # Try to get some points
                response = requests.post("http://localhost:6333/collections/knowledge_chunks/points/scroll", 
                                       json={"limit": 3, "with_payload": True})
                if response.status_code == 200:
                    scroll_result = response.json()
                    points = scroll_result['result']['points']
                    print(f"\n📋 Found {len(points)} points:")
                    
                    for i, point in enumerate(points):
                        print(f"  Point {i+1}:")
                        print(f"    • ID: {point['id']}")
                        print(f"    • Payload: {point.get('payload', {})}")
                        if 'vector' in point:
                            print(f"    • Vector size: {len(point['vector'])}")
                else:
                    print(f"❌ Failed to scroll points: {response.status_code}")
                    print(f"Error: {response.text}")
                
            except Exception as e:
                print(f"❌ Error checking collection: {e}")
        else:
            print(f"❌ knowledge_chunks collection not found")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_qdrant_storage()

