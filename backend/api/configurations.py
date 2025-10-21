"""
Configuration API endpoints for the Conceptualizer Workbench
Handles DAS-generated system architecture configurations
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Dict, Any, Optional
import json
import uuid
import logging
from datetime import datetime, timezone
from pydantic import BaseModel

from backend.services.auth import get_user as get_current_user
from backend.services.configuration_manager import ConfigurationManager, get_db_connection
from backend.services.graph_builder import GraphBuilder
from backend.services.das_integration import DASIntegration
from backend.services.das2_core_engine import DAS2CoreEngine
from backend.api.das2 import get_das2_engine
import psycopg2.extras

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/configurations", tags=["configurations"])

# =====================================
# PYDANTIC MODELS
# =====================================

class DASMetadata(BaseModel):
    generated_at: str
    das_version: str
    confidence: float
    rationale: Optional[str] = None

class NodeProperties(BaseModel):
    name: str
    description: Optional[str] = None
    type: Optional[str] = None

class ConfigurationNode(BaseModel):
    id: str
    type: str
    label: str
    properties: NodeProperties
    das_metadata: Optional[DASMetadata] = None

class ConfigurationEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    label: str
    multiplicity: Optional[str] = None

class ConfigurationCluster(BaseModel):
    id: str
    label: str
    node_ids: List[str]

class GraphData(BaseModel):
    nodes: List[ConfigurationNode]
    edges: List[ConfigurationEdge]
    clusters: List[ConfigurationCluster]

class ConfigurationCreate(BaseModel):
    name: str
    ontology_graph: str
    source_requirement: Optional[str] = None
    structure: Dict[str, Any]
    das_metadata: Optional[DASMetadata] = None

class ConfigurationUpdate(BaseModel):
    name: Optional[str] = None
    structure: Optional[Dict[str, Any]] = None

class BatchGenerateRequest(BaseModel):
    requirement_ids: Optional[List[str]] = None
    das_options: Dict[str, Any] = {}
    filters: Dict[str, Any] = {}

class PaginationFilters(BaseModel):
    source: Optional[str] = None
    date_range: Optional[str] = None
    requirement_prefix: Optional[str] = None
    confidence_min: Optional[float] = None

# =====================================
# CONFIGURATION CRUD ENDPOINTS
# =====================================

@router.get("/{project_id}/ontologies/{ontology_graph}/configurations")
async def list_configurations(
    project_id: str,
    ontology_graph: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    source: Optional[str] = None,
    date_range: Optional[str] = None,
    requirement_prefix: Optional[str] = None,
    confidence_min: Optional[float] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    List root individuals for conceptualization (ontology-scoped)
    """
    try:
        logger.info(f"🔍 Listing root individuals for ontology {ontology_graph}")
        
        config_manager = ConfigurationManager()
        
        # Get root individuals from the selected ontology
        result = await config_manager.list_root_individuals(
            project_id=project_id,
            ontology_graph=ontology_graph,
            page=page,
            page_size=page_size
        )
        
        return {
            "configurations": result["configurations"],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": result["total"],
                "total_pages": (result["total"] + page_size - 1) // page_size,
                "filters": {
                    "source": source,
                    "date_range": date_range,
                    "requirement_prefix": requirement_prefix,
                    "confidence_min": confidence_min
                }
            },
            "root_classes": result.get("root_classes", [])
        }
        
    except Exception as e:
        logger.error(f"❌ Error listing configurations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list configurations: {str(e)}"
        )

