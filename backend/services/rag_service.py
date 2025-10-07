"""
RAG (Retrieval Augmented Generation) Service for ODRAS Knowledge Management

Combines vector similarity search with LLM generation to answer questions
using the knowledge base as context.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from .config import Settings
from .qdrant_service import QdrantService
from .llm_team import LLMTeam
from .db import DatabaseService

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG service that retrieves relevant knowledge chunks and generates
    contextual responses using LLMs.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.qdrant_service = QdrantService(settings)
        self.llm_team = LLMTeam(settings)
        self.db_service = DatabaseService(settings)

        # Feature flags for SQL-first RAG
        self.sql_read_through = getattr(settings, 'rag_sql_read_through', 'true').lower() == 'true'
        if self.sql_read_through:
            logger.info("RAG service initialized with SQL read-through enabled")

    async def query_knowledge_base(
        self,
        question: str,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        max_chunks: int = 10,
        similarity_threshold: float = 0.3,
        include_metadata: bool = True,
        response_style: str = "comprehensive",
        project_thread_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Query the knowledge base and generate a contextual response.

        Args:
            question: The user's question
            project_id: Optional project scope (if None, searches user's projects + public)
            user_id: User ID for access control
            max_chunks: Maximum number of relevant chunks to retrieve
            similarity_threshold: Minimum similarity score for relevance
            include_metadata: Include source metadata in response
            response_style: "comprehensive", "concise", or "technical"

        Returns:
            Dict containing generated response, sources, and metadata
        """
        try:
            logger.info(f"Processing RAG query: '{question}' for user {user_id}")

            # 1. Retrieve relevant knowledge chunks
            relevant_chunks = await self._retrieve_relevant_chunks(
                question=question,
                project_id=project_id,
                user_id=user_id,
                max_chunks=max_chunks,
                similarity_threshold=similarity_threshold,
            )

            if not relevant_chunks:
                return {
                    "success": True,
                    "response": "I couldn't find any relevant information in the knowledge base to answer your question. You may want to try rephrasing your question or adding more knowledge assets to your project.",
                    "sources": [],
                    "query": question,
                    "chunks_found": 0,
                    "generated_at": datetime.utcnow().isoformat(),
                }

            # 2. Generate response using LLM with retrieved context
            response_data = await self._generate_response(
                question=question,
                relevant_chunks=relevant_chunks,
                response_style=response_style,
                project_thread_context=project_thread_context,
            )

            # 3. Format final response
            result = {
                "success": True,
                "response": response_data["answer"],
                "confidence": response_data.get("confidence", "medium"),
                "sources": (self._format_sources(relevant_chunks) if include_metadata else []),
                "query": question,
                "chunks_found": len(relevant_chunks),
                "response_style": response_style,
                "generated_at": datetime.utcnow().isoformat(),
                "model_used": self.settings.llm_model,
                "provider": self.settings.llm_provider,
            }

            logger.info(f"Successfully generated RAG response with {len(relevant_chunks)} chunks")
            return result

        except Exception as e:
            logger.error(f"RAG query failed: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to process query: {str(e)}",
                "query": question,
                "generated_at": datetime.utcnow().isoformat(),
            }

    async def _retrieve_relevant_chunks(
        self,
        question: str,
        project_id: Optional[str],
        user_id: Optional[str],
        max_chunks: int,
        similarity_threshold: float,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant knowledge chunks using vector similarity search.
        With SQL read-through enabled, fetches actual text content from SQL.
        """
        try:
            # Perform vector search in both collections
            print(f"🔍 VECTOR_QUERY_DEBUG: Searching for '{question}' in both collections")
            print(f"   Max chunks: {max_chunks * 2}, Threshold: {similarity_threshold}")

            # Build metadata filter for project
            metadata_filter = None
            if project_id:
                metadata_filter = {
                    "project_id": project_id
                }
                print(f"🔍 VECTOR_QUERY_DEBUG: Using metadata filter: {metadata_filter}")

            # Search both collections
            search_results_384 = await self.qdrant_service.search_similar_chunks(
                query_text=question,
                collection_name="knowledge_chunks",
                limit=max_chunks * 2,  # Get extra results for filtering
                score_threshold=similarity_threshold,
                metadata_filter=metadata_filter,
            )

            search_results_768 = await self.qdrant_service.search_similar_chunks(
                query_text=question,
                collection_name="knowledge_chunks_768",
                limit=max_chunks * 2,  # Get extra results for filtering
                score_threshold=similarity_threshold,
                metadata_filter=metadata_filter,
            )

            # Combine and deduplicate results
            all_results = search_results_384 + search_results_768
            # Remove duplicates based on chunk_id
            seen_chunks = set()
            search_results = []
            for result in all_results:
                # chunk_id might be in the payload
                chunk_id = result.get('chunk_id') or result.get('payload', {}).get('chunk_id')
                if chunk_id and chunk_id not in seen_chunks:
                    seen_chunks.add(chunk_id)
                    search_results.append(result)
                elif not chunk_id:
                    # If no chunk_id, include it anyway (legacy chunk)
                    search_results.append(result)

            print(f"🔍 VECTOR_QUERY_DEBUG: Combined search returned {len(search_results)} results ({len(search_results_384)} from 384-dim, {len(search_results_768)} from 768-dim)")

            # Filter chunks based on project access permissions
            accessible_chunks = []
            for chunk in search_results:
                if await self._has_chunk_access(chunk, project_id, user_id):
                    accessible_chunks.append(chunk)

            # PREFER SQL-first chunks over legacy chunks
            print(f"🔍 RAG_FILTER_DEBUG: Found {len(accessible_chunks)} accessible chunks")
            sql_first_chunks = []
            legacy_chunks = []

            for chunk in accessible_chunks:
                payload = chunk.get('payload', {})
                has_chunk_id = 'chunk_id' in payload
                has_content = 'content' in payload

                if has_chunk_id and not has_content:
                    sql_first_chunks.append(chunk)
                    print(f"✅ RAG_FILTER_DEBUG: SQL-first chunk found - {payload['chunk_id'][:8]}...")
                else:
                    legacy_chunks.append(chunk)
                    print(f"❌ RAG_FILTER_DEBUG: Legacy chunk found - score {chunk.get('score', 0):.3f}")

            # Use SQL-first chunks if available, otherwise fall back to legacy
            if sql_first_chunks:
                print(f"🎯 RAG_FILTER_DEBUG: Using {len(sql_first_chunks)} SQL-first chunks")
                filtered_chunks = sql_first_chunks[:max_chunks]
            else:
                print(f"⚠️ RAG_FILTER_DEBUG: No SQL-first chunks, using {len(legacy_chunks)} legacy chunks")
                filtered_chunks = legacy_chunks[:max_chunks]

            # Deduplicate sources - keep only the best chunk per asset/document
            deduplicated_chunks = self._deduplicate_sources(filtered_chunks, max_chunks)

            # SQL read-through: fetch actual text content from SQL if enabled
            print(f"🔍 SQL_READTHROUGH_DEBUG: SQL read-through enabled: {self.sql_read_through}")
            if self.sql_read_through:
                print(f"🔍 SQL_READTHROUGH_DEBUG: Enriching {len(deduplicated_chunks)} chunks with SQL content")
                deduplicated_chunks = await self._enrich_chunks_with_sql_content(deduplicated_chunks)
                print(f"🔍 SQL_READTHROUGH_DEBUG: After enrichment: {len(deduplicated_chunks)} chunks")

            return deduplicated_chunks

        except Exception as e:
            logger.error(f"Failed to retrieve relevant chunks: {str(e)}")
            return []

    async def _enrich_chunks_with_sql_content(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich vector search results with actual text content from SQL.

        Args:
            chunks: List of chunks from vector search with payloads

        Returns:
            List of chunks with SQL text content added to payload
        """
        try:
            # Extract chunk IDs from vector payloads
            chunk_ids = []
            chunk_id_to_vector_chunk = {}

            for chunk in chunks:
                payload = chunk.get("payload", {})
                chunk_id = payload.get("chunk_id")

                if chunk_id:
                    chunk_ids.append(chunk_id)
                    chunk_id_to_vector_chunk[chunk_id] = chunk
                else:
                    logger.warning(f"No chunk_id found in payload: {payload}")

            if not chunk_ids:
                print("❌ SQL_READTHROUGH_DEBUG: No chunk_ids found in vector search results for SQL read-through")
                logger.warning("No chunk_ids found in vector search results for SQL read-through")
                return chunks  # Return original chunks if no IDs

            print(f"🔍 SQL_READTHROUGH_DEBUG: Fetching {len(chunk_ids)} chunks from SQL")
            print(f"   Chunk IDs: {[cid[:8] + '...' for cid in chunk_ids[:5]]}")
            logger.debug(f"Fetching {len(chunk_ids)} chunks from SQL for read-through")

            # Fetch actual text content from SQL
            conn = self.db_service._conn()
            try:
                from backend.db.queries import get_chunks_by_ids
                sql_chunks = get_chunks_by_ids(conn, chunk_ids)
                print(f"🔍 SQL_READTHROUGH_DEBUG: Retrieved {len(sql_chunks)} chunks from SQL")

                # Debug first chunk content
                if sql_chunks:
                    first_chunk = sql_chunks[0]
                    chunk_text = first_chunk.get('content', '')
                    print(f"🔍 SQL_READTHROUGH_DEBUG: First chunk preview: {chunk_text[:200]}...")
                    print(f"   Contains 'aeromapper': {'aeromapper' in chunk_text.lower()}")
                    print(f"   Contains '20': {'20' in chunk_text}")
                    print(f"   Contains 'kg': {'kg' in chunk_text.lower()}")

                logger.debug(f"Retrieved {len(sql_chunks)} chunks from SQL")

                # Create mapping of chunk_id to SQL text
                chunk_id_to_sql_text = {
                    chunk['chunk_id']: chunk['text']
                    for chunk in sql_chunks
                }

                # Enrich vector chunks with SQL text
                enriched_chunks = []
                for chunk_id in chunk_ids:  # Preserve order from vector search
                    if chunk_id in chunk_id_to_vector_chunk and chunk_id in chunk_id_to_sql_text:
                        vector_chunk = chunk_id_to_vector_chunk[chunk_id]
                        sql_text = chunk_id_to_sql_text[chunk_id]

                        # Clone the chunk and add SQL text to payload
                        enriched_chunk = {
                            "score": vector_chunk.get("score", 0),
                            "payload": {
                                **vector_chunk.get("payload", {}),
                                "content": sql_text,  # SQL text as authoritative content
                                "sql_read_through": True  # Flag to indicate source
                            }
                        }
                        enriched_chunks.append(enriched_chunk)
                    else:
                        logger.warning(f"No SQL text found for chunk_id: {chunk_id}")
                        # Keep original chunk as fallback
                        enriched_chunks.append(chunk_id_to_vector_chunk.get(chunk_id, {}))

                logger.info(f"Successfully enriched {len(enriched_chunks)} chunks with SQL content")
                return enriched_chunks

            finally:
                self.db_service._return(conn)

        except Exception as e:
            logger.error(f"Failed to enrich chunks with SQL content: {e}")
            logger.warning("Falling back to vector payload content")
            return chunks  # Return original chunks on error

    async def store_conversation_messages(
        self,
        project_id: str,
        session_id: str,
        user_message: str,
        assistant_message: str
    ) -> Tuple[str, str]:
        """
        Store conversation messages using SQL-first approach.

        Args:
            project_id: Project identifier
            session_id: Session identifier
            user_message: User's question/message
            assistant_message: Assistant's response

        Returns:
            Tuple of (user_message_id, assistant_message_id)
        """
        try:
            # Check if dual-write is enabled
            dual_write = getattr(self.settings, 'rag_dual_write', 'true').lower() == 'true'

            if dual_write:
                # Use SQL-first storage service
                from .store import create_rag_store_service
                rag_store = create_rag_store_service(self.settings)

                conn = self.db_service._conn()
                try:
                    # Store user message
                    user_msg_id = rag_store.store_message_and_vector(
                        conn=conn,
                        project_id=project_id,
                        session_id=session_id,
                        role="user",
                        content=user_message
                    )

                    # Store assistant message
                    assistant_msg_id = rag_store.store_message_and_vector(
                        conn=conn,
                        project_id=project_id,
                        session_id=session_id,
                        role="assistant",
                        content=assistant_message
                    )

                    logger.debug(f"Stored conversation messages: user={user_msg_id}, assistant={assistant_msg_id}")
                    return user_msg_id, assistant_msg_id

                finally:
                    self.db_service._return(conn)
            else:
                logger.debug("Dual-write disabled, skipping conversation message storage")
                return "disabled", "disabled"

        except Exception as e:
            logger.error(f"Failed to store conversation messages: {e}")
            return "error", "error"

    def _deduplicate_sources(self, chunks: List[Dict[str, Any]], max_chunks: int) -> List[Dict[str, Any]]:
        """
        Deduplicate chunks by keeping multiple chunks per asset/document for comprehensive queries.
        For UAS specifications and other detailed documents, we need multiple chunks to get complete information.
        """
        if not chunks:
            return []

        # Group chunks by asset_id
        asset_groups = {}
        for chunk in chunks:
            payload = chunk.get("payload", {})
            asset_id = payload.get("asset_id", "unknown")

            if asset_id not in asset_groups:
                asset_groups[asset_id] = []
            asset_groups[asset_id].append(chunk)

        # Keep multiple chunks from each asset (up to 3 per asset for comprehensive coverage)
        deduplicated_chunks = []
        for asset_id, asset_chunks in asset_groups.items():
            # Sort by score (highest first) and take up to 3 chunks per asset
            asset_chunks.sort(key=lambda c: c.get("score", 0), reverse=True)
            chunks_to_keep = asset_chunks[:3]  # Keep up to 3 chunks per asset
            deduplicated_chunks.extend(chunks_to_keep)

        # Sort all deduplicated chunks by score and limit to max_chunks
        deduplicated_chunks.sort(key=lambda c: c.get("score", 0), reverse=True)
        return deduplicated_chunks[:max_chunks]

    async def _has_chunk_access(
        self, chunk: Dict[str, Any], project_id: Optional[str], user_id: Optional[str]
    ) -> bool:
        """
        Check if user has access to a knowledge chunk based on project membership
        and public asset visibility.
        """
        try:
            chunk_metadata = chunk.get("payload", {})
            chunk_project_id = chunk_metadata.get("project_id")
            asset_id = chunk_metadata.get("asset_id")

            # Skip chunks with invalid or missing metadata
            if not chunk_project_id or not user_id or chunk_project_id in ["unknown", "null", ""]:
                logger.debug(f"Skipping chunk with invalid project_id: {chunk_project_id}")
                return False

            # Validate that chunk_project_id is a valid UUID format
            try:
                from uuid import UUID

                UUID(chunk_project_id)  # This will raise ValueError if not valid UUID
            except (ValueError, TypeError):
                logger.debug(f"Skipping chunk with non-UUID project_id: {chunk_project_id}")
                return False

            # Check if asset is public
            if asset_id and asset_id not in ["unknown", "null", ""]:
                try:
                    UUID(asset_id)  # Validate asset_id too
                    conn = self.db_service._conn()
                    try:
                        with conn.cursor() as cur:
                            cur.execute(
                                "SELECT is_public FROM knowledge_assets WHERE id = %s",
                                (asset_id,),
                            )
                            result = cur.fetchone()
                            if result and result[0]:  # Asset is public
                                return True
                    finally:
                        self.db_service._return(conn)
                except (ValueError, TypeError):
                    logger.debug(f"Skipping chunk with non-UUID asset_id: {asset_id}")

            # If specific project requested, check if chunk belongs to it
            if project_id:
                return chunk_project_id == project_id

            # Otherwise, check if user has access to chunk's project
            return self.db_service.is_user_member(project_id=chunk_project_id, user_id=user_id)

        except Exception as e:
            logger.warning(f"Access check failed for chunk: {str(e)}")
            return False

    async def _generate_response(
        self, question: str, relevant_chunks: List[Dict[str, Any]], response_style: str, project_thread_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a response using LLM with retrieved knowledge context.
        """
        try:
            # Prepare context from retrieved chunks
            context = self._prepare_context(relevant_chunks)

            # Choose system prompt based on response style
            system_prompts = {
                "comprehensive": """You are a knowledgeable assistant helping users understand information from their knowledge base.
                Provide comprehensive, well-structured answers using the provided context.
                Include relevant details and explain concepts clearly.
                If the context doesn't fully answer the question, be honest about limitations.
                Always ground your response in the provided context.""",
                "concise": """You are a helpful assistant providing concise, direct answers from the knowledge base.
                Give brief, to-the-point responses using only the most relevant information.
                Focus on answering the specific question asked.
                Keep responses short but accurate.""",
                "technical": """You are a technical expert assistant providing detailed technical responses.
                Include specific technical details, specifications, and implementation notes.
                Use precise terminology and provide comprehensive technical context.
                Focus on accuracy and completeness of technical information.""",
            }

            system_prompt = system_prompts.get(response_style, system_prompts["comprehensive"])

            # Prepare project thread context if available
            project_context_section = ""
            if project_thread_context:
                project_context_section = f"""
PROJECT CONTEXT:
Project ID: {project_thread_context.get('project_id', 'Unknown')}
Project Thread ID: {project_thread_context.get('project_thread_id', 'Unknown')}
Created: {project_thread_context.get('created_at', 'Unknown')}
Last Activity: {project_thread_context.get('last_activity', 'Unknown')}

Project Events ({len(project_thread_context.get('thread_data', {}).get('project_events', []))} total):
{self._format_project_events(project_thread_context.get('thread_data', {}).get('project_events', []))}

Active Ontologies: {project_thread_context.get('thread_data', {}).get('active_ontologies', [])}
Current Workbench: {project_thread_context.get('thread_data', {}).get('current_workbench', 'Unknown')}
Recent Documents: {project_thread_context.get('thread_data', {}).get('recent_documents', [])}
"""

            # Create user prompt with both project context and knowledge base context
            user_prompt = f"""{project_context_section}
KNOWLEDGE BASE CONTEXT:
{context}

User Question: {question}

Please provide a helpful response using both the project context (showing what has been done in this project) and the knowledge base context (relevant documents and information). If you can answer from the project context, do so. If you need information from the knowledge base, use that. Be specific about what you found in the project vs. what you found in the knowledge base."""

            # Use the existing LLM team infrastructure
            # Create a simple schema for RAG responses
            response_schema = {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "The main response to the user's question",
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Confidence level in the response based on context quality",
                    },
                    "key_points": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key points covered in the response",
                    },
                },
                "required": ["answer", "confidence"],
            }

            # Call LLM with custom persona for RAG
            custom_personas = [
                {
                    "name": "Knowledge Assistant",
                    "system_prompt": system_prompt,
                    "is_active": True,
                }
            ]

            # Use the analyze_requirement method adapted for RAG
            llm_response = await self.llm_team.analyze_requirement(
                requirement_text=user_prompt,
                ontology_json_schema=response_schema,
                custom_personas=custom_personas,
            )

            return llm_response

        except Exception as e:
            logger.error(f"Failed to generate LLM response: {str(e)}")
            return {
                "answer": "I encountered an error while generating a response. Please try again.",
                "confidence": "low",
                "error": str(e),
            }

    def _prepare_context(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Prepare context string from retrieved knowledge chunks.
        """
        context_parts = []

        for i, chunk in enumerate(chunks):
            chunk_data = chunk.get("payload", {})
            content = chunk_data.get("content", "")  # FIXED: content not text!
            source = chunk_data.get("source_asset", "Unknown")
            doc_type = chunk_data.get("document_type", "document")

            context_part = f"""[Source {i+1}: {source} ({doc_type})]
{content}

"""
            context_parts.append(context_part)

        return "\n".join(context_parts)

    def _format_project_events(self, events: List[Dict[str, Any]]) -> str:
        """Format project events for LLM context"""
        if not events:
            return "No project events recorded."

        formatted_events = []
        for i, event in enumerate(events[-10:], 1):  # Show last 10 events
            event_type = event.get("event_type", "unknown")
            timestamp = event.get("timestamp", "unknown")
            action = event.get("key_data", {}).get("semantic_action", event.get("key_data", {}).get("action", "unknown"))

            # Format timestamp to be more readable
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                readable_time = dt.strftime("%Y-%m-%d %H:%M")
            except:
                readable_time = timestamp

            formatted_events.append(f"  {i}. [{event_type}] {action} ({readable_time})")

        return "\n".join(formatted_events)

    def _format_sources(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format source information with proper asset titles from database.
        """
        sources = []
        seen_assets = set()

        # Get database connection to look up asset titles
        from .db import DatabaseService

        db_service = DatabaseService(self.settings)
        conn = db_service._conn()

        try:
            with conn.cursor() as cur:
                for chunk in chunks:
                    chunk_data = chunk.get("payload", {})
                    asset_id = chunk_data.get("asset_id")
                    doc_id = chunk_data.get("doc_id")

                    # Try asset_id first, then fall back to doc_id
                    lookup_id = asset_id or doc_id
                    if lookup_id and lookup_id not in seen_assets:
                        # Look up actual asset title from database using doc_id
                        # First try to find the file_id for this doc_id, then find the knowledge asset
                        cur.execute("""
                            SELECT ka.title
                            FROM knowledge_assets ka
                            JOIN files f ON ka.source_file_id = f.id
                            JOIN doc d ON f.filename = d.filename
                            WHERE d.doc_id = %s
                        """, (lookup_id,))
                        result = cur.fetchone()
                        asset_title = result[0] if result else "Unknown Document"

                        source = {
                            "asset_id": lookup_id,
                            "title": asset_title,  # ACTUAL ASSET TITLE FROM DATABASE!
                            "document_type": chunk_data.get("document_type", "document"),
                            "chunk_id": chunk_data.get("chunk_id"),
                            "relevance_score": chunk.get("score", 0.0),
                        }
                        sources.append(source)
                        seen_assets.add(lookup_id)
        finally:
            db_service._return(conn)

        return sources

    async def get_query_suggestions(
        self,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[str]:
        """
        Generate suggested queries based on the available knowledge assets.
        """
        try:
            # Get asset types and topics from the knowledge base
            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    # Base query for user's accessible assets
                    base_query = """
                    SELECT DISTINCT document_type, title, metadata
                    FROM knowledge_assets ka
                    """

                    if project_id:
                        cur.execute(
                            f"{base_query} WHERE ka.project_id = %s LIMIT %s",
                            (project_id, limit * 2),
                        )
                    else:
                        # Get user's projects + public assets
                        user_projects = self.db_service.list_projects_for_user(
                            user_id=user_id, active=True
                        )
                        if not user_projects:
                            return []

                        project_ids = [str(p["project_id"]) for p in user_projects]
                        placeholders = ",".join(["%s"] * len(project_ids))
                        cur.execute(
                            f"{base_query} WHERE (ka.project_id IN ({placeholders}) OR ka.is_public = true) LIMIT %s",
                            project_ids + [limit * 2],
                        )

                    assets = cur.fetchall()

            finally:
                self.db_service._return(conn)

            # Generate suggestions based on asset content
            suggestions = []
            doc_types = set()
            topics = set()

            for doc_type, title, metadata in assets:
                doc_types.add(doc_type)
                if title and title != "unknown":
                    # Extract potential topics from titles
                    title_words = title.replace("_", " ").replace("-", " ").split()
                    for word in title_words:
                        if len(word) > 4:  # Skip short words
                            topics.add(word.title())

            # Create query templates
            if doc_types:
                for doc_type in list(doc_types)[:2]:  # Limit to avoid too many suggestions
                    suggestions.append(f"What are the key {doc_type} in this project?")

            if topics:
                for topic in list(topics)[:2]:
                    suggestions.append(f"Tell me about {topic}")

            # Add generic suggestions
            generic_suggestions = [
                "What are the main requirements in this project?",
                "Summarize the key documents",
                "What safety considerations are mentioned?",
                "What are the technical specifications?",
                "Show me the compliance requirements",
            ]

            suggestions.extend(generic_suggestions)

            return suggestions[:limit]

        except Exception as e:
            logger.error(f"Failed to generate query suggestions: {str(e)}")
            return [
                "What are the main requirements?",
                "Summarize the key documents",
                "What safety considerations are mentioned?",
                "What are the technical specifications?",
            ]


def get_rag_service() -> RAGService:
    """Factory function to get RAG service instance."""
    settings = Settings()
    return RAGService(settings)
