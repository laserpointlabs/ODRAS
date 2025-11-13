"""
Unit tests for DASCodeGenerator.

Tests code generation with mocked LLM.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from backend.services.das_code_generator import DASCodeGenerator
from backend.services.code_generator_interface import (
    CodeGenerationRequest,
    CodeGenerationCapability,
    CodeGenerationError,
)
from backend.services.config import Settings


@pytest.fixture
def generator():
    """Create DASCodeGenerator instance."""
    settings = Settings()
    return DASCodeGenerator(settings)


class TestDASCodeGenerator:
    """Test DASCodeGenerator."""
    
    def test_generator_properties(self, generator):
        """Test generator properties."""
        capabilities = generator.get_supported_capabilities()
        assert len(capabilities) > 0
        assert CodeGenerationCapability.DATA_FETCHING in capabilities
    
    def test_get_capability_description(self, generator):
        """Test getting capability description."""
        desc = generator.get_capability_description(
            CodeGenerationCapability.DATA_FETCHING
        )
        assert isinstance(desc, str)
        assert len(desc) > 0
    
    @pytest.mark.asyncio
    async def test_validate_valid_code(self, generator):
        """Test validating valid Python code."""
        code = """
def add(a, b):
    return a + b

result = add(1, 2)
"""
        result = await generator.validate_code(code)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_validate_invalid_code(self, generator):
        """Test validating invalid Python code."""
        code = "def invalid syntax here"
        result = await generator.validate_code(code)
        
        assert result["valid"] is False
        assert len(result["errors"]) > 0
    
    @pytest.mark.asyncio
    async def test_validate_dangerous_code(self, generator):
        """Test validating code with dangerous operations."""
        code = """
import os
import subprocess
result = os.system("rm -rf /")
"""
        result = await generator.validate_code(code)
        
        # Should have warnings about dangerous operations
        assert len(result["warnings"]) > 0
        assert result["safety_score"] < 1.0
    
    @pytest.mark.asyncio
    async def test_generate_code_with_mocked_llm(self, generator):
        """Test code generation with mocked LLM."""
        mock_code = """
def fetch_data(url):
    import httpx
    response = httpx.get(url)
    return response.json()
"""
        
        with patch.object(generator, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = f"```python\n{mock_code}\n```"
            
            request = CodeGenerationRequest(
                intent="Fetch data from API",
                context={"api_url": "https://api.example.com/data"},
                capabilities=[CodeGenerationCapability.DATA_FETCHING],
            )
            
            result = await generator.generate_code(request)
            
            assert result.code.strip() == mock_code.strip()
            assert result.language == "python"
            assert result.validation_passed is True
    
    @pytest.mark.asyncio
    async def test_extract_code_from_markdown(self, generator):
        """Test extracting code from markdown code blocks."""
        response = """
Here's the code:

```python
def hello():
    return "world"
```
"""
        code = generator._extract_code_from_response(response)
        assert "def hello()" in code
        assert "```" not in code
    
    @pytest.mark.asyncio
    async def test_extract_code_from_plain_text(self, generator):
        """Test extracting code from plain text."""
        response = """
def hello():
    return "world"
"""
        code = generator._extract_code_from_response(response)
        assert "def hello()" in code
    
    def test_extract_dependencies(self, generator):
        """Test extracting dependencies from code."""
        code = """
import httpx
import json
from datetime import datetime
import requests
"""
        dependencies = generator._extract_dependencies(code)
        
        assert "httpx" in dependencies
        assert "requests" in dependencies
        assert "json" not in dependencies  # Standard library
        assert "datetime" not in dependencies  # Standard library
    
    def test_build_code_generation_prompt(self, generator):
        """Test building code generation prompt."""
        request = CodeGenerationRequest(
            intent="Calculate sum of numbers",
            context={"numbers": [1, 2, 3]},
            capabilities=[CodeGenerationCapability.CALCULATIONS],
            constraints={"timeout": 30},
        )
        
        prompt = generator._build_code_generation_prompt(request)
        
        assert request.intent in prompt
        assert "calculations" in prompt
        assert "timeout" in prompt
    
    @pytest.mark.asyncio
    async def test_generate_code_error_handling(self, generator):
        """Test error handling during code generation."""
        with patch.object(generator, '_call_llm', new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("LLM call failed")
            
            request = CodeGenerationRequest(
                intent="Test",
                context={},
                capabilities=[CodeGenerationCapability.CALCULATIONS],
            )
            
            with pytest.raises(CodeGenerationError):
                await generator.generate_code(request)
