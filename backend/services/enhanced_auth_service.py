"""
Enhanced Authentication Service for ODRAS Multi-Tenant Architecture
Simplified tenant-aware authentication using existing auth system.
"""

import logging
from typing import Dict, Optional
from fastapi import HTTPException, Header, Depends

from .auth import get_user as original_get_user  # Import existing auth function
from .tenant_service import TenantService, TenantUser, get_tenant_service
from .config import Settings
from .db import DatabaseService

logger = logging.getLogger(__name__)


def get_tenant_user(authorization: Optional[str] = Header(None)) -> TenantUser:
    """
    Enhanced authentication dependency that includes tenant context.
    
    This replaces the existing get_user dependency and provides tenant-aware authentication.
    """
    # First authenticate using existing auth system
    user = original_get_user(authorization)  # This will raise HTTPException if auth fails
    
    # For now, create a TenantUser with system tenant
    # This maintains compatibility while we build out full tenant support
    return TenantUser(
        user_id=user["user_id"],
        username=user["username"],
        tenant_id="00000000-0000-0000-0000-000000000000",  # System tenant for now
        tenant_code="system",
        tenant_role="member",
        is_admin=user.get("is_admin", False),
        is_super_admin=user.get("is_admin", False)  # For now, admin = super_admin
    )


def get_tenant_admin_user(tenant_user: TenantUser = Depends(get_tenant_user)) -> TenantUser:
    """Enhanced dependency for tenant admin users."""
    if not (tenant_user.tenant_role == 'admin' or tenant_user.is_super_admin):
        raise HTTPException(
            status_code=403, 
            detail=f"Tenant admin privileges required. Current role: {tenant_user.tenant_role}"
        )
    
    return tenant_user


def get_super_admin_user(tenant_user: TenantUser = Depends(get_tenant_user)) -> TenantUser:
    """Enhanced dependency for super admin users."""
    if not tenant_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Super admin privileges required")
    
    return tenant_user


def get_tenant_service_dependency() -> TenantService:
    """Simplified tenant service dependency"""
    settings = Settings()
    db_service = DatabaseService(settings)
    return get_tenant_service(db_service, settings)
