"""
Proactive Worker Framework

Base classes and infrastructure for proactive workers that monitor system state,
review knowledge, and assist users proactively.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field

from .worker_interface import WorkerInterface
from .config import Settings

logger = logging.getLogger(__name__)


@dataclass
class WorkerStatus:
    """Worker status information."""
    status: str  # "running", "idle", "error", "stopped"
    last_run: Optional[datetime] = None
    last_error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    health: str = "healthy"  # "healthy", "degraded", "unhealthy"
    events_processed: int = 0
    scheduled_runs: int = 0


class BaseProactiveWorker(WorkerInterface):
    """
    Base class for proactive workers implementing WorkerInterface.
    
    Provides:
    - Event subscription and processing
    - Scheduled task execution
    - Status tracking and health monitoring
    - Lifecycle management
    """
    
    def __init__(self, settings: Settings, db_service=None):
        """
        Initialize base proactive worker.
        
        Args:
            settings: Application settings
            db_service: Optional database service
        """
        self.settings = settings
        self.db_service = db_service
        self._status = WorkerStatus(status="idle")
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._scheduler_task: Optional[asyncio.Task] = None
        self._event_queue: asyncio.Queue = asyncio.Queue()
        
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
    
    async def process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process an event from the event bus.
        
        Args:
            event: Event dictionary with type, payload, metadata
            
        Returns:
            Optional result dictionary if worker produced output, None otherwise
        """
        event_type = event.get("type") or event.get("event_type")
        
        # Check if worker subscribes to this event type
        if event_type not in self.subscribed_events:
            return None
        
        try:
            # Queue event for processing
            await self._event_queue.put(event)
            self._status.events_processed += 1
            logger.debug(f"{self.worker_name} queued event: {event_type}")
            return None
        except Exception as e:
            logger.error(f"{self.worker_name} failed to queue event: {e}")
            self._status.last_error = str(e)
            self._status.health = "degraded"
            return None
    
    async def run_scheduled(self) -> Optional[Dict[str, Any]]:
        """
        Run scheduled task (called periodically by scheduler).
        
        Returns:
            Optional result dictionary with status, metrics, actions taken
        """
        if not self._running:
            return None
        
        try:
            self._status.status = "running"
            logger.debug(f"{self.worker_name} running scheduled task")
            
            result = await self._execute_scheduled_task()
            
            self._status.last_run = datetime.now(timezone.utc)
            self._status.scheduled_runs += 1
            self._status.status = "idle"
            self._status.health = "healthy"
            
            return result
        except Exception as e:
            logger.error(f"{self.worker_name} scheduled task failed: {e}")
            self._status.last_error = str(e)
            self._status.health = "unhealthy"
            self._status.status = "error"
            return {"error": str(e)}
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get current worker status and health.
        
        Returns:
            Dictionary with status, metrics, health information
        """
        return {
            "worker_name": self.worker_name,
            "worker_type": self.worker_type,
            "status": self._status.status,
            "health": self._status.health,
            "last_run": self._status.last_run.isoformat() if self._status.last_run else None,
            "last_error": self._status.last_error,
            "events_processed": self._status.events_processed,
            "scheduled_runs": self._status.scheduled_runs,
            "metrics": self._status.metrics,
            "running": self._running,
        }
    
    async def start(self):
        """Start the worker."""
        if self._running:
            logger.warning(f"{self.worker_name} already running")
            return
        
        self._running = True
        self._status.status = "running"
        
        # Start event processing loop
        self._worker_task = asyncio.create_task(self._event_loop())
        logger.info(f"{self.worker_name} started")
        
        # Start scheduler if interval is set
        if self.schedule_interval:
            self._scheduler_task = asyncio.create_task(self._scheduler_loop())
            logger.info(f"{self.worker_name} scheduler started (interval: {self.schedule_interval}s)")
    
    async def stop(self):
        """Stop the worker."""
        self._running = False
        self._status.status = "stopped"
        
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"{self.worker_name} stopped")
    
    async def _event_loop(self):
        """Main event processing loop."""
        logger.info(f"{self.worker_name} event loop started")
        
        while self._running:
            try:
                # Wait for event with timeout
                try:
                    event = await asyncio.wait_for(
                        self._event_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Process event
                try:
                    await self._handle_event(event)
                except Exception as e:
                    logger.error(f"{self.worker_name} error processing event: {e}")
                    self._status.last_error = str(e)
                    self._status.health = "degraded"
                
            except asyncio.CancelledError:
                logger.info(f"{self.worker_name} event loop cancelled")
                break
            except Exception as e:
                logger.error(f"{self.worker_name} event loop error: {e}")
                await asyncio.sleep(1)  # Brief pause before retry
    
    async def _scheduler_loop(self):
        """Scheduled task execution loop."""
        logger.info(f"{self.worker_name} scheduler loop started")
        
        while self._running:
            try:
                await asyncio.sleep(self.schedule_interval)
                if self._running:
                    await self.run_scheduled()
            except asyncio.CancelledError:
                logger.info(f"{self.worker_name} scheduler loop cancelled")
                break
            except Exception as e:
                logger.error(f"{self.worker_name} scheduler loop error: {e}")
                await asyncio.sleep(1)  # Brief pause before retry
    
    @abstractmethod
    async def _handle_event(self, event: Dict[str, Any]) -> None:
        """
        Handle a single event (implemented by subclasses).
        
        Args:
            event: Event dictionary
        """
        pass
    
    @abstractmethod
    async def _execute_scheduled_task(self) -> Optional[Dict[str, Any]]:
        """
        Execute scheduled task (implemented by subclasses).
        
        Returns:
            Optional result dictionary
        """
        pass


class WorkerRegistry:
    """
    Registry for managing all proactive workers.
    
    Provides:
    - Worker registration and discovery
    - Event distribution to subscribed workers
    - Worker lifecycle management
    - Health monitoring
    """
    
    def __init__(self):
        self._workers: Dict[str, BaseProactiveWorker] = {}
        self._event_subscriptions: Dict[str, Set[str]] = {}  # event_type -> worker_names
    
    def register(self, worker: BaseProactiveWorker):
        """Register a worker."""
        worker_name = worker.worker_name
        
        if worker_name in self._workers:
            logger.warning(f"Worker {worker_name} already registered, replacing")
        
        self._workers[worker_name] = worker
        
        # Register event subscriptions
        for event_type in worker.subscribed_events:
            if event_type not in self._event_subscriptions:
                self._event_subscriptions[event_type] = set()
            self._event_subscriptions[event_type].add(worker_name)
        
        logger.info(f"Registered worker: {worker_name} (type: {worker.worker_type})")
    
    def unregister(self, worker_name: str):
        """Unregister a worker."""
        if worker_name not in self._workers:
            logger.warning(f"Worker {worker_name} not registered")
            return
        
        worker = self._workers[worker_name]
        
        # Remove event subscriptions
        for event_type in worker.subscribed_events:
            if event_type in self._event_subscriptions:
                self._event_subscriptions[event_type].discard(worker_name)
        
        del self._workers[worker_name]
        logger.info(f"Unregistered worker: {worker_name}")
    
    async def distribute_event(self, event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Distribute event to all subscribed workers.
        
        Args:
            event: Event dictionary
            
        Returns:
            List of results from workers that processed the event
        """
        event_type = event.get("type") or event.get("event_type")
        
        if event_type not in self._event_subscriptions:
            return []
        
        results = []
        worker_names = self._event_subscriptions[event_type]
        
        for worker_name in worker_names:
            if worker_name in self._workers:
                worker = self._workers[worker_name]
                try:
                    result = await worker.process_event(event)
                    if result:
                        results.append({"worker": worker_name, "result": result})
                except Exception as e:
                    logger.error(f"Worker {worker_name} failed to process event: {e}")
        
        return results
    
    async def start_all(self):
        """Start all registered workers."""
        for worker in self._workers.values():
            try:
                await worker.start()
            except Exception as e:
                logger.error(f"Failed to start worker {worker.worker_name}: {e}")
    
    async def stop_all(self):
        """Stop all registered workers."""
        for worker in self._workers.values():
            try:
                await worker.stop()
            except Exception as e:
                logger.error(f"Failed to stop worker {worker.worker_name}: {e}")
    
    def get_worker(self, worker_name: str) -> Optional[BaseProactiveWorker]:
        """Get worker by name."""
        return self._workers.get(worker_name)
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all workers."""
        return {
            name: worker.get_status()
            for name, worker in self._workers.items()
        }
    
    def list_workers(self) -> List[str]:
        """List all registered worker names."""
        return list(self._workers.keys())


# Global worker registry instance
_worker_registry: Optional[WorkerRegistry] = None


def get_worker_registry() -> WorkerRegistry:
    """Get global worker registry instance."""
    global _worker_registry
    if _worker_registry is None:
        _worker_registry = WorkerRegistry()
    return _worker_registry
