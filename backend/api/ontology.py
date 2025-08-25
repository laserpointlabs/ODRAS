"""
Ontology API endpoints for ODRAS
Provides REST API for ontology management operations.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

from ..services.config import Settings
from ..services.db import DatabaseService
from ..services.ontology_manager import OntologyManager

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


class OntologyUpdate(BaseModel):
    metadata: Optional[Dict[str, Any]] = Field(None, description="Ontology metadata")
    classes: Optional[List[Dict[str, Any]]] = Field(None, description="List of classes")
    object_properties: Optional[List[Dict[str, Any]]] = Field(None, description="List of object properties")
    datatype_properties: Optional[List[Dict[str, Any]]] = Field(None, description="List of datatype properties")


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
    return OntologyManager(settings)


def get_db_service() -> DatabaseService:
    return DatabaseService(Settings())


@router.get("/", response_model=Dict[str, Any])
async def get_ontology(manager: OntologyManager = Depends(get_ontology_manager)):
    """
    Retrieve the current ontology in JSON format.

    Returns:
        The complete ontology structure
    """
    try:
        ontology_json = manager.get_current_ontology_json()
        return {"success": True, "data": ontology_json, "message": "Ontology retrieved successfully"}
    except Exception as e:
        logger.error(f"Failed to get ontology: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve ontology: {str(e)}")


@router.put("/", response_model=OntologyResponse)
async def update_ontology(
    ontology_data: OntologyUpdate, user_id: str = "api_user", manager: OntologyManager = Depends(get_ontology_manager)
):
    """
    Update the entire ontology from JSON format.

    Args:
        ontology_data: The complete ontology structure
        user_id: ID of the user making the change

    Returns:
        Update operation result
    """
    try:
        # Convert Pydantic model to dict
        ontology_dict = ontology_data.dict(exclude_none=True)

        # If this is a partial update, merge with existing ontology
        if not all(key in ontology_dict for key in ["metadata", "classes", "object_properties", "datatype_properties"]):
            current_ontology = manager.get_current_ontology_json()
            for key, value in ontology_dict.items():
                current_ontology[key] = value
            ontology_dict = current_ontology

        result = manager.update_ontology_from_json(ontology_dict, user_id)

        if result["success"]:
            return OntologyResponse(
                success=True,
                message=result["message"],
                data={"backup_id": result.get("backup_id"), "triples_count": result.get("triples_count")},
            )
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except Exception as e:
        logger.error(f"Failed to update ontology: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update ontology: {str(e)}")


@router.post("/classes", response_model=OntologyResponse)
async def add_class(class_data: OntologyClass, manager: OntologyManager = Depends(get_ontology_manager)):
    """
    Add a new class to the ontology.

    Args:
        class_data: Class information

    Returns:
        Operation result
    """
    try:
        result = manager.add_class(class_data.dict())

        if result["success"]:
            return OntologyResponse(success=True, message=result["message"], data={"class_uri": result.get("class_uri")})
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except Exception as e:
        logger.error(f"Failed to add class: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add class: {str(e)}")


@router.post("/properties", response_model=OntologyResponse)
async def add_property(property_data: OntologyProperty, manager: OntologyManager = Depends(get_ontology_manager)):
    """
    Add a new property to the ontology.

    Args:
        property_data: Property information

    Returns:
        Operation result
    """
    try:
        result = manager.add_property(property_data.dict())

        if result["success"]:
            return OntologyResponse(success=True, message=result["message"], data={"property_uri": result.get("property_uri")})
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
async def delete_property(property_name: str, manager: OntologyManager = Depends(get_ontology_manager)):
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
async def get_ontology_statistics(manager: OntologyManager = Depends(get_ontology_manager)):
    """
    Get statistics about the current ontology.

    Returns:
        Ontology statistics including counts of classes, properties, etc.
    """
    try:
        stats = manager.get_ontology_statistics()
        return {"success": True, "data": stats, "message": "Statistics retrieved successfully"}
    except Exception as e:
        logger.error(f"Failed to get ontology statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.post("/validate", response_model=OntologyResponse)
async def validate_ontology(
    ontology_data: Dict[str, Any] = Body(...), manager: OntologyManager = Depends(get_ontology_manager)
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
            message="Validation completed" if validation_result["valid"] else "Validation failed",
            data={"errors": validation_result["errors"]} if not validation_result["valid"] else None,
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
                "imported_at": manager._get_current_timestamp(),
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
