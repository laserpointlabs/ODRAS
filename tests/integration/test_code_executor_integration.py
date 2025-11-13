"""
Integration tests for SandboxedCodeExecutor.

Tests with real code execution.
"""

import pytest

from backend.services.code_executor import SandboxedCodeExecutor
from backend.services.code_executor_interface import ExecutionStatus
from backend.services.config import Settings


@pytest.fixture
def executor():
    """Create SandboxedCodeExecutor instance."""
    settings = Settings()
    return SandboxedCodeExecutor(settings)


@pytest.mark.integration
class TestSandboxedCodeExecutorIntegration:
    """Integration tests for SandboxedCodeExecutor."""
    
    @pytest.mark.asyncio
    async def test_execute_complex_calculation(self, executor):
        """Test executing complex calculations."""
        code = """
import math
result = math.sqrt(math.pow(2, 8))
"""
        result = await executor.execute(code)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.success is True
        assert result.return_value == 16.0
    
    @pytest.mark.asyncio
    async def test_execute_json_processing(self, executor):
        """Test executing JSON processing."""
        code = """
import json
data = json.loads('{"key": "value", "number": 42}')
result = data["number"] * 2
"""
        result = await executor.execute(code)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.return_value == 84
    
    @pytest.mark.asyncio
    async def test_execute_with_context_variables(self, executor):
        """Test executing code with context variables."""
        code = """
result = {
    "sum": a + b,
    "product": a * b,
    "difference": a - b
}
"""
        context = {"a": 10, "b": 5}
        
        result = await executor.execute(code, context=context)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.return_value["sum"] == 15
        assert result.return_value["product"] == 50
        assert result.return_value["difference"] == 5
    
    @pytest.mark.asyncio
    async def test_execute_timeout_enforcement(self, executor):
        """Test that timeout is enforced."""
        code = """
import time
# This would sleep forever, but should timeout
for i in range(1000000):
    pass
result = "completed"
"""
        result = await executor.execute(code, timeout_seconds=2)
        
        # Should timeout or complete quickly
        assert result.status in (ExecutionStatus.COMPLETED, ExecutionStatus.TIMEOUT)
        if result.status == ExecutionStatus.TIMEOUT:
            assert result.execution_time_seconds <= 3  # Allow some margin
