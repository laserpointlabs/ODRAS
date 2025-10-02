# backend/db/queries.py
"""
SQL helper functions for RAG SQL-first storage

Provides parameterized SQL operations for:
- Document metadata management
- Chunk storage and retrieval
- Chat message history

All functions use parameterized queries to prevent SQL injection.
"""

import uuid
import datetime
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def now_utc() -> datetime.datetime:
    """Return current UTC timestamp"""
    return datetime.datetime.now(datetime.timezone.utc)


def insert_doc(conn, project_id: str, filename: str, version: int, sha256: str) -> str:
    """
    Insert a document record into the doc table.

    Args:
        conn: psycopg2 database connection
        project_id: UUID of the project
        filename: Original filename
        version: Document version (default 1)
        sha256: SHA256 hash of the document

    Returns:
        str: Generated doc_id
    """
    doc_id = str(uuid.uuid4())

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO doc(doc_id, project_id, filename, version, sha256, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (doc_id, project_id, filename, version, sha256, now_utc()))

    conn.commit()
    logger.debug(f"Inserted document {doc_id} for project {project_id}")
    return doc_id


def insert_chunk(conn, doc_id: str, idx: int, text: str,
                page: Optional[int] = None, start: Optional[int] = None,
                end: Optional[int] = None) -> str:
    """
    Insert a document chunk into the doc_chunk table.

    Args:
        conn: psycopg2 database connection
        doc_id: Reference to document
        idx: Chunk sequence number within document
        text: Full text content of the chunk
        page: Optional page number
        start: Optional start character position
        end: Optional end character position

    Returns:
        str: Generated chunk_id
    """
    chunk_id = str(uuid.uuid4())

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO doc_chunk(chunk_id, doc_id, chunk_index, text, page, start_char, end_char, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (chunk_id, doc_id, idx, text, page, start, end, now_utc()))

    conn.commit()
    logger.debug(f"Inserted chunk {chunk_id} (index {idx}) for document {doc_id}")
    return chunk_id


def insert_chat(conn, session_id: str, project_id: str, role: str, content: str) -> str:
    """
    Insert a chat message into the chat_message table.

    Args:
        conn: psycopg2 database connection
        session_id: Chat session identifier
        project_id: Project context for the message
        role: Message role ('user' or 'assistant')
        content: Message content

    Returns:
        str: Generated message_id

    Raises:
        ValueError: If role is not 'user' or 'assistant'
    """
    if role not in ('user', 'assistant'):
        raise ValueError(f"Invalid role '{role}'. Must be 'user' or 'assistant'")

    message_id = str(uuid.uuid4())

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO chat_message(message_id, session_id, project_id, role, content, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (message_id, session_id, project_id, role, content, now_utc()))

    conn.commit()
    logger.debug(f"Inserted {role} message {message_id} in session {session_id}")
    return message_id


def get_chunks_by_ids(conn, chunk_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Retrieve chunks by their IDs with full text content.

    Args:
        conn: psycopg2 database connection
        chunk_ids: List of chunk IDs to retrieve

    Returns:
        List[Dict]: List of chunk records with columns as keys
    """
    if not chunk_ids:
        return []

    with conn.cursor() as cur:
        # Use ANY() for efficient IN-clause with list parameter
        cur.execute("""
            SELECT chunk_id, doc_id, chunk_index, text, page, start_char, end_char, created_at
            FROM doc_chunk
            WHERE chunk_id = ANY(%s)
            ORDER BY doc_id, chunk_index
        """, (chunk_ids,))

        # Convert to list of dictionaries
        cols = [desc[0] for desc in cur.description]
        results = [dict(zip(cols, row)) for row in cur.fetchall()]

    logger.debug(f"Retrieved {len(results)} chunks from {len(chunk_ids)} requested IDs")
    return results


def get_doc_by_id(conn, doc_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve document metadata by ID.

    Args:
        conn: psycopg2 database connection
        doc_id: Document ID to retrieve

    Returns:
        Optional[Dict]: Document record or None if not found
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT doc_id, project_id, filename, version, sha256, created_at
            FROM doc
            WHERE doc_id = %s
        """, (doc_id,))

        row = cur.fetchone()
        if row:
            cols = [desc[0] for desc in cur.description]
            return dict(zip(cols, row))
        return None


