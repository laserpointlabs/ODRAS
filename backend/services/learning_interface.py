"""
Learning Interface

Abstract interface for DAS learning system.
Enables DAS to learn from interactions and improve over time.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime, timezone


class InteractionType(Enum):
    """Types of interactions that can be learned from."""
    QUERY = "query"  # User query and DAS response
    FEEDBACK = "feedback"  # User feedback (positive/negative)
    CORRECTION = "correction"  # User correction to DAS output
    TASK_COMPLETION = "task_completion"  # Successful task completion
    ERROR = "error"  # Error that occurred


class FeedbackType(Enum):
    """Types of feedback."""
    POSITIVE = "positive"  # User liked the response
    NEGATIVE = "negative"  # User didn't like the response
    CORRECTION = "correction"  # User provided corrected information
    CLARIFICATION = "clarification"  # User asked for clarification


class InteractionRecord:
    """Record of an interaction for learning."""
    
    def __init__(
        self,
        interaction_id: str,
        interaction_type: InteractionType,
        user_id: str,
        project_id: Optional[str],
        query: str,
        response: str,
        context: Dict[str, Any],
        feedback: Optional[FeedbackType] = None,
        correction: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ):
        """
        Initialize interaction record.
        
        Args:
            interaction_id: Unique interaction identifier
            interaction_type: Type of interaction
            user_id: User who initiated interaction
            project_id: Optional project context
            query: User query/message
            response: DAS response
            context: Context information (personas used, tools called, etc.)
            feedback: Optional feedback type
            correction: Optional correction text
            metadata: Additional metadata
            timestamp: Interaction timestamp
        """
        self.interaction_id = interaction_id
        self.interaction_type = interaction_type
        self.user_id = user_id
        self.project_id = project_id
        self.query = query
        self.response = response
        self.context = context
        self.feedback = feedback
        self.correction = correction
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "interaction_id": self.interaction_id,
            "interaction_type": self.interaction_type.value,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "query": self.query,
            "response": self.response,
            "context": self.context,
            "feedback": self.feedback.value if self.feedback else None,
            "correction": self.correction,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class LearningInsight:
    """Insight derived from learning."""
    
    def __init__(
        self,
        insight_id: str,
        insight_type: str,
        description: str,
        confidence: float,
        recommendations: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize learning insight.
        
        Args:
            insight_id: Unique insight identifier
            insight_type: Type of insight (pattern, improvement, etc.)
            description: Insight description
            confidence: Confidence score (0.0-1.0)
            recommendations: List of recommended actions
            metadata: Additional metadata
        """
        self.insight_id = insight_id
        self.insight_type = insight_type
        self.description = description
        self.confidence = confidence
        self.recommendations = recommendations
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "insight_id": self.insight_id,
            "insight_type": self.insight_type,
            "description": self.description,
            "confidence": self.confidence,
            "recommendations": self.recommendations,
            "metadata": self.metadata,
        }


class LearningInterface(ABC):
    """
    Abstract interface for DAS learning system.
    
    Enables DAS to learn from interactions, user feedback, and corrections
    to improve behavior over time.
    """
    
    @abstractmethod
    async def record_interaction(self, interaction: InteractionRecord) -> bool:
        """
        Record an interaction for learning.
        
        Args:
            interaction: Interaction record to store
            
        Returns:
            True if recorded successfully, False otherwise
        """
        pass
    
    @abstractmethod
    async def learn_from_feedback(
        self,
        interaction_id: str,
        feedback_type: FeedbackType,
        feedback_text: Optional[str] = None,
    ) -> bool:
        """
        Learn from user feedback.
        
        Args:
            interaction_id: ID of interaction to learn from
            feedback_type: Type of feedback
            feedback_text: Optional feedback text
            
        Returns:
            True if learning was successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def learn_from_correction(
        self,
        interaction_id: str,
        correction: str,
        corrected_response: str,
    ) -> bool:
        """
        Learn from user correction.
        
        Args:
            interaction_id: ID of interaction to learn from
            correction: Correction text explaining what was wrong
            corrected_response: Corrected response
            
        Returns:
            True if learning was successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_improvements(
        self,
        persona_name: Optional[str] = None,
        domain: Optional[str] = None,
        limit: int = 10,
    ) -> List[LearningInsight]:
        """
        Get learning insights and improvements.
        
        Args:
            persona_name: Optional persona to get improvements for
            domain: Optional domain to filter by
            limit: Maximum number of insights to return
            
        Returns:
            List of learning insights
        """
        pass
    
    @abstractmethod
    async def get_interaction_history(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        interaction_type: Optional[InteractionType] = None,
        limit: int = 50,
    ) -> List[InteractionRecord]:
        """
        Get interaction history for analysis.
        
        Args:
            user_id: Optional user ID filter
            project_id: Optional project ID filter
            interaction_type: Optional interaction type filter
            limit: Maximum number of interactions to return
            
        Returns:
            List of interaction records
        """
        pass
    
    @abstractmethod
    async def analyze_patterns(
        self,
        domain: Optional[str] = None,
        time_period_days: int = 30,
    ) -> Dict[str, Any]:
        """
        Analyze patterns in interactions.
        
        Args:
            domain: Optional domain to analyze
            time_period_days: Number of days to analyze
            
        Returns:
            Dictionary with pattern analysis results
        """
        pass
    
    @abstractmethod
    async def apply_learning(
        self,
        insight_id: str,
        persona_name: Optional[str] = None,
    ) -> bool:
        """
        Apply a learning insight to improve behavior.
        
        Args:
            insight_id: ID of insight to apply
            persona_name: Optional persona to apply to
            
        Returns:
            True if applied successfully, False otherwise
        """
        pass
