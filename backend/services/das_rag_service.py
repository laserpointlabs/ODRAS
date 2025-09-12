"""
DAS RAG Service - Enhanced RAG capabilities for the Digital Assistance System

This service extends the existing RAG service with DAS-specific instruction collection
and contextual knowledge retrieval.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

from .config import Settings
from .rag_service import RAGService
from .qdrant_service import QdrantService
from .db import DatabaseService

logger = logging.getLogger(__name__)


@dataclass
class DASInstruction:
    """Represents a DAS instruction for the knowledge base"""
    instruction_id: str
    category: str
    title: str
    description: str
    steps: List[str]
    examples: List[Dict[str, Any]]
    prerequisites: List[str]
    related_commands: List[str]
    confidence_level: str
    last_updated: datetime
    content: str  # Full text content for embedding

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'instruction_id': self.instruction_id,
            'category': self.category,
            'title': self.title,
            'description': self.description,
            'steps': self.steps,
            'examples': self.examples,
            'prerequisites': self.prerequisites,
            'related_commands': self.related_commands,
            'confidence_level': self.confidence_level,
            'last_updated': self.last_updated.isoformat(),
            'content': self.content
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DASInstruction':
        """Create from dictionary"""
        data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        return cls(**data)


class DASRAGService:
    """
    Enhanced RAG service that combines general knowledge with DAS-specific instructions
    """

    def __init__(self, settings: Settings, rag_service: RAGService, qdrant_service: QdrantService, db_service: DatabaseService):
        self.settings = settings
        self.rag_service = rag_service
        self.qdrant_service = qdrant_service
        self.db_service = db_service
        self.instruction_collection_name = "das_instructions"
        self.instruction_templates = self._load_instruction_templates()

    def _load_instruction_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load pre-defined instruction templates"""
        return {
            "api_usage": [
                {
                    "id": "retrieve_ontology",
                    "title": "How to retrieve an ontology from the API",
                    "description": "Learn how to fetch ontology data using the ODRAS API",
                    "steps": [
                        "Identify the ontology ID you want to retrieve",
                        "Use the GET /api/ontologies/{ontology_id} endpoint",
                        "Handle the response and parse the ontology data",
                        "Display or process the retrieved ontology"
                    ],
                    "examples": [
                        {
                            "ontology_id": "foundational_se_ontology",
                            "expected_result": "Ontology object with classes and relationships"
                        }
                    ],
                    "prerequisites": ["Basic understanding of REST APIs", "Knowledge of ontology structure"],
                    "related_commands": ["create_class", "update_ontology"],
                    "level": "beginner"
                },
                {
                    "id": "create_ontology_class",
                    "title": "How to create a new class in an ontology",
                    "description": "Step-by-step guide to adding new classes to existing ontologies",
                    "steps": [
                        "Identify the target ontology",
                        "Define the class name and properties",
                        "Use POST /api/ontologies/{ontology_id}/classes",
                        "Validate the created class",
                        "Update related relationships if needed"
                    ],
                    "examples": [
                        {
                            "ontology_id": "foundational_se_ontology",
                            "class_name": "SystemComponent",
                            "class_type": "PhysicalEntity",
                            "properties": {"hasFunction": "string", "hasInterface": "string"}
                        }
                    ],
                    "prerequisites": ["Ontology structure knowledge", "Class definition concepts"],
                    "related_commands": ["retrieve_ontology", "add_relationship"],
                    "level": "intermediate"
                },
                {
                    "id": "upload_document",
                    "title": "How to upload and process documents",
                    "description": "Guide for uploading documents and triggering analysis workflows",
                    "steps": [
                        "Prepare the document file",
                        "Use POST /api/files/upload endpoint",
                        "Wait for processing to complete",
                        "Check processing status",
                        "Access processed results"
                    ],
                    "examples": [
                        {
                            "file_type": "PDF",
                            "document_type": "CDD",
                            "expected_result": "Processed document with extracted requirements"
                        }
                    ],
                    "prerequisites": ["File upload concepts", "Document processing workflow"],
                    "related_commands": ["run_analysis", "check_processing_status"],
                    "level": "beginner"
                }
            ],
            "ontology_management": [
                {
                    "id": "creating_foundational_ontologies",
                    "title": "Creating foundational ontologies",
                    "description": "Best practices for creating foundational system engineering ontologies",
                    "steps": [
                        "Define the domain scope and boundaries",
                        "Identify core concepts and entities",
                        "Establish foundational relationships",
                        "Define properties and constraints",
                        "Validate ontology consistency",
                        "Document ontology structure"
                    ],
                    "examples": [
                        {
                            "domain": "System Engineering",
                            "core_concepts": ["System", "Component", "Interface", "Requirement"],
                            "relationships": ["hasComponent", "hasInterface", "satisfies"]
                        }
                    ],
                    "prerequisites": ["Ontology design principles", "Domain knowledge"],
                    "related_commands": ["validate_ontology", "export_ontology"],
                    "level": "advanced"
                },
                {
                    "id": "adding_relationships",
                    "title": "Adding first-order relationships",
                    "description": "How to define and implement relationships between ontology classes",
                    "steps": [
                        "Identify the classes to relate",
                        "Define the relationship type and properties",
                        "Specify cardinality constraints",
                        "Add inverse relationships if needed",
                        "Validate relationship consistency"
                    ],
                    "examples": [
                        {
                            "source_class": "System",
                            "target_class": "Component",
                            "relationship": "hasComponent",
                            "cardinality": "one-to-many"
                        }
                    ],
                    "prerequisites": ["Relationship modeling", "Cardinality concepts"],
                    "related_commands": ["create_class", "validate_ontology"],
                    "level": "intermediate"
                }
            ],
            "analysis_workflows": [
                {
                    "id": "requirements_analysis",
                    "title": "Running requirements analysis",
                    "description": "Complete workflow for analyzing requirements documents",
                    "steps": [
                        "Upload requirements document",
                        "Configure analysis parameters",
                        "Start analysis workflow",
                        "Monitor progress",
                        "Review analysis results",
                        "Export findings"
                    ],
                    "examples": [
                        {
                            "document_type": "CDD",
                            "analysis_type": "full",
                            "questions": ["What are the key capabilities?", "What are the performance requirements?"]
                        }
                    ],
                    "prerequisites": ["Document processing", "Requirements analysis concepts"],
                    "related_commands": ["upload_document", "run_workflow"],
                    "level": "intermediate"
                },
                {
                    "id": "sensitivity_analysis",
                    "title": "Running sensitivity analysis",
                    "description": "How to perform sensitivity analysis on system requirements",
                    "steps": [
                        "Define analysis parameters",
                        "Select requirements for analysis",
                        "Configure sensitivity metrics",
                        "Execute analysis workflow",
                        "Interpret results",
                        "Generate recommendations"
                    ],
                    "examples": [
                        {
                            "requirements": ["Performance", "Reliability", "Cost"],
                            "metrics": ["Impact", "Variance", "Correlation"],
                            "expected_output": "Sensitivity matrix with recommendations"
                        }
                    ],
                    "prerequisites": ["Statistical analysis", "Requirements engineering"],
                    "related_commands": ["run_analysis", "generate_report"],
                    "level": "advanced"
                }
            ],
            "troubleshooting": [
                {
                    "id": "common_errors",
                    "title": "Common error resolution",
                    "description": "Solutions for frequently encountered issues",
                    "steps": [
                        "Identify the error type and message",
                        "Check system logs for details",
                        "Verify input parameters",
                        "Check system status",
                        "Apply appropriate fix",
                        "Test resolution"
                    ],
                    "examples": [
                        {
                            "error": "Ontology validation failed",
                            "cause": "Inconsistent relationships",
                            "solution": "Review and fix relationship definitions"
                        }
                    ],
                    "prerequisites": ["System troubleshooting", "Error analysis"],
                    "related_commands": ["check_logs", "validate_system"],
                    "level": "intermediate"
                }
            ]
        }

    async def initialize_instruction_collection(self) -> bool:
        """
        Initialize the DAS instruction collection in the vector store
        """
        try:
            # Check if collection already exists
            collections = self.qdrant_service.list_collections()
            if self.instruction_collection_name in collections:
                # Check if collection has correct dimensions
                try:
                    collection_info = self.qdrant_service.get_collection_info(self.instruction_collection_name)
                    if collection_info and collection_info.get('config', {}).get('params', {}).get('vectors', {}).get('size') == 384:
                        logger.info(f"Instruction collection {self.instruction_collection_name} already exists with correct dimensions")
                        return True
                    else:
                        logger.info(f"Recreating instruction collection {self.instruction_collection_name} with correct dimensions")
                        # Delete existing collection
                        self.qdrant_service.client.delete_collection(self.instruction_collection_name)
                except Exception as e:
                    logger.warning(f"Could not check collection info: {e}")
                    # Try to delete and recreate
                    try:
                        self.qdrant_service.client.delete_collection(self.instruction_collection_name)
                    except:
                        pass

            # Create collection
            self.qdrant_service.ensure_collection(
                collection_name=self.instruction_collection_name,
                vector_size=384,  # all-MiniLM-L6-v2 embedding size
                distance="Cosine"
            )

            # Populate with instruction templates
            await self.populate_instruction_collection()
            
            logger.info(f"Instruction collection {self.instruction_collection_name} initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize instruction collection: {e}")
            return False

    async def populate_instruction_collection(self) -> int:
        """
        Populate the instruction collection with pre-defined templates
        """
        try:
            instructions = []
            
            for category, templates in self.instruction_templates.items():
                for template in templates:
                    instruction = self._create_instruction_from_template(category, template)
                    instructions.append(instruction)

            # Generate embeddings and store
            if instructions:
                await self._store_instructions(instructions)
                logger.info(f"Stored {len(instructions)} instructions in collection")
                return len(instructions)
            
            return 0

        except Exception as e:
            logger.error(f"Failed to populate instruction collection: {e}")
            return 0

    def _create_instruction_from_template(self, category: str, template: Dict[str, Any]) -> DASInstruction:
        """
        Create a DAS instruction from a template
        """
        # Create comprehensive content for embedding
        content_parts = [
            f"Title: {template['title']}",
            f"Description: {template['description']}",
            f"Category: {category}",
            f"Steps: {'; '.join(template['steps'])}",
            f"Prerequisites: {', '.join(template.get('prerequisites', []))}",
            f"Related commands: {', '.join(template.get('related_commands', []))}"
        ]
        
        if template.get('examples'):
            content_parts.append(f"Examples: {json.dumps(template['examples'])}")
        
        content = "\n".join(content_parts)

        return DASInstruction(
            instruction_id=f"{category}_{template['id']}",
            category=category,
            title=template['title'],
            description=template['description'],
            steps=template['steps'],
            examples=template.get('examples', []),
            prerequisites=template.get('prerequisites', []),
            related_commands=template.get('related_commands', []),
            confidence_level=template.get('level', 'beginner'),
            last_updated=datetime.now(),
            content=content
        )

    async def _store_instructions(self, instructions: List[DASInstruction]):
        """
        Store instructions in the vector store with embeddings
        """
        try:
            from .embedding_service import EmbeddingService
            
            embedding_service = EmbeddingService(self.settings)
            
            # Generate embeddings for all instructions
            texts = [instruction.content for instruction in instructions]
            embeddings = embedding_service.generate_embeddings(texts)
            
            # Prepare points for Qdrant
            points = []
            for i, instruction in enumerate(instructions):
                point = {
                    "id": i,  # Use integer ID for Qdrant compatibility
                    "vector": embeddings[i],
                    "payload": instruction.to_dict()
                }
                points.append(point)
            
            # Store in Qdrant
            self.qdrant_service.store_vectors(
                collection_name=self.instruction_collection_name,
                vectors=points
            )
            
        except Exception as e:
            logger.error(f"Failed to store instructions: {e}")
            raise

    async def query_das_knowledge(
        self,
        question: str,
        context: Dict[str, Any] = None,
        max_chunks: int = 5,
        include_instructions: bool = True,
        include_general_knowledge: bool = True
    ) -> Dict[str, Any]:
        """
        Query both general knowledge and DAS-specific instructions
        """
        try:
            results = {
                "answer": "",
                "sources": [],
                "confidence": 0.0,
                "instruction_results": [],
                "general_results": []
            }

            # Query general knowledge if requested
            if include_general_knowledge:
                try:
                    general_response = await self.rag_service.query_knowledge_base(
                        question=question,
                        project_id=context.get("session_context", {}).get("active_project") if context else None,
                        user_id=context.get("session_context", {}).get("user_id") if context else None,
                        max_chunks=max_chunks,
                        similarity_threshold=0.3  # Lower threshold for better recall
                    )
                    results["general_results"] = general_response
                except Exception as e:
                    logger.warning(f"Failed to query general knowledge: {e}")

            # Query instruction collection if requested
            if include_instructions:
                try:
                    instruction_results = await self._query_instruction_collection(
                        question, max_chunks=max_chunks
                    )
                    results["instruction_results"] = instruction_results
                except Exception as e:
                    logger.warning(f"Failed to query instruction collection: {e}")

            # Combine and rank results
            combined_answer = await self._combine_knowledge_sources(
                question, results["general_results"], results["instruction_results"]
            )
            
            results["answer"] = combined_answer["answer"]
            results["confidence"] = combined_answer["confidence"]
            results["sources"] = combined_answer["sources"]

            return results

        except Exception as e:
            logger.error(f"Error in DAS knowledge query: {e}")
            return {
                "answer": "I apologize, but I encountered an error while searching for information. Please try again.",
                "sources": [],
                "confidence": 0.0,
                "instruction_results": [],
                "general_results": []
            }

    async def _query_instruction_collection(self, question: str, max_chunks: int = 5) -> List[Dict[str, Any]]:
        """
        Query the instruction collection for relevant instructions
        """
        try:
            from .embedding_service import EmbeddingService
            
            embedding_service = EmbeddingService(self.settings)
            
            # Generate embedding for the question
            question_embedding = embedding_service.generate_embeddings([question])
            
            # Search in instruction collection
            search_results = self.qdrant_service.search_vectors(
                collection_name=self.instruction_collection_name,
                query_vector=question_embedding[0],
                limit=max_chunks,
                score_threshold=0.3  # Lower threshold to include more relevant results
            )
            
            # Format results
            results = []
            for result in search_results:
                payload = result.get("payload", {})
                results.append({
                    "instruction_id": payload.get("instruction_id"),
                    "title": payload.get("title"),
                    "description": payload.get("description"),
                    "category": payload.get("category"),
                    "steps": payload.get("steps", []),
                    "examples": payload.get("examples", []),
                    "confidence_level": payload.get("confidence_level"),
                    "score": result.get("score", 0),
                    "content": payload.get("content")
                })
            
            return results

        except Exception as e:
            logger.error(f"Error querying instruction collection: {e}")
            return []

    async def _combine_knowledge_sources(
        self,
        question: str,
        general_results: Dict[str, Any],
        instruction_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Combine results from general knowledge and instruction collection using LLM
        """
        try:
            # Prepare context for LLM
            context_chunks = []
            sources = []
            
            # Add instruction results to context
            if instruction_results:
                for instruction in instruction_results[:3]:  # Top 3 instructions
                    context_chunks.append({
                        "payload": {
                            "content": f"Instruction: {instruction['title']}\nDescription: {instruction['description']}\nSteps: {'; '.join(instruction['steps'])}",
                            "source_asset": f"DAS Instruction: {instruction['title']}",
                            "document_type": "instruction",
                            "type": "instruction",
                            "title": instruction['title'],
                            "category": instruction['category'],
                            "confidence_level": instruction['confidence_level']
                        }
                    })
                    sources.append({
                        "type": "instruction",
                        "title": instruction['title'],
                        "category": instruction['category'],
                        "confidence_level": instruction['confidence_level']
                    })
            
            # Add general knowledge results to context
            if general_results and general_results.get("sources"):
                for source in general_results["sources"][:3]:  # Top 3 general sources
                    context_chunks.append({
                        "payload": source  # General results already have the correct payload format
                    })
                    sources.append(source)
            
            # Use LLM to generate response if we have context
            if context_chunks:
                try:
                    # Use the existing RAG service's LLM generation
                    llm_response = await self.rag_service._generate_response(
                        question=question,
                        relevant_chunks=context_chunks,
                        response_style="comprehensive"
                    )
                    
                    return {
                        "answer": llm_response.get("answer", "I couldn't generate a proper response."),
                        "confidence": llm_response.get("confidence", 0.7),
                        "sources": sources,
                        "llm_used": True,
                        "model": self.settings.llm_model
                    }
                except Exception as llm_error:
                    logger.warning(f"LLM generation failed, falling back to template: {llm_error}")
                    # Fall back to template-based response
                    return await self._fallback_template_response(question, instruction_results, general_results, sources)
            else:
                # No context available
                return {
                    "answer": "I don't have specific information about that topic. Could you provide more details or try rephrasing your question?",
                    "confidence": 0.3,
                    "sources": [],
                    "llm_used": False
                }

        except Exception as e:
            logger.error(f"Error combining knowledge sources: {e}")
            return {
                "answer": "I encountered an error while processing your request. Please try again.",
                "confidence": 0.0,
                "sources": [],
                "llm_used": False
            }
    
    async def _fallback_template_response(
        self,
        question: str,
        instruction_results: List[Dict[str, Any]],
        general_results: Dict[str, Any],
        sources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Fallback to template-based response when LLM is unavailable
        """
        try:
            # If we have instruction results, prioritize them for how-to questions
            if instruction_results and any(keyword in question.lower() for keyword in ["how", "how to", "guide", "tutorial", "steps"]):
                best_instruction = instruction_results[0]
                
                # Create a comprehensive answer from the instruction
                answer_parts = [
                    f"**{best_instruction['title']}**",
                    f"{best_instruction['description']}",
                    "",
                    "**Steps:**"
                ]
                
                for i, step in enumerate(best_instruction['steps'], 1):
                    answer_parts.append(f"{i}. {step}")
                
                if best_instruction.get('examples'):
                    answer_parts.extend(["", "**Examples:**"])
                    for example in best_instruction['examples']:
                        answer_parts.append(f"- {json.dumps(example, indent=2)}")
                
                return {
                    "answer": "\n".join(answer_parts),
                    "confidence": best_instruction.get('score', 0.8),
                    "sources": sources,
                    "llm_used": False,
                    "fallback_reason": "LLM unavailable"
                }
            
            # Otherwise, use general knowledge results
            elif general_results and general_results.get("answer"):
                return {
                    "answer": general_results["answer"],
                    "confidence": general_results.get("confidence", 0.7),
                    "sources": sources,
                    "llm_used": False,
                    "fallback_reason": "LLM unavailable"
                }
            
            # Fallback response
            else:
                return {
                    "answer": "I don't have specific information about that topic. Could you provide more details or try rephrasing your question?",
                    "confidence": 0.3,
                    "sources": [],
                    "llm_used": False,
                    "fallback_reason": "No context available"
                }

        except Exception as e:
            logger.error(f"Error in fallback template response: {e}")
            return {
                "answer": "I encountered an error while processing your request. Please try again.",
                "confidence": 0.0,
                "sources": [],
                "llm_used": False,
                "fallback_reason": "Template error"
            }

    async def get_instruction_categories(self) -> List[str]:
        """
        Get list of available instruction categories
        """
        return list(self.instruction_templates.keys())

    async def get_instructions_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Get all instructions for a specific category
        """
        return self.instruction_templates.get(category, [])

    async def add_custom_instruction(self, instruction: DASInstruction) -> bool:
        """
        Add a custom instruction to the collection
        """
        try:
            await self._store_instructions([instruction])
            logger.info(f"Added custom instruction: {instruction.instruction_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add custom instruction: {e}")
            return False
