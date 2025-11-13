"""
DAS Team Orchestrator Implementation

Implements TeamOrchestratorInterface for coordinating teams of personas.
Supports flexible team configurations that can be created by admins/SMEs.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from .team_orchestrator_interface import (
    TeamOrchestratorInterface,
    CoordinationStrategy,
    TeamResult,
)
from .persona_interface import PersonaTask, PersonaResult, PersonaInterface
from .config import Settings
from .db import DatabaseService

# Import PersonaFactory - will be defined in das_personas.py
from .das_personas import PersonaFactory

logger = logging.getLogger(__name__)


class DASTeamOrchestrator(TeamOrchestratorInterface):
    """
    DAS team orchestrator implementation.
    
    Coordinates teams of personas with flexible configurations.
    Supports loading team configurations from database (created by admins/SMEs).
    """
    
    def __init__(
        self,
        settings: Settings,
        persona_factory: Optional[PersonaFactory] = None,
        db_service: Optional[DatabaseService] = None,
    ):
        """
        Initialize team orchestrator.
        
        Args:
            settings: Application settings
            persona_factory: Optional persona factory (creates one if not provided)
            db_service: Optional database service
        """
        self.settings = settings
        self.db_service = db_service or DatabaseService(settings)
        self.persona_factory = persona_factory or PersonaFactory(settings, db_service)
        
        self._personas: Dict[str, PersonaInterface] = {}
        self._coordination_strategy = CoordinationStrategy.MODERATOR
        self._team_config: Optional[Dict[str, Any]] = None
        self._team_id: Optional[str] = None
        self._team_name: Optional[str] = None
    
    async def add_persona(
        self,
        persona: PersonaInterface,
        role_in_team: Optional[str] = None,
    ) -> bool:
        """Add a persona to the team."""
        self._personas[persona.get_name()] = persona
        logger.info(f"Added persona '{persona.get_name()}' to team")
        return True
    
    async def remove_persona(self, persona_name: str) -> bool:
        """Remove a persona from the team."""
        if persona_name in self._personas:
            del self._personas[persona_name]
            logger.info(f"Removed persona '{persona_name}' from team")
            return True
        return False
    
    async def get_team_status(self) -> Dict[str, Any]:
        """Get current team status."""
        persona_statuses = {}
        for name, persona in self._personas.items():
            persona_statuses[name] = await persona.get_status()
        
        return {
            "team_id": self._team_id,
            "team_name": self._team_name,
            "coordination_strategy": self._coordination_strategy.value,
            "persona_count": len(self._personas),
            "persona_statuses": persona_statuses,
        }
    
    async def get_team_members(self) -> List[Dict[str, Any]]:
        """Get list of team members."""
        members = []
        for name, persona in self._personas.items():
            members.append({
                "name": name,
                "role": persona.get_role().value,
                "capabilities": [cap.value for cap in persona.get_capabilities()],
                "description": persona.get_description(),
            })
        return members
    
    def get_coordination_strategy(self) -> CoordinationStrategy:
        """Get coordination strategy."""
        return self._coordination_strategy
    
    async def load_team_config(self, team_id_or_name: str) -> bool:
        """
        Load team configuration from database.
        
        Args:
            team_id_or_name: Team ID (UUID) or name
            
        Returns:
            True if loaded successfully, False otherwise
        """
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                # Try UUID first, then name
                try:
                    UUID(team_id_or_name)
                    cur.execute("""
                        SELECT 
                            team_id, name, description, domain, persona_ids,
                            workflow_config, coordination_strategy, metadata
                        FROM das_teams
                        WHERE team_id = %s AND is_active = TRUE
                    """, (team_id_or_name,))
                except ValueError:
                    cur.execute("""
                        SELECT 
                            team_id, name, description, domain, persona_ids,
                            workflow_config, coordination_strategy, metadata
                        FROM das_teams
                        WHERE name = %s AND is_active = TRUE
                    """, (team_id_or_name,))
                
                row = cur.fetchone()
                if not row:
                    logger.warning(f"Team '{team_id_or_name}' not found")
                    return False
                
                team_id, name, description, domain, persona_ids, \
                workflow_config, strategy_str, metadata = row
                
                self._team_id = str(team_id)
                self._team_name = name
                self._team_config = {
                    "description": description,
                    "domain": domain,
                    "workflow_config": workflow_config or {},
                    "metadata": metadata or {},
                }
                
                # Set coordination strategy
                try:
                    self._coordination_strategy = CoordinationStrategy(strategy_str)
                except ValueError:
                    logger.warning(f"Invalid strategy {strategy_str}, defaulting to MODERATOR")
                    self._coordination_strategy = CoordinationStrategy.MODERATOR
                
                # Load personas
                self._personas.clear()
                for persona_id in (persona_ids or []):
                    persona = await self.persona_factory.get_persona(str(persona_id))
                    if persona:
                        await self.add_persona(persona)
                    else:
                        logger.warning(f"Failed to load persona {persona_id} for team {name}")
                
                logger.info(f"Loaded team '{name}' with {len(self._personas)} personas")
                return True
        except Exception as e:
            logger.error(f"Failed to load team {team_id_or_name}: {e}")
            return False
        finally:
            self.db_service._return(conn)
    
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
        if not self._personas:
            return TeamResult(
                task_id=task.task_id,
                result="No personas available in team",
                persona_results=[],
                coordination_metadata={"error": "no_personas"},
            )
        
        # Use override config if provided
        config = team_config or self._team_config or {}
        strategy = self._coordination_strategy
        
        # Execute based on strategy
        if strategy == CoordinationStrategy.MODERATOR:
            return await self._coordinate_with_moderator(task, config)
        elif strategy == CoordinationStrategy.PARALLEL:
            return await self._coordinate_parallel(task, config)
        elif strategy == CoordinationStrategy.SEQUENTIAL:
            return await self._coordinate_sequential(task, config)
        else:  # CUSTOM
            return await self._coordinate_custom(task, config)
    
    async def _coordinate_with_moderator(
        self,
        task: PersonaTask,
        config: Dict[str, Any],
    ) -> TeamResult:
        """Coordinate using moderator strategy."""
        # Find moderator persona
        moderator = None
        for persona in self._personas.values():
            if persona.get_role().value == "moderator":
                moderator = persona
                break
        
        if not moderator:
            # If no moderator, use first persona
            moderator = list(self._personas.values())[0]
        
        # Moderator breaks down task and assigns to team members
        moderator_task = PersonaTask(
            task_id=f"{task.task_id}_moderator",
            description=f"Coordinate this task: {task.description}. Break it down and assign to team members: {', '.join(self._personas.keys())}",
            context=task.context,
        )
        
        moderator_result = await moderator.process_task(moderator_task)
        
        # For now, return moderator's coordination result
        # In full implementation, moderator would assign subtasks to other personas
        return TeamResult(
            task_id=task.task_id,
            result=moderator_result.result,
            persona_results=[moderator_result],
            coordination_metadata={"strategy": "moderator", "moderator": moderator.get_name()},
        )
    
    async def _coordinate_parallel(
        self,
        task: PersonaTask,
        config: Dict[str, Any],
    ) -> TeamResult:
        """Coordinate using parallel strategy - all personas work simultaneously."""
        import asyncio
        
        # Create tasks for all personas
        tasks = []
        for persona in self._personas.values():
            if await persona.can_handle_task(task):
                tasks.append(persona.process_task(task))
        
        # Execute all in parallel
        persona_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        valid_results = []
        for result in persona_results:
            if isinstance(result, PersonaResult):
                valid_results.append(result)
            else:
                logger.error(f"Persona task failed: {result}")
        
        # Synthesize results
        synthesized = self._synthesize_results(valid_results)
        
        return TeamResult(
            task_id=task.task_id,
            result=synthesized,
            persona_results=valid_results,
            coordination_metadata={"strategy": "parallel", "persona_count": len(valid_results)},
        )
    
    async def _coordinate_sequential(
        self,
        task: PersonaTask,
        config: Dict[str, Any],
    ) -> TeamResult:
        """Coordinate using sequential strategy - personas work in order."""
        persona_results = []
        current_task = task
        
        # Process through personas in order
        for persona in self._personas.values():
            if await persona.can_handle_task(current_task):
                result = await persona.process_task(current_task)
                persona_results.append(result)
                
                # Next persona gets previous result as context
                current_task = PersonaTask(
                    task_id=f"{task.task_id}_{persona.get_name()}",
                    description=current_task.description,
                    context={
                        **current_task.context,
                        "previous_result": result.result,
                    },
                )
        
        # Synthesize final result
        synthesized = self._synthesize_results(persona_results)
        
        return TeamResult(
            task_id=task.task_id,
            result=synthesized,
            persona_results=persona_results,
            coordination_metadata={"strategy": "sequential", "persona_count": len(persona_results)},
        )
    
    async def _coordinate_custom(
        self,
        task: PersonaTask,
        config: Dict[str, Any],
    ) -> TeamResult:
        """Coordinate using custom workflow from config."""
        workflow = config.get("workflow_config", {})
        
        # For now, fall back to moderator strategy
        # Full implementation would parse custom workflow
        logger.warning("Custom workflow not fully implemented, using moderator strategy")
        return await self._coordinate_with_moderator(task, config)
    
    def _synthesize_results(self, results: List[PersonaResult]) -> str:
        """
        Synthesize multiple persona results into a single result.
        
        Args:
            results: List of persona results
            
        Returns:
            Synthesized result text
        """
        if not results:
            return "No results from team members."
        
        if len(results) == 1:
            return results[0].result
        
        # Combine results with headers
        synthesized = "Team Results:\n\n"
        for i, result in enumerate(results, 1):
            persona_name = result.metadata.get("persona", f"Persona {i}")
            synthesized += f"--- {persona_name} ---\n{result.result}\n\n"
        
        return synthesized
