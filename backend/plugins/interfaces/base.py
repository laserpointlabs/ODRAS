"""
Base Plugin Interface

Defines the core plugin interface that all plugins must implement.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional

from ..manifest import PluginManifest


class PluginType(Enum):
    """Plugin type enumeration"""
    WORKBENCH = "workbench"
    DAS_ENGINE = "das_engine"
    WORKER = "worker"
    MIDDLEWARE = "middleware"


class Plugin(ABC):
    """
    Base plugin interface that all plugins must implement.
    
    Plugins are the fundamental building blocks of ODRAS, providing
    modular, hot-swappable components for workbenches, DAS engines, workers, etc.
    """
    
    def __init__(self, manifest: PluginManifest):
        """
        Initialize plugin with manifest.
        
        Args:
            manifest: Plugin manifest containing metadata and configuration
        """
        self.manifest = manifest
    
    @property
    def plugin_id(self) -> str:
        """Get plugin ID from manifest"""
        return self.manifest.id
    
    @property
    def plugin_type(self) -> PluginType:
        """Get plugin type from manifest"""
        return PluginType(self.manifest.type)
    
    @abstractmethod
    async def initialize(self, **kwargs) -> None:
        """
        Initialize the plugin.
        
        This is called during application startup after all dependencies
        are available. Plugins should perform any setup needed here.
        
        Args:
            **kwargs: Plugin-specific initialization parameters
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """
        Shutdown the plugin.
        
        This is called during application shutdown. Plugins should
        clean up resources here.
        """
        pass
    
    def get_health_check(self) -> Optional[callable]:
        """
        Get optional health check function for this plugin.
        
        Returns:
            Health check function that returns health status, or None
        """
        return None
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get plugin metadata.
        
        Returns:
            Dictionary containing plugin metadata
        """
        return {
            "id": self.manifest.id,
            "name": self.manifest.name,
            "version": self.manifest.version,
            "type": self.manifest.type,
            "description": self.manifest.description,
            "author": self.manifest.author,
        }

