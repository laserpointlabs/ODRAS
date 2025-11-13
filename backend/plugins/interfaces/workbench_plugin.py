"""
Workbench Plugin Interface

Defines the interface for workbench plugins.
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.routing import APIRouter

from ..manifest import PluginManifest
from .base import Plugin
from ...services.config import Settings
from ...services.db import DatabaseService


class WorkbenchPlugin(Plugin):
    """
    Workbench plugin interface.
    
    Workbenches provide UI panels and functionality for specific domains
    (Requirements, Ontology, Knowledge, etc.).
    """
    
    def __init__(self, manifest: PluginManifest):
        """
        Initialize workbench plugin.
        
        Args:
            manifest: Plugin manifest
        """
        super().__init__(manifest)
        self.router: Optional[APIRouter] = None
    
    @abstractmethod
    async def initialize(
        self,
        app: FastAPI,
        settings: Settings,
        db: DatabaseService,
        **kwargs
    ) -> None:
        """
        Initialize the workbench plugin.
        
        This should:
        - Create and configure the API router
        - Register routes with the FastAPI app
        - Initialize any workbench-specific services
        - Set up database connections if needed
        
        Args:
            app: FastAPI application instance
            settings: Application settings
            db: Database service instance
            **kwargs: Additional initialization parameters
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """
        Shutdown the workbench plugin.
        
        Clean up resources, close connections, etc.
        """
        pass
    
    @abstractmethod
    def get_frontend_config(self) -> Dict[str, Any]:
        """
        Get frontend configuration for this workbench.
        
        Returns:
            Dictionary containing:
            - panel_id: Unique panel identifier
            - panel_title: Display title
            - icon: Icon identifier or path
            - shortcut: Keyboard shortcut (e.g., "F1")
            - position: Panel position preference
            - size: Default panel size
            - dependencies: Frontend module dependencies
        """
        pass
    
    def get_api_router(self) -> Optional[APIRouter]:
        """
        Get the API router for this workbench.
        
        Returns:
            APIRouter instance, or None if no API routes
        """
        return self.router
    
    def get_database_migrations(self) -> List[str]:
        """
        Get list of database migration SQL files.
        
        Returns:
            List of migration file paths (relative to plugin directory)
        """
        return []
    
    def get_permissions(self) -> List[str]:
        """
        Get list of required permissions for this workbench.
        
        Returns:
            List of permission identifiers
        """
        return []

