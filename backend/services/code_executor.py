"""
Sandboxed Code Executor

Implements CodeExecutorInterface to execute Python code safely in an isolated environment.
Provides security restrictions, resource limits, and output capture.

FUTURE CONSIDERATION:
For enhanced security and isolation, consider moving code execution to a dedicated Docker container.
See: docs/architecture/CODE_EXECUTOR_CONTAINERIZATION.md for architectural considerations.
"""

import ast
import asyncio
import io
import logging
import re
import sys
import time
import traceback
import uuid
from contextlib import redirect_stderr, redirect_stdout
from typing import Any, Dict, List, Optional

from .code_executor_interface import (
    CodeExecutorInterface,
    ExecutionResult,
    ExecutionStatus,
    ExecutionError,
)
from .config import Settings

logger = logging.getLogger(__name__)


class RestrictedImportHook:
    """Import hook to restrict dangerous imports."""
    
    def __init__(self, allowed_imports: List[str], blocked_imports: List[str], namespace: Dict[str, Any]):
        """
        Initialize import hook.
        
        Args:
            allowed_imports: List of allowed import names
            blocked_imports: List of blocked import names
            namespace: Execution namespace to modify
        """
        self.allowed_imports = set(allowed_imports)
        self.blocked_imports = set(blocked_imports)
        self.namespace = namespace
        import builtins
        self.original_import = builtins.__import__
    
    def __enter__(self):
        """Enter context manager."""
        # Add restricted import to namespace's builtins
        if "__builtins__" in self.namespace:
            self.namespace["__builtins__"]["__import__"] = self._restricted_import
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        # Restore original import (or remove if it wasn't there)
        if "__builtins__" in self.namespace:
            if "__import__" in self.namespace["__builtins__"]:
                del self.namespace["__builtins__"]["__import__"]
    
    def _restricted_import(self, name, globals=None, locals=None, fromlist=(), level=0):
        """Restricted import function."""
        # Extract base module name
        base_name = name.split('.')[0]
        
        # Check if blocked
        if base_name in self.blocked_imports:
            raise ImportError(f"Import of '{base_name}' is not allowed")
        
        # Check if allowed (if allow list is specified)
        if self.allowed_imports and base_name not in self.allowed_imports:
            raise ImportError(f"Import of '{base_name}' is not allowed")
        
        # Allow the import
        return self.original_import(name, globals, locals, fromlist, level)


