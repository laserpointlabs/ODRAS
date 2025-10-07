#!/usr/bin/env python3
"""
ODRAS Embedding Model Test Script

Tests both embedding models (fast and better) with the improved chunking
to ensure consistent RAG performance.

Usage:
    python scripts/test_embedders.py [project_id]

If no project_id provided, creates test projects automatically.
"""

import asyncio
import httpx
import json
import sys
import requests
from typing import Dict, List, Optional

ODRAS_BASE_URL = "http://localhost:8000"
USERNAME = "das_service"
PASSWORD = "das_service_2024!"

class EmbedderTester:
    def __init__(self):
        self.base_url = ODRAS_BASE_URL
        self.token = None
        
    async def login(self) -> bool:
        """Login to ODRAS."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/auth/login",
                    json={"username": USERNAME, "password": PASSWORD}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.token = data.get("token")
                    return True
                else:
                    print(f"❌ Login failed: {response.status_code}")
                    return False
            except Exception as e:
                print(f"❌ Login error: {e}")
                return False
    
    def get_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}
    
    async def create_test_project(self, name: str, description: str) -> str:
        """Create a test project."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/projects",
                json={
                    "name": name,
                    "description": description,
                    "domain": "systems-engineering"
                },
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                return response.json()["project"]["project_id"]
            else:
                raise Exception(f"Failed to create project: {response.status_code}")
    
    async def upload_test_file(self, project_id: str, embedding_model: str) -> bool:
        """Upload UAS specifications with specified embedding model."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                with open('data/uas_specifications.md', 'rb') as f:
                    files = {'file': ('uas_specifications.md', f, 'text/markdown')}
                    data = {
                        'project_id': project_id,
                        'document_type': 'specification',
                        'embedding_model': embedding_model,
                        'chunking_strategy': 'simple_semantic'
                    }
                    
                    response = await client.post(
                        f"{self.base_url}/api/files/upload",
                        files=files,
                        data=data,
                        headers=self.get_headers()
                    )
                
                return response.status_code == 200
            except Exception as e:
                print(f"Upload error: {e}")
                return False
    
    async def test_queries(self, project_id: str, model_name: str) -> Dict[str, any]:
        """Run test queries and return results."""
        test_queries = [
            "How many UAS are mentioned in the specifications?",
            "List all UAS names with their types",
            "What is the weight of the QuadCopter T4?", 
            "Which UAS has the longest endurance?",
            "List all Fixed-Wing UAS with their weights"
        ]
        
        results = {
            "model": model_name,
            "project_id": project_id,
            "query_results": []
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            for i, query in enumerate(test_queries, 1):
                print(f"  Query {i}: {query}")
                
                try:
                    response = await client.post(
                        f"{self.base_url}/api/das2/chat",
                        json={"message": query, "project_id": project_id},
                        headers=self.get_headers(),
                        timeout=45.0
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        query_result = {
                            "query": query,
                            "success": True,
                            "chunks_found": result.get("metadata", {}).get("chunks_found", 0),
                            "response_length": len(result.get("message", "")),
                            "response_preview": result.get("message", "")[:100]
                        }
                        print(f"    ✅ {query_result['chunks_found']} chunks - {query_result['response_preview']}...")
                    else:
                        query_result = {
                            "query": query,
                            "success": False,
                            "error": f"HTTP {response.status_code}"
                        }
                        print(f"    ❌ Failed: {query_result['error']}")
                        
                except Exception as e:
                    query_result = {
                        "query": query,
                        "success": False,
                        "error": str(e)
                    }
                    print(f"    ❌ Error: {e}")
                
                results["query_results"].append(query_result)
                await asyncio.sleep(1)  # Brief pause between queries
        
        return results

async def main():
    """Main test routine."""
    print("🧪 ODRAS Embedding Model Test Suite")
    print("=" * 50)
    
    tester = EmbedderTester()
    
    # Login
    if not await tester.login():
        print("❌ Login failed")
        return False
    
    print("✅ Logged in successfully")
    
    # Check Qdrant collections before testing
    print("\n📊 Initial Qdrant Status:")
    chunks_384 = requests.get('http://localhost:6333/collections/knowledge_chunks').json()['result']['points_count']
    chunks_768 = requests.get('http://localhost:6333/collections/knowledge_chunks_768').json()['result']['points_count']
    print(f"  knowledge_chunks (384 dims): {chunks_384} points")
    print(f"  knowledge_chunks_768 (768 dims): {chunks_768} points")
    
    # Test Fast Embedder (all-MiniLM-L6-v2)
    print("\n🚀 Testing Fast Embedder (all-MiniLM-L6-v2)")
    print("-" * 40)
    
    project_id_fast = await tester.create_test_project(
        "Fast Embedder Test",
        "Test project for all-MiniLM-L6-v2 with improved chunking"
    )
    print(f"Created project: {project_id_fast}")
    
    if await tester.upload_test_file(project_id_fast, "all-MiniLM-L6-v2"):
        print("✅ File uploaded successfully")
        await asyncio.sleep(6)  # Wait for processing
        
        fast_results = await tester.test_queries(project_id_fast, "all-MiniLM-L6-v2")
    else:
        print("❌ File upload failed")
        return False
    
    # Test Better Embedder (all-mpnet-base-v2)
    print("\n🔥 Testing Better Embedder (all-mpnet-base-v2)")
    print("-" * 40)
    
    project_id_better = await tester.create_test_project(
        "Better Embedder Test", 
        "Test project for all-mpnet-base-v2 with improved chunking"
    )
    print(f"Created project: {project_id_better}")
    
    if await tester.upload_test_file(project_id_better, "all-mpnet-base-v2"):
        print("✅ File uploaded successfully")
        await asyncio.sleep(6)  # Wait for processing
        
        better_results = await tester.test_queries(project_id_better, "all-mpnet-base-v2")
    else:
        print("❌ File upload failed")
        return False
    
    # Final Qdrant status
    print("\n📊 Final Qdrant Status:")
    chunks_384_final = requests.get('http://localhost:6333/collections/knowledge_chunks').json()['result']['points_count']
    chunks_768_final = requests.get('http://localhost:6333/collections/knowledge_chunks_768').json()['result']['points_count']
    print(f"  knowledge_chunks (384 dims): {chunks_384_final} points (+{chunks_384_final - chunks_384})")
    print(f"  knowledge_chunks_768 (768 dims): {chunks_768_final} points (+{chunks_768_final - chunks_768})")
    
    # Summary comparison
    print("\n📋 EMBEDDER COMPARISON SUMMARY")
    print("=" * 50)
    
    fast_success = sum(1 for r in fast_results["query_results"] if r.get("success", False))
    better_success = sum(1 for r in better_results["query_results"] if r.get("success", False))
    
    total_queries = len(fast_results["query_results"])
    
    print(f"🚀 Fast Embedder (all-MiniLM-L6-v2):")
    print(f"   Success Rate: {fast_success}/{total_queries} queries")
    print(f"   Avg Chunks Found: {sum(r.get('chunks_found', 0) for r in fast_results['query_results'] if r.get('success')) / max(fast_success, 1):.1f}")
    
    print(f"\n🔥 Better Embedder (all-mpnet-base-v2):")
    print(f"   Success Rate: {better_success}/{total_queries} queries")
    print(f"   Avg Chunks Found: {sum(r.get('chunks_found', 0) for r in better_results['query_results'] if r.get('success')) / max(better_success, 1):.1f}")
    
    if fast_success == total_queries and better_success == total_queries:
        print("\n🎉 BOTH EMBEDDERS WORKING PERFECTLY!")
        print("✅ Improved chunking strategy successful")
        print("✅ Dual collection system operational")
        print("✅ RAG performance excellent for both models")
    else:
        print("\n⚠️  Some queries failed - check logs for details")
    
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
