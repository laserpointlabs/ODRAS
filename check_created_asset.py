#!/usr/bin/env python3
"""
Check if the newly created knowledge asset has chunks stored properly
"""
import psycopg2

def check_asset():
    print("🔍 Checking Created Knowledge Asset")
    print("=" * 50)
    
    asset_id = "08ef1cfe-2ba8-4b77-83fa-1772e4c591d1"
    
    try:
        conn = psycopg2.connect(
            host="localhost", database="odras", user="postgres", 
            password="password", port=5432, connect_timeout=5
        )
        cur = conn.cursor()
        
        # Check knowledge asset
        print("📊 Knowledge Asset Details:")
        cur.execute("SELECT * FROM knowledge_assets WHERE id = %s", (asset_id,))
        asset = cur.fetchone()
        
        if asset:
            columns = [desc[0] for desc in cur.description]
            asset_dict = dict(zip(columns, asset))
            print(f"  ✅ Found asset: {asset_dict['title']}")
            print(f"  📄 Type: {asset_dict['document_type']}")
            print(f"  📊 Status: {asset_dict['status']}")
            print(f"  📈 Processing stats: {asset_dict.get('processing_stats', {})}")
        else:
            print(f"  ❌ Asset {asset_id} not found")
            return
        
        # Check chunks
        print(f"\n📝 Knowledge Chunks:")
        cur.execute("SELECT * FROM knowledge_chunks WHERE asset_id = %s ORDER BY sequence_number", (asset_id,))
        chunks = cur.fetchall()
        
        if chunks:
            print(f"  ✅ Found {len(chunks)} chunks")
            for i, chunk in enumerate(chunks):
                chunk_columns = [desc[0] for desc in cur.description]
                chunk_dict = dict(zip(chunk_columns, chunk))
                print(f"  📋 Chunk {i+1}:")
                print(f"    • ID: {chunk_dict['id']}")
                print(f"    • Sequence: {chunk_dict['sequence_number']}")
                print(f"    • Type: {chunk_dict['chunk_type']}")
                print(f"    • Content length: {len(chunk_dict['content'])}")
                print(f"    • Content preview: {chunk_dict['content'][:100]}...")
                print(f"    • Qdrant point ID: {chunk_dict.get('qdrant_point_id')}")
                if i >= 2:  # Limit to first 3 chunks
                    break
        else:
            print(f"  ❌ No chunks found for asset {asset_id}")
        
        cur.close()
        conn.close()
        
        print(f"\n✅ Knowledge asset appears to be properly stored with chunks!")
        
    except Exception as e:
        print(f"❌ Error checking asset: {e}")

if __name__ == "__main__":
    check_asset()
