"""
Ontology API endpoints for ODRAS
Provides REST API for ontology management operations.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import json

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

from ..services.config import Settings
from ..services.db import DatabaseService
from ..services.ontology_manager import OntologyManager
from ..services.auth import get_user

logger = logging.getLogger(__name__)


# Pydantic models for request/response validation
class OntologyClass(BaseModel):
    name: str = Field(..., description="Class name")
    label: Optional[str] = Field(None, description="Human-readable label")
    comment: Optional[str] = Field(None, description="Description of the class")
    subclass_of: Optional[str] = Field(None, description="Parent class name")


class OntologyProperty(BaseModel):
    name: str = Field(..., description="Property name")
    type: str = Field(..., description="Property type: object, datatype, or annotation")
    label: Optional[str] = Field(None, description="Human-readable label")
    comment: Optional[str] = Field(None, description="Description of the property")
    domain: Optional[str] = Field(None, description="Domain class name")
    range: Optional[str] = Field(None, description="Range class name or datatype")
    
    # SHACL constraints
    min_count: Optional[int] = Field(None, description="Minimum cardinality (SHACL sh:minCount)")
    max_count: Optional[int] = Field(None, description="Maximum cardinality (SHACL sh:maxCount)")
    datatype_constraint: Optional[str] = Field(None, description="Required datatype (SHACL sh:datatype)")
    enumeration_values: Optional[List[str]] = Field(None, description="Valid enumeration values (SHACL sh:in)")


class OntologyUpdate(BaseModel):
    metadata: Optional[Dict[str, Any]] = Field(None, description="Ontology metadata")
    classes: Optional[List[Dict[str, Any]]] = Field(None, description="List of classes")
    object_properties: Optional[List[Dict[str, Any]]] = Field(
        None, description="List of object properties"
    )
    datatype_properties: Optional[List[Dict[str, Any]]] = Field(
        None, description="List of datatype properties"
    )


class OntologyResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Create router
router = APIRouter(prefix="/api/ontology", tags=["ontology"])


def get_ontology_manager() -> OntologyManager:
    """Dependency to get OntologyManager instance."""
    settings = Settings()
    # Pass db_service to ensure proper ResourceURIService initialization
    from ..services.db import DatabaseService

    db_service = DatabaseService(settings)
    return OntologyManager(settings, db_service)


def get_db_service() -> DatabaseService:
    return DatabaseService(Settings())


@router.get("/", response_model=Dict[str, Any])
async def get_ontology(
    graph: Optional[str] = None,
    manager: OntologyManager = Depends(get_ontology_manager),
):
    """
    Retrieve the current ontology in JSON format.

    Args:
        graph: Optional graph IRI to retrieve specific ontology

    Returns:
        The complete ontology structure
    """
    try:
        if graph:
            # Extract project ID from graph URI for proper context
            project_id = (
                manager.uri_service.parse_project_from_uri(graph)
                if hasattr(manager, "uri_service")
                else None
            )
            manager.set_graph_context(graph, project_id or "")
            ontology_json = manager.get_ontology_json_by_graph(graph)
        else:
            ontology_json = manager.get_current_ontology_json()
        return {
            "success": True,
            "data": ontology_json,
            "message": "Ontology retrieved successfully",
        }
    except Exception as e:
        logger.error(f"Failed to get ontology: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve ontology: {str(e)}")


@router.put("/", response_model=OntologyResponse, deprecated=True)
async def update_ontology(
    ontology_data: OntologyUpdate,
    project_id: Optional[str] = None,
    user_id: str = "api_user",
    manager: OntologyManager = Depends(get_ontology_manager),
):
    """
    ⚠️ DEPRECATED: Update the entire ontology from JSON format.

    🔥 WARNING: This endpoint has known issues with rich attribute persistence.
    Classes and properties may not save correctly to Fuseki.

    ✅ RECOMMENDED ALTERNATIVES:
    - Use POST /api/ontologies (create) + POST /api/ontology/save (turtle content)
    - Use individual endpoints: POST /api/ontology/classes, POST /api/ontology/properties

    See: docs/architecture/MULTI_ENDPOINT_ONTOLOGY_ISSUE.md

    Args:
        ontology_data: The complete ontology structure
        user_id: ID of the user making the change

    Returns:
        Update operation result (may be incomplete due to known JSON→RDF conversion issues)
    """

    import warnings
    warnings.warn(
        "PUT /api/ontology/ is deprecated due to JSON→RDF conversion issues. "
        "Use POST /api/ontologies + POST /api/ontology/save instead. "
        "See docs/architecture/MULTI_ENDPOINT_ONTOLOGY_ISSUE.md",
        DeprecationWarning,
        stacklevel=2
    )

    logger.warning("🔥 DEPRECATED ENDPOINT USED: PUT /api/ontology/ - Consider migrating to working alternatives")
    try:
        # Convert Pydantic model to dict
        ontology_dict = ontology_data.dict(exclude_none=True)

        # If this is a partial update, merge with existing ontology
        if not all(
            key in ontology_dict
            for key in [
                "metadata",
                "classes",
                "object_properties",
                "datatype_properties",
            ]
        ):
            current_ontology = manager.get_current_ontology_json()
            for key, value in ontology_dict.items():
                current_ontology[key] = value
            ontology_dict = current_ontology

        result = manager.update_ontology_from_json(ontology_dict, user_id)

        if result["success"]:
            return OntologyResponse(
                success=True,
                message=result["message"],
                data={
                    "backup_id": result.get("backup_id"),
                    "triples_count": result.get("triples_count"),
                },
            )
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except Exception as e:
        logger.error(f"Failed to update ontology: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update ontology: {str(e)}")


@router.post("/", response_model=OntologyResponse, deprecated=True)
async def create_ontology(
    ontology_data: OntologyUpdate,
    project_id: Optional[str] = None,
    user_id: str = "api_user",
    manager: OntologyManager = Depends(get_ontology_manager),
):
    """
    ⚠️ DEPRECATED: Create a new ontology from JSON format.

    🔥 WARNING: This endpoint has the same JSON→RDF conversion issues as PUT.
    Rich attributes may not persist correctly to Fuseki.

    ✅ RECOMMENDED ALTERNATIVE:
    - Use POST /api/ontologies (create empty) + POST /api/ontology/save (turtle content)

    See: docs/architecture/MULTI_ENDPOINT_ONTOLOGY_ISSUE.md

    Args:
        ontology_data: The complete ontology structure
        project_id: ID of the project this ontology belongs to
        user_id: ID of the user creating the ontology

    Returns:
        Creation operation result (may be incomplete due to JSON→RDF issues)
    """

    import warnings
    warnings.warn(
        "POST /api/ontology/ is deprecated due to JSON→RDF conversion issues. "
        "Use POST /api/ontologies + POST /api/ontology/save instead.",
        DeprecationWarning,
        stacklevel=2
    )

    logger.warning("🔥 DEPRECATED ENDPOINT USED: POST /api/ontology/ - Use POST /api/ontologies instead")
    try:
        # Convert Pydantic model to dict
        ontology_dict = ontology_data.dict(exclude_none=True)

        # Ensure we have basic structure for new ontology
        if "metadata" not in ontology_dict:
            raise HTTPException(status_code=400, detail="Metadata is required for new ontology")

        # Set default empty arrays if not provided
        ontology_dict.setdefault("classes", [])
        ontology_dict.setdefault("object_properties", [])
        ontology_dict.setdefault("datatype_properties", [])

        result = manager.update_ontology_from_json(ontology_dict, user_id)

        if result["success"]:
            return OntologyResponse(
                success=True,
                message=f"Ontology '{ontology_dict['metadata'].get('name', 'Unnamed')}' created successfully",
                data={
                    "backup_id": result.get("backup_id"),
                    "triples_count": result.get("triples_count"),
                    "project_id": project_id,
                },
            )
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except Exception as e:
        logger.error(f"Failed to create ontology: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create ontology: {str(e)}")


@router.post("/classes", response_model=OntologyResponse)
async def add_class(
    class_data: OntologyClass,
    graph: Optional[str] = None,
    manager: OntologyManager = Depends(get_ontology_manager),
    user: dict = Depends(get_user),
):
    """
    Add a new class to the ontology.

    Args:
        class_data: Class information
        graph: Optional graph IRI to add class to specific ontology

    Returns:
        Operation result
    """
    try:
        # Set the graph context if provided
        if graph:
            # Extract project ID from graph URI to ensure proper entity URI generation
            project_id = (
                manager.uri_service.parse_project_from_uri(graph)
                if hasattr(manager, "uri_service")
                else None
            )
            manager.set_graph_context(graph, project_id or "")

        result = manager.add_class(class_data.dict())

        if result["success"]:
            # EventCapture2: Capture class creation event
            try:
                from ..services.eventcapture2 import get_event_capture
                event_capture = get_event_capture()
                if event_capture and graph:
                    # Extract project_id and ontology_name from graph URI
                    project_id = manager.uri_service.parse_project_from_uri(graph) if hasattr(manager, "uri_service") else None
                    ontology_name = graph.split("/")[-1] if "/" in graph else "unknown"

                    if project_id:
                        await event_capture.capture_ontology_operation(
                            operation_type="modified",
                            ontology_name=ontology_name,
                            project_id=project_id,
                            user_id=user["user_id"],
                            username=user.get("username", "unknown"),
                            operation_details={
                                "class_name": class_data.name,
                                "class_label": class_data.label,
                                "class_comment": class_data.comment,
                                "subclass_of": class_data.subclass_of,
                                "operation": "class_added",
                                "graph_uri": graph
                            }
                        )
                        print(f"🔥 DIRECT: EventCapture2 class creation captured - {class_data.name} in {ontology_name}")
            except Exception as e:
                print(f"🔥 DIRECT: EventCapture2 class creation failed: {e}")
                logger.warning(f"EventCapture2 class creation failed: {e}")

            return OntologyResponse(
                success=True,
                message=result["message"],
                data={"class_uri": result.get("class_uri")},
            )
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except Exception as e:
        logger.error(f"Failed to add class: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add class: {str(e)}")


@router.post("/properties", response_model=OntologyResponse)
async def add_property(
    property_data: OntologyProperty,
    graph: Optional[str] = None,
    manager: OntologyManager = Depends(get_ontology_manager),
):
    """
    Add a new property to the ontology.

    Args:
        property_data: Property information
        graph: Optional graph IRI to store property in

    Returns:
        Operation result
    """
    try:
        # Set graph context if provided
        if graph:
            manager.set_graph_context(graph, "")
            
        result = manager.add_property(property_data.dict())

        if result["success"]:
            return OntologyResponse(
                success=True,
                message=result["message"],
                data={"property_uri": result.get("property_uri")},
            )
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except Exception as e:
        logger.error(f"Failed to add property: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add property: {str(e)}")


@router.delete("/classes/{class_name}", response_model=OntologyResponse)
async def delete_class(class_name: str, manager: OntologyManager = Depends(get_ontology_manager)):
    """
    Delete a class from the ontology.

    Args:
        class_name: Name of the class to delete

    Returns:
        Operation result
    """
    try:
        result = manager.delete_entity(class_name, "class")

        if result["success"]:
            return OntologyResponse(success=True, message=result["message"])
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except Exception as e:
        logger.error(f"Failed to delete class: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete class: {str(e)}")


@router.delete("/properties/{property_name}", response_model=OntologyResponse)
async def delete_property(
    property_name: str, manager: OntologyManager = Depends(get_ontology_manager)
):
    """
    Delete a property from the ontology.

    Args:
        property_name: Name of the property to delete

    Returns:
        Operation result
    """
    try:
        result = manager.delete_entity(property_name, "property")

        if result["success"]:
            return OntologyResponse(success=True, message=result["message"])
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except Exception as e:
        logger.error(f"Failed to delete property: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete property: {str(e)}")


@router.get("/statistics", response_model=Dict[str, Any])
async def get_ontology_statistics(
    manager: OntologyManager = Depends(get_ontology_manager),
):
    """
    Get statistics about the current ontology.

    Returns:
        Ontology statistics including counts of classes, properties, etc.
    """
    try:
        stats = manager.get_ontology_statistics()
        return {
            "success": True,
            "data": stats,
            "message": "Statistics retrieved successfully",
        }
    except Exception as e:
        logger.error(f"Failed to get ontology statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.post("/validate", response_model=OntologyResponse)
async def validate_ontology(
    ontology_data: Dict[str, Any] = Body(...),
    manager: OntologyManager = Depends(get_ontology_manager),
):
    """
    Validate an ontology JSON structure without saving it.

    Args:
        ontology_data: The ontology structure to validate

    Returns:
        Validation result
    """
    try:
        validation_result = manager._validate_ontology_json(ontology_data)

        return OntologyResponse(
            success=validation_result["valid"],
            message=("Validation completed" if validation_result["valid"] else "Validation failed"),
            data=(
                {"errors": validation_result["errors"]} if not validation_result["valid"] else None
            ),
        )

    except Exception as e:
        logger.error(f"Failed to validate ontology: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")


@router.post("/import", response_model=OntologyResponse)
async def import_ontology_file(
    file_content: str = Body(..., description="RDF/Turtle file content"),
    format: str = Body("turtle", description="RDF format (turtle, xml, n3)"),
    user_id: str = Body("api_user", description="User ID"),
    manager: OntologyManager = Depends(get_ontology_manager),
):
    """
    Import an ontology from RDF file content.

    Args:
        file_content: The RDF content to import
        format: RDF serialization format
        user_id: ID of the user importing

    Returns:
        Import operation result
    """
    try:
        # Parse RDF content and convert to JSON
        from rdflib import Graph

        graph = Graph()
        graph.parse(data=file_content, format=format)

        # Convert RDF graph to our JSON format
        # This is a simplified conversion - you might want to enhance this
        ontology_json = {
            "metadata": {
                "name": "Imported Ontology",
                "imported_at": datetime.now().isoformat(),
                "format": format,
                "namespace": manager.base_uri,
            },
            "classes": [],
            "object_properties": [],
            "datatype_properties": [],
        }

        # Extract classes and properties from the graph
        # Implementation would parse the RDF graph structure

        result = manager.update_ontology_from_json(ontology_json, user_id)

        if result["success"]:
            return OntologyResponse(
                success=True,
                message=f"Ontology imported successfully from {format} format",
                data={"backup_id": result.get("backup_id")},
            )
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except Exception as e:
        logger.error(f"Failed to import ontology: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("/export/{format}")
async def export_ontology(format: str, manager: OntologyManager = Depends(get_ontology_manager)):
    """
    Export the current ontology in various formats.

    Args:
        format: Export format (json, turtle, xml, n3)

    Returns:
        Ontology in the requested format
    """
    try:
        if format.lower() == "json":
            ontology_json = manager.get_current_ontology_json()
            return {"success": True, "data": ontology_json, "format": "json"}
        else:
            # Convert to RDF and serialize in requested format
            ontology_json = manager.get_current_ontology_json()
            rdf_graph = manager._json_to_rdf(ontology_json)
            serialized = rdf_graph.serialize(format=format)

            return {"success": True, "data": serialized, "format": format}

    except Exception as e:
        logger.error(f"Failed to export ontology: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/layout", response_model=Dict[str, Any])
async def get_layout(graph: str, manager: OntologyManager = Depends(get_ontology_manager)):
    """
    Retrieve layout data for a specific ontology graph.

    Args:
        graph: Graph IRI to retrieve layout for

    Returns:
        Layout data including node positions, zoom, and pan
    """
    try:
        layout_data = manager.get_layout_by_graph(graph)
        return {
            "success": True,
            "data": layout_data,
            "message": "Layout retrieved successfully",
        }
    except Exception as e:
        logger.error(f"Failed to get layout: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve layout: {str(e)}")


@router.put("/layout", response_model=OntologyResponse)
async def save_layout(
    graph: str,
    layout_data: Dict[str, Any] = Body(...),
    manager: OntologyManager = Depends(get_ontology_manager),
):
    """
    Save layout data for a specific ontology graph.

    Args:
        graph: Graph IRI to save layout for
        layout_data: Layout data including node positions, zoom, and pan

    Returns:
        Save operation result
    """
    try:
        result = manager.save_layout_by_graph(graph, layout_data)

        if result["success"]:
            return OntologyResponse(
                success=True,
                message=result["message"],
                data={"layout_id": result.get("layout_id")},
            )
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except Exception as e:
        logger.error(f"Failed to save layout: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save layout: {str(e)}")


@router.get("/named-views", response_model=Dict[str, Any])
async def get_named_views(graph: str, manager: OntologyManager = Depends(get_ontology_manager)):
    """
    Retrieve named views data for a specific ontology graph.

    Args:
        graph: Graph IRI to retrieve named views for

    Returns:
        Named views data for the ontology
    """
    try:
        named_views_data = manager.get_named_views_by_graph(graph)
        return {
            "success": True,
            "data": named_views_data,
        }
    except Exception as e:
        logger.error(f"Failed to get named views: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve named views: {str(e)}")


@router.put("/named-views", response_model=OntologyResponse)
async def save_named_views(
    graph: str,
    named_views_data: List[Dict[str, Any]] = Body(...),
    manager: OntologyManager = Depends(get_ontology_manager),
):
    """
    Save named views data for a specific ontology graph.

    Args:
        graph: Graph IRI to save named views for
        named_views_data: Named views data including view definitions and settings

    Returns:
        Save operation result
    """
    try:
        result = manager.save_named_views_by_graph(graph, named_views_data)

        if result["success"]:
            return OntologyResponse(
                success=True,
                message=result["message"],
                data={"views_count": len(named_views_data)},
            )
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except Exception as e:
        logger.error(f"Failed to save named views: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save named views: {str(e)}")


@router.post("/mint-iri", response_model=Dict[str, Any])
async def mint_unique_iri(
    base_name: str = Body(..., description="Base name for the entity"),
    entity_type: str = Body(
        ..., description="Type of entity (class, objectProperty, datatypeProperty)"
    ),
    graph: Optional[str] = Body(None, description="Graph IRI to check within"),
    manager: OntologyManager = Depends(get_ontology_manager),
):
    """
    Mint a unique IRI for a new entity.

    Args:
        base_name: Base name for the entity
        entity_type: Type of entity
        graph: Optional graph IRI to check within

    Returns:
        Unique IRI string
    """
    try:
        unique_iri = manager.mint_unique_iri(base_name, entity_type, graph or "")
        return {
            "success": True,
            "data": {"iri": unique_iri},
            "message": f"Unique IRI minted for {entity_type}",
        }
    except Exception as e:
        logger.error(f"Failed to mint IRI: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to mint IRI: {str(e)}")


@router.get("/validate-integrity", response_model=Dict[str, Any])
async def validate_ontology_integrity(
    graph: str, manager: OntologyManager = Depends(get_ontology_manager)
):
    """
    Validate IRI integrity for an ontology graph.

    Args:
        graph: Graph IRI to validate

    Returns:
        Validation results with warnings and errors
    """
    try:
        validation_result = manager.validate_iri_integrity(graph)
        return {
            "success": True,
            "data": validation_result,
            "message": "Integrity validation completed",
        }
    except Exception as e:
        logger.error(f"Failed to validate integrity: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to validate integrity: {str(e)}")
