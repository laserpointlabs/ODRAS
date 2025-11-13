"""
Unit tests for CodeGeneratorInterface.

Tests interface contract and abstract methods.
"""

import pytest
from abc import ABC

from backend.services.code_generator_interface import (
    CodeGeneratorInterface,
    CodeGenerationRequest,
    CodeGenerationResult,
    CodeGenerationCapability,
    CodeGenerationError,
)


class ConcreteCodeGenerator(CodeGeneratorInterface):
    """Concrete implementation for testing."""
    
    def __init__(self):
        self.supported_capabilities = [
            CodeGenerationCapability.DATA_FETCHING,
            CodeGenerationCapability.CALCULATIONS,
        ]
    
    async def generate_code(self, request: CodeGenerationRequest) -> CodeGenerationResult:
        """Generate code."""
        return CodeGenerationResult(
            code="print('Hello, World!')",
            description="Test code",
            validation_passed=True,
        )
    
    async def validate_code(self, code: str, language: str = "python") -> dict:
        """Validate code."""
        return {
            "valid": True,
            "errors": [],
            "warnings": [],
            "safety_score": 1.0,
        }
    
    def get_supported_capabilities(self) -> list:
        """Get supported capabilities."""
        return self.supported_capabilities
    
    def get_capability_description(self, capability: CodeGenerationCapability) -> str:
        """Get capability description."""
        descriptions = {
            CodeGenerationCapability.DATA_FETCHING: "Fetch data from APIs and databases",
            CodeGenerationCapability.CALCULATIONS: "Perform calculations and transformations",
        }
        return descriptions.get(capability, "Unknown capability")


class TestCodeGeneratorInterface:
    """Test CodeGeneratorInterface contract."""
    
    def test_interface_is_abstract(self):
        """Test that interface cannot be instantiated directly."""
        with pytest.raises(TypeError):
            CodeGeneratorInterface()
    
    def test_concrete_implementation(self):
        """Test that concrete implementation works."""
        generator = ConcreteCodeGenerator()
        assert isinstance(generator, CodeGeneratorInterface)
        assert isinstance(generator, ABC)
    
    @pytest.mark.asyncio
    async def test_generate_code(self):
        """Test code generation."""
        generator = ConcreteCodeGenerator()
        request = CodeGenerationRequest(
            intent="Fetch data from API",
            context={"api_url": "https://api.example.com"},
            capabilities=[CodeGenerationCapability.DATA_FETCHING],
        )
        
        result = await generator.generate_code(request)
        
        assert isinstance(result, CodeGenerationResult)
        assert result.code == "print('Hello, World!')"
        assert result.description == "Test code"
        assert result.validation_passed is True
    
    @pytest.mark.asyncio
    async def test_validate_code(self):
        """Test code validation."""
        generator = ConcreteCodeGenerator()
        
        result = await generator.validate_code("print('test')")
        
        assert isinstance(result, dict)
        assert result["valid"] is True
        assert "errors" in result
        assert "warnings" in result
        assert "safety_score" in result
    
    def test_get_supported_capabilities(self):
        """Test getting supported capabilities."""
        generator = ConcreteCodeGenerator()
        
        capabilities = generator.get_supported_capabilities()
        
        assert isinstance(capabilities, list)
        assert len(capabilities) > 0
        assert CodeGenerationCapability.DATA_FETCHING in capabilities
    
    def test_get_capability_description(self):
        """Test getting capability description."""
        generator = ConcreteCodeGenerator()
        
        description = generator.get_capability_description(
            CodeGenerationCapability.DATA_FETCHING
        )
        
        assert isinstance(description, str)
        assert len(description) > 0


class TestCodeGenerationRequest:
    """Test CodeGenerationRequest."""
    
    def test_create_request(self):
        """Test creating a code generation request."""
        request = CodeGenerationRequest(
            intent="Calculate sum",
            context={"numbers": [1, 2, 3]},
            capabilities=[CodeGenerationCapability.CALCULATIONS],
            user_id="test-user",
            project_id="test-project",
        )
        
        assert request.intent == "Calculate sum"
        assert request.context == {"numbers": [1, 2, 3]}
        assert CodeGenerationCapability.CALCULATIONS in request.capabilities
        assert request.user_id == "test-user"
        assert request.project_id == "test-project"
    
    def test_request_with_constraints(self):
        """Test request with constraints."""
        request = CodeGenerationRequest(
            intent="Fetch data",
            context={},
            capabilities=[CodeGenerationCapability.DATA_FETCHING],
            constraints={"timeout": 30, "max_memory": "100MB"},
        )
        
        assert request.constraints["timeout"] == 30
        assert request.constraints["max_memory"] == "100MB"


class TestCodeGenerationResult:
    """Test CodeGenerationResult."""
    
    def test_create_result(self):
        """Test creating a code generation result."""
        result = CodeGenerationResult(
            code="result = 1 + 2",
            description="Add two numbers",
            validation_passed=True,
        )
        
        assert result.code == "result = 1 + 2"
        assert result.description == "Add two numbers"
        assert result.validation_passed is True
        assert result.language == "python"
    
    def test_result_with_dependencies(self):
        """Test result with dependencies."""
        result = CodeGenerationResult(
            code="import requests",
            dependencies=["requests"],
        )
        
        assert "requests" in result.dependencies
    
    def test_result_with_validation_errors(self):
        """Test result with validation errors."""
        result = CodeGenerationResult(
            code="invalid code",
            validation_passed=False,
            validation_errors=["Syntax error"],
        )
        
        assert result.validation_passed is False
        assert len(result.validation_errors) > 0


class TestCodeGenerationError:
    """Test CodeGenerationError."""
    
    def test_create_error(self):
        """Test creating a code generation error."""
        error = CodeGenerationError("Generation failed", error_type="generation_error")
        
        assert str(error) == "Generation failed"
        assert error.error_type == "generation_error"
    
    def test_error_inheritance(self):
        """Test that error inherits from Exception."""
        error = CodeGenerationError("Test error")
        assert isinstance(error, Exception)
