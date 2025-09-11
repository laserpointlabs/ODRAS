#!/usr/bin/env python3
import psycopg2
import sys

try:
    # Connect to database
    conn = psycopg2.connect(
        host="localhost", database="odras", user="postgres", password="password"
    )

    cur = conn.cursor()

    # Check if namespace_registry table exists
    cur.execute(
        """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'namespace_registry'
        );
    """
    )

    table_exists = cur.fetchone()[0]
    print(f"namespace_registry table exists: {table_exists}")

    if table_exists:
        # Count records
        cur.execute("SELECT COUNT(*) FROM namespace_registry;")
        count = cur.fetchone()[0]
        print(f"Number of namespaces: {count}")

        # Show all namespaces
        cur.execute(
            "SELECT id, name, type, path, prefix, status FROM namespace_registry;"
        )
        rows = cur.fetchall()
        for row in rows:
            print(f"  {row[1]} ({row[2]}) - {row[3]} - {row[5]}")
    else:
        print("Table does not exist - migrations may not have been run")

    cur.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