def get_chat_messages_by_session(conn, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieve chat messages for a session, ordered by creation time.

    Args:
        conn: psycopg2 database connection
        session_id: Session ID to retrieve messages for
        limit: Maximum number of messages to retrieve

    Returns:
        List[Dict]: List of chat message records
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT message_id, session_id, project_id, role, content, created_at
            FROM chat_message
            WHERE session_id = %s
            ORDER BY created_at ASC
            LIMIT %s
        """, (session_id, limit))

        cols = [desc[0] for desc in cur.description]
        results = [dict(zip(cols, row)) for row in cur.fetchall()]

    logger.debug(f"Retrieved {len(results)} messages for session {session_id}")
    return results


def get_chunks_for_doc(conn, doc_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all chunks for a document, ordered by chunk_index.

    Args:
        conn: psycopg2 database connection
        doc_id: Document ID

    Returns:
        List[Dict]: List of chunk records for the document
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT chunk_id, doc_id, chunk_index, text, page, start_char, end_char, created_at
            FROM doc_chunk
            WHERE doc_id = %s
            ORDER BY chunk_index ASC
        """, (doc_id,))

        cols = [desc[0] for desc in cur.description]
        results = [dict(zip(cols, row)) for row in cur.fetchall()]

    logger.debug(f"Retrieved {len(results)} chunks for document {doc_id}")
    return results


def delete_doc_and_chunks(conn, doc_id: str) -> int:
    """
    Delete a document and all its chunks (CASCADE handled by foreign key).

    Args:
        conn: psycopg2 database connection
        doc_id: Document ID to delete

    Returns:
        int: Number of documents deleted (0 or 1)
    """
    with conn.cursor() as cur:
        cur.execute("DELETE FROM doc WHERE doc_id = %s", (doc_id,))
        deleted_count = cur.rowcount

    conn.commit()
    logger.info(f"Deleted document {doc_id} and its chunks")
    return deleted_count


# Utility functions for statistics and debugging

def get_rag_table_counts(conn) -> Dict[str, int]:
    """
    Get row counts for all RAG tables.

    Args:
        conn: psycopg2 database connection

    Returns:
        Dict[str, int]: Table names mapped to row counts
    """
    counts = {}
    tables = ['doc', 'doc_chunk', 'chat_message']

    with conn.cursor() as cur:
        for table in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cur.fetchone()[0]
            except Exception as e:
                logger.warning(f"Failed to get count for table {table}: {e}")
                counts[table] = -1

    return counts


def get_recent_activity(conn, limit: int = 10) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get recent activity across RAG tables for debugging.

    Args:
        conn: psycopg2 database connection
        limit: Number of recent records per table

    Returns:
        Dict: Recent records by table name
    """
    activity = {}

    with conn.cursor() as cur:
        # Recent documents
        cur.execute("""
            SELECT doc_id, project_id, filename, created_at
            FROM doc
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))
        cols = [desc[0] for desc in cur.description]
        activity['docs'] = [dict(zip(cols, row)) for row in cur.fetchall()]

        # Recent chunks
        cur.execute("""
            SELECT chunk_id, doc_id, chunk_index, LEFT(text, 100) as text_preview, created_at
            FROM doc_chunk
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))
        cols = [desc[0] for desc in cur.description]
        activity['chunks'] = [dict(zip(cols, row)) for row in cur.fetchall()]

        # Recent messages
        cur.execute("""
            SELECT message_id, session_id, project_id, role, LEFT(content, 100) as content_preview, created_at
            FROM chat_message
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))
        cols = [desc[0] for desc in cur.description]
        activity['messages'] = [dict(zip(cols, row)) for row in cur.fetchall()]

    return activity

