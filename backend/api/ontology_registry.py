"""
Ontology Registry API endpoints for ODRAS
Provides REST API for ontology registry operations (plural /api/ontologies endpoints).
"""

import logging
from typing import Any, Dict, List, Optional
import httpx
import requests
from rdflib import Graph, RDF
from rdflib.namespace import OWL, RDFS

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from ..services.config import Settings
from ..services.db import DatabaseService
from ..services.auth import get_user, get_admin_user
from ..services.namespace_uri_generator import NamespaceURIGenerator
from ..services.resource_uri_service import get_resource_uri_service

logger = logging.getLogger(__name__)

# Create registry router (plural /api/ontologies)
registry_router = APIRouter(prefix="/api/ontologies", tags=["ontology-registry"])


def get_db_service() -> DatabaseService:
    """Dependency to get database service"""
    return DatabaseService(Settings())


@registry_router.get("")
async def list_ontologies(
    project: Optional[str] = None,
    db_service: DatabaseService = Depends(get_db_service)
):
    """Discover available ontologies (named graphs with owl:Ontology) from Fuseki.

    Returns a list of { graphIri, label } entries. Optional project filter limits by substring match in graph IRI.
    """
    try:
        # Prefer registry when project is provided
        if project:
            try:
                regs = db_service.list_ontologies(project_id=project)
                if regs:
                    return {
                        "ontologies": [
                            {
                                "graphIri": r.get("graph_iri"),
                                "label": r.get("label"),
                                "role": r.get("role"),
                                "is_reference": r.get("is_reference", False),
                            }
                            for r in regs
                            if r.get("graph_iri")
                        ]
                    }
            except Exception:
                pass

        s = Settings()
        base = s.fuseki_url.rstrip("/")
        query_url = f"{base}/query"
        # Baseline discovery: graphs with owl:Ontology
        filter_clause = ""
        if project:
            # naive substring filter; safe for MVP
            safe = project.replace('"', '\\"')
            filter_clause = f'FILTER(CONTAINS(STR(?graph), "{safe}"))'
        sparql = (
            "PREFIX owl: <http://www.w3.org/2002/07/owl#>\n"
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
            "SELECT DISTINCT ?graph ?ontology ?label WHERE {\n"
            "  GRAPH ?graph {\n"
            "    ?ontology a owl:Ontology .\n"
            "    OPTIONAL { ?ontology rdfs:label ?label }\n"
            f"    {filter_clause}\n"
            "  }\n"
            "} ORDER BY LCASE(STR(?label))"
        )
        headers = {
            "Accept": "application/sparql-results+json",
            "Content-Type": "application/sparql-query",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(query_url, content=sparql.encode("utf-8"), headers=headers)
            r.raise_for_status()
            data = r.json()
            rows = data.get("results", {}).get("bindings", [])
            ontologies = []
            for b in rows:
                graph = b.get("graph", {}).get("value")
                label = (b.get("label", {}) or {}).get("value")
                if not label and graph:
                    # Fallback label from IRI tail
                    tail = graph.rsplit("/", 1)[-1]
                    label = tail or graph
                if graph:
                    ontologies.append({"graphIri": graph, "label": label or graph})

            # Fallback: any non-empty named graph if no owl:Ontology found
            if not ontologies:
                sparql2 = "SELECT DISTINCT ?graph WHERE { GRAPH ?graph { ?s ?p ?o } } ORDER BY STR(?graph) LIMIT 200"
                r2 = await client.post(query_url, content=sparql2.encode("utf-8"), headers=headers)
                r2.raise_for_status()
                data2 = r2.json()
                for b in data2.get("results", {}).get("bindings", []):
                    graph = b.get("graph", {}).get("value")
                    if not graph:
                        continue
                    if project and project not in graph:
                        continue
                    tail = graph.rsplit("/", 1)[-1]
                    ontologies.append({"graphIri": graph, "label": tail or graph})

            return {"ontologies": ontologies}
    except httpx.HTTPStatusError as he:
        detail = he.response.text if he.response is not None else str(he)
        raise HTTPException(status_code=500, detail=f"SPARQL error: {detail}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list ontologies: {str(e)}")


@registry_router.post("")
async def create_ontology(
    body: Dict,
    user=Depends(get_user),
    db_service: DatabaseService = Depends(get_db_service)
):
    """Create a new empty ontology as a named graph with owl:Ontology and rdfs:label.

    Body: { project: string, name: string, label?: string, is_reference?: boolean }
    Returns: { graphIri, label }
    """
    project = (body.get("project") or "").strip()
    name = (body.get("name") or "").strip().strip("/")
    label = (body.get("label") or name or "New Ontology").strip()
    is_reference = body.get("is_reference", False)
    if not project or not name:
        raise HTTPException(status_code=400, detail="project and name are required")

    # Only admins can create reference ontologies
    if is_reference and not user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Only admins can create reference ontologies")

    # Use centralized URI service for consistent namespace-aware URI generation
    settings = Settings()
    uri_service = get_resource_uri_service(settings, db_service)
    namespace_generator = NamespaceURIGenerator(settings)  # Always initialize for header generation

    # Validate installation configuration
    config_issues = uri_service.validate_installation_config()
    if config_issues:
        for issue in config_issues:
            logger.warning(f"URI Configuration Issue: {issue}")

    if is_reference:
        # For reference ontologies, use the legacy namespace generator for now
        # TODO: Integrate reference ontology patterns into ResourceURIService
        if project.startswith("core-"):
            graph_iri = namespace_generator.generate_ontology_uri("core", ontology_name=name)
        elif project.startswith("domain-"):
            domain = project.replace("domain-", "")
            graph_iri = namespace_generator.generate_ontology_uri(
                "domain", domain=domain, ontology_name=name
            )
        elif project.startswith("program-"):
            program = project.replace("program-", "")
            graph_iri = namespace_generator.generate_ontology_uri(
                "program", program=program, ontology_name=name
            )
        else:
            # Use standard project-based URI even for reference ontologies
            graph_iri = uri_service.generate_ontology_uri(project, name)
    else:
        # For working ontologies, use the new centralized URI service
        graph_iri = uri_service.generate_ontology_uri(project, name)

        logger.info(f"Generated ontology URI: {graph_iri} for project: {project}, name: {name}")
        logger.info(f"Installation base URI: {settings.installation_base_uri}")

        # Log namespace info for debugging
        namespace_info = uri_service.get_namespace_info(project)
        logger.info(f"Project namespace info: {namespace_info}")

    # Generate proper ontology header
    external_imports = namespace_generator.get_external_namespace_mappings()
    turtle = namespace_generator.generate_ontology_header(
        ontology_uri=graph_iri,
        title=label,
        description=f"Ontology created in ODRAS for {project}",
        version="1.0.0",
        imports=external_imports,
    )
    try:
        # Membership check
        # project here is a plain string id
        # Ensure user is member
        if not db_service.is_user_member(project_id=project, user_id=user["user_id"]):
            raise HTTPException(status_code=403, detail="Not a member of project")
        s = Settings()
        base = s.fuseki_url.rstrip("/")
        url = f"{base}/data?graph={graph_iri}"
        headers = {"Content-Type": "text/turtle"}
        auth = (s.fuseki_user, s.fuseki_password) if s.fuseki_user and s.fuseki_password else None
        resp = requests.put(
            url, data=turtle.encode("utf-8"), headers=headers, auth=auth, timeout=20
        )
        if 200 <= resp.status_code < 300:
            # Register in ontologies_registry
            try:
                db_service.add_ontology(
                    project_id=project,
                    graph_iri=graph_iri,
                    label=label,
                    role="base",
                    is_reference=is_reference,
                )
            except Exception:
                pass

            # EventCapture2: Capture ontology creation event directly
            try:
                from ..services.eventcapture2 import get_event_capture
                event_capture = get_event_capture()
                if event_capture:
                    await event_capture.capture_ontology_operation(
                        operation_type="created",
                        ontology_name=name,
                        project_id=project,
                        user_id=user["user_id"],
                        username=user.get("username", "unknown"),
                        operation_details={
                            "label": label,
                            "is_reference": is_reference,
                            "graph_iri": graph_iri,
                            "classes_count": 0,
                            "properties_count": 0,
                            "created_via": "gui"
                        }
                    )
                    print(f"🔥 DIRECT: EventCapture2 ontology creation captured for {name}")
            except Exception as e:
                print(f"🔥 DIRECT: EventCapture2 ontology creation failed: {e}")
                logger.warning(f"EventCapture2 ontology creation failed: {e}")

            return {"graphIri": graph_iri, "label": label}
        raise HTTPException(
            status_code=500, detail=f"Fuseki returned {resp.status_code}: {resp.text}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create ontology: {str(e)}")


@registry_router.get("/reference")
async def list_reference_ontologies(
    user=Depends(get_user),
    db_service: DatabaseService = Depends(get_db_service)
):
    """List all reference ontologies across all projects."""
    try:
        reference_ontologies = db_service.list_reference_ontologies()
        return {"reference_ontologies": reference_ontologies}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list reference ontologies: {str(e)}"
        )


