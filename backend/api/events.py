"""
Event Manager API - Comprehensive event management endpoints for admin users

Provides admin-only access to:
- Real-time event monitoring
- Event analytics and statistics
- Event history with filtering
- Event configuration management
- System health monitoring

Uses SQL-first approach with project_event table as source of truth.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
import json

from ..services.db import DatabaseService
from ..services.config import Settings
from ..services.auth import get_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/events", tags=["events"])


# ===== RESPONSE MODELS =====

class EventStatistics(BaseModel):
    """Event analytics and dashboard statistics"""
    total_events_24h: int
    total_events_7d: int
    active_projects_24h: int
    top_event_types: List[Dict[str, Any]]
    most_active_project: Optional[Dict[str, Any]]
    events_by_hour: List[Dict[str, Any]]
    system_health: str


class RecentEvent(BaseModel):
    """Recent event data for live monitoring"""
    event_id: str
    event_type: str
    semantic_summary: str
    project_id: Optional[str]
    project_name: Optional[str]
    user_id: str
    created_at: datetime
    event_data: Dict[str, Any]
    context_snapshot: Dict[str, Any]


class EventHistoryResponse(BaseModel):
    """Event history with pagination and filtering"""
    events: List[RecentEvent]
    total_count: int
    page: int
    per_page: int
    has_more: bool


class EventTypeConfig(BaseModel):
    """Event type configuration"""
    event_type: str
    enabled: bool
    description: str
    count_24h: int


class EventHealthStatus(BaseModel):
    """Event system health status"""
    status: str  # "healthy", "warning", "error"
    sql_first_active: bool
    event_capture_initialized: bool
    database_status: Dict[str, Any]
    recent_errors: List[str]
    performance_metrics: Dict[str, Any]


# ===== ADMIN VERIFICATION =====

def verify_admin_access(user: dict):
    """Verify user has admin access for event management"""
    if not user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Event Manager access requires admin privileges"
        )


# ===== EVENT ANALYTICS ENDPOINTS =====

@router.get("/statistics", response_model=EventStatistics)
async def get_event_statistics(
    user: dict = Depends(get_user),
    db: DatabaseService = Depends(lambda: DatabaseService(Settings()))
):
    """Get comprehensive event analytics for dashboard"""
    verify_admin_access(user)

    try:
        conn = db._conn()

        try:
            with conn.cursor() as cur:
                # Total events in last 24 hours
                cur.execute("""
                    SELECT COUNT(*) FROM project_event
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                """)
                total_events_24h = cur.fetchone()[0]

                # Total events in last 7 days
                cur.execute("""
                    SELECT COUNT(*) FROM project_event
                    WHERE created_at > NOW() - INTERVAL '7 days'
                """)
                total_events_7d = cur.fetchone()[0]

                # Active projects (with events in last 24 hours)
                cur.execute("""
                    SELECT COUNT(DISTINCT project_id) FROM project_event
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                """)
                active_projects_24h = cur.fetchone()[0]

                # Top event types in last 24 hours
                cur.execute("""
                    SELECT event_type, COUNT(*) as count
                    FROM project_event
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                    GROUP BY event_type
                    ORDER BY count DESC
                    LIMIT 10
                """)
                top_event_types = [
                    {"event_type": row[0], "count": row[1]}
                    for row in cur.fetchall()
                ]

                # Most active project
                cur.execute("""
                    SELECT
                        pe.project_id,
                        p.name as project_name,
                        COUNT(*) as event_count
                    FROM project_event pe
                    LEFT JOIN projects p ON pe.project_id = p.project_id::text
                    WHERE pe.created_at > NOW() - INTERVAL '24 hours'
                    GROUP BY pe.project_id, p.name
                    ORDER BY event_count DESC
                    LIMIT 1
                """)
                most_active_row = cur.fetchone()
                most_active_project = None
                if most_active_row:
                    most_active_project = {
                        "project_id": most_active_row[0],
                        "project_name": most_active_row[1] or "Unknown Project",
                        "event_count": most_active_row[2]
                    }

                # Events by hour (last 24 hours)
                cur.execute("""
                    SELECT
                        DATE_TRUNC('hour', created_at) as hour,
                        COUNT(*) as count
                    FROM project_event
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                    GROUP BY DATE_TRUNC('hour', created_at)
                    ORDER BY hour
                """)
                events_by_hour = [
                    {
                        "hour": row[0].isoformat(),
                        "count": row[1]
                    }
                    for row in cur.fetchall()
                ]

        finally:
            db._return(conn)

        # Determine system health
        system_health = "healthy"
        if total_events_24h == 0:
            system_health = "warning"
        elif total_events_24h < 5:
            system_health = "warning"

        return EventStatistics(
            total_events_24h=total_events_24h,
            total_events_7d=total_events_7d,
            active_projects_24h=active_projects_24h,
            top_event_types=top_event_types,
            most_active_project=most_active_project,
            events_by_hour=events_by_hour,
            system_health=system_health
        )

    except Exception as e:
        logger.error(f"Failed to get event statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve event statistics: {str(e)}"
        )


@router.get("/recent", response_model=List[RecentEvent])
async def get_recent_events(
    limit: int = Query(50, ge=1, le=200),
    event_type: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    user: dict = Depends(get_user),
    db: DatabaseService = Depends(lambda: DatabaseService(Settings()))
):
    """Get recent events for live monitoring"""
    verify_admin_access(user)

    try:
        conn = db._conn()

        try:
            with conn.cursor() as cur:
                # Build dynamic query with optional filters
                base_query = """
                    SELECT
                        pe.event_id,
                        pe.event_type,
                        pe.semantic_summary,
                        pe.project_id,
                        p.name as project_name,
                        pe.user_id,
                        pe.created_at,
                        pe.event_data,
                        pe.context_snapshot
                    FROM project_event pe
                    LEFT JOIN projects p ON pe.project_id = p.project_id::text
                """

                conditions = []
                params = []

                if event_type:
                    conditions.append("pe.event_type = %s")
                    params.append(event_type)

                if project_id:
                    conditions.append("pe.project_id = %s")
                    params.append(project_id)

                if conditions:
                    base_query += " WHERE " + " AND ".join(conditions)

                base_query += " ORDER BY pe.created_at DESC LIMIT %s"
                params.append(limit)

                cur.execute(base_query, params)
                events = cur.fetchall()

        finally:
            db._return(conn)

        # Format events for response
        recent_events = []
        for event_row in events:
            try:
                # Handle JSONB data - it might already be parsed or need parsing
                if isinstance(event_row[7], dict):
                    event_data = event_row[7]
                elif event_row[7]:
                    event_data = json.loads(event_row[7])
                else:
                    event_data = {}

                if isinstance(event_row[8], dict):
                    context_snapshot = event_row[8]
                elif event_row[8]:
                    context_snapshot = json.loads(event_row[8])
                else:
                    context_snapshot = {}

                recent_events.append(RecentEvent(
                    event_id=event_row[0],
                    event_type=event_row[1],
                    semantic_summary=event_row[2] or "No summary available",
                    project_id=event_row[3],
                    project_name=event_row[4] or "Unknown Project",
                    user_id=event_row[5],
                    created_at=event_row[6],
                    event_data=event_data,
                    context_snapshot=context_snapshot
                ))
            except Exception as parse_error:
                logger.warning(f"Error parsing event {event_row[0]}: {parse_error}")
                continue

        return recent_events

    except Exception as e:
        logger.error(f"Failed to get recent events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve recent events: {str(e)}"
        )


@router.get("/history", response_model=EventHistoryResponse)
async def get_event_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    event_type: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    user: dict = Depends(get_user),
    db: DatabaseService = Depends(lambda: DatabaseService(Settings()))
):
    """Get filtered event history with pagination"""
    verify_admin_access(user)

    try:
        conn = db._conn()
        offset = (page - 1) * per_page

        try:
            with conn.cursor() as cur:
                # Build query with filters
                base_query = """
                    SELECT
                        pe.event_id,
                        pe.event_type,
                        pe.semantic_summary,
                        pe.project_id,
                        p.name as project_name,
                        pe.user_id,
                        pe.created_at,
                        pe.event_data,
                        pe.context_snapshot
                    FROM project_event pe
                    LEFT JOIN projects p ON pe.project_id = p.project_id::text
                """

                count_query = "SELECT COUNT(*) FROM project_event pe"

                conditions = []
                params = []

                if event_type:
                    conditions.append("pe.event_type = %s")
                    params.append(event_type)

                if project_id:
                    conditions.append("pe.project_id = %s")
                    params.append(project_id)

                if start_date:
                    conditions.append("pe.created_at >= %s")
                    params.append(start_date)

                if end_date:
                    conditions.append("pe.created_at <= %s")
                    params.append(end_date)

                if conditions:
                    where_clause = " WHERE " + " AND ".join(conditions)
                    base_query += where_clause
                    count_query += where_clause

                # Get total count
                cur.execute(count_query, params)
                total_count = cur.fetchone()[0]

                # Get paginated events
                base_query += " ORDER BY pe.created_at DESC LIMIT %s OFFSET %s"
                params.extend([per_page, offset])

                cur.execute(base_query, params)
                events = cur.fetchall()

        finally:
            db._return(conn)

        # Format events
        formatted_events = []
        for event_row in events:
            try:
                # Handle JSONB data safely
                if isinstance(event_row[7], dict):
                    event_data = event_row[7]
                elif event_row[7]:
                    event_data = json.loads(event_row[7])
                else:
                    event_data = {}

                if isinstance(event_row[8], dict):
                    context_snapshot = event_row[8]
                elif event_row[8]:
                    context_snapshot = json.loads(event_row[8])
                else:
                    context_snapshot = {}

                formatted_events.append(RecentEvent(
                    event_id=event_row[0],
                    event_type=event_row[1],
                    semantic_summary=event_row[2] or "No summary available",
                    project_id=event_row[3],
                    project_name=event_row[4] or "Unknown Project",
                    user_id=event_row[5],
                    created_at=event_row[6],
                    event_data=event_data,
                    context_snapshot=context_snapshot
                ))
            except Exception as parse_error:
                logger.warning(f"Error parsing event {event_row[0]}: {parse_error}")
                continue

        has_more = offset + len(formatted_events) < total_count

        return EventHistoryResponse(
            events=formatted_events,
            total_count=total_count,
            page=page,
            per_page=per_page,
            has_more=has_more
        )

    except Exception as e:
        logger.error(f"Failed to get event history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve event history: {str(e)}"
        )


@router.get("/types", response_model=List[EventTypeConfig])
async def get_event_types(
    user: dict = Depends(get_user),
    db: DatabaseService = Depends(lambda: DatabaseService(Settings()))
):
    """Get available event types with configuration"""
    verify_admin_access(user)

    try:
        # Get event type counts from database
        conn = db._conn()

        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        event_type,
                        COUNT(*) as count_24h
                    FROM project_event
                    WHERE created_at > NOW() - INTERVAL '24 hours'
                    GROUP BY event_type
                    ORDER BY count_24h DESC
                """)

                active_types = dict(cur.fetchall())

        finally:
            db._return(conn)

        # Define all available event types with descriptions
        all_event_types = {
            "project_created": "Project creation events",
            "project_updated": "Project modification events",
            "project_deleted": "Project deletion events",
            "ontology_created": "Ontology creation events",
            "ontology_modified": "Ontology modification events",
            "ontology_saved": "Ontology save events",
            "class_created": "Class creation events",
            "class_updated": "Class modification events",
            "property_created": "Property creation events",
            "relationship_added": "Relationship/axiom creation events",
            "file_uploaded": "File upload events",
            "file_deleted": "File deletion events",
            "file_processing_started": "File processing initiation events",
            "file_processing_completed": "File processing completion events",
            "file_processing_failed": "File processing failure events",
            "knowledge_asset_created": "Knowledge asset creation events",
            "knowledge_asset_updated": "Knowledge asset update events",
            "knowledge_searched": "Knowledge search events",
            "workflow_started": "Workflow execution events",
            "das_interaction": "DAS interaction events",
            "das_question": "DAS question events",
            "das_response": "DAS response events",
            "user_login": "User authentication events",
            "system_error": "System error events"
        }

        # Build response
        event_type_configs = []
        for event_type, description in all_event_types.items():
            count_24h = active_types.get(event_type, 0)

            event_type_configs.append(EventTypeConfig(
                event_type=event_type,
                enabled=True,  # All types enabled by default
                description=description,
                count_24h=count_24h
            ))

        return event_type_configs

    except Exception as e:
        logger.error(f"Failed to get event types: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve event types: {str(e)}"
        )


