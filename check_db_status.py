#!/usr/bin/env python3
"""
Check current database status and identify the file storage issues
"""
import psycopg2
import requests

def check_db_status():
    print("🔍 Database Status Check")
    print("=" * 50)
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host="localhost", database="odras", user="postgres", 
            password="password", port=5432, connect_timeout=5
        )
        cur = conn.cursor()
        
        # Check critical tables
        critical_tables = ['users', 'projects', 'files', 'knowledge_assets', 'knowledge_chunks']
        print("📊 Critical Tables Status:")
        
        for table in critical_tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                print(f"  ✅ {table}: {count} records")
            except Exception as e:
                print(f"  ❌ {table}: ERROR - {e}")
        
        # Check foreign key constraints
        print("\n🔗 Foreign Key Constraints:")
        cur.execute("""
            SELECT 
                tc.table_name, 
                kcu.column_name, 
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name 
            FROM 
                information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' 
                AND tc.table_name IN ('knowledge_assets', 'knowledge_chunks')
        """)
        
        constraints = cur.fetchall()
        for table, column, ref_table, ref_column in constraints:
            print(f"  🔗 {table}.{column} → {ref_table}.{ref_column}")
        
        # Check recent file upload attempts
        print("\n📁 Recent Files (if any):")
        try:
            cur.execute("SELECT id, filename, created_at FROM files ORDER BY created_at DESC LIMIT 3")
            files = cur.fetchall()
            if files:
                for file_id, filename, created_at in files:
                    print(f"  📄 {filename} ({file_id}) - {created_at}")
            else:
                print("  📭 No files found in database")
        except Exception as e:
            print(f"  ❌ Error checking files: {e}")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")
    
    # Check Qdrant
    print("\n🔍 Qdrant Status:")
    try:
        response = requests.get("http://localhost:6333/collections", timeout=5)
        if response.status_code == 200:
            collections = response.json()
            if collections and 'result' in collections:
                coll_names = [c['name'] for c in collections['result']['collections']]
                print(f"  ✅ Collections: {', '.join(coll_names)}")
            else:
                print("  📭 No collections found")
        else:
            print(f"  ❌ Qdrant error: {response.status_code}")
    except Exception as e:
        print(f"  ❌ Qdrant connection error: {e}")

if __name__ == "__main__":
    check_db_status()