@registry_router.put("/reference")
async def toggle_reference_ontology(
    body: Dict,
    user=Depends(get_admin_user),
    db_service: DatabaseService = Depends(get_db_service)
):
    """Toggle reference status of an ontology. Admin only."""
    graph_iri = (body.get("graph") or "").strip()
    is_reference = body.get("is_reference", False)

    if not graph_iri:
        raise HTTPException(status_code=400, detail="graph parameter is required")

    try:
        # Update the reference status in the database
        result = db_service.update_ontology_reference_status(graph_iri=graph_iri, is_reference=is_reference)
        if result:
            return {
                "success": True,
                "graph_iri": graph_iri,
                "is_reference": is_reference,
            }
        else:
            raise HTTPException(status_code=404, detail="Ontology not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update reference status: {str(e)}")


@registry_router.post("/import-url")
async def import_ontology_from_url(
    body: Dict,
    user=Depends(get_user),
    db_service: DatabaseService = Depends(get_db_service)
):
    """Import an ontology from a remote URL. Any authenticated user can import, but only admins can set as reference."""
    url = body.get("url", "").strip()
    project_id = body.get("project_id", "").strip()
    name = body.get("name", "").strip()
    label = body.get("label", "").strip()

    # Only admins can set ontologies as reference
    is_admin = user.get("is_admin", False)
    if is_admin:
        is_reference = body.get("is_reference", True)  # Default to reference for URL imports
    else:
        is_reference = False  # Non-admins cannot set as reference

    if not url:
        raise HTTPException(status_code=400, detail="URL parameter is required")

    if not project_id:
        raise HTTPException(status_code=400, detail="project_id parameter is required")

    if not name:
        raise HTTPException(status_code=400, detail="name parameter is required")

    try:
        # Fetch the ontology from the URL
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            content = response.text

        # Parse the RDF content
        graph = Graph()
        try:
            # Try to detect format from content-type or content
            content_type = response.headers.get("content-type", "").lower()
            if "xml" in content_type or "rdf" in content_type:
                format = "xml"
            elif "turtle" in content_type or "ttl" in content_type:
                format = "turtle"
            elif "n3" in content_type:
                format = "n3"
            else:
                # Try to auto-detect format
                if content.strip().startswith("<?xml") or content.strip().startswith("<rdf"):
                    format = "xml"
                elif content.strip().startswith("@prefix") or content.strip().startswith("PREFIX"):
                    format = "turtle"
                else:
                    format = "xml"  # Default fallback

            graph.parse(data=content, format=format)
        except Exception as parse_error:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to parse RDF content: {str(parse_error)}",
            )

        # Extract ontology IRI and label
        ontology_iri = None
        ontology_label = label or name

        # Look for owl:Ontology declarations
        for s, p, o in graph.triples((None, RDF.type, OWL.Ontology)):
            ontology_iri = str(s)
            # Try to get the label
            for label_triple in graph.triples((s, RDFS.label, None)):
                ontology_label = str(label_triple[2])
                break
            break

        if not ontology_iri:
            # If no owl:Ontology found, use the URL as the IRI
            ontology_iri = url

        # Create the graph IRI for our system using installation configuration
        settings = Settings()
        base_uri = settings.installation_base_uri.rstrip("/")
        graph_iri = f"{base_uri}/{project_id}/{name}"

        # Store the ontology in Fuseki using the REST API
        fuseki_url = "http://localhost:3030/odras"
        fuseki_data_url = f"{fuseki_url}/data"

        # Convert graph to turtle format for storage
        turtle_content = graph.serialize(format="turtle")

        # Upload the ontology to Fuseki as a named graph
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                f"{fuseki_data_url}?graph={graph_iri}",
                content=turtle_content,
                headers={"Content-Type": "text/turtle"},
            )
            response.raise_for_status()

        # Register the ontology in our database
        db_service.add_ontology(
            project_id=project_id,
            graph_iri=graph_iri,
            label=ontology_label,
            role="imported",
            is_reference=is_reference,
        )

        return {
            "success": True,
            "graph_iri": graph_iri,
            "label": ontology_label,
            "original_iri": ontology_iri,
            "source_url": url,
            "is_reference": is_reference,
        }

    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch ontology from URL: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import ontology: {str(e)}")


