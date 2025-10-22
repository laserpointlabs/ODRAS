"""
CQ/MT Workbench API endpoints
Provides REST API for Competency Question and Microtheory management.
"""

import logging
import json
import re
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..services.auth import get_user_or_anonymous
from ..services.config import Settings
from ..services.db import DatabaseService
from ..services.cqmt_service import CQMTService
from ..services.sparql_runner import SPARQLRunner

logger = logging.getLogger(__name__)

# =====================================
# PYDANTIC MODELS
# =====================================

class MicrotheoryCreate(BaseModel):
    label: str = Field(..., description="Human-readable label for the microtheory")
    description: Optional[str] = Field(None, description="Description of the microtheory")
    iri: Optional[str] = Field(None, description="Custom IRI (auto-generated if not provided)")
    cloneFrom: Optional[str] = Field(None, description="Source microtheory IRI to clone from")
    setDefault: bool = Field(False, description="Set as project default microtheory")
    triples: Optional[List[Dict[str, str]]] = Field(None, description="List of triples to add to the microtheory")

class MicrotheoryResponse(BaseModel):
    id: str
    label: str
    iri: str
    parent_iri: Optional[str]
    is_default: bool
    triple_count: int
    created_at: Optional[str]

class CQCreate(BaseModel):
    cq_name: str = Field(..., description="Human-readable name for the CQ")
    problem_text: str = Field(..., description="Natural language problem statement")
    params_json: Dict[str, Any] = Field(default_factory=dict, description="SPARQL template parameters")
    sparql_text: str = Field(..., description="SPARQL SELECT query template")
    mt_iri_default: Optional[str] = Field(None, description="Default microtheory IRI")
    contract_json: Dict[str, Any] = Field(..., description="Pass/fail contract specification")
    status: str = Field("draft", description="CQ status: draft, active, deprecated")

class CQRun(BaseModel):
    mt_iri: Optional[str] = Field(None, description="Microtheory IRI (uses CQ default if not provided)")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parameter values for SPARQL template")

class CQResponse(BaseModel):
    id: str
    cq_name: str
    problem_text: str
    sparql_text: str
    mt_iri_default: Optional[str]
    contract_json: Dict[str, Any]
    status: str
    last_run_status: Optional[bool]
    last_run_reason: Optional[str] = Field(None, description="Reason for last run pass/fail")
    last_run_at: Optional[str]
    created_at: Optional[str]

class CQRunResponse(BaseModel):
    passed: bool = Field(..., description="Whether CQ execution passed contract validation")
    reason: str = Field(..., description="Pass/fail reason")
    columns: List[str] = Field(..., description="SPARQL result columns")
    row_count: int = Field(..., description="Number of result rows")
    rows_preview: List[List[str]] = Field(..., description="First 10 rows for preview")
    latency_ms: int = Field(..., description="Query execution time in milliseconds")
    run_id: str = Field(..., description="Unique run identifier")

class SuggestSPARQLRequest(BaseModel):
    problem_text: str = Field(..., description="Natural language problem statement")
    project_id: Optional[str] = Field(None, description="Project UUID for ontology context")
    ontology_graph_iri: Optional[str] = Field(None, description="Specific ontology graph IRI")
    use_das: bool = Field(False, description="Whether to use DAS for intelligent generation")

class SuggestSPARQLResponse(BaseModel):
    sparql_draft: str = Field(..., description="Generated SPARQL template")
    confidence: float = Field(..., description="AI confidence score (0.0-1.0)")
    notes: str = Field(..., description="Additional notes and guidance")

class SuggestOntologyDeltasRequest(BaseModel):
    sparql_text: str = Field(..., description="SPARQL query to analyze")
    project_id: str = Field(..., description="Project UUID for ontology context")

class SuggestOntologyDeltasResponse(BaseModel):
    existing: List[str] = Field(..., description="IRIs that exist in the ontology")
    missing: List[str] = Field(..., description="IRIs referenced but not found in ontology")

class TestQueryRequest(BaseModel):
    sparql: str = Field(..., description="SPARQL query to test")
    mt_iri: str = Field(..., description="Microtheory IRI to execute against")
    project_id: str = Field(..., description="Project UUID")

