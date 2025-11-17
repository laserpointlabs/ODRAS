"""
Tenant Management API for ODRAS Multi-Tenant Architecture
Clean, modern endpoints for tenant operations.
"""

import logging
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..services.enhanced_auth_service import (
    get_tenant_user, get_super_admin_user, get_tenant_service_dependency, TenantUser
)
from ..services.tenant_service import TenantService, TenantInfo
from ..services.unified_iri_service import UnifiedIRIService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["tenants"], prefix="/api/tenants")


class CreateTenantRequest(BaseModel):
    tenant_code: str
    tenant_name: str
    tenant_type: str = 'organization'
    custom_domain: str = None


class TenantResponse(BaseModel):
    tenant_id: str
    tenant_code: str
    tenant_name: str
    tenant_type: str
    base_iri: str
    status: str


class UserTenantResponse(BaseModel):
    tenant_id: str
    tenant_code: str
    tenant_name: str
    role: str


# =======================
# Tenant Management Endpoints
# =======================

@router.get("/", response_model=List[TenantResponse])
def list_tenants(
    tenant_service: TenantService = Depends(get_tenant_service_dependency),
    admin_user: TenantUser = Depends(get_super_admin_user)
):
    """List all tenants (super admin only)"""
    tenants = tenant_service.list_tenants()
    return [TenantResponse(**tenant.to_dict()) for tenant in tenants]


@router.post("/", response_model=TenantResponse)
def create_tenant(
    request: CreateTenantRequest,
    tenant_service: TenantService = Depends(get_tenant_service_dependency),
    admin_user: TenantUser = Depends(get_super_admin_user)
):
    """Create a new tenant (super admin only)"""
    try:
        tenant = tenant_service.create_tenant(
            tenant_code=request.tenant_code,
            tenant_name=request.tenant_name,
            tenant_type=request.tenant_type,
            custom_domain=request.custom_domain,
            created_by=admin_user.user_id
        )
        return TenantResponse(**tenant.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create tenant: {e}")
        raise HTTPException(status_code=500, detail="Failed to create tenant")


@router.get("/current", response_model=TenantResponse)
def get_current_tenant(
    tenant_user: TenantUser = Depends(get_tenant_user),
    tenant_service: TenantService = Depends(get_tenant_service_dependency)
):
    """Get current tenant information"""
    tenant = tenant_service.get_tenant(tenant_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Current tenant not found")
    
    return TenantResponse(**tenant.to_dict())


@router.get("/me/memberships", response_model=List[UserTenantResponse])
def get_my_tenant_memberships(
    tenant_user: TenantUser = Depends(get_tenant_user),
    tenant_service: TenantService = Depends(get_tenant_service_dependency)
):
    """Get current user's tenant memberships"""
    memberships = tenant_service.get_user_tenant_memberships(tenant_user.user_id)
    return [
        UserTenantResponse(
            tenant_id=membership["tenant_id"],
            tenant_code=membership["tenant_code"],
            tenant_name=membership["tenant_name"],
            role=membership["role"]
        )
        for membership in memberships
    ]


# =======================
# IRI Testing Endpoint
# =======================

@router.get("/iri-test/{project_id}")
def test_tenant_iris(
    project_id: str,
    tenant_user: TenantUser = Depends(get_tenant_user),
    tenant_service: TenantService = Depends(get_tenant_service_dependency)
):
    """Test IRI generation for the current tenant"""
    # Get tenant info
    tenant_info = tenant_service.get_tenant(tenant_user.tenant_id)
    if not tenant_info:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    # Create IRI service for current tenant
    iri_service = UnifiedIRIService(tenant_info.to_context())
    
    return {
        "tenant_context": {
            "tenant_id": tenant_user.tenant_id,
            "tenant_code": tenant_user.tenant_code
        },
        "test_iris": {
            "project": iri_service.generate_project_iri(project_id),
            "ontology": iri_service.generate_ontology_iri(project_id, "Requirements"),
            "knowledge": iri_service.generate_knowledge_iri(project_id, "asset-123"),
            "file": iri_service.generate_file_iri(project_id, "document-456"),
            "user": iri_service.generate_user_iri(tenant_user.username),
            "requirement": iri_service.generate_requirement_iri(project_id, "req-789")
        }
    }


# =======================
# 8-Character Ontology Element IRI Generation
# =======================

class MintElementIRIRequest(BaseModel):
    project_id: str
    ontology_name: str
    element_type: str = "element"  # class, objectProperty, dataProperty, individual


class ElementIRIResponse(BaseModel):
    code: str           # 8-character code like "A1B2-C3D4"
    iri: str            # Full IRI
    element_type: str   # Type of element
    project_id: str     # Project UUID
    ontology_name: str  # Ontology name


@router.post("/mint-element-iri", response_model=ElementIRIResponse)
def mint_ontology_element_iri(
    request: MintElementIRIRequest,
    tenant_user: TenantUser = Depends(get_tenant_user),
    tenant_service: TenantService = Depends(get_tenant_service_dependency)
):
    """
    Mint a new 8-character IRI for an ontology element.
    
    This endpoint generates human-memorable 8-character codes (like A1B2-C3D4)
    for ontology elements (classes, properties, individuals) instead of UUIDs.
    """
    # Get tenant info and create IRI service
    tenant_info = tenant_service.get_tenant(tenant_user.tenant_id)
    if not tenant_info:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    iri_service = UnifiedIRIService(tenant_info.to_context())
    
    # Mint the element IRI
    result = iri_service.mint_ontology_element_iri(
        project_id=request.project_id,
        ontology_name=request.ontology_name,
        element_type=request.element_type
    )
    
    return ElementIRIResponse(**result)


@router.get("/generate-8char-codes/{count}")
def generate_sample_8char_codes(
    count: int,
    tenant_user: TenantUser = Depends(get_tenant_user),
    tenant_service: TenantService = Depends(get_tenant_service_dependency)
):
    """
    Generate sample 8-character codes for testing/preview.
    Useful for showing users what the codes look like.
    """
    if count < 1 or count > 20:
        raise HTTPException(status_code=400, detail="Count must be between 1 and 20")
    
    # Get tenant info and create IRI service
    tenant_info = tenant_service.get_tenant(tenant_user.tenant_id)
    if not tenant_info:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    iri_service = UnifiedIRIService(tenant_info.to_context())
    
    # Generate sample codes
    codes = []
    for i in range(count):
        code = iri_service.generate_8char_code()
        codes.append({
            "code": code,
            "example_iri": f"{tenant_info.base_iri}/projects/sample-project/ontologies/example#{code}"
        })
    
    return {
        "tenant_code": tenant_user.tenant_code,
        "sample_codes": codes,
        "format_description": "8-character codes in format XXXX-XXXX using clear alphanumeric characters"
    }