@registry_router.delete("")
async def delete_ontology(
    graph: str,
    project: Optional[str] = None,
    user=Depends(get_user),
    db_service: DatabaseService = Depends(get_db_service)
):
    """Delete a named graph (drop ontology)."""
    if not graph:
        raise HTTPException(status_code=400, detail="graph parameter required")
    try:
        # Optional membership check if project provided
        if project and not db_service.is_user_member(project_id=project, user_id=user["user_id"]):
            raise HTTPException(status_code=403, detail="Not a member of project")
        s = Settings()
        update_url = f"{s.fuseki_url.rstrip('/')}/update"

        # Delete the main ontology graph
        query = f"DROP GRAPH <{graph}>"
        headers = {"Content-Type": "application/sparql-update"}
        r = requests.post(update_url, data=query.encode("utf-8"), headers=headers, timeout=20)

        # Also delete the associated layout graph if it exists
        layout_graph = f"{graph}#layout"
        layout_query = f"DROP GRAPH <{layout_graph}>"
        try:
            requests.post(
                update_url,
                data=layout_query.encode("utf-8"),
                headers=headers,
                timeout=20,
            )
        except Exception:
            pass  # Layout graph might not exist, that's okay

        if 200 <= r.status_code < 300:
            try:
                db_service.delete_ontology(graph_iri=graph)
            except Exception:
                pass
            return {"deleted": graph}
        raise HTTPException(status_code=500, detail=f"Fuseki returned {r.status_code}: {r.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete ontology: {str(e)}")


