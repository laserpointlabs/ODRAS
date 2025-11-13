"""
RAG Service Interface

Abstract interface for RAG services. This interface ensures decoupling
between DAS and RAG implementations, allowing for easy testing and
swappable implementations.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .context_models import RAGContext


class RAGServiceInterface(ABC):
    """
    Abstract interface for RAG services.
    
    This interface defines the contract that all RAG service implementations
    must follow. It ensures that:
    1. RAG services return structured context (not formatted prompts)
    2. No LLM calls are made within RAG services
    3. Prompt formatting is handled by consumers (e.g., DAS)
    """
    
    @abstractmethod
    async def query_knowledge_base(
        self,
        query: str,
        context: Dict[str, Any],
    ) -> RAGContext:
        """
        Query the knowledge base and return structured context.
        
        Args:
            query: User's query/question
            context: Context dictionary containing:
                - project_id: Optional project ID for project-scoped queries
                - user_id: Optional user ID for access control
                - max_chunks: Maximum number of chunks to return (default: 5)
                - similarity_threshold: Minimum similarity score (default: 0.3)
                - Additional context as needed
        
        Returns:
            RAGContext containing retrieved chunks and metadata
        
        Raises:
            Exception: If query processing fails
        """
        pass
    
    @abstractmethod
    async def get_query_suggestions(
        self,
        context: Dict[str, Any],
    ) -> List[str]:
        """
        Get query suggestions based on available knowledge.
        
        Args:
            context: Context dictionary containing:
                - project_id: Optional project ID
                - user_id: Optional user ID
                - Additional context as needed
        
        Returns:
            List of suggested query strings
        """
        pass
    
    @abstractmethod
    async def store_conversation_messages(
        self,
        thread_id: str,
        messages: List[Dict[str, Any]],
        project_id: Optional[str] = None,
    ) -> None:
        """
        Store conversation messages in SQL-first storage.
        
        Args:
            thread_id: Thread identifier
            messages: List of message dictionaries with 'role' and 'content'
            project_id: Optional project ID
        """
        pass
