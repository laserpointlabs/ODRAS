# backend/db/event_queries_fixed.py
"""
SQL-first event storage for project threads and user activities - FIXED VERSION

Extends the RAG SQL-first approach to events and project threads:
- Events stored in SQL as source of truth
- Vector search with IDs-only payloads
- Read-through pattern for event content
- FIXED: Proper JSON/JSONB handling for PostgreSQL
"""

import uuid
import datetime
import logging
from typing import List, Dict, Any, Optional
import json

logger = logging.getLogger(__name__)


def now_utc() -> datetime.datetime:
    """Return current UTC timestamp"""
    return datetime.datetime.now(datetime.timezone.utc)


def create_event_tables(conn) -> bool:
    """
    Create event storage tables following SQL-first RAG pattern.

    These complement the existing RAG tables (doc, doc_chunk, chat_message)
    with dedicated event storage.
    """
    try:
        with conn.cursor() as cur:
            # Project threads table (metadata only)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS project_thread (
                    project_thread_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    last_activity TIMESTAMPTZ DEFAULT NOW(),
                    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived', 'completed')),
                    goals TEXT,
                    current_workbench TEXT
                );
            """)

            # Individual project events (SQL source of truth)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS project_event (
                    event_id TEXT PRIMARY KEY,
                    project_thread_id TEXT NOT NULL REFERENCES project_thread(project_thread_id) ON DELETE CASCADE,
                    project_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_data JSONB NOT NULL DEFAULT '{}',
                    context_snapshot JSONB DEFAULT '{}',
                    semantic_summary TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)

            # Conversation messages (separate from events)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS thread_conversation (
                    conversation_id TEXT PRIMARY KEY,
                    project_thread_id TEXT NOT NULL REFERENCES project_thread(project_thread_id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
                    content TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)

            # Indexes for performance
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_project_thread_project ON project_thread(project_id);
                CREATE INDEX IF NOT EXISTS idx_project_thread_created_by ON project_thread(created_by);
                CREATE INDEX IF NOT EXISTS idx_project_thread_status ON project_thread(status);

                CREATE INDEX IF NOT EXISTS idx_project_event_thread ON project_event(project_thread_id);
                CREATE INDEX IF NOT EXISTS idx_project_event_project ON project_event(project_id);
                CREATE INDEX IF NOT EXISTS idx_project_event_type ON project_event(event_type);
                CREATE INDEX IF NOT EXISTS idx_project_event_created ON project_event(created_at);

                CREATE INDEX IF NOT EXISTS idx_thread_conversation_thread ON thread_conversation(project_thread_id);
                CREATE INDEX IF NOT EXISTS idx_thread_conversation_role ON thread_conversation(role);
                CREATE INDEX IF NOT EXISTS idx_thread_conversation_created ON thread_conversation(created_at);
            """)

            # Comments for documentation
            cur.execute("""
                COMMENT ON TABLE project_thread IS 'SQL-first project thread metadata - no full text content';
                COMMENT ON TABLE project_event IS 'Individual project events as source of truth for event content';
                COMMENT ON TABLE thread_conversation IS 'Conversation messages separate from project events';
                COMMENT ON COLUMN project_event.event_data IS 'Full event data stored in SQL, not vectors';
                COMMENT ON COLUMN project_event.semantic_summary IS 'Optional semantic summary for embedding';
            """)

        conn.commit()
        logger.info("Successfully created SQL-first event tables")
        return True

    except Exception as e:
        logger.error(f"Failed to create event tables: {e}")
        conn.rollback()
        return False


def insert_project_thread(conn, project_id: str, created_by: str, goals: Optional[str] = None) -> str:
    """Create a new project thread record"""
    project_thread_id = str(uuid.uuid4())

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO project_thread(project_thread_id, project_id, created_by, created_at, last_activity, goals)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (project_thread_id, project_id, created_by, now_utc(), now_utc(), goals))

    conn.commit()
    logger.debug(f"Created project thread {project_thread_id} for project {project_id}")
    return project_thread_id


