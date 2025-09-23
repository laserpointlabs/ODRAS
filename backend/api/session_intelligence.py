"""
Session Intelligence API - Demonstrates DAS's session awareness capabilities
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from backend.services.config import Settings
from backend.services.session_thread_service import session_thread_service
from backend.services.semantic_event_capture import semantic_capture

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/session-intelligence", tags=["session-intelligence"])


class SessionSummaryResponse(BaseModel):
    """Response model for session summary"""
    session_thread_id: str
    username: str
    start_time: str
    duration_minutes: float
    session_goals: Optional[str]
    project_id: Optional[str]
    event_count: int
    activity_summary: Dict[str, Any]
    key_insights: List[str]


class SessionSearchRequest(BaseModel):
    """Request model for session search"""
    username: str
    query: str
    limit: int = 5


class SessionSearchResponse(BaseModel):
    """Response model for session search"""
    results: List[Dict[str, Any]]
    total_found: int


class DASContextRequest(BaseModel):
    """Request for DAS context about current session"""
    session_thread_id: str
    current_question: str


class DASContextResponse(BaseModel):
    """DAS context response with session intelligence"""
    session_context: Dict[str, Any]
    relevant_history: List[Dict[str, Any]]
    suggested_actions: List[str]
    context_insights: List[str]


@router.get("/session/{session_thread_id}/summary", response_model=SessionSummaryResponse)
async def get_session_summary(
    session_thread_id: str
):
    """
    Get a comprehensive summary of a session thread with intelligent insights
    """
    try:
        if not session_thread_service:
            raise HTTPException(status_code=503, detail="Session service not available")

        # Get session thread
        session_thread = await session_thread_service.get_session_thread(session_thread_id)
        if not session_thread:
            raise HTTPException(status_code=404, detail="Session thread not found")

        # Calculate duration
        end_time = session_thread.end_time or datetime.now()
        duration = (end_time - session_thread.start_time).total_seconds() / 60

        # Analyze activity patterns
        activity_summary = _analyze_session_activity(session_thread.events)

        # Generate insights
        insights = _generate_session_insights(session_thread, activity_summary)

        return SessionSummaryResponse(
            session_thread_id=session_thread.session_thread_id,
            username=session_thread.username,
            start_time=session_thread.start_time.isoformat(),
            duration_minutes=duration,
            session_goals=session_thread.session_goals,
            project_id=session_thread.project_id,
            event_count=len(session_thread.events),
            activity_summary=activity_summary,
            key_insights=insights
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SessionSearchResponse)
async def search_sessions(
    request: SessionSearchRequest
):
    """
    Search for similar session threads using semantic similarity
    """
    try:
        if not session_thread_service:
            raise HTTPException(status_code=503, detail="Session service not available")

        results = await session_thread_service.search_user_threads(
            username=request.username,
            query=request.query,
            limit=request.limit
        )

        return SessionSearchResponse(
            results=results,
            total_found=len(results)
        )

    except Exception as e:
        logger.error(f"Error searching sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/das-context", response_model=DASContextResponse)
async def get_das_context(
    request: DASContextRequest
):
    """
    Get intelligent context for DAS based on current session and history
    """
    try:
        if not session_thread_service:
            raise HTTPException(status_code=503, detail="Session service not available")

        # Get current session
        session_thread = await session_thread_service.get_session_thread(request.session_thread_id)
        if not session_thread:
            raise HTTPException(status_code=404, detail="Session thread not found")

        # Get session context
        session_context = {
            "session_goals": session_thread.session_goals,
            "project_id": session_thread.project_id,
            "username": session_thread.username,
            "duration_minutes": (datetime.now() - session_thread.start_time).total_seconds() / 60,
            "recent_activity": _get_recent_activity_summary(session_thread.events[-5:])
        }

        # Find relevant historical sessions
        relevant_history = await session_thread_service.search_user_threads(
            username=session_thread.username,
            query=request.current_question,
            limit=3
        )

        # Generate contextual insights
        context_insights = _generate_context_insights(session_thread, request.current_question)

        # Generate suggested actions
        suggested_actions = _generate_suggested_actions(session_thread, request.current_question)

        return DASContextResponse(
            session_context=session_context,
            relevant_history=relevant_history,
            suggested_actions=suggested_actions,
            context_insights=context_insights
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting DAS context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active-sessions")
async def get_active_sessions():
    """
    Get list of currently active session threads
    """
    try:
        # This would normally query Redis for active sessions
        # For now, return a placeholder response
        return {
            "active_sessions": [],
            "message": "Active session tracking requires Redis key scanning implementation"
        }

    except Exception as e:
        logger.error(f"Error getting active sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _analyze_session_activity(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze session activity patterns"""
    if not events:
        return {"total_events": 0, "activity_types": {}, "timeline": []}

    activity_types = {}
    timeline = []

    for event in events:
        event_type = event.get("event_type", "unknown")
        activity_types[event_type] = activity_types.get(event_type, 0) + 1

        timeline.append({
            "timestamp": event.get("timestamp"),
            "event_type": event_type,
            "summary": _summarize_event(event)
        })

    return {
        "total_events": len(events),
        "activity_types": activity_types,
        "timeline": timeline[-10:],  # Last 10 events
        "dominant_activity": max(activity_types.items(), key=lambda x: x[1])[0] if activity_types else "none"
    }


