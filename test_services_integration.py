#!/usr/bin/env python3
"""
Test all services integration for ODRAS Knowledge Management
Tests MinIO, Qdrant, Neo4j, and PostgreSQL connections
"""

import json
import requests
import psycopg2
from minio import Minio
from minio.error import S3Error
import sys
import io

def test_minio():
    """Test MinIO S3-compatible storage"""
    print("🗄️  Testing MinIO...")
    try:
        client = Minio(
            "localhost:9000",
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False
        )
        
        # Test connection by listing buckets
        buckets = client.list_buckets()
        print(f"   ✅ MinIO connected - {len(buckets)} buckets found")
        
        # Check if our bucket exists
        bucket_name = "odras-files"
        if not client.bucket_exists(bucket_name):
            print(f"   📦 Creating bucket: {bucket_name}")
            client.make_bucket(bucket_name)
            print(f"   ✅ Bucket '{bucket_name}' created")
        else:
            print(f"   ✅ Bucket '{bucket_name}' exists")
        
        # Test file upload/download
        test_content = b"Hello ODRAS Knowledge Management!"
        test_file = "test-file.txt"
        
        client.put_object(
            bucket_name, 
            test_file, 
            io.BytesIO(test_content),
            length=len(test_content),
            content_type="text/plain"
        )
        print(f"   ✅ Test file uploaded to MinIO")
        
        # Test download
        response = client.get_object(bucket_name, test_file)
        downloaded_content = response.read()
        if downloaded_content == test_content:
            print(f"   ✅ Test file downloaded successfully")
        else:
            print(f"   ❌ File content mismatch")
            return False
        
        # Clean up test file
        client.remove_object(bucket_name, test_file)
        print(f"   🧹 Test file cleaned up")
        
        return True
        
    except Exception as e:
        print(f"   ❌ MinIO error: {e}")
        return False

def test_qdrant():
    """Test Qdrant vector database"""
    print("🔍 Testing Qdrant...")
    try:
        # Test basic connection
        response = requests.get("http://localhost:6333/")
        if response.status_code != 200:
            print(f"   ❌ Qdrant connection failed: {response.status_code}")
            return False
        
        info = response.json()
        print(f"   ✅ Qdrant connected - version {info.get('version')}")
        
        # Test collections endpoint
        collections_response = requests.get("http://localhost:6333/collections")
        if collections_response.status_code == 200:
            collections = collections_response.json()
            print(f"   ✅ Collections accessible - {len(collections.get('result', {}).get('collections', []))} collections found")
        else:
            print(f"   ❌ Collections endpoint error: {collections_response.status_code}")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Qdrant error: {e}")
        return False

def test_neo4j():
    """Test Neo4j graph database"""
    print("📊 Testing Neo4j...")
    try:
        # Test HTTP endpoint
        response = requests.get("http://localhost:7474/")
        if response.status_code != 200:
            print(f"   ❌ Neo4j HTTP connection failed: {response.status_code}")
            return False
        
        info = response.json()
        print(f"   ✅ Neo4j connected - version {info.get('neo4j_version')}")
        
        # Test authentication and query capability
        auth = ("neo4j", "testpassword")
        
        # Simple query to test connection
        query_data = {
            "statements": [
                {
                    "statement": "RETURN 'Hello Neo4j' AS message",
                    "resultDataContents": ["row"]
                }
            ]
        }
        
        query_response = requests.post(
            "http://localhost:7474/db/neo4j/tx/commit",
            json=query_data,
            auth=auth,
            headers={"Content-Type": "application/json"}
        )
        
        if query_response.status_code == 200:
            result = query_response.json()
            if result.get('results') and len(result['results']) > 0:
                print("   ✅ Neo4j query executed successfully")
            else:
                print("   ❌ Neo4j query returned no results")
                return False
        else:
            print(f"   ❌ Neo4j query failed: {query_response.status_code}")
            print(f"       Response: {query_response.text}")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ❌ Neo4j error: {e}")
        return False

def test_postgresql():
    """Test PostgreSQL database"""
    print("🗃️  Testing PostgreSQL...")
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="odras",
            user="postgres", 
            password="password",
            port=5432
        )
        
        cur = conn.cursor()
        
        # Test basic query
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"   ✅ PostgreSQL connected - {version.split()[0]} {version.split()[1]}")
        
        # Check required tables exist
        required_tables = ['files', 'knowledge_assets', 'knowledge_chunks']
        
        for table in required_tables:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                );
            """, (table,))
            
            exists = cur.fetchone()[0]
            if exists:
                print(f"   ✅ Table '{table}' exists")
            else:
                print(f"   ❌ Table '{table}' missing")
                cur.close()
                conn.close()
                return False
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ PostgreSQL error: {e}")
        return False

def test_odras_api():
    """Test ODRAS API endpoints"""
    print("🌐 Testing ODRAS API...")
    try:
        # Test health endpoints
        endpoints = [
            ("http://localhost:8000/api/files/storage/info", "File Storage"),
            ("http://localhost:8000/api/knowledge/health", "Knowledge Management")
        ]
        
        all_good = True
        for url, name in endpoints:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print(f"   ✅ {name} API accessible")
                else:
                    print(f"   ❌ {name} API error: {response.status_code}")
                    all_good = False
            except requests.RequestException as e:
                print(f"   ❌ {name} API connection failed: {e}")
                all_good = False
        
        return all_good
        
    except Exception as e:
        print(f"   ❌ ODRAS API error: {e}")
        return False

def main():
    """Run all service integration tests"""
    print("🧪 ODRAS Services Integration Test")
    print("=" * 50)
    
    tests = [
        ("MinIO", test_minio),
        ("Qdrant", test_qdrant),
        ("Neo4j", test_neo4j),
        ("PostgreSQL", test_postgresql),
        ("ODRAS API", test_odras_api)
    ]
    
    results = {}
    
    for name, test_func in tests:
        try:
            results[name] = test_func()
            print()
        except Exception as e:
            print(f"   ❌ {name} test crashed: {e}")
            results[name] = False
            print()
    
    # Summary
    print("📊 Test Results Summary")
    print("-" * 30)
    
    all_passed = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:<15} {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 All services are properly configured and connected!")
        print("🚀 Ready for Knowledge Management integration!")
    else:
        print("💥 Some services failed - please check configurations")
        sys.exit(1)

if __name__ == "__main__":
    main()