def insert_project_event(
    conn,
    project_thread_id: str,
    project_id: str,
    user_id: str,
    event_type: str,
    event_data: Dict[str, Any],
    context_snapshot: Optional[Dict[str, Any]] = None,
    semantic_summary: Optional[str] = None
) -> str:
    """Insert a project event with full data in SQL"""
    event_id = str(uuid.uuid4())

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO project_event(event_id, project_thread_id, project_id, user_id, event_type, event_data, context_snapshot, semantic_summary, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (event_id, project_thread_id, project_id, user_id, event_type,
              json.dumps(event_data), json.dumps(context_snapshot or {}), semantic_summary, now_utc()))

    # Update thread last activity
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE project_thread SET last_activity = %s WHERE project_thread_id = %s
        """, (now_utc(), project_thread_id))

    conn.commit()
    logger.debug(f"Inserted event {event_id} of type {event_type}")
    return event_id


def insert_thread_conversation(
    conn,
    project_thread_id: str,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """Insert conversation message"""
    conversation_id = str(uuid.uuid4())

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO thread_conversation(conversation_id, project_thread_id, role, content, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (conversation_id, project_thread_id, role, content, json.dumps(metadata or {}), now_utc()))

    conn.commit()
    logger.debug(f"Inserted conversation message {conversation_id}")
    return conversation_id


def get_project_thread_by_id(conn, project_thread_id: str) -> Optional[Dict[str, Any]]:
    """Get project thread metadata"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT project_thread_id, project_id, created_by, created_at, last_activity, status, goals, current_workbench
            FROM project_thread
            WHERE project_thread_id = %s
        """, (project_thread_id,))

        row = cur.fetchone()
        if row:
            cols = [desc[0] for desc in cur.description]
            return dict(zip(cols, row))
        return None


def get_project_thread_by_project_id(conn, project_id: str) -> Optional[Dict[str, Any]]:
    """Get active project thread for a project"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT project_thread_id, project_id, created_by, created_at, last_activity, status, goals, current_workbench
            FROM project_thread
            WHERE project_id = %s AND status = 'active'
            ORDER BY last_activity DESC
            LIMIT 1
        """, (project_id,))

        row = cur.fetchone()
        if row:
            cols = [desc[0] for desc in cur.description]
            return dict(zip(cols, row))
        return None


def get_events_by_ids(conn, event_ids: List[str]) -> List[Dict[str, Any]]:
    """Get events by IDs (for SQL read-through after vector search)"""
    if not event_ids:
        return []

    with conn.cursor() as cur:
        cur.execute("""
            SELECT event_id, project_thread_id, project_id, user_id, event_type,
                   event_data, context_snapshot, semantic_summary, created_at
            FROM project_event
            WHERE event_id = ANY(%s)
            ORDER BY created_at DESC
        """, (event_ids,))

        cols = [desc[0] for desc in cur.description]
        results = []
        for row in cur.fetchall():
            event_dict = dict(zip(cols, row))
            # FIXED: Handle JSONB fields properly - psycopg2 returns them as Python objects
            # No JSON parsing needed for JSONB fields!
            results.append(event_dict)

    logger.debug(f"Retrieved {len(results)} events from SQL")
    return results


def get_recent_events(conn, project_thread_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent events for a project thread"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT event_id, project_thread_id, project_id, user_id, event_type,
                   event_data, context_snapshot, semantic_summary, created_at
            FROM project_event
            WHERE project_thread_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (project_thread_id, limit))

        cols = [desc[0] for desc in cur.description]
        results = []
        for row in cur.fetchall():
            event_dict = dict(zip(cols, row))
            # FIXED: Handle JSONB fields properly - psycopg2 returns them as Python objects
            # No JSON parsing needed for JSONB fields!
            results.append(event_dict)

    logger.debug(f"Retrieved {len(results)} recent events for thread {project_thread_id}")
    return results


def get_conversation_history(conn, project_thread_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Get conversation history for a project thread"""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT conversation_id, project_thread_id, role, content, metadata, created_at
            FROM thread_conversation
            WHERE project_thread_id = %s
            ORDER BY created_at ASC
            LIMIT %s
        """, (project_thread_id, limit))

        cols = [desc[0] for desc in cur.description]
        results = []
        for row in cur.fetchall():
            conv_dict = dict(zip(cols, row))
            # FIXED: Handle JSONB fields properly - psycopg2 returns them as Python objects
            # No JSON parsing needed for JSONB fields!
            results.append(conv_dict)

    logger.debug(f"Retrieved {len(results)} conversation messages for thread {project_thread_id}")
    return results

