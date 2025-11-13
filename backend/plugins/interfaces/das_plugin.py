"""
DAS Engine Plugin Interface

Defines the interface for DAS (Design Assistant System) engine plugins.
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional

from fastapi.routing import APIRouter

from ..manifest import PluginManifest
from .base import Plugin
from ...services.config import Settings
from ...services.db import DatabaseService
from ...rag.core.modular_rag_service import ModularRAGService
from ...services.das_core_engine import DASResponse


class DASEnginePlugin(Plugin):
    """
    DAS engine plugin interface.
    
    DAS engines provide AI reasoning and conversation capabilities.
    Multiple DAS engines can be registered (e.g., DAS2, DAS3, custom engines).
    """
    
    @abstractmethod
    async def initialize(
        self,
        settings: Settings,
        rag_service: ModularRAGService,
        db_service: DatabaseService,
        redis_client: Any,
        **kwargs
    ) -> None:
        """
        Initialize the DAS engine plugin.
        
        Args:
            settings: Application settings
            rag_service: RAG service instance
            db_service: Database service instance
            redis_client: Redis client instance
            **kwargs: Additional initialization parameters
        """
        pass
    
    @abstractmethod
    async def process_message(
        self,
        message: str,
        context: Dict[str, Any],
        **kwargs
    ) -> DASResponse:
        """
        Process a user message and generate a response.
        
        Args:
            message: User message text
            context: Conversation context (project_id, thread_id, etc.)
            **kwargs: Additional processing parameters
            
        Returns:
            DASResponse with message and context
        """
        pass
    
    @abstractmethod
    async def get_suggestions(
        self,
        context: Dict[str, Any],
        **kwargs
    ) -> List[str]:
        """
        Get suggested follow-up questions or actions.
        
        Args:
            context: Current conversation context
            **kwargs: Additional parameters
            
        Returns:
            List of suggestion strings
        """
        pass
    
    def get_api_router(self) -> Optional[APIRouter]:
        """
        Get optional API router for DAS-specific endpoints.
        
        Returns:
            APIRouter instance, or None if no custom endpoints
        """
        return None