@router.get("/health", response_model=EventHealthStatus)
async def get_event_health(
    user: dict = Depends(get_user),
    db: DatabaseService = Depends(lambda: DatabaseService(Settings()))
):
    """Get event system health status"""
    verify_admin_access(user)

    try:
        # Check EventCapture2 status
        event_capture_initialized = False
        sql_first_active = False

        try:
            from backend.services.eventcapture2 import get_event_capture
            event_capture = get_event_capture()
            event_capture_initialized = bool(event_capture)
            sql_first_active = bool(event_capture and event_capture.sql_first_manager)
        except:
            pass

        # Check database status
        conn = db._conn()
        database_status = {}
        recent_errors = []

        try:
            with conn.cursor() as cur:
                # Check table existence
                cur.execute("""
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_name IN ('project_event', 'thread_conversation', 'project_thread')
                """)
                tables_exist = cur.fetchone()[0]

                # Get event counts
                cur.execute("SELECT COUNT(*) FROM project_event")
                total_events = cur.fetchone()[0]

                cur.execute("""
                    SELECT COUNT(*) FROM project_event
                    WHERE created_at > NOW() - INTERVAL '1 hour'
                """)
                events_last_hour = cur.fetchone()[0]

                database_status = {
                    "tables_exist": tables_exist == 3,
                    "total_events": total_events,
                    "events_last_hour": events_last_hour,
                    "connection_healthy": True
                }

        finally:
            db._return(conn)

        # Determine overall status
        if not database_status.get("connection_healthy"):
            overall_status = "error"
        elif not event_capture_initialized or not sql_first_active:
            overall_status = "warning"
        elif database_status.get("events_last_hour", 0) == 0:
            overall_status = "warning"
        else:
            overall_status = "healthy"

        return EventHealthStatus(
            status=overall_status,
            sql_first_active=sql_first_active,
            event_capture_initialized=event_capture_initialized,
            database_status=database_status,
            recent_errors=recent_errors,
            performance_metrics={
                "avg_events_per_hour": database_status.get("events_last_hour", 0),
                "total_events": database_status.get("total_events", 0)
            }
        )

    except Exception as e:
        logger.error(f"Failed to get event health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve event health: {str(e)}"
        )


