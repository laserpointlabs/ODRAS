"""
Team Orchestrator Interface

Abstract interface for coordinating teams of personas.
Enables flexible team configurations that can be created by admins/SMEs.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum

from .persona_interface import PersonaTask, PersonaResult, PersonaInterface


class CoordinationStrategy(Enum):
    """Strategies for coordinating team members."""
    MODERATOR = "moderator"  # Moderator assigns tasks and synthesizes
    PARALLEL = "parallel"  # All personas work in parallel
    SEQUENTIAL = "sequential"  # Personas work in sequence
    CUSTOM = "custom"  # Custom workflow defined in metadata


class TeamResult:
    """Result from team coordination."""
    
    def __init__(
        self,
        task_id: str,
        result: str,
        persona_results: List[PersonaResult],
        coordination_metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize team result.
        
        Args:
            task_id: Task identifier
            result: Final synthesized result
            persona_results: Results from individual personas
            coordination_metadata: Metadata about coordination process
        """
        self.task_id = task_id
        self.result = result
        self.persona_results = persona_results
        self.coordination_metadata = coordination_metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "result": self.result,
            "persona_results": [pr.to_dict() for pr in self.persona_results],
            "coordination_metadata": self.coordination_metadata,
        }


class TeamOrchestratorInterface(ABC):
    """
    Abstract interface for team coordination.
    
    Enables flexible team configurations where admins/SMEs can create
    custom teams (e.g., acquisition team) with specific personas and workflows.
    """
    
    @abstractmethod
    async def coordinate_task(
        self,
        task: PersonaTask,
        team_config: Optional[Dict[str, Any]] = None,
    ) -> TeamResult:
        """
        Coordinate a task across team members.
        
        Args:
            task: Task to coordinate
            team_config: Optional team configuration override
            
        Returns:
            TeamResult with synthesized output
        """
        pass
    
    @abstractmethod
    async def add_persona(
        self,
        persona: PersonaInterface,
        role_in_team: Optional[str] = None,
    ) -> bool:
        """
        Add a persona to the team.
        
        Args:
            persona: Persona to add
            role_in_team: Optional role description for this persona in the team
            
        Returns:
            True if added, False otherwise
        """
        pass
    
    @abstractmethod
    async def remove_persona(self, persona_name: str) -> bool:
        """
        Remove a persona from the team.
        
        Args:
            persona_name: Name of persona to remove
            
        Returns:
            True if removed, False if not found
        """
        pass
    
    @abstractmethod
    async def get_team_status(self) -> Dict[str, Any]:
        """
        Get current team status.
        
        Returns:
            Dictionary with team status information
        """
        pass
    
    @abstractmethod
    async def get_team_members(self) -> List[Dict[str, Any]]:
        """
        Get list of team members.
        
        Returns:
            List of team member dictionaries
        """
        pass
    
    @abstractmethod
    def get_coordination_strategy(self) -> CoordinationStrategy:
        """
        Get coordination strategy for this team.
        
        Returns:
            CoordinationStrategy enum value
        """
        pass
    
    @abstractmethod
    async def load_team_config(self, team_id_or_name: str) -> bool:
        """
        Load team configuration from database.
        
        Args:
            team_id_or_name: Team ID (UUID) or name
            
        Returns:
            True if loaded successfully, False otherwise
        """
        pass
