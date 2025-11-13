"""
Code Generator Interface

Abstract interface for runtime code generation by DAS.
Enables DAS to generate Python code on-the-fly for various tasks:
- Data fetching from APIs and databases
- Calculations and transformations
- Knowledge creation workflows
- Custom tool execution
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum


class CodeGenerationCapability(Enum):
    """Supported code generation capabilities."""
    DATA_FETCHING = "data_fetching"  # Fetch data from APIs, databases
    CALCULATIONS = "calculations"  # Mathematical calculations and transformations
    KNOWLEDGE_CREATION = "knowledge_creation"  # Create knowledge artifacts
    FILE_OPERATIONS = "file_operations"  # Read/write files
    DATABASE_QUERIES = "database_queries"  # Query databases
    API_CALLS = "api_calls"  # Make HTTP API calls
    DATA_TRANSFORMATION = "data_transformation"  # Transform data formats
    WORKFLOW_AUTOMATION = "workflow_automation"  # Automate workflows


class CodeGenerationRequest:
    """Request for code generation."""
    
    def __init__(
        self,
        intent: str,
        context: Dict[str, Any],
        capabilities: List[CodeGenerationCapability],
        constraints: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ):
        """
        Initialize code generation request.
        
        Args:
            intent: Natural language description of what code should do
            context: Context information (available APIs, data sources, etc.)
            capabilities: List of capabilities this code should use
            constraints: Optional constraints (timeout, memory limits, etc.)
            user_id: User requesting code generation
            project_id: Project context
        """
        self.intent = intent
        self.context = context
        self.capabilities = capabilities
        self.constraints = constraints or {}
        self.user_id = user_id
        self.project_id = project_id


class CodeGenerationResult:
    """Result of code generation."""
    
    def __init__(
        self,
        code: str,
        language: str = "python",
        dependencies: Optional[List[str]] = None,
        description: Optional[str] = None,
        validation_passed: bool = False,
        validation_errors: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize code generation result.
        
        Args:
            code: Generated code string
            language: Programming language (default: python)
            dependencies: Required dependencies/packages
            description: Human-readable description of what the code does
            validation_passed: Whether code validation passed
            validation_errors: List of validation errors if any
            metadata: Additional metadata about the generated code
        """
        self.code = code
        self.language = language
        self.dependencies = dependencies or []
        self.description = description
        self.validation_passed = validation_passed
        self.validation_errors = validation_errors or []
        self.metadata = metadata or {}


class CodeGeneratorInterface(ABC):
    """
    Abstract interface for code generation.
    
    Enables DAS to generate Python code dynamically based on user intent.
    Code generation should be:
    - Safe: Validated before execution
    - Context-aware: Uses available APIs, data sources, and tools
    - Capability-specific: Generates code appropriate for requested capabilities
    """
    
    @abstractmethod
    async def generate_code(
        self,
        request: CodeGenerationRequest
    ) -> CodeGenerationResult:
        """
        Generate code based on user intent and context.
        
        Args:
            request: Code generation request with intent, context, and capabilities
            
        Returns:
            CodeGenerationResult with generated code and metadata
            
        Raises:
            CodeGenerationError: If code generation fails
        """
        pass
    
    @abstractmethod
    async def validate_code(
        self,
        code: str,
        language: str = "python"
    ) -> Dict[str, Any]:
        """
        Validate generated code for safety and correctness.
        
        Args:
            code: Code string to validate
            language: Programming language (default: python)
            
        Returns:
            Dictionary with:
            - valid: bool - Whether code is valid
            - errors: List[str] - List of validation errors
            - warnings: List[str] - List of validation warnings
            - safety_score: float - Safety score (0.0-1.0)
        """
        pass
    
    @abstractmethod
    def get_supported_capabilities(self) -> List[CodeGenerationCapability]:
        """
        Get list of supported code generation capabilities.
        
        Returns:
            List of CodeGenerationCapability enums
        """
        pass
    
    @abstractmethod
    def get_capability_description(
        self,
        capability: CodeGenerationCapability
    ) -> str:
        """
        Get human-readable description of a capability.
        
        Args:
            capability: CodeGenerationCapability enum
            
        Returns:
            Description string
        """
        pass


class CodeGenerationError(Exception):
    """Exception raised during code generation."""
    
    def __init__(self, message: str, error_type: str = "generation_error"):
        """
        Initialize code generation error.
        
        Args:
            message: Error message
            error_type: Type of error (generation_error, validation_error, etc.)
        """
        self.message = message
        self.error_type = error_type
        super().__init__(self.message)
