"""
Unit tests for CodeExecutorInterface.

Tests interface contract and abstract methods.
"""

import pytest
from abc import ABC
from typing import Optional, Dict, List, Any

from backend.services.code_executor_interface import (
    CodeExecutorInterface,
    ExecutionResult,
    ExecutionStatus,
    ExecutionError,
)


class ConcreteCodeExecutor(CodeExecutorInterface):
    """Concrete implementation for testing."""
    
    def __init__(self):
        self._executions: dict = {}
        self._execution_counter = 0
    
    async def execute(
        self,
        code: str,
        timeout_seconds: Optional[int] = None,
        memory_limit_mb: Optional[int] = None,
        allowed_imports: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """Execute code."""
        execution_id = f"exec_{self._execution_counter}"
        self._execution_counter += 1
        
        # Simple mock execution
        try:
            # Simulate execution
            result = ExecutionResult(
                status=ExecutionStatus.COMPLETED,
                output="Execution completed",
                return_value={"result": "success"},
                execution_time_seconds=0.1,
            )
            self._executions[execution_id] = result
            return result
        except Exception as e:
            result = ExecutionResult(
                status=ExecutionStatus.FAILED,
                error=str(e),
            )
            self._executions[execution_id] = result
            return result
    
    async def validate_safety(
        self,
        code: str,
        strict: bool = True
    ) -> Dict[str, Any]:
        """Validate code safety."""
        blocked = []
        if "import os" in code:
            blocked.append("os")
        
        return {
            "safe": len(blocked) == 0,
            "warnings": [],
            "blocked_operations": blocked,
            "risk_score": 0.5 if blocked else 0.0,
        }
    
    async def get_execution_status(
        self,
        execution_id: str
    ) -> Optional[ExecutionResult]:
        """Get execution status."""
        return self._executions.get(execution_id)
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel execution."""
        if execution_id in self._executions:
            result = self._executions[execution_id]
            if result.status == ExecutionStatus.RUNNING:
                result.status = ExecutionStatus.CANCELLED
                return True
        return False
    
    def get_default_allowed_imports(self) -> List[str]:
        """Get default allowed imports."""
        return ["json", "math", "datetime"]
    
    def get_default_blocked_imports(self) -> List[str]:
        """Get default blocked imports."""
        return ["os", "subprocess", "sys"]


class TestCodeExecutorInterface:
    """Test CodeExecutorInterface contract."""
    
    def test_interface_is_abstract(self):
        """Test that interface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            CodeExecutorInterface()
    
    def test_concrete_implementation(self):
        """Test that concrete implementation works."""
        executor = ConcreteCodeExecutor()
        assert isinstance(executor, CodeExecutorInterface)
        assert isinstance(executor, ABC)
    
    @pytest.mark.asyncio
    async def test_execute_code(self):
        """Test code execution."""
        executor = ConcreteCodeExecutor()
        
        result = await executor.execute("print('test')")
        
        assert isinstance(result, ExecutionResult)
        assert result.status == ExecutionStatus.COMPLETED
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_execute_with_timeout(self):
        """Test execution with timeout."""
        executor = ConcreteCodeExecutor()
        
        result = await executor.execute("print('test')", timeout_seconds=10)
        
        assert result.status == ExecutionStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_validate_safety(self):
        """Test safety validation."""
        executor = ConcreteCodeExecutor()
        
        # Safe code
        result = await executor.validate_safety("import json")
        assert result["safe"] is True
        
        # Unsafe code
        result = await executor.validate_safety("import os")
        assert result["safe"] is False
        assert len(result["blocked_operations"]) > 0
    
    @pytest.mark.asyncio
    async def test_get_execution_status(self):
        """Test getting execution status."""
        executor = ConcreteCodeExecutor()
        
        # Execute code first
        result = await executor.execute("print('test')")
        
        # Get status (note: our mock doesn't return execution_id, so this tests the pattern)
        status = await executor.get_execution_status("exec_0")
        assert status is not None
        assert status.status == ExecutionStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_cancel_execution(self):
        """Test cancelling execution."""
        executor = ConcreteCodeExecutor()
        
        # Cancel non-existent execution
        cancelled = await executor.cancel_execution("nonexistent")
        assert cancelled is False
    
    def test_get_default_allowed_imports(self):
        """Test getting default allowed imports."""
        executor = ConcreteCodeExecutor()
        
        imports = executor.get_default_allowed_imports()
        
        assert isinstance(imports, list)
        assert "json" in imports
    
    def test_get_default_blocked_imports(self):
        """Test getting default blocked imports."""
        executor = ConcreteCodeExecutor()
        
        imports = executor.get_default_blocked_imports()
        
        assert isinstance(imports, list)
        assert "os" in imports


class TestExecutionResult:
    """Test ExecutionResult."""
    
    def test_create_result(self):
        """Test creating execution result."""
        result = ExecutionResult(
            status=ExecutionStatus.COMPLETED,
            output="Success",
            return_value={"data": "test"},
        )
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.output == "Success"
        assert result.return_value == {"data": "test"}
        assert result.success is True
        assert result.failed is False
    
    def test_failed_result(self):
        """Test failed execution result."""
        result = ExecutionResult(
            status=ExecutionStatus.FAILED,
            error="Execution failed",
        )
        
        assert result.status == ExecutionStatus.FAILED
        assert result.error == "Execution failed"
        assert result.success is False
        assert result.failed is True
    
    def test_timeout_result(self):
        """Test timeout execution result."""
        result = ExecutionResult(
            status=ExecutionStatus.TIMEOUT,
            execution_time_seconds=30.0,
        )
        
        assert result.status == ExecutionStatus.TIMEOUT
        assert result.failed is True
    
    def test_result_with_metadata(self):
        """Test result with metadata."""
        result = ExecutionResult(
            status=ExecutionStatus.COMPLETED,
            metadata={"execution_id": "test-123", "memory_peak": 50.0},
        )
        
        assert result.metadata["execution_id"] == "test-123"
        assert result.metadata["memory_peak"] == 50.0


class TestExecutionError:
    """Test ExecutionError."""
    
    def test_create_error(self):
        """Test creating execution error."""
        error = ExecutionError("Execution failed", error_type="execution_error")
        
        assert str(error) == "Execution failed"
        assert error.error_type == "execution_error"
    
    def test_error_inheritance(self):
        """Test that error inherits from Exception."""
        error = ExecutionError("Test error")
        assert isinstance(error, Exception)
