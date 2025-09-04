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

    async def query_knowledge_base(
        self,
        question: str,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        max_chunks: int = 5,
        similarity_threshold: float = 0.5,
        include_metadata: bool = True,
        response_style: str = "comprehensive"
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
                similarity_threshold=similarity_threshold
            )

            if not relevant_chunks:
                return {
                    "success": True,
                    "response": "I couldn't find any relevant information in the knowledge base to answer your question. You may want to try rephrasing your question or adding more knowledge assets to your project.",
                    "sources": [],
                    "query": question,
                    "chunks_found": 0,
                    "generated_at": datetime.utcnow().isoformat()
                }

            # 2. Generate response using LLM with retrieved context
            response_data = await self._generate_response(
                question=question,
                relevant_chunks=relevant_chunks,
                response_style=response_style
            )

            # 3. Format final response
            result = {
                "success": True,
                "response": response_data["answer"],
                "confidence": response_data.get("confidence", "medium"),
                "sources": self._format_sources(relevant_chunks) if include_metadata else [],
                "query": question,
                "chunks_found": len(relevant_chunks),
                "response_style": response_style,
                "generated_at": datetime.utcnow().isoformat(),
                "model_used": self.settings.llm_model,
                "provider": self.settings.llm_provider
            }

            logger.info(f"Successfully generated RAG response with {len(relevant_chunks)} chunks")
            return result

        except Exception as e:
            logger.error(f"RAG query failed: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to process query: {str(e)}",
                "query": question,
                "generated_at": datetime.utcnow().isoformat()
            }

    async def _retrieve_relevant_chunks(
        self,
        question: str,
        project_id: Optional[str],
        user_id: Optional[str],
        max_chunks: int,
        similarity_threshold: float
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant knowledge chunks using vector similarity search.
        """
        try:
            # Perform vector search in the knowledge_chunks collection
            search_results = await self.qdrant_service.search_similar_chunks(
                query_text=question,
                collection_name="knowledge_chunks",
                limit=max_chunks * 2,  # Get extra results for filtering
                score_threshold=similarity_threshold
            )

            # Filter chunks based on project access permissions
            accessible_chunks = []
            for chunk in search_results:
                if await self._has_chunk_access(chunk, project_id, user_id):
                    accessible_chunks.append(chunk)
                    if len(accessible_chunks) >= max_chunks:
                        break

            return accessible_chunks

        except Exception as e:
            logger.error(f"Failed to retrieve relevant chunks: {str(e)}")
            return []

    async def _has_chunk_access(
        self,
        chunk: Dict[str, Any],
        project_id: Optional[str],
        user_id: Optional[str]
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
                                (asset_id,)
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
            return self.db_service.is_user_member(
                project_id=chunk_project_id,
                user_id=user_id
            )

        except Exception as e:
            logger.warning(f"Access check failed for chunk: {str(e)}")
            return False

    async def _generate_response(
        self,
        question: str,
        relevant_chunks: List[Dict[str, Any]],
        response_style: str
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
                Focus on accuracy and completeness of technical information."""
            }

            system_prompt = system_prompts.get(response_style, system_prompts["comprehensive"])

            # Create user prompt with context and question
            user_prompt = f"""Context from knowledge base:
{context}

User Question: {question}

Please provide a helpful response based on the context provided. If the context doesn't contain enough information to fully answer the question, acknowledge this and provide what information you can."""

            # Use the existing LLM team infrastructure
            # Create a simple schema for RAG responses
            response_schema = {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "The main response to the user's question"
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Confidence level in the response based on context quality"
                    },
                    "key_points": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key points covered in the response"
                    }
                },
                "required": ["answer", "confidence"]
            }

            # Call LLM with custom persona for RAG
            custom_personas = [{
                "name": "Knowledge Assistant",
                "system_prompt": system_prompt,
                "is_active": True
            }]

            # Use the analyze_requirement method adapted for RAG
            llm_response = await self.llm_team.analyze_requirement(
                requirement_text=user_prompt,
                ontology_json_schema=response_schema,
                custom_personas=custom_personas
            )

            return llm_response

        except Exception as e:
            logger.error(f"Failed to generate LLM response: {str(e)}")
            return {
                "answer": "I encountered an error while generating a response. Please try again.",
                "confidence": "low",
                "error": str(e)
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
                    
                    if asset_id and asset_id not in seen_assets:
                        # Look up actual asset title from database
                        cur.execute("SELECT title FROM knowledge_assets WHERE id = %s", (asset_id,))
                        result = cur.fetchone()
                        asset_title = result[0] if result else "Unknown Document"
                        
                        source = {
                            "asset_id": asset_id,
                            "title": asset_title,  # ACTUAL ASSET TITLE FROM DATABASE!
                            "document_type": chunk_data.get("document_type", "document"),
                            "chunk_id": chunk_data.get("chunk_id"),
                            "relevance_score": chunk.get("score", 0.0)
                        }
                        sources.append(source)
                        seen_assets.add(asset_id)
        finally:
            db_service._return(conn)
        
        return sources

    async def get_query_suggestions(
        self,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 5
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
                        cur.execute(f"{base_query} WHERE ka.project_id = %s LIMIT %s", (project_id, limit * 2))
                    else:
                        # Get user's projects + public assets
                        user_projects = self.db_service.list_projects_for_user(user_id=user_id, active=True)
                        if not user_projects:
                            return []
                        
                        project_ids = [str(p["project_id"]) for p in user_projects]
                        placeholders = ",".join(["%s"] * len(project_ids))
                        cur.execute(
                            f"{base_query} WHERE (ka.project_id IN ({placeholders}) OR ka.is_public = true) LIMIT %s",
                            project_ids + [limit * 2]
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
                "Show me the compliance requirements"
            ]
            
            suggestions.extend(generic_suggestions)
            
            return suggestions[:limit]
            
        except Exception as e:
            logger.error(f"Failed to generate query suggestions: {str(e)}")
            return [
                "What are the main requirements?",
                "Summarize the key documents",
                "What safety considerations are mentioned?",
                "What are the technical specifications?"
            ]


def get_rag_service() -> RAGService:
    """Factory function to get RAG service instance."""
    settings = Settings()
    return RAGService(settings)
