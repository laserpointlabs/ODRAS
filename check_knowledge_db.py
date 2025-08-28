#!/usr/bin/env python3
"""
Quick script to check if knowledge management tables exist and create them if needed.
"""

import psycopg2
import sys
import os

def check_and_create_tables():
    try:
        # Connect to database
        conn = psycopg2.connect(
            host="localhost",
            database="odras", 
            user="postgres",
            password="password",
            port=5432
        )
        
        cur = conn.cursor()
        
        # Check if knowledge_assets table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'knowledge_assets'
            );
        """)
        
        table_exists = cur.fetchone()[0]
        print(f"knowledge_assets table exists: {table_exists}")
        
        if not table_exists:
            print("Creating knowledge management tables...")
            
            # Read and execute the migration file
            migration_path = "backend/migrations/001_knowledge_management.sql"
            if os.path.exists(migration_path):
                with open(migration_path, 'r') as f:
                    migration_sql = f.read()
                
                cur.execute(migration_sql)
                conn.commit()
                print("✅ Knowledge management tables created successfully")
            else:
                print("❌ Migration file not found:", migration_path)
                return False
        else:
            print("✅ Knowledge management tables already exist")
        
        # Check table contents
        cur.execute("SELECT COUNT(*) FROM knowledge_assets;")
        asset_count = cur.fetchone()[0]
        print(f"Knowledge assets in database: {asset_count}")
        
        cur.execute("SELECT COUNT(*) FROM knowledge_chunks;")
        chunk_count = cur.fetchone()[0] 
        print(f"Knowledge chunks in database: {chunk_count}")
        
        cur.execute("SELECT COUNT(*) FROM knowledge_processing_jobs;")
        job_count = cur.fetchone()[0]
        print(f"Processing jobs in database: {job_count}")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

if __name__ == "__main__":
    success = check_and_create_tables()
    sys.exit(0 if success else 1)


