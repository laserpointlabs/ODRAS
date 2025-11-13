"""
Unit tests for SandboxedCodeExecutor.

Tests security restrictions and resource limits.
"""

import pytest
import asyncio

from backend.services.code_executor import SandboxedCodeExecutor
from backend.services.code_executor_interface import ExecutionStatus
from backend.services.config import Settings


@pytest.fixture
def executor():
    """Create SandboxedCodeExecutor instance."""
    settings = Settings()
    return SandboxedCodeExecutor(settings)


class TestSandboxedCodeExecutor:
    """Test SandboxedCodeExecutor."""
    
    def test_executor_properties(self, executor):
        """Test executor properties."""
        allowed = executor.get_default_allowed_imports()
        blocked = executor.get_default_blocked_imports()
        
        assert len(allowed) > 0
        assert len(blocked) > 0
        assert "json" in allowed
        assert "os" in blocked
    
    @pytest.mark.asyncio
    async def test_execute_simple_code(self, executor):
        """Test executing simple safe code."""
        code = """
result = 1 + 2
"""
        result = await executor.execute(code)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.success is True
        assert result.return_value == 3
    
    @pytest.mark.asyncio
    async def test_execute_with_output(self, executor):
        """Test executing code with output."""
        code = """
print("Hello, World!")
result = "success"
"""
        result = await executor.execute(code)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert "Hello, World!" in result.output
        assert result.return_value == "success"
    
    @pytest.mark.asyncio
    async def test_execute_with_context(self, executor):
        """Test executing code with context variables."""
        code = """
result = data * multiplier
"""
        context = {"data": 5, "multiplier": 3}
        
        result = await executor.execute(code, context=context)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.return_value == 15
    
    @pytest.mark.asyncio
    async def test_execute_with_timeout(self, executor):
        """Test execution timeout."""
        code = """
import time
time.sleep(60)  # Sleep for 60 seconds
"""
        result = await executor.execute(code, timeout_seconds=1)
        
        assert result.status == ExecutionStatus.TIMEOUT
        assert result.failed is True
    
    @pytest.mark.asyncio
    async def test_block_dangerous_imports(self, executor):
        """Test blocking dangerous imports."""
        code = """
import os
result = os.getcwd()
"""
        result = await executor.execute(code)
        
        # Should fail due to blocked import (caught by safety check)
        assert result.status == ExecutionStatus.FAILED
        assert "os" in result.error.lower() or "safety check" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_allow_safe_imports(self, executor):
        """Test allowing safe imports."""
        code = """
import json
data = json.dumps({"key": "value"})
result = data
"""
        result = await executor.execute(code)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_validate_safe_code(self, executor):
        """Test validating safe code."""
        code = """
import json
result = json.loads('{"key": "value"}')
"""
        validation = await executor.validate_safety(code)
        
        assert validation["safe"] is True
        assert len(validation["blocked_operations"]) == 0
    
    @pytest.mark.asyncio
    async def test_validate_unsafe_code(self, executor):
        """Test validating unsafe code."""
        code = """
import os
result = os.getcwd()
"""
        validation = await executor.validate_safety(code)
        
        assert validation["safe"] is False
        assert len(validation["blocked_operations"]) > 0
    
    @pytest.mark.asyncio
    async def test_validate_syntax_error(self, executor):
        """Test validating code with syntax error."""
        code = "def invalid syntax here"
        
        validation = await executor.validate_safety(code)
        
        assert validation["safe"] is False
        assert "syntax_error" in validation["blocked_operations"]
    
    @pytest.mark.asyncio
    async def test_execute_calculation(self, executor):
        """Test executing mathematical calculations."""
        code = """
import math
result = math.sqrt(16)
"""
        result = await executor.execute(code)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.return_value == 4.0
    
    @pytest.mark.asyncio
    async def test_execute_error_handling(self, executor):
        """Test error handling during execution."""
        code = """
result = undefined_variable + 1
"""
        result = await executor.execute(code)
        
        assert result.status == ExecutionStatus.FAILED
        assert result.error is not None
        assert "undefined" in result.error.lower() or "name" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_get_execution_status(self, executor):
        """Test getting execution status."""
        code = "result = 42"
        result = await executor.execute(code)
        
        # Get status using execution_id from metadata
        execution_id = result.metadata.get("execution_id")
        if execution_id:
            status = await executor.get_execution_status(execution_id)
            assert status is not None
            assert status.status == ExecutionStatus.COMPLETED
