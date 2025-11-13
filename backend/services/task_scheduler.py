"""
Task Scheduler Service

Abstract scheduler interface for scheduling periodic tasks.
Supports distributed task execution and integrates with worker infrastructure.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime, timezone

from .config import Settings

logger = logging.getLogger(__name__)


class TaskSchedulerInterface(ABC):
    """
    Abstract interface for task scheduling.
    
    Provides decoupled scheduling that can work with:
    - Simple in-process scheduling
    - Celery for distributed execution
    - Other task queue systems
    """
    
    @abstractmethod
    def schedule_periodic(
        self,
        task_id: str,
        task_func: Callable,
        interval_seconds: int,
        **kwargs
    ) -> str:
        """
        Schedule a periodic task.
        
        Args:
            task_id: Unique identifier for the task
            task_func: Async function to execute
            interval_seconds: Interval between executions in seconds
            **kwargs: Additional arguments to pass to task function
            
        Returns:
            Task identifier string
        """
        pass
    
    @abstractmethod
    def schedule_once(
        self,
        task_id: str,
        task_func: Callable,
        delay_seconds: int = 0,
        **kwargs
    ) -> str:
        """
        Schedule a one-time task.
        
        Args:
            task_id: Unique identifier for the task
            task_func: Async function to execute
            delay_seconds: Delay before execution in seconds
            **kwargs: Additional arguments to pass to task function
            
        Returns:
            Task identifier string
        """
        pass
    
    @abstractmethod
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a scheduled task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            True if task was cancelled, False if not found
        """
        pass
    
    @abstractmethod
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get status of a scheduled task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Dictionary with task status information
        """
        pass
    
    @abstractmethod
    def list_tasks(self) -> List[Dict[str, Any]]:
        """
        List all scheduled tasks.
        
        Returns:
            List of task dictionaries with status information
        """
        pass


class SimpleTaskScheduler(TaskSchedulerInterface):
    """
    Simple in-process task scheduler.
    
    Uses asyncio for scheduling tasks within the same process.
    Suitable for single-instance deployments.
    """
    
    def __init__(self, settings: Settings):
        """Initialize simple task scheduler."""
        self.settings = settings
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._running = False
    
    def schedule_periodic(
        self,
        task_id: str,
        task_func: Callable,
        interval_seconds: int,
        **kwargs
    ) -> str:
        """Schedule a periodic task."""
        if task_id in self._tasks:
            logger.warning(f"Task {task_id} already scheduled, replacing")
            self.cancel_task(task_id)
        
        self._tasks[task_id] = {
            "task_id": task_id,
            "task_func": task_func,
            "interval_seconds": interval_seconds,
            "kwargs": kwargs,
            "type": "periodic",
            "status": "scheduled",
            "created_at": datetime.now(timezone.utc),
            "last_run": None,
            "next_run": None,
            "run_count": 0,
        }
        
        logger.info(f"Scheduled periodic task {task_id} with interval {interval_seconds}s")
        return task_id
    
    def schedule_once(
        self,
        task_id: str,
        task_func: Callable,
        delay_seconds: int = 0,
        **kwargs
    ) -> str:
        """Schedule a one-time task."""
        if task_id in self._tasks:
            logger.warning(f"Task {task_id} already scheduled, replacing")
            self.cancel_task(task_id)
        
        self._tasks[task_id] = {
            "task_id": task_id,
            "task_func": task_func,
            "delay_seconds": delay_seconds,
            "kwargs": kwargs,
            "type": "once",
            "status": "scheduled",
            "created_at": datetime.now(timezone.utc),
            "last_run": None,
            "next_run": None,
            "run_count": 0,
        }
        
        logger.info(f"Scheduled one-time task {task_id} with delay {delay_seconds}s")
        return task_id
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        if task_id not in self._tasks:
            return False
        
        task = self._tasks[task_id]
        task["status"] = "cancelled"
        del self._tasks[task_id]
        
        logger.info(f"Cancelled task {task_id}")
        return True
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a scheduled task."""
        if task_id not in self._tasks:
            return {
                "task_id": task_id,
                "status": "not_found",
            }
        
        task = self._tasks[task_id]
        status = {
            "task_id": task["task_id"],
            "type": task["type"],
            "status": task["status"],
            "created_at": task["created_at"].isoformat() if task["created_at"] else None,
            "last_run": task["last_run"].isoformat() if task["last_run"] else None,
            "next_run": task["next_run"].isoformat() if task["next_run"] else None,
            "run_count": task["run_count"],
        }
        
        # Add type-specific fields
        if task["type"] == "periodic":
            status["interval_seconds"] = task["interval_seconds"]
        elif task["type"] == "once":
            status["delay_seconds"] = task["delay_seconds"]
        
        return status
    
    def list_tasks(self) -> List[Dict[str, Any]]:
        """List all scheduled tasks."""
        return [self.get_task_status(task_id) for task_id in self._tasks.keys()]
    
    async def start(self):
        """Start the scheduler (begin executing tasks)."""
        if self._running:
            logger.warning("Scheduler already running")
            return
        
        self._running = True
        logger.info("Simple task scheduler started")
        
        # Note: Actual task execution would be handled by worker framework
        # This scheduler just tracks task definitions
    
    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        logger.info("Simple task scheduler stopped")


def create_task_scheduler(settings: Settings, scheduler_type: Optional[str] = None) -> TaskSchedulerInterface:
    """
    Factory function to create appropriate task scheduler.
    
    Args:
        settings: Application settings
        scheduler_type: Optional scheduler type override ("simple", "celery")
        
    Returns:
        TaskSchedulerInterface implementation
    """
    # For now, use simple scheduler
    # In future, could check settings for Celery or other backends
    if scheduler_type is None:
        scheduler_type = getattr(settings, "task_scheduler_backend", "simple")
    
    scheduler_type = scheduler_type.lower()
    
    if scheduler_type == "simple":
        return SimpleTaskScheduler(settings)
    elif scheduler_type == "celery":
        # Future: CeleryTaskScheduler implementation
        raise NotImplementedError("Celery scheduler not yet implemented")
    else:
        raise ValueError(f"Unknown task scheduler backend: {scheduler_type}")