class SandboxedCodeExecutor(CodeExecutorInterface):
    """
    Sandboxed code executor with security restrictions.
    
    Executes Python code in an isolated namespace with:
    - Restricted imports
    - Timeout controls
    - Output capture
    - Error handling
    """
    
    def __init__(self, settings: Settings):
        """Initialize sandboxed code executor."""
        self.settings = settings
        self._executions: Dict[str, ExecutionResult] = {}
        
        # Default allowed imports (safe standard library)
        self._default_allowed_imports = [
            "json", "math", "datetime", "time", "collections",
            "itertools", "functools", "operator", "re", "string",
            "random", "hashlib", "base64", "decimal", "fractions",
            "statistics", "array", "copy", "enum",
        ]
        
        # Default blocked imports (dangerous)
        self._default_blocked_imports = [
            "os", "subprocess", "sys", "shutil", "socket",
            "multiprocessing", "threading", "ctypes", "pickle",
            "marshal", "importlib", "__builtin__", "builtins",
        ]
    
    async def execute(
        self,
        code: str,
        timeout_seconds: Optional[int] = None,
        memory_limit_mb: Optional[int] = None,
        allowed_imports: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        Execute Python code safely in sandboxed environment.
        
        Args:
            code: Python code string to execute
            timeout_seconds: Maximum execution time (default: 30)
            memory_limit_mb: Memory limit (not enforced in current implementation)
            allowed_imports: List of allowed imports (None = use defaults)
            context: Optional context variables to inject
            
        Returns:
            ExecutionResult with execution status and output
        """
        execution_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Default timeout
        if timeout_seconds is None:
            timeout_seconds = 30
        
        # Use default allowed imports if not specified
        if allowed_imports is None:
            allowed_imports = self._default_allowed_imports
        
        # Create restricted namespace with safe builtins
        safe_builtins = {
            # Safe builtin functions
            "abs": abs, "all": all, "any": any, "bool": bool,
            "dict": dict, "enumerate": enumerate, "float": float,
            "int": int, "len": len, "list": list, "max": max,
            "min": min, "range": range, "reversed": reversed,
            "round": round, "set": set, "sorted": sorted,
            "str": str, "sum": sum, "tuple": tuple, "type": type,
            "zip": zip,
            # Safe type checking functions
            "print": print, "isinstance": isinstance,
            "hasattr": hasattr, "getattr": getattr,
            "setattr": setattr, "delattr": delattr,
        }
        
        namespace = {
            "__builtins__": safe_builtins,
        }
        
        # Inject context variables
        if context:
            namespace.update(context)
        
        # Capture stdout/stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            # Validate safety first
            safety_check = await self.validate_safety(code, strict=True)
            if not safety_check["safe"]:
                return ExecutionResult(
                    status=ExecutionStatus.FAILED,
                    error=f"Code failed safety check: {', '.join(safety_check['blocked_operations'])}",
                    execution_time_seconds=time.time() - start_time,
                    metadata={"safety_check": safety_check},
                )
            
            # Execute with timeout
            try:
                # Execute code with timeout (import hook applied during execution)
                with RestrictedImportHook(allowed_imports, self._default_blocked_imports, namespace):
                    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                        await asyncio.wait_for(
                            self._execute_code(code, namespace),
                            timeout=timeout_seconds
                        )
                
                execution_time = time.time() - start_time
                output = stdout_capture.getvalue()
                error_output = stderr_capture.getvalue()
                
                # Get return value if code defines 'result'
                return_value = namespace.get("result")
                
                result = ExecutionResult(
                    status=ExecutionStatus.COMPLETED,
                    output=output,
                    error=error_output if error_output else None,
                    return_value=return_value,
                    execution_time_seconds=execution_time,
                    metadata={
                        "execution_id": execution_id,
                        "code_length": len(code),
                    },
                )
                
                self._executions[execution_id] = result
                return result
                
            except asyncio.TimeoutError:
                execution_time = time.time() - start_time
                result = ExecutionResult(
                    status=ExecutionStatus.TIMEOUT,
                    error=f"Execution timed out after {timeout_seconds} seconds",
                    execution_time_seconds=execution_time,
                    metadata={"execution_id": execution_id},
                )
                self._executions[execution_id] = result
                return result
                
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Execution failed: {str(e)}\n{traceback.format_exc()}"
            
            result = ExecutionResult(
                status=ExecutionStatus.FAILED,
                error=error_msg,
                execution_time_seconds=execution_time,
                metadata={"execution_id": execution_id},
            )
            self._executions[execution_id] = result
            return result
    
    async def _execute_code(self, code: str, namespace: Dict[str, Any]) -> None:
        """Execute code in namespace (async wrapper for sync exec)."""
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        def _exec():
            exec(code, namespace)
        await loop.run_in_executor(None, _exec)
    
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
            Dictionary with safety validation results
        """
        warnings = []
        blocked_operations = []
        risk_score = 0.0
        
        # Parse AST to check for dangerous operations
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return {
                "safe": False,
                "warnings": [f"Syntax error: {str(e)}"],
                "blocked_operations": ["syntax_error"],
                "risk_score": 1.0,
            }
        
        # Check for dangerous operations
        dangerous_patterns = [
            (r"import\s+os\b", "os module"),
            (r"import\s+subprocess\b", "subprocess module"),
            (r"import\s+sys\b", "sys module"),
            (r"from\s+os\s+import", "os module"),
            (r"from\s+subprocess\s+import", "subprocess module"),
            (r"from\s+sys\s+import", "sys module"),
            (r"__import__\s*\(", "dynamic import"),
            (r"eval\s*\(", "eval function"),
            (r"exec\s*\(", "exec function"),
            (r"compile\s*\(", "compile function"),
            (r"open\s*\(", "file operations"),
        ]
        
        for pattern, description in dangerous_patterns:
            if re.search(pattern, code, re.MULTILINE):
                blocked_operations.append(description)
                risk_score += 0.2
        
        # Check AST for dangerous nodes
        for node in ast.walk(tree):
            # Check for function calls to dangerous functions
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    if func_name in ["eval", "exec", "compile", "__import__"]:
                        blocked_operations.append(f"{func_name}() call")
                        risk_score += 0.3
            
            # Check for imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split('.')[0] in self._default_blocked_imports:
                        blocked_operations.append(f"import {alias.name}")
                        risk_score += 0.2
            
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.split('.')[0] in self._default_blocked_imports:
                    blocked_operations.append(f"from {node.module} import")
                    risk_score += 0.2
        
        safe = len(blocked_operations) == 0 and risk_score < 0.5
        
        return {
            "safe": safe,
            "warnings": warnings,
            "blocked_operations": blocked_operations,
            "risk_score": min(1.0, risk_score),
        }
    
    async def get_execution_status(
        self,
        execution_id: str
    ) -> Optional[ExecutionResult]:
        """
        Get status of a completed execution.
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            ExecutionResult if found, None otherwise
        """
        return self._executions.get(execution_id)
    
    async def cancel_execution(
        self,
        execution_id: str
    ) -> bool:
        """
        Cancel a running execution.
        
        Note: Current implementation doesn't support cancellation of running executions.
        This would require more complex async task management.
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            True if execution was cancelled, False otherwise
        """
        # Check if execution exists and is running
        result = self._executions.get(execution_id)
        if result and result.status == ExecutionStatus.RUNNING:
            result.status = ExecutionStatus.CANCELLED
            return True
        return False
    
    def get_default_allowed_imports(self) -> List[str]:
        """Get default allowed imports."""
        return self._default_allowed_imports.copy()
    
    def get_default_blocked_imports(self) -> List[str]:
        """Get default blocked imports."""
        return self._default_blocked_imports.copy()
