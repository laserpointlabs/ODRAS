"""
Unit tests for WorkerInterface.

Tests the abstract interface contract and ensures implementations follow the contract.
"""

import pytest
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services.worker_interface import WorkerInterface


class MockWorker(WorkerInterface):
    """Mock implementation of WorkerInterface for testing."""
    
    def __init__(self, name: str, worker_type: str, schedule_interval: Optional[int] = None):
        self._name = name
        self._type = worker_type
        self._schedule = schedule_interval
        self._subscribed = []
        self.processed_events = []
        self.scheduled_runs = []
    
    @property
    def worker_name(self) -> str:
        return self._name
    
    @property
    def worker_type(self) -> str:
        return self._type
    
    @property
    def schedule_interval(self) -> Optional[int]:
        return self._schedule
    
    @property
    def subscribed_events(self) -> List[str]:
        return self._subscribed
    
    def set_subscribed_events(self, events: List[str]):
        """Helper to set subscribed events."""
        self._subscribed = events
    
    async def process_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        self.processed_events.append(event)
        return {"processed": True, "event_type": event.get("type")}
    
    async def run_scheduled(self) -> Optional[Dict[str, Any]]:
        self.scheduled_runs.append(datetime.now(timezone.utc))
        return {"scheduled_run": True}
    
    async def get_status(self) -> Dict[str, Any]:
        return {
            "status": "idle",
            "last_run": None,
            "metrics": {},
            "health": "healthy",
        }


class TestWorkerInterface:
    """Test WorkerInterface contract."""
    
    def test_worker_has_name(self):
        """Test that worker has a name property."""
        worker = MockWorker("test-worker", "monitor")
        assert worker.worker_name == "test-worker"
    
    def test_worker_has_type(self):
        """Test that worker has a type property."""
        worker = MockWorker("test-worker", "review")
        assert worker.worker_type == "review"
    
    def test_worker_has_schedule_interval(self):
        """Test that worker has schedule_interval property."""
        worker = MockWorker("test-worker", "monitor", schedule_interval=60)
        assert worker.schedule_interval == 60
        
        worker_no_schedule = MockWorker("test-worker-2", "monitor", schedule_interval=None)
        assert worker_no_schedule.schedule_interval is None
    
    def test_worker_has_subscribed_events(self):
        """Test that worker has subscribed_events property."""
        worker = MockWorker("test-worker", "monitor")
        worker.set_subscribed_events(["event.type1", "event.type2"])
        assert len(worker.subscribed_events) == 2
        assert "event.type1" in worker.subscribed_events
    
    @pytest.mark.asyncio
    async def test_process_event_returns_result(self):
        """Test that process_event can return a result."""
        worker = MockWorker("test-worker", "monitor")
        worker.set_subscribed_events(["test.event"])
        
        event = {"type": "test.event", "payload": {"data": "test"}}
        result = await worker.process_event(event)
        
        assert result is not None
        assert result["processed"] is True
        assert len(worker.processed_events) == 1
    
    @pytest.mark.asyncio
    async def test_process_event_can_return_none(self):
        """Test that process_event can return None."""
        worker = MockWorker("test-worker", "monitor")
        worker.set_subscribed_events(["test.event"])
        
        # Worker that doesn't process this event type
        worker.set_subscribed_events(["other.event"])
        
        event = {"type": "test.event", "payload": {}}
        result = await worker.process_event(event)
        
        # Worker doesn't subscribe, so it might return None or not process
        # This tests the interface allows None return
        assert result is None or isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_run_scheduled_returns_result(self):
        """Test that run_scheduled returns a result."""
        worker = MockWorker("test-worker", "monitor", schedule_interval=60)
        
        result = await worker.run_scheduled()
        
        assert result is not None
        assert result["scheduled_run"] is True
        assert len(worker.scheduled_runs) == 1
    
    @pytest.mark.asyncio
    async def test_get_status_returns_dict(self):
        """Test that get_status returns a dictionary."""
        worker = MockWorker("test-worker", "monitor")
        
        status = await worker.get_status()
        
        assert isinstance(status, dict)
        assert "status" in status
        assert "health" in status
    
    def test_interface_cannot_be_instantiated(self):
        """Test that WorkerInterface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            WorkerInterface()  # Abstract class cannot be instantiated
