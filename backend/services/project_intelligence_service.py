"""
Project Intelligence Service - Cross-project learning and contextual understanding

This service enables DAS to:
- Learn from project events and patterns
- Understand contextual references ("that class", "this ontology")
- Provide intelligent suggestions based on project history
- Bootstrap new projects from similar project patterns
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from .project_thread_manager import ProjectThreadContext, ProjectEvent, ProjectEventType

logger = logging.getLogger(__name__)


@dataclass
class ContextualReference:
    """Represents a contextual reference that DAS can understand"""
    reference_id: str
    reference_type: str  # "class", "ontology", "document", "analysis"
    name: str
    details: Dict[str, Any]
    created_at: datetime
    context: str  # The conversation context where this was mentioned

    def to_dict(self) -> Dict[str, Any]:
        return {
            'reference_id': self.reference_id,
            'reference_type': self.reference_type,
            'name': self.name,
            'details': self.details,
            'created_at': self.created_at.isoformat(),
            'context': self.context
        }


@dataclass
class ProjectPattern:
    """Represents a learned pattern from project activities"""
    pattern_id: str
    pattern_type: str  # "workflow", "decision", "success_factor"
    description: str
    frequency: int
    success_rate: float
    applicable_contexts: List[str]
    example_projects: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'pattern_id': self.pattern_id,
            'pattern_type': self.pattern_type,
            'description': self.description,
            'frequency': self.frequency,
            'success_rate': self.success_rate,
            'applicable_contexts': self.applicable_contexts,
            'example_projects': self.example_projects
        }


class ProjectIntelligenceService:
    """
    Provides intelligent project analysis and contextual understanding
    """

    def __init__(self, settings, redis_client, qdrant_service, llm_service):
        self.settings = settings
        self.redis = redis_client
        self.qdrant = qdrant_service
        self.llm = llm_service

        logger.info("Project Intelligence Service initialized")

    async def resolve_contextual_reference(
        self,
        project_thread_context: ProjectThreadContext,
        user_query: str
    ) -> Optional[Dict[str, Any]]:
        """
        Resolve contextual references like 'that class', 'this ontology', 'the document'
        """
        try:
            query_lower = user_query.lower()

            # Extract reference type and find matching context
            reference_type = None
            if any(term in query_lower for term in ["that class", "this class", "the class"]):
                reference_type = "class"
            elif any(term in query_lower for term in ["that ontology", "this ontology", "the ontology"]):
                reference_type = "ontology"
            elif any(term in query_lower for term in ["that document", "this document", "the document"]):
                reference_type = "document"
            elif any(term in query_lower for term in ["that analysis", "this analysis", "the analysis"]):
                reference_type = "analysis"

            if not reference_type:
                return None

            # Look through recent conversation and events for matching references
            recent_context = await self._get_recent_context(project_thread_context, reference_type)

            if recent_context:
                logger.info(f"Resolved contextual reference '{reference_type}' to: {recent_context.get('name', 'Unknown')}")
                return recent_context

            return None

        except Exception as e:
            logger.error(f"Failed to resolve contextual reference: {e}")
            return None

    async def _get_recent_context(
        self,
        thread_context: ProjectThreadContext,
        reference_type: str
    ) -> Optional[Dict[str, Any]]:
        """Get the most recent context for a reference type"""

        # Check conversation history first (most recent)
        for conversation in reversed(thread_context.conversation_history[-10:]):
            user_msg = conversation.get("user_message", "").lower()
            das_msg = conversation.get("das_response", "").lower()

            if reference_type == "class":
                # Look for class creation or mention
                if "class" in user_msg or "class" in das_msg:
                    # Extract class name from context
                    class_name = self._extract_entity_name(user_msg + " " + das_msg, "class")
                    if class_name:
                        return {
                            "type": "ontology_class",
                            "name": class_name,
                            "source": "conversation",
                            "timestamp": conversation.get("timestamp")
                        }

            elif reference_type == "ontology":
                if "ontology" in user_msg or "ontology" in das_msg:
                    ontology_name = self._extract_entity_name(user_msg + " " + das_msg, "ontology")
                    if ontology_name:
                        return {
                            "type": "ontology",
                            "name": ontology_name,
                            "source": "conversation",
                            "timestamp": conversation.get("timestamp")
                        }

        # Check project events for entity references
        for event in reversed(thread_context.project_events[-20:]):
            event_type = event.get("event_type", "")
            event_data = event.get("key_data", {})

            if reference_type == "class" and event_type == "class_created":
                return {
                    "type": "ontology_class",
                    "name": event_data.get("class_name"),
                    "ontology": event_data.get("ontology_id"),
                    "source": "project_event",
                    "timestamp": event.get("timestamp")
                }

            elif reference_type == "ontology" and event_type == "ontology_created":
                return {
                    "type": "ontology",
                    "name": event_data.get("ontology_name"),
                    "ontology_id": event_data.get("ontology_id"),
                    "source": "project_event",
                    "timestamp": event.get("timestamp")
                }

            elif reference_type == "document" and event_type == "document_uploaded":
                return {
                    "type": "document",
                    "name": event_data.get("filename"),
                    "document_id": event_data.get("document_id"),
                    "source": "project_event",
                    "timestamp": event.get("timestamp")
                }

        # Check active context
        if reference_type == "ontology" and thread_context.active_ontologies:
            return {
                "type": "ontology",
                "name": thread_context.active_ontologies[-1],  # Most recent
                "source": "active_context"
            }

        return None

    def _extract_entity_name(self, text: str, entity_type: str) -> Optional[str]:
        """Extract entity names from text using simple patterns"""
        import re

        if entity_type == "class":
            # Look for patterns like "create a class called X", "X class", etc.
            patterns = [
                r"class called (\w+)",
                r"(\w+) class",
                r"create (\w+)",
                r"add (\w+)"
            ]
        elif entity_type == "ontology":
            patterns = [
                r"ontology called (\w+)",
                r"(\w+) ontology",
                r"ontology (\w+)"
            ]
        else:
            return None

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    async def analyze_project_patterns(self, project_thread_context: ProjectThreadContext) -> List[ProjectPattern]:
        """
        Analyze project events to identify patterns and learning opportunities
        """
        try:
            patterns = []
            events = project_thread_context.project_events

            if len(events) < 5:  # Need some events to identify patterns
                return patterns

            # Analyze workflow patterns
            workflow_pattern = await self._analyze_workflow_patterns(events)
            if workflow_pattern:
                patterns.append(workflow_pattern)

            # Analyze decision patterns
            decision_patterns = await self._analyze_decision_patterns(events, project_thread_context.key_decisions)
            patterns.extend(decision_patterns)

            # Analyze success factors
            success_pattern = await self._analyze_success_factors(events)
            if success_pattern:
                patterns.append(success_pattern)

            return patterns

        except Exception as e:
            logger.error(f"Failed to analyze project patterns: {e}")
            return []

    async def _analyze_workflow_patterns(self, events: List[Dict[str, Any]]) -> Optional[ProjectPattern]:
        """Identify common workflow patterns"""
        try:
            # Group events by type to identify sequences
            event_sequence = [event.get("event_type") for event in events[-10:]]

            # Look for common patterns
            if "document_uploaded" in event_sequence and "analysis_started" in event_sequence:
                return ProjectPattern(
                    pattern_id=str(uuid.uuid4()),
                    pattern_type="workflow",
                    description="Document upload followed by analysis",
                    frequency=1,
                    success_rate=0.8,
                    applicable_contexts=["requirements_analysis", "document_processing"],
                    example_projects=[events[0].get("project_id", "")]
                )

            return None

        except Exception as e:
            logger.error(f"Failed to analyze workflow patterns: {e}")
            return None

    async def _analyze_decision_patterns(
        self,
        events: List[Dict[str, Any]],
        decisions: List[Dict[str, Any]]
    ) -> List[ProjectPattern]:
        """Analyze decision-making patterns"""
        patterns = []

        # Simple pattern: ontology creation decisions
        ontology_events = [e for e in events if e.get("event_type") == "ontology_created"]
        if len(ontology_events) > 0:
            patterns.append(ProjectPattern(
                pattern_id=str(uuid.uuid4()),
                pattern_type="decision",
                description="Ontology-first approach to project structure",
                frequency=len(ontology_events),
                success_rate=0.9,
                applicable_contexts=["project_setup", "requirements_modeling"],
                example_projects=[events[0].get("project_id", "")]
            ))

        return patterns

    async def _analyze_success_factors(self, events: List[Dict[str, Any]]) -> Optional[ProjectPattern]:
        """Identify factors that contribute to project success"""
        try:
            # Simple heuristic: projects with regular DAS interaction tend to be more successful
            das_interactions = len([e for e in events if "das_" in e.get("event_type", "")])
            total_events = len(events)

            if total_events > 10 and das_interactions / total_events > 0.3:
                return ProjectPattern(
                    pattern_id=str(uuid.uuid4()),
                    pattern_type="success_factor",
                    description="High DAS engagement correlates with project progress",
                    frequency=das_interactions,
                    success_rate=0.85,
                    applicable_contexts=["project_management", "knowledge_work"],
                    example_projects=[events[0].get("project_id", "")]
                )

            return None

        except Exception as e:
            logger.error(f"Failed to analyze success factors: {e}")
            return None

    async def get_project_suggestions(
        self,
        project_thread_context: ProjectThreadContext,
        current_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate intelligent suggestions based on project context and patterns
        """
        try:
            suggestions = []

            # Context-aware suggestions based on current state
            if not project_thread_context.active_ontologies:
                suggestions.append({
                    "type": "ontology_creation",
                    "title": "Create Project Ontology",
                    "description": "Start by creating an ontology to structure your project knowledge",
                    "action": "create_ontology",
                    "priority": "high"
                })

            if not project_thread_context.recent_documents:
                suggestions.append({
                    "type": "document_upload",
                    "title": "Upload Project Documents",
                    "description": "Upload requirements or specification documents for analysis",
                    "action": "upload_document",
                    "priority": "medium"
                })

            # Workflow-based suggestions
            recent_events = project_thread_context.project_events[-5:]
            if any("document_uploaded" in e.get("event_type", "") for e in recent_events):
                if not any("analysis_started" in e.get("event_type", "") for e in recent_events):
                    suggestions.append({
                        "type": "analysis_workflow",
                        "title": "Analyze Uploaded Documents",
                        "description": "Run requirements analysis on your uploaded documents",
                        "action": "start_analysis",
                        "priority": "high"
                    })

            # Query-specific suggestions
            if current_query:
                query_suggestions = await self._generate_query_suggestions(
                    project_thread_context, current_query
                )
                suggestions.extend(query_suggestions)

            return suggestions[:5]  # Limit to 5 suggestions

        except Exception as e:
            logger.error(f"Failed to generate project suggestions: {e}")
            return []

    async def _generate_query_suggestions(
        self,
        thread_context: ProjectThreadContext,
        query: str
    ) -> List[Dict[str, Any]]:
        """Generate suggestions based on the current query"""
        suggestions = []
        query_lower = query.lower()

        # Ontology-related suggestions
        if "ontology" in query_lower and thread_context.active_ontologies:
            suggestions.append({
                "type": "ontology_exploration",
                "title": "Explore Ontology Structure",
                "description": f"View the structure of your {thread_context.active_ontologies[-1]} ontology",
                "action": "explore_ontology",
                "priority": "medium"
            })

        # Class-related suggestions
        if "class" in query_lower:
            suggestions.append({
                "type": "class_management",
                "title": "Manage Ontology Classes",
                "description": "Create, modify, or explore ontology classes",
                "action": "manage_classes",
                "priority": "medium"
            })

        # Requirements suggestions
        if any(term in query_lower for term in ["requirement", "specification", "need"]):
            suggestions.append({
                "type": "requirements_analysis",
                "title": "Analyze Requirements",
                "description": "Extract and analyze requirements from your documents",
                "action": "analyze_requirements",
                "priority": "high"
            })

        return suggestions

    async def enhance_query_with_context(
        self,
        project_thread_context: ProjectThreadContext,
        user_query: str
    ) -> str:
        """
        Enhance user query with project context ONLY when it helps
        """
        try:
            # For specific knowledge queries, don't add extra context that confuses search
            query_lower = user_query.lower()

            # If asking about specific entities, keep query clean
            if any(term in query_lower for term in [
                "quadcopter", "trivector", "vtol", "specifications", "platform",
                "hovercruise", "skyeagle", "octicopter", "falcon"
            ]):
                # Keep the query clean for precise matching
                return user_query

            # Only enhance general/ambiguous queries
            enhanced_parts = [user_query]

            # Add minimal helpful context for general queries
            if "ontology" in query_lower and project_thread_context.active_ontologies:
                active_ontology = project_thread_context.active_ontologies[-1]
                enhanced_parts.append(f"ontology: {active_ontology}")

            if "goal" in query_lower and project_thread_context.project_goals:
                enhanced_parts.append(f"goals: {project_thread_context.project_goals}")

            # Only join if we actually added context
            if len(enhanced_parts) > 1:
                return " | ".join(enhanced_parts)
            else:
                return user_query

        except Exception as e:
            logger.error(f"Failed to enhance query with context: {e}")
            return user_query

    async def update_contextual_references(
        self,
        project_thread_context: ProjectThreadContext,
        user_message: str,
        das_response: str
    ):
        """
        Update contextual references based on conversation
        """
        try:
            # Extract entities mentioned in the conversation
            entities = await self._extract_entities_from_conversation(user_message, das_response)

            for entity in entities:
                # Add to contextual references
                ref_id = str(uuid.uuid4())
                reference = ContextualReference(
                    reference_id=ref_id,
                    reference_type=entity["type"],
                    name=entity["name"],
                    details=entity.get("details", {}),
                    created_at=datetime.now(),
                    context=f"User: {user_message[:100]}... DAS: {das_response[:100]}..."
                )

                # Store in thread context
                thread_context.contextual_references[ref_id] = reference.to_dict()

        except Exception as e:
            logger.error(f"Failed to update contextual references: {e}")

    async def _extract_entities_from_conversation(
        self,
        user_message: str,
        das_response: str
    ) -> List[Dict[str, Any]]:
        """
        Extract entities (classes, ontologies, documents) from conversation
        """
        entities = []

        # Simple pattern matching - can be enhanced with NLP
        import re

        combined_text = f"{user_message} {das_response}"

        # Extract class names
        class_patterns = [
            r"class called (\w+)",
            r"(\w+) class",
            r"create (\w+)",
            r"(\w+Class|\w+Entity)"
        ]

        for pattern in class_patterns:
            matches = re.findall(pattern, combined_text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                if len(match) > 2:  # Filter out short words
                    entities.append({
                        "type": "class",
                        "name": match,
                        "details": {"extracted_from": "conversation"}
                    })

        # Extract ontology names
        ontology_patterns = [
            r"ontology called (\w+)",
            r"(\w+) ontology",
            r"(\w+-v\d+)"  # Pattern like "seov1", "bseo-v1"
        ]

        for pattern in ontology_patterns:
            matches = re.findall(pattern, combined_text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                if len(match) > 2:
                    entities.append({
                        "type": "ontology",
                        "name": match,
                        "details": {"extracted_from": "conversation"}
                    })

        return entities

    async def bootstrap_project_from_similar(
        self,
        project_id: str,
        project_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Bootstrap a new project using patterns from similar projects
        """
        try:
            # This would search the project_threads collection for similar projects
            # For now, return basic bootstrap recommendations

            bootstrap_recommendations = {
                "suggested_ontologies": [
                    {
                        "name": "Core System Ontology",
                        "description": "Foundational classes for system modeling",
                        "classes": ["Component", "Function", "Requirement", "Interface"]
                    }
                ],
                "recommended_workflows": [
                    {
                        "name": "Requirements Analysis",
                        "description": "Standard workflow for extracting and analyzing requirements",
                        "steps": ["Upload documents", "Extract requirements", "Create ontology", "Validate model"]
                    }
                ],
                "suggested_documents": [
                    "Upload system requirements document",
                    "Upload architectural specifications",
                    "Upload interface control documents"
                ],
                "best_practices": [
                    "Start with a foundational ontology",
                    "Upload requirements documents early",
                    "Use consistent naming conventions",
                    "Validate models regularly"
                ]
            }

            return bootstrap_recommendations

        except Exception as e:
            logger.error(f"Failed to bootstrap project: {e}")
            return {}

