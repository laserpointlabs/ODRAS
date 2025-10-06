# backend/services/sql_first_thread_manager.py
"""
SQL-first Project Thread Manager

Replaces the existing project thread manager with SQL-first storage:
- Project thread metadata stored in SQL
- Individual events stored in SQL with full content
- Vector search returns event IDs only
- Read-through pattern fetches full event content from SQL

This fixes the violation where thread_data and searchable_text were stored
in vector payloads, breaking SQL-first principles.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from backend.db.event_queries import (
    create_event_tables, insert_project_thread, insert_project_event,
    insert_thread_conversation, get_project_thread_by_id, get_project_thread_by_project_id,
    get_events_by_ids, get_recent_events, get_conversation_history
)
from backend.services.qdrant_service import QdrantService
from backend.services.embedding_service import EmbeddingService
from backend.services.db import DatabaseService

logger = logging.getLogger(__name__)


class SqlFirstThreadManager:
    """
    SQL-first project thread manager that follows RAG SQL-first principles:

    1. SQL stores all thread metadata and event content (source of truth)
    2. Vectors store only embeddings and IDs for semantic search
    3. Read-through pattern fetches content from SQL using vector-found IDs
    """

    def __init__(self, settings, qdrant_service: QdrantService):
        self.settings = settings
        self.qdrant = qdrant_service
        self.db_service = DatabaseService(settings)

        # Collections for different types of vectors
        self.events_collection = "project_threads"  # Use same collection for events (they're all project-related)
        self.threads_collection = "project_threads"  # Project threads and events in same collection

        # Initialize embedding service
        self.embedding_service = EmbeddingService(settings)

        # Ensure event tables exist
        self._ensure_event_tables()

        logger.info("SQL-first Thread Manager initialized")

    def _ensure_event_tables(self):
        """Ensure SQL event tables exist"""
        try:
            conn = self.db_service._conn()
            try:
                create_event_tables(conn)
            finally:
                self.db_service._return(conn)
        except Exception as e:
            logger.error(f"Failed to ensure event tables: {e}")

    async def get_or_create_project_thread(self, project_id: str, user_id: str) -> Dict[str, Any]:
        """Get existing project thread or create new one"""
        try:
            # Check for existing thread
            conn = self.db_service._conn()
            try:
                existing_thread = get_project_thread_by_project_id(conn, project_id)
                if existing_thread:
                    logger.info(f"Found existing thread {existing_thread['project_thread_id']} for project {project_id}")
                    return existing_thread

                # Create new thread in SQL
                print(f"🔍 THREAD_CREATE_DEBUG: Creating project thread in SQL")
                print(f"   Project ID: {project_id}")
                print(f"   User ID: {user_id}")

                project_thread_id = insert_project_thread(
                    conn=conn,
                    project_id=project_id,
                    created_by=user_id
                )
                print(f"✅ THREAD_CREATE_DEBUG: SQL thread created: {project_thread_id[:8]}...")

                # Get the created thread
                thread = get_project_thread_by_id(conn, project_thread_id)
                print(f"✅ THREAD_CREATE_DEBUG: Retrieved thread metadata from SQL")

                # DUAL-WRITE: Create vector for project thread (if enabled)
                dual_write = getattr(self.settings, 'rag_dual_write', 'true').lower() == 'true'
                print(f"🔍 THREAD_CREATE_DEBUG: Dual-write enabled: {dual_write}")

                if dual_write:
                    try:
                        print(f"🔍 THREAD_CREATE_DEBUG: Creating project thread vector...")
                        await self._create_thread_vector(
                            project_thread_id=project_thread_id,
                            project_id=project_id,
                            created_by=user_id,
                            thread_metadata=thread
                        )
                        print(f"✅ THREAD_CREATE_DEBUG: Project thread vector created")
                    except Exception as ve:
                        print(f"❌ THREAD_CREATE_DEBUG: Vector creation failed: {ve}")
                        logger.warning(f"Failed to create project thread vector: {ve}")
                else:
                    print(f"⚠️ THREAD_CREATE_DEBUG: Dual-write disabled, skipping vector")

                logger.info(f"Created new project thread {project_thread_id} for project {project_id}")
                return thread

            finally:
                self.db_service._return(conn)

        except Exception as e:
            logger.error(f"Error getting/creating project thread: {e}")
            raise

    async def capture_event(
        self,
        project_thread_id: str,
        project_id: str,
        user_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        context_snapshot: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Capture project event using SQL-first approach:
        1. Store full event in SQL
        2. Create vector with IDs-only payload for semantic search
        """
        try:
            # Step 1: Store event in SQL (source of truth)
            conn = self.db_service._conn()
            try:
                # Create semantic summary for embedding
                semantic_summary = self._create_event_summary(event_type, event_data)

                event_id = insert_project_event(
                    conn=conn,
                    project_thread_id=project_thread_id,
                    project_id=project_id,
                    user_id=user_id,
                    event_type=event_type,
                    event_data=event_data,
                    context_snapshot=context_snapshot,
                    semantic_summary=semantic_summary
                )

            finally:
                self.db_service._return(conn)

            # Step 2: Create vector with IDs-only payload (if dual-write enabled)
            dual_write = getattr(self.settings, 'rag_dual_write', 'true').lower() == 'true'
            if dual_write:
                await self._create_event_vector(
                    event_id=event_id,
                    project_thread_id=project_thread_id,
                    project_id=project_id,
                    event_type=event_type,
                    semantic_summary=semantic_summary
                )

            logger.debug(f"Captured event {event_id} of type {event_type}")
            return event_id

        except Exception as e:
            logger.error(f"Failed to capture event: {e}")
            raise

    async def _create_thread_vector(
        self,
        project_thread_id: str,
        project_id: str,
        created_by: str,
        thread_metadata: Dict[str, Any]
    ):
        """Create vector for project thread with IDs-only payload"""
        try:
            print(f"🔍 THREAD_VECTOR_DEBUG: Creating thread vector")
            print(f"   Thread ID: {project_thread_id}")
            print(f"   Project ID: {project_id}")

            # Create searchable text for thread (for embedding)
            searchable_text = f"Project thread for project {project_id} created by {created_by}"

            # Add any goals or workbench info
            goals = thread_metadata.get('goals')
            workbench = thread_metadata.get('current_workbench')
            if goals:
                searchable_text += f" with goals: {goals}"
            if workbench:
                searchable_text += f" workbench: {workbench}"

            print(f"🔍 THREAD_VECTOR_DEBUG: Searchable text: {searchable_text}")

            # Generate embedding
            embedding = self.embedding_service.generate_single_embedding(searchable_text)
            print(f"✅ THREAD_VECTOR_DEBUG: Generated embedding - {len(embedding)} dimensions")

            # Vector payload contains ONLY IDs and metadata - NO content
            vector_data = [{
                "id": project_thread_id,
                "vector": embedding,
                "payload": {
                    "project_thread_id": project_thread_id,
                    "project_id": project_id,
                    "created_by": created_by,
                    "item_id": project_thread_id,  # For consistency with project_threads collection
                    "kind": "project_thread",
                    "created_at": datetime.now().isoformat(),
                    "sql_first": True,  # Flag to indicate SQL-first storage
                    # CRITICAL: NO thread metadata, goals, or content in payload - SQL is source of truth
                }
            }]

            print(f"🔍 THREAD_VECTOR_DEBUG: Storing in collection: {self.threads_collection}")
            stored_ids = self.qdrant.store_vectors(self.threads_collection, vector_data)
            print(f"✅ THREAD_VECTOR_DEBUG: Thread vector stored - IDs: {stored_ids}")

        except Exception as e:
            print(f"❌ THREAD_VECTOR_DEBUG: Vector creation failed: {e}")
            logger.error(f"Failed to create thread vector: {e}")
            import traceback
            traceback.print_exc()
            # Don't fail the whole operation if vector storage fails

    async def _create_event_vector(
        self,
        event_id: str,
        project_thread_id: str,
        project_id: str,
        event_type: str,
        semantic_summary: str
    ):
        """Create vector for event with IDs-only payload"""
        try:
            print(f"🔍 EVENT_VECTOR_DEBUG: Creating event vector")
            print(f"   Event ID: {event_id}")
            print(f"   Event type: {event_type}")
            print(f"   Summary: {semantic_summary}")

            # Generate embedding from semantic summary
            embedding = self.embedding_service.generate_single_embedding(semantic_summary)
            print(f"✅ EVENT_VECTOR_DEBUG: Generated embedding - {len(embedding)} dimensions")

            # Vector payload contains ONLY IDs and metadata - NO content
            vector_data = [{
                "id": event_id,
                "vector": embedding,
                "payload": {
                    "event_id": event_id,
                    "project_thread_id": project_thread_id,
                    "project_id": project_id,
                    "event_type": event_type,
                    "created_at": datetime.now().isoformat(),
                    "sql_first": True,  # Flag to indicate SQL-first storage
                    # CRITICAL: NO event_data, context_snapshot, or semantic_summary in payload
                }
            }]

            print(f"🔍 EVENT_VECTOR_DEBUG: Storing in collection: {self.events_collection}")
            stored_ids = self.qdrant.store_vectors(self.events_collection, vector_data)
            print(f"✅ EVENT_VECTOR_DEBUG: Event vector stored - IDs: {stored_ids}")

        except Exception as e:
            print(f"❌ EVENT_VECTOR_DEBUG: Vector creation failed: {e}")
            logger.error(f"Failed to create event vector: {e}")
            import traceback
            traceback.print_exc()
            # Don't fail the whole operation if vector storage fails

    def _create_event_summary(self, event_type: str, event_data: Dict[str, Any]) -> str:
        """Create semantic summary for event embedding"""
        try:
            # Create searchable summary based on event type and data
            summary_parts = [f"Event type: {event_type}"]

            # Add key information from event data
            if isinstance(event_data, dict):
                for key, value in event_data.items():
                    if isinstance(value, str) and len(value) < 200:
                        summary_parts.append(f"{key}: {value}")
                    elif key in ['action', 'semantic_action', 'command', 'query', 'response']:
                        summary_parts.append(f"{key}: {str(value)[:100]}")

            return " | ".join(summary_parts)

        except Exception as e:
            logger.warning(f"Failed to create event summary: {e}")
            return f"Event: {event_type}"

    async def search_relevant_events(
        self,
        query: str,
        project_id: str,
        limit: int = 10,
        similarity_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant events using vector search + SQL read-through
        """
        try:
            # Step 1: Vector search for relevant event IDs
            query_embedding = self.embedding_service.generate_single_embedding(query)

            # Search with project filter
            vector_results = self.qdrant.search_vectors(
                collection_name=self.events_collection,
                query_vector=query_embedding,
                limit=limit * 2,  # Get extra results for filtering
                score_threshold=similarity_threshold,
                metadata_filter={"must": [{"key": "project_id", "match": {"value": project_id}}]}
            )

            if not vector_results:
                logger.debug(f"No relevant events found for query: {query}")
                return []

            # Step 2: Extract event IDs from vector results
            event_ids = [result.get("payload", {}).get("event_id") for result in vector_results]
            event_ids = [eid for eid in event_ids if eid]  # Filter out None values

            if not event_ids:
                logger.warning("Vector search returned results but no event_ids found")
                return []

            # Step 3: SQL read-through to get full event content
            conn = self.db_service._conn()
            try:
                events = get_events_by_ids(conn, event_ids)

                # Combine with vector scores
                id_to_score = {
                    result.get("payload", {}).get("event_id"): result.get("score", 0)
                    for result in vector_results
                }

                for event in events:
                    event["similarity_score"] = id_to_score.get(event["event_id"], 0)

                # Sort by similarity score
                events.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)

                logger.info(f"Retrieved {len(events)} relevant events for query")
                return events[:limit]

            finally:
                self.db_service._return(conn)

        except Exception as e:
            logger.error(f"Failed to search relevant events: {e}")
            return []

    async def get_project_context(self, project_id: str) -> Dict[str, Any]:
        """Get comprehensive project context using SQL read-through"""
        try:
            conn = self.db_service._conn()
            try:
                # Get thread metadata
                thread = get_project_thread_by_project_id(conn, project_id)
                if not thread:
                    return {"error": "No project thread found"}

                project_thread_id = thread["project_thread_id"]

                # Get ALL recent events (from SQL, not vectors) - no smart filtering
                recent_events = get_recent_events(conn, project_thread_id, limit=20)

                # Get conversation history
                conversation = get_conversation_history(conn, project_thread_id, limit=20)

                # ✅ FORMAT conversations for DAS dock compatibility
                formatted_conversations = self._format_conversation_for_ui(conversation)
                print(f"🔍 GET_BY_PROJECT_DEBUG: Formatted {len(conversation)} raw → {len(formatted_conversations)} DAS-compatible")

                # ✅ GET PROJECT METADATA (files, ontologies, classes)
                project_metadata = self._get_comprehensive_project_metadata(conn, project_id)
                print(f"🔍 PROJECT_METADATA_DEBUG: Retrieved metadata with {len(project_metadata.get('files', []))} files, {len(project_metadata.get('ontologies', []))} ontologies")

                return {
                    "project_thread": thread,
                    "recent_events": recent_events,
                    "conversation_history": formatted_conversations,  # ← Now properly formatted for DAS dock
                    "project_metadata": project_metadata,  # ← Add comprehensive project metadata
                    "sql_first": True  # Flag indicating SQL-first retrieval
                }

            finally:
                self.db_service._return(conn)

        except Exception as e:
            logger.error(f"Failed to get project context: {e}")
            return {"error": str(e)}

    async def store_conversation_message(
        self,
        project_thread_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store conversation message in SQL-first approach"""
        try:
            print(f"🔍 THREAD_STORAGE_DEBUG: Storing conversation message")
            print(f"   Thread ID: {project_thread_id}")
            print(f"   Role: {role}")
            print(f"   Content length: {len(content)}")
            print(f"   Metadata keys: {list(metadata.keys()) if metadata else 'None'}")

            conn = self.db_service._conn()
            try:
                conversation_id = insert_thread_conversation(
                    conn=conn,
                    project_thread_id=project_thread_id,
                    role=role,
                    content=content,
                    metadata=metadata
                )

                print(f"✅ THREAD_STORAGE_DEBUG: Stored conversation message {conversation_id[:8]}...")

                # Debug what was actually stored
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT role, LEFT(content, 50), jsonb_object_keys(metadata) as keys
                        FROM thread_conversation
                        WHERE conversation_id = %s
                    """, (conversation_id,))

                    stored_data = cur.fetchall()
                    if stored_data:
                        print(f"✅ THREAD_STORAGE_DEBUG: Verified storage:")
                        for row in stored_data:
                            print(f"   Role: {row[0]}, Content: {row[1]}..., Metadata key: {row[2]}")

                return conversation_id

            finally:
                self.db_service._return(conn)

        except Exception as e:
            print(f"❌ THREAD_STORAGE_DEBUG: Storage failed: {e}")
            logger.error(f"Failed to store conversation message: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def get_project_thread_by_project_id(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get project thread by project ID for DAS compatibility.
        Returns the project context in a format DAS engines expect.
        """
        try:
            project_context = await self.get_project_context(project_id)
            if "error" in project_context:
                return None

            # Return context in format DAS engines expect
            return project_context

        except Exception as e:
            logger.error(f"Error getting project thread by project ID: {e}")
            return None

    async def create_project_thread(self, project_id: str, user_id: str) -> Dict[str, Any]:
        """
        Create project thread for DAS compatibility.
        Returns the same format as get_project_thread_by_project_id.
        """
        try:
            return await self.get_or_create_project_thread(project_id, user_id)
        except Exception as e:
            logger.error(f"Error creating project thread: {e}")
            raise

    async def get_project_thread(self, project_thread_id: str) -> Optional[Dict[str, Any]]:
        """
        Get project thread by thread ID for Thread Manager API compatibility.
        Returns data in format expected by thread manager workbench.
        """
        try:
            conn = self.db_service._conn()
            try:
                # Get thread metadata
                thread = get_project_thread_by_id(conn, project_thread_id)

                if not thread:
                    return None

                # Get conversation history
                conversation = get_conversation_history(conn, project_thread_id, limit=50)

                # Get recent events
                events = get_recent_events(conn, project_thread_id, limit=20)

                # Return in format expected by Thread Manager API
                return {
                    "project_thread_id": thread["project_thread_id"],
                    "project_id": thread["project_id"],
                    "created_by": thread["created_by"],
                    "created_at": thread["created_at"],
                    "last_activity": thread["last_activity"],
                    "status": thread.get("status", "active"),
                    "goals": thread.get("goals"),
                    "current_workbench": thread.get("current_workbench", "unknown"),

                    # Convert SQL data to expected format
                    "conversation_history": self._format_conversation_for_ui(conversation),
                    "project_events": self._format_events_for_ui(events),

                    # Default values for fields not yet implemented in SQL-first
                    "active_ontologies": [],
                    "recent_documents": [],
                    "key_decisions": [],
                    "learned_patterns": [],
                    "contextual_references": {},
                    "similar_projects": [],
                    "applied_patterns": [],

                    # SQL-first indicators
                    "sql_first": True,
                    "content_source": "PostgreSQL"
                }

            finally:
                self.db_service._return(conn)

        except Exception as e:
            logger.error(f"Error getting project thread by ID: {e}")
            return None

    def _format_conversation_for_ui(self, conversation: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format SQL conversation history for BOTH DAS dock AND Thread Manager UI"""
        print(f"🔍 FORMAT_DEBUG: Converting {len(conversation)} SQL messages to DAS dock format")

        if not conversation:
            print("   No conversations to format")
            return []

        # Debug first few raw SQL entries
        for i, msg in enumerate(conversation[:3]):
            print(f"   SQL message {i+1}: role={msg.get('role')}, content_length={len(msg.get('content', ''))}")

        formatted = []

        # Process conversations in chronological order and group user/assistant pairs
        i = 0
        while i < len(conversation):
            current_msg = conversation[i]
            current_role = current_msg.get("role")

            print(f"🔍 Processing message {i}: role={current_role}")

            if current_role == "user":
                # Found user message, look for corresponding assistant response
                user_msg = current_msg
                das_response = None

                # Look for assistant response (next message or nearby)
                if i + 1 < len(conversation) and conversation[i + 1].get("role") == "assistant":
                    das_response = conversation[i + 1]
                    print(f"   Found pair: user + assistant")
                    i += 2  # Skip both messages
                else:
                    print(f"   Found user message without assistant response")
                    i += 1  # Only user message

                # Create DAS dock compatible entry
                assistant_metadata = das_response.get("metadata", {}) if das_response else {}
                user_metadata = user_msg.get("metadata", {})

                entry = {
                    # ✅ DAS DOCK REQUIRED FORMAT
                    "user_message": user_msg["content"],
                    "das_response": das_response["content"] if das_response else "",
                    "timestamp": user_msg["created_at"].isoformat() if hasattr(user_msg["created_at"], "isoformat") else str(user_msg["created_at"]),

                    # ✅ THREAD MANAGER RICH CONTEXT
                    "prompt_context": assistant_metadata.get("prompt_context", "No prompt context available"),
                    "rag_context": assistant_metadata.get("rag_context", {"chunks_found": 0, "sources": [], "success": False}),
                    "project_context": assistant_metadata.get("project_context", {}),
                    "thread_metadata": assistant_metadata.get("thread_metadata", {}),

                    # ✅ METADATA
                    "sql_first": True,
                    "processing_time": assistant_metadata.get("processing_time", 0)
                }

                print(f"   ✅ Created entry: user='{entry['user_message'][:40]}...', das='{entry['das_response'][:40]}...'")
                formatted.append(entry)

            else:
                # Skip non-user messages (orphaned assistant messages, etc.)
                print(f"   Skipping {current_role} message")
                i += 1

        print(f"✅ FORMAT_DEBUG: Converted {len(formatted)} conversation pairs for DAS dock")
        return formatted

    def _format_events_for_ui(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format events for Thread Manager UI"""
        formatted = []

        for event in events:
            formatted_event = {
                "event_id": event["event_id"],
                "event_type": event["event_type"],
                "timestamp": event["created_at"].isoformat() if hasattr(event["created_at"], "isoformat") else str(event["created_at"]),
                "summary": event.get("semantic_summary", f"{event['event_type']} event"),
                "event_data": event.get("event_data", {}),
                "sql_first": True
            }
            formatted.append(formatted_event)

        return formatted

    async def list_threads(self, project_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List project threads for Thread Manager workbench.
        """
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    if project_id:
                        # Filter by project
                        cur.execute("""
                            SELECT project_thread_id, project_id, created_by, created_at, last_activity, status, goals, current_workbench
                            FROM project_thread
                            WHERE project_id = %s
                            ORDER BY last_activity DESC
                            LIMIT %s
                        """, (project_id, limit))
                    else:
                        # All threads
                        cur.execute("""
                            SELECT project_thread_id, project_id, created_by, created_at, last_activity, status, goals, current_workbench
                            FROM project_thread
                            ORDER BY last_activity DESC
                            LIMIT %s
                        """, (limit,))

                    cols = [desc[0] for desc in cur.description]
                    threads = [dict(zip(cols, row)) for row in cur.fetchall()]

                    # Format for Thread Manager API with counts
                    formatted_threads = []
                    for thread in threads:
                        thread_id = thread["project_thread_id"]

                        # Get conversation and event counts for this thread
                        with conn.cursor() as count_cur:
                            # Count conversations
                            count_cur.execute("SELECT COUNT(*) FROM thread_conversation WHERE project_thread_id = %s", (thread_id,))
                            conversation_count = count_cur.fetchone()[0]

                            # Count events
                            count_cur.execute("SELECT COUNT(*) FROM project_event WHERE project_thread_id = %s", (thread_id,))
                            events_count = count_cur.fetchone()[0]

                        formatted_thread = {
                            "project_thread_id": thread["project_thread_id"],
                            "project_id": thread["project_id"],
                            "created_by": thread["created_by"],
                            "created_at": thread["created_at"].isoformat() if hasattr(thread["created_at"], "isoformat") else str(thread["created_at"]),
                            "last_activity": thread["last_activity"].isoformat() if hasattr(thread["last_activity"], "isoformat") else str(thread["last_activity"]),
                            "status": thread.get("status", "active"),
                            "current_workbench": thread.get("current_workbench", "unknown"),
                            "conversation_count": conversation_count,
                            "project_events_count": events_count,
                            "sql_first": True
                        }
                        formatted_threads.append(formatted_thread)

                    logger.debug(f"Listed {len(formatted_threads)} threads")
                    return formatted_threads

            finally:
                self.db_service._return(conn)

        except Exception as e:
            logger.error(f"Failed to list threads: {e}")
            return []

    async def delete_last_conversation(self, project_thread_id: str) -> bool:
        """Delete the last conversation entry (user + assistant pair) from SQL"""
        try:
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    # Get the last conversation entry
                    cur.execute("""
                        SELECT conversation_id, role, content, created_at
                        FROM thread_conversation
                        WHERE project_thread_id = %s
                        ORDER BY created_at DESC
                        LIMIT 2
                    """, (project_thread_id,))

                    last_entries = cur.fetchall()
                    print(f"🔍 DELETE_DEBUG: Found {len(last_entries)} entries for thread {project_thread_id}")
                    for i, entry in enumerate(last_entries):
                        print(f"   Entry {i}: role={entry[1]}, content_preview={entry[2][:50]}...")

                    if not last_entries:
                        logger.info(f"No conversation entries found for thread {project_thread_id}")
                        return False

                    # Check if we have a user message (should be the last one chronologically)
                    # The entries are ordered by created_at DESC, so we need to find the user message
                    user_entry = None
                    assistant_entry = None

                    for entry in last_entries:
                        if entry[1] == 'user':
                            user_entry = entry
                        elif entry[1] == 'assistant':
                            assistant_entry = entry

                    if not user_entry:
                        logger.info(f"No user message found in last entries, cannot delete conversation pair")
                        return False

                    # Delete the user message and assistant message if it exists
                    entries_to_delete = 2 if assistant_entry else 1

                    cur.execute("""
                        DELETE FROM thread_conversation
                        WHERE project_thread_id = %s
                        AND conversation_id IN (
                            SELECT conversation_id FROM (
                                SELECT conversation_id
                                FROM thread_conversation
                                WHERE project_thread_id = %s
                                ORDER BY created_at DESC
                                LIMIT %s
                            ) AS last_entries
                        )
                    """, (project_thread_id, project_thread_id, entries_to_delete))

                    deleted_count = cur.rowcount
                    conn.commit()

                    logger.info(f"Deleted {deleted_count} conversation entries from thread {project_thread_id}")
                    return deleted_count > 0

            finally:
                self.db_service._return(conn)

        except Exception as e:
            logger.error(f"Failed to delete last conversation for thread {project_thread_id}: {e}")
            return False

    def _get_comprehensive_project_metadata(self, conn, project_id: str) -> Dict[str, Any]:
        """Get comprehensive project metadata including files, ontologies, and classes"""
        try:
            metadata = {
                "files": [],
                "ontologies": [],
                "classes": [],
                "recent_activities": []
            }

            with conn.cursor() as cur:
                # Get uploaded files/knowledge assets
                cur.execute("""
                    SELECT ka.title, ka.document_type, ka.created_at, ka.status,
                           f.filename, f.file_size, f.content_type
                    FROM knowledge_assets ka
                    LEFT JOIN files f ON ka.source_file_id::text = f.id::text
                    WHERE ka.project_id = %s AND ka.status = 'active'
                    ORDER BY ka.created_at DESC
                """, (project_id,))

                files = cur.fetchall()
                for file_row in files:
                    metadata["files"].append({
                        "title": file_row[0],
                        "document_type": file_row[1],
                        "filename": file_row[4],
                        "size": file_row[5],
                        "created_at": file_row[2].isoformat() if file_row[2] else None
                    })

                # Get ontologies
                cur.execute("""
                    SELECT graph_iri, label, role, is_reference, created_at
                    FROM ontologies_registry
                    WHERE project_id = %s
                    ORDER BY created_at DESC
                """, (project_id,))

                ontologies = cur.fetchall()
                for onto_row in ontologies:
                    metadata["ontologies"].append({
                        "graph_iri": onto_row[0],
                        "label": onto_row[1],
                        "role": onto_row[2],
                        "is_reference": onto_row[3],
                        "created_at": onto_row[4].isoformat() if onto_row[4] else None
                    })

                # Get ontology classes using SPARQL (for each ontology)
                for onto_row in ontologies:
                    try:
                        graph_iri = onto_row[0]
                        onto_label = onto_row[1]

                        # Simple SPARQL query to get classes
                        import requests
                        from backend.services.config import Settings
                        settings = Settings()

                        sparql_query = f"""
                        PREFIX owl: <http://www.w3.org/2002/07/owl#>
                        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                        SELECT ?class ?label WHERE {{
                            GRAPH <{graph_iri}> {{
                                ?class a owl:Class .
                                OPTIONAL {{ ?class rdfs:label ?label }}
                            }}
                        }}
                        """

                        fuseki_url = f"{settings.fuseki_url}/query"
                        response = requests.post(
                            fuseki_url,
                            data={"query": sparql_query},
                            headers={"Accept": "application/json"},
                            auth=(settings.fuseki_user, settings.fuseki_password) if settings.fuseki_user else None,
                            timeout=5
                        )

                        if response.status_code == 200:
                            sparql_result = response.json()
                            bindings = sparql_result.get("results", {}).get("bindings", [])

                            for binding in bindings:
                                class_uri = binding.get("class", {}).get("value", "")
                                class_label = binding.get("label", {}).get("value", "")

                                # Extract class name from URI
                                class_name = class_uri.split("#")[-1] if "#" in class_uri else class_uri.split("/")[-1]

                                metadata["classes"].append({
                                    "class_name": class_name,
                                    "class_label": class_label or class_name,
                                    "class_uri": class_uri,
                                    "ontology": onto_label
                                })

                    except Exception as e:
                        logger.warning(f"Failed to get classes for ontology {onto_row[0]}: {e}")

                # Get recent project activities from events
                cur.execute("""
                    SELECT event_type, semantic_summary, created_at
                    FROM project_event
                    WHERE project_id = %s
                    ORDER BY created_at DESC
                    LIMIT 10
                """, (project_id,))

                activities = cur.fetchall()
                for activity in activities:
                    metadata["recent_activities"].append({
                        "event_type": activity[0],
                        "summary": activity[1],
                        "created_at": activity[2].isoformat() if activity[2] else None
                    })

            return metadata

        except Exception as e:
            logger.error(f"Failed to get comprehensive project metadata: {e}")
            return {
                "files": [],
                "ontologies": [],
                "recent_activities": [],
                "error": str(e)
            }

    def _get_diverse_recent_events(self, conn, project_thread_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get diverse recent events - prioritize important project events over DAS interactions

        Returns a mix of event types to give DAS better project context awareness
        """
        try:
            with conn.cursor() as cur:
                # Get diverse events with priority for non-DAS interactions
                cur.execute("""
                    (
                        SELECT event_id, project_thread_id, project_id, user_id, event_type,
                               event_data, context_snapshot, semantic_summary, created_at,
                               1 as priority  -- High priority for important events
                        FROM project_event
                        WHERE project_thread_id = %s
                        AND event_type IN ('project_created', 'ontology_created', 'ontology_modified', 'file_uploaded', 'class_created')
                        ORDER BY created_at DESC
                        LIMIT %s
                    )
                    UNION ALL
                    (
                        SELECT event_id, project_thread_id, project_id, user_id, event_type,
                               event_data, context_snapshot, semantic_summary, created_at,
                               2 as priority  -- Lower priority for DAS interactions
                        FROM project_event
                        WHERE project_thread_id = %s
                        AND event_type = 'das_interaction'
                        ORDER BY created_at DESC
                        LIMIT %s
                    )
                    ORDER BY priority ASC, created_at DESC
                    LIMIT %s
                """, (project_thread_id, limit // 2, project_thread_id, limit // 2, limit))

                cols = [desc[0] for desc in cur.description if desc[0] != 'priority']
                results = []
                for row in cur.fetchall():
                    # Exclude the priority column from the result
                    event_dict = dict(zip(cols, row[:-1]))  # Exclude last column (priority)
                    results.append(event_dict)

                logger.debug(f"Retrieved {len(results)} diverse events for thread {project_thread_id}")
                return results

        except Exception as e:
            logger.error(f"Failed to get diverse recent events: {e}")
            # Fallback to regular recent events
            from backend.db.event_queries import get_recent_events
            return get_recent_events(conn, project_thread_id, limit)

    def get_service_info(self) -> Dict[str, Any]:
        """Get service information"""
        dual_write = getattr(self.settings, 'rag_dual_write', 'true').lower() == 'true'

        return {
            "service": "SqlFirstThreadManager",
            "sql_first_storage": True,
            "dual_write_enabled": dual_write,
            "collections": {
                "events": self.events_collection,
                "threads": self.threads_collection
            },
            "vector_payload_contains_content": False,  # Key difference!
            "content_source_of_truth": "PostgreSQL",
            "replaces": "ProjectThreadManager (violates SQL-first)"
        }
