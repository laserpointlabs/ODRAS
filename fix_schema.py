#!/usr/bin/env python3
"""
Fix foreign key constraint in file_content table
"""

import psycopg2

def fix_foreign_key_constraint():
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="odras",
            user="postgres", 
            password="password",
            port=5432
        )
        
        cur = conn.cursor()
        
        print("🔧 Fixing foreign key constraint in file_content table...")
        
        # Drop the old constraint
        print("   Dropping old foreign key constraint...")
        cur.execute("""
            ALTER TABLE file_content 
            DROP CONSTRAINT IF EXISTS file_content_file_id_fkey;
        """)
        
        # Add new constraint pointing to files table
        print("   Adding new foreign key constraint to files table...")
        cur.execute("""
            ALTER TABLE file_content 
            ADD CONSTRAINT file_content_file_id_fkey 
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE;
        """)
        
        conn.commit()
        print("✅ Foreign key constraint fixed!")
        
        # Check the current table structure
        print("\n📊 Current table structure:")
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('files', 'file_storage', 'file_content')
            ORDER BY table_name;
        """)
        
        tables = cur.fetchall()
        for table in tables:
            print(f"   - {table[0]}")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error fixing schema: {e}")
        return False

if __name__ == "__main__":
    fix_foreign_key_constraint()
