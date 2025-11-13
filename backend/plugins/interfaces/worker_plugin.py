"""
Worker Plugin Interface

Defines the interface for worker plugins that handle background processing.
"""

from abc import abstractmethod
from typing import Any, Callable, Dict, Optional

from ..manifest import PluginManifest
from .base import Plugin


class WorkerPlugin(Plugin):
    """
    Worker plugin interface.
    
    Workers handle background processing, task execution, and async operations.
    Examples: External Task Worker, Ingestion Worker, Event Capture Worker.
    """
    
    @abstractmethod
    async def start(self, **kwargs) -> None:
        """
        Start the worker.
        
        This should:
        - Initialize worker resources
        - Start background tasks/loops
        - Register with task queue if needed
        
        Args:
            **kwargs: Worker-specific startup parameters
        """
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """
        Stop the worker.
        
        This should:
        - Stop background tasks gracefully
        - Clean up resources
        - Unregister from task queue if needed
        """
        pass
    
    @abstractmethod
    def get_task_handlers(self) -> Dict[str, Callable]:
        """
        Get dictionary of task type -> handler function mappings.
        
        Returns:
            Dictionary mapping task type strings to handler functions
            Example: {"ingest_document": handle_ingest, "process_file": handle_process}
        """
        pass
    
    def get_health_check(self) -> Optional[callable]:
        """
        Get optional health check function.
        
        Returns:
            Function that returns health status dict, or None
        """
        return None