class TestQueryResponse(BaseModel):
    success: bool = Field(..., description="Whether query executed successfully")
    columns: List[str] = Field(..., description="Result columns")
    rows: List[List[str]] = Field(..., description="Result rows")
    row_count: int = Field(..., description="Number of result rows")
    execution_time_ms: int = Field(..., description="Query execution time in milliseconds")
    error: Optional[str] = Field(None, description="Error message if execution failed")

# =====================================
# ROUTER SETUP
# =====================================

router = APIRouter(prefix="/api/cqmt", tags=["cqmt"])

def get_db_service() -> DatabaseService:
    """Get database service instance."""
    settings = Settings()
    return DatabaseService(settings)

def get_cqmt_service() -> CQMTService:
    """Dependency to get CQMTService instance."""
    settings = Settings()
    db_service = DatabaseService(settings)
    return CQMTService(db_service, settings.fuseki_url)

# =====================================
# MICROTHEORY ENDPOINTS
# =====================================

@router.post("/projects/{project_id}/microtheories")
async def create_microtheory(
    project_id: str,
    request: MicrotheoryCreate,
    user: dict = Depends(get_user_or_anonymous),
    service: CQMTService = Depends(get_cqmt_service)
):
    """
    Create a new microtheory (named graph) with optional cloning.
    
    Creates a named graph in Fuseki and tracks metadata in PostgreSQL.
    If cloneFrom is provided, all triples are copied from the source graph.
    """
    try:
        user_id = user.get("user_id")
        
        # Handle anonymous user - don't pass user_id if it's "anonymous"
        created_by = user_id if user_id != "anonymous" else None
        
        result = service.create_microtheory(
            project_id=project_id,
            label=request.label,
            iri=request.iri,
            clone_from=request.cloneFrom,
            set_default=request.setDefault,
            created_by=created_by
        )
        
        if result["success"]:
            return {
                "success": True,
                "data": result["data"],
                "message": "Microtheory created successfully"
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_microtheory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/projects/{project_id}/microtheories", response_model=List[MicrotheoryResponse])
async def list_microtheories(
    project_id: str,
    user: dict = Depends(get_user_or_anonymous),
    service: CQMTService = Depends(get_cqmt_service)
):
    """
    List all microtheories for a project with triple counts.
    
    Returns metadata from PostgreSQL enriched with triple counts from Fuseki.
    """
    try:
        result = service.list_microtheories(project_id)
        
        if result["success"]:
            return result["data"]
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in list_microtheories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/microtheories/{mt_id}")
async def get_microtheory(
    mt_id: str,
    user: dict = Depends(get_user_or_anonymous),
    service: CQMTService = Depends(get_cqmt_service)
):
    """
    Get a single microtheory with its triples.
    
    Returns metadata from PostgreSQL and triples from Fuseki.
    """
    try:
        result = service.get_microtheory(mt_id)
        
        if result["success"]:
            return {"success": True, "data": result["data"]}
        else:
            raise HTTPException(status_code=404, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_microtheory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/microtheories/{mt_id}")
async def update_microtheory(
    mt_id: str,
    request: MicrotheoryCreate,
    user: dict = Depends(get_user_or_anonymous),
    service: CQMTService = Depends(get_cqmt_service)
):
    """
    Update a microtheory (label, description, triples, and default status).
    
    Updates metadata in PostgreSQL and triples in Fuseki.
    """
    try:
        user_id = user.get("user_id")
        
        result = service.update_microtheory(
            mt_id=mt_id,
            label=request.label,
            description=request.description,
            triples=request.triples,
            set_default=request.setDefault,
            updated_by=user_id if user_id != "anonymous" else None
        )
        
        if result["success"]:
            return {
                "success": True,
                "data": result["data"],
                "message": "Microtheory updated successfully"
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_microtheory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/microtheories/{mt_id}")
async def delete_microtheory(
    mt_id: str,
    user: dict = Depends(get_user_or_anonymous),
    service: CQMTService = Depends(get_cqmt_service)
):
    """
    Delete a microtheory and its named graph.
    
    Drops the named graph from Fuseki and deletes metadata from PostgreSQL.
    """
    try:
        result = service.delete_microtheory(mt_id)
        
        if result["success"]:
            return {"success": True, "message": "Microtheory deleted successfully"}
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_microtheory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/microtheories/{mt_id}/set-default")
async def set_default_microtheory(
    mt_id: str,
    project_id: str = Query(..., description="Project ID for validation"),
    user: dict = Depends(get_user_or_anonymous),
    service: CQMTService = Depends(get_cqmt_service)
):
    """
    Set a microtheory as the project default.
    
    Only one microtheory per project can be the default.
    """
    try:
        result = service.set_default_microtheory(mt_id, project_id)
        
        if result["success"]:
            return {"success": True, "message": "Default microtheory set successfully"}
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in set_default_microtheory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/microtheories/{mt_id}")
async def delete_microtheory(
    mt_id: str,
    user: dict = Depends(get_user_or_anonymous),
    service: CQMTService = Depends(get_cqmt_service)
):
    """
    Delete a microtheory.
    
    Drops the named graph from Fuseki and deletes the SQL record.
    """
    try:
        result = service.delete_microtheory(mt_id)
        
        if result["success"]:
            return {
                "success": True,
                "message": "Microtheory deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_microtheory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================
# COMPETENCY QUESTION ENDPOINTS
# =====================================

@router.post("/projects/{project_id}/cqs")
async def create_or_update_cq(
    project_id: str,
    request: CQCreate,
    user: dict = Depends(get_user_or_anonymous),
    service: CQMTService = Depends(get_cqmt_service)
):
    """
    Create or update a competency question.
    
    Performs upsert based on cq_name within the project.
    Validates SPARQL syntax and contract structure.
    """
    try:
        user_id = user.get("user_id")
        
        # Handle anonymous user - don't pass user_id if it's "anonymous"
        created_by = user_id if user_id != "anonymous" else None
        
        # Convert Pydantic model to dict
        cq_data = request.dict()
        
        result = service.create_or_update_cq(
            project_id=project_id,
            cq_data=cq_data,
            created_by=created_by
        )
        
        if result["success"]:
            return {
                "success": True,
                "data": result["data"],
                "message": "Competency question saved successfully"
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_or_update_cq: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/projects/{project_id}/cqs", response_model=List[CQResponse])
async def list_cqs(
    project_id: str,
    status: Optional[str] = Query(None, description="Filter by status"),
    mt_iri: Optional[str] = Query(None, description="Filter by default microtheory IRI"),
    user: dict = Depends(get_user_or_anonymous),
    service: CQMTService = Depends(get_cqmt_service)
):
    """
    List competency questions for a project with optional filters.
    
    Returns CQs with their last run status and timestamp.
    """
    try:
        result = service.get_cqs(
            project_id=project_id,
            status=status,
            mt_iri=mt_iri
        )
        
        if result["success"]:
            return result["data"]
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in list_cqs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cqs/{cq_id}")
async def get_cq_details(
    cq_id: str,
    user: dict = Depends(get_user_or_anonymous),
    service: CQMTService = Depends(get_cqmt_service)
):
    """
    Get detailed CQ information including recent runs.
    
    Returns full CQ details with the last 5 execution runs.
    """
    try:
        result = service.get_cq_details(cq_id)
        
        if result["success"]:
            return {"success": True, "data": result["data"]}
        else:
            raise HTTPException(status_code=404, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_cq_details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/cqs/{cq_id}")
async def update_cq(
    cq_id: str,
    request: CQCreate,
    user: dict = Depends(get_user_or_anonymous),
    service: CQMTService = Depends(get_cqmt_service)
):
    """
    Update an existing competency question.
    
    Updates the CQ with new data, validates SPARQL syntax and contract structure.
    """
    try:
        user_id = user.get("user_id")
        
        # Handle anonymous user - don't pass user_id if it's "anonymous"
        updated_by = user_id if user_id != "anonymous" else None
        
        # Convert Pydantic model to dict
        cq_data = request.dict()
        
        result = service.update_cq(
            cq_id=cq_id,
            cq_data=cq_data,
            updated_by=updated_by
        )
        
        if result["success"]:
            return {
                "success": True,
                "data": result["data"],
                "message": "Competency question updated successfully"
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_cq: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cqs/{cq_id}")
async def delete_cq(
    cq_id: str,
    user: dict = Depends(get_user_or_anonymous),
    service: CQMTService = Depends(get_cqmt_service)
):
    """
    Delete a competency question.
    
    Deletes the CQ and all associated run records.
    """
    try:
        result = service.delete_cq(cq_id)
        
        if result["success"]:
            return {
                "success": True,
                "message": "Competency question deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_cq: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cqs/{cq_id}/run", response_model=CQRunResponse)
async def run_cq(
    cq_id: str,
    request: CQRun,
    user: dict = Depends(get_user_or_anonymous),
    service: CQMTService = Depends(get_cqmt_service)
):
    """
    Execute a competency question and validate against its contract.
    
    Binds parameters, executes SPARQL in specified microtheory, validates contract,
    persists run record, and publishes completion event.
    """
    try:
        user_id = user.get("user_id")
        
        # Handle anonymous user - don't pass user_id if it's "anonymous"
        executed_by = user_id if user_id != "anonymous" else None
        
        result = service.run_cq(
            cq_id=cq_id,
            mt_iri=request.mt_iri,
            params=request.params,
            executed_by=executed_by
        )
        
        if result["success"]:
            return CQRunResponse(
                passed=result["pass"],
                reason=result["reason"],
                columns=result["columns"],
                row_count=result["row_count"],
                rows_preview=result["rows_preview"],
                latency_ms=result["latency_ms"],
                run_id=result["run_id"]
            )
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in run_cq: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cqs/{cq_id}/runs")
async def get_cq_runs(
    cq_id: str,
    limit: int = Query(20, description="Maximum number of runs to return", ge=1, le=100),
    offset: int = Query(0, description="Offset for pagination", ge=0),
    user: dict = Depends(get_user_or_anonymous),
    service: CQMTService = Depends(get_cqmt_service)
):
    """
    Get paginated run history for a CQ.
    
    Returns execution history with pass/fail status and performance metrics.
    """
    try:
        result = service.get_cq_runs(cq_id, limit, offset)
        
        if result["success"]:
            return {"success": True, "data": result["data"]}
        else:
            raise HTTPException(status_code=500, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_cq_runs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================
# DAS ASSIST ENDPOINTS (STUBS)
# =====================================

@router.post("/assist/suggest-sparql", response_model=SuggestSPARQLResponse)
async def suggest_sparql(
    request: SuggestSPARQLRequest,
    user: dict = Depends(get_user_or_anonymous)
):
    """
    Suggest SPARQL query from natural language problem text.
    
    If use_das=True and project_id provided, loads ontology context and generates intelligent suggestions.
    Otherwise returns basic template.
    """
    try:
        problem_text = request.problem_text
        
        logger.info(f"=== SPARQL SUGGESTION REQUEST ===")
        logger.info(f"use_das: {request.use_das}")
        logger.info(f"project_id: {request.project_id}")
        logger.info(f"ontology_graph_iri: {request.ontology_graph_iri}")
        logger.info(f"problem_text: {problem_text}")
        
        # If DAS is requested and we have project context, call DAS
        if request.use_das and request.project_id:
            logger.info("DAS path: use_das=True and project_id provided")
            try:
                logger.info(f"DAS suggestion requested for project {request.project_id}, ontology: {request.ontology_graph_iri}")
                
                # Get prefixes for the project
                db_service = DatabaseService(Settings())
                ontologies = db_service.list_ontologies(project_id=request.project_id)
                
                if not ontologies:
                    logger.warning(f"No ontologies found for project {request.project_id}")
                else:
                    logger.info(f"Found {len(ontologies)} ontologies for project")
                    
                    target_ontology = None
                    if request.ontology_graph_iri:
                        target_ontology = next((o for o in ontologies if o.get("graph_iri") == request.ontology_graph_iri), None)
                        if not target_ontology:
                            logger.warning(f"Specified ontology {request.ontology_graph_iri} not found, using first available")
                    if not target_ontology:
                        target_ontology = ontologies[0]
                    
                    graph_iri = target_ontology.get("graph_iri")
                    namespace_iri = graph_iri if "#" in graph_iri else f"{graph_iri}#"
                    
                    logger.info(f"Using ontology: {graph_iri}")
                    
                    # Load ontology details
                    ontology_context = None
                    try:
                        settings = Settings()
                        from ..services.ontology_manager import OntologyManager
                        manager = OntologyManager(settings)
                        ontology_json = manager.get_ontology_json_by_graph(graph_iri)
                        
                        # Extract key information for context
                        classes = ontology_json.get('classes', [])
                        object_properties = ontology_json.get('object_properties', [])
                        datatype_properties = ontology_json.get('datatype_properties', [])
                        
                        logger.info(f"Loaded ontology with {len(classes)} classes, {len(object_properties)} object properties, {len(datatype_properties)} datatype properties")
                        
                        ontology_context = {
                            'classes': [c.get('name', '') for c in classes[:20]],
                            'object_properties': [p.get('name', '') for p in object_properties[:20]],
                            'datatype_properties': [p.get('name', '') for p in datatype_properties[:20]]
                        }
                    except Exception as ontology_error:
                        logger.warning(f"Failed to load ontology details: {ontology_error}")
                    
                    # Build DAS prompt with ontology context
                    classes_list = ', '.join(ontology_context['classes']) if ontology_context and ontology_context['classes'] else 'None'
                    object_props_list = ', '.join(ontology_context['object_properties']) if ontology_context and ontology_context['object_properties'] else 'None'
                    datatype_props_list = ', '.join(ontology_context['datatype_properties']) if ontology_context and ontology_context['datatype_properties'] else 'None'
                    
                    das_prompt = f"""You are an expert SPARQL query builder for RDF ontologies.

PROBLEM STATEMENT:
{problem_text}

ONTOLOGY CONTEXT:
Namespace: {namespace_iri}
Available Classes: {classes_list}
Object Properties: {object_props_list}
Datatype Properties: {datatype_props_list}

TASK:
Generate a SPARQL SELECT query that answers the problem statement using the ontology classes and properties provided.

REQUIREMENTS:
1. Use the provided namespace prefix ':' for ontology terms
2. Always include standard prefixes: rdf, rdfs, owl
3. The query must be a SELECT query (not INSERT, UPDATE, DELETE)
4. Use actual class names from the Available Classes list
5. Use actual property names from the properties lists
6. If asking for classes in the ontology, query for owl:Class
7. If asking for instances, use the appropriate class type
8. Include proper WHERE clause with triple patterns
9. Use LIMIT if appropriate for large datasets
10. Return ONLY the SPARQL query - no explanation, no markdown, no additional text

IMPORTANT:
- If the problem asks to "list classes" or "show classes", query for owl:Class types
- If the problem asks for instances/examples/data, use rdf:type with specific classes
- Always use OPTIONAL for labels: OPTIONAL {{ ?subject rdfs:label ?label }}
- Use proper SPARQL syntax

Example for listing classes:
PREFIX : <{namespace_iri}>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT ?class ?label WHERE {{
    ?class rdf:type owl:Class .
    OPTIONAL {{ ?class rdfs:label ?label }}
    FILTER(STRSTARTS(STR(?class), STR(:)))
}}
ORDER BY ?label

Generate the SPARQL query now:"""
                    
                    # Call DAS to generate the query
                    try:
                        from ..services.das2_core_engine import DAS2CoreEngine
                        from ..services.rag_service import RAGService
                        from ..services.qdrant_service import QdrantService
                        from ..services.sql_first_thread_manager import SqlFirstThreadManager
                        
                        # Initialize services
                        qdrant_service = QdrantService(Settings())
                        rag_service = RAGService(Settings())
                        db_service = DatabaseService(Settings())
                        project_manager = SqlFirstThreadManager(Settings(), qdrant_service)
                        
                        das_engine = DAS2CoreEngine(Settings(), rag_service, project_manager, db_service)
                        
                        full_response = ""
                        async for chunk in das_engine.process_message_stream(
                            project_id=request.project_id,
                            message=das_prompt,
                            user_id=user.get("user_id", "system")
                        ):
                            if chunk.get("type") == "content":
                                full_response += chunk.get("content", "")
                            elif chunk.get("type") == "error":
                                logger.error(f"DAS error: {chunk.get('message', 'Unknown error')}")
                                raise Exception(f"DAS error: {chunk.get('message', 'Unknown error')}")
                        
                        # Extract SPARQL from response (remove any markdown formatting)
                        sparql_query = full_response.strip()
                        if "```sparql" in sparql_query:
                            sparql_query = sparql_query.split("```sparql")[1].split("```")[0].strip()
                        elif "```" in sparql_query:
                            sparql_query = sparql_query.split("```")[1].split("```")[0].strip()
                        
                        notes = "Generated by DAS using ontology context."
                        if ontology_context and ontology_context['classes']:
                            available_classes = ', '.join(ontology_context['classes'][:5])
                            notes += f" Available classes: {available_classes}"
                        
                        return SuggestSPARQLResponse(
                            sparql_draft=sparql_query,
                            confidence=0.85,
                            notes=notes
                        )
                    
                    except Exception as das_error:
                        logger.error(f"Failed to call DAS: {das_error}", exc_info=True)
                        # Fall through to basic template
                    
            except Exception as e:
                logger.error(f"Failed to process DAS request, falling back to template: {e}", exc_info=True)
                # Fall through to basic template
        else:
            logger.info(f"DAS path: Skipping DAS (use_das={request.use_das}, project_id={request.project_id})")
        
        # Basic template (fallback or non-DAS mode)
        logger.info("Returning basic template (30% confidence)")
        template = f"""# Problem: {problem_text}
# TODO: Replace variables and IRIs with project-specific values

PREFIX ex: <http://example.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?subject ?label WHERE {{
    # TODO: Add triple patterns here based on your problem
    ?subject rdfs:label ?label .
    # TODO: Add filters, constraints, and additional patterns as needed
}}
LIMIT 10"""
        
        return SuggestSPARQLResponse(
            sparql_draft=template,
            confidence=0.3,
            notes="This is a basic template. Review and customize for your ontology and specific requirements."
        )
        
    except Exception as e:
        logger.error(f"Error in suggest_sparql: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/assist/suggest-ontology-deltas", response_model=SuggestOntologyDeltasResponse)
async def suggest_ontology_deltas(
    request: SuggestOntologyDeltasRequest,
    user: dict = Depends(get_user_or_anonymous)
):
    """
    Analyze SPARQL query and identify missing ontology terms.
    
    Parses SPARQL, extracts referenced IRIs, checks against project ontology,
    returns lists of existing and missing terms.
    """
    try:
        sparql_text = request.sparql_text
        project_id = request.project_id
        
        # Extract IRIs from SPARQL query
        referenced_iris = _extract_iris_from_sparql(sparql_text)
        
        if not referenced_iris:
            return SuggestOntologyDeltasResponse(
                existing=[],
                missing=[]
            )
        
        # For V1, return stub response
        # V2 would query Fuseki to check existence
        existing_iris = [
            "http://www.w3.org/2000/01/rdf-schema#label",
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
        ]
        
        missing_iris = [iri for iri in referenced_iris if iri not in existing_iris]
        existing_filtered = [iri for iri in referenced_iris if iri in existing_iris]
        
        return SuggestOntologyDeltasResponse(
            existing=existing_filtered,
            missing=missing_iris
        )
        
    except Exception as e:
        logger.error(f"Error in suggest_ontology_deltas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================
# PREFIX MANAGEMENT ENDPOINTS
# =====================================

@router.get("/projects/{project_id}/prefixes")
async def get_project_prefixes(
    project_id: str,
    ontology_graph_iri: Optional[str] = Query(None, description="Specific ontology graph IRI, otherwise uses project default"),
    db_service: DatabaseService = Depends(get_db_service),
    user: dict = Depends(get_user_or_anonymous)
):
    """
    Get SPARQL prefixes for a project's ontology.
    
    Returns project-specific namespace prefix plus standard RDF prefixes.
    """
    try:
        # Get project's ontologies
        ontologies = db_service.list_ontologies(project_id=project_id)
        
        if not ontologies:
            # Return minimal prefixes if no ontology found
            return {
                "prefixes": [
                    {"prefix": "rdf:", "iri": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"},
                    {"prefix": "rdfs:", "iri": "http://www.w3.org/2000/01/rdf-schema#"},
                    {"prefix": "owl:", "iri": "http://www.w3.org/2002/07/owl#"}
                ],
                "default_ns": None
            }
        
        # Use specified ontology or first one found
        target_ontology = None
        if ontology_graph_iri:
            target_ontology = next((o for o in ontologies if o.get("graph_iri") == ontology_graph_iri), None)
        
        if not target_ontology:
            target_ontology = ontologies[0]
        
        graph_iri = target_ontology.get("graph_iri")
        
        # Extract namespace from graph IRI
        # Format: http://.../{ontology_name}# or http://.../{ontology_name}
        if "#" in graph_iri:
            namespace_iri = graph_iri
        else:
            namespace_iri = f"{graph_iri}#"
        
        # Build prefix list
        prefixes = [
            {"prefix": ":", "iri": namespace_iri},
            {"prefix": "rdf:", "iri": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"},
            {"prefix": "rdfs:", "iri": "http://www.w3.org/2000/01/rdf-schema#"},
            {"prefix": "owl:", "iri": "http://www.w3.org/2002/07/owl#"}
        ]
        
        return {
            "prefixes": prefixes,
            "default_ns": namespace_iri,
            "ontology_label": target_ontology.get("label", "Unknown")
        }
        
    except Exception as e:
        logger.error(f"Error getting project prefixes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-query", response_model=TestQueryResponse)
async def test_query(
    request: TestQueryRequest,
    user: dict = Depends(get_user_or_anonymous)
):
    """
    Test a SPARQL query against a microtheory without saving a CQ.
    
    Returns execution results immediately for testing during CQ development.
    """
    try:
        # Get services
        settings = Settings()
        runner = SPARQLRunner(settings.fuseki_url)
        
        # Execute query (no contract validation, no persistence)
        execution_result = runner.run_select_in_graph(
            request.mt_iri,
            request.sparql,
            {}  # No parameters for test queries
        )
        
        if execution_result["success"]:
            return TestQueryResponse(
                success=True,
                columns=execution_result["columns"],
                rows=execution_result["rows"],
                row_count=execution_result["row_count"],
                execution_time_ms=execution_result["latency_ms"],
                error=None
            )
        else:
            return TestQueryResponse(
                success=False,
                columns=[],
                rows=[],
                row_count=0,
                execution_time_ms=execution_result.get("latency_ms", 0),
                error=execution_result.get("error", "Unknown error")
            )
        
    except Exception as e:
        logger.error(f"Error testing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================
# UTILITY FUNCTIONS
# =====================================

def _extract_iris_from_sparql(sparql_text: str) -> List[str]:
    """
    Extract IRI references from SPARQL query.
    
    Args:
        sparql_text: SPARQL query string
        
    Returns:
        List of unique IRIs found in the query
    """
    iris = set()
    
    # Pattern for full IRIs in angle brackets: <http://example.org/thing>
    full_iri_pattern = r'<(https?://[^>\s]+)>'
    full_iris = re.findall(full_iri_pattern, sparql_text)
    iris.update(full_iris)
    
    # Pattern for QNames: prefix:localName
    # This is simplified - full implementation would need prefix resolution
    qname_pattern = r'\b(\w+):(\w+)\b'
    qnames = re.findall(qname_pattern, sparql_text)
    
    # Convert common prefixes to IRIs (simplified)
    prefix_map = {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "owl": "http://www.w3.org/2002/07/owl#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "ex": "http://example.org/"
    }
    
    for prefix, local_name in qnames:
        if prefix in prefix_map:
            full_iri = f"{prefix_map[prefix]}{local_name}"
            iris.add(full_iri)
    
    return list(iris)
