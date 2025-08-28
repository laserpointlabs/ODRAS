#!/usr/bin/env python3
import psycopg2
import sys

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
    
    # Check what tables exist
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;")
    tables = cur.fetchall()
    
    print("=== Existing Tables ===")
    if tables:
        for table in tables:
            print(f"- {table[0]}")
    else:
        print("No tables found")
    
    # Check specifically for files table
    cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'files');")
    files_exists = cur.fetchone()[0]
    
    # Check for knowledge tables
    cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'knowledge_assets');")
    knowledge_exists = cur.fetchone()[0]
    
    print(f"\n=== Key Tables Status ===")
    print(f"files table exists: {files_exists}")
    print(f"knowledge_assets table exists: {knowledge_exists}")
    
    cur.close()
    conn.close()
    
    # Exit code indicates if we need to create tables
    if not files_exists:
        print("\n❌ Files table missing - need to run main migrations first")
        sys.exit(1)
    elif not knowledge_exists:
        print("\n⚠️  Knowledge tables missing - need to run knowledge migrations")
        sys.exit(2)
    else:
        print("\n✅ All required tables exist")
        sys.exit(0)
        
except Exception as e:
    print(f"❌ Database error: {e}")
    sys.exit(3)
