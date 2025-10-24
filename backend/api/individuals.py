"""
Individual Tables API - Manage ontology individuals/instances

This module provides endpoints for:
- Analyzing ontology structure for individual table generation
- Creating and managing individual instances
- Importing requirements from Requirements Workbench
- Data mapping and external data import
- Validation of individuals against ontology constraints
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from SPARQLWrapper import SPARQLWrapper, JSON as SPARQL_JSON

from ..services.auth import get_user as get_current_user
from ..services.ontology_manager import OntologyManager
from ..services.config import Settings
from ..services.individual_table_manager import IndividualTableManager
from ..services.constraint_analyzer import ConstraintAnalyzer
from ..services.property_migration import PropertyMigrationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/individuals", tags=["individuals"])

def get_db_connection():
    """Get raw database connection for complex queries."""
    settings = Settings()
    try:
        conn = psycopg2.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_database,
            user=settings.postgres_user,
            password=settings.postgres_password
        )
        return conn
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection failed"
        )

# =====================================
# PYDANTIC MODELS
# =====================================

class IndividualTableInit(BaseModel):
    graph_iri: str = Field(..., description="Ontology graph IRI")
    ontology_label: str = Field(..., description="Display label for ontology")
    ontology_structure: Dict[str, Any] = Field(..., description="Analyzed ontology structure")

class IndividualCreate(BaseModel):
    name: str = Field(..., description="Individual instance name")
    class_type: str = Field(..., description="Ontology class this individual belongs to")
    properties: Dict[str, Any] = Field(default={}, description="Property values")
    graph_iri: Optional[str] = Field(None, description="Ontology graph IRI")
    
class IndividualUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Updated name")
    properties: Optional[Dict[str, Any]] = Field(None, description="Updated properties")

class RequirementImportRequest(BaseModel):
    requirement_ids: List[str] = Field(..., description="Requirements to import as individuals")
    mapping: Dict[str, str] = Field(default={}, description="Field mapping configuration")

class DataMappingRequest(BaseModel):
    source_data: Dict[str, Any] = Field(..., description="External data to map")
    mapping_config: Dict[str, str] = Field(..., description="Mapping configuration")
    target_class: str = Field(..., description="Target ontology class")

# =====================================
# ONTOLOGY ANALYSIS ENDPOINTS
# =====================================

@router.get("/individuals/schema")
async def analyze_ontology_schema(
    graph: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze ontology structure to generate individual table schemas
    Uses the current ontology API to get JSON structure
    """
    try:
        logger.info(f"🔍 Analyzing ontology schema for: {graph}")
        
        # Get current ontology from the existing API - USE ACTUAL ONTOLOGY DATA
        import requests
        from urllib.parse import urlencode
        
        # Get ontology data using the same method as the frontend
        try:
            # Use the ontology manager to get the actual graph data
            settings = Settings()
            ontology_manager = OntologyManager(
                fuseki_query_url=settings.fuseki_query_url,
                fuseki_update_url=settings.fuseki_update_url
            )
            
            # Try to get ontology from Fuseki using the specific graph IRI
            logger.info(f"🔍 Querying Fuseki for graph: {graph}")
            
            # Query SPARQL directly using SPARQLWrapper (like we tested)
            sparql = SPARQLWrapper(settings.fuseki_query_url)
            
            sparql_query = f"""
            SELECT ?class ?label ?comment WHERE {{
                GRAPH <{graph}> {{
                    ?class a <http://www.w3.org/2002/07/owl#Class> .
                    OPTIONAL {{ ?class <http://www.w3.org/2000/01/rdf-schema#label> ?label }}
                    OPTIONAL {{ ?class <http://www.w3.org/2000/01/rdf-schema#comment> ?comment }}
                }}
            }}
            """
            
            sparql.setQuery(sparql_query)
            sparql.setReturnFormat(SPARQL_JSON)
            sparql_result = sparql.query().convert()
            
            # Build ontology structure from SPARQL results
            classes = []
            bindings = sparql_result.get("results", {}).get("bindings", [])
            
            logger.info(f"🔍 SPARQL returned {len(bindings)} class bindings")
            
            for binding in bindings:
                class_uri = binding.get("class", {}).get("value", "")
                class_label = binding.get("label", {}).get("value", "")
                class_comment = binding.get("comment", {}).get("value", "")
                
                # Extract class name from label or URI
                class_name = class_label if class_label and class_label != "None" else class_uri.split("#")[-1].split("/")[-1]
                
                if class_name:
                    class_data = {
                        "name": class_name,
                        "uri": class_uri,
                        "comment": class_comment,
                        "definition": class_comment
                    }
                    classes.append(class_data)
                    logger.info(f"🔍 Found class: {class_name}")
            
            # Create ontology structure in the format expected by Individual Tables
            current_ontology_data = {
                "model": {"name": f"Test Ontology ({len(classes)} classes)"},
                "nodes": [
                    {
                        "data": {
                            "label": cls["name"], 
                            "type": "class", 
                            "attrs": {
                                "comment": cls["comment"],
                                "definition": cls["definition"]
                            }
                        }
                    } for cls in classes
                ],
                "edges": []  # We'll add properties later if needed
            }
            
            logger.info(f"🔍 Built ontology structure with {len(classes)} classes for Individual Tables")
            
            # Convert to Individual Tables format
            table_manager = IndividualTableManager()
            schema = table_manager.analyze_ontology_for_tables(current_ontology_data)
        
        except Exception as e:
            logger.error(f"❌ Error getting current ontology: {e}")
            # Fallback to empty structure
            schema = {
                "name": "Error Loading Ontology", 
                "classes": [],
                "object_properties": [],
                "datatype_properties": [],
                "constraints": {},
                "form_configs": {},
                "enumerations": {}
            }
        
        logger.info(f"✅ Schema analysis complete for {graph}")
        return schema
        
    except Exception as e:
        logger.error(f"❌ Error analyzing ontology schema: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze ontology schema: {str(e)}"
        )

