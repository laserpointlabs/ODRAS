"""
Persona Interface

Abstract interface for DAS personas (specialized AI agents).
Enables DAS to use a team of personas with different roles and capabilities.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum


class PersonaRole(Enum):
    """Roles that personas can take."""
    RESEARCHER = "researcher"  # Finds and gathers information
    ANALYST = "analyst"  # Analyzes data and patterns
    WRITER = "writer"  # Creates content and documentation
    MODERATOR = "moderator"  # Coordinates team and assigns tasks
    SPECIALIST = "specialist"  # Domain-specific expertise


class PersonaCapability(Enum):
    """Capabilities that personas can have."""
    INFORMATION_RETRIEVAL = "information_retrieval"
    DATA_ANALYSIS = "data_analysis"
    CONTENT_CREATION = "content_creation"
    COORDINATION = "coordination"
    CODE_GENERATION = "code_generation"
    KNOWLEDGE_SYNTHESIS = "knowledge_synthesis"
    QUALITY_REVIEW = "quality_review"


class PersonaTask:
    """Task to be processed by a persona."""
    
    def __init__(
        self,
        task_id: str,
        description: str,
        context: Dict[str, Any],
        priority: int = 5,  # 1-10, higher is more important
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize persona task.
        
        Args:
            task_id: Unique task identifier
            description: Task description
            context: Context information for the task
            priority: Task priority (1-10)
            dependencies: List of task IDs this task depends on
            metadata: Additional metadata
        """
        self.task_id = task_id
        self.description = description
        self.context = context
        self.priority = priority
        self.dependencies = dependencies or []
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "context": self.context,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "metadata": self.metadata,
        }


class PersonaResult:
    """Result from persona task processing."""
    
    def __init__(
        self,
        task_id: str,
        result: str,
        confidence: float = 1.0,  # 0.0-1.0
        sources: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize persona result.
        
        Args:
            task_id: Task identifier this result corresponds to
            result: Result content/text
            confidence: Confidence score (0.0-1.0)
            sources: List of sources used
            metadata: Additional metadata
        """
        self.task_id = task_id
        self.result = result
        self.confidence = confidence
        self.sources = sources or []
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "result": self.result,
            "confidence": self.confidence,
            "sources": self.sources,
            "metadata": self.metadata,
        }


class PersonaInterface(ABC):
    """
    Abstract interface for DAS personas.
    
    Personas are specialized AI agents with specific roles and capabilities.
    They process tasks using their specialized knowledge and skills.
    """
    
    @abstractmethod
    async def process_task(self, task: PersonaTask) -> PersonaResult:
        """
        Process a task using this persona's specialized capabilities.
        
        Args:
            task: Task to process
            
        Returns:
            PersonaResult with the processed result
        """
        pass
    
    @abstractmethod
    def get_role(self) -> PersonaRole:
        """
        Get this persona's role.
        
        Returns:
            PersonaRole enum value
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[PersonaCapability]:
        """
        Get this persona's capabilities.
        
        Returns:
            List of PersonaCapability enum values
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """
        Get this persona's name.
        
        Returns:
            Persona name string
        """
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """
        Get this persona's description.
        
        Returns:
            Persona description string
        """
        pass
    
    @abstractmethod
    async def can_handle_task(self, task: PersonaTask) -> bool:
        """
        Check if this persona can handle a given task.
        
        Args:
            task: Task to check
            
        Returns:
            True if persona can handle the task, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """
        Get current status of this persona.
        
        Returns:
            Dictionary with status information (available, busy, etc.)
        """
        pass