def _summarize_event(event: Dict[str, Any]) -> str:
    """Create a human-readable summary of an event"""
    event_type = event.get("event_type", "unknown")
    event_data = event.get("event_data", {})

    if event_type == "user_message":
        return f"Asked: {event_data.get('message', '')[:50]}..."
    elif event_type == "das_response":
        return f"DAS responded about: {event_data.get('response', '')[:50]}..."
    elif event_type == "api_call":
        return f"API: {event_data.get('method', '')} {event_data.get('endpoint', '')}"
    elif event_type == "ontology_selected":
        return f"Selected ontology: {event_data.get('ontology_name', 'Unknown')}"
    else:
        return f"{event_type}: {str(event_data)[:50]}..."


def _generate_session_insights(session_thread, activity_summary: Dict[str, Any]) -> List[str]:
    """Generate intelligent insights about the session"""
    insights = []

    # Duration insights
    duration = (datetime.now() - session_thread.start_time).total_seconds() / 60
    if duration > 60:
        insights.append(f"Long session ({duration:.1f} minutes) - user is deeply engaged")
    elif duration < 5:
        insights.append("Short session - user may need quick assistance")

    # Activity pattern insights
    dominant_activity = activity_summary.get("dominant_activity", "none")
    if dominant_activity == "user_message":
        insights.append("Heavy interaction session - user is actively asking questions")
    elif dominant_activity == "api_call":
        insights.append("System-focused session - user is working with tools")

    # Goal-based insights
    if session_thread.session_goals:
        insights.append(f"Session has clear goals: {session_thread.session_goals}")
    else:
        insights.append("No explicit goals set - DAS could help clarify objectives")

    # Project context
    if session_thread.project_id:
        insights.append(f"Working within project context: {session_thread.project_id}")

    return insights


def _get_recent_activity_summary(recent_events: List[Dict[str, Any]]) -> List[str]:
    """Get summary of recent activity"""
    return [_summarize_event(event) for event in recent_events]


def _generate_context_insights(session_thread, current_question: str) -> List[str]:
    """Generate insights based on session context and current question"""
    insights = []

    # Question pattern analysis
    if "ontology" in current_question.lower():
        insights.append("User is asking about ontologies - check if they have an active ontology selected")

    if "help" in current_question.lower():
        insights.append("User is requesting help - provide comprehensive assistance")

    if session_thread.session_goals and any(word in current_question.lower() for word in session_thread.session_goals.lower().split()):
        insights.append("Question relates to stated session goals - prioritize goal-relevant response")

    return insights


def _generate_suggested_actions(session_thread, current_question: str) -> List[str]:
    """Generate suggested actions for DAS"""
    actions = []

    # Based on session context
    if not session_thread.session_goals:
        actions.append("Ask user to clarify their goals for this session")

    if not session_thread.project_id:
        actions.append("Help user select or create a project context")

    # Based on question content
    if "ontology" in current_question.lower():
        actions.append("Show available ontologies and help with selection")
        actions.append("Offer to create or modify ontology structures")

    if "document" in current_question.lower() or "file" in current_question.lower():
        actions.append("Check if user has uploaded relevant documents")
        actions.append("Offer document analysis services")

    return actions

