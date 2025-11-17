import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.pool
from psycopg2.extras import RealDictCursor

from .config import Settings


logger = logging.getLogger(__name__)


class DatabaseService:
    """Lightweight Postgres access layer for users, projects, memberships, and ontologies registry."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=settings.postgres_pool_min_connections,
            maxconn=settings.postgres_pool_max_connections,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_database,
            user=settings.postgres_user,
            password=settings.postgres_password,
            # Add keepalive to prevent stale connections
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5,
        )
        self._connections_in_use = {}  # Track connections currently checked out
        logger.info(f"Database connection pool initialized: min={settings.postgres_pool_min_connections}, max={settings.postgres_pool_max_connections}")

    def _conn(self):
        try:
            conn = self.pool.getconn()
            conn_id = id(conn)
            current_time = time.time()
            
            # Track connection checkout time
            self._connections_in_use[conn_id] = current_time

            # Validate connection is alive - test with a simple query
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                logger.warning(f"Dead connection detected, recreating: {e}")
                # Close the dead connection
                try:
                    conn.close()
                except Exception:
                    pass
                # Remove from in-use tracking
                if conn_id in self._connections_in_use:
                    del self._connections_in_use[conn_id]
                # Get a new connection
                conn = self.pool.getconn()
                conn_id = id(conn)
                self._connections_in_use[conn_id] = current_time

            return conn
        except psycopg2.pool.PoolError as e:
            logger.error(f"Failed to get database connection: {e}")
            logger.error(f"Pool status: {self.get_pool_status()}")
            raise

    def _return(self, conn):
        try:
            conn_id = id(conn)
            current_time = time.time()
            
            # Track whether this connection was in our tracking dict
            was_tracked = conn_id in self._connections_in_use
            checkout_time = None
            
            # Remove from in-use tracking if present
            if was_tracked:
                checkout_time = self._connections_in_use[conn_id]
                del self._connections_in_use[conn_id]
                logger.debug(f"Returning tracked connection (age: {current_time - checkout_time:.1f}s)")
            else:
                logger.warning("Returning untracked connection - potential leak source")
            
            # Check if connection should be recycled (>30 minutes old)
            should_recycle = checkout_time and (current_time - checkout_time > 1800)
            
            # Validate and return connection
            try:
                if conn is None:
                    logger.error("Attempted to return None connection")
                    return
                    
                if conn.closed:
                    logger.warning("Attempted to return already closed connection")
                    return
                
                # Rollback any uncommitted transactions
                try:
                    conn.rollback()
                except Exception as e:
                    logger.warning(f"Error rolling back transaction: {e}")
                    should_recycle = True
                
                # Either recycle or return the connection
                if should_recycle:
                    logger.info(f"Recycling connection (age: {current_time - checkout_time:.1f}s if tracked)")
                    self.pool.putconn(conn, close=True)
                else:
                    self.pool.putconn(conn)
                    
            except Exception as e:
                logger.error(f"Error returning connection to pool: {e}")
                # Try to force close the connection
                try:
                    self.pool.putconn(conn, close=True)
                except Exception as close_error:
                    logger.error(f"Failed to force close connection: {close_error}")
                    
        except Exception as e:
            logger.error(f"Critical error in _return: {e}")

    @contextmanager
    def get_connection(self):
        """Context manager for database connections that ensures cleanup."""
        conn = None
        try:
            conn = self._conn()
            yield conn
        finally:
            if conn:
                self._return(conn)

    def get_pool_status(self) -> Dict[str, Any]:
        """Get current connection pool status for monitoring."""
        try:
            current_time = time.time()
            in_use_count = len(self._connections_in_use)
            
            # Calculate oldest in-use connection age
            oldest_age = 0
            if self._connections_in_use:
                oldest_checkout = min(self._connections_in_use.values())
                oldest_age = current_time - oldest_checkout
            
            # Detect leaked connections (>10 minutes in use)
            leaked_count = sum(1 for checkout_time in self._connections_in_use.values() 
                             if current_time - checkout_time > 600)  # 10 minutes
            
            return {
                "minconn": self.pool.minconn,
                "maxconn": self.pool.maxconn,
                "closed": self.pool.closed,
                "available_connections": len(self.pool._pool),
                "active_connections": self.pool.maxconn - len(self.pool._pool),
                "tracked_in_use": in_use_count,
                "oldest_in_use_age": round(oldest_age, 1),
                "has_leaked_connections": leaked_count > 0,
                "leaked_connections": leaked_count
            }
        except Exception as e:
            return {"error": str(e)}

    def prune_old_connections(self):
        """Prune connections that have been in use for too long."""
        current_time = time.time()
        lifetime_threshold = self.settings.postgres_pool_connection_lifetime

        # Get connections that are too old
        old_connections = [
            conn_id for conn_id, checkout_time in self._connections_in_use.items()
            if current_time - checkout_time > lifetime_threshold
        ]

        if old_connections:
            logger.warning(f"Found {len(old_connections)} connections in use >{lifetime_threshold}s - potential leaks")
            # Note: We can't directly close connections that are in use
            # This is logged for monitoring purposes
            for conn_id in old_connections:
                age = current_time - self._connections_in_use[conn_id]
                logger.warning(f"Connection {conn_id} in use for {age:.1f}s")

    # Users
    def get_or_create_user(
        self, username: str, display_name: Optional[str] = None, is_admin: bool = False
    ) -> Dict[str, Any]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT user_id, username, display_name, COALESCE(is_admin,false) AS is_admin FROM public.users WHERE username=%s",
                    (username,),
                )
                row = cur.fetchone()
                if row:
                    user_dict = dict(row)
                    # Validate user_id is a proper UUID
                    import uuid

                    try:
                        uuid.UUID(str(user_dict["user_id"]))
                    except ValueError as e:
                        raise ValueError(
                            f"Invalid user_id in database: {user_dict['user_id']!r}"
                        ) from e
                    return user_dict
                cur.execute(
                    "INSERT INTO public.users (username, display_name, is_admin) VALUES (%s, %s, %s) RETURNING user_id, username, display_name, COALESCE(is_admin,false) AS is_admin",
                    (username, display_name or username, is_admin),
                )
                row = cur.fetchone()
                conn.commit()
                user_dict = dict(row)
                # Validate user_id is a proper UUID
                import uuid

                try:
                    uuid.UUID(str(user_dict["user_id"]))
                except ValueError as e:
                    raise ValueError(f"Invalid user_id created: {user_dict['user_id']!r}") from e
                return user_dict
        finally:
            self._return(conn)

    # Projects
    def create_project(
        self,
        name: str,
        owner_user_id: str,
        description: Optional[str] = None,
        namespace_id: Optional[str] = None,
        domain: Optional[str] = None,
        project_level: Optional[int] = None,
        parent_project_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Validate parent-child relationship if parent specified
                if parent_project_id:
                    validation_result = self._validate_parent_child_relationship(
                        parent_project_id, project_level, cur
                    )
                    if not validation_result["valid"]:
                        raise ValueError(validation_result["error"])
                
                cur.execute(
                    """INSERT INTO public.projects 
                       (name, description, created_by, namespace_id, domain, project_level, parent_project_id, tenant_id) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s) 
                       RETURNING project_id, name, description, created_at, updated_at, created_by, 
                                 is_active, namespace_id, domain, project_level, parent_project_id, 
                                 publication_status, tenant_id""",
                    (name, description or None, owner_user_id, namespace_id, domain, 
                     project_level, parent_project_id, tenant_id),
                )
                proj = dict(cur.fetchone())
                # add membership as owner
                cur.execute(
                    "INSERT INTO public.project_members (project_id, user_id, role) VALUES (%s, %s, 'owner') ON CONFLICT DO NOTHING",
                    (proj["project_id"], owner_user_id),
                )
                conn.commit()
                return proj
        finally:
            self._return(conn)

    def _validate_parent_child_relationship(
        self, parent_project_id: str, child_level: Optional[int], cursor
    ) -> Dict[str, Any]:
        """Validate parent-child relationship rules."""
        try:
            # Get parent project info - cursor is already RealDictCursor from create_project
            cursor.execute(
                "SELECT project_level, domain FROM public.projects WHERE project_id = %s",
                (parent_project_id,),
            )
            result = cursor.fetchone()
            if not result:
                return {"valid": False, "error": f"Parent project {parent_project_id} not found"}
            
            # RealDictCursor returns dict-like objects
            parent_level = result["project_level"] 
            parent_domain = result["domain"]
            
            # Convert to int - parent_level should already be int from database
            if parent_level is not None and not isinstance(parent_level, int):
                parent_level = int(parent_level)
            
            # Rule: No upward relationships (parent level must be <= child level)
            if child_level is not None and parent_level is not None:
                if parent_level > child_level:
                    return {
                        "valid": False,
                        "error": f"Parent L{parent_level} cannot be parent of child L{child_level}. "
                                 "Knowledge flows downward only (L0→L1→L2→L3)."
                    }
            
            return {"valid": True}
        
        except Exception as e:
            return {"valid": False, "error": f"Validation error: {str(e)}"}

    def get_child_projects(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all direct child projects."""
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT p.project_id, p.name, p.domain, p.project_level, p.publication_status
                       FROM public.projects p
                       WHERE p.parent_project_id = %s
                       ORDER BY p.project_level, p.name""",
                    (project_id,),
                )
                return [dict(row) for row in cur.fetchall()]
        finally:
            self._return(conn)

    def get_parent_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get parent project if exists."""
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT p2.project_id, p2.name, p2.domain, p2.project_level, p2.publication_status
                       FROM public.projects p1
                       JOIN public.projects p2 ON p1.parent_project_id = p2.project_id
                       WHERE p1.project_id = %s""",
                    (project_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            self._return(conn)

    def get_project_lineage(self, project_id: str) -> List[Dict[str, Any]]:
        """Get complete parent lineage up to L0."""
        lineage = []
        current_id = project_id
        
        while True:
            parent = self.get_parent_project(current_id)
            if not parent:
                break
            lineage.append(parent)
            current_id = parent["project_id"]
            
            # Safety check to prevent infinite loops
            if len(lineage) > 10:
                logger.warning(f"Project lineage too deep for {project_id}, stopping at 10 levels")
                break
                
        return lineage

    def get_domain_projects(
        self, domain: str, publication_status: str = "published"
    ) -> List[Dict[str, Any]]:
        """Get all published projects in a domain."""
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT project_id, name, domain, project_level, publication_status, published_at
                       FROM public.projects
                       WHERE domain = %s AND publication_status = %s
                       ORDER BY project_level, name""",
                    (domain, publication_status),
                )
                return [dict(row) for row in cur.fetchall()]
        finally:
            self._return(conn)

    def list_projects_for_user(
        self, user_id: str, active: Optional[bool] = True
    ) -> List[Dict[str, Any]]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if active is None:
                    cur.execute(
                        """
                        SELECT p.project_id, p.name, p.description, p.created_at, p.updated_at, p.is_active, p.namespace_id, p.domain, pm.role
                        FROM public.projects p
                        JOIN public.project_members pm ON pm.project_id = p.project_id
                        WHERE pm.user_id = %s
                        ORDER BY p.created_at DESC
                        """,
                        (user_id,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT p.project_id, p.name, p.description, p.created_at, p.updated_at, p.is_active, p.namespace_id, p.domain, pm.role
                        FROM public.projects p
                        JOIN public.project_members pm ON pm.project_id = p.project_id
                        WHERE pm.user_id = %s AND p.is_active = %s
                        ORDER BY p.created_at DESC
                        """,
                        (user_id, active),
                    )
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._return(conn)

    def is_user_member(self, project_id: str, user_id: str) -> bool:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM public.project_members WHERE project_id=%s AND user_id=%s",
                    (project_id, user_id),
                )
                return cur.fetchone() is not None
        finally:
            self._return(conn)

    def add_member(self, project_id: str, user_id: str, role: str = "editor") -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO public.project_members (project_id, user_id, role) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                    (project_id, user_id, role),
                )
                conn.commit()
        finally:
            self._return(conn)

    def archive_project(self, project_id: str) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE public.projects SET is_active = FALSE WHERE project_id = %s",
                    (project_id,),
                )
                conn.commit()
        finally:
            self._return(conn)

    def restore_project(self, project_id: str) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE public.projects SET is_active = TRUE WHERE project_id = %s",
                    (project_id,),
                )
                conn.commit()
        finally:
            self._return(conn)

    def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        domain: Optional[str] = None,
        namespace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update project fields. Only updates provided fields."""
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Build dynamic update query
                update_fields = []
                update_values = []

                if name is not None:
                    update_fields.append("name = %s")
                    update_values.append(name)

                if description is not None:
                    update_fields.append("description = %s")
                    update_values.append(description)

                if domain is not None:
                    update_fields.append("domain = %s")
                    update_values.append(domain)

                if namespace_id is not None:
                    update_fields.append("namespace_id = %s")
                    update_values.append(namespace_id)

                if not update_fields:
                    raise ValueError("No fields to update")

                update_fields.append("updated_at = NOW()")
                update_values.append(project_id)

                cur.execute(
                    f"""
                    UPDATE public.projects
                    SET {', '.join(update_fields)}
                    WHERE project_id = %s
                    RETURNING project_id, name, description, created_at, updated_at, created_by, is_active, namespace_id, domain
                    """,
                    update_values,
                )
                row = cur.fetchone()
                if not row:
                    conn.rollback()
                    raise ValueError("Project not found")
                conn.commit()
                return dict(row)
        finally:
            self._return(conn)

    def rename_project(self, project_id: str, new_name: str) -> Dict[str, Any]:
        """Legacy method - use update_project instead."""
        return self.update_project(project_id, name=new_name)

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project details by ID."""
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT project_id, name, description, created_at, updated_at,
                           created_by, is_active, namespace_id, domain
                    FROM public.projects
                    WHERE project_id = %s AND is_active = true
                    """,
                    (project_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            self._return(conn)

    def get_project_comprehensive(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive project details including namespace, creator info, and URI."""
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT p.project_id, p.name, p.description, p.created_at, p.updated_at,
                           p.created_by, p.is_active, p.namespace_id, p.domain,
                           u.username as created_by_username,
                           n.path as namespace_path, n.name as namespace_name,
                           n.description as namespace_description, n.status as namespace_status
                    FROM public.projects p
                    LEFT JOIN public.users u ON p.created_by = u.user_id
                    LEFT JOIN public.namespace_registry n ON p.namespace_id = n.id
                    WHERE p.project_id = %s AND p.is_active = true
                    """,
                    (project_id,),
                )
                row = cur.fetchone()
                if row:
                    project_data = dict(row)

                    # Generate project URI using resource URI service
                    try:
                        from .resource_uri_service import ResourceURIService
                        from .config import Settings
                        settings = Settings()
                        uri_service = ResourceURIService(settings, self)
                        project_data['project_uri'] = uri_service.generate_project_uri(project_id)
                    except Exception as e:
                        project_data['project_uri'] = f"Error generating URI: {e}"

                    return project_data
                return None
        finally:
            self._return(conn)

    async def get_user_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all projects for a user, ordered by most recent activity."""
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT p.project_id, p.name, p.description, p.created_at, p.updated_at,
                           p.is_active, pm.role
                    FROM public.projects p
                    JOIN public.project_members pm ON p.project_id = pm.project_id
                    WHERE pm.user_id = %s AND p.is_active = true
                    ORDER BY p.updated_at DESC
                    """,
                    (user_id,),
                )
                rows = cur.fetchall()
                return [dict(row) for row in rows]
        finally:
            self._return(conn)

    # Ontologies registry
    def add_ontology(
        self,
        project_id: str,
        graph_iri: str,
        label: Optional[str],
        role: str = "base",
        is_reference: bool = False,
    ) -> Dict[str, Any]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "INSERT INTO public.ontologies_registry (project_id, graph_iri, label, role, is_reference) VALUES (%s, %s, %s, %s, %s) RETURNING id, project_id, graph_iri, label, role, is_reference, created_at, updated_at",
                    (project_id, graph_iri, label, role, is_reference),
                )
                row = cur.fetchone()
                conn.commit()
                return dict(row)
        finally:
            self._return(conn)

    def delete_ontology(self, graph_iri: str) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM public.ontologies_registry WHERE graph_iri=%s",
                    (graph_iri,),
                )
                conn.commit()
        finally:
            self._return(conn)

    def list_ontologies(self, project_id: str) -> List[Dict[str, Any]]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT graph_iri, label, role, is_reference FROM public.ontologies_registry WHERE project_id=%s ORDER BY created_at DESC",
                    (project_id,),
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._return(conn)

    def list_reference_ontologies(self) -> List[Dict[str, Any]]:
        """List all reference ontologies across all projects."""
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT o.graph_iri, o.label, o.role, p.name as project_name FROM public.ontologies_registry o JOIN public.projects p ON o.project_id = p.project_id WHERE o.is_reference = TRUE ORDER BY o.created_at DESC"
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._return(conn)

    def update_ontology_reference_status(self, graph_iri: str, is_reference: bool) -> bool:
        """Update the reference status of an ontology."""
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE public.ontologies_registry SET is_reference = %s, updated_at = NOW() WHERE graph_iri = %s RETURNING id",
                    (is_reference, graph_iri),
                )
                result = cur.fetchone()
                conn.commit()
                return result is not None
        finally:
            self._return(conn)