# ===== EVENT MANAGEMENT ENDPOINTS =====

@router.post("/clear")
async def clear_old_events(
    days_old: int = Query(30, ge=1, le=365),
    user: dict = Depends(get_user),
    db: DatabaseService = Depends(lambda: DatabaseService(Settings()))
):
    """Clear events older than specified days (admin maintenance)"""
    verify_admin_access(user)

    try:
        conn = db._conn()

        try:
            with conn.cursor() as cur:
                # Get count before deletion
                cur.execute("""
                    SELECT COUNT(*) FROM project_event
                    WHERE created_at < NOW() - INTERVAL '%s days'
                """, (days_old,))
                old_count = cur.fetchone()[0]

                # Delete old events
                cur.execute("""
                    DELETE FROM project_event
                    WHERE created_at < NOW() - INTERVAL '%s days'
                """, (days_old,))

                conn.commit()

        finally:
            db._return(conn)

        logger.info(f"Cleared {old_count} events older than {days_old} days by admin {user.get('username')}")

        return {
            "success": True,
            "message": f"Cleared {old_count} events older than {days_old} days",
            "events_cleared": old_count
        }

    except Exception as e:
        logger.error(f"Failed to clear old events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear old events: {str(e)}"
        )


@router.get("/config")
async def get_event_config(
    user: dict = Depends(get_user)
):
    """Get event system configuration"""
    verify_admin_access(user)

    try:
        # Get current configuration
        from backend.services.eventcapture2 import get_event_capture
        event_capture = get_event_capture()

        config = {
            "event_capture_initialized": bool(event_capture),
            "sql_first_active": bool(event_capture and event_capture.sql_first_manager),
            "redis_backup_active": bool(event_capture and event_capture.redis),
            "supported_event_types": 25,  # Based on our comprehensive EventType enum
            "storage_method": "sql_first" if event_capture and event_capture.sql_first_manager else "redis_only",
            "architecture": "unified",
            "version": "2.0"
        }

        return {"success": True, "config": config}

    except Exception as e:
        logger.error(f"Failed to get event config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve event configuration: {str(e)}"
        )
