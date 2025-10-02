# backend/db/init.py
"""
Database initialization for RAG SQL-first storage

Creates the required tables for SQL-first RAG implementation:
- doc: Document metadata
- doc_chunk: Document chunks with full text
- chat_message: Chat conversation history

These tables complement the existing knowledge management tables and provide
dedicated RAG storage with SQL as the source of truth.
"""

import logging
from typing import Optional
import psycopg2

logger = logging.getLogger(__name__)

# DDL for RAG SQL-first tables
RAG_TABLES_DDL = """
-- RAG SQL-first storage tables
-- These complement existing knowledge management tables

-- Document metadata table
CREATE TABLE IF NOT EXISTS doc (
    doc_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    sha256 TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Document chunks with full text content
CREATE TABLE IF NOT EXISTS doc_chunk (
    chunk_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL REFERENCES doc(doc_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    page INTEGER,
    start_char INTEGER,
    end_char INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Chat message history
CREATE TABLE IF NOT EXISTS chat_message (
    message_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user','assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_doc_chunk_doc ON doc_chunk(doc_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_doc_chunk_doc_id ON doc_chunk(doc_id);
CREATE INDEX IF NOT EXISTS idx_chat_message_session ON chat_message(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_message_project ON chat_message(project_id);
CREATE INDEX IF NOT EXISTS idx_chat_message_created ON chat_message(created_at);

-- Comments for documentation
COMMENT ON TABLE doc IS 'RAG document metadata for SQL-first storage';
COMMENT ON TABLE doc_chunk IS 'RAG document chunks with full text content as source of truth';
COMMENT ON TABLE chat_message IS 'RAG chat conversation history';
COMMENT ON COLUMN doc_chunk.text IS 'Full text content - source of truth for RAG chunks';
COMMENT ON COLUMN chat_message.role IS 'Message role: user or assistant';
"""


def ensure_rag_schema(conn) -> bool:
    """
    Ensure RAG SQL-first tables exist in the database.

    Args:
        conn: psycopg2 database connection

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with conn.cursor() as cur:
            logger.info("Creating RAG SQL-first tables...")
            cur.execute(RAG_TABLES_DDL)
            conn.commit()
            logger.info("✓ RAG SQL-first tables created successfully")
            return True
    except Exception as e:
        logger.error(f"Failed to create RAG SQL-first tables: {e}")
        conn.rollback()
        return False


def ensure_rag_schema_from_settings(settings) -> bool:
    """
    Create RAG tables using database connection from settings.

    Args:
        settings: Application settings with database configuration

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get database connection parameters from settings
        db_params = {
            'host': getattr(settings, 'db_host', 'localhost'),
            'port': getattr(settings, 'db_port', 5432),
            'database': getattr(settings, 'db_name', 'odras'),
            'user': getattr(settings, 'db_user', 'postgres'),
            'password': getattr(settings, 'db_password', 'password'),
        }

        logger.info(f"Connecting to database at {db_params['host']}:{db_params['port']}/{db_params['database']}")

        with psycopg2.connect(**db_params) as conn:
            success = ensure_rag_schema(conn)

            # Also create event tables for SQL-first thread management
            if success:
                try:
                    from backend.db.event_queries import create_event_tables
                    event_success = create_event_tables(conn)
                    if event_success:
                        logger.info("✓ Event tables created successfully")
                    else:
                        logger.warning("⚠ Event tables creation failed")
                        success = False
                except Exception as e:
                    logger.error(f"Failed to create event tables: {e}")
                    success = False

            return success

    except Exception as e:
        logger.error(f"Failed to connect to database for RAG schema creation: {e}")
        return False


def verify_rag_tables(conn) -> dict:
    """
    Verify that RAG tables exist and return basic statistics.

    Args:
        conn: psycopg2 database connection

    Returns:
        dict: Table status and basic counts
    """
    try:
        with conn.cursor() as cur:
            # Check if tables exist
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('doc', 'doc_chunk', 'chat_message')
            """)
            existing_tables = [row[0] for row in cur.fetchall()]

            # Get basic counts
            counts = {}
            for table in ['doc', 'doc_chunk', 'chat_message']:
                if table in existing_tables:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    counts[table] = cur.fetchone()[0]
                else:
                    counts[table] = None  # Table doesn't exist

            return {
                'tables_exist': existing_tables,
                'expected_tables': ['doc', 'doc_chunk', 'chat_message'],
                'all_tables_exist': len(existing_tables) == 3,
                'counts': counts
            }

    except Exception as e:
        logger.error(f"Failed to verify RAG tables: {e}")
        return {
            'tables_exist': [],
            'expected_tables': ['doc', 'doc_chunk', 'chat_message'],
            'all_tables_exist': False,
            'counts': {},
            'error': str(e)
        }