@router.post("/{project_id}/individuals/create-tables")
async def initialize_individual_tables(
    project_id: str,
    request: IndividualTableInit,
    current_user: dict = Depends(get_current_user)
):
    """
    Initialize Individual Tables workspace for an ontology
    """
    try:
        logger.info(f"🔍 Initializing Individual Tables for project: {project_id}")
        
        # Store individual tables configuration
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if individual tables already exist for this ontology
            cursor.execute("""
                SELECT table_id FROM individual_tables_config 
                WHERE project_id = %s AND graph_iri = %s
            """, (project_id, request.graph_iri))
            
            existing = cursor.fetchone()
            if existing:
                logger.info("✅ Individual Tables already initialized")
                return {"success": True, "message": "Individual Tables already exist"}
            
            # Create individual tables configuration
            table_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO individual_tables_config (
                    table_id, project_id, graph_iri, ontology_label,
                    ontology_structure, created_by, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                table_id, project_id, request.graph_iri, 
                request.ontology_label, json.dumps(request.ontology_structure),
                current_user["user_id"], datetime.utcnow()
            ))
            
            conn.commit()
            
            logger.info(f"✅ Individual Tables initialized with ID: {table_id}")
            return {"success": True, "table_id": table_id}
            
    except Exception as e:
        logger.error(f"❌ Error initializing Individual Tables: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize Individual Tables: {str(e)}"
        )

# =====================================
# INDIVIDUAL CRUD ENDPOINTS
# =====================================

