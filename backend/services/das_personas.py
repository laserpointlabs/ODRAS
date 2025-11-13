"""
DAS Personas Implementation

Implements PersonaInterface for specialized AI agents:
- Researcher: Finds and gathers information
- Analyst: Analyzes data and patterns
- Writer: Creates content and documentation
- Moderator: Coordinates team and assigns tasks
- Custom personas: Created by admins/SMEs and stored in database

Supports flexible, extensible persona system where admins can create
specialized personas (e.g., ontology specialist) and teams (e.g., acquisition team).
"""

import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
import httpx

from .persona_interface import (
    PersonaInterface,
    PersonaRole,
    PersonaCapability,
    PersonaTask,
    PersonaResult,
)
from .config import Settings
from .db import DatabaseService

logger = logging.getLogger(__name__)


class BasePersona(PersonaInterface):
    """Base persona implementation with common LLM calling logic."""
    
    def __init__(
        self,
        name: str,
        role: PersonaRole,
        capabilities: List[PersonaCapability],
        description: str,
        system_prompt: str,
        settings: Settings,
    ):
        """
        Initialize base persona.
        
        Args:
            name: Persona name
            role: Persona role
            capabilities: List of capabilities
            description: Persona description
            system_prompt: System prompt for LLM
            settings: Application settings
        """
        self._name = name
        self._role = role
        self._capabilities = capabilities
        self._description = description
        self._system_prompt = system_prompt
        self.settings = settings
        self._status = {"available": True, "busy": False}
    
    def get_name(self) -> str:
        """Get persona name."""
        return self._name
    
    def get_role(self) -> PersonaRole:
        """Get persona role."""
        return self._role
    
    def get_capabilities(self) -> List[PersonaCapability]:
        """Get persona capabilities."""
        return self._capabilities
    
    def get_description(self) -> str:
        """Get persona description."""
        return self._description
    
    async def can_handle_task(self, task: PersonaTask) -> bool:
        """
        Check if persona can handle task.
        
        Base implementation: check if task description matches persona capabilities.
        """
        task_lower = task.description.lower()
        
        # Simple keyword matching based on role
        role_keywords = {
            PersonaRole.RESEARCHER: ["find", "search", "gather", "retrieve", "information", "research"],
            PersonaRole.ANALYST: ["analyze", "analysis", "evaluate", "assess", "examine", "review"],
            PersonaRole.WRITER: ["write", "create", "document", "draft", "compose", "generate"],
            PersonaRole.MODERATOR: ["coordinate", "assign", "organize", "manage", "moderate"],
        }
        
        keywords = role_keywords.get(self._role, [])
        return any(keyword in task_lower for keyword in keywords)
    
    async def get_status(self) -> Dict[str, Any]:
        """Get persona status."""
        return self._status.copy()
    
    async def _call_llm(self, user_prompt: str, temperature: float = 0.7) -> str:
        """
        Call LLM with persona's system prompt.
        
        Args:
            user_prompt: User prompt/task description
            temperature: Temperature for response generation
            
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
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": temperature,
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
            logger.error(f"LLM call failed for {self._name}: {e}")
            raise
    
    async def process_task(self, task: PersonaTask) -> PersonaResult:
        """
        Process task using persona's specialized capabilities.
        
        Args:
            task: Task to process
            
        Returns:
            PersonaResult with processed result
        """
        self._status["busy"] = True
        self._status["available"] = False
        
        try:
            # Build prompt from task
            prompt = self._build_task_prompt(task)
            
            # Call LLM
            result_text = await self._call_llm(prompt, temperature=self._get_temperature())
            
            # Extract sources from context if available
            sources = []
            if task.context.get("sources"):
                sources = task.context["sources"]
            
            # Calculate confidence (simple heuristic)
            confidence = self._calculate_confidence(result_text, task)
            
            return PersonaResult(
                task_id=task.task_id,
                result=result_text,
                confidence=confidence,
                sources=sources,
                metadata={"persona": self._name, "role": self._role.value},
            )
        finally:
            self._status["busy"] = False
            self._status["available"] = True
    
    def _build_task_prompt(self, task: PersonaTask) -> str:
        """Build prompt from task (can be overridden by subclasses)."""
        prompt = f"Task: {task.description}\n\n"
        
        if task.context:
            prompt += "Context:\n"
            for key, value in task.context.items():
                if key != "sources":  # Sources handled separately
                    prompt += f"- {key}: {value}\n"
            prompt += "\n"
        
        return prompt
    
    def _get_temperature(self) -> float:
        """Get temperature for LLM calls (can be overridden by subclasses)."""
        return 0.7
    
    def _calculate_confidence(self, result: str, task: PersonaTask) -> float:
        """Calculate confidence score (can be overridden by subclasses)."""
        # Simple heuristic: longer, more detailed responses = higher confidence
        if len(result) < 50:
            return 0.5
        elif len(result) < 200:
            return 0.7
        else:
            return 0.9


class ResearcherPersona(BasePersona):
    """Researcher persona - finds and gathers information."""
    
    def __init__(self, settings: Settings):
        super().__init__(
            name="Researcher",
            role=PersonaRole.RESEARCHER,
            capabilities=[
                PersonaCapability.INFORMATION_RETRIEVAL,
                PersonaCapability.KNOWLEDGE_SYNTHESIS,
            ],
            description="Finds and gathers information from various sources",
            system_prompt="""You are a Researcher persona in a team of AI assistants. Your role is to:
