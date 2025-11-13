"""
Worker Interface

Abstract interface for all proactive workers in the DAS system.
Workers monitor system state, review knowledge, and proactively assist users.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime


class WorkerInterface(ABC):
    """
    Abstract interface for all workers.
    
    Workers are proactive components that:
    - Monitor system state and user activity
    - Review knowledge quality and usage
    - Proactively suggest improvements or assistance
    - Run on schedules or respond to events
    """
    
    @abstractmethod
    async def process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process an event from the event bus.
        
        Args:
            event: Event dictionary with type, payload, metadata
            
        Returns:
            Optional result dictionary if worker produced output, None otherwise
        """
        pass
    
    @abstractmethod
    async def run_scheduled(self) -> Optional[Dict[str, Any]]:
        """
        Run scheduled task (called periodically by scheduler).
        
        Returns:
            Optional result dictionary with status, metrics, actions taken
        """
        pass
    
    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """
        Get current worker status and health.
        
        Returns:
            Dictionary with:
            - status: "running", "idle", "error"
            - last_run: timestamp of last execution
            - metrics: worker-specific metrics
            - health: overall health status
        """
        pass
    
    @property
    @abstractmethod
    def worker_name(self) -> str:
        """Return unique worker name/identifier."""
        pass
    
    @property
    @abstractmethod
    def worker_type(self) -> str:
        """Return worker type: 'monitor', 'review', 'assist', etc."""
        pass
    
    @property
    @abstractmethod
    def schedule_interval(self) -> Optional[int]:
        """
        Return schedule interval in seconds, or None if event-driven only.
        
        Returns:
            Seconds between scheduled runs, or None if only event-driven
        """
        pass
    
    @property
    @abstractmethod
    def subscribed_events(self) -> List[str]:
        """
        Return list of event types this worker subscribes to.
        
        Returns:
            List of event type strings (e.g., ['knowledge.uploaded', 'user.query'])
        """
        pass
