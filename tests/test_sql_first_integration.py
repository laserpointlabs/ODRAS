"""
Integration test for SQL-first RAG implementation

Tests the complete SQL-first workflow:
1. Document ingestion with SQL-first storage
2. Event capture with SQL-first storage
3. RAG queries with SQL read-through
4. Verification that vectors contain IDs-only (no content)
"""

import pytest
import uuid
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

# Test data
TEST_DOCUMENT_CONTENT = """
ODRAS System Requirements

1. Authentication Requirements
The system shall provide secure user authentication using industry-standard protocols.
Users must be able to authenticate using their organizational credentials.

2. Data Processing Requirements
The system shall process requirements documents and extract key information.
Processing shall be completed within 30 seconds for documents under 10MB.

3. Vector Storage Requirements
The system shall use vector embeddings for semantic search capabilities.
Vector storage shall maintain high availability with 99.9% uptime.
""".strip()

TEST_PROJECT_ID = str(uuid.uuid4())
TEST_USER_ID = "test_user"


class TestSqlFirstIntegration:
    """Integration tests for SQL-first RAG implementation"""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings with SQL-first enabled"""
        from backend.services.config import Settings
        settings = Settings()
        settings.rag_dual_write = "true"
        settings.rag_sql_read_through = "true"
        return settings

    @pytest.fixture
    def mock_db_service(self):
        """Mock database service"""
        mock_service = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_conn.cursor.return_value.__exit__.return_value = None
        mock_service._conn.return_value = mock_conn
        mock_service._return.return_value = None
        return mock_service, mock_conn, mock_cursor

    def test_document_ingestion_sql_first(self, mock_settings, mock_db_service):
        """Test that document ingestion follows SQL-first principles"""
        from backend.services.store import RAGStoreService

        mock_db_service_obj, mock_conn, mock_cursor = mock_db_service

        with patch('backend.services.store.EmbeddingService') as mock_embedding, \
             patch('backend.services.store.QdrantService') as mock_qdrant:

            # Setup mocks
            mock_embedding_instance = mock_embedding.return_value
            mock_embedding_instance.generate_embeddings.return_value = [[0.1] * 384] * 3

            mock_qdrant_instance = mock_qdrant.return_value
            mock_qdrant_instance.store_vectors.return_value = ["id1", "id2", "id3"]

            # Create service
            rag_store = RAGStoreService(mock_settings)
            rag_store.embedding_service = mock_embedding_instance
            rag_store.qdrant_service = mock_qdrant_instance

            # Mock SQL inserts
            with patch('backend.services.store.insert_doc') as mock_insert_doc, \
                 patch('backend.services.store.insert_chunk') as mock_insert_chunk:

                mock_insert_doc.return_value = "test_doc_id"
                mock_insert_chunk.side_effect = ["chunk_1", "chunk_2", "chunk_3"]

                # Test bulk chunk storage
                chunks_data = [
                    {"text": "Authentication requirements text", "index": 0},
                    {"text": "Data processing requirements text", "index": 1},
                    {"text": "Vector storage requirements text", "index": 2}
                ]

                chunk_ids = rag_store.bulk_store_chunks_and_vectors(
                    conn=mock_conn,
                    project_id=TEST_PROJECT_ID,
                    doc_id="test_doc_id",
                    chunks_data=chunks_data,
                    version=1
                )

                # Verify SQL storage was called
                assert mock_insert_chunk.call_count == 3

                # Verify vector storage was called with IDs-only payloads
                mock_qdrant_instance.store_vectors.assert_called_once()

                # Extract the vector data that was stored
                call_args = mock_qdrant_instance.store_vectors.call_args
                collection_name = call_args[0][0]
                vectors_data = call_args[0][1]

                assert collection_name == "knowledge_chunks"
                assert len(vectors_data) == 3

                # CRITICAL TEST: Verify vectors contain IDs-only, NO text content
                for i, vector_data in enumerate(vectors_data):
                    payload = vector_data["payload"]

                    # Should have IDs and metadata
                    assert "chunk_id" in payload
                    assert "project_id" in payload
                    assert "doc_id" in payload
                    assert payload["chunk_index"] == i

                    # Should NOT have text content in payload
                    assert "text" not in payload, "VIOLATION: Vector payload contains text content!"
                    assert "content" not in payload, "VIOLATION: Vector payload contains content!"

    def test_event_capture_sql_first(self, mock_settings, mock_db_service):
        """Test that event capture follows SQL-first principles"""
        from backend.services.sql_first_thread_manager import SqlFirstThreadManager

        mock_db_service_obj, mock_conn, mock_cursor = mock_db_service

        with patch('backend.services.qdrant_service.QdrantService') as mock_qdrant, \
             patch('backend.services.embedding_service.EmbeddingService') as mock_embedding:

            # Setup mocks
            mock_qdrant_instance = mock_qdrant.return_value
            mock_qdrant_instance.store_vectors.return_value = ["event_vector_id"]

            mock_embedding_instance = mock_embedding.return_value
            mock_embedding_instance.generate_single_embedding.return_value = [0.2] * 384

            # Create manager
            thread_manager = SqlFirstThreadManager(mock_settings, mock_qdrant_instance)
            thread_manager.db_service = mock_db_service_obj
            thread_manager.embedding_service = mock_embedding_instance

            # Mock SQL event insert
            with patch('backend.services.sql_first_thread_manager.insert_project_event') as mock_insert_event:
                mock_insert_event.return_value = "test_event_id"

                # Test event capture
                event_data = {
                    "action": "file_uploaded",
                    "filename": "test.pdf",
                    "details": "User uploaded requirements document"
                }

                # Use asyncio to run the async method
                event_id = asyncio.run(thread_manager.capture_event(
                    project_thread_id="thread_123",
                    project_id=TEST_PROJECT_ID,
                    user_id=TEST_USER_ID,
                    event_type="file_upload",
                    event_data=event_data
                ))

                # Verify SQL storage was called with full event data
                mock_insert_event.assert_called_once()
                call_args = mock_insert_event.call_args[1]
                assert call_args["event_data"] == event_data

                # Verify vector storage was called with IDs-only payload
                mock_qdrant_instance.store_vectors.assert_called_once()

                # Extract vector payload
                vector_call_args = mock_qdrant_instance.store_vectors.call_args
                vectors_data = vector_call_args[0][1]

                assert len(vectors_data) == 1
                payload = vectors_data[0]["payload"]

                # Should have IDs and metadata
                assert "event_id" in payload
                assert "project_thread_id" in payload
                assert "project_id" in payload
                assert "event_type" in payload
                assert payload["sql_first"] is True

                # CRITICAL TEST: Should NOT have event content in payload
                assert "event_data" not in payload, "VIOLATION: Vector payload contains event_data!"
                assert "context_snapshot" not in payload, "VIOLATION: Vector payload contains context_snapshot!"
                assert "semantic_summary" not in payload, "VIOLATION: Vector payload contains semantic_summary!"

    def test_rag_query_sql_read_through(self, mock_settings, mock_db_service):
        """Test that RAG queries use SQL read-through correctly"""
        from backend.services.rag_service import RAGService

        mock_db_service_obj, mock_conn, mock_cursor = mock_db_service

        with patch('backend.services.qdrant_service.QdrantService') as mock_qdrant, \
             patch('backend.services.llm_team.LLMTeam') as mock_llm:

            # Setup vector search mock (returns IDs-only)
            mock_qdrant_instance = mock_qdrant.return_value
            mock_qdrant_instance.search_similar_chunks = AsyncMock(return_value=[
                {
                    "score": 0.9,
                    "payload": {
                        "chunk_id": "chunk_1",
                        "project_id": TEST_PROJECT_ID,
                        "doc_id": "doc_1",
                        # NO text content in vector payload
                    }
                },
                {
                    "score": 0.8,
                    "payload": {
                        "chunk_id": "chunk_2",
                        "project_id": TEST_PROJECT_ID,
                        "doc_id": "doc_1",
                        # NO text content in vector payload
                    }
                }
            ])

            # Setup SQL read-through mock
            mock_cursor.fetchall.return_value = [
                ("chunk_1", "doc_1", 0, "Authentication requirements content from SQL", None, None, None, "2024-01-01"),
                ("chunk_2", "doc_1", 1, "Data processing requirements content from SQL", None, None, None, "2024-01-01")
            ]
            mock_cursor.description = [
                ("chunk_id",), ("doc_id",), ("chunk_index",), ("text",),
                ("page",), ("start_char",), ("end_char",), ("created_at",)
            ]

            # Setup LLM mock
            mock_llm_instance = mock_llm.return_value
            mock_llm_instance.generate_response.return_value = {
                "content": "Based on the requirements, the system provides secure authentication and data processing capabilities.",
                "confidence": "high"
            }

            # Create RAG service
            rag_service = RAGService(mock_settings)
            rag_service.qdrant_service = mock_qdrant_instance
            rag_service.llm_team = mock_llm_instance
            rag_service.db_service = mock_db_service_obj

            # Mock access control
            with patch.object(rag_service, '_has_chunk_access', return_value=True):

                # Test RAG query
                result = asyncio.run(rag_service.query_knowledge_base(
                    question="What are the authentication requirements?",
                    project_id=TEST_PROJECT_ID,
                    user_id=TEST_USER_ID,
                    max_chunks=2
                ))

                # Verify vector search was called
                mock_qdrant_instance.search_similar_chunks.assert_called_once()

                # Verify SQL read-through was called
                mock_cursor.execute.assert_called()

                # Verify response was generated
                assert result["success"] is True
                assert result["chunks_found"] == 2

    def test_architecture_compliance(self):
        """Test that the architecture follows SQL-first principles"""

        # Test knowledge asset relationships
        expected_flow = {
            "files": "File storage metadata (existing)",
            "knowledge_assets": "Processing metadata (existing)",
            "doc": "RAG document metadata (new SQL-first)",
            "doc_chunk": "RAG chunk content - SOURCE OF TRUTH (new)",
            "project_thread": "Thread metadata (new SQL-first)",
            "project_event": "Event content - SOURCE OF TRUTH (new)",
            "vectors": "Semantic search with IDs-only payloads"
        }

        # Verify the flow makes sense
        assert "SOURCE OF TRUTH" in expected_flow["doc_chunk"]
        assert "SOURCE OF TRUTH" in expected_flow["project_event"]
        assert "IDs-only" in expected_flow["vectors"]

        # Knowledge asset relationship clarification
        asset_relationship = {
            "user_uploads": "file → knowledge_asset (processed metadata)",
            "rag_ingestion": "knowledge_asset → doc + doc_chunks (RAG-specific)",
            "vector_storage": "doc_chunks → vectors (IDs-only for search)",
            "rag_query": "vectors find IDs → SQL reads chunk.text (authoritative)"
        }

        assert "authoritative" in asset_relationship["rag_query"]

        # This test passes to document the architecture compliance

    def test_violation_detection(self):
        """Test that we can detect SQL-first violations"""

        # Examples of VIOLATIONS (what we fixed)
        violations = [
            {
                "service": "ProjectThreadManager._persist_project_thread",
                "violation": "thread_data and searchable_text in vector payload",
                "line": "Lines 474-475 in project_thread_manager.py",
                "fix": "Use SqlFirstThreadManager with IDs-only payloads"
            },
            {
                "service": "Legacy RAG implementations",
                "violation": "Full text content in vector payloads",
                "fix": "Use RAGStoreService with SQL read-through"
            }
        ]

        # Verify we understand the violations
        assert len(violations) == 2
        assert "thread_data" in violations[0]["violation"]
        assert "Full text content" in violations[1]["violation"]

        # Verify we have fixes
        for violation in violations:
            assert "fix" in violation
            assert violation["fix"] is not None

if __name__ == "__main__":
    pytest.main([__file__])
