#!/usr/bin/env python3
"""
Check if file metadata was properly stored in PostgreSQL files table
"""
import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost", database="odras", user="postgres", 
        password="password", port=5432, connect_timeout=3
    )
    cur = conn.cursor()
    
    print("📊 Files in PostgreSQL:")
    cur.execute("""
        SELECT id, filename, file_size, storage_backend, storage_path, project_id, created_at 
        FROM files 
        ORDER BY created_at DESC 
        LIMIT 5
    """)
    files = cur.fetchall()
    
    if files:
        print("Recent files:")
        for file_id, filename, file_size, storage_backend, storage_path, project_id, created_at in files:
            print(f"  • ID: {file_id}")
            print(f"    Filename: {filename}")
            print(f"    Size: {file_size}")
            print(f"    Backend: {storage_backend}")
            print(f"    Path: {storage_path}")
            print(f"    Project: {project_id}")
            print(f"    Created: {created_at}")
            print()
    else:
        print("  No files found in files table")
    
    # Check file_content table
    print("📊 File Content Table:")
    cur.execute("SELECT COUNT(*) FROM file_content")
    content_count = cur.fetchone()[0]
    print(f"  • Content records: {content_count}")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
