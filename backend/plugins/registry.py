"""
Plugin Registry

Manages plugin registration, discovery, and lifecycle.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict

from fastapi import FastAPI

from .interfaces.base import Plugin, PluginType
from .manifest import PluginManifest
from ..services.config import Settings

logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    Central registry for all ODRAS plugins.
    
    Handles:
    - Plugin registration and discovery
    - Dependency resolution
    - Initialization order
    - Lifecycle management
    """
    
    def __init__(self):
        """Initialize plugin registry"""
        self._plugins: Dict[str, Plugin] = {}
        self._manifests: Dict[str, PluginManifest] = {}
        self._startup_hooks: List[Callable] = []
        self._shutdown_hooks: List[Callable] = []
        self._initialized: Set[str] = set()
    
    def register(self, plugin: Plugin, manifest: Optional[PluginManifest] = None) -> None:
        """
        Register a plugin with the registry.
        
        Args:
            plugin: Plugin instance
            manifest: Optional manifest (uses plugin.manifest if not provided)
        """
        manifest = manifest or plugin.manifest
        plugin_id = manifest.id
        
        if plugin_id in self._plugins:
            logger.warning(f"Plugin {plugin_id} already registered, overwriting")
        
        self._plugins[plugin_id] = plugin
        self._manifests[plugin_id] = manifest
        logger.info(f"Registered plugin: {plugin_id} ({manifest.name} v{manifest.version})")
    
    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """
        Get plugin by ID.
        
        Args:
            plugin_id: Plugin identifier
            
        Returns:
            Plugin instance, or None if not found
        """
        return self._plugins.get(plugin_id)
    
    def get_plugins_by_type(self, plugin_type: PluginType) -> List[Plugin]:
        """
        Get all plugins of a specific type.
        
        Args:
            plugin_type: Plugin type to filter by
            
        Returns:
            List of plugins of the specified type
        """
        return [
            plugin
            for plugin in self._plugins.values()
            if plugin.plugin_type == plugin_type
        ]
    
    def get_all_plugins(self) -> List[Plugin]:
        """
        Get all registered plugins.
        
        Returns:
            List of all plugins
        """
        return list(self._plugins.values())
    
    def resolve_dependencies(self) -> List[Plugin]:
        """
        Resolve plugin dependencies and return plugins in initialization order.
        
        Uses topological sort to ensure dependencies are initialized before dependents.
        
        Returns:
            List of plugins in dependency order
            
        Raises:
            ValueError: If circular dependencies are detected
        """
        # Build dependency graph
        graph: Dict[str, Set[str]] = defaultdict(set)
        in_degree: Dict[str, int] = {}
        
        # Initialize in-degree for all plugins
        for plugin_id in self._plugins:
            in_degree[plugin_id] = 0
        
        # Build graph and calculate in-degrees
        for plugin_id, manifest in self._manifests.items():
            for dep_id in manifest.dependencies:
                if dep_id not in self._plugins:
                    logger.warning(
                        f"Plugin {plugin_id} depends on {dep_id}, but {dep_id} is not registered"
                    )
                    continue
                graph[dep_id].add(plugin_id)
                in_degree[plugin_id] += 1
        
        # Topological sort (Kahn's algorithm)
        queue: List[str] = [pid for pid, degree in in_degree.items() if degree == 0]
        result: List[Plugin] = []
        
        while queue:
            plugin_id = queue.pop(0)
            result.append(self._plugins[plugin_id])
            
            for dependent_id in graph[plugin_id]:
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)
        
        # Check for circular dependencies
        if len(result) != len(self._plugins):
            remaining = set(self._plugins.keys()) - {p.plugin_id for p in result}
            raise ValueError(f"Circular dependency detected involving: {remaining}")
        
        return result
    
    async def initialize_all(
        self,
        app: FastAPI,
        settings: Settings,
        **kwargs
    ) -> None:
        """
        Initialize all registered plugins in dependency order.
        
        Args:
            app: FastAPI application instance
            settings: Application settings
            **kwargs: Additional initialization parameters
        """
        logger.info("Initializing all plugins...")
        
        # Resolve initialization order
        plugins = self.resolve_dependencies()
        
        # Initialize each plugin
        for plugin in plugins:
            if plugin.plugin_id in self._initialized:
                logger.debug(f"Plugin {plugin.plugin_id} already initialized, skipping")
                continue
            
            try:
                logger.info(f"Initializing plugin: {plugin.plugin_id}")
                
                # Call plugin-specific initialize
                if plugin.plugin_type == PluginType.WORKBENCH:
                    from ..services.db import DatabaseService
                    db = kwargs.get("db")
                    if db is None:
                        raise ValueError("DatabaseService required for workbench plugins")
                    await plugin.initialize(app=app, settings=settings, db=db, **kwargs)
                elif plugin.plugin_type == PluginType.DAS_ENGINE:
                    rag_service = kwargs.get("rag_service")
                    db_service = kwargs.get("db_service")
                    redis_client = kwargs.get("redis_client")
                    if not all([rag_service, db_service, redis_client]):
                        raise ValueError("RAG service, DB service, and Redis client required for DAS plugins")
                    await plugin.initialize(
                        settings=settings,
                        rag_service=rag_service,
                        db_service=db_service,
                        redis_client=redis_client,
                        **kwargs
                    )
                elif plugin.plugin_type == PluginType.WORKER:
                    await plugin.start(**kwargs)
                else:
                    await plugin.initialize(**kwargs)
                
                self._initialized.add(plugin.plugin_id)
                logger.info(f"✅ Plugin {plugin.plugin_id} initialized successfully")
                
            except Exception as e:
                logger.error(f"Failed to initialize plugin {plugin.plugin_id}: {e}", exc_info=True)
                if not plugin.manifest.enabled:
                    logger.warning(f"Plugin {plugin.plugin_id} is disabled, skipping")
                    continue
                raise
    
    async def shutdown_all(self) -> None:
        """
        Shutdown all initialized plugins in reverse order.
        """
        logger.info("Shutting down all plugins...")
        
        # Shutdown in reverse initialization order
        plugins = list(reversed(self.resolve_dependencies()))
        
        for plugin in plugins:
            if plugin.plugin_id not in self._initialized:
                continue
            
            try:
                logger.info(f"Shutting down plugin: {plugin.plugin_id}")
                
                if plugin.plugin_type == PluginType.WORKER:
                    await plugin.stop()
                else:
                    await plugin.shutdown()
                
                self._initialized.remove(plugin.plugin_id)
                logger.info(f"✅ Plugin {plugin.plugin_id} shut down successfully")
                
            except Exception as e:
                logger.error(f"Error shutting down plugin {plugin.plugin_id}: {e}", exc_info=True)
        
        logger.info("All plugins shut down")

