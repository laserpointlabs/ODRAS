"""
DAS Code Generator Service

Implements CodeGeneratorInterface to generate Python code dynamically
using LLM based on user intent and context.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from .code_generator_interface import (
    CodeGeneratorInterface,
    CodeGenerationRequest,
    CodeGenerationResult,
    CodeGenerationCapability,
    CodeGenerationError,
)
from .config import Settings

logger = logging.getLogger(__name__)


class DASCodeGenerator(CodeGeneratorInterface):
    """
    Code generator that uses LLM to generate Python code.
    
    Generates code for:
    - Data fetching from APIs and databases
    - Calculations and transformations
    - Knowledge creation workflows
    - Custom tool execution
    """
    
    def __init__(self, settings: Settings):
        """Initialize DAS code generator."""
        self.settings = settings
        self.supported_capabilities = [
            CodeGenerationCapability.DATA_FETCHING,
            CodeGenerationCapability.CALCULATIONS,
            CodeGenerationCapability.KNOWLEDGE_CREATION,
            CodeGenerationCapability.FILE_OPERATIONS,
            CodeGenerationCapability.DATABASE_QUERIES,
            CodeGenerationCapability.API_CALLS,
            CodeGenerationCapability.DATA_TRANSFORMATION,
            CodeGenerationCapability.WORKFLOW_AUTOMATION,
        ]
    
    async def generate_code(
        self,
        request: CodeGenerationRequest
    ) -> CodeGenerationResult:
        """
        Generate code using LLM based on user intent.
        
        Args:
            request: Code generation request
            
        Returns:
            CodeGenerationResult with generated code
        """
        try:
            # Build prompt for code generation
            prompt = self._build_code_generation_prompt(request)
            
            # Call LLM
            llm_response = await self._call_llm(prompt)
            
            # Extract code from response
            code = self._extract_code_from_response(llm_response)
            
            # Validate code
            validation_result = await self.validate_code(code)
            
            # Extract dependencies
            dependencies = self._extract_dependencies(code)
            
            # Build result
            result = CodeGenerationResult(
                code=code,
                language="python",
                dependencies=dependencies,
                description=self._generate_description(request.intent),
                validation_passed=validation_result["valid"],
                validation_errors=validation_result["errors"],
                metadata={
                    "capabilities": [cap.value for cap in request.capabilities],
                    "intent": request.intent,
                    "llm_model": self.settings.llm_model,
                },
            )
            
            logger.info(f"Generated code for intent: {request.intent[:50]}...")
            return result
            
        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            raise CodeGenerationError(f"Code generation failed: {str(e)}")
    
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
            Dictionary with validation results
        """
        errors = []
        warnings = []
        safety_score = 1.0
        
        if language != "python":
            errors.append(f"Unsupported language: {language}")
            return {
                "valid": False,
                "errors": errors,
                "warnings": warnings,
                "safety_score": 0.0,
            }
        
        # Basic syntax validation using AST
        try:
            import ast
            ast.parse(code)
        except SyntaxError as e:
            errors.append(f"Syntax error: {str(e)}")
            safety_score = 0.0
        
        # Security checks - dangerous imports/operations
        dangerous_patterns = [
            (r"import\s+os\s*$", "os module - file system access"),
            (r"import\s+subprocess", "subprocess - command execution"),
            (r"import\s+sys\s*$", "sys module - system access"),
            (r"__import__\s*\(", "dynamic import"),
            (r"eval\s*\(", "eval - code execution"),
            (r"exec\s*\(", "exec - code execution"),
            (r"open\s*\(", "file operations"),
        ]
        
        for pattern, description in dangerous_patterns:
            if re.search(pattern, code, re.MULTILINE):
                warnings.append(f"Potentially dangerous: {description}")
                safety_score = max(0.0, safety_score - 0.1)
        
        # Check for allowed imports only (if constraints specify)
        # For now, we allow common safe libraries
        
        valid = len(errors) == 0
        
        return {
            "valid": valid,
            "errors": errors,
            "warnings": warnings,
            "safety_score": max(0.0, safety_score),
        }
    
    def get_supported_capabilities(self) -> List[CodeGenerationCapability]:
        """Get supported capabilities."""
        return self.supported_capabilities
    
    def get_capability_description(
        self,
        capability: CodeGenerationCapability
    ) -> str:
        """Get capability description."""
        descriptions = {
            CodeGenerationCapability.DATA_FETCHING: "Fetch data from APIs, databases, and external sources",
            CodeGenerationCapability.CALCULATIONS: "Perform mathematical calculations and data transformations",
            CodeGenerationCapability.KNOWLEDGE_CREATION: "Create knowledge artifacts and documentation",
            CodeGenerationCapability.FILE_OPERATIONS: "Read and write files (restricted)",
            CodeGenerationCapability.DATABASE_QUERIES: "Query databases using SQL or ORM",
            CodeGenerationCapability.API_CALLS: "Make HTTP API calls to external services",
            CodeGenerationCapability.DATA_TRANSFORMATION: "Transform data between formats",
            CodeGenerationCapability.WORKFLOW_AUTOMATION: "Automate workflows and processes",
        }
        return descriptions.get(capability, "Unknown capability")
    
    def _build_code_generation_prompt(
        self,
        request: CodeGenerationRequest
    ) -> str:
        """Build prompt for LLM code generation."""
        capabilities_str = ", ".join([cap.value for cap in request.capabilities])
        
        prompt = f"""You are a Python code generator for DAS (Digital Assistant System).

TASK: Generate Python code to accomplish the following intent:
{request.intent}

REQUIRED CAPABILITIES:
{capabilities_str}

CONTEXT:
{json.dumps(request.context, indent=2)}

CONSTRAINTS:
{json.dumps(request.constraints, indent=2) if request.constraints else "None"}

REQUIREMENTS:
1. Generate ONLY Python code - no explanations, no markdown, no comments outside code
2. Use only safe, standard libraries (json, math, datetime, etc.)
3. For API calls, use httpx or requests (if available)
4. For database queries, use parameterized queries for safety
5. Include error handling
6. Return results in a structured format (dict or list)
7. Code should be self-contained and executable

SAFETY REQUIREMENTS:
- Do NOT use: os, subprocess, sys, eval, exec, __import__
- Do NOT include file system operations unless explicitly requested
- Do NOT include network operations to untrusted sources
- Use parameterized queries for database operations

Generate the Python code now:"""
        
        return prompt
    
    async def _call_llm(self, prompt: str) -> str:
        """
        Call LLM to generate code.
        
        Args:
            prompt: Code generation prompt
            
        Returns:
            LLM response text
        """
        try:
            # Determine LLM URL based on provider
            if self.settings.llm_provider == "ollama":
                base_url = self.settings.ollama_url.rstrip("/")
                llm_url = f"{base_url}/v1/chat/completions"
            else:  # openai
                llm_url = "https://api.openai.com/v1/chat/completions"
            
            payload = {
                "model": self.settings.llm_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a Python code generator. Generate only valid Python code without explanations."
                    },
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,  # Lower temperature for more deterministic code
                "max_tokens": 2000,
                "stream": False,
            }
            
            headers = {"Content-Type": "application/json"}
            if hasattr(self.settings, 'openai_api_key') and self.settings.openai_api_key:
                headers["Authorization"] = f"Bearer {self.settings.openai_api_key}"
            
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(llm_url, json=payload, headers=headers)
                response.raise_for_status()
                
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                return content
                
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise CodeGenerationError(f"LLM call failed: {str(e)}")
    
    def _extract_code_from_response(self, response: str) -> str:
        """
        Extract Python code from LLM response.
        
        Handles markdown code blocks and plain code.
        """
        # Try to extract from markdown code blocks
        code_block_pattern = r"```(?:python)?\s*\n?(.*?)```"
        matches = re.findall(code_block_pattern, response, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # If no code blocks, assume entire response is code
        return response.strip()
    
    def _extract_dependencies(self, code: str) -> List[str]:
        """
        Extract Python package dependencies from code.
        
        Returns:
            List of package names
        """
        dependencies = []
        
        # Find import statements
        import_pattern = r"^(?:from\s+(\S+)|import\s+(\S+))"
        for line in code.split("\n"):
            match = re.match(import_pattern, line.strip())
            if match:
                package = match.group(1) or match.group(2)
                if package:
                    # Extract base package name (before first dot)
                    base_package = package.split(".")[0]
                    # Skip standard library packages
                    stdlib_packages = {
                        "json", "math", "datetime", "time", "collections",
                        "itertools", "functools", "operator", "re", "string",
                        "random", "hashlib", "base64", "urllib", "http",
                    }
                    if base_package not in stdlib_packages:
                        dependencies.append(base_package)
        
        return list(set(dependencies))  # Remove duplicates
    
    def _generate_description(self, intent: str) -> str:
        """Generate a brief description of what the code does."""
        return f"Generated code to: {intent}"
