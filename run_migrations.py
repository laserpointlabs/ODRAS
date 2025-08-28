#!/usr/bin/env python3
"""
ODRAS Database Migration Runner
"""

import psycopg2
import sys
import os
from pathlib import Path

def run_migrations():
    try:
        # Connect to database
        conn = psycopg2.connect(
            host="localhost",
            database="odras", 
            user="postgres",
            password="password",
            port=5432
        )
        
        # Get migrations directory
        migrations_dir = Path(__file__).parent / "backend" / "migrations"
        
        # Find all SQL migration files
        sql_files = sorted([f for f in migrations_dir.glob("*.sql")])
        
        if not sql_files:
            print("❌ No SQL migration files found")
            return False
            
        print(f"📁 Found {len(sql_files)} migration files:")
        for f in sql_files:
            print(f"   - {f.name}")
        print()
        
        cur = conn.cursor()
        
        # Run each migration
        for sql_file in sql_files:
            print(f"🔄 Running migration: {sql_file.name}")
            
            try:
                with open(sql_file, 'r') as f:
                    sql_content = f.read()
                
                # Execute the migration
                cur.execute(sql_content)
                conn.commit()
                
                print(f"✅ Successfully applied: {sql_file.name}")
                
            except Exception as e:
                print(f"❌ Failed to apply {sql_file.name}: {e}")
                conn.rollback()
                return False
        
        cur.close()
        conn.close()
        
        print("\n🎉 All migrations completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def verify_tables():
    """Verify that expected tables exist"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="odras", 
            user="postgres",
            password="password",
            port=5432
        )
        
        cur = conn.cursor()
        
        # Check for required tables
        required_tables = [
            'files',
            'knowledge_assets', 
            'knowledge_chunks',
            'knowledge_processing_jobs'
        ]
        
        print("\n🔍 Verifying required tables:")
        all_exist = True
        
        for table in required_tables:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                );
            """, (table,))
            
            exists = cur.fetchone()[0]
            status = "✅" if exists else "❌"
            print(f"   {status} {table}: {'EXISTS' if exists else 'MISSING'}")
            
            if not exists:
                all_exist = False
        
        cur.close()
        conn.close()
        
        return all_exist
        
    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 ODRAS Database Migration Runner")
    print("=" * 40)
    
    # Run migrations
    if run_migrations():
        # Verify tables
        if verify_tables():
            print("\n🎯 Database is ready for ODRAS Knowledge Management!")
        else:
            print("\n⚠️  Some tables are missing - please check migrations")
            sys.exit(1)
    else:
        print("\n💥 Migration failed!")
        sys.exit(1)
