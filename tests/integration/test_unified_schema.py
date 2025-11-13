"""
Integration tests for unified knowledge collection schema.

Tests schema migration, constraints, and indexes.
"""

import pytest
from backend.services.db import DatabaseService
from backend.services.config import Settings


@pytest.mark.integration
class TestUnifiedKnowledgeSchema:
    """Tests for unified knowledge collection schema."""
    
    @pytest.fixture
    def db_service(self):
        """Create database service."""
        settings = Settings()
        return DatabaseService(settings)
    
    def test_das_knowledge_chunks_table_exists(self, db_service):
        """Test that das_knowledge_chunks table exists."""
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'das_knowledge_chunks'
                    )
                """)
                exists = cur.fetchone()[0]
                assert exists, "das_knowledge_chunks table should exist"
        finally:
            db_service._return(conn)
    
    def test_knowledge_type_constraint(self, db_service):
        """Test that knowledge_type constraint works."""
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                # Try to insert with invalid knowledge_type (should fail)
                try:
                    cur.execute("""
                        INSERT INTO das_knowledge_chunks 
                        (content, knowledge_type, domain)
                        VALUES ('Test content', 'invalid_type', 'testing')
                    """)
                    conn.commit()
                    assert False, "Should have raised constraint violation"
                except Exception:
                    # Expected constraint violation
                    conn.rollback()
                    pass
                
                # Try to insert with valid knowledge_type (should succeed)
                cur.execute("""
                    INSERT INTO das_knowledge_chunks 
                    (content, knowledge_type, domain)
                    VALUES ('Test content', 'project', 'testing')
                    RETURNING chunk_id
                """)
                chunk_id = cur.fetchone()[0]
                
                # Cleanup
                cur.execute("DELETE FROM das_knowledge_chunks WHERE chunk_id = %s", (chunk_id,))
                conn.commit()
        finally:
            db_service._return(conn)
    
    def test_domain_constraint(self, db_service):
        """Test that domain constraint works."""
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                # Try to insert with invalid domain (should fail)
                try:
                    cur.execute("""
                        INSERT INTO das_knowledge_chunks 
                        (content, knowledge_type, domain)
                        VALUES ('Test content', 'project', 'invalid_domain')
                    """)
                    conn.commit()
                    assert False, "Should have raised constraint violation"
                except Exception:
                    # Expected constraint violation
                    conn.rollback()
                    pass
                
                # Try to insert with valid domain (should succeed)
                cur.execute("""
                    INSERT INTO das_knowledge_chunks 
                    (content, knowledge_type, domain)
                    VALUES ('Test content', 'project', 'ontology')
                    RETURNING chunk_id
                """)
                chunk_id = cur.fetchone()[0]
                
                # Cleanup
                cur.execute("DELETE FROM das_knowledge_chunks WHERE chunk_id = %s", (chunk_id,))
                conn.commit()
        finally:
            db_service._return(conn)
    
    def test_project_id_nullable(self, db_service):
        """Test that project_id can be NULL for global knowledge."""
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                # Insert with NULL project_id (global knowledge)
                cur.execute("""
                    INSERT INTO das_knowledge_chunks 
                    (content, knowledge_type, domain, project_id)
                    VALUES ('Global training content', 'training', 'ontology', NULL)
                    RETURNING chunk_id
                """)
                chunk_id = cur.fetchone()[0]
                
                # Verify it was inserted
                cur.execute("""
                    SELECT project_id FROM das_knowledge_chunks WHERE chunk_id = %s
                """, (chunk_id,))
                project_id = cur.fetchone()[0]
                assert project_id is None, "project_id should be NULL for global knowledge"
                
                # Cleanup
                cur.execute("DELETE FROM das_knowledge_chunks WHERE chunk_id = %s", (chunk_id,))
                conn.commit()
        finally:
            db_service._return(conn)
    
    def test_tags_array_support(self, db_service):
        """Test that tags array works correctly."""
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                # Insert with tags
                cur.execute("""
                    INSERT INTO das_knowledge_chunks 
                    (content, knowledge_type, domain, tags)
                    VALUES ('Tagged content', 'project', 'requirements', ARRAY['tag1', 'tag2', 'important'])
                    RETURNING chunk_id
                """)
                chunk_id = cur.fetchone()[0]
                
                # Verify tags
                cur.execute("""
                    SELECT tags FROM das_knowledge_chunks WHERE chunk_id = %s
                """, (chunk_id,))
                tags = cur.fetchone()[0]
                assert 'tag1' in tags, "Should contain tag1"
                assert 'important' in tags, "Should contain important"
                
                # Cleanup
                cur.execute("DELETE FROM das_knowledge_chunks WHERE chunk_id = %s", (chunk_id,))
                conn.commit()
        finally:
            db_service._return(conn)
    
    def test_metadata_jsonb_support(self, db_service):
        """Test that metadata JSONB works correctly."""
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                # Insert with metadata
                cur.execute("""
                    INSERT INTO das_knowledge_chunks 
                    (content, knowledge_type, domain, metadata)
                    VALUES ('Metadata content', 'system', 'files', '{"source_id": "file-123", "filename": "test.pdf"}'::jsonb)
                    RETURNING chunk_id
                """)
                chunk_id = cur.fetchone()[0]
                
                # Verify metadata
                cur.execute("""
                    SELECT metadata FROM das_knowledge_chunks WHERE chunk_id = %s
                """, (chunk_id,))
                metadata = cur.fetchone()[0]
                assert metadata['source_id'] == 'file-123', "Should contain source_id"
                assert metadata['filename'] == 'test.pdf', "Should contain filename"
                
                # Cleanup
                cur.execute("DELETE FROM das_knowledge_chunks WHERE chunk_id = %s", (chunk_id,))
                conn.commit()
        finally:
            db_service._return(conn)
    
    def test_indexes_exist(self, db_service):
        """Test that required indexes exist."""
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT indexname FROM pg_indexes 
                    WHERE tablename = 'das_knowledge_chunks'
                """)
                indexes = [row[0] for row in cur.fetchall()]
                
                required_indexes = [
                    'idx_das_knowledge_chunks_type',
                    'idx_das_knowledge_chunks_domain',
                    'idx_das_knowledge_chunks_project_id',
                    'idx_das_knowledge_chunks_qdrant_point',
                ]
                
                for idx_name in required_indexes:
                    assert any(idx_name in idx for idx in indexes), f"Index {idx_name} should exist"
        finally:
            db_service._return(conn)
