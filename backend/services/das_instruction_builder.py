"""
DAS Instruction Builder - Populate vector collection with executable command examples

This module builds a comprehensive instruction collection with actual CURL commands,
API examples, and executable procedures that DAS can search and execute.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass

from .config import Settings
from .qdrant_service import QdrantService
from .embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


@dataclass
class ExecutableInstruction:
    """An instruction with executable commands that DAS can run"""
    instruction_id: str
    title: str
    description: str
    user_intent_examples: List[str]  # What user might say
    command_template: str  # Actual command to execute
    api_endpoint: str
    http_method: str
    parameters: Dict[str, Any]
    curl_example: str  # Full CURL command example
    expected_response: Dict[str, Any]
    category: str

    def to_searchable_content(self) -> str:
        """Convert to searchable text for embedding"""
        content_parts = [
            f"Title: {self.title}",
            f"Description: {self.description}",
            f"Category: {self.category}",
            f"User Intent Examples: {'; '.join(self.user_intent_examples)}",
            f"API Endpoint: {self.http_method} {self.api_endpoint}",
            f"CURL Example: {self.curl_example}",
            f"Parameters: {json.dumps(self.parameters)}",
            f"Expected Response: {json.dumps(self.expected_response)}"
        ]
        return "\n".join(content_parts)


class DASInstructionBuilder:
    """
    Builds executable instruction collection for DAS autonomous operations
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.qdrant_service = QdrantService(settings)
        self.embedding_service = EmbeddingService(settings)
        self.collection_name = "das_instructions"

    def create_instruction_collection(self) -> List[ExecutableInstruction]:
        """Create comprehensive instruction collection with executable commands"""

        instructions = []

        # Project Management Instructions
        instructions.extend([
            ExecutableInstruction(
                instruction_id="create_project",
                title="Create New Project",
                description="Create a new project in ODRAS with specified name and description",
                user_intent_examples=[
                    "create a new project called test-a",
                    "please create a project named aircraft-systems",
                    "make a new project for navigation systems",
                    "create project test-a"
                ],
                command_template="POST /api/projects",
                api_endpoint="/api/projects",
                http_method="POST",
                parameters={
                    "name": "string (required)",
                    "description": "string (optional)",
                    "domain": "string (optional, default: systems-engineering)"
                },
                curl_example='curl -X POST http://localhost:8000/api/projects -H "Content-Type: application/json" -H "Authorization: Bearer TOKEN" -d \'{"name": "test-a", "description": "Test project A", "domain": "systems-engineering"}\'',
                expected_response={
                    "success": True,
                    "project": {
                        "project_id": "uuid",
                        "name": "test-a",
                        "description": "Test project A"
                    }
                },
                category="project_management"
            ),

            ExecutableInstruction(
                instruction_id="list_projects",
                title="List All Projects",
                description="Get list of all accessible projects for the current user",
                user_intent_examples=[
                    "show me my projects",
                    "list all projects",
                    "what projects do I have access to",
                    "show projects"
                ],
                command_template="GET /api/projects",
                api_endpoint="/api/projects",
                http_method="GET",
                parameters={},
                curl_example='curl -X GET http://localhost:8000/api/projects -H "Authorization: Bearer TOKEN"',
                expected_response={
                    "projects": [
                        {
                            "project_id": "uuid",
                            "name": "project_name",
                            "description": "project description"
                        }
                    ]
                },
                category="project_management"
            )
        ])

        # Ontology Management Instructions
        instructions.extend([
            ExecutableInstruction(
                instruction_id="create_ontology_class",
                title="Create Ontology Class",
                description="Create a new class in an existing ontology",
                user_intent_examples=[
                    "create a class called AirVehicle in my seov1 ontology",
                    "add a new class named SystemComponent to the ontology",
                    "create class Vehicle in the current ontology"
                ],
                command_template="POST /api/ontologies/{ontology_id}/classes",
                api_endpoint="/api/ontologies/{ontology_id}/classes",
                http_method="POST",
                parameters={
                    "ontology_id": "string (from context or user input)",
                    "name": "string (required)",
                    "description": "string (optional)",
                    "parent_class": "string (optional)"
                },
                curl_example='curl -X POST http://localhost:8000/api/ontologies/seov1/classes -H "Content-Type: application/json" -H "Authorization: Bearer TOKEN" -d \'{"name": "AirVehicle", "description": "Class for air vehicles", "parent_class": "Vehicle"}\'',
                expected_response={
                    "success": True,
                    "class": {
                        "id": "AirVehicle",
                        "name": "AirVehicle",
                        "description": "Class for air vehicles"
                    }
                },
                category="ontology_management"
            ),

            ExecutableInstruction(
                instruction_id="retrieve_ontology",
                title="Retrieve Ontology Information",
                description="Get detailed information about an ontology including classes and relationships",
                user_intent_examples=[
                    "show me the seov1 ontology",
                    "get the foundational ontology structure",
                    "retrieve ontology information for aircraft-systems"
                ],
                command_template="GET /api/ontologies/{ontology_id}",
                api_endpoint="/api/ontologies/{ontology_id}",
                http_method="GET",
                parameters={
                    "ontology_id": "string (from context or user input)"
                },
                curl_example='curl -X GET http://localhost:8000/api/ontologies/seov1 -H "Authorization: Bearer TOKEN"',
                expected_response={
                    "ontology": {
                        "id": "seov1",
                        "name": "Systems Engineering Ontology v1",
                        "classes": ["System", "Component", "Interface"],
                        "relationships": ["hasComponent", "connectsTo"]
                    }
                },
                category="ontology_management"
            )
        ])

        # File Management Instructions
        instructions.extend([
            ExecutableInstruction(
                instruction_id="upload_document",
                title="Upload Document for Processing",
                description="Upload a document file and trigger automatic processing workflows",
                user_intent_examples=[
                    "upload the requirements document",
                    "process this CDD file",
                    "add the specification document to the project"
                ],
                command_template="POST /api/files/upload",
                api_endpoint="/api/files/upload",
                http_method="POST",
                parameters={
                    "file": "file (required)",
                    "project_id": "string (from context)",
                    "document_type": "string (optional: CDD, specification, requirements)"
                },
                curl_example='curl -X POST http://localhost:8000/api/files/upload -H "Authorization: Bearer TOKEN" -F "file=@requirements.pdf" -F "project_id=PROJECT_ID" -F "document_type=requirements"',
                expected_response={
                    "success": True,
                    "file": {
                        "file_id": "uuid",
                        "filename": "requirements.pdf",
                        "status": "uploaded"
                    }
                },
                category="file_management"
            )
        ])

        # Analysis Instructions
        instructions.extend([
            ExecutableInstruction(
                instruction_id="run_requirements_analysis",
                title="Run Requirements Analysis",
                description="Execute requirements analysis workflow on a document",
                user_intent_examples=[
                    "analyze the uploaded requirements document",
                    "run analysis on the CDD file",
                    "extract requirements from the specification"
                ],
                command_template="POST /api/workflows/requirements_analysis",
                api_endpoint="/api/workflows/requirements_analysis",
                http_method="POST",
                parameters={
                    "document_id": "string (from recent uploads or user input)",
                    "analysis_type": "string (full, quick, custom)",
                    "ontology_id": "string (from context)"
                },
                curl_example='curl -X POST http://localhost:8000/api/workflows/requirements_analysis -H "Content-Type: application/json" -H "Authorization: Bearer TOKEN" -d \'{"document_id": "DOC_ID", "analysis_type": "full", "ontology_id": "seov1"}\'',
                expected_response={
                    "success": True,
                    "workflow_id": "uuid",
                    "status": "started",
                    "message": "Requirements analysis workflow started"
                },
                category="analysis_workflows"
            )
        ])

        # Knowledge Search Instructions
        instructions.extend([
            ExecutableInstruction(
                instruction_id="search_knowledge",
                title="Search Knowledge Base",
                description="Search the project knowledge base for specific information",
                user_intent_examples=[
                    "find information about navigation requirements",
                    "search for aircraft safety protocols",
                    "look up performance specifications"
                ],
                command_template="POST /api/knowledge/search",
                api_endpoint="/api/knowledge/search",
                http_method="POST",
                parameters={
                    "query": "string (required)",
                    "project_id": "string (from context)",
                    "max_results": "integer (optional, default: 10)"
                },
                curl_example='curl -X POST http://localhost:8000/api/knowledge/search -H "Content-Type: application/json" -H "Authorization: Bearer TOKEN" -d \'{"query": "navigation requirements", "project_id": "PROJECT_ID", "max_results": 10}\'',
                expected_response={
                    "success": True,
                    "results": [
                        {
                            "title": "Navigation System Requirements",
                            "content": "System shall provide GPS navigation...",
                            "source": "requirements_doc.pdf"
                        }
                    ]
                },
                category="knowledge_management"
            )
        ])

        return instructions

    async def populate_instruction_collection(self) -> bool:
        """Populate the das_instructions vector collection with executable commands"""
        try:
            # Ensure collection exists
            self.qdrant_service.ensure_collection(
                collection_name=self.collection_name,
                vector_size=384,  # sentence-transformers embedding size
                distance="Cosine"
            )

            # Create instruction collection
            instructions = self.create_instruction_collection()

            # Generate embeddings for all instructions
            texts = [instruction.to_searchable_content() for instruction in instructions]
            embeddings = self.embedding_service.generate_embeddings(texts)

            # Prepare points for Qdrant
            points = []
            for i, instruction in enumerate(instructions):
                point = {
                    "id": i,
                    "vector": embeddings[i],
                    "payload": {
                        "instruction_id": instruction.instruction_id,
                        "title": instruction.title,
                        "description": instruction.description,
                        "user_intent_examples": instruction.user_intent_examples,
                        "command_template": instruction.command_template,
                        "api_endpoint": instruction.api_endpoint,
                        "http_method": instruction.http_method,
                        "parameters": instruction.parameters,
                        "curl_example": instruction.curl_example,
                        "expected_response": instruction.expected_response,
                        "category": instruction.category,
                        "content": instruction.to_searchable_content()
                    }
                }
                points.append(point)

            # Store in Qdrant
            self.qdrant_service.store_vectors(
                collection_name=self.collection_name,
                vectors=points
            )

            logger.info(f"Successfully populated {len(instructions)} executable instructions in das_instructions collection")
            return True

        except Exception as e:
            logger.error(f"Failed to populate instruction collection: {e}")
            return False

    async def search_executable_instructions(self, user_query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Search for executable instructions based on user query"""
        try:
            # Generate embedding for user query
            query_embedding = self.embedding_service.generate_embeddings([user_query])

            # Search instruction collection
            results = self.qdrant_service.search_vectors(
                collection_name=self.collection_name,
                query_vector=query_embedding[0],
                limit=limit,
                score_threshold=0.4  # Lower threshold to catch more possibilities
            )

            # Format results with executable commands
            executable_instructions = []
            for result in results:
                payload = result.get("payload", {})
                executable_instructions.append({
                    "instruction_id": payload.get("instruction_id"),
                    "title": payload.get("title"),
                    "description": payload.get("description"),
                    "command_template": payload.get("command_template"),
                    "api_endpoint": payload.get("api_endpoint"),
                    "http_method": payload.get("http_method"),
                    "parameters": payload.get("parameters", {}),
                    "curl_example": payload.get("curl_example"),
                    "expected_response": payload.get("expected_response"),
                    "confidence": result.get("score", 0),
                    "category": payload.get("category")
                })

            return executable_instructions

        except Exception as e:
            logger.error(f"Error searching executable instructions: {e}")
            return []





