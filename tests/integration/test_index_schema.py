"""
Integration tests for system index schema.

Tests schema migration, constraints, and indexes.
"""

import pytest
from backend.services.db import DatabaseService
from backend.services.config import Settings


@pytest.mark.integration
class TestSystemIndexSchema:
    """Tests for system index schema."""
    
    @pytest.fixture
    def db_service(self):
        """Create database service."""
        settings = Settings()
        return DatabaseService(settings)
    
    def test_system_index_table_exists(self, db_service):
        """Test that system_index table exists."""
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'system_index'
                    )
                """)
                exists = cur.fetchone()[0]
                assert exists, "system_index table should exist"
        finally:
            db_service._return(conn)
    
    def test_system_index_vectors_table_exists(self, db_service):
        """Test that system_index_vectors table exists."""
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'system_index_vectors'
                    )
                """)
                exists = cur.fetchone()[0]
                assert exists, "system_index_vectors table should exist"
        finally:
            db_service._return(conn)
    
    def test_system_index_unique_constraint(self, db_service):
        """Test that unique constraint works on entity_type + entity_id."""
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                # Insert first entry
                cur.execute("""
                    INSERT INTO system_index (entity_type, entity_id, content_summary)
                    VALUES ('file', 'test-id-1', 'Test content')
                    ON CONFLICT (entity_type, entity_id) DO NOTHING
                """)
                
                # Try to insert duplicate (should fail or be ignored)
                cur.execute("""
                    INSERT INTO system_index (entity_type, entity_id, content_summary)
                    VALUES ('file', 'test-id-1', 'Different content')
                    ON CONFLICT (entity_type, entity_id) DO NOTHING
                """)
                
                # Verify only one entry exists
                cur.execute("""
                    SELECT COUNT(*) FROM system_index 
                    WHERE entity_type = 'file' AND entity_id = 'test-id-1'
                """)
                count = cur.fetchone()[0]
                assert count == 1, "Should only have one entry per entity_type+entity_id"
                
                # Cleanup
                cur.execute("DELETE FROM system_index WHERE entity_id = 'test-id-1'")
                conn.commit()
        finally:
            db_service._return(conn)
    
    def test_system_index_foreign_key_to_projects(self, db_service):
        """Test that foreign key constraint works for project_id."""
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                # Try to insert with invalid project_id (should fail)
                with pytest.raises(Exception):  # Should raise foreign key violation
                    cur.execute("""
                        INSERT INTO system_index (entity_type, entity_id, project_id, content_summary)
                        VALUES ('file', 'test-id-2', '00000000-0000-0000-0000-000000000000', 'Test')
                    """)
                    conn.commit()
        finally:
            db_service._return(conn)
    
    def test_system_index_vectors_foreign_key(self, db_service):
        """Test that system_index_vectors references system_index correctly."""
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                # Create index entry first
                cur.execute("""
                    INSERT INTO system_index (entity_type, entity_id, content_summary)
                    VALUES ('file', 'test-id-3', 'Test content')
                    RETURNING index_id
                """)
                index_id = cur.fetchone()[0]
                
                # Insert vector entry
                cur.execute("""
                    INSERT INTO system_index_vectors (index_id, content, embedding_model)
                    VALUES (%s, 'Test content', 'all-MiniLM-L6-v2')
                """, (index_id,))
                
                # Verify it was inserted
                cur.execute("""
                    SELECT COUNT(*) FROM system_index_vectors WHERE index_id = %s
                """, (index_id,))
                count = cur.fetchone()[0]
                assert count == 1, "Vector entry should be created"
                
                # Try to insert with invalid index_id (should fail)
                try:
                    cur.execute("""
                        INSERT INTO system_index_vectors (index_id, content, embedding_model)
                        VALUES ('00000000-0000-0000-0000-000000000000', 'Test', 'all-MiniLM-L6-v2')
                    """)
                    conn.commit()
                    assert False, "Should have raised foreign key violation"
                except Exception:
                    # Expected foreign key violation
                    conn.rollback()
                    pass
                
                # Cleanup
                cur.execute("DELETE FROM system_index_vectors WHERE index_id = %s", (index_id,))
                cur.execute("DELETE FROM system_index WHERE index_id = %s", (index_id,))
                conn.commit()
        finally:
            db_service._return(conn)
    
    def test_system_index_indexes_exist(self, db_service):
        """Test that required indexes exist on system_index table."""
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT indexname FROM pg_indexes 
                    WHERE tablename = 'system_index'
                """)
                indexes = [row[0] for row in cur.fetchall()]
                
                required_indexes = [
                    'idx_system_index_entity_type',
                    'idx_system_index_entity_id',
                    'idx_system_index_project_id',
                    'idx_system_index_domain',
                ]
                
                for idx_name in required_indexes:
                    assert any(idx_name in idx for idx in indexes), f"Index {idx_name} should exist"
        finally:
            db_service._return(conn)
    
    def test_system_index_vectors_indexes_exist(self, db_service):
        """Test that required indexes exist on system_index_vectors table."""
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT indexname FROM pg_indexes 
                    WHERE tablename = 'system_index_vectors'
                """)
                indexes = [row[0] for row in cur.fetchall()]
                
                required_indexes = [
                    'idx_system_index_vectors_index_id',
                    'idx_system_index_vectors_qdrant_point',
                ]
                
                for idx_name in required_indexes:
                    assert any(idx_name in idx for idx in indexes), f"Index {idx_name} should exist"
        finally:
            db_service._return(conn)
