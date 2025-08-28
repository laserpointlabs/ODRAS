#!/usr/bin/env python3
"""
Test script to verify database connectivity for ODRAS system.
"""
import requests
import json
import psycopg2

def test_postgresql():
    """Test PostgreSQL connectivity"""
    try:
        conn = psycopg2.connect(
            host="localhost", database="odras", user="postgres", 
            password="password", port=5432
        )
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
        table_count = cur.fetchone()[0]
        cur.close()
        conn.close()
        print(f"✅ PostgreSQL: Connected ({table_count} tables)")
        return True
    except Exception as e:
        print(f"❌ PostgreSQL: {e}")
        return False

def test_qdrant():
    """Test Qdrant connectivity"""
    try:
        response = requests.get("http://localhost:6333/collections", timeout=5)
        if response.status_code == 200:
            collections = response.json().get('result', {}).get('collections', [])
            print(f"✅ Qdrant: Connected ({len(collections)} collections)")
            return True
        else:
            print(f"❌ Qdrant: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Qdrant: {e}")
        return False

def test_neo4j():
    """Test Neo4j connectivity"""
    try:
        import subprocess
        result = subprocess.run([
            'docker', 'exec', 'odras_neo4j', 'cypher-shell', 
            '-u', 'neo4j', '-p', 'testpassword', 
            'MATCH (n) RETURN count(n) as node_count'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            # Parse the result - look for node count
            output_lines = result.stdout.strip().split('\n')
            node_count = 0
            for line in output_lines:
                if line.isdigit():
                    node_count = int(line)
                    break
            print(f"✅ Neo4j: Connected ({node_count} nodes)")
            return True
        else:
            print(f"❌ Neo4j: Command failed")
            return False
    except Exception as e:
        print(f"❌ Neo4j: {e}")
        return False

def test_fuseki():
    """Test Fuseki connectivity"""
    try:
        response = requests.get("http://localhost:3030/$/datasets", timeout=5)
        if response.status_code == 200:
            datasets = response.json().get('datasets', [])
            print(f"✅ Fuseki: Connected ({len(datasets)} datasets)")
            return True
        else:
            print(f"❌ Fuseki: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Fuseki: {e}")
        return False

def test_minio():
    """Test MinIO connectivity"""
    try:
        response = requests.get("http://localhost:9000/minio/health/live", timeout=5)
        if response.status_code == 200:
            print("✅ MinIO: Connected")
            return True
        else:
            print(f"❌ MinIO: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ MinIO: {e}")
        return False

def main():
    """Test all database connections"""
    print("🔍 Testing ODRAS Database Connectivity...")
    print("=" * 50)
    
    results = []
    results.append(("PostgreSQL", test_postgresql()))
    results.append(("Qdrant", test_qdrant()))
    results.append(("Neo4j", test_neo4j()))
    results.append(("Fuseki", test_fuseki()))
    results.append(("MinIO", test_minio()))
    
    print("\n📊 Summary:")
    print("-" * 30)
    all_connected = True
    for name, connected in results:
        status = "✅ Connected" if connected else "❌ Failed"
        print(f"{name:12} {status}")
        if not connected:
            all_connected = False
    
    if all_connected:
        print("\n🎉 All databases are connected and ready!")
        print("💡 You can now safely use './odras.sh clean' for testing")
    else:
        print("\n⚠️  Some databases are not accessible")
        print("💡 Run './odras.sh up' to start all services first")

if __name__ == "__main__":
    main()