@registry_router.put("/label")
async def relabel_ontology(body: Dict):
    """Update rdfs:label of the ontology node inside the named graph (IRI unchanged)."""
    graph = (body.get("graph") or "").strip()
    label = (body.get("label") or "").strip()
    if not graph or not label:
        raise HTTPException(status_code=400, detail="graph and label are required")
    try:
        s = Settings()
        update_url = f"{s.fuseki_url.rstrip('/')}/update"
        safe_label = label.replace("\\", "\\\\").replace('"', '\\"')
        sparql = (
            "PREFIX owl: <http://www.w3.org/2002/07/owl#>\n"
            "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
            f"DELETE {{ GRAPH <{graph}> {{ ?o rdfs:label ?old }} }}\n"
            f'INSERT {{ GRAPH <{graph}> {{ ?o rdfs:label "{safe_label}" }} }}\n'
            f"WHERE  {{ GRAPH <{graph}> {{ ?o a owl:Ontology . OPTIONAL {{ ?o rdfs:label ?old }} }} }}\n"
        )
        headers = {"Content-Type": "application/sparql-update"}
        auth = (s.fuseki_user, s.fuseki_password) if s.fuseki_user and s.fuseki_password else None
        r = requests.post(
            update_url,
            data=sparql.encode("utf-8"),
            headers=headers,
            timeout=20,
            auth=auth,
        )
        if 200 <= r.status_code < 300:
            return {"graphIri": graph, "label": label}
        raise HTTPException(status_code=500, detail=f"Fuseki returned {r.status_code}: {r.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to relabel ontology: {str(e)}")
