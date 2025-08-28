#!/usr/bin/env python3
"""
Check projects table structure and get a valid project ID
"""
import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost", database="odras", user="postgres", 
        password="password", port=5432, connect_timeout=3
    )
    cur = conn.cursor()
    
    print("🏗️  Projects Table Structure:")
    cur.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'projects'
        ORDER BY ordinal_position
    """)
    columns = cur.fetchall()
    for col_name, data_type, nullable in columns:
        null_str = "NULL" if nullable == "YES" else "NOT NULL"
        print(f"  • {col_name}: {data_type} ({null_str})")
    
    print(f"\n📊 Projects in database:")
    cur.execute("SELECT * FROM projects ORDER BY created_at LIMIT 5")
    projects = cur.fetchall()
    
    if projects:
        # Get column names
        col_names = [desc[0] for desc in cur.description]
        for project in projects:
            project_dict = dict(zip(col_names, project))
            project_id = project_dict.get('project_id') or project_dict.get('id') or project_dict.get('uuid') or 'unknown'
            name = project_dict.get('name') or project_dict.get('title') or 'unnamed'
            print(f"  • ID: {project_id}")
            print(f"    Name: {name}")
            print(f"    All fields: {project_dict}")
            print()
    else:
        print("  No projects found")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
