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
from ..retrieval.vector_retriever import VectorRetriever
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
        retriever: Optional[Retriever] = None,
        db_service: Optional[DatabaseService] = None,
        llm_team: Optional[LLMTeam] = None,
    ):
        """
        Initialize modular RAG service.

        Args:
            settings: Application settings
            vector_store: Optional vector store (creates from factory if not provided)
            retriever: Optional retriever (creates VectorRetriever if not provided)
            db_service: Optional database service (creates if not provided)
            llm_team: Optional LLM team (creates if not provided)
        """
        self.settings = settings

        # Initialize components (allow dependency injection for testing)
        self.vector_store = vector_store or create_vector_store(settings)
        self.retriever = retriever or VectorRetriever(self.vector_store)
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

            # Search both collections using modular retriever
            collections_results = await self.retriever.retrieve_multiple_collections(
                query=question,
                collections=["knowledge_chunks", "knowledge_chunks_768"],
                limit_per_collection=max_chunks * 2,
                score_threshold=similarity_threshold,
                metadata_filter=metadata_filter,
            )

            # Combine and deduplicate results
            all_results = []
            for collection_name, results in collections_results.items():
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

            # SQL read-through if enabled
            if self.sql_read_through:
                accessible_chunks = await self._enrich_chunks_with_sql_content(accessible_chunks)

            # Deduplicate sources and limit to max_chunks
            deduplicated_chunks = self._deduplicate_sources(accessible_chunks, max_chunks)

            return deduplicated_chunks

        except Exception as e:
            logger.error(f"Failed to retrieve relevant chunks: {str(e)}")
            return []

    async def _enrich_chunks_with_sql_content(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich vector chunks with SQL text content (SQL-first approach)."""
        try:
            chunk_ids = []
            chunk_id_to_vector_chunk = {}

            for chunk in chunks:
                payload = chunk.get("payload", {})
                chunk_id = payload.get("chunk_id")
                if chunk_id:
                    chunk_ids.append(chunk_id)
                    chunk_id_to_vector_chunk[chunk_id] = chunk

            if not chunk_ids:
                return chunks

            # Fetch from SQL
            conn = self.db_service._conn()
            try:
                from backend.db.queries import get_chunks_by_ids
                sql_chunks = get_chunks_by_ids(conn, chunk_ids)

                chunk_id_to_sql_text = {chunk["chunk_id"]: chunk["text"] for chunk in sql_chunks}

                # Enrich chunks
                enriched_chunks = []
                for chunk_id in chunk_ids:
                    if chunk_id in chunk_id_to_vector_chunk and chunk_id in chunk_id_to_sql_text:
                        vector_chunk = chunk_id_to_vector_chunk[chunk_id]
                        sql_text = chunk_id_to_sql_text[chunk_id]

                        enriched_chunk = {
                            "score": vector_chunk.get("score", 0),
                            "payload": {
                                **vector_chunk.get("payload", {}),
                                "content": sql_text,
                                "sql_read_through": True,
                            },
                        }
                        enriched_chunks.append(enriched_chunk)

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
            sources.append({
                "chunk_id": payload.get("chunk_id"),
                "asset_id": payload.get("asset_id"),
                "score": chunk.get("score", 0),
            })
        return sources

