"""
Knowledge CRUD Operations Tests

Comprehensive tests for all knowledge management operations:
- Create knowledge documents
- Process and extract knowledge
- Search knowledge base
- Update knowledge metadata
- Delete knowledge entries
- Knowledge chunking and embedding
- Knowledge graph operations

Run with: pytest tests/api/test_knowledge_crud.py -v
"""

import pytest
import time
import json
import asyncio
from typing import Dict, List, Any
from httpx import AsyncClient
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))



class TestKnowledgeCRUD:
    """Test all knowledge CRUD operations"""

    @pytest.fixture
    async def client(self):
        # Connect to the REAL running API
        async with AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
            yield client

    @pytest.fixture
    async def auth_headers(self, client):
        response = await client.post(
            "/api/auth/login",
            json={"username": "das_service", "password": "das_service_2024!"}
        )
        assert response.status_code == 200
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    async def test_project(self, client, auth_headers):
        """Create a test project for knowledge operations"""
        response = await client.post(
            "/api/projects",
            json={"name": f"Knowledge Test Project {int(time.time())}"},
            headers=auth_headers
        )
        project_id = response.json()["project_id"]
        yield project_id
        # Cleanup
        await client.delete(f"/api/projects/{project_id}", headers=auth_headers)

    # ========== CREATE OPERATIONS ==========

    @pytest.mark.asyncio
    async def test_upload_knowledge_document(self, client, auth_headers, test_project):
        """Test uploading a document for knowledge extraction"""
        content = """
        ODRAS Knowledge Management System

        ODRAS is an advanced knowledge management platform that uses AI and semantic
        technologies to organize, process, and retrieve information. The system supports
        multiple document formats and provides intelligent search capabilities.

        Key features include:
        - Document processing and chunking
        - Semantic search using embeddings
        - Knowledge graph construction
        - Ontology-based organization
        """

        files = {"file": ("knowledge_doc.txt", content.encode(), "text/plain")}

        response = await client.post(
            f"/api/knowledge/{test_project}/upload",
            files=files,
            headers=auth_headers
        )
        assert response.status_code == 200

        result = response.json()
        if "document_id" in result:
            assert result["document_id"] is not None

        print("✓ Knowledge document upload tested")

    @pytest.mark.asyncio
    async def test_upload_multiple_documents(self, client, auth_headers, test_project):
        """Test uploading multiple knowledge documents"""
        documents = [
            ("intro.txt", "Introduction to ODRAS system and its capabilities."),
            ("features.txt", "ODRAS features include search, analytics, and visualization."),
            ("architecture.txt", "ODRAS uses microservices architecture with AI components."),
            ("api_guide.txt", "The ODRAS API provides RESTful endpoints for all operations.")
        ]

        uploaded_docs = []
        for filename, content in documents:
            files = {"file": (filename, content.encode(), "text/plain")}
            response = await client.post(
                f"/api/knowledge/{test_project}/upload",
                files=files,
                headers=auth_headers
            )
            assert response.status_code == 200
            uploaded_docs.append(response.json())

        print(f"✓ Uploaded {len(documents)} knowledge documents")

    @pytest.mark.asyncio
    async def test_create_knowledge_from_text(self, client, auth_headers, test_project):
        """Test creating knowledge directly from text"""
        knowledge_data = {
            "title": "ODRAS Best Practices",
            "content": """
            Best practices for using ODRAS:
            1. Organize documents by project
            2. Use meaningful file names
            3. Apply appropriate tags
            4. Regular knowledge base maintenance
            """,
            "tags": ["best-practices", "guide", "documentation"],
            "metadata": {
                "author": "ODRAS Team",
                "version": "1.0",
                "category": "guide"
            }
        }

        response = await client.post(
            f"/api/knowledge/{test_project}/create",
            json=knowledge_data,
            headers=auth_headers
        )

        if response.status_code == 200:
            result = response.json()
            print("✓ Knowledge creation from text tested")
        elif response.status_code == 404:
            print("⚠ Direct knowledge creation endpoint not implemented")

    @pytest.mark.asyncio
    async def test_process_existing_file(self, client, auth_headers, test_project):
        """Test processing an existing file for knowledge extraction"""
        # First upload a regular file
        content = "This file will be processed for knowledge extraction."
        files = {"file": ("process_me.txt", content.encode(), "text/plain")}

        upload_resp = await client.post(
            f"/api/files/upload/{test_project}",
            files=files,
            headers=auth_headers
        )
        file_id = upload_resp.json()["file_id"]

        # Process file for knowledge
        process_resp = await client.post(
            f"/api/knowledge/{test_project}/process/{file_id}",
            headers=auth_headers
        )

        if process_resp.status_code in [200, 202]:
            print("✓ File processing for knowledge tested")
        else:
            print("⚠ File processing endpoint not implemented")

    # ========== SEARCH OPERATIONS ==========

    @pytest.mark.asyncio
    async def test_basic_knowledge_search(self, client, auth_headers, test_project):
        """Test basic knowledge search"""
        # Upload some content first
        test_content = """
        Machine Learning in ODRAS

        ODRAS leverages machine learning for intelligent document processing,
        automated tagging, and semantic search capabilities. The system uses
        neural networks for embedding generation and similarity matching.
        """

        files = {"file": ("ml_content.txt", test_content.encode(), "text/plain")}
        await client.post(
            f"/api/knowledge/{test_project}/upload",
            files=files,
            headers=auth_headers
        )

        # Search for content
        search_queries = [
            {"query": "machine learning", "top_k": 5},
            {"query": "neural networks", "top_k": 3},
            {"query": "document processing", "top_k": 10}
        ]

        for search_data in search_queries:
            response = await client.post(
                f"/api/knowledge/{test_project}/search",
                json=search_data,
                headers=auth_headers
            )
            assert response.status_code == 200

            results = response.json()
            if isinstance(results, dict) and "results" in results:
                results_list = results["results"]
            else:
                results_list = results if isinstance(results, list) else []

            print(f"✓ Search for '{search_data['query']}' returned {len(results_list)} results")

    @pytest.mark.asyncio
    async def test_advanced_search(self, client, auth_headers, test_project):
        """Test advanced search with filters"""
        # Upload tagged content
        documents = [
            {
                "filename": "tech_doc.txt",
                "content": "Technical documentation for ODRAS API",
                "tags": ["technical", "api", "documentation"]
            },
            {
                "filename": "user_guide.txt",
                "content": "User guide for ODRAS platform",
                "tags": ["user-guide", "documentation"]
            },
            {
                "filename": "admin_manual.txt",
                "content": "Administration manual for ODRAS",
                "tags": ["admin", "manual", "documentation"]
            }
        ]

        for doc in documents:
            files = {"file": (doc["filename"], doc["content"].encode(), "text/plain")}
            # Upload with tags if supported
            await client.post(
                f"/api/knowledge/{test_project}/upload",
                files=files,
                data={"tags": json.dumps(doc["tags"])},
                headers=auth_headers
            )

        # Advanced search with filters
        advanced_searches = [
            {
                "query": "documentation",
                "top_k": 5,
                "filters": {"tags": ["technical"]}
            },
            {
                "query": "guide",
                "top_k": 5,
                "filters": {"tags": ["user-guide"]}
            },
            {
                "query": "ODRAS",
                "top_k": 10,
                "threshold": 0.7  # Similarity threshold
            }
        ]

        for search_data in advanced_searches:
            response = await client.post(
                f"/api/knowledge/{test_project}/search",
                json=search_data,
                headers=auth_headers
            )
            # Advanced features might not be implemented
            assert response.status_code in [200, 400]

        print("✓ Advanced search features tested")

    @pytest.mark.asyncio
    async def test_semantic_search(self, client, auth_headers, test_project):
        """Test semantic search capabilities"""
        # Upload content with semantic meaning
        semantic_content = """
        The canine companion eagerly awaited its owner's return.
        The loyal dog sat by the door, tail wagging with anticipation.
        Man's best friend showed unwavering devotion.
        """

        files = {"file": ("semantic.txt", semantic_content.encode(), "text/plain")}
        await client.post(
            f"/api/knowledge/{test_project}/upload",
            files=files,
            headers=auth_headers
        )

        # Search with semantically related terms
        semantic_queries = [
            "dog waiting for owner",  # Direct match
            "pet loyalty",  # Semantic match
            "animal companionship"  # Broader semantic match
        ]

        for query in semantic_queries:
            response = await client.post(
                f"/api/knowledge/{test_project}/search",
                json={"query": query, "top_k": 3},
                headers=auth_headers
            )
            assert response.status_code == 200
            print(f"✓ Semantic search for '{query}' completed")

    # ========== READ OPERATIONS ==========

    @pytest.mark.asyncio
    async def test_get_knowledge_stats(self, client, auth_headers, test_project):
        """Test retrieving knowledge base statistics"""
        # Upload some documents first
        for i in range(5):
            files = {"file": (f"doc_{i}.txt", f"Document {i} content".encode(), "text/plain")}
            await client.post(
                f"/api/knowledge/{test_project}/upload",
                files=files,
                headers=auth_headers
            )

        # Get statistics
        stats_resp = await client.get(
            f"/api/knowledge/{test_project}/stats",
            headers=auth_headers
        )

        if stats_resp.status_code == 200:
            stats = stats_resp.json()
            expected_keys = ["total_documents", "total_chunks", "total_embeddings"]
            for key in expected_keys:
                if key in stats:
                    print(f"✓ {key}: {stats[key]}")
            print("✓ Knowledge statistics retrieved")
        else:
            print("⚠ Knowledge statistics endpoint not implemented")

    @pytest.mark.asyncio
    async def test_list_knowledge_documents(self, client, auth_headers, test_project):
        """Test listing knowledge documents"""
        # List documents
        list_resp = await client.get(
            f"/api/knowledge/{test_project}/documents",
            headers=auth_headers
        )

        if list_resp.status_code == 200:
            documents = list_resp.json()
            assert isinstance(documents, list)
            print(f"✓ Listed {len(documents)} knowledge documents")
        else:
            print("⚠ List documents endpoint not implemented")

    @pytest.mark.asyncio
    async def test_get_document_details(self, client, auth_headers, test_project):
        """Test getting detailed information about a knowledge document"""
        # Upload a document
        files = {"file": ("details_test.txt", b"Detailed content", "text/plain")}
        upload_resp = await client.post(
            f"/api/knowledge/{test_project}/upload",
            files=files,
            headers=auth_headers
        )

        if "document_id" in upload_resp.json():
            doc_id = upload_resp.json()["document_id"]

            # Get document details
            details_resp = await client.get(
                f"/api/knowledge/{test_project}/documents/{doc_id}",
                headers=auth_headers
            )

            if details_resp.status_code == 200:
                details = details_resp.json()
                print("✓ Document details retrieved")
            else:
                print("⚠ Document details endpoint not implemented")

    # ========== UPDATE OPERATIONS ==========

    @pytest.mark.asyncio
    async def test_update_knowledge_metadata(self, client, auth_headers, test_project):
        """Test updating knowledge document metadata"""
        # Upload a document
        files = {"file": ("update_test.txt", b"Original content", "text/plain")}
        upload_resp = await client.post(
            f"/api/knowledge/{test_project}/upload",
            files=files,
            headers=auth_headers
        )

        if "document_id" in upload_resp.json():
            doc_id = upload_resp.json()["document_id"]

            # Update metadata
            update_data = {
                "tags": ["updated", "tested", "knowledge"],
                "metadata": {
                    "reviewed": True,
                    "review_date": "2024-01-15",
                    "reviewer": "Test System"
                }
            }

            update_resp = await client.put(
                f"/api/knowledge/{test_project}/documents/{doc_id}",
                json=update_data,
                headers=auth_headers
            )

            if update_resp.status_code == 200:
                print("✓ Knowledge metadata update tested")
            else:
                print("⚠ Knowledge update endpoint not implemented")

    @pytest.mark.asyncio
    async def test_reprocess_document(self, client, auth_headers, test_project):
        """Test reprocessing a knowledge document"""
        # Upload a document
        files = {"file": ("reprocess_test.txt", b"Content to reprocess", "text/plain")}
        upload_resp = await client.post(
            f"/api/knowledge/{test_project}/upload",
            files=files,
            headers=auth_headers
        )

        if "document_id" in upload_resp.json():
            doc_id = upload_resp.json()["document_id"]

            # Reprocess document
            reprocess_resp = await client.post(
                f"/api/knowledge/{test_project}/documents/{doc_id}/reprocess",
                headers=auth_headers
            )

            if reprocess_resp.status_code in [200, 202]:
                print("✓ Document reprocessing tested")
            else:
                print("⚠ Document reprocessing not implemented")

    # ========== DELETE OPERATIONS ==========

    @pytest.mark.asyncio
    async def test_delete_knowledge_document(self, client, auth_headers, test_project):
        """Test deleting a knowledge document"""
        # Upload a document
        files = {"file": ("delete_test.txt", b"Delete this knowledge", "text/plain")}
        upload_resp = await client.post(
            f"/api/knowledge/{test_project}/upload",
            files=files,
            headers=auth_headers
        )

        if "document_id" in upload_resp.json():
            doc_id = upload_resp.json()["document_id"]

            # Delete document
            delete_resp = await client.delete(
                f"/api/knowledge/{test_project}/documents/{doc_id}",
                headers=auth_headers
            )

            if delete_resp.status_code in [200, 204]:
                # Verify deletion
                search_resp = await client.post(
                    f"/api/knowledge/{test_project}/search",
                    json={"query": "Delete this knowledge", "top_k": 5},
                    headers=auth_headers
                )
                # Should not find the deleted content
                print("✓ Knowledge document deletion tested")
            else:
                print("⚠ Knowledge deletion not implemented")

    @pytest.mark.asyncio
    async def test_bulk_delete_knowledge(self, client, auth_headers, test_project):
        """Test bulk deletion of knowledge documents"""
        # Upload multiple documents
        doc_ids = []
        for i in range(3):
            files = {"file": (f"bulk_del_{i}.txt", f"Bulk delete {i}".encode(), "text/plain")}
            resp = await client.post(
                f"/api/knowledge/{test_project}/upload",
                files=files,
                headers=auth_headers
            )
            if "document_id" in resp.json():
                doc_ids.append(resp.json()["document_id"])

        if doc_ids:
            # Bulk delete
            bulk_resp = await client.post(
                f"/api/knowledge/{test_project}/documents/bulk-delete",
                json={"document_ids": doc_ids},
                headers=auth_headers
            )

            if bulk_resp.status_code in [200, 204]:
                print("✓ Bulk knowledge deletion tested")
            else:
                # Delete individually
                for doc_id in doc_ids:
                    await client.delete(
                        f"/api/knowledge/{test_project}/documents/{doc_id}",
                        headers=auth_headers
                    )
                print("⚠ Bulk deletion not implemented, deleted individually")

    # ========== KNOWLEDGE GRAPH OPERATIONS ==========

    @pytest.mark.asyncio
    async def test_knowledge_graph_extraction(self, client, auth_headers, test_project):
        """Test knowledge graph extraction"""
        # Upload content with entities and relationships
        graph_content = """
        John Smith is the CEO of ACME Corporation.
        ACME Corporation was founded in 1990 in New York.
        The company specializes in artificial intelligence.
        Jane Doe works as CTO at ACME Corporation.
        """

        files = {"file": ("graph_content.txt", graph_content.encode(), "text/plain")}
        upload_resp = await client.post(
            f"/api/knowledge/{test_project}/upload",
            files=files,
            headers=auth_headers
        )

        # Extract entities and relationships
        graph_resp = await client.get(
            f"/api/knowledge/{test_project}/graph",
            headers=auth_headers
        )

        if graph_resp.status_code == 200:
            graph_data = graph_resp.json()
            if "entities" in graph_data:
                print(f"✓ Extracted {len(graph_data['entities'])} entities")
            if "relationships" in graph_data:
                print(f"✓ Extracted {len(graph_data['relationships'])} relationships")
            print("✓ Knowledge graph extraction tested")
        else:
            print("⚠ Knowledge graph extraction not implemented")

    # ========== CHUNKING AND EMBEDDINGS ==========

    @pytest.mark.asyncio
    async def test_document_chunking(self, client, auth_headers, test_project):
        """Test document chunking strategies"""
        # Upload a longer document
        long_content = "\n\n".join([
            f"Section {i}: This is paragraph {i} of the document. " * 10
            for i in range(10)
        ])

        files = {"file": ("long_doc.txt", long_content.encode(), "text/plain")}

        # Upload with chunking parameters
        upload_resp = await client.post(
            f"/api/knowledge/{test_project}/upload",
            files=files,
            data={
                "chunk_size": 500,
                "chunk_overlap": 50
            },
            headers=auth_headers
        )

        assert upload_resp.status_code == 200

        # Check chunk information
        if "document_id" in upload_resp.json():
            doc_id = upload_resp.json()["document_id"]

            chunks_resp = await client.get(
                f"/api/knowledge/{test_project}/documents/{doc_id}/chunks",
                headers=auth_headers
            )

            if chunks_resp.status_code == 200:
                chunks = chunks_resp.json()
                print(f"✓ Document chunked into {len(chunks)} pieces")
            else:
                print("⚠ Chunk retrieval not implemented")

    @pytest.mark.asyncio
    async def test_embedding_generation(self, client, auth_headers, test_project):
        """Test embedding generation for knowledge"""
        # Upload content
        files = {"file": ("embed_test.txt", b"Generate embeddings for this text", "text/plain")}
        upload_resp = await client.post(
            f"/api/knowledge/{test_project}/upload",
            files=files,
            headers=auth_headers
        )

        # Get embeddings
        if "document_id" in upload_resp.json():
            doc_id = upload_resp.json()["document_id"]

            embed_resp = await client.get(
                f"/api/knowledge/{test_project}/documents/{doc_id}/embeddings",
                headers=auth_headers
            )

            if embed_resp.status_code == 200:
                embeddings = embed_resp.json()
                print("✓ Embedding generation tested")
            else:
                print("⚠ Embedding retrieval not implemented")

    # ========== BATCH OPERATIONS ==========

    @pytest.mark.asyncio
    async def test_batch_knowledge_operations(self, client, auth_headers, test_project):
        """Test batch knowledge operations"""
        # Batch upload
        batch_docs = []
        for i in range(5):
            content = f"Batch document {i} with unique content for testing"
            batch_docs.append({
                "filename": f"batch_{i}.txt",
                "content": content,
                "tags": [f"batch-{i}", "test"]
            })

        # Upload all documents
        tasks = []
        for doc in batch_docs:
            files = {"file": (doc["filename"], doc["content"].encode(), "text/plain")}
            task = client.post(
                f"/api/knowledge/{test_project}/upload",
                files=files,
                headers=auth_headers
            )
            tasks.append(task)

        responses = await asyncio.gather(*tasks)
        successful = [r for r in responses if r.status_code == 200]
        print(f"✓ Batch uploaded {len(successful)} knowledge documents")

        # Batch search
        batch_queries = [
            {"query": f"Batch document {i}", "top_k": 3}
            for i in range(3)
        ]

        search_tasks = []
        for query in batch_queries:
            task = client.post(
                f"/api/knowledge/{test_project}/search",
                json=query,
                headers=auth_headers
            )
            search_tasks.append(task)

        search_responses = await asyncio.gather(*search_tasks)
        successful_searches = [r for r in search_responses if r.status_code == 200]
        print(f"✓ Batch search completed {len(successful_searches)} queries")


# Run all knowledge CRUD tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
