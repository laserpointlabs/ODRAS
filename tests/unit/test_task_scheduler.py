"""
Unit tests for TaskScheduler.

Tests scheduling logic with mocked components.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timezone

from backend.services.task_scheduler import (
    TaskSchedulerInterface,
    SimpleTaskScheduler,
    create_task_scheduler,
)
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


class TestTaskSchedulerInterface:
    """Test TaskSchedulerInterface contract."""
    
    def test_interface_cannot_be_instantiated(self):
        """Test that TaskSchedulerInterface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            TaskSchedulerInterface()  # Abstract class cannot be instantiated


class TestSimpleTaskScheduler:
    """Test SimpleTaskScheduler."""
    
    def test_schedule_periodic_task(self, scheduler, mock_task_func):
        """Test scheduling a periodic task."""
        task_id = scheduler.schedule_periodic(
            "test-task",
            mock_task_func,
            interval_seconds=60,
            arg1="value1",
        )
        
        assert task_id == "test-task"
        status = scheduler.get_task_status("test-task")
        assert status["type"] == "periodic"
        assert status["interval_seconds"] == 60
        assert status["status"] == "scheduled"
    
    def test_schedule_once_task(self, scheduler, mock_task_func):
        """Test scheduling a one-time task."""
        task_id = scheduler.schedule_once(
            "test-once-task",
            mock_task_func,
            delay_seconds=30,
        )
        
        assert task_id == "test-once-task"
        status = scheduler.get_task_status("test-once-task")
        assert status["type"] == "once"
        assert status["status"] == "scheduled"
    
    def test_cancel_task(self, scheduler, mock_task_func):
        """Test cancelling a task."""
        task_id = scheduler.schedule_periodic(
            "test-task",
            mock_task_func,
            interval_seconds=60,
        )
        
        assert scheduler.cancel_task(task_id) is True
        assert scheduler.cancel_task(task_id) is False  # Already cancelled
        
        status = scheduler.get_task_status(task_id)
        assert status["status"] == "not_found"
    
    def test_get_task_status(self, scheduler, mock_task_func):
        """Test getting task status."""
        task_id = scheduler.schedule_periodic(
            "test-task",
            mock_task_func,
            interval_seconds=60,
        )
        
        status = scheduler.get_task_status(task_id)
        
        assert status["task_id"] == "test-task"
        assert status["type"] == "periodic"
        assert status["status"] == "scheduled"
        assert "created_at" in status
        assert status["run_count"] == 0
    
    def test_list_tasks(self, scheduler, mock_task_func):
        """Test listing all tasks."""
        scheduler.schedule_periodic("task-1", mock_task_func, interval_seconds=60)
        scheduler.schedule_periodic("task-2", mock_task_func, interval_seconds=120)
        scheduler.schedule_once("task-3", mock_task_func, delay_seconds=30)
        
        tasks = scheduler.list_tasks()
        
        assert len(tasks) == 3
        task_ids = [t["task_id"] for t in tasks]
        assert "task-1" in task_ids
        assert "task-2" in task_ids
        assert "task-3" in task_ids
    
    def test_replace_existing_task(self, scheduler, mock_task_func):
        """Test replacing an existing task."""
        scheduler.schedule_periodic("test-task", mock_task_func, interval_seconds=60)
        
        # Replace with different interval
        scheduler.schedule_periodic("test-task", mock_task_func, interval_seconds=120)
        
        status = scheduler.get_task_status("test-task")
        assert status["interval_seconds"] == 120
    
    @pytest.mark.asyncio
    async def test_start_stop_scheduler(self, scheduler):
        """Test starting and stopping scheduler."""
        await scheduler.start()
        assert scheduler._running is True
        
        await scheduler.stop()
        assert scheduler._running is False


class TestTaskSchedulerFactory:
    """Test task scheduler factory."""
    
    def test_create_simple_scheduler(self):
        """Test creating simple scheduler."""
        settings = Settings()
        scheduler = create_task_scheduler(settings)
        
        assert isinstance(scheduler, SimpleTaskScheduler)
    
    def test_create_celery_scheduler_not_implemented(self):
        """Test that Celery scheduler is not yet implemented."""
        settings = Settings()
        
        with pytest.raises(NotImplementedError):
            create_task_scheduler(settings, scheduler_type="celery")
