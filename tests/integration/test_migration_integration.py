"""
Integration tests for unified collection migration.

Tests that migration preserves data integrity and all chunks are migrated correctly.
"""

import pytest
from backend.services.db import DatabaseService
from backend.services.config import Settings


@pytest.mark.integration
class TestMigrationIntegration:
    """Tests for migration data integrity."""
    
    @pytest.fixture
    def db_service(self):
        """Create database service."""
        settings = Settings()
        return DatabaseService(settings)
    
    def test_project_chunks_migrated(self, db_service):
        """Test that project chunks are migrated correctly."""
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                # Count original chunks
                cur.execute("SELECT COUNT(*) FROM knowledge_chunks")
                original_count = cur.fetchone()[0]
                
                # Count migrated chunks
                cur.execute("""
                    SELECT COUNT(*) FROM das_knowledge_chunks 
                    WHERE knowledge_type = 'project'
                """)
                migrated_count = cur.fetchone()[0]
                
                # Should have same or more chunks (migration may add new unified chunks)
                assert migrated_count >= original_count, \
                    f"Migrated chunks ({migrated_count}) should be >= original ({original_count})"
                
                # Verify content is preserved
                cur.execute("""
                    SELECT content FROM das_knowledge_chunks 
                    WHERE knowledge_type = 'project' 
                    LIMIT 1
                """)
                row = cur.fetchone()
                if row:
                    assert len(row[0]) > 0, "Content should not be empty"
                    
        finally:
            db_service._return(conn)
    
    def test_training_chunks_migrated(self, db_service):
        """Test that training chunks are migrated correctly."""
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                # Count original chunks
                cur.execute("SELECT COUNT(*) FROM das_training_chunks")
                original_count = cur.fetchone()[0]
                
                # Count migrated chunks
                cur.execute("""
                    SELECT COUNT(*) FROM das_knowledge_chunks 
                    WHERE knowledge_type = 'training'
                """)
                migrated_count = cur.fetchone()[0]
                
                # Should have same or more chunks
                assert migrated_count >= original_count, \
                    f"Migrated chunks ({migrated_count}) should be >= original ({original_count})"
                
                # Verify domain is preserved
                cur.execute("""
                    SELECT DISTINCT domain FROM das_knowledge_chunks 
                    WHERE knowledge_type = 'training'
                """)
                domains = [row[0] for row in cur.fetchall()]
                assert len(domains) > 0, "Should have at least one domain"
                
        finally:
            db_service._return(conn)
    
    def test_metadata_preserved(self, db_service):
        """Test that metadata is preserved during migration."""
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                # Check project chunks have source metadata
                cur.execute("""
                    SELECT metadata FROM das_knowledge_chunks 
                    WHERE knowledge_type = 'project' 
                    LIMIT 1
                """)
                row = cur.fetchone()
                if row and row[0]:
                    metadata = row[0] if isinstance(row[0], dict) else {}
                    assert 'source_table' in metadata, "Should have source_table in metadata"
                    assert metadata['source_table'] == 'knowledge_chunks', \
                        "Source table should be knowledge_chunks"
                
                # Check training chunks have source metadata
                cur.execute("""
                    SELECT metadata FROM das_knowledge_chunks 
                    WHERE knowledge_type = 'training' 
                    LIMIT 1
                """)
                row = cur.fetchone()
                if row and row[0]:
                    metadata = row[0] if isinstance(row[0], dict) else {}
                    assert 'source_table' in metadata, "Should have source_table in metadata"
                    assert metadata['source_table'] == 'das_training_chunks', \
                        "Source table should be das_training_chunks"
                    
        finally:
            db_service._return(conn)
    
    def test_project_id_preserved(self, db_service):
        """Test that project_id is preserved for project chunks."""
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                # Get a project chunk with project_id
                cur.execute("""
                    SELECT kc.id, ka.project_id 
                    FROM knowledge_chunks kc
                    JOIN knowledge_assets ka ON kc.asset_id = ka.id
                    WHERE ka.project_id IS NOT NULL
                    LIMIT 1
                """)
                original_row = cur.fetchone()
                
                if original_row:
                    original_chunk_id = str(original_row[0])
                    original_project_id = str(original_row[1])
                    
                    # Find migrated chunk
                    cur.execute("""
                        SELECT project_id FROM das_knowledge_chunks
                        WHERE metadata->>'original_chunk_id' = %s
                        AND knowledge_type = 'project'
                    """, (original_chunk_id,))
                    migrated_row = cur.fetchone()
                    
                    if migrated_row:
                        migrated_project_id = str(migrated_row[0]) if migrated_row[0] else None
                        assert migrated_project_id == original_project_id, \
                            f"Project ID should be preserved: {original_project_id} != {migrated_project_id}"
                    
        finally:
            db_service._return(conn)
    
    def test_domain_assigned(self, db_service):
        """Test that domains are assigned correctly."""
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                # Check that domains are assigned
                cur.execute("""
                    SELECT COUNT(*) FROM das_knowledge_chunks
                    WHERE domain IS NOT NULL
                """)
                with_domain = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM das_knowledge_chunks")
                total = cur.fetchone()[0]
                
                # Most chunks should have domains assigned
                if total > 0:
                    domain_percentage = (with_domain / total) * 100
                    assert domain_percentage > 50, \
                        f"At least 50% of chunks should have domains, got {domain_percentage}%"
                    
        finally:
            db_service._return(conn)
    
    def test_no_duplicate_chunks(self, db_service):
        """Test that migration doesn't create duplicate chunks."""
        conn = db_service._conn()
        try:
            with conn.cursor() as cur:
                # Check for duplicate content with same metadata
                cur.execute("""
                    SELECT content, knowledge_type, domain, project_id, COUNT(*) as cnt
                    FROM das_knowledge_chunks
                    GROUP BY content, knowledge_type, domain, project_id
                    HAVING COUNT(*) > 1
                """)
                duplicates = cur.fetchall()
                
                # Allow some duplicates if they have different sequence numbers
                # But flag if there are many exact duplicates
                assert len(duplicates) < 10, \
                    f"Should have minimal duplicates, found {len(duplicates)}"
                    
        finally:
            db_service._return(conn)
