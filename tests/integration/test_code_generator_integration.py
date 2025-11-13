"""
Integration tests for DASCodeGenerator.

Tests with real LLM (if available) to verify code quality.
"""

import pytest

from backend.services.das_code_generator import DASCodeGenerator
from backend.services.code_generator_interface import (
    CodeGenerationRequest,
    CodeGenerationCapability,
)
from backend.services.config import Settings


@pytest.fixture
def generator():
    """Create DASCodeGenerator instance."""
    settings = Settings()
    return DASCodeGenerator(settings)


@pytest.mark.integration
class TestDASCodeGeneratorIntegration:
    """Integration tests for DASCodeGenerator."""
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not pytest.config.getoption("--run-llm-tests", default=False),
        reason="LLM tests require --run-llm-tests flag"
    )
    async def test_generate_simple_calculation_code(self, generator):
        """Test generating simple calculation code with real LLM."""
        request = CodeGenerationRequest(
            intent="Calculate the sum of numbers in a list",
            context={"numbers": [1, 2, 3, 4, 5]},
            capabilities=[CodeGenerationCapability.CALCULATIONS],
        )
        
        result = await generator.generate_code(request)
        
        assert result.code is not None
        assert len(result.code) > 0
        assert result.language == "python"
        assert result.validation_passed is True
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not pytest.config.getoption("--run-llm-tests", default=False),
        reason="LLM tests require --run-llm-tests flag"
    )
    async def test_generate_data_fetching_code(self, generator):
        """Test generating data fetching code with real LLM."""
        request = CodeGenerationRequest(
            intent="Fetch JSON data from an API endpoint",
            context={
                "api_url": "https://api.example.com/data",
                "method": "GET",
            },
            capabilities=[CodeGenerationCapability.DATA_FETCHING],
        )
        
        result = await generator.generate_code(request)
        
        assert result.code is not None
        assert len(result.code) > 0
        assert result.language == "python"
        # Should include httpx or requests import
        assert "httpx" in result.code.lower() or "requests" in result.code.lower()
    
    @pytest.mark.asyncio
    async def test_validate_generated_code_syntax(self, generator):
        """Test that generated code has valid Python syntax."""
        # Use a simple test case that doesn't require LLM
        test_code = """
def calculate_sum(numbers):
    return sum(numbers)

result = calculate_sum([1, 2, 3])
"""
        result = await generator.validate_code(test_code)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_code_generation_with_constraints(self, generator):
        """Test code generation with constraints."""
        # This test can work without LLM by testing the prompt building
        request = CodeGenerationRequest(
            intent="Process data",
            context={},
            capabilities=[CodeGenerationCapability.DATA_TRANSFORMATION],
            constraints={"timeout": 30, "max_memory": "100MB"},
        )
        
        prompt = generator._build_code_generation_prompt(request)
        
        assert "timeout" in prompt
        assert "max_memory" in prompt
        assert "data_transformation" in prompt
