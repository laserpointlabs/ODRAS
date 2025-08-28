#!/usr/bin/env python3
"""
Simple test to check just file upload without knowledge processing
"""

import requests
import json
import psycopg2

def test_simple_upload():
    # Get auth token
    login_url = "http://localhost:8000/api/auth/login"
    login_data = {"username": "admin", "password": "admin"}
    response = requests.post(login_url, json=login_data)
    token = response.json().get("token")
    
    # Get project ID
    conn = psycopg2.connect(host="localhost", database="odras", user="postgres", password="password", port=5432)
    cur = conn.cursor()
    cur.execute("SELECT project_id FROM projects LIMIT 1")
    project_id = str(cur.fetchone()[0])
    cur.close()
    conn.close()
    
    # Upload file WITHOUT knowledge processing
    url = "http://localhost:8000/api/files/upload"
    files = {'file': ('test.txt', 'Hello world test file', 'text/plain')}
    data = {
        'project_id': project_id,
        'tags': json.dumps({'docType': 'test', 'status': 'new'}),
        # NOTE: No process_for_knowledge parameter
    }
    headers = {'Authorization': f'Bearer {token}'}
    
    response = requests.post(url, files=files, data=data, headers=headers)
    print(f"Upload response: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"File ID: {result.get('file_id')}")
        print(f"Message: {result.get('message')}")
        
        # Check database
        conn = psycopg2.connect(host="localhost", database="odras", user="postgres", password="password", port=5432)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM files")
        count = cur.fetchone()[0]
        print(f"Files in database: {count}")
        
        if count > 0:
            cur.execute("SELECT id, filename, file_size, content_type FROM files ORDER BY created_at DESC LIMIT 1")
            row = cur.fetchone()
            print(f"Latest file: {row}")
        
        cur.close()
        conn.close()
        return True
    else:
        print(f"Error: {response.text}")
        return False

if __name__ == "__main__":
    test_simple_upload()
