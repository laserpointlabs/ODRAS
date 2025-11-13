"""
Code Executor Interface

Abstract interface for executing generated code safely.
Enables DAS to execute Python code in isolated environments with:
- Security restrictions
- Resource limits
- Timeout controls
- Output capture
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum


class ExecutionStatus(Enum):
    """Execution status values."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ExecutionResult:
    """Result of code execution."""
    
    def __init__(
        self,
        status: ExecutionStatus,
        output: Optional[str] = None,
        error: Optional[str] = None,
        return_value: Optional[Any] = None,
        execution_time_seconds: Optional[float] = None,
        memory_used_mb: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize execution result.
        
        Args:
            status: Execution status
            output: Standard output from execution
            error: Error message if execution failed
            return_value: Return value from executed code
            execution_time_seconds: Execution time in seconds
            memory_used_mb: Memory used in MB
            metadata: Additional metadata about execution
        """
        self.status = status
        self.output = output
        self.error = error
        self.return_value = return_value
        self.execution_time_seconds = execution_time_seconds
        self.memory_used_mb = memory_used_mb
        self.metadata = metadata or {}
    
    @property
    def success(self) -> bool:
        """Check if execution was successful."""
        return self.status == ExecutionStatus.COMPLETED
    
    @property
    def failed(self) -> bool:
        """Check if execution failed."""
        return self.status in (
            ExecutionStatus.FAILED,
            ExecutionStatus.TIMEOUT,
            ExecutionStatus.CANCELLED,
        )


class CodeExecutorInterface(ABC):
    """
    Abstract interface for code execution.
    
    Provides safe execution of generated Python code with:
    - Security restrictions (imports, operations)
    - Resource limits (time, memory, CPU)
    - Timeout controls
    - Output capture
    """
    
    @abstractmethod
    async def execute(
        self,
        code: str,
        timeout_seconds: Optional[int] = None,
        memory_limit_mb: Optional[int] = None,
        allowed_imports: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Execute Python code safely.
        
        Args:
            code: Python code string to execute
            timeout_seconds: Maximum execution time in seconds
            memory_limit_mb: Maximum memory usage in MB
            allowed_imports: List of allowed import names (None = use defaults)
            context: Optional context variables to inject into execution environment
            
        Returns:
            ExecutionResult with status, output, and metadata
            
        Raises:
            ExecutionError: If execution setup fails
        """
        pass
    
    @abstractmethod
    async def validate_safety(
        self,
        code: str,
        strict: bool = True
    ) -> Dict[str, Any]:
        """
        Validate code for safety before execution.
        
        Args:
            code: Code string to validate
            strict: If True, use strict safety checks
            
        Returns:
            Dictionary with:
            - safe: bool - Whether code is safe to execute
            - warnings: List[str] - Safety warnings
            - blocked_operations: List[str] - Blocked operations found
            - risk_score: float - Risk score (0.0-1.0, higher = more risky)
        """
        pass
    
    @abstractmethod
    async def get_execution_status(
        self,
        execution_id: str
    ) -> Optional[ExecutionResult]:
        """
        Get status of a running or completed execution.
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            ExecutionResult if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def cancel_execution(
        self,
        execution_id: str
    ) -> bool:
        """
        Cancel a running execution.
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            True if execution was cancelled, False if not found or already completed
        """
        pass
    
    @abstractmethod
    def get_default_allowed_imports(self) -> List[str]:
        """
        Get default list of allowed imports.
        
        Returns:
            List of allowed import names
        """
        pass
    
    @abstractmethod
    def get_default_blocked_imports(self) -> List[str]:
        """
        Get default list of blocked imports.
        
        Returns:
            List of blocked import names
        """
        pass


class ExecutionError(Exception):
    """Exception raised during code execution."""
    
    def __init__(self, message: str, error_type: str = "execution_error"):
        """
        Initialize execution error.
        
        Args:
            message: Error message
            error_type: Type of error (execution_error, timeout_error, etc.)
        """
        self.message = message
        self.error_type = error_type
        super().__init__(self.message)