@router.post("/{project_id}/ontologies/{ontology_graph}/configurations")
async def create_configuration(
    project_id: str,
    ontology_graph: str,
    config: ConfigurationCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new configuration (DAS-friendly endpoint)
    """
    try:
        logger.info(f"🔍 Creating configuration for project {project_id}")
        
        config_manager = ConfigurationManager()
        
        config_id = await config_manager.create_configuration(
            project_id=project_id,
            config_data=config.dict(),
            user_id=current_user["user_id"]
        )
        
        logger.info(f"✅ Configuration created: {config_id}")
        return {"success": True, "config_id": config_id}
        
    except Exception as e:
        logger.error(f"❌ Error creating configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create configuration: {str(e)}"
        )

@router.get("/{project_id}/ontologies/{ontology_graph}/configurations/{config_id}")
async def get_configuration(
    project_id: str,
    ontology_graph: str,
    config_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get specific configuration details
    """
    try:
        logger.info(f"🔍 Getting configuration {config_id}")
        
        config_manager = ConfigurationManager()
        config = await config_manager.get_configuration(project_id, config_id)
        
        if not config:
            raise HTTPException(404, "Configuration not found")
        
        return config
        
    except Exception as e:
        logger.error(f"❌ Error getting configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get configuration: {str(e)}"
        )

@router.get("/{project_id}/ontologies/{ontology_graph}/configurations/{config_id}/graph")
async def get_configuration_graph(
    project_id: str,
    ontology_graph: str,
    config_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get configuration in graph format for visualization
    """
    try:
        logger.info(f"🔍 Getting graph data for configuration {config_id}")
        
        config_manager = ConfigurationManager()
        config = await config_manager.get_configuration(project_id, config_id)
        
        if not config:
            raise HTTPException(404, "Configuration not found")
        
        # Convert to graph format
        graph_builder = GraphBuilder()
        graph_data = await graph_builder.build_graph_from_configuration(config)
        
        # Add legend data for dynamic styling
        legend_data = graph_builder.get_legend_data(graph_data)
        graph_data["legend"] = legend_data
        
        return graph_data
        
    except Exception as e:
        logger.error(f"❌ Error getting configuration graph: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get configuration graph: {str(e)}"
        )

@router.put("/{project_id}/ontologies/{ontology_graph}/configurations/{config_id}")
async def update_configuration(
    project_id: str,
    ontology_graph: str,
    config_id: str,
    update_data: ConfigurationUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update existing configuration
    """
    try:
        logger.info(f"🔍 Updating configuration {config_id}")
        
        config_manager = ConfigurationManager()
        success = await config_manager.update_configuration(
            project_id=project_id,
            config_id=config_id,
            update_data=update_data.dict(exclude_none=True),
            user_id=current_user["user_id"]
        )
        
        if not success:
            raise HTTPException(404, "Configuration not found")
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"❌ Error updating configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}"
        )

@router.delete("/{project_id}/ontologies/{ontology_graph}/configurations/{config_id}")
async def delete_configuration(
    project_id: str,
    ontology_graph: str,
    config_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete configuration
    """
    try:
        logger.info(f"🔍 Deleting configuration {config_id}")
        
        config_manager = ConfigurationManager()
        success = await config_manager.delete_configuration(project_id, config_id)
        
        if not success:
            raise HTTPException(404, "Configuration not found")
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"❌ Error deleting configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete configuration: {str(e)}"
        )

# =====================================
# OVERVIEW AND AGGREGATION ENDPOINTS
# =====================================

@router.get("/{project_id}/ontologies/{ontology_graph}/configurations/overview-graph")
async def get_overview_graph(
    project_id: str,
    ontology_graph: str,
    config_ids: Optional[List[str]] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Get aggregated view of multiple configurations
    """
    try:
        logger.info(f"🔍 Getting overview graph for project {project_id}")
        
        config_manager = ConfigurationManager()
        graph_builder = GraphBuilder()
        
        # Get root individuals for overview
        result = await config_manager.list_root_individuals(
            project_id=project_id,
            ontology_graph=ontology_graph,
            page=1,
            page_size=1000  # Large limit for overview
        )
        configs = result["configurations"]
        
        # Build aggregated graph
        graph_data = await graph_builder.build_overview_graph(configs)
        
        return graph_data
        
    except Exception as e:
        logger.error(f"❌ Error getting overview graph: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get overview graph: {str(e)}"
        )

# =====================================
# DAS INTEGRATION ENDPOINTS
# =====================================

@router.post("/{project_id}/ontologies/{ontology_graph}/configurations/batch-generate")
async def batch_generate_configurations(
    project_id: str,
    ontology_graph: str,
    request: BatchGenerateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Trigger DAS batch generation process
    """
    try:
        logger.info(f"🔍 Starting batch generation for project {project_id}")
        
        das_integration = DASIntegration()
        config_manager = ConfigurationManager()
        
        # Start batch generation process
        job_id = await das_integration.start_batch_generation(
            project_id=project_id,
            requirement_ids=request.requirement_ids,
            das_options=request.das_options,
            filters=request.filters,
            user_id=current_user["user_id"]
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "status": "started",
            "message": "Batch generation started"
        }
        
    except Exception as e:
        logger.error(f"❌ Error starting batch generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start batch generation: {str(e)}"
        )

@router.get("/{project_id}/ontologies/{ontology_graph}/configurations/batch-generate/{job_id}/status")
async def get_batch_generation_status(
    project_id: str,
    ontology_graph: str,
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get status of batch generation job
    """
    try:
        logger.info(f"🔍 Getting batch generation status for job {job_id}")
        
        das_integration = DASIntegration()
        status = await das_integration.get_job_status(job_id)
        
        return status
        
    except Exception as e:
        logger.error(f"❌ Error getting batch generation status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get batch generation status: {str(e)}"
        )

# =====================================
# VALIDATION ENDPOINTS
# =====================================

@router.post("/{project_id}/ontologies/{ontology_graph}/configurations/validate")
async def validate_configuration(
    project_id: str,
    ontology_graph: str,
    config: ConfigurationCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Validate configuration structure against ontology
    """
    try:
        logger.info(f"🔍 Validating configuration structure")
        
        config_manager = ConfigurationManager()
        validation_result = await config_manager.validate_configuration(
            project_id=project_id,
            config_data=config.dict()
        )
        
        return validation_result
        
    except Exception as e:
        logger.error(f"❌ Error validating configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate configuration: {str(e)}"
        )

# =====================================
# TESTING ENDPOINTS (DEV ONLY)
# =====================================

@router.post("/{project_id}/ontologies/{ontology_graph}/configurations/create-sample")
async def create_sample_configuration_DISABLED(
    project_id: str,
    ontology_graph: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a sample configuration for testing (development only)
    """
    try:
        logger.info(f"🔍 Creating sample configuration for project {project_id}")
        
        # Create sample configuration for the specified ontology
        sample_config = ConfigurationCreate(
            name=f"Sample Configuration for {ontology_graph.split('/')[-1]}",
            ontology_graph=ontology_graph,
            source_requirement="sample-req-001",
            structure={
                "class": "Requirement",
                "instanceId": "req-001",
                "properties": {
                    "name": "System shall process user data efficiently",
                    "description": "Sample requirement for testing"
                },
                "relationships": [
                    {
                        "property": "has_constraint",
                        "multiplicity": "0..*",
                        "targets": [
                            {
                                "class": "Constraint",
                                "instanceId": "const-001",
                                "properties": {
                                    "name": "Response time < 2 seconds",
                                    "type": "performance"
                                }
                            }
                        ]
                    },
                    {
                        "property": "specifies",
                        "multiplicity": "1..*",
                        "targets": [
                            {
                                "class": "Component",
                                "instanceId": "comp-001",
                                "properties": {
                                    "name": "Data Processing Engine",
                                    "dasRationale": "Primary processing component for user data"
                                },
                                "relationships": [
                                    {
                                        "property": "presents",
                                        "multiplicity": "1..*",
                                        "targets": [
                                            {
                                                "class": "Interface",
                                                "instanceId": "intf-001",
                                                "properties": {
                                                    "name": "REST API"
                                                }
                                            }
                                        ]
                                    },
                                    {
                                        "property": "performs",
                                        "multiplicity": "1..0",
                                        "targets": [
                                            {
                                                "class": "Process",
                                                "instanceId": "proc-001",
                                                "properties": {
                                                    "name": "Data Validation"
                                                },
                                                "relationships": [
                                                    {
                                                        "property": "realizes",
                                                        "multiplicity": "1..0",
                                                        "targets": [
                                                            {
                                                                "class": "Function",
                                                                "instanceId": "func-001",
                                                                "properties": {
                                                                    "name": "Validate Input Format"
                                                                },
                                                                "relationships": [
                                                                    {
                                                                        "property": "specifically_depends_upon",
                                                                        "multiplicity": "1..0",
                                                                        "targets": [
                                                                            {"componentRef": "comp-001"}
                                                                        ]
                                                                    }
                                                                ]
                                                            }
                                                        ]
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            das_metadata=DASMetadata(
                generated_at=datetime.now().isoformat(),
                das_version="2.0-test",
                confidence=0.85,
                rationale="Sample configuration for testing the Conceptualizer"
            )
        )
        
        config_manager = ConfigurationManager()
        
        config_id = await config_manager.create_configuration(
            project_id=project_id,
            config_data=sample_config.dict(),
            user_id=current_user["user_id"]
        )
        
        logger.info(f"✅ Sample configuration created: {config_id}")
        return {"success": True, "config_id": config_id, "message": "Sample configuration created for testing"}
        
    except Exception as e:
        logger.error(f"❌ Error creating sample configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create sample configuration: {str(e)}"
        )

# =====================================
# SYNC WITH INDIVIDUAL TABLES
# =====================================

@router.post("/{project_id}/ontologies/{ontology_graph}/configurations/{config_id}/sync-to-individuals")
async def sync_configuration_to_individuals(
    project_id: str,
    ontology_graph: str,
    config_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Sync configuration to individual tables (create/update individuals)
    """
    try:
        logger.info(f"🔍 Syncing configuration {config_id} to individual tables")
        
        config_manager = ConfigurationManager()
        sync_result = await config_manager.sync_configuration_to_individuals(
            project_id, config_id, current_user["user_id"]
        )
        
        return sync_result
        
    except Exception as e:
        logger.error(f"❌ Error syncing configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync configuration: {str(e)}"
        )

@router.get("/{project_id}/ontologies/{ontology_graph}/configurations/{config_id}/sync-status")
async def get_configuration_sync_status(
    project_id: str,
    ontology_graph: str,
    config_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get sync status between configuration and individual tables
    """
    try:
        logger.info(f"🔍 Getting sync status for configuration {config_id}")
        
        config_manager = ConfigurationManager()
        sync_status = await config_manager.get_sync_status(project_id, config_id)
        
        return sync_status
        
    except Exception as e:
        logger.error(f"❌ Error getting sync status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sync status: {str(e)}"
        )

# =====================================
# DEVELOPMENT/TESTING ENDPOINTS
# =====================================

@router.get("/{project_id}/ontologies/{ontology_name}/root-individuals")
async def get_root_individuals_by_name(
    project_id: str,
    ontology_name: str,  # e.g., "bseo-a", "base", etc.
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """
    Get root individuals for a specific ontology by name (development endpoint)
    """
    try:
        logger.info(f"🔍 Getting root individuals for ontology {ontology_name}")
        
        # Construct full ontology graph IRI based on project and name
        # This matches the pattern from ODRAS project structure
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Find ontology graph IRI by project and name pattern
            cursor.execute("""
                SELECT graph_iri, label 
                FROM ontologies_registry 
                WHERE project_id = %s 
                AND (LOWER(label) = %s OR graph_iri LIKE %s)
                LIMIT 1
            """, (project_id, ontology_name.lower(), f"%{ontology_name}%"))
            
            ontology_record = cursor.fetchone()
            
            if not ontology_record:
                return {
                    "configurations": [],
                    "total": 0,
                    "root_classes": [],
                    "message": f"Ontology '{ontology_name}' not found"
                }
            
            ontology_graph = ontology_record["graph_iri"]
            
            logger.info(f"🔍 Found ontology graph: {ontology_graph}")
        
        config_manager = ConfigurationManager()
        
        # Get root individuals from this ontology
        result = await config_manager.list_root_individuals(
            project_id=project_id,
            ontology_graph=ontology_graph,
            page=page,
            page_size=page_size
        )
        
        return {
            "configurations": result["configurations"],
            "total": result["total"],
            "root_classes": result["root_classes"],
            "ontology": {
                "graph_iri": ontology_graph,
                "label": ontology_record["label"],
                "name": ontology_name
            },
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_pages": (result["total"] + page_size - 1) // page_size
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting root individuals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get root individuals: {str(e)}"
        )

@router.get("/{project_id}/ontologies/{ontology_name}/individuals/{individual_id}/conceptualize")
async def conceptualize_individual(
    project_id: str,
    ontology_name: str,
    individual_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate conceptualization graph for a root individual (mock DAS implementation)
    """
    try:
        logger.info(f"🔍 Conceptualizing individual {individual_id} in {ontology_name}")
        
        # Get the individual from database
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute("""
                SELECT ii.*, itc.graph_iri, itc.ontology_label
                FROM individual_instances ii
                JOIN individual_tables_config itc ON ii.table_id = itc.table_id
                WHERE ii.instance_id = %s AND itc.project_id = %s
            """, (individual_id, project_id))
            
            individual = cursor.fetchone()
            
            if not individual:
                raise HTTPException(404, "Individual not found")
            
            # Parse properties
            props = individual["properties"] if isinstance(individual["properties"], dict) else json.loads(individual["properties"])
            
            # Mock DAS conceptualization - generate system architecture
            mock_config = {
                "class": "Requirement",
                "instanceId": individual["instance_name"],
                "properties": {
                    "name": props.get("displayName", individual["instance_name"]),
                    "text": props.get("Text", ""),
                    "id": props.get("ID", "")
                },
                "relationships": [
                    {
                        "property": "has_constraint",
                        "multiplicity": "0..*",
                        "targets": [
                            {
                                "class": "Constraint",
                                "instanceId": f"const-{individual['instance_name']}",
                                "properties": {
                                    "name": "Performance Constraint",
                                    "type": "operational",
                                    "dasRationale": f"Generated constraint for {props.get('displayName', 'requirement')}"
                                }
                            }
                        ]
                    },
                    {
                        "property": "specifies",
                        "multiplicity": "1..*", 
                        "targets": [
                            {
                                "class": "Component",
                                "instanceId": f"comp-{individual['instance_name']}",
                                "properties": {
                                    "name": f"Control System for {props.get('displayName', 'System')}",
                                    "dasRationale": f"Primary component to implement {props.get('displayName', 'requirement')}"
                                },
                                "relationships": [
                                    {
                                        "property": "presents",
                                        "multiplicity": "1..*",
                                        "targets": [
                                            {
                                                "class": "Interface",
                                                "instanceId": f"intf-{individual['instance_name']}",
                                                "properties": {
                                                    "name": "Control Interface",
                                                    "dasRationale": "Interface for component interaction"
                                                }
                                            }
                                        ]
                                    },
                                    {
                                        "property": "performs",
                                        "multiplicity": "1..0",
                                        "targets": [
                                            {
                                                "class": "Process",
                                                "instanceId": f"proc-{individual['instance_name']}",
                                                "properties": {
                                                    "name": f"Execute {props.get('displayName', 'Function')}",
                                                    "dasRationale": "Process to realize the requirement"
                                                },
                                                "relationships": [
                                                    {
                                                        "property": "realizes",
                                                        "multiplicity": "1..0",
                                                        "targets": [
                                                            {
                                                                "class": "Function",
                                                                "instanceId": f"func-{individual['instance_name']}",
                                                                "properties": {
                                                                    "name": f"{props.get('displayName', 'Core')} Function",
                                                                    "dasRationale": "Core function implementing the requirement"
                                                                },
                                                                "relationships": [
                                                                    {
                                                                        "property": "specifically_depends_upon",
                                                                        "multiplicity": "1..0",
                                                                        "targets": [
                                                                            {"componentRef": f"comp-{individual['instance_name']}"}
                                                                        ]
                                                                    }
                                                                ]
                                                            }
                                                        ]
                                                    }
                                                ]
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        
        # Build graph from mock configuration
        graph_builder = GraphBuilder()
        graph_data = await graph_builder.build_graph_from_configuration({
            "config_id": individual_id,
            "name": f"DAS Conceptualization: {props.get('displayName', individual['instance_name'])}",
            "structure": mock_config,
            "das_metadata": {
                "generated_at": datetime.now().isoformat(),
                "das_version": "2.0-mock", 
                "confidence": 0.75,  # Lower mock confidence to distinguish from real DAS
                "rationale": f"Mock DAS conceptualization for {props.get('displayName', 'requirement')}"
            }
        })
        
        # Add legend data
        legend_data = graph_builder.get_legend_data(graph_data)
        graph_data["legend"] = legend_data
        
        logger.info(f"✅ Generated mock conceptualization: {len(graph_data.get('nodes', []))} nodes")
        return graph_data
        
    except Exception as e:
        logger.error(f"❌ Error conceptualizing individual: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to conceptualize individual: {str(e)}"
        )

@router.post("/{project_id}/ontologies/{ontology_name}/individuals/{individual_id}/conceptualize-and-store")
async def conceptualize_and_store_individual(
    project_id: str,
    ontology_name: str,
    individual_id: str,
    request_data: Dict[str, Any] = {},
    current_user: dict = Depends(get_current_user),
    das_engine: DAS2CoreEngine = Depends(get_das2_engine)
):
    """
    Generate concepts with DAS and store as individuals in database
    """
    try:
        logger.info(f"🚀 DAS conceptualization and storage for {individual_id}")
        
        # Get the individual from database
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            cursor.execute("""
                SELECT ii.*, itc.graph_iri, itc.ontology_label, itc.ontology_structure
                FROM individual_instances ii
                JOIN individual_tables_config itc ON ii.table_id = itc.table_id
                WHERE ii.instance_id = %s AND itc.project_id = %s
            """, (individual_id, project_id))
            
            individual = cursor.fetchone()
            
            if not individual:
                raise HTTPException(404, "Individual not found")
            
            # Parse properties
            props = individual["properties"] if isinstance(individual["properties"], dict) else json.loads(individual["properties"])
            
            # DYNAMIC ONTOLOGY FETCH: Build graph IRI from selected ontology_name
            # This ensures we use the CURRENTLY SELECTED ontology, not stale database structure
            graph_iri = f"https://xma-adt.usnc.mil/odras/core/{project_id}/ontologies/{ontology_name}"
            
            logger.info(f"🔍 Fetching ontology structure from Fuseki: {graph_iri}")
            
            # Fetch current comprehensive ontology structure from Fuseki
            ontology_structure = await das_engine._fetch_ontology_details(graph_iri)
            
            if not ontology_structure or not ontology_structure.get("classes"):
                logger.error(f"❌ Could not fetch ontology structure for {ontology_name}")
                raise HTTPException(400, f"Could not fetch ontology structure for {ontology_name}. Ensure the ontology exists in Fuseki.")
            
            logger.info(f"✅ Fetched ontology with {len(ontology_structure.get('classes', []))} classes, {len(ontology_structure.get('object_properties', []))} object properties")
            
            # CLEANUP: Remove existing DAS-generated concepts for this requirement (1:1 relationship)
            logger.info(f"🧹 Cleaning up existing DAS concepts for requirement {individual_id}")
            cleanup_das_concepts_for_requirement(cursor, individual_id)
            
            # Real DAS call - analyze requirement and generate concepts with COMPREHENSIVE ontology structure
            das_result = await generate_concepts_with_das(individual, ontology_structure, das_engine, project_id, current_user["user_id"])
            
            # Extract concepts and relationships from DAS result
            das_concepts = das_result.get("concepts", {})
            das_relationships = das_result.get("relationships", {})
            ontology_info = das_result.get("ontology_structure", ontology_structure)
            
            # Store concepts as individuals in database
            table_id = individual["table_id"]
            individuals_created = 0
            
            for class_name, concepts in das_concepts.items():
                if concepts:  # Skip empty concept lists
                    for concept in concepts:
                        try:
                            # Generate ODRAS-style individual ID
                            concept_id = generate_concept_individual_id(cursor, table_id, class_name, ontology_name)
                            
                            # Create concept individual with metadata
                            concept_properties = {
                                "name": concept["name"],
                                "dasGenerated": True,
                                "sourceRequirement": individual["instance_name"],
                                "confidence": concept.get("confidence"),  # Use actual DAS confidence, no fallback to expose missing values
                                "rationale": concept.get("rationale", f"DAS concept for {class_name}"),
                                "conceptType": "das_concept",
                                "generatedAt": datetime.now().isoformat()
                            }
                            
                            # Add any class-specific data properties that exist
                            if concept.get("properties"):
                                concept_properties.update(concept["properties"])
                            
                            instance_id = str(uuid.uuid4())
                            instance_uri = f"{individual['graph_iri']}#{concept_id}"
                            
                            cursor.execute("""
                                INSERT INTO individual_instances (
                                    instance_id, table_id, class_name, instance_name,
                                    instance_uri, properties, source_type,
                                    validation_status, created_by, created_at, updated_at
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                instance_id, table_id, class_name, concept_id,
                                instance_uri, json.dumps(concept_properties), "das_generated",
                                "valid", current_user["user_id"], datetime.now(timezone.utc), datetime.now(timezone.utc)
                            ))
                            
                            individuals_created += 1
                            logger.info(f"✅ Created concept individual: {concept_id} ({class_name})")
                            
                        except Exception as e:
                            logger.error(f"❌ Failed to create concept for {class_name}: {e}")
            
            conn.commit()
            
            # Create a complete configuration from the concepts
            config_id = str(uuid.uuid4())
            
            # Build configuration structure from DAS concepts using ontology relationships
            configuration_structure = build_configuration_from_concepts(
                individual, das_concepts, das_relationships, ontology_info, concepts_created_map={}
            )
            
            # Calculate actual confidence from DAS concepts - no fallbacks to expose issues
            total_confidence = 0
            concept_count = 0
            missing_confidence_count = 0
            
            for class_concepts in das_concepts.values():
                for concept in class_concepts:
                    if "confidence" in concept and concept["confidence"] is not None:
                        total_confidence += concept["confidence"]
                        concept_count += 1
                    else:
                        missing_confidence_count += 1
            
            if missing_confidence_count > 0:
                logger.warning(f"⚠️ DAS returned {missing_confidence_count} concepts without confidence scores")
            
            actual_das_confidence = total_confidence / concept_count if concept_count > 0 else None  # No fallback - expose missing confidence
            
            # Store the configuration
            config_manager = ConfigurationManager()
            stored_config_id = await config_manager.create_configuration(
                project_id=project_id,
                config_data={
                    "name": f"DAS Configuration: {props.get('displayName', individual['instance_name'])} ({individuals_created} concepts)",
                    "ontology_graph": individual["graph_iri"], 
                    "source_requirement": individual["instance_name"],
                    "structure": configuration_structure,
                    "das_metadata": {
                        "generated_at": datetime.now().isoformat(),
                        "das_version": "2.0-real",
                        "confidence": actual_das_confidence,
                        "rationale": f"DAS conceptualization for {props.get('displayName', individual['instance_name'])} - avg confidence from {concept_count} concepts",
                        "individualsCreated": individuals_created
                    }
                },
                user_id=current_user["user_id"]
            )
            
            logger.info(f"🎯 DAS conceptualization complete: {individuals_created} individuals + 1 configuration created")
            
            return {
                "success": True,
                "individualsCreated": individuals_created,
                "configurationId": stored_config_id,
                "concepts": das_concepts,
                "sourceRequirement": individual["instance_name"]
            }
        
    except Exception as e:
        logger.error(f"❌ Error in DAS conceptualization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to conceptualize and store: {str(e)}"
        )

async def generate_mock_concepts_for_requirement(individual: Dict[str, Any], ontology_structure: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Mock DAS conceptualization - generates realistic concepts for UAS requirements
    """
    try:
        props = individual["properties"] if isinstance(individual["properties"], dict) else json.loads(individual["properties"])
        req_name = props.get("displayName", individual["instance_name"])
        req_text = props.get("Text", "")
        req_id = props.get("ID", "")
        
        # Mock DAS logic based on requirement content
        concepts = {}
        
        # Get available classes from ontology (excluding the source class)
        available_classes = []
        if "classes" in ontology_structure:
            available_classes = [cls["name"] for cls in ontology_structure["classes"] if cls["name"] != "Requirement"]
        
        # Generate concepts based on requirement content (simplified DAS logic)
        if "flight" in req_text.lower() or "autonomous" in req_text.lower():
            concepts["Component"] = [
                {"name": "Flight Control Computer", "confidence": 0.9, "rationale": "Primary flight control system"},
                {"name": "GPS Navigation Unit", "confidence": 0.85, "rationale": "Position and navigation hardware"}
            ]
            concepts["Process"] = [
                {"name": "Flight Path Execution", "confidence": 0.8, "rationale": "Process to execute autonomous flight"}
            ]
            concepts["Function"] = [
                {"name": "Waypoint Navigation", "confidence": 0.9, "rationale": "Core navigation function"}
            ]
            concepts["Interface"] = [
                {"name": "Autopilot Command Interface", "confidence": 0.75, "rationale": "Interface for autopilot commands"}
            ]
        elif "control" in req_text.lower() or "manual" in req_text.lower():
            concepts["Component"] = [
                {"name": "Manual Control Override System", "confidence": 0.9, "rationale": "Manual override capability"}
            ]
            concepts["Process"] = [
                {"name": "Control Input Processing", "confidence": 0.8, "rationale": "Process manual control inputs"}
            ]
            concepts["Function"] = [
                {"name": "Pilot Command Execution", "confidence": 0.85, "rationale": "Execute pilot commands"}
            ]
            concepts["Interface"] = [
                {"name": "Ground Control Station Interface", "confidence": 0.9, "rationale": "GCS control interface"}
            ]
        elif "return" in req_text.lower() or "home" in req_text.lower():
            concepts["Component"] = [
                {"name": "Emergency Return System", "confidence": 0.95, "rationale": "Automatic return-to-home system"}
            ]
            concepts["Process"] = [
                {"name": "Emergency Navigation", "confidence": 0.9, "rationale": "Navigate back to launch point"}
            ]
            concepts["Function"] = [
                {"name": "Safe Return Execution", "confidence": 0.9, "rationale": "Execute safe return procedure"}
            ]
        else:
            # Generic concepts for other requirements
            concepts["Component"] = [
                {"name": f"System Component for {req_name}", "confidence": 0.7, "rationale": "Generic component"}
            ]
            concepts["Process"] = [
                {"name": f"Process for {req_name}", "confidence": 0.7, "rationale": "Generic process"}
            ]
        
        # Always add a constraint
        concepts["Constraint"] = [
            {"name": "Performance Constraint", "confidence": 0.8, "rationale": f"Performance requirement for {req_name}"}
        ]
        
        # Only include classes that exist in the ontology
        filtered_concepts = {}
        for class_name, class_concepts in concepts.items():
            if class_name in available_classes:
                filtered_concepts[class_name] = class_concepts
        
        logger.info(f"🎯 Generated {sum(len(concepts) for concepts in filtered_concepts.values())} concepts for {req_name}")
        return filtered_concepts
        
    except Exception as e:
        logger.error(f"❌ Error generating DAS concepts: {e}")
        return {}

def build_configuration_from_concepts(
    individual: Dict[str, Any],
    das_concepts: Dict[str, List[Dict[str, Any]]],
    das_relationships: Dict[str, List[Dict[str, Any]]],
    ontology_structure: Dict[str, Any],
    concepts_created_map: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Build a complete configuration structure from DAS-generated concepts using ontology-defined relationships
    """
    try:
        props = individual["properties"] if isinstance(individual["properties"], dict) else json.loads(individual["properties"])
        
        # Root requirement
        configuration = {
            "class": "Requirement",
            "instanceId": individual["instance_name"],
            "properties": {
                "name": props.get("displayName", individual["instance_name"]),
                "text": props.get("Text", ""),
                "id": props.get("ID", "")
            },
            "relationships": []
        }
        
        # Get Requirement class's object properties from ontology (COMPREHENSIVE FORMAT)
        requirement_relationships = {}
        all_classes = ontology_structure.get("classes", [])
        all_object_properties = ontology_structure.get("object_properties", [])
        
        # Find object properties where domain is "Requirement" (case-insensitive match)
        for obj_prop in all_object_properties:
            domain = obj_prop.get("domain", "").lower()
            if domain == "requirement" and obj_prop.get("range"):
                # Capitalize the range for consistency with class names in das_concepts
                range_name = obj_prop["range"].capitalize() if obj_prop["range"] else ""
                requirement_relationships[range_name] = {
                    "property": obj_prop["name"],
                    "minCount": obj_prop.get("minCardinality", 0),
                    "maxCount": obj_prop.get("maxCardinality"),
                    "comment": obj_prop.get("comment", "") or obj_prop.get("definition", "")
                }
        
        logger.info(f"✅ Found {len(requirement_relationships)} requirement relationships from ontology")
        
        # Track visited concepts to prevent infinite recursion
        visited_concepts = set()
        
        # Helper function to build nested relationships recursively with cycle detection
        def build_nested_relationships(class_name: str, concept: Dict[str, Any], concept_index: int, base_id: str, depth: int = 0) -> Dict[str, Any]:
            """Recursively build relationships for a concept based on ontology structure"""
            
            # Prevent infinite recursion
            concept_key = f"{class_name}-{concept_index}"
            if concept_key in visited_concepts or depth > 10:  # Max depth of 10
                # Return concept without nested relationships if already visited or too deep
                return {
                    "class": class_name,
                    "instanceId": f"{base_id}-{class_name.lower()[:4]}-{concept_index+1:03d}",
                    "properties": {
                        "name": concept["name"],
                        "dasRationale": concept.get("rationale", "")
                    }
                }
            
            visited_concepts.add(concept_key)
            
            concept_node = {
                "class": class_name,
                "instanceId": f"{base_id}-{class_name.lower()[:4]}-{concept_index+1:03d}",
                "properties": {
                    "name": concept["name"],
                    "dasRationale": concept.get("rationale", "")
                },
                "relationships": []
            }
            
            # Find this class's object properties in ontology (COMPREHENSIVE FORMAT - case-insensitive)
            class_obj_props = {}
            for obj_prop in all_object_properties:
                domain = obj_prop.get("domain", "").lower()
                if domain == class_name.lower() and obj_prop.get("range"):
                    # Capitalize the range for consistency
                    range_name = obj_prop["range"].capitalize() if obj_prop["range"] else ""
                    class_obj_props[range_name] = {
                        "property": obj_prop["name"],
                        "minCount": obj_prop.get("minCardinality", 0),
                        "maxCount": obj_prop.get("maxCardinality"),
                        "comment": obj_prop.get("comment", "") or obj_prop.get("definition", "")
                    }
            
            # Build relationships to other concept classes
            for target_class, rel_info in class_obj_props.items():
                if target_class in das_concepts and das_concepts[target_class]:
                    targets = []
                    for j, target_concept in enumerate(das_concepts[target_class]):
                        # Recursively build the target concept with its relationships
                        nested_target = build_nested_relationships(target_class, target_concept, j, base_id, depth + 1)
                        targets.append(nested_target)
                    
                    if targets:
                        mult = f"({rel_info['minCount']}..{'*' if rel_info['maxCount'] is None else rel_info['maxCount']})"
                        concept_node["relationships"].append({
                            "property": rel_info["property"],
                            "multiplicity": mult,
                            "targets": targets
                        })
            
            return concept_node
        
        # Dynamically add relationships based on ontology definition
        for target_class, rel_info in requirement_relationships.items():
            if target_class in das_concepts and das_concepts[target_class]:
                # Reset visited set for each top-level relationship to allow concepts to appear in different chains
                visited_concepts.clear()
                targets = []
                for i, concept in enumerate(das_concepts[target_class]):
                    # Recursively build each concept with its nested relationships
                    nested_concept = build_nested_relationships(target_class, concept, i, individual['instance_name'])
                    targets.append(nested_concept)
                
                if targets:
                    mult = f"({rel_info['minCount']}..{'*' if rel_info['maxCount'] is None else rel_info['maxCount']})"
                    configuration["relationships"].append({
                        "property": rel_info["property"],
                        "multiplicity": mult,
                        "targets": targets
                    })
        
        
        logger.info(f"✅ Built configuration structure with {len(configuration['relationships'])} relationship types from ontology")
        
        return configuration
        
    except Exception as e:
        logger.error(f"❌ Error building configuration from concepts: {e}")
        return {
            "class": "Requirement",
            "instanceId": individual["instance_name"],
            "properties": {"name": "Error building configuration"},
            "relationships": []
        }

def cleanup_das_concepts_for_requirement(cursor, requirement_id: str):
    """
    Clean up existing DAS-generated concepts for a specific requirement to maintain 1:1 relationship
    """
    try:
        # Remove DAS-generated individual instances for this requirement
        cursor.execute("""
            DELETE FROM individual_instances 
            WHERE properties::jsonb ? 'dasGenerated' 
            AND properties::jsonb ? 'sourceRequirement'
            AND properties::jsonb->>'sourceRequirement' = %s
        """, (requirement_id,))
        
        deleted_individuals = cursor.rowcount
        
        # Remove DAS-generated configurations for this requirement  
        cursor.execute("""
            DELETE FROM configurations 
            WHERE das_metadata::jsonb ? 'source'
            AND das_metadata::jsonb->>'source' = %s
        """, (requirement_id,))
        
        deleted_configs = cursor.rowcount
        
        logger.info(f"🧹 Cleanup complete: {deleted_individuals} individuals, {deleted_configs} configurations removed for requirement {requirement_id}")
        
    except Exception as e:
        logger.error(f"❌ Error during cleanup for requirement {requirement_id}: {e}")
        # Don't raise - continue with generation even if cleanup fails

def generate_concept_individual_id(cursor, table_id: str, class_name: str, ontology_name: str) -> str:
    """
    Generate ODRAS-style individual ID for concepts
    """
    try:
        # Get next available number for this class in this ontology
        cursor.execute("""
            SELECT instance_name FROM individual_instances 
            WHERE table_id = %s AND class_name = %s
            AND instance_name ~ %s
            ORDER BY instance_name DESC
            LIMIT 1
        """, (table_id, class_name, f"^{ontology_name}-.*-[0-9]+$"))
        
        last_instance = cursor.fetchone()
        
        if last_instance:
            # Extract number from last instance (e.g., "bseo.a-comp-005" -> 5)
            parts = last_instance["instance_name"].split('-')
            if len(parts) >= 3 and parts[-1].isdigit():
                last_num = int(parts[-1])
                next_num = last_num + 1
            else:
                next_num = 1
        else:
            next_num = 1
        
        # Format: bseo.a-comp-001, bseo.a-proc-001, etc.
        class_abbrev = class_name.lower()[:4]  # "component" -> "comp", "process" -> "proc"
        concept_id = f"{ontology_name}-{class_abbrev}-{next_num:03d}"
        
        return concept_id
        
    except Exception as e:
        logger.error(f"❌ Error generating concept ID: {e}")
        return f"{ontology_name}-{class_name.lower()}-{uuid.uuid4().hex[:6]}"

@router.get("/{project_id}/configurations")
async def list_stored_configurations(
    project_id: str,
    ontology_graph: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """
    List stored DAS configurations (not root individuals)
    """
    try:
        logger.info(f"🔍 Listing stored configurations for project {project_id}")
        
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Base query for stored configurations
            base_query = """
                SELECT * FROM configurations 
                WHERE project_id = %s
            """
            params = [project_id]
            
            # Filter by ontology graph if provided
            if ontology_graph:
                base_query += " AND ontology_graph = %s"
                params.append(ontology_graph)
            
            # Add ordering and pagination
            offset = (page - 1) * page_size
            base_query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.extend([page_size, offset])
            
            # Get total count
            count_query = "SELECT COUNT(*) as total FROM configurations WHERE project_id = %s"
            count_params = [project_id]
            if ontology_graph:
                count_query += " AND ontology_graph = %s"
                count_params.append(ontology_graph)
            
            cursor.execute(count_query, count_params)
            total = cursor.fetchone()["total"]
            
            # Get configurations
            cursor.execute(base_query, params)
            configs = cursor.fetchall()
            
            # Convert to list of dicts and parse JSON fields
            configurations = []
            for config in configs:
                config_dict = dict(config)
                
                # Parse JSON fields if they are strings
                if config_dict["das_metadata"] and isinstance(config_dict["das_metadata"], str):
                    config_dict["das_metadata"] = json.loads(config_dict["das_metadata"])
                if config_dict["structure"] and isinstance(config_dict["structure"], str):
                    config_dict["structure"] = json.loads(config_dict["structure"])
                
                configurations.append(config_dict)
            
            logger.info(f"✅ Found {len(configurations)} stored configurations")
            
            return {
                "configurations": configurations,
                "total": total,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total + page_size - 1) // page_size
                }
            }
            
    except Exception as e:
        logger.error(f"❌ Error listing stored configurations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list configurations: {str(e)}"
        )

@router.get("/{project_id}/configurations/{config_id}/graph")
async def get_stored_configuration_graph(
    project_id: str,
    config_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get graph visualization for a stored DAS configuration
    """
    try:
        logger.info(f"🔍 Getting graph for stored configuration {config_id}")
        
        with get_db_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Get the stored configuration
            cursor.execute("""
                SELECT * FROM configurations 
                WHERE project_id = %s AND config_id = %s
            """, (project_id, config_id))
            
            config = cursor.fetchone()
            
            if not config:
                raise HTTPException(404, "Configuration not found")
            
            # Parse the configuration structure
            config_dict = dict(config)
            if config_dict["structure"] and isinstance(config_dict["structure"], str):
                config_dict["structure"] = json.loads(config_dict["structure"])
            if config_dict["das_metadata"] and isinstance(config_dict["das_metadata"], str):
                config_dict["das_metadata"] = json.loads(config_dict["das_metadata"])
            
            # Build graph from stored configuration
            graph_builder = GraphBuilder()
            graph_data = await graph_builder.build_graph_from_configuration(config_dict)
            
            # Add legend data
            legend_data = graph_builder.get_legend_data(graph_data)
            graph_data["legend"] = legend_data
            
            logger.info(f"✅ Built graph for stored configuration: {len(graph_data.get('nodes', []))} nodes")
            return graph_data
            
    except Exception as e:
        logger.error(f"❌ Error getting stored configuration graph: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get configuration graph: {str(e)}"
        )

async def generate_concepts_with_das(
    individual: Dict[str, Any], 
    ontology_structure: Dict[str, Any],
    das_engine: DAS2CoreEngine,
    project_id: str,
    user_id: str
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Use real DAS to analyze requirement and generate system concepts
    """
    try:
        # Parse individual properties
        props = individual["properties"] if isinstance(individual["properties"], dict) else json.loads(individual["properties"])
        req_name = props.get("displayName", individual["instance_name"])
        req_text = props.get("Text", "")
        req_id = props.get("ID", "")
        
        # COMPREHENSIVE FORMAT PROCESSING
        # Extract available classes, object properties, and data properties from comprehensive format
        all_classes = ontology_structure.get("classes", [])
        all_object_properties = ontology_structure.get("object_properties", [])
        all_data_properties = ontology_structure.get("data_properties", [])
        
        # Get available ontology classes (excluding Requirement)
        available_classes = [cls["name"] for cls in all_classes if cls["name"] != "Requirement"]
        
        # Get detailed ontology class information with matched properties
        ontology_classes_info = []
        source_class_relationships = []  # Relationships FROM the source class (Requirement)
        
        for cls in all_classes:
            class_name = cls["name"]
            
            # Find object properties for this class (where domain = class_name)
            class_obj_props = []
            for prop in all_object_properties:
                if prop.get("domain") == class_name:
                    class_obj_props.append({
                        "name": prop["name"],
                        "range": prop.get("range", ""),
                        "comment": prop.get("comment", "") or prop.get("definition", ""),
                        "minCount": prop.get("minCardinality", 0),
                        "maxCount": prop.get("maxCardinality"),
                        "inverse_of": prop.get("inverse_of", ""),
                        "subproperty_of": prop.get("subproperty_of", "")
                    })
            
            # Find data properties for this class (where domain = class_name)
            class_data_props = []
            for prop in all_data_properties:
                if prop.get("domain") == class_name:
                    class_data_props.append({
                        "name": prop["name"],
                        "range": prop.get("range", ""),
                        "comment": prop.get("comment", "") or prop.get("definition", "")
                    })
            
            # Build comprehensive class info
            class_info = {
                "name": class_name,
                "description": cls.get("comment", "") or cls.get("definition", ""),
                "data_properties": class_data_props,
                "object_properties": class_obj_props,
                "subclass_of": cls.get("subclass_of", ""),
                "equivalent_class": cls.get("equivalent_class", ""),
                "priority": cls.get("priority", ""),
                "status": cls.get("status", "")
            }
            
            # If this is the source class (Requirement), extract its outgoing relationships
            if class_name == "Requirement":
                for obj_prop in class_obj_props:
                    cardinality_str = f"({obj_prop.get('minCount', 0)}..{'*' if obj_prop.get('maxCount') is None else obj_prop.get('maxCount')})"
                    source_class_relationships.append({
                        "property": obj_prop["name"],
                        "target_class": obj_prop.get("range", ""),
                        "cardinality": cardinality_str,
                        "comment": obj_prop.get("comment", "")
                    })
            else:
                # Include non-source classes for concept generation
                ontology_classes_info.append(class_info)

        # Generate dynamic example using actual ontology classes
        dynamic_example = {}
        for i, cls_info in enumerate(ontology_classes_info[:3]):  # First 3 classes as examples
            class_name = cls_info["name"]
            dynamic_example[class_name] = [
                {
                    "name": f"Example {class_name} Instance",
                    "confidence": 0.85,
                    "rationale": f"Sample {class_name} concept derived from requirement analysis"
                }
            ]
        
        # Build DAS prompt including ontology relationships and cardinality constraints
        das_prompt = f"""
You are a systems engineering expert analyzing requirements to conceptualize implementations using a specific ontology structure.

REQUIREMENT TO ANALYZE:
- Name: {req_name}
- ID: {req_id}  
- Text: {req_text}

ONTOLOGY CLASSES AVAILABLE:
{json.dumps(ontology_classes_info, indent=2)}

RELATIONSHIPS FROM REQUIREMENT CLASS:
The Requirement class has these relationships to other classes:
{json.dumps(source_class_relationships, indent=2)}

CARDINALITY CONSTRAINTS (IMPORTANT):
- Pay attention to minCount and maxCount in object_properties
- minCount > 0 means the relationship is REQUIRED (mandatory)
- maxCount = 1 means at most ONE target (functional relationship)
- maxCount = None or missing means unlimited (*) targets allowed
- Respect these constraints in your conceptualization
- Example: If "has_component" has minCount=1, you MUST generate at least 1 Component

ONTOLOGY HIERARCHY:
- Classes may have "subclass_of" indicating inheritance
- Classes may have "equivalent_class" indicating semantic equivalence
- Use this to understand relationships between concepts

TASK:
1. Analyze the requirement thoroughly and determine what concepts are needed from EACH ontology class
2. Consider ALL aspects of the requirement: functionality, limitations, boundaries, interactions
3. Think deeply about:
   - What COMPONENTS are needed? (physical/logical parts)
   - What PROCESSES must occur? (activities performed)
   - What FUNCTIONS are realized? (capabilities delivered)
   - What CONSTRAINTS apply? (limitations, bounds, restrictions - performance limits, operational constraints, design restrictions)
   - What INTERFACES exist? (boundaries where components interact - data interfaces, control interfaces, physical connections)
   - What PARAMETERS define or measure the above? (values, metrics, settings that characterize or constrain the system)

IMPORTANT - CONSIDER ALL CLASSES INCLUDING PARAMETERS:
- Don't skip classes too quickly - think about implicit requirements
- CONSTRAINTS: Look for implied limits, bounds, accuracy requirements, tolerances, performance criteria
- INTERFACES: Consider how components communicate and interact (data flows, control signals, physical connections)
- PARAMETERS: Identify quantifiable values that define or constrain concepts:
  * For CONSTRAINTS: What numeric values/thresholds appear? (e.g., "5 km²", "2 hours", "accuracy ±10m")
  * For COMPONENTS: What configuration parameters or specifications matter? (e.g., "sensor resolution", "battery capacity")
  * For PROCESSES: What tunable settings affect the process? (e.g., "scan rate", "altitude", "overlap percentage")
- Even if not explicitly stated, identify reasonable engineering concepts for completeness

INSTRUCTIONS:
- Analyze each ontology class systematically
- Generate 1-3 concepts per class where applicable
- Provide confidence scores (0.7-1.0) and clear rationales
- Consider the semantic relationships between classes
- Respect cardinality constraints from the ontology

RESPONSE FORMAT (JSON):
Return a JSON object where each key is a class name from the ontology, and each value is an array of concept objects.

Each concept object must have:
- "name": descriptive name for the concept instance
- "confidence": score from 0.7 to 1.0 indicating your confidence
- "rationale": brief explanation of why this concept is needed

EXAMPLE FORMAT (using classes from THIS ontology):
{json.dumps(dynamic_example, indent=2)}

NOTE: The system will automatically build relationships between concepts based on the ontology structure.
You only need to identify the concepts themselves.

IMPORTANT GUIDANCE:
- Analyze EVERY class in the ontology systematically
- Generate 1-3 concepts per class where applicable based on the requirement
- If a relationship has minCount > 0, you MUST generate concepts for that target class
- If numeric values, thresholds, or measurable quantities appear in the requirement, create Parameter concepts
- Consider both explicit and implicit needs from the requirement

Analyze the requirement comprehensively against ALL ontology classes. Return ONLY valid JSON - no markdown, no extra text.
"""

        logger.info(f"🔍 Calling DAS for requirement analysis: {req_name}")
        
        # Log the complete prompt for debugging/review
        logger.info("📝 === DAS PROMPT START ===")
        logger.info(das_prompt)
        logger.info("📝 === DAS PROMPT END ===")
        
        # Call DAS for analysis
        full_response = ""
        async for chunk in das_engine.process_message_stream(
            project_id=project_id,
            message=das_prompt,
            user_id=user_id
        ):
            if chunk.get("type") == "content":
                full_response += chunk.get("content", "")
            elif chunk.get("type") == "error":
                logger.error(f"❌ DAS analysis failed: {chunk.get('message', 'Unknown error')}")
                # Fall back to mock if DAS fails
                mock_concepts = await generate_mock_concepts_for_requirement(individual, ontology_structure)
                return {"concepts": mock_concepts, "relationships": {}, "ontology_structure": ontology_structure}
        
        # Parse DAS JSON response
        try:
            # Extract JSON from DAS response (may have additional text)
            import re
            json_match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', full_response)
            if not json_match:
                # Try without markdown code fences
                json_match = re.search(r'\{[\s\S]*\}', full_response)
            
            if json_match:
                das_json = json_match.group(1) if json_match.lastindex else json_match.group()
                # Try to parse - if it fails due to incomplete JSON, try to fix it
                try:
                    das_response = json.loads(das_json)
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ JSON parse error: {e}, attempting to fix incomplete JSON")
                    # If JSON is incomplete, try to close it properly
                    # Common issue: missing closing braces for relationships section
                    if '"relationships"' in das_json and das_json.rstrip().endswith((',', '{')):
                        # Close the relationships section properly
                        fixed_json = das_json.rstrip().rstrip(',')
                        # Count opening and closing braces to balance them
                        open_braces = das_json.count('{')
                        close_braces = das_json.count('}')
                        missing_braces = open_braces - close_braces
                        fixed_json += '}' * missing_braces
                        logger.info(f"🔧 Fixed JSON by adding {missing_braces} closing braces")
                        das_response = json.loads(fixed_json)
                    else:
                        raise
                
                # Handle both formats: direct class mapping OR wrapped in "concepts"
                if "concepts" in das_response:
                    # Wrapped format
                    concepts = das_response["concepts"]
                    relationships = das_response.get("relationships", {})
                    if relationships:
                        logger.info(f"🔗 DAS returned {len(relationships)} relationship mappings (will be built from ontology instead)")
                else:
                    # Direct format - class names as top-level keys
                    concepts = das_response
                    relationships = {}
                
                # Validate and filter concepts
                filtered_concepts = {}
                total_raw_concepts = 0
                for class_name, class_concepts in concepts.items():
                    total_raw_concepts += len(class_concepts) if class_concepts else 0
                    if class_name in available_classes and class_concepts:
                        filtered_concepts[class_name] = class_concepts
                
                # Debug logging to understand DAS decisions
                class_breakdown = {class_name: len(class_concepts) for class_name, class_concepts in filtered_concepts.items()}
                logger.info(f"🎯 DAS breakdown for {req_name}: {class_breakdown} (Total: {sum(class_breakdown.values())} concepts)")
                logger.info(f"🔍 Raw DAS response had {total_raw_concepts} concepts across {len(concepts)} classes")
                
                # Return both concepts and relationships
                return {"concepts": filtered_concepts, "relationships": relationships, "ontology_structure": ontology_structure}
            else:
                logger.warning(f"⚠️ DAS response didn't contain valid JSON, using fallback")
                return {"concepts": await generate_mock_concepts_for_requirement(individual, ontology_structure), "relationships": {}, "ontology_structure": ontology_structure}
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse DAS JSON response: {e}")
            logger.info(f"DAS Response: {full_response[:200]}...")
            # Fall back to mock if JSON parsing fails
            return {"concepts": await generate_mock_concepts_for_requirement(individual, ontology_structure), "relationships": {}, "ontology_structure": ontology_structure}
        
    except Exception as e:
        logger.error(f"❌ Error in DAS concept generation: {e}")
        # Fall back to mock on any error
        mock_concepts = await generate_mock_concepts_for_requirement(individual, ontology_structure)
        return {"concepts": mock_concepts, "relationships": {}, "ontology_structure": ontology_structure}

async def generate_mock_concepts_for_requirement(individual: Dict[str, Any], ontology_structure: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Mock DAS conceptualization - fallback when real DAS fails
    """
    try:
        props = individual["properties"] if isinstance(individual["properties"], dict) else json.loads(individual["properties"])
        req_name = props.get("displayName", individual["instance_name"])
        req_text = props.get("Text", "")
        
        # Simple mock concepts as fallback
        available_classes = []
        if "classes" in ontology_structure:
            available_classes = [cls["name"] for cls in ontology_structure["classes"] if cls["name"] != "Requirement"]
        
        concepts = {}
        
        # Generic fallback concepts
        if "Component" in available_classes:
            concepts["Component"] = [{"name": f"System Component for {req_name}", "confidence": 0.7, "rationale": "Fallback concept"}]
        if "Process" in available_classes:
            concepts["Process"] = [{"name": f"Process for {req_name}", "confidence": 0.7, "rationale": "Fallback concept"}]
        if "Constraint" in available_classes:
            concepts["Constraint"] = [{"name": "Performance Constraint", "confidence": 0.6, "rationale": "Fallback constraint"}]
        
        return concepts
        
    except Exception as e:
        logger.error(f"❌ Error in mock concept generation: {e}")
        return {}
