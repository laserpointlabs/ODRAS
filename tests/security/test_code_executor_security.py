"""
Security tests for SandboxedCodeExecutor.

Penetration tests and access control verification.
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


@pytest.mark.security
class TestCodeExecutorSecurity:
    """Security tests for SandboxedCodeExecutor."""
    
    @pytest.mark.asyncio
    async def test_block_os_import(self, executor):
        """Test that os module import is blocked."""
        code = "import os"
        result = await executor.execute(code)
        
        assert result.status == ExecutionStatus.FAILED
        assert "os" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_block_subprocess_import(self, executor):
        """Test that subprocess module import is blocked."""
        code = "import subprocess"
        result = await executor.execute(code)
        
        assert result.status == ExecutionStatus.FAILED
        assert "subprocess" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_block_sys_import(self, executor):
        """Test that sys module import is blocked."""
        code = "import sys"
        result = await executor.execute(code)
        
        assert result.status == ExecutionStatus.FAILED
        assert "sys" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_block_eval_function(self, executor):
        """Test that eval() function calls are blocked."""
        code = "result = eval('1+1')"
        result = await executor.execute(code)
        
        # Should fail safety check
        assert result.status == ExecutionStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_block_exec_function(self, executor):
        """Test that exec() function calls are blocked."""
        code = "exec('result = 1+1')"
        result = await executor.execute(code)
        
        # Should fail safety check
        assert result.status == ExecutionStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_block_file_operations(self, executor):
        """Test that file operations are blocked."""
        code = "result = open('/etc/passwd', 'r').read()"
        result = await executor.execute(code)
        
        # Should fail safety check
        assert result.status == ExecutionStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_block_dynamic_import(self, executor):
        """Test that dynamic imports are blocked."""
        code = "result = __import__('os')"
        result = await executor.execute(code)
        
        # Should fail safety check
        assert result.status == ExecutionStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_allow_safe_imports(self, executor):
        """Test that safe imports are allowed."""
        code = """
import json
import math
result = json.dumps({"pi": math.pi})
"""
        result = await executor.execute(code)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_validate_safety_checks(self, executor):
        """Test that safety validation catches dangerous code."""
        dangerous_codes = [
            "import os",
            "import subprocess",
            "eval('1+1')",
            "exec('print(1)')",
            "open('/file')",
            "__import__('os')",
        ]
        
        for code in dangerous_codes:
            validation = await executor.validate_safety(code, strict=True)
            assert validation["safe"] is False
            assert len(validation["blocked_operations"]) > 0