- Find and gather relevant information from available sources
- Synthesize information from multiple sources
- Provide comprehensive, well-sourced answers
- Identify knowledge gaps and suggest where to find missing information

Be thorough, accurate, and cite your sources when possible.""",
            settings=settings,
        )
    
    def _get_temperature(self) -> float:
        """Lower temperature for more factual, accurate responses."""
        return 0.5


class AnalystPersona(BasePersona):
    """Analyst persona - analyzes data and patterns."""
    
    def __init__(self, settings: Settings):
        super().__init__(
            name="Analyst",
            role=PersonaRole.ANALYST,
            capabilities=[
                PersonaCapability.DATA_ANALYSIS,
                PersonaCapability.QUALITY_REVIEW,
            ],
            description="Analyzes data, identifies patterns, and provides insights",
            system_prompt="""You are an Analyst persona in a team of AI assistants. Your role is to:
- Analyze data and identify patterns, trends, and relationships
- Evaluate quality and consistency
- Provide insights and recommendations based on analysis
- Identify potential issues or concerns
- Present findings in a clear, structured manner

Be analytical, objective, and evidence-based in your analysis.""",
            settings=settings,
        )
    
    def _get_temperature(self) -> float:
        """Moderate temperature for balanced analysis."""
        return 0.6


class WriterPersona(BasePersona):
    """Writer persona - creates content and documentation."""
    
    def __init__(self, settings: Settings):
        super().__init__(
            name="Writer",
            role=PersonaRole.WRITER,
            capabilities=[
                PersonaCapability.CONTENT_CREATION,
            ],
            description="Creates content, documentation, and written materials",
            system_prompt="""You are a Writer persona in a team of AI assistants. Your role is to:
- Create clear, well-structured content and documentation
- Write in an appropriate tone and style for the audience
- Organize information logically and coherently
- Ensure content is accurate, complete, and easy to understand
- Format content appropriately (markdown, structured text, etc.)

Be clear, concise, and professional in your writing.""",
            settings=settings,
        )
    
    def _get_temperature(self) -> float:
        """Higher temperature for more creative writing."""
        return 0.8


class ModeratorPersona(BasePersona):
    """Moderator persona - coordinates team and assigns tasks."""
    
    def __init__(self, settings: Settings):
        super().__init__(
            name="Moderator",
            role=PersonaRole.MODERATOR,
            capabilities=[
                PersonaCapability.COORDINATION,
            ],
            description="Coordinates team, assigns tasks, and synthesizes team outputs",
            system_prompt="""You are a Moderator persona coordinating a team of AI assistants. Your role is to:
