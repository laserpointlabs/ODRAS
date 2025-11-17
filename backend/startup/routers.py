"""
Router registration module.

Handles registration of all API routers with the FastAPI application.
"""

from fastapi import FastAPI

from ..api.files import router as files_router
from ..api.ontology import router as ontology_router
from ..api.ontology_registry import registry_router as ontology_registry_router
from ..api.workflows import router as workflows_router
from ..api.embedding_models import router as embedding_models_router
from ..api.knowledge import router as knowledge_router
from ..api.das import router as das_router
from ..api.das_training import router as das_training_router
from ..api.cqmt import router as cqmt_router
from ..api.thread_manager import router as thread_manager_router
from ..api.project_threads import router as project_threads_router
from ..api.requirements import router as requirements_router
from ..api.individuals import router as individuals_router
from ..api.configurations import router as configurations_router
from ..api.namespace_simple import (
    router as namespace_router,
    public_router as namespace_public_router,
)
from ..api.prefix_management import router as prefix_router
from ..api.domain_management import (
    router as domain_router,
    public_router as domain_public_router,
)
from ..api.session_intelligence import router as session_intelligence_router
from ..api.iri_resolution import router as iri_router
from ..api.federated_access import router as federated_router
from ..api.events import router as events_router
from ..api.users import router as users_router
from ..api.tenants import router as tenants_router
from ..api.core import router as core_router
from ..api.ui import router as ui_router
from ..api.system import router as system_router
from ..api.admin import router as admin_router
from ..api.project_relationships import router as project_relationships_router
from ..test_review_endpoint import router as test_router


def register_routers(app: FastAPI) -> None:
    """
    Register all API routers with the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # UI routes (must be registered early to avoid conflicts)
    app.include_router(ui_router)
    
    # Core routers (auth, health, sync, projects)
    app.include_router(core_router)
    
    # System and admin routers
    app.include_router(system_router)
    app.include_router(admin_router)
    
    # Test router
    app.include_router(test_router)
    
    # Ontology routers
    app.include_router(ontology_router)
    app.include_router(ontology_registry_router)
    
    # Core routers
    app.include_router(files_router)
    app.include_router(workflows_router)
    app.include_router(embedding_models_router)
    app.include_router(knowledge_router)
    app.include_router(requirements_router)  # REQUIREMENTS WORKBENCH API
    app.include_router(individuals_router)    # INDIVIDUAL TABLES API
    app.include_router(configurations_router)  # CONCEPTUALIZER WORKBENCH API
    app.include_router(cqmt_router)           # CQ/MT WORKBENCH API
    
    # DAS implementation (consolidated from DAS2)
    app.include_router(das_router)
    
    # DAS Training Workbench
    app.include_router(das_training_router)
    
    # Thread and project management
    app.include_router(thread_manager_router)  # THREAD MANAGER FOR DEBUGGING
    app.include_router(project_threads_router)  # PROJECT THREAD CREATION (UI ONLY)
    
    # IRI resolution
    app.include_router(iri_router)
    
    # Namespace and prefix management
    app.include_router(namespace_router)
    app.include_router(namespace_public_router)
    app.include_router(prefix_router)
    app.include_router(domain_router)
    app.include_router(domain_public_router)
    
    # Session and events
    app.include_router(session_intelligence_router)
    app.include_router(events_router)
    
    # Federated access
    app.include_router(federated_router)
    
    # User management
    app.include_router(users_router)
    
    # Tenant management
    app.include_router(tenants_router)
    
    # Project lattice endpoints
    app.include_router(project_relationships_router, tags=["project-relationships"])
