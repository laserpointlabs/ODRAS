"""
Indexing Service Interface

Abstract interface for indexing system entities.
This interface ensures decoupling between indexing implementations
and consumers (RAG, DAS, etc.).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class IndexingServiceInterface(ABC):
    """
    Abstract interface for indexing services.
    
    This interface defines the contract that all indexing service implementations
    must follow. It ensures that:
    1. Indexing is decoupled from specific entity sources
    2. Indexing can be tested with mocks
    3. Different indexing strategies can be swapped
    """
    
    @abstractmethod
    async def index_entity(
        self,
        entity_type: str,
        entity_id: str,
        content_summary: str,
        project_id: Optional[str] = None,
        entity_uri: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        domain: Optional[str] = None,
    ) -> str:
        """
        Index a system entity.
        
        Args:
            entity_type: Type of entity (file, event, ontology, requirement, etc.)
            entity_id: Unique identifier for the entity
            content_summary: Summary/content to index
            project_id: Optional project ID
            entity_uri: Optional URI/IRI of the entity
            metadata: Optional additional metadata
            tags: Optional list of tags
            domain: Optional domain category
        
        Returns:
            Index ID (UUID string) of the created index entry
        
        Raises:
            Exception: If indexing fails
        """
        pass
    
    @abstractmethod
    async def update_index(
        self,
        index_id: str,
        content_summary: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """
        Update an existing index entry.
        
        Args:
            index_id: Index entry ID
            content_summary: Updated summary/content
            metadata: Updated metadata (merged with existing)
            tags: Updated tags (replaces existing)
        
        Raises:
            Exception: If update fails
        """
        pass
    
    @abstractmethod
    async def delete_index(
        self,
        entity_type: str,
        entity_id: str,
    ) -> None:
        """
        Delete an index entry by entity type and ID.
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
        
        Raises:
            Exception: If deletion fails
        """
        pass
    
    @abstractmethod
    async def get_indexed_entities(
        self,
        entity_type: Optional[str] = None,
        project_id: Optional[str] = None,
        domain: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get indexed entities matching criteria.
        
        Args:
            entity_type: Filter by entity type
            project_id: Filter by project ID
            domain: Filter by domain
            tags: Filter by tags (entities must have all specified tags)
            limit: Maximum number of results
        
        Returns:
            List of index entry dictionaries
        """
        pass
