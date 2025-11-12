"""
Modular RAG Service

Refactored RAG service using modular components for better testability and extensibility.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

from ...services.config import Settings
from ...services.db import DatabaseService
from ...services.llm_team import LLMTeam
from ..storage.factory import create_vector_store
from ..storage.vector_store import VectorStore
from ..storage.text_search_store import TextSearchStore
from ..storage.opensearch_store import OpenSearchTextStore
from ..storage.text_search_factory import create_text_search_store
from ..retrieval.vector_retriever import VectorRetriever
from ..retrieval.hybrid_retriever import HybridRetriever
from ..retrieval.reranker import (
    Reranker,
    ReciprocalRankFusionReranker,
    CrossEncoderReranker,
    HybridReranker,
)
from ..retrieval.retriever import Retriever

logger = logging.getLogger(__name__)


class ModularRAGService:
    """
    Modular RAG service using abstract interfaces for all components.

    This service can easily swap implementations (e.g., Qdrant -> OpenSearch)
    and is fully testable with mocks.
    """

    def __init__(
        self,
        settings: Settings,
        vector_store: Optional[VectorStore] = None,
        text_search_store: Optional[TextSearchStore] = None,
        retriever: Optional[Retriever] = None,
        reranker: Optional[Reranker] = None,
        db_service: Optional[DatabaseService] = None,
        llm_team: Optional[LLMTeam] = None,
    ):
        """
        Initialize modular RAG service.

        Args:
            settings: Application settings
            vector_store: Optional vector store (creates from factory if not provided)
            text_search_store: Optional text search store for keyword search
            retriever: Optional retriever (creates based on config if not provided)
            reranker: Optional reranker (creates based on config if not provided)
            db_service: Optional database service (creates if not provided)
            llm_team: Optional LLM team (creates if not provided)
        """
        self.settings = settings

        # Initialize components (allow dependency injection for testing)
        self.vector_store = vector_store or create_vector_store(settings)
        
        # Initialize text search store if enabled
        self.hybrid_search_enabled = getattr(settings, "rag_hybrid_search", "false").lower() == "true"
        self.opensearch_enabled = getattr(settings, "opensearch_enabled", "false").lower() == "true"
        
        if self.hybrid_search_enabled and self.opensearch_enabled and not text_search_store:
            try:
                self.text_search_store = create_text_search_store(settings)
                if self.text_search_store:
                    logger.info("OpenSearch text search store initialized")
                else:
                    logger.warning("OpenSearch not available or disabled. Continuing with vector-only search.")
                    self.hybrid_search_enabled = False
            except Exception as e:
                logger.warning(f"Failed to initialize OpenSearch: {e}. Continuing with vector-only search.")
                self.text_search_store = None
                self.hybrid_search_enabled = False
        else:
            self.text_search_store = text_search_store

        # Initialize reranker based on config
        if not reranker:
            reranker_type = getattr(settings, "rag_reranker", "rrf").lower()
            if reranker_type == "cross_encoder":
                reranker = CrossEncoderReranker()
            elif reranker_type == "hybrid":
                reranker = HybridReranker(use_cross_encoder=True)
            elif reranker_type == "rrf":
                reranker = ReciprocalRankFusionReranker()
            else:
                reranker = None  # No reranking

        # Initialize retriever (hybrid if text search available, otherwise vector-only)
        if not retriever:
            if self.hybrid_search_enabled and self.text_search_store:
                self.retriever = HybridRetriever(
                    vector_store=self.vector_store,
                    text_search_store=self.text_search_store,
                    reranker=reranker,
                )
                logger.info("Using HybridRetriever (vector + keyword search)")
            else:
                self.retriever = VectorRetriever(self.vector_store)
                logger.info("Using VectorRetriever (vector-only search)")
        else:
            self.retriever = retriever

        self.db_service = db_service or DatabaseService(settings)
        self.llm_team = llm_team or LLMTeam(settings)

        # Feature flags
        self.sql_read_through = getattr(settings, "rag_sql_read_through", "true").lower() == "true"
        logger.info("ModularRAGService initialized with modular components")

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

        Uses modular components for retrieval and generation.

        Args:
            question: The user's question
            project_id: Optional project scope
            user_id: User ID for access control
            max_chunks: Maximum number of relevant chunks to retrieve
            similarity_threshold: Minimum similarity score for relevance
            include_metadata: Include source metadata in response
            response_style: "comprehensive", "concise", or "technical"
            project_thread_context: Optional project thread context

        Returns:
            Dict containing generated response, sources, and metadata
        """
        try:
            logger.info(f"Processing RAG query: '{question}' for user {user_id}")

            # 1. Retrieve relevant knowledge chunks using modular retriever
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
                    "response": "I couldn't find any relevant information in the knowledge base to answer your question.",
                    "sources": [],
                    "query": question,
                    "chunks_found": 0,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
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
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model_used": response_data.get("model_used", self.settings.llm_model),
                "provider": response_data.get("provider_used", self.settings.llm_provider),
            }

            logger.info(f"Successfully generated RAG response with {len(relevant_chunks)} chunks")
            return result

        except Exception as e:
            logger.error(f"RAG query failed: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to process query: {str(e)}",
                "query": question,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
            }

    async def _retrieve_relevant_chunks(
        self,
        question: str,
        project_id: Optional[str],
        user_id: Optional[str],
        max_chunks: int,
        similarity_threshold: float,
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant chunks using modular retriever."""
        try:
            # Build metadata filter for project
            metadata_filter = None
            if project_id:
                metadata_filter = {"project_id": project_id}

            # Enhance query with project context for vague queries
            enhanced_query = question
            vague_indicators = ["tell me about", "what is", "describe", "explain", "summarize"]
            is_vague = any(indicator in question.lower() for indicator in vague_indicators)
            
            # Lower threshold for vague queries to improve recall
            effective_threshold = similarity_threshold
            if is_vague:
                # More aggressive lowering for vague queries - always go to 0.1 for better recall
                effective_threshold = 0.1  # Lower threshold significantly for vague queries
                logger.info(f"Lowered threshold for vague query '{question[:50]}...': {similarity_threshold} -> {effective_threshold}")
            
            if is_vague and project_id:
                # Try to get project context to enhance the query
                try:
                    conn = self.db_service._conn()
                    try:
                        with conn.cursor() as cur:
                            cur.execute(
                                "SELECT name, description FROM projects WHERE project_id = %s",
                                (project_id,)
                            )
                            project_row = cur.fetchone()
                            if project_row:
                                project_name, project_desc = project_row
                                
                                # Enhance vague queries with project context
                                if "project" in question.lower():
                                    # For "tell me about the project" queries, expand to include system info
                                    enhanced_query = f"{question} Include information about the system, architecture, requirements, and features"
                                    if project_name and "test" not in project_name.lower():
                                        enhanced_query += f" related to {project_name}"
                                    logger.info(f"Enhanced vague project query: '{question}' -> '{enhanced_query}'")
                                elif any(word in question.lower() for word in ["what", "describe", "explain"]):
                                    # For other vague queries, add context about what to look for
                                    enhanced_query = f"{question} Include relevant system information, requirements, specifications, and documentation"
                                    logger.info(f"Enhanced vague query: '{question}' -> '{enhanced_query}'")
                    finally:
                        self.db_service._return(conn)
                except Exception as e:
                    logger.debug(f"Could not enhance query with project context: {e}")
                    # Continue with original query

            # Get active training collections (global, not project-scoped)
            training_collections = await self._get_active_training_collections()
            training_collection_names = [c["collection_name"] for c in training_collections]

            # Search project collections (with project_id filter)
            project_collections = ["knowledge_chunks", "knowledge_chunks_768"]
            project_results = await self.retriever.retrieve_multiple_collections(
                query=enhanced_query,
                collections=project_collections,
                limit_per_collection=max_chunks * 2,
                score_threshold=effective_threshold,
                metadata_filter=metadata_filter,  # Project-scoped filter
            )

            # Search training collections (NO project_id filter - global)
            training_results = {}
            if training_collection_names:
                training_results = await self.retriever.retrieve_multiple_collections(
                    query=enhanced_query,
                    collections=training_collection_names,
                    limit_per_collection=max_chunks,  # Fewer from training collections
                    score_threshold=effective_threshold,
                    metadata_filter=None,  # Global collections - no project filter
                )

            # Combine results from both project and training collections
            all_results = []
            for collection_name, results in project_results.items():
                # Mark as project knowledge
                for result in results:
                    result["source_type"] = "project"
                    result["collection_type"] = "project"
                all_results.extend(results)
            
            for collection_name, results in training_results.items():
                # Mark as training knowledge
                for result in results:
                    result["source_type"] = "training"
                    result["collection_type"] = "training"
                    # Get collection domain for context
                    collection_info = next(
                        (c for c in training_collections if c["collection_name"] == collection_name),
                        {}
                    )
                    if collection_info:
                        result["collection_domain"] = collection_info.get("domain", "general")
                all_results.extend(results)

            # Deduplicate by chunk_id
            seen_chunks = set()
            search_results = []
            for result in all_results:
                chunk_id = result.get("chunk_id") or result.get("payload", {}).get("chunk_id")
                if chunk_id and chunk_id not in seen_chunks:
                    seen_chunks.add(chunk_id)
                    search_results.append(result)
                elif not chunk_id:
                    search_results.append(result)

            # Filter by access permissions
            accessible_chunks = []
            for chunk in search_results:
                if await self._has_chunk_access(chunk, project_id, user_id):
                    accessible_chunks.append(chunk)

            # SQL read-through for SQL-first storage (always enabled for training chunks)
            # Training chunks always need SQL enrichment since they don't store text in Qdrant
            accessible_chunks = await self._enrich_chunks_with_sql_content(accessible_chunks)

            # Deduplicate sources and limit to max_chunks
            deduplicated_chunks = self._deduplicate_sources(accessible_chunks, max_chunks)

            return deduplicated_chunks

        except Exception as e:
            logger.error(f"Failed to retrieve relevant chunks: {str(e)}")
            return []

    async def _get_active_training_collections(self) -> List[Dict[str, Any]]:
        """
        Get list of active training collections from database.
        
        Returns:
            List of collection metadata dicts with collection_name and domain
        """
        try:
            if not self.db_service:
                logger.warning("Database service not available, skipping training collections")
                return []

            conn = self.db_service._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT collection_name, domain, display_name
                        FROM das_training_collections
                        WHERE is_active = TRUE
                        ORDER BY domain, display_name
                        """
                    )
                    rows = cur.fetchall()
                    
                    return [
                        {
                            "collection_name": row[0],
                            "domain": row[1],
                            "display_name": row[2],
                        }
                        for row in rows
                    ]
            finally:
                self.db_service._return(conn)

        except Exception as e:
            logger.warning(f"Failed to get active training collections: {e}")
            return []  # Return empty list on error, don't fail the query

    async def _enrich_chunks_with_sql_content(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich vector chunks with SQL text content (SQL-first approach)."""
        try:
            chunk_ids = []
            chunk_id_to_vector_chunk = {}
            training_chunk_ids = []
            project_chunk_ids = []

            # Separate training and project chunks
            for chunk in chunks:
                payload = chunk.get("payload", {})
                chunk_id = payload.get("chunk_id")
                source_type = chunk.get("source_type") or payload.get("source_type")
                
                if chunk_id:
                    chunk_ids.append(chunk_id)
                    chunk_id_to_vector_chunk[chunk_id] = chunk
                    
                    if source_type == "training":
                        training_chunk_ids.append(chunk_id)
                    else:
                        project_chunk_ids.append(chunk_id)

            if not chunk_ids:
                return chunks

            # Fetch from SQL - handle both project and training chunks
            conn = self.db_service._conn()
            try:
                chunk_id_to_sql_text = {}
                
                # Fetch project chunks from doc_chunk table
                if project_chunk_ids:
                    from backend.db.queries import get_chunks_by_ids
                    sql_chunks = get_chunks_by_ids(conn, project_chunk_ids)
                    chunk_id_to_sql_text.update({chunk["chunk_id"]: chunk["text"] for chunk in sql_chunks})
                
                # Fetch training chunks from das_training_chunks table
                if training_chunk_ids:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            SELECT chunk_id, content
                            FROM das_training_chunks
                            WHERE chunk_id = ANY(%s)
                            """,
                            (training_chunk_ids,)
                        )
                        training_rows = cur.fetchall()
                        chunk_id_to_sql_text.update({str(row[0]): row[1] for row in training_rows})

                # Enrich chunks
                enriched_chunks = []
                for chunk_id in chunk_ids:
                    if chunk_id in chunk_id_to_vector_chunk and chunk_id in chunk_id_to_sql_text:
                        vector_chunk = chunk_id_to_vector_chunk[chunk_id]
                        sql_text = chunk_id_to_sql_text[chunk_id]

                        enriched_chunk = {
                            "score": vector_chunk.get("score", 0),
                            "relevance_score": vector_chunk.get("score", 0),  # For API compatibility
                            "payload": {
                                **vector_chunk.get("payload", {}),
                                "content": sql_text,  # Add text from SQL
                                "text": sql_text,  # Also add as 'text' for compatibility
                                "sql_read_through": True,
                            },
                            "source_type": vector_chunk.get("source_type"),
                            "collection_type": vector_chunk.get("collection_type"),
                        }
                        enriched_chunks.append(enriched_chunk)
                    else:
                        # If SQL lookup failed, return original chunk
                        enriched_chunks.append(chunk_id_to_vector_chunk[chunk_id])

                return enriched_chunks
            finally:
                self.db_service._return(conn)

        except Exception as e:
            logger.error(f"Failed to enrich chunks with SQL content: {e}")
            return chunks

    async def _has_chunk_access(
        self, chunk: Dict[str, Any], project_id: Optional[str], user_id: Optional[str]
    ) -> bool:
        """Check if user has access to chunk."""
        try:
            chunk_metadata = chunk.get("payload", {})
            
            # Training chunks are global - always accessible (no project_id)
            source_type = chunk.get("source_type") or chunk_metadata.get("source_type")
            if source_type == "training":
                return True  # Training knowledge is global and accessible to all
            
            # Project chunks require project membership check
            chunk_project_id = chunk_metadata.get("project_id")

            if not chunk_project_id or not user_id:
                return False

            from uuid import UUID
            try:
                UUID(chunk_project_id)
            except (ValueError, TypeError):
                return False

            if project_id:
                return chunk_project_id == project_id

            return self.db_service.is_user_member(project_id=chunk_project_id, user_id=user_id)

        except Exception as e:
            logger.warning(f"Access check failed: {str(e)}")
            return False

    def _deduplicate_sources(self, chunks: List[Dict[str, Any]], max_chunks: int) -> List[Dict[str, Any]]:
        """Deduplicate chunks by keeping best chunks per asset."""
        if not chunks:
            return []

        # Group by asset_id
        asset_groups = {}
        for chunk in chunks:
            payload = chunk.get("payload", {})
            asset_id = payload.get("asset_id", "unknown")
            if asset_id not in asset_groups:
                asset_groups[asset_id] = []
            asset_groups[asset_id].append(chunk)

        # Keep up to 3 chunks per asset
        deduplicated_chunks = []
        for asset_chunks in asset_groups.values():
            asset_chunks.sort(key=lambda c: c.get("score", 0), reverse=True)
            deduplicated_chunks.extend(asset_chunks[:3])

        # Sort and limit
        deduplicated_chunks.sort(key=lambda c: c.get("score", 0), reverse=True)
        return deduplicated_chunks[:max_chunks]

    async def _generate_response(
        self,
        question: str,
        relevant_chunks: List[Dict[str, Any]],
        response_style: str,
        project_thread_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate response using LLM."""
        try:
            context = self._prepare_context(relevant_chunks)

            system_prompts = {
                "comprehensive": """You are a knowledgeable assistant helping users understand information from their knowledge base.
Provide comprehensive, well-structured answers using the provided context.
Include relevant details and explain concepts clearly.
Always ground your response in the provided context.""",
                "concise": """You are a helpful assistant providing concise, direct answers.
Give brief, to-the-point responses using only the most relevant information.""",
                "technical": """You are a technical expert providing detailed technical responses.
Include specific technical details, specifications, and implementation notes.""",
            }

            system_prompt = system_prompts.get(response_style, system_prompts["comprehensive"])

            # Add project context if available
            if project_thread_context:
                system_prompt += f"\n\nPROJECT CONTEXT: {project_thread_context}"

            # Use generate_response method which supports both OpenAI and Ollama
            response = await self.llm_team.generate_response(
                system_prompt=system_prompt,
                user_message=question,
                context=context,
                temperature=0.7,
            )

            return {
                "answer": response.get("content", ""),
                "confidence": "high" if len(relevant_chunks) >= 3 else "medium",
                "model_used": response.get("model", self.settings.llm_model),
                "provider_used": response.get("provider", self.settings.llm_provider),
            }

        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return {"answer": "I encountered an error generating a response.", "confidence": "low"}

    def _prepare_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Prepare context string from chunks."""
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            payload = chunk.get("payload", {})
            content = payload.get("content", "")
            if content:
                context_parts.append(f"[Source {i}]\n{content}")
        return "\n\n".join(context_parts)

    def _format_sources(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format sources for response."""
        sources = []
        for chunk in chunks:
            payload = chunk.get("payload", {})
            score = chunk.get("score", 0)
            source_type = chunk.get("source_type") or payload.get("source_type", "project")
            
            # Get asset metadata for title and document_type
            asset_id = payload.get("asset_id")
            title = payload.get("title") or payload.get("source_asset") or "Unknown Document"
            document_type = payload.get("document_type") or payload.get("doc_type") or "document"
            
            sources.append({
                "chunk_id": payload.get("chunk_id"),
                "asset_id": asset_id,
                "title": title,
                "document_type": document_type,
                "source_type": source_type,  # "training" or "project"
                "score": score,  # Keep for backward compatibility
                "relevance_score": score,  # API expects this field name
            })
        return sources
    
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
                from ...services.store import create_rag_store_service
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
