"""
Data models and schemas for the ODRAS application.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class Persona(BaseModel):
    """Persona model for LLM team members."""
    id: str = Field(..., description="Unique identifier for the persona")
    name: str = Field(..., description="Display name for the persona")
    description: str = Field(..., description="Description of the persona's role")
    system_prompt: str = Field(..., description="System prompt for the persona")
    is_active: bool = Field(True, description="Whether the persona is currently active")


class Prompt(BaseModel):
    """Prompt template model."""
    id: str = Field(..., description="Unique identifier for the prompt")
    name: str = Field(..., description="Display name for the prompt")
    description: str = Field(..., description="Description of the prompt")
    prompt_template: str = Field(..., description="Template string with variables")
    variables: List[str] = Field(..., description="List of variable names in the template")
    is_active: bool = Field(True, description="Whether the prompt is currently active")


class RunStatus(BaseModel):
    """Model for tracking run status."""
    run_id: str = Field(..., description="Unique identifier for the run")
    status: str = Field(..., description="Current status of the run")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UserDecision(BaseModel):
    """Model for user decisions in review process."""
    decision: str = Field(..., description="User's decision (approve, edit, rerun)")
    user_edits: Optional[List[Dict[str, Any]]] = Field(None, description="User's edits if decision is edit")
    extraction_parameters: Optional[Dict[str, Any]] = Field(None, description="Parameters for rerun if decision is rerun")
    comment: Optional[str] = Field(None, description="Optional comment from user")


class APIResponse(BaseModel):
    """Standard API response model."""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Human-readable message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data if any")
    error: Optional[str] = Field(None, description="Error message if operation failed")
