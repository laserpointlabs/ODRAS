"""
Tenant Service for ODRAS Multi-Tenant Architecture
Clean, modern tenant management without legacy complexity.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone

from .config import Settings
from .db import DatabaseService
from .unified_iri_service import TenantContext

logger = logging.getLogger(__name__)


class TenantUser:
    """Enhanced user context with tenant information"""
    
    def __init__(self, user_id: str, username: str, tenant_id: str, tenant_code: str, 
                 tenant_role: str, is_admin: bool = False, is_super_admin: bool = False):
        self.user_id = user_id
        self.username = username
        self.tenant_id = tenant_id
        self.tenant_code = tenant_code
        self.tenant_role = tenant_role  # admin, member, viewer
        self.is_admin = is_admin
        self.is_super_admin = is_super_admin

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "tenant_id": self.tenant_id,
            "tenant_code": self.tenant_code,
            "tenant_role": self.tenant_role,
            "is_admin": self.is_admin,
            "is_super_admin": self.is_super_admin
        }


class TenantInfo:
    """Tenant information"""
    
    def __init__(self, tenant_id: str, tenant_code: str, tenant_name: str, tenant_type: str,
                 base_iri: str, status: str = 'active'):
        self.tenant_id = tenant_id
        self.tenant_code = tenant_code
        self.tenant_name = tenant_name
        self.tenant_type = tenant_type
        self.base_iri = base_iri
        self.status = status

    def to_context(self) -> TenantContext:
        """Convert to TenantContext for IRI service"""
        return TenantContext(self.tenant_id, self.tenant_code, self.tenant_name, self.base_iri)

    def to_dict(self) -> Dict:
        """Convert to dictionary for API responses"""
        return {
            "tenant_id": self.tenant_id,
            "tenant_code": self.tenant_code,
            "tenant_name": self.tenant_name,
            "tenant_type": self.tenant_type,
            "base_iri": self.base_iri,
            "status": self.status
        }


class TenantService:
    """
    Clean tenant management service for ODRAS multi-tenant architecture.
    
    Handles tenant creation, user membership, and tenant context resolution.
    """

    def __init__(self, db_service: DatabaseService, settings: Settings):
        self.db_service = db_service
        self.settings = settings
        self.system_tenant_id = "00000000-0000-0000-0000-000000000000"

    # =======================
    # Tenant Management
    # =======================

    def create_tenant(self, tenant_code: str, tenant_name: str, tenant_type: str = 'organization',
                     custom_domain: Optional[str] = None, created_by: Optional[str] = None) -> TenantInfo:
        """Create a new tenant."""
        # Validate tenant code format
        self._validate_tenant_code(tenant_code)
        
        # Generate base IRI
        base_iri = self._generate_tenant_base_iri(tenant_code, custom_domain)
        
        # Create tenant in database
        import uuid
        tenant_id = str(uuid.uuid4())
        
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO public.tenants (
                        tenant_id, tenant_code, tenant_name, tenant_type,
                        base_iri, custom_domain, created_by, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (tenant_id, tenant_code, tenant_name, tenant_type,
                      base_iri, custom_domain, created_by, 'active'))
                
                conn.commit()
                
                logger.info(f"Created tenant: {tenant_code} ({tenant_id})")
                
                return TenantInfo(
                    tenant_id=tenant_id,
                    tenant_code=tenant_code,
                    tenant_name=tenant_name,
                    tenant_type=tenant_type,
                    base_iri=base_iri,
                    status='active'
                )
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create tenant {tenant_code}: {e}")
            raise
        finally:
            self.db_service._return(conn)

    def get_tenant(self, tenant_id: str) -> Optional[TenantInfo]:
        """Get tenant information by ID."""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT tenant_id, tenant_code, tenant_name, tenant_type, base_iri, status
                    FROM public.tenants
                    WHERE tenant_id = %s
                """, (tenant_id,))
                
                result = cur.fetchone()
                if result:
                    tenant_id, tenant_code, tenant_name, tenant_type, base_iri, status = result
                    return TenantInfo(
                        tenant_id=tenant_id,
                        tenant_code=tenant_code,
                        tenant_name=tenant_name,
                        tenant_type=tenant_type,
                        base_iri=base_iri,
                        status=status
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get tenant {tenant_id}: {e}")
            return None
        finally:
            self.db_service._return(conn)

    def get_tenant_by_code(self, tenant_code: str) -> Optional[TenantInfo]:
        """Get tenant information by tenant code."""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT tenant_id, tenant_code, tenant_name, tenant_type, base_iri, status
                    FROM public.tenants
                    WHERE tenant_code = %s
                """, (tenant_code,))
                
                result = cur.fetchone()
                if result:
                    tenant_id, tenant_code, tenant_name, tenant_type, base_iri, status = result
                    return TenantInfo(
                        tenant_id=tenant_id,
                        tenant_code=tenant_code,
                        tenant_name=tenant_name,
                        tenant_type=tenant_type,
                        base_iri=base_iri,
                        status=status
                    )
                return None
                
        except Exception as e:
            logger.error(f"Failed to get tenant by code {tenant_code}: {e}")
            return None
        finally:
            self.db_service._return(conn)

    def list_tenants(self) -> List[TenantInfo]:
        """List all active tenants."""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT tenant_id, tenant_code, tenant_name, tenant_type, base_iri, status
                    FROM public.tenants
                    WHERE status = 'active'
                    ORDER BY tenant_name
                """)
                
                results = cur.fetchall()
                tenants = []
                for result in results:
                    tenant_id, tenant_code, tenant_name, tenant_type, base_iri, status = result
                    tenants.append(TenantInfo(
                        tenant_id=tenant_id,
                        tenant_code=tenant_code,
                        tenant_name=tenant_name,
                        tenant_type=tenant_type,
                        base_iri=base_iri,
                        status=status
                    ))
                
                return tenants
                
        except Exception as e:
            logger.error(f"Failed to list tenants: {e}")
            return []
        finally:
            self.db_service._return(conn)

    # =======================
    # Tenant User Management
    # =======================

    def add_user_to_tenant(self, tenant_id: str, user_id: str, role: str = 'member') -> bool:
        """Add a user to a tenant with specified role."""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO public.tenant_members (tenant_id, user_id, role)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (tenant_id, user_id) 
                    DO UPDATE SET role = EXCLUDED.role
                """, (tenant_id, user_id, role))
                
                conn.commit()
                logger.info(f"Added user {user_id} to tenant {tenant_id} with role {role}")
                return True
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to add user {user_id} to tenant {tenant_id}: {e}")
            return False
        finally:
            self.db_service._return(conn)

    def get_user_tenant_memberships(self, user_id: str) -> List[Dict]:
        """Get all tenant memberships for a user."""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT t.tenant_id, t.tenant_code, t.tenant_name, t.tenant_type,
                           t.base_iri, t.status, tm.role
                    FROM public.tenants t
                    JOIN public.tenant_members tm ON t.tenant_id = tm.tenant_id
                    WHERE tm.user_id = %s AND t.status = 'active'
                    ORDER BY t.tenant_name
                """, (user_id,))
                
                results = cur.fetchall()
                memberships = []
                for result in results:
                    tenant_id, tenant_code, tenant_name, tenant_type, base_iri, status, role = result
                    memberships.append({
                        "tenant_id": tenant_id,
                        "tenant_code": tenant_code,
                        "tenant_name": tenant_name,
                        "tenant_type": tenant_type,
                        "base_iri": base_iri,
                        "status": status,
                        "role": role
                    })
                
                return memberships
                
        except Exception as e:
            logger.error(f"Failed to get tenant memberships for user {user_id}: {e}")
            return []
        finally:
            self.db_service._return(conn)

    def get_user_primary_tenant(self, user_id: str) -> Optional[TenantInfo]:
        """Get user's primary tenant (first one they joined or system tenant)."""
        memberships = self.get_user_tenant_memberships(user_id)
        if memberships:
            # Return first membership (ordered by tenant name)
            first_membership = memberships[0]
            return TenantInfo(
                tenant_id=first_membership["tenant_id"],
                tenant_code=first_membership["tenant_code"],
                tenant_name=first_membership["tenant_name"],
                tenant_type=first_membership["tenant_type"],
                base_iri=first_membership["base_iri"],
                status=first_membership["status"]
            )
        
        # Fallback to system tenant
        return self.get_tenant(self.system_tenant_id)

    # =======================
    # Tenant Context Resolution
    # =======================

    def get_tenant_user_context(self, user_id: str, tenant_id: Optional[str] = None) -> Optional[TenantUser]:
        """
        Get complete tenant user context for authentication.
        """
        # Get user basic info
        user_info = self._get_user_info(user_id)
        if not user_info:
            return None
        
        # Get tenant info
        if tenant_id:
            tenant_info = self.get_tenant(tenant_id)
            tenant_role = self._get_user_tenant_role(user_id, tenant_id)
        else:
            tenant_info = self.get_user_primary_tenant(user_id)
            tenant_role = 'member' if tenant_info else None
        
        if not tenant_info or not tenant_role:
            return None
        
        return TenantUser(
            user_id=user_id,
            username=user_info["username"],
            tenant_id=tenant_info.tenant_id,
            tenant_code=tenant_info.tenant_code,
            tenant_role=tenant_role,
            is_admin=user_info.get("is_admin", False),
            is_super_admin=user_info.get("is_admin", False)  # For now, admin = super_admin
        )

    def switch_user_tenant_context(self, user_id: str, target_tenant_id: str) -> Optional[TenantUser]:
        """Switch user's active tenant context."""
        # Verify user has access to target tenant
        tenant_role = self._get_user_tenant_role(user_id, target_tenant_id)
        if not tenant_role:
            logger.warning(f"User {user_id} attempted to switch to unauthorized tenant {target_tenant_id}")
            return None
        
        return self.get_tenant_user_context(user_id, target_tenant_id)

    def validate_tenant_access(self, user_id: str, tenant_id: str) -> bool:
        """Validate that a user has access to a specific tenant."""
        role = self._get_user_tenant_role(user_id, tenant_id)
        return role is not None

    # =======================
    # Private Helper Methods
    # =======================

    def _validate_tenant_code(self, tenant_code: str):
        """Validate tenant code format."""
        import re
        
        if not tenant_code:
            raise ValueError("Tenant code cannot be empty")
        
        if len(tenant_code) < 3 or len(tenant_code) > 50:
            raise ValueError("Tenant code must be 3-50 characters long")
        
        if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$', tenant_code):
            raise ValueError("Tenant code must be kebab-case (lowercase, hyphens only)")
        
        # Check for reserved codes
        reserved_codes = ["system", "admin", "api", "www", "mail", "ftp"]
        if tenant_code in reserved_codes:
            raise ValueError(f"Tenant code '{tenant_code}' is reserved")

    def _generate_tenant_base_iri(self, tenant_code: str, custom_domain: Optional[str] = None) -> str:
        """Generate base IRI for tenant."""
        if custom_domain:
            return f"https://{custom_domain}"
        else:
            # Use installation base URI with tenant path
            base = self.settings.installation_base_uri.rstrip("/")
            return f"{base}/{tenant_code}"

    def _get_user_info(self, user_id: str) -> Optional[Dict]:
        """Get basic user information."""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT user_id, username, is_admin
                    FROM public.users
                    WHERE user_id = %s
                """, (user_id,))
                
                result = cur.fetchone()
                if result:
                    user_id, username, is_admin = result
                    return {
                        "user_id": user_id,
                        "username": username,
                        "is_admin": is_admin
                    }
                return None
                
        except Exception as e:
            logger.error(f"Failed to get user info for {user_id}: {e}")
            return None
        finally:
            self.db_service._return(conn)

    def _get_user_tenant_role(self, user_id: str, tenant_id: str) -> Optional[str]:
        """Get user's role in a specific tenant."""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT role FROM public.tenant_members
                    WHERE user_id = %s AND tenant_id = %s
                """, (user_id, tenant_id))
                
                result = cur.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            logger.error(f"Failed to get user role for {user_id} in tenant {tenant_id}: {e}")
            return None
        finally:
            self.db_service._return(conn)


class TenantAwareDatabaseService:
    """Database service wrapper that automatically adds tenant filtering to queries."""
    
    def __init__(self, db_service: DatabaseService, tenant_id: str):
        self.db_service = db_service
        self.tenant_id = tenant_id
    
    def get_projects(self) -> List[Dict]:
        """Get projects filtered by tenant."""
        conn = self.db_service._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT project_id, name, description, domain, status, created_at
                    FROM public.projects
                    WHERE tenant_id = %s AND is_active = true
                    ORDER BY name
                """, (self.tenant_id,))
                
                results = cur.fetchall()
                projects = []
                for result in results:
                    project_id, name, description, domain, status, created_at = result
                    projects.append({
                        "project_id": project_id,
                        "name": name,
                        "description": description,
                        "domain": domain,
                        "status": status,
                        "created_at": created_at.isoformat() if created_at else None
                    })
                
                return projects
                
        except Exception as e:
            logger.error(f"Failed to get projects for tenant {self.tenant_id}: {e}")
            return []
        finally:
            self.db_service._return(conn)


# =======================
# Factory Functions
# =======================

def get_tenant_service(db_service: DatabaseService, settings: Settings) -> TenantService:
    """Factory function to create TenantService instance."""
    return TenantService(db_service, settings)