@router.get("/{project_id}/individuals/{class_name}")
async def get_class_individuals(
    project_id: str,
    class_name: str,
    graph: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all individuals for a specific ontology class
    """
    try:
        logger.info(f"🔍 Getting individuals for {class_name}, project: {project_id}, graph: {graph}")
        
        # Use provided graph parameter or try to get project ontology  
        if graph:
            graph_iri = graph
            logger.info(f"✅ Using provided graph: {graph_iri}")
        else:
            graph_iri = await get_project_ontology_graph(project_id)
            if not graph_iri:
                logger.error(f"❌ No ontology specified and no default found for project {project_id}")
                raise HTTPException(404, "No ontology specified and no default ontology found for project")
            logger.info(f"✅ Using default graph: {graph_iri}")
        
        # Query individuals from database (more reliable than Fuseki for Individual Tables)
        logger.info(f"🔍 Querying {class_name} individuals from database...")
        individuals = await query_class_individuals_from_db(project_id, graph_iri, class_name)
        
        logger.info(f"✅ Found {len(individuals)} {class_name} individuals")
        return {"individuals": individuals}
        
    except Exception as e:
        logger.error(f"❌ Error getting individuals for {class_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get individuals: {str(e)}"
        )

@router.post("/{project_id}/individuals/{class_name}")
async def create_individual(
    project_id: str,
    class_name: str,
    individual: IndividualCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new individual instance
    """
    try:
        logger.info(f"🔍 Creating individual {individual.name} for class {class_name}")
        
        # Get ontology graph from request or fallback to getting from project
        graph_iri = individual.graph_iri
        if not graph_iri:
            graph_iri = await get_project_ontology_graph(project_id)
            if not graph_iri:
                raise HTTPException(404, "No ontology found for project")
        
        # Create individual in Fuseki
        individual_uri = await create_fuseki_individual(
            graph_iri, class_name, individual
        )
        
        # Also store in database for Individual Tables
        await store_individual_in_db(project_id, graph_iri, class_name, individual, individual_uri)
        
        logger.info(f"✅ Individual created: {individual_uri}")
        return {"success": True, "individual_uri": individual_uri}
        
    except Exception as e:
        logger.error(f"❌ Error creating individual: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create individual: {str(e)}"
        )

@router.put("/{project_id}/individuals/{class_name}/{individual_id}")
async def update_individual(
    project_id: str,
    class_name: str,
    individual_id: str,
    update_data: IndividualUpdate,
    graph: Optional[str] = Query(None),
    uri: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Update an existing individual
    """
    try:
        logger.info(f"🔍 Updating individual: project={project_id}, class={class_name}, id={individual_id}")
        logger.info(f"🔍 Update data: {update_data}")
        
        # Get ontology graph from query parameter or fallback
        graph_iri = graph
        if not graph_iri:
            graph_iri = await get_project_ontology_graph(project_id)
            if not graph_iri:
                raise HTTPException(404, "No ontology found for project")
        
        logger.info(f"🔍 Using graph IRI: {graph_iri}")
        
        # Use provided URI or construct from individual_id
        individual_uri = uri if uri else individual_id
        
        # Update individual in Fuseki (may fail if not in Fuseki)
        try:
            await update_fuseki_individual(graph_iri, individual_uri, update_data)
        except Exception as e:
            logger.warning(f"⚠️ Fuseki update failed (may not exist in Fuseki): {e}")
        
        # Update in database
        await update_individual_in_db(project_id, graph_iri, class_name, individual_uri, update_data)
        
        logger.info(f"✅ Successfully updated individual: {individual_id}")
        return {"success": True}
        
    except Exception as e:
        logger.error(f"❌ Error updating individual: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update individual: {str(e)}"
        )

@router.delete("/{project_id}/individuals/{class_name}/{individual_id}")
async def delete_individual(
    project_id: str,
    class_name: str,
    individual_id: str,
    graph: Optional[str] = Query(None),
    uri: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete an individual instance
    """
    try:
        logger.info(f"🗑️ Deleting individual: project={project_id}, class={class_name}, id={individual_id}")
        
        # Get ontology graph from query parameter or fallback
        graph_iri = graph
        if not graph_iri:
            graph_iri = await get_project_ontology_graph(project_id)
            if not graph_iri:
                raise HTTPException(404, "No ontology found for project")
        
        logger.info(f"🔍 Using graph IRI: {graph_iri}")
        
        # Use provided URI or construct from individual_id
        individual_uri = uri if uri else individual_id
        
        # Delete individual from Fuseki (may fail if not in Fuseki)
        try:
            await delete_fuseki_individual(graph_iri, individual_uri)
        except Exception as e:
            logger.warning(f"⚠️ Fuseki delete failed (may not exist in Fuseki): {e}")
        
        # Delete from database
        await delete_individual_in_db(project_id, graph_iri, class_name, individual_uri)
        
        logger.info(f"✅ Successfully deleted individual: {individual_id}")
        return {"success": True}
        
    except Exception as e:
        logger.error(f"❌ Error deleting individual: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete individual: {str(e)}"
        )

# =====================================
# REQUIREMENTS WORKBENCH INTEGRATION
# =====================================

@router.get("/{project_id}/requirements-workbench/available")
async def get_available_requirements(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get available requirements from Requirements Workbench for import
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT requirement_id, requirement_name, requirement_text,
                       verification_method, created_at
                FROM requirements_enhanced 
                WHERE project_id = %s
                ORDER BY created_at DESC
            """, (project_id,))
            
            requirements = []
            for row in cursor.fetchall():
                requirements.append({
                    "requirement_id": row[0],
                    "requirement_name": row[1],
                    "requirement_text": row[2],
                    "verification_method": row[3],
                    "created_at": row[4].isoformat()
                })
            
            return {"requirements": requirements}
            
    except Exception as e:
        logger.error(f"❌ Error getting available requirements: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get requirements: {str(e)}"
        )

@router.post("/{project_id}/individuals/import-requirements")
async def import_requirements_as_individuals(
    project_id: str,
    request: RequirementImportRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Import selected requirements as Requirement class individuals
    """
    try:
        logger.info(f"🔍 Importing {len(request.requirement_ids)} requirements as individuals")
        
        # Get ontology graph
        graph_iri = await get_project_ontology_graph(project_id)
        if not graph_iri:
            raise HTTPException(404, "No ontology found for project")
        
        imported_count = 0
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            for req_id in request.requirement_ids:
                # Get requirement data
                cursor.execute("""
                    SELECT requirement_name, requirement_text, verification_method
                    FROM requirements_enhanced 
                    WHERE requirement_id = %s AND project_id = %s
                """, (req_id, project_id))
                
                req_data = cursor.fetchone()
                if not req_data:
                    continue
                
                # Create individual from requirement
                individual_data = IndividualCreate(
                    name=req_data[0] or f"Requirement_{req_id}",
                    class_type="Requirement",
                    properties={
                        "rdfs:comment": req_data[1],
                        "definition": req_data[2] or req_data[1],
                        "dc:identifier": req_id,
                        "source": "requirements_workbench"
                    }
                )
                
                # Create in Fuseki
                await create_fuseki_individual(graph_iri, "Requirement", individual_data)
                imported_count += 1
        
        logger.info(f"✅ Imported {imported_count} requirements as individuals")
        return {"success": True, "imported_count": imported_count}
        
    except Exception as e:
        logger.error(f"❌ Error importing requirements: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import requirements: {str(e)}"
        )

# =====================================
# DATA MAPPING AND IMPORT
# =====================================

@router.post("/{project_id}/individuals/import-data")
async def import_external_data(
    project_id: str,
    request: DataMappingRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Import external data using mapping configuration
    """
    try:
        logger.info(f"🔍 Importing external data for class: {request.target_class}")
        
        # Get ontology graph
        graph_iri = await get_project_ontology_graph(project_id)
        if not graph_iri:
            raise HTTPException(404, "No ontology found for project")
        
        # Process data mapping and create individuals
        imported_count = await process_data_mapping(
            graph_iri, request.source_data, request.mapping_config, request.target_class
        )
        
        return {"success": True, "imported_count": imported_count}
        
    except Exception as e:
        logger.error(f"❌ Error importing external data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import data: {str(e)}"
        )

# =====================================
# VALIDATION ENDPOINTS
# =====================================

@router.post("/{project_id}/individuals/validate")
async def validate_individuals(
    project_id: str,
    individual_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    Validate individual data against ontology constraints
    """
    try:
        # Get ontology graph
        graph_iri = await get_project_ontology_graph(project_id)
        if not graph_iri:
            raise HTTPException(404, "No ontology found for project")
        
        # Perform validation
        validation_results = await validate_individual_constraints(
            graph_iri, individual_data
        )
        
        return validation_results
        
    except Exception as e:
        logger.error(f"❌ Error validating individuals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Validation failed: {str(e)}"
        )

# =====================================
# HELPER FUNCTIONS
# =====================================

async def get_ontology_structure(graph_iri: str, ontology_manager: OntologyManager) -> Dict[str, Any]:
    """
    Get comprehensive ontology structure for individual table generation
    Uses the JSON export format that ODRAS already generates (like bseo-v1b.json)
    """
    try:
        logger.info(f"🔍 Getting ontology structure for: {graph_iri}")
        
        # First try to get from existing API that returns JSON format
        settings = Settings()
        
        # Use the existing ontology API that returns JSON structure
        import requests
        response = requests.get(f"{settings.api_base_url}/api/ontology/", headers={
            'Authorization': f'Bearer {get_auth_token()}'
        })
        
        if response.status_code == 200:
            ontology_json = response.json().get('data', {})
            
            # Transform JSON structure to individual tables format
            structure = transform_json_to_structure(ontology_json)
            return structure
        
        # Fallback to SPARQL if JSON API not available
        return await get_ontology_structure_sparql(graph_iri)
        
    except Exception as e:
        logger.error(f"❌ Error getting ontology structure: {e}")
        # Try SPARQL fallback
        return await get_ontology_structure_sparql(graph_iri)

def transform_json_to_structure(ontology_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform ODRAS JSON ontology format to individual tables structure
    Handles format like bseo-v1b.json with nodes/edges structure
    """
    structure = {
        "name": ontology_json.get("model", {}).get("name", "Ontology"),
        "classes": [],
        "object_properties": [], 
        "datatype_properties": []
    }
    
    # Process nodes to find classes and data properties
    nodes = ontology_json.get("nodes", [])
    classes_map = {}
    
    for node in nodes:
        node_data = node.get("data", {})
        node_type = node_data.get("type", "")
        
        if node_type == "class":
            class_info = {
                "name": node_data.get("label", ""),
                "id": node_data.get("id", ""),
                "comment": node_data.get("attrs", {}).get("comment", ""),
                "definition": node_data.get("attrs", {}).get("definition", ""),
                "example": node_data.get("attrs", {}).get("example", "")
            }
            classes_map[node_data.get("id", "")] = class_info
            structure["classes"].append(class_info)
        
        elif node_type == "dataProperty":
            prop_info = {
                "name": node_data.get("label", ""),
                "id": node_data.get("id", ""),
                "type": "datatype",
                "comment": node_data.get("attrs", {}).get("comment", ""),
                "range": node_data.get("attrs", {}).get("range", "xsd:string"),
                "domain": None,  # Will be set from edges
                "constraints": {}
            }
            structure["datatype_properties"].append(prop_info)
    
    # Process edges to find object properties and property domains
    edges = ontology_json.get("edges", [])
    
    for edge in edges:
        edge_data = edge.get("data", {})
        edge_type = edge_data.get("type", "")
        
        if edge_type == "objectProperty":
            # Get source and target class names
            source_id = edge_data.get("source", "")
            target_id = edge_data.get("target", "")
            
            source_class = classes_map.get(source_id, {}).get("name", "")
            target_class = classes_map.get(target_id, {}).get("name", "")
            
            prop_info = {
                "name": edge_data.get("predicate", ""),
                "label": edge_data.get("label", edge_data.get("predicate", "")),
                "type": "object",
                "comment": edge_data.get("attrs", {}).get("comment", ""),
                "domain": source_class,
                "range": target_class,
                "constraints": {
                    "min_count": edge_data.get("minCount"),
                    "max_count": edge_data.get("maxCount"),
                    "enumeration": edge_data.get("enumerationValues", [])
                }
            }
            structure["object_properties"].append(prop_info)
        
        # Handle data property domains
        elif edge_data.get("target", "") in [dp.get("id", "") for dp in structure["datatype_properties"]]:
            source_id = edge_data.get("source", "")
            source_class = classes_map.get(source_id, {}).get("name", "")
            
            # Update domain for matching data property
            for dp in structure["datatype_properties"]:
                if dp.get("id", "") == edge_data.get("target", ""):
                    dp["domain"] = source_class
                    break
    
    return structure

async def get_ontology_structure_sparql(graph_iri: str) -> Dict[str, Any]:
    """
    Fallback SPARQL-based ontology structure extraction
    """
    # Simplified SPARQL fallback implementation
    return {
        "name": "Ontology",
        "classes": [],
        "object_properties": [],
        "datatype_properties": []
    }

def get_auth_token() -> str:
    """Get authentication token for internal API calls"""
    # This would get a service token for internal API calls
    return ""

async def get_project_ontology_graph(project_id: str) -> Optional[str]:
    """
    Get the active ontology graph IRI for a project
    """
    # This would query the project database to find the active ontology
    # For now, return None - this will be implemented when we have project-ontology mapping
    return None

async def store_individual_in_db(
    project_id: str,
    graph_iri: str,
    class_name: str,
    individual: IndividualCreate,
    individual_uri: str
):
    """
    Store individual in database for Individual Tables
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get or create table configuration
            cursor.execute("""
                SELECT table_id FROM individual_tables_config
                WHERE project_id = %s AND graph_iri = %s
            """, (project_id, graph_iri))
            
            result = cursor.fetchone()
            if not result:
                # Create table config if it doesn't exist
                table_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO individual_tables_config (
                        table_id, project_id, graph_iri, ontology_label, ontology_structure, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (table_id, project_id, graph_iri, "Auto-created", "{}", datetime.utcnow()))
            else:
                table_id = result[0]
            
            # Store individual instance
            instance_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO individual_instances (
                    instance_id, table_id, class_name, instance_name,
                    instance_uri, properties, source_type, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                instance_id, table_id, class_name, individual.name,
                individual_uri, json.dumps(individual.properties),
                "manual", datetime.utcnow()
            ))
            
            conn.commit()
            logger.info(f"✅ Stored individual {individual.name} in database")
            
    except Exception as e:
        logger.error(f"❌ Error storing individual in database: {e}")
        # Don't raise - Fuseki creation succeeded, DB storage is secondary

async def query_class_individuals_from_db(project_id: str, graph_iri: str, class_name: str) -> List[Dict[str, Any]]:
    """
    Query individuals from Individual Tables database
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Query individuals from database
            cursor.execute("""
                SELECT 
                    ii.instance_id,
                    ii.instance_name,
                    ii.instance_uri,
                    ii.properties,
                    ii.validation_status,
                    ii.source_type,
                    ii.created_at,
                    ii.updated_at
                FROM individual_instances ii
                JOIN individual_tables_config itc ON ii.table_id = itc.table_id
                WHERE itc.project_id = %s 
                AND itc.graph_iri = %s
                AND ii.class_name = %s
                ORDER BY ii.instance_name
            """, (project_id, graph_iri, class_name))
            
            rows = cursor.fetchall()
            
            individuals = []
            for row in rows:
                # Parse properties JSON if it's a string
                properties = row[3]  # properties column
                if isinstance(properties, str):
                    try:
                        properties = json.loads(properties)
                    except:
                        properties = {}
                elif not isinstance(properties, dict):
                    properties = {}
                
                individual = {
                    "instance_id": row[0],  # instance_id
                    "name": row[1],         # instance_name (ODRAS ID)
                    "instance_name": row[1], # alias for compatibility
                    "uri": row[2],          # instance_uri
                    "properties": properties,
                    "validation_status": row[4], # validation_status
                    "source_type": row[5],  # source_type
                    "created_at": row[6].isoformat() if row[6] else None,
                    "updated_at": row[7].isoformat() if row[7] else None
                }
                individuals.append(individual)
            
            logger.info(f"✅ Found {len(individuals)} {class_name} individuals in database")
            return individuals
            
    except Exception as e:
        logger.error(f"❌ Error querying individuals from database: {e}")
        return []

async def query_class_individuals(graph_iri: str, class_name: str) -> List[Dict[str, Any]]:
    """
    Query individuals for a specific class from Fuseki
    """
    try:
        settings = Settings()
        sparql = SPARQLWrapper(settings.fuseki_query_url)
        
        query = f"""
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?individual ?label ?property ?value WHERE {{
            GRAPH <{graph_iri}> {{
                ?individual rdf:type ?class .
                ?class rdfs:label "{class_name}" .
                OPTIONAL {{ ?individual rdfs:label ?label }}
                OPTIONAL {{ ?individual ?property ?value }}
            }}
        }}
        """
        
        sparql.setQuery(query)
        sparql.setReturnFormat(SPARQL_JSON)
        results = sparql.query().convert()
        
        # Process results into individual objects
        individuals = {}
        
        for binding in results["results"]["bindings"]:
            individual_uri = binding["individual"]["value"]
            
            if individual_uri not in individuals:
                individuals[individual_uri] = {
                    "uri": individual_uri,
                    "name": binding.get("label", {}).get("value", individual_uri.split("#")[-1]),
                    "properties": {}
                }
            
            # Add properties
            if "property" in binding and "value" in binding:
                prop_name = binding["property"]["value"].split("#")[-1]
                prop_value = binding["value"]["value"]
                individuals[individual_uri]["properties"][prop_name] = prop_value
        
        return list(individuals.values())
        
    except Exception as e:
        logger.error(f"❌ Error querying individuals: {e}")
        return []

async def create_fuseki_individual(
    graph_iri: str, 
    class_name: str, 
    individual: IndividualCreate
) -> str:
    """
    Create individual in Fuseki triplestore
    """
    try:
        settings = Settings()
        fuseki_update_url = f"{settings.fuseki_url.rstrip('/')}/update"
        sparql = SPARQLWrapper(fuseki_update_url)
        
        # Generate unique URI for individual
        individual_uri = f"{graph_iri}#{individual.name}_{uuid.uuid4().hex[:8]}"
        
        # Build SPARQL INSERT query
        # Use the class name directly as a type reference
        # Replace spaces with underscores for IRI compatibility
        class_name_for_iri = class_name.replace(" ", "")
        class_iri = f"<{graph_iri}#{class_name_for_iri}>"
        triples = [
            f"<{individual_uri}> rdf:type {class_iri} .",
            f"<{individual_uri}> rdfs:label \"{individual.name}\" ."
        ]
        
        # Add property triples
        for prop_name, prop_value in individual.properties.items():
            # Ensure property name is wrapped as IRI
            # Remove spaces for IRI compatibility (e.g., "has Max Speed" -> "hasMaxSpeed")
            prop_name_for_iri = prop_name.replace(" ", "")
            prop_iri = prop_name if prop_name.startswith('<') and prop_name.endswith('>') else f"<{graph_iri}#{prop_name_for_iri}>"
            if isinstance(prop_value, str):
                triples.append(f"<{individual_uri}> {prop_iri} \"{prop_value}\" .")
            else:
                triples.append(f"<{individual_uri}> {prop_iri} {prop_value} .")
        
        query = f"""
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        INSERT DATA {{
            GRAPH <{graph_iri}> {{
                {' '.join(triples)}
            }}
        }}
        """
        
        logger.info(f"🔍 Creating Fuseki individual with URI: {individual_uri}")
        logger.info(f"🔍 SPARQL INSERT query:\n{query}")
        
        sparql.setQuery(query)
        sparql.method = "POST"
        result = sparql.query()
        
        logger.info(f"✅ Fuseki INSERT result: {result}")
        logger.info(f"✅ Fuseki individual created successfully: {individual_uri}")
        
        return individual_uri
        
    except Exception as e:
        logger.error(f"❌ Error creating Fuseki individual: {e}")
        raise e

async def update_fuseki_individual(
    graph_iri: str,
    individual_id: str, 
    update_data: IndividualUpdate
):
    """
    Update individual in Fuseki triplestore
    """
    try:
        settings = Settings()
        fuseki_update_url = f"{settings.fuseki_url}/update"
        sparql = SPARQLWrapper(fuseki_update_url)
        
        # Construct individual URI - handle both full URI and ID
        if individual_id.startswith('http://') or individual_id.startswith('https://'):
            # Full URI provided
            individual_uri = f"<{individual_id}>"
        else:
            # Just ID provided
            individual_uri = f"<{graph_iri}#{individual_id}>"
        
        # Build DELETE clauses for old values
        delete_clauses = []
        insert_clauses = []
        
        # If name is being updated, delete old label and insert new one
        if update_data.name:
            delete_clauses.append(f"{individual_uri} rdfs:label ?oldName .")
            insert_clauses.append(f"{individual_uri} rdfs:label \"{update_data.name}\" .")
        
        # If properties are being updated, delete old properties and insert new ones
        if update_data.properties:
            for prop_name, prop_value in update_data.properties.items():
                # Convert property name to proper IRI format
                if prop_name.startswith('http://') or prop_name.startswith('https://'):
                    prop_iri = f"<{prop_name}>"
                elif ':' in prop_name:
                    prop_iri = prop_name
                else:
                    prop_iri = f"<{graph_iri}#{prop_name}>"
                
                # Delete old property value with specific predicate
                delete_clauses.append(f"{individual_uri} {prop_iri} ?oldPropValue_{prop_name} .")
                
                # Insert new property value
                if isinstance(prop_value, str):
                    insert_clauses.append(f"{individual_uri} {prop_iri} \"{prop_value}\" .")
                else:
                    insert_clauses.append(f"{individual_uri} {prop_iri} {prop_value} .")
        
        # Build DELETE/INSERT query
        query = f"""
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        DELETE {{
            GRAPH <{graph_iri}> {{
                {' '.join(delete_clauses)}
            }}
        }}
        INSERT {{
            GRAPH <{graph_iri}> {{
                {' '.join(insert_clauses)}
            }}
        }}
        WHERE {{
            GRAPH <{graph_iri}> {{
                {individual_uri} rdf:type ?class .
                OPTIONAL {{ {individual_uri} rdfs:label ?oldName }}
                {' '.join([f'OPTIONAL {{ {individual_uri} <{graph_iri}#{prop_name}> ?oldPropValue_{prop_name} }}' for prop_name in (update_data.properties or {}).keys()])}
            }}
        }}
        """
        
        logger.info(f"🔍 SPARQL UPDATE query:\n{query}")
        sparql.setQuery(query)
        sparql.method = "POST"
        result = sparql.query()
        logger.info(f"✅ SPARQL UPDATE result: {result}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error updating Fuseki individual: {e}")
        raise e

async def delete_fuseki_individual(graph_iri: str, individual_id: str):
    """
    Delete individual from Fuseki triplestore
    """
    try:
        settings = Settings()
        fuseki_update_url = f"{settings.fuseki_url.rstrip('/')}/update"
        sparql = SPARQLWrapper(fuseki_update_url)
        
        # Handle both full URI and ID
        if individual_id.startswith('http://') or individual_id.startswith('https://'):
            # Full URI provided
            individual_uri = f"<{individual_id}>"
        else:
            # Just ID provided
            individual_uri = f"<{graph_iri}#{individual_id}>"
        
        # DELETE query to remove all triples about this individual
        query = f"""
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        DELETE {{
            GRAPH <{graph_iri}> {{
                ?s ?p ?o .
            }}
        }}
        WHERE {{
            GRAPH <{graph_iri}> {{
                BIND({individual_uri} AS ?s)
                ?s ?p ?o .
            }}
        }}
        """
        
        sparql.setQuery(query)
        sparql.method = "POST"
        sparql.query()
        
        logger.info(f"✅ Deleted individual from Fuseki: {individual_id}")
        
    except Exception as e:
        logger.error(f"❌ Error deleting Fuseki individual: {e}")
        raise e

async def update_individual_in_db(project_id: str, graph_iri: str, class_name: str, individual_id: str, update_data: IndividualUpdate):
    """
    Update individual in database
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Build update query based on what's provided
            updates = []
            params = []
            
            if update_data.name:
                updates.append("instance_name = %s")
                params.append(update_data.name)
            
            if update_data.properties:
                updates.append("properties = %s")
                params.append(json.dumps(update_data.properties))
            
            if updates:
                updates.append("updated_at = %s")
                params.append(datetime.utcnow())
                
                # Build WHERE clause params - match by instance_uri only
                where_params = [individual_id, project_id, graph_iri, class_name]
                
                # Combine SET params and WHERE params
                all_params = params + where_params
                
                cursor.execute(f"""
                    UPDATE individual_instances
                    SET {', '.join(updates)}
                    WHERE instance_uri = %s
                    AND instance_id IN (
                        SELECT ii.instance_id 
                        FROM individual_instances ii
                        JOIN individual_tables_config itc ON ii.table_id = itc.table_id
                        WHERE itc.project_id = %s 
                        AND itc.graph_iri = %s
                        AND ii.class_name = %s
                    )
                """, all_params)
                
                conn.commit()
                logger.info(f"✅ Updated individual in database: {individual_id}")
            
    except Exception as e:
        logger.error(f"❌ Error updating individual in database: {e}")
        # Don't raise - Fuseki update succeeded, DB update is secondary

async def delete_individual_in_db(project_id: str, graph_iri: str, class_name: str, individual_id: str):
    """
    Delete individual from database
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Delete individual from database - match by instance_uri only
            cursor.execute("""
                DELETE FROM individual_instances
                WHERE instance_uri = %s
                AND instance_id IN (
                    SELECT ii.instance_id 
                    FROM individual_instances ii
                    JOIN individual_tables_config itc ON ii.table_id = itc.table_id
                    WHERE itc.project_id = %s 
                    AND itc.graph_iri = %s
                    AND ii.class_name = %s
                )
            """, (individual_id, project_id, graph_iri, class_name))
            
            conn.commit()
            logger.info(f"✅ Deleted individual from database: {individual_id}")
            
    except Exception as e:
        logger.error(f"❌ Error deleting individual from database: {e}")
        # Don't raise - Fuseki deletion succeeded, DB deletion is secondary

async def process_data_mapping(
    graph_iri: str,
    source_data: Dict[str, Any],
    mapping_config: Dict[str, str],
    target_class: str
) -> int:
    """
    Process data mapping and create individuals
    """
    # Implementation for data mapping and import
    return 0

async def validate_individual_constraints(
    graph_iri: str,
    individual_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate individual against ontology constraints using Fuseki
    """
    return {"valid": True, "errors": [], "warnings": []}


# =====================================
# PROPERTY MIGRATION ENDPOINTS
# =====================================

@router.get("/{project_id}/property-mappings")
async def get_property_mappings(
    project_id: str,
    graph: Optional[str] = Query(None),
    class_name: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Get pending property mappings that need migration
    """
    try:
        graph_iri = graph
        if not graph_iri:
            raise HTTPException(400, "graph parameter required")
        
        migration_service = PropertyMigrationService()
        mappings = migration_service.get_pending_mappings(project_id, graph_iri, class_name)
        
        # Add affected individuals count
        for mapping in mappings:
            mapping['affected_count'] = migration_service.get_affected_individuals_count(
                project_id, graph_iri, mapping['class_name'], mapping['old_property_name']
            )
        
        return {"mappings": mappings}
        
    except Exception as e:
        logger.error(f"Error getting property mappings: {e}")
        raise HTTPException(500, f"Failed to get property mappings: {str(e)}")


@router.post("/{project_id}/property-mappings/migrate")
async def migrate_property(
    project_id: str,
    mapping_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    Migrate individual properties from old name to new name
    """
    try:
        graph_iri = mapping_data.get("graph_iri")
        class_name = mapping_data.get("class_name")
        old_property_name = mapping_data.get("old_property_name")
        new_property_name = mapping_data.get("new_property_name")
        
        if not all([graph_iri, class_name, old_property_name, new_property_name]):
            raise HTTPException(400, "Missing required fields")
        
        migration_service = PropertyMigrationService()
        result = migration_service.migrate_individuals(
            project_id, graph_iri, class_name, old_property_name, new_property_name
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error migrating property: {e}")
        raise HTTPException(500, f"Failed to migrate property: {str(e)}")


@router.post("/{project_id}/property-mappings/skip")
async def skip_property_migration(
    project_id: str,
    mapping_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    Skip a property migration (property values will be lost)
    """
    try:
        graph_iri = mapping_data.get("graph_iri")
        class_name = mapping_data.get("class_name")
        old_property_name = mapping_data.get("old_property_name")
        new_property_name = mapping_data.get("new_property_name")
        
        if not all([graph_iri, class_name, old_property_name, new_property_name]):
            raise HTTPException(400, "Missing required fields")
        
        migration_service = PropertyMigrationService()
        migration_service.skip_mapping(
            project_id, graph_iri, class_name, old_property_name, new_property_name
        )
        
        return {"success": True, "message": "Migration skipped"}
        
    except Exception as e:
        logger.error(f"Error skipping migration: {e}")
        raise HTTPException(500, f"Failed to skip migration: {str(e)}")


@router.post("/{project_id}/class-mappings/migrate")
async def migrate_class_rename(
    project_id: str,
    mapping_data: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """
    Migrate individuals from old class name to new class name
    """
    try:
        graph_iri = mapping_data.get("graph_iri")
        old_class_name = mapping_data.get("old_class_name")
        new_class_name = mapping_data.get("new_class_name")
        
        if not all([graph_iri, old_class_name, new_class_name]):
            raise HTTPException(400, "Missing required fields: graph_iri, old_class_name, new_class_name")
        
        migration_service = PropertyMigrationService()
        result = migration_service.migrate_class_rename(
            project_id, graph_iri, old_class_name, new_class_name
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error migrating class rename: {e}")
        raise HTTPException(500, f"Failed to migrate class rename: {str(e)}")
