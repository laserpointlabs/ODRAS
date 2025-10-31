#!/usr/bin/env python3
"""Debug script to check what classes the ontology API returns."""
import httpx
import json

BASE_URL = "http://localhost:8000"
GRAPH_IRI = "https://xma-adt.usnc.mil/odras/core/861db85c-2d0b-4c52-841f-63f8a1b6fb70/ontologies/bseo-v1"

# Login
print("🔐 Logging in...")
response = httpx.post(f"{BASE_URL}/api/auth/login", json={"username": "jdehart", "password": "jdehart123!"})
token = response.json().get("token")
print(f"✅ Logged in, token: {token[:30]}...")

# Get ontology
print(f"\n📚 Fetching ontology: {GRAPH_IRI}")
headers = {"Authorization": f"Bearer {token}"}
resp = httpx.get(f"{BASE_URL}/api/ontology", params={"graph": GRAPH_IRI}, headers=headers, follow_redirects=True)
print(f"   Status: {resp.status_code}")

data = resp.json()
print(f"\n📊 Response structure:")
print(f"   Top-level keys: {list(data.keys())}")

if "data" in data:
    print(f"   Data keys: {list(data['data'].keys())}")
    nodes = data["data"].get("nodes", [])
    print(f"   Number of nodes: {len(nodes)}")
    
    print("\n🎯 Classes found:")
    for i, node in enumerate(nodes[:10]):  # First 10 nodes
        node_data = node.get("data", {})
        if node_data.get("type") == "class":
            print(f"   {i}: label={node_data.get('label')}, id={node_data.get('id')}, name={node_data.get('name')}")

print("\n📝 Full first node example:")
if nodes:
    print(json.dumps(nodes[0], indent=2))


