import logging
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
            minconn=1,
            maxconn=10,
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_database,
            user=settings.postgres_user,
            password=settings.postgres_password,
        )

    def _conn(self):
        return self.pool.getconn()

    def _return(self, conn):
        try:
            self.pool.putconn(conn)
        except Exception:
            pass

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
    ) -> Dict[str, Any]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "INSERT INTO public.projects (name, description, created_by, namespace_id, domain) VALUES (%s, %s, %s, %s, %s) RETURNING project_id, name, description, created_at, updated_at, created_by, is_active, namespace_id, domain",
                    (name, description or None, owner_user_id, namespace_id, domain),
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