- Understand complex tasks and break them down into subtasks
- Assign appropriate tasks to team members (Researcher, Analyst, Writer)
- Coordinate team efforts and synthesize outputs
- Ensure quality and completeness of final deliverables
- Provide clear instructions and feedback to team members

Be organized, strategic, and ensure all aspects of tasks are covered.""",
            settings=settings,
        )
    
    async def can_handle_task(self, task: PersonaTask) -> bool:
        """Moderator can handle coordination tasks."""
        task_lower = task.description.lower()
        coordination_keywords = [
            "coordinate", "organize", "manage", "assign", "moderate",
            "team", "multiple", "complex", "synthesize", "combine"
        ]
        return any(keyword in task_lower for keyword in coordination_keywords)
    
    def _get_temperature(self) -> float:
        """Moderate temperature for structured coordination."""
        return 0.6


class CustomPersona(BasePersona):
    """
    Custom persona loaded from database configuration.
    
    Allows admins/SMEs to create specialized personas (e.g., ontology specialist)
    with custom system prompts and capabilities.
    """
    
    def __init__(
        self,
        persona_id: str,
        name: str,
        role: PersonaRole,
        capabilities: List[PersonaCapability],
        description: str,
        system_prompt: str,
        temperature: float,
        domain: Optional[str],
        settings: Settings,
    ):
        """
        Initialize custom persona from database configuration.
        
        Args:
            persona_id: Persona ID from database
            name: Persona name
            role: Persona role
            capabilities: List of capabilities
            description: Persona description
            system_prompt: Custom system prompt
            temperature: LLM temperature
            domain: Optional domain specialization
            settings: Application settings
        """
        super().__init__(
            name=name,
            role=role,
            capabilities=capabilities,
            description=description,
            system_prompt=system_prompt,
            settings=settings,
        )
        self.persona_id = persona_id
        self._temperature = temperature
        self._domain = domain
    
    def _get_temperature(self) -> float:
        """Get custom temperature from configuration."""
        return self._temperature
    
    async def can_handle_task(self, task: PersonaTask) -> bool:
        """
        Check if persona can handle task.
        
        Custom personas can have domain-specific matching.
        """
        # If persona has a domain, check if task mentions that domain
        if self._domain:
            task_lower = task.description.lower()
            if self._domain.lower() in task_lower:
                return True
        
        # Fall back to base implementation
        return await super().can_handle_task(task)


class PersonaFactory:
    """
    Factory for creating personas from database or built-in configurations.
    
    Supports loading custom personas created by admins/SMEs.
    """
    
    def __init__(self, settings: Settings, db_service: Optional[DatabaseService] = None):
        """Initialize persona factory."""
        self.settings = settings
        self.db_service = db_service or DatabaseService(settings)
        self._persona_cache: Dict[str, PersonaInterface] = {}
    
    async def get_persona(self, persona_id_or_name: str) -> Optional[PersonaInterface]:
        """
        Get persona by ID or name.
        
        Args:
            persona_id_or_name: Persona ID (UUID) or name
            
        Returns:
            PersonaInterface instance or None if not found
        """
        # Check cache first
        if persona_id_or_name in self._persona_cache:
            return self._persona_cache[persona_id_or_name]
        
        # Try built-in personas first
        built_in_personas = {
            "Researcher": ResearcherPersona(self.settings),
            "Analyst": AnalystPersona(self.settings),
            "Writer": WriterPersona(self.settings),
            "Moderator": ModeratorPersona(self.settings),
        }
        
        if persona_id_or_name in built_in_personas:
            persona = built_in_personas[persona_id_or_name]
            self._persona_cache[persona_id_or_name] = persona
            return persona
        
        # Load from database
        persona = await self._load_persona_from_db(persona_id_or_name)
        if persona:
            self._persona_cache[persona_id_or_name] = persona
        
        return persona
    
    async def _load_persona_from_db(self, persona_id_or_name: str) -> Optional[PersonaInterface]:
        """Load persona from database."""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                # Try UUID first, then name
                try:
                    UUID(persona_id_or_name)
                    cur.execute("""
                        SELECT 
                            persona_id, name, description, role, system_prompt,
                            capabilities, temperature, domain, metadata
                        FROM das_personas
                        WHERE persona_id = %s AND is_active = TRUE
                    """, (persona_id_or_name,))
                except ValueError:
                    cur.execute("""
                        SELECT 
                            persona_id, name, description, role, system_prompt,
                            capabilities, temperature, domain, metadata
                        FROM das_personas
                        WHERE name = %s AND is_active = TRUE
                    """, (persona_id_or_name,))
                
                row = cur.fetchone()
                if not row:
                    return None
                
                persona_id, name, description, role_str, system_prompt, \
                capabilities_list, temperature, domain, metadata = row
                
                # Convert role string to enum
                try:
                    role = PersonaRole(role_str)
                except ValueError:
                    logger.warning(f"Invalid role {role_str} for persona {name}, defaulting to SPECIALIST")
                    role = PersonaRole.SPECIALIST
                
                # Convert capabilities strings to enums
                capabilities = []
                for cap_str in (capabilities_list or []):
                    try:
                        capabilities.append(PersonaCapability(cap_str))
                    except ValueError:
                        logger.warning(f"Invalid capability {cap_str} for persona {name}")
                
                # Create custom persona
                persona = CustomPersona(
                    persona_id=str(persona_id),
                    name=name,
                    role=role,
                    capabilities=capabilities,
                    description=description or "",
                    system_prompt=system_prompt,
                    temperature=temperature or 0.7,
                    domain=domain,
                    settings=self.settings,
                )
                
                return persona
        except Exception as e:
            logger.error(f"Failed to load persona {persona_id_or_name}: {e}")
            return None
        finally:
            self.db_service._return(conn)
    
    async def list_personas(self, domain: Optional[str] = None, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        List all available personas.
        
        Args:
            domain: Optional domain filter
            active_only: Only return active personas
            
        Returns:
            List of persona dictionaries
        """
        personas = []
        
        # Add built-in personas
        built_in = [
            {"name": "Researcher", "role": "researcher", "is_system": True},
            {"name": "Analyst", "role": "analyst", "is_system": True},
            {"name": "Writer", "role": "writer", "is_system": True},
            {"name": "Moderator", "role": "moderator", "is_system": True},
        ]
        personas.extend(built_in)
        
        # Load from database
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                conditions = []
                params = []
                
                if active_only:
                    conditions.append("is_active = TRUE")
                
                if domain:
                    conditions.append("domain = %s")
                    params.append(domain)
                
                where_clause = " AND ".join(conditions) if conditions else "TRUE"
                
                cur.execute(f"""
                    SELECT 
                        persona_id, name, description, role, domain,
                        capabilities, temperature, is_system, created_by
                    FROM das_personas
                    WHERE {where_clause}
                    ORDER BY is_system DESC, name ASC
                """, params)
                
                rows = cur.fetchall()
                for row in rows:
                    persona_id, name, description, role, domain_val, \
                    capabilities, temperature, is_system, created_by = row
                    
                    personas.append({
                        "persona_id": str(persona_id),
                        "name": name,
                        "description": description,
                        "role": role,
                        "domain": domain_val,
                        "capabilities": capabilities or [],
                        "temperature": temperature,
                        "is_system": is_system,
                        "created_by": created_by,
                    })
        except Exception as e:
            logger.error(f"Failed to list personas: {e}")
        finally:
            self.db_service._return(conn)
        
        return personas
    
    def clear_cache(self):
        """Clear persona cache."""
        self._persona_cache.clear()
