"""
Integration tests for TaskScheduler.

Tests with real scheduling and execution.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock

from backend.services.task_scheduler import SimpleTaskScheduler, create_task_scheduler
from backend.services.config import Settings


@pytest.fixture
def scheduler():
    """Create SimpleTaskScheduler instance."""
    settings = Settings()
    return SimpleTaskScheduler(settings)


@pytest.fixture
def mock_task_func():
    """Create mock task function."""
    return AsyncMock(return_value={"result": "success"})


@pytest.mark.integration
class TestTaskSchedulerIntegration:
    """Integration tests for TaskScheduler."""
    
    def test_schedule_and_list_tasks(self, scheduler, mock_task_func):
        """Test scheduling and listing tasks."""
        # Schedule multiple tasks
        scheduler.schedule_periodic("task-1", mock_task_func, interval_seconds=60)
        scheduler.schedule_periodic("task-2", mock_task_func, interval_seconds=120)
        scheduler.schedule_once("task-3", mock_task_func, delay_seconds=30)
        
        tasks = scheduler.list_tasks()
        
        assert len(tasks) == 3
        task_ids = [t["task_id"] for t in tasks]
        assert "task-1" in task_ids
        assert "task-2" in task_ids
        assert "task-3" in task_ids
    
    def test_cancel_task_integration(self, scheduler, mock_task_func):
        """Test cancelling a task."""
        task_id = scheduler.schedule_periodic("test-cancel", mock_task_func, interval_seconds=60)
        
        # Verify task exists
        status = scheduler.get_task_status(task_id)
        assert status["status"] == "scheduled"
        
        # Cancel task
        cancelled = scheduler.cancel_task(task_id)
        assert cancelled is True
        
        # Verify task is gone
        status = scheduler.get_task_status(task_id)
        assert status["status"] == "not_found"
    
    @pytest.mark.asyncio
    async def test_start_stop_scheduler_integration(self, scheduler):
        """Test starting and stopping scheduler."""
        await scheduler.start()
        assert scheduler._running is True
        
        await scheduler.stop()
        assert scheduler._running is False
    
    def test_create_scheduler_factory(self):
        """Test creating scheduler via factory."""
        settings = Settings()
        scheduler = create_task_scheduler(settings)
        
        assert isinstance(scheduler, SimpleTaskScheduler)
        
        # Test scheduling a task
        mock_func = AsyncMock()
        task_id = scheduler.schedule_periodic("factory-task", mock_func, interval_seconds=60)
        assert task_id == "factory-task"
