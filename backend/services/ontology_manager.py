"""
Ontology Manager Service for ODRAS
Handles JSON-based ontology editing, validation, and synchronization with Fuseki server.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import requests
from rdflib import OWL, RDF, RDFS, XSD, Graph, Literal, Namespace, URIRef
from rdflib.namespace import NamespaceManager
from SPARQLWrapper import GET
from SPARQLWrapper import JSON as SPARQL_JSON
from SPARQLWrapper import POST, SPARQLWrapper

from .config import Settings
from .namespace_uri_generator import NamespaceURIGenerator
from .resource_uri_service import ResourceURIService

logger = logging.getLogger(__name__)


class OntologyManager:
    """
    Manages ontology operations including:
    - JSON-based ontology editing
    - RDF serialization/deserialization
    - Fuseki server synchronization
    - Ontology validation
    """

    def __init__(self, settings: Settings, db_service=None):
        self.settings = settings
        self.fuseki_url = settings.fuseki_url
        self.fuseki_query_url = f"{self.fuseki_url}/query"
        self.fuseki_update_url = f"{self.fuseki_url}/update"

        # Initialize namespace URI generator
        self.namespace_generator = NamespaceURIGenerator(settings)

        # Initialize resource URI service for proper namespace-aware URIs
        if db_service:
            self.uri_service = ResourceURIService(settings, db_service)
        else:
            from .db import DatabaseService

            self.uri_service = ResourceURIService(settings, DatabaseService(settings))

        # Define ODRAS namespace using installation configuration
        self.base_uri = settings.installation_base_uri
        self.odras_ns = Namespace(f"{self.base_uri}/#")
        self.current_graph_uri = None
        self.current_project_id = None

        # Initialize RDF graph for working copy
        self.graph = Graph()
        self.graph.bind("odras", self.odras_ns)
        self.graph.bind("owl", OWL)
        self.graph.bind("rdfs", RDFS)

    def set_graph_context(self, graph_uri: str, project_id: Optional[str] = None):
        """Set the current graph context for operations."""
        self.current_graph_uri = graph_uri
        self.current_project_id = project_id

        # Update base_uri to use the graph URI as the namespace
        self.base_uri = graph_uri

        # Extract project ID from URI if not provided
        if not project_id and self.uri_service:
            self.current_project_id = self.uri_service.parse_project_from_uri(graph_uri)

    def get_current_ontology_json(self) -> Dict[str, Any]:
        """
        Retrieve the current ontology from Fuseki and convert to JSON format.

        Returns:
            Dict containing the ontology in JSON format
        """
        try:
            # Query all classes, properties, and individuals from Fuseki
            query = f"""
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX odras: <{self.base_uri}/ontology#>

            SELECT ?s ?p ?o WHERE {{
                ?s ?p ?o .
                FILTER(STRSTARTS(STR(?s), "{self.base_uri}/ontology"))
            }}
            """

            sparql = SPARQLWrapper(self.fuseki_query_url)
            sparql.setQuery(query)
            sparql.setReturnFormat(SPARQL_JSON)
            results = sparql.query().convert()

            # Convert SPARQL results to structured JSON
            ontology_json = self._sparql_results_to_json(results)
            return ontology_json

        except Exception as e:
            logger.error(f"Failed to retrieve ontology from Fuseki: {e}")
            # Return base ontology structure if Fuseki is unavailable
            return self._get_base_ontology_json()

    def get_ontology_json_by_graph(self, graph_iri: str) -> Dict[str, Any]:
        """
        Retrieve a specific ontology from Fuseki by graph IRI and convert to JSON format.

        Args:
            graph_iri: The IRI of the named graph to query

        Returns:
            Dict containing the ontology in JSON format
        """
        try:
            # Query specific named graph for classes, properties, and individuals
            query = f"""
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX odras: <{self.base_uri}/ontology#>

            SELECT ?s ?p ?o WHERE {{
                GRAPH <{graph_iri}> {{
                    ?s ?p ?o .
                }}
            }}
            """

            sparql = SPARQLWrapper(self.fuseki_query_url)
            sparql.setQuery(query)
            sparql.setReturnFormat(SPARQL_JSON)
            results = sparql.query().convert()

            # Convert SPARQL results to structured JSON
            ontology_json = self._sparql_results_to_json(results)
            return ontology_json

        except Exception as e:
            logger.error(f"Failed to retrieve ontology {graph_iri} from Fuseki: {e}")
            # Return base ontology structure if query fails
            return self._get_base_ontology_json()

    def update_ontology_from_json(
        self, ontology_json: Dict[str, Any], user_id: str = "system"
    ) -> Dict[str, Any]:
        """
        Update the ontology from JSON format and push to Fuseki.

        Args:
            ontology_json: The ontology in JSON format
            user_id: ID of the user making the change

        Returns:
            Dict containing update status and metadata
        """
        try:
            # Validate JSON structure
            validation_result = self._validate_ontology_json(ontology_json)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": "Invalid ontology JSON",
                    "validation_errors": validation_result["errors"],
                }

            # Convert JSON to RDF
            rdf_graph = self._json_to_rdf(ontology_json)

            # Create backup of current ontology
            backup_id = self._create_ontology_backup()

            # Clear current ontology in Fuseki
            self._clear_ontology_graph()

            # Upload new ontology to Fuseki
            turtle_content = rdf_graph.serialize(format="turtle")
            update_result = self._upload_rdf_to_fuseki(turtle_content)

            if update_result["success"]:
                # Log the change
                self._log_ontology_change(user_id, backup_id, "full_update")

                return {
                    "success": True,
                    "message": "Ontology updated successfully",
                    "backup_id": backup_id,
                    "triples_count": len(rdf_graph),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            else:
                # Restore backup if upload failed
                self._restore_ontology_backup(backup_id)
                return {
                    "success": False,
                    "error": "Failed to upload to Fuseki",
                    "details": update_result.get("error", "Unknown error"),
                }

        except Exception as e:
            logger.error(f"Failed to update ontology: {e}")
            return {"success": False, "error": f"Update failed: {str(e)}"}

    def add_class(self, class_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new class to the ontology.

        Args:
            class_data: Dict containing class information

        Returns:
            Dict containing operation result
        """
        try:
            # Debug: log the base_uri being used for entity generation
            logger.info(f"OntologyManager.add_class - base_uri: {self.base_uri}")
            logger.info(f"OntologyManager.add_class - current_graph_uri: {self.current_graph_uri}")
            logger.info(
                f"OntologyManager.add_class - current_project_id: {getattr(self, 'current_project_id', 'None')}"
            )

            # CRITICAL FIX: Use the current_graph_uri as the base for entity URIs if available
            if self.current_graph_uri:
                base_for_entities = self.current_graph_uri
                logger.info(f"Using current_graph_uri as entity base: {base_for_entities}")
            else:
                base_for_entities = self.base_uri
                logger.info(f"Using fallback base_uri as entity base: {base_for_entities}")

            class_uri = URIRef(f"{base_for_entities}#{class_data['name']}")

            # Check if class already exists
            if self._class_exists(class_uri):
                return {
                    "success": False,
                    "error": f"Class {class_data['name']} already exists",
                }

            # Create RDF triples for the new class
            triples = [
                (class_uri, RDF.type, OWL.Class),
                (
                    class_uri,
                    RDFS.label,
                    Literal(class_data.get("label", class_data["name"])),
                ),
            ]

            if class_data.get("comment"):
                triples.append((class_uri, RDFS.comment, Literal(class_data["comment"])))

            # Support multiple parents (multiple inheritance)
            if class_data.get("subclass_of"):
                # Handle both single parent (string) and multiple parents (list)
                parents = class_data["subclass_of"]
                if isinstance(parents, str):
                    parents = [parents]
                
                for parent in parents:
                    # Support both local and cross-project parents
                    if parent.startswith("http"):
                        # Full URI provided (cross-project reference)
                        parent_uri = URIRef(parent)
                    elif "#" in parent:
                        # Graph#class format
                        parent_uri = URIRef(parent)
                    else:
                        # Local class name
                        parent_uri = URIRef(f"{self.base_uri}#{parent}")
                    
                    triples.append((class_uri, RDFS.subClassOf, parent_uri))
                    
            # Add abstract class flag if specified
            if class_data.get("is_abstract", False):
                abstract_uri = URIRef(f"{self.base_uri}/isAbstract")
                triples.append((class_uri, abstract_uri, Literal(True)))

            # Add to Fuseki
            result = self._add_triples_to_fuseki(triples)

            if result["success"]:
                return {
                    "success": True,
                    "message": f"Class {class_data['name']} added successfully",
                    "class_uri": str(class_uri),
                }
            else:
                return result

        except Exception as e:
            logger.error(f"Failed to add class: {e}")
            return {"success": False, "error": f"Failed to add class: {str(e)}"}

    def add_property(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new property to the ontology.

        Args:
            property_data: Dict containing property information

        Returns:
            Dict containing operation result
        """
        try:
            prop_uri = URIRef(f"{self.base_uri}#{property_data['name']}")

            # Check if property already exists
            if self._property_exists(prop_uri):
                return {
                    "success": False,
                    "error": f"Property {property_data['name']} already exists",
                }

            # Determine property type
            prop_type = OWL.ObjectProperty
            if property_data.get("type") == "datatype":
                prop_type = OWL.DatatypeProperty
            elif property_data.get("type") == "annotation":
                prop_type = OWL.AnnotationProperty

            # Create RDF triples for the new property
            triples = [
                (prop_uri, RDF.type, prop_type),
                (
                    prop_uri,
                    RDFS.label,
                    Literal(property_data.get("label", property_data["name"])),
                ),
            ]

            if property_data.get("comment"):
                triples.append((prop_uri, RDFS.comment, Literal(property_data["comment"])))

            if property_data.get("domain"):
                domain_uri = URIRef(f"{self.base_uri}#{property_data['domain']}")
                triples.append((prop_uri, RDFS.domain, domain_uri))

            if property_data.get("range"):
                if property_data["type"] == "datatype":
                    range_uri = XSD[property_data["range"]]
                else:
                    range_uri = URIRef(f"{self.base_uri}#{property_data['range']}")
                triples.append((prop_uri, RDFS.range, range_uri))

            # Add inheritance system enhancements
            if property_data.get("default_value"):
                default_uri = URIRef(f"{self.base_uri}/defaultValue")
                triples.append((prop_uri, default_uri, Literal(property_data["default_value"])))
            
            if property_data.get("required", False):
                required_uri = URIRef(f"{self.base_uri}/required")
                triples.append((prop_uri, required_uri, Literal(True)))
            
            if property_data.get("units"):
                units_uri = URIRef(f"{self.base_uri}/units")
                triples.append((prop_uri, units_uri, Literal(property_data["units"])))
            
            if property_data.get("sort_order") is not None:
                sort_uri = URIRef(f"{self.base_uri}/sortOrder")
                triples.append((prop_uri, sort_uri, Literal(property_data["sort_order"], datatype=XSD.integer)))

            # Add SHACL constraints as custom properties (MVP approach)
            # Multiplicity constraints
            if property_data.get("min_count") is not None:
                min_count_uri = URIRef("http://odras.ai/ontology/minCount")
                triples.append((prop_uri, min_count_uri, Literal(property_data["min_count"], datatype=XSD.integer)))
            
            if property_data.get("max_count") is not None:
                max_count_uri = URIRef("http://odras.ai/ontology/maxCount")
                triples.append((prop_uri, max_count_uri, Literal(property_data["max_count"], datatype=XSD.integer)))
            
            # Datatype constraints
            if property_data.get("datatype_constraint"):
                datatype_uri = URIRef("http://odras.ai/ontology/datatypeConstraint")
                triples.append((prop_uri, datatype_uri, Literal(property_data["datatype_constraint"])))
            
            # Enumeration constraints  
            if property_data.get("enumeration_values"):
                enumeration_uri = URIRef("http://odras.ai/ontology/enumerationValues")
                # Store as JSON array string with proper escaping
                import json
                enum_json = json.dumps(property_data["enumeration_values"])
                # Escape for SPARQL - use Literal with proper datatype
                triples.append((prop_uri, enumeration_uri, Literal(enum_json, datatype=XSD.string)))

            # Add to Fuseki
            result = self._add_triples_to_fuseki(triples)

            if result["success"]:
                return {
                    "success": True,
                    "message": f"Property {property_data['name']} added successfully",
                    "property_uri": str(prop_uri),
                }
            else:
                return result

        except Exception as e:
            logger.error(f"Failed to add property: {e}")
            return {"success": False, "error": f"Failed to add property: {str(e)}"}

    def delete_entity(self, entity_name: str, entity_type: str) -> Dict[str, Any]:
        """
        Delete a class or property from the ontology.

        Args:
            entity_name: Name of the entity to delete
            entity_type: Type of entity ('class' or 'property')

        Returns:
            Dict containing operation result
        """
        try:
            entity_uri = URIRef(f"{self.base_uri}#{entity_name}")

            # Delete all triples where this entity is the subject
            delete_query_1 = f"""
            DELETE WHERE {{
                <{entity_uri}> ?p ?o .
            }}
            """
            
            # Delete all triples where this entity is the object
            delete_query_2 = f"""
            DELETE WHERE {{
                ?s ?p <{entity_uri}> .
            }}
            """

            # Execute both delete queries
            result1 = self._execute_sparql_update(delete_query_1)
            result2 = self._execute_sparql_update(delete_query_2)

            # Check if at least one succeeded
            if result1["success"] or result2["success"]:
                result = {"success": True}
            else:
                result = {"success": False, "error": f"Failed to delete: {result1.get('error', 'Unknown error')}"}

            if result["success"]:
                return {
                    "success": True,
                    "message": f"{entity_type.capitalize()} {entity_name} deleted successfully",
                }
            else:
                return result

        except Exception as e:
            logger.error(f"Failed to delete entity: {e}")
            return {"success": False, "error": f"Failed to delete entity: {str(e)}"}

    def get_ontology_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the current ontology.

        Returns:
            Dict containing ontology statistics
        """
        try:
            query = """
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

            SELECT
                (COUNT(DISTINCT ?class) AS ?classCount)
                (COUNT(DISTINCT ?objProp) AS ?objectPropertyCount)
                (COUNT(DISTINCT ?dataProp) AS ?datatypePropertyCount)
                (COUNT(DISTINCT ?individual) AS ?individualCount)
            WHERE {
                OPTIONAL { ?class a owl:Class }
                OPTIONAL { ?objProp a owl:ObjectProperty }
                OPTIONAL { ?dataProp a owl:DatatypeProperty }
                OPTIONAL { ?individual a ?someClass . ?someClass a owl:Class }
            }
            """

            sparql = SPARQLWrapper(self.fuseki_query_url)
            sparql.setQuery(query)
            sparql.setReturnFormat(SPARQL_JSON)
            results = sparql.query().convert()

            bindings = results["results"]["bindings"][0]

            return {
                "classes": int(bindings.get("classCount", {}).get("value", 0)),
                "object_properties": int(bindings.get("objectPropertyCount", {}).get("value", 0)),
                "datatype_properties": int(
                    bindings.get("datatypePropertyCount", {}).get("value", 0)
                ),
                "individuals": int(bindings.get("individualCount", {}).get("value", 0)),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to get ontology statistics: {e}")
            return {
                "classes": 0,
                "object_properties": 0,
                "datatype_properties": 0,
                "individuals": 0,
                "error": str(e),
            }

    # Private helper methods

    def _get_base_ontology_json(self) -> Dict[str, Any]:
        """Return the base ODRAS ontology structure."""
        return {
            "metadata": {
                "name": "ODRAS Base Ontology",
                "version": "1.0",
                "description": "Base ontology for Ontology-Driven Requirements Analysis System",
                "namespace": self.base_uri,
                "created": datetime.now(timezone.utc).isoformat(),
            },
            "classes": [
                {
                    "name": "Requirement",
                    "label": "Requirement",
                    "comment": "A statement that identifies a necessary attribute, capability, characteristic, or quality of a system",
                },
                {
                    "name": "Constraint",
                    "label": "Constraint",
                    "comment": "A restriction or limitation on system behavior or design",
                },
                {
                    "name": "Component",
                    "label": "Component",
                    "comment": "A modular part of a system that encapsulates specific functionality",
                },
                {
                    "name": "Interface",
                    "label": "Interface",
                    "comment": "A shared boundary between system components",
                },
                {
                    "name": "Function",
                    "label": "Function",
                    "comment": "A specific purpose or activity that the system must perform",
                },
                {
                    "name": "Process",
                    "label": "Process",
                    "comment": "A series of actions or steps taken to achieve a particular end",
                },
                {
                    "name": "Condition",
                    "label": "Condition",
                    "comment": "A circumstance or situation that must be met for a function to execute",
                },
                {
                    "name": "Stakeholder",
                    "label": "Stakeholder",
                    "comment": "An individual or organization with an interest in the system",
                },
                {
                    "name": "SourceDocument",
                    "label": "Source Document",
                    "comment": "A document from which requirements are extracted",
                },
            ],
            "object_properties": [
                {
                    "name": "constrained_by",
                    "label": "constrained by",
                    "domain": "Requirement",
                    "range": "Constraint",
                    "comment": "Links a requirement to constraints that apply to it",
                },
                {
                    "name": "satisfied_by",
                    "label": "satisfied by",
                    "domain": "Requirement",
                    "range": "Component",
                    "comment": "Links a requirement to components that satisfy it",
                },
                {
                    "name": "has_interface",
                    "label": "has interface",
                    "domain": "Component",
                    "range": "Interface",
                    "comment": "Links a component to its interfaces",
                },
                {
                    "name": "realizes",
                    "label": "realizes",
                    "domain": "Process",
                    "range": "Function",
                    "comment": "Links a process to the function it realizes",
                },
                {
                    "name": "triggered_by",
                    "label": "triggered by",
                    "domain": "Function",
                    "range": "Condition",
                    "comment": "Links a function to conditions that trigger it",
                },
                {
                    "name": "originates_from",
                    "label": "originates from",
                    "domain": "Requirement",
                    "range": "SourceDocument",
                    "comment": "Links a requirement to its source document",
                },
            ],
            "datatype_properties": [
                {
                    "name": "id",
                    "label": "identifier",
                    "domain": "Requirement",
                    "range": "string",
                    "comment": "Unique identifier for the requirement",
                },
                {
                    "name": "text",
                    "label": "text",
                    "domain": "Requirement",
                    "range": "string",
                    "comment": "The textual content of the requirement",
                },
                {
                    "name": "state",
                    "label": "state",
                    "domain": "Requirement",
                    "range": "string",
                    "comment": "Current state of the requirement (Draft, Reviewed, Approved)",
                },
                {
                    "name": "priority",
                    "label": "priority",
                    "domain": "Requirement",
                    "range": "string",
                    "comment": "Priority level of the requirement",
                },
                {
                    "name": "created_at",
                    "label": "created at",
                    "range": "dateTime",
                    "comment": "Timestamp when the entity was created",
                },
                {
                    "name": "updated_at",
                    "label": "updated at",
                    "range": "dateTime",
                    "comment": "Timestamp when the entity was last updated",
                },
            ],
        }

    def _sparql_results_to_json(self, results: Dict) -> Dict[str, Any]:
        """Convert SPARQL query results to structured JSON ontology format."""
        ontology_json = {
            "metadata": {
                "name": "ODRAS Ontology",
                "namespace": self.base_uri,
                "retrieved": datetime.now(timezone.utc).isoformat(),
            },
            "classes": [],
            "object_properties": [],
            "datatype_properties": [],
            "individuals": [],
        }

        # Group all triples by subject
        entities = {}
        for binding in results["results"]["bindings"]:
            subject = binding["s"]["value"]
            predicate = binding["p"]["value"]
            obj_value = binding["o"]["value"]

            if subject not in entities:
                entities[subject] = {}

            # Store multiple values for properties like rdfs:domain, rdfs:range
            if predicate not in entities[subject]:
                entities[subject][predicate] = []
            entities[subject][predicate].append(obj_value)

        # Extract name from URI (after # or last /)
        def extract_name(uri):
            if "#" in uri:
                return uri.split("#")[-1]
            return uri.split("/")[-1]

        # Convert entities to structured JSON
        for uri, props in entities.items():
            # Skip blank nodes and non-URI entities
            if uri.startswith("b") and uri[1:].isdigit():
                continue
            if uri.startswith("_:"):
                continue
            # Skip empty or invalid URIs
            if not uri or uri.strip() == "":
                continue

            entity_name = extract_name(uri)
            rdf_type = str(RDF.type)
            rdfs_label = str(RDFS.label)
            rdfs_comment = str(RDFS.comment)
            rdfs_domain = str(RDFS.domain)
            rdfs_range = str(RDFS.range)
            rdfs_subclass = str(RDFS.subClassOf)

            # Get entity type
            types = props.get(rdf_type, [])

            # Build common fields
            common_fields = {
                "name": entity_name,
                "uri": uri,
                "label": props.get(rdfs_label, [None])[0],
                "comment": props.get(rdfs_comment, [None])[0],
            }

            if str(OWL.Class) in types:
                # Class
                class_obj = {**common_fields}
                subclass_of_uris = props.get(rdfs_subclass, [])
                if subclass_of_uris:
                    class_obj["subclass_of"] = extract_name(subclass_of_uris[0])
                ontology_json["classes"].append(class_obj)

            elif str(OWL.ObjectProperty) in types:
                # Object Property
                prop_obj = {**common_fields}
                domain_uris = props.get(rdfs_domain, [])
                range_uris = props.get(rdfs_range, [])
                if domain_uris:
                    prop_obj["domain"] = extract_name(domain_uris[0])
                if range_uris:
                    prop_obj["range"] = extract_name(range_uris[0])
                
                # Extract SHACL constraints (MVP approach using custom properties)
                # Multiplicity constraints
                min_count_uris = props.get("http://odras.ai/ontology/minCount", [])
                max_count_uris = props.get("http://odras.ai/ontology/maxCount", [])
                if min_count_uris:
                    try:
                        prop_obj["min_count"] = int(min_count_uris[0])
                    except (ValueError, TypeError):
                        pass
                if max_count_uris:
                    try:
                        prop_obj["max_count"] = int(max_count_uris[0])
                    except (ValueError, TypeError):
                        pass
                
                # Datatype constraints
                datatype_constraint_uris = props.get("http://odras.ai/ontology/datatypeConstraint", [])
                if datatype_constraint_uris:
                    prop_obj["datatype_constraint"] = datatype_constraint_uris[0]
                
                # Enumeration constraints
                enumeration_uris = props.get("http://odras.ai/ontology/enumerationValues", [])
                if enumeration_uris:
                    try:
                        import json
                        enumeration_values = json.loads(enumeration_uris[0])
                        prop_obj["enumeration_values"] = enumeration_values
                    except (ValueError, TypeError, json.JSONDecodeError):
                        pass
                
                ontology_json["object_properties"].append(prop_obj)

            elif str(OWL.DatatypeProperty) in types:
                # Datatype Property
                prop_obj = {**common_fields}
                domain_uris = props.get(rdfs_domain, [])
                range_uris = props.get(rdfs_range, [])
                if domain_uris:
                    prop_obj["domain"] = extract_name(domain_uris[0])
                if range_uris:
                    # Keep full XSD datatype URIs
                    range_uri = range_uris[0]
                    if "XMLSchema#" in range_uri:
                        prop_obj["range"] = "xsd:" + extract_name(range_uri)
                    else:
                        prop_obj["range"] = extract_name(range_uri)
                
                # Extract SHACL constraints for datatype properties too
                # Multiplicity constraints
                min_count_uris = props.get("http://odras.ai/ontology/minCount", [])
                max_count_uris = props.get("http://odras.ai/ontology/maxCount", [])
                if min_count_uris:
                    try:
                        prop_obj["min_count"] = int(min_count_uris[0])
                    except (ValueError, TypeError):
                        pass
                if max_count_uris:
                    try:
                        prop_obj["max_count"] = int(max_count_uris[0])
                    except (ValueError, TypeError):
                        pass
                
                # Datatype constraints
                datatype_constraint_uris = props.get("http://odras.ai/ontology/datatypeConstraint", [])
                if datatype_constraint_uris:
                    prop_obj["datatype_constraint"] = datatype_constraint_uris[0]
                
                # Enumeration constraints
                enumeration_uris = props.get("http://odras.ai/ontology/enumerationValues", [])
                if enumeration_uris:
                    try:
                        import json
                        enumeration_values = json.loads(enumeration_uris[0])
                        prop_obj["enumeration_values"] = enumeration_values
                    except (ValueError, TypeError, json.JSONDecodeError):
                        pass
                        
                ontology_json["datatype_properties"].append(prop_obj)

        return ontology_json

    def _validate_ontology_json(self, ontology_json: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the structure and content of ontology JSON."""
        errors = []

        # Check required top-level keys
        required_keys = [
            "metadata",
            "classes",
            "object_properties",
            "datatype_properties",
        ]
        for key in required_keys:
            if key not in ontology_json:
                errors.append(f"Missing required key: {key}")

        # Validate classes
        if "classes" in ontology_json:
            for i, cls in enumerate(ontology_json["classes"]):
                if "name" not in cls:
                    errors.append(f"Class at index {i} missing 'name' field")

        # Validate properties
        if "object_properties" in ontology_json:
            for i, prop in enumerate(ontology_json["object_properties"]):
                if "name" not in prop:
                    errors.append(f"Object property at index {i} missing 'name' field")

        return {"valid": len(errors) == 0, "errors": errors}

    def _json_to_rdf(self, ontology_json: Dict[str, Any]) -> Graph:
        """Convert JSON ontology to RDF graph."""
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"🔍 JSON_TO_RDF: Converting JSON ontology with keys: {list(ontology_json.keys())}")
        logger.info(f"🔍 JSON_TO_RDF: Classes count: {len(ontology_json.get('classes', []))}")
        logger.info(f"🔍 JSON_TO_RDF: Object properties count: {len(ontology_json.get('object_properties', []))}")
        logger.info(f"🔍 JSON_TO_RDF: Datatype properties count: {len(ontology_json.get('datatype_properties', []))}")

        graph = Graph()
        graph.bind("odras", self.odras_ns)
        graph.bind("owl", OWL)
        graph.bind("rdfs", RDFS)
        graph.bind("skos", URIRef("http://www.w3.org/2004/02/skos/core#"))
        graph.bind("dc", URIRef("http://purl.org/dc/elements/1.1/"))
        graph.bind("dcterms", URIRef("http://purl.org/dc/terms/"))
        graph.bind("xsd", XSD)

        # Add ontology metadata
        ontology_uri = URIRef(self.base_uri)
        graph.add((ontology_uri, RDF.type, OWL.Ontology))

        if "metadata" in ontology_json:
            metadata = ontology_json["metadata"]
            if "name" in metadata:
                graph.add((ontology_uri, RDFS.label, Literal(metadata["name"])))
            if "description" in metadata:
                graph.add((ontology_uri, RDFS.comment, Literal(metadata["description"])))

        # Add classes with comprehensive attribute support
        logger.info(f"🔍 JSON_TO_RDF: Processing {len(ontology_json.get('classes', []))} classes")
        for i, cls in enumerate(ontology_json.get("classes", [])):
            logger.info(f"🔍 JSON_TO_RDF: Processing class {i+1}: {cls.get('name', 'Unknown')} with keys: {list(cls.keys())}")

            try:
                class_uri = URIRef(f"{self.base_uri}#{cls['name']}")
                graph.add((class_uri, RDF.type, OWL.Class))
                graph.add((class_uri, RDFS.label, Literal(cls.get("label", cls["name"]))))

                # Standard ontological properties
                if "comment" in cls and cls["comment"]:
                    graph.add((class_uri, RDFS.comment, Literal(cls["comment"])))
                    logger.info(f"🔍 JSON_TO_RDF: Added comment for {cls['name']}")
                if "definition" in cls and cls["definition"]:
                    graph.add((class_uri, URIRef("http://www.w3.org/2004/02/skos/core#definition"), Literal(cls["definition"])))
                    logger.info(f"🔍 JSON_TO_RDF: Added definition for {cls['name']}")
                if "example" in cls and cls["example"]:
                    graph.add((class_uri, URIRef("http://www.w3.org/2004/02/skos/core#example"), Literal(cls["example"])))
                    logger.info(f"🔍 JSON_TO_RDF: Added example for {cls['name']}")
                if "identifier" in cls and cls["identifier"]:
                    graph.add((class_uri, URIRef("http://purl.org/dc/elements/1.1/identifier"), Literal(cls["identifier"])))

                # Class relationships
                if "subclassOf" in cls and cls["subclassOf"]:
                    if cls["subclassOf"].startswith("http"):
                        graph.add((class_uri, RDFS.subClassOf, URIRef(cls["subclassOf"])))
                    else:
                        parent_uri = URIRef(f"{self.base_uri}#{cls['subclassOf']}")
                        graph.add((class_uri, RDFS.subClassOf, parent_uri))
                if "equivalentClass" in cls and cls["equivalentClass"]:
                    equiv_uri = URIRef(cls["equivalentClass"]) if cls["equivalentClass"].startswith("http") else URIRef(f"{self.base_uri}#{cls['equivalentClass']}")
                    graph.add((class_uri, OWL.equivalentClass, equiv_uri))
                if "disjointWith" in cls and cls["disjointWith"]:
                    disjoint_uri = URIRef(cls["disjointWith"]) if cls["disjointWith"].startswith("http") else URIRef(f"{self.base_uri}#{cls['disjointWith']}")
                    graph.add((class_uri, OWL.disjointWith, disjoint_uri))

                # Metadata properties
                if "creator" in cls and cls["creator"]:
                    graph.add((class_uri, URIRef("http://purl.org/dc/elements/1.1/creator"), Literal(cls["creator"])))
                    logger.info(f"🔍 JSON_TO_RDF: Added creator for {cls['name']}: {cls['creator']}")
                if "created_date" in cls and cls["created_date"]:
                    graph.add((class_uri, URIRef("http://purl.org/dc/elements/1.1/date"), Literal(cls["created_date"])))
                if "last_modified_by" in cls and cls["last_modified_by"]:
                    graph.add((class_uri, URIRef("http://purl.org/dc/elements/1.1/contributor"), Literal(cls["last_modified_by"])))
                if "last_modified_date" in cls and cls["last_modified_date"]:
                    graph.add((class_uri, URIRef("http://purl.org/dc/terms/modified"), Literal(cls["last_modified_date"])))

                # Custom properties
                if "priority" in cls and cls["priority"]:
                    graph.add((class_uri, URIRef(f"{self.base_uri}#priority"), Literal(cls["priority"])))
                    logger.info(f"🔍 JSON_TO_RDF: Added priority for {cls['name']}: {cls['priority']}")
                if "status" in cls and cls["status"]:
                    graph.add((class_uri, URIRef(f"{self.base_uri}#status"), Literal(cls["status"])))
                    logger.info(f"🔍 JSON_TO_RDF: Added status for {cls['name']}: {cls['status']}")

                logger.info(f"✅ JSON_TO_RDF: Successfully processed class {cls['name']}")

            except Exception as e:
                logger.error(f"❌ JSON_TO_RDF: Error processing class {cls.get('name', 'Unknown')}: {e}")

        # Add object properties with comprehensive attribute support
        for prop in ontology_json.get("object_properties", []):
            prop_uri = URIRef(f"{self.base_uri}#{prop['name']}")
            graph.add((prop_uri, RDF.type, OWL.ObjectProperty))
            graph.add((prop_uri, RDFS.label, Literal(prop.get("label", prop["name"]))))

            # Standard ontological properties
            if "comment" in prop and prop["comment"]:
                graph.add((prop_uri, RDFS.comment, Literal(prop["comment"])))
            if "definition" in prop and prop["definition"]:
                graph.add((prop_uri, URIRef("http://www.w3.org/2004/02/skos/core#definition"), Literal(prop["definition"])))
            if "example" in prop and prop["example"]:
                graph.add((prop_uri, URIRef("http://www.w3.org/2004/02/skos/core#example"), Literal(prop["example"])))
            if "identifier" in prop and prop["identifier"]:
                graph.add((prop_uri, URIRef("http://purl.org/dc/elements/1.1/identifier"), Literal(prop["identifier"])))

            # Property relationships
            if "domain" in prop and prop["domain"]:
                domain_uri = URIRef(f"{self.base_uri}#{prop['domain']}")
                graph.add((prop_uri, RDFS.domain, domain_uri))
            if "range" in prop and prop["range"]:
                range_uri = URIRef(f"{self.base_uri}#{prop['range']}")
                graph.add((prop_uri, RDFS.range, range_uri))
            if "inverseOf" in prop and prop["inverseOf"]:
                inverse_uri = URIRef(prop["inverseOf"]) if prop["inverseOf"].startswith("http") else URIRef(f"{self.base_uri}#{prop['inverseOf']}")
                graph.add((prop_uri, OWL.inverseOf, inverse_uri))
            if "subPropertyOf" in prop and prop["subPropertyOf"]:
                parent_uri = URIRef(prop["subPropertyOf"]) if prop["subPropertyOf"].startswith("http") else URIRef(f"{self.base_uri}#{prop['subPropertyOf']}")
                graph.add((prop_uri, RDFS.subPropertyOf, parent_uri))
            if "equivalentProperty" in prop and prop["equivalentProperty"]:
                equiv_uri = URIRef(prop["equivalentProperty"]) if prop["equivalentProperty"].startswith("http") else URIRef(f"{self.base_uri}#{prop['equivalentProperty']}")
                graph.add((prop_uri, OWL.equivalentProperty, equiv_uri))

            # Metadata properties
            if "creator" in prop and prop["creator"]:
                graph.add((prop_uri, URIRef("http://purl.org/dc/elements/1.1/creator"), Literal(prop["creator"])))
            if "created_date" in prop and prop["created_date"]:
                graph.add((prop_uri, URIRef("http://purl.org/dc/elements/1.1/date"), Literal(prop["created_date"])))
            if "last_modified_by" in prop and prop["last_modified_by"]:
                graph.add((prop_uri, URIRef("http://purl.org/dc/elements/1.1/contributor"), Literal(prop["last_modified_by"])))
            if "last_modified_date" in prop and prop["last_modified_date"]:
                graph.add((prop_uri, URIRef("http://purl.org/dc/terms/modified"), Literal(prop["last_modified_date"])))

            # Property characteristics
            if "functional" in prop and prop["functional"]:
                graph.add((prop_uri, RDF.type, OWL.FunctionalProperty))
            if "inverse_functional" in prop and prop["inverse_functional"]:
                graph.add((prop_uri, RDF.type, OWL.InverseFunctionalProperty))

        # Add datatype properties with comprehensive attribute support
        for prop in ontology_json.get("datatype_properties", []):
            prop_uri = URIRef(f"{self.base_uri}#{prop['name']}")
            graph.add((prop_uri, RDF.type, OWL.DatatypeProperty))
            graph.add((prop_uri, RDFS.label, Literal(prop.get("label", prop["name"]))))

            # Standard ontological properties
            if "comment" in prop and prop["comment"]:
                graph.add((prop_uri, RDFS.comment, Literal(prop["comment"])))
            if "definition" in prop and prop["definition"]:
                graph.add((prop_uri, URIRef("http://www.w3.org/2004/02/skos/core#definition"), Literal(prop["definition"])))
            if "example" in prop and prop["example"]:
                graph.add((prop_uri, URIRef("http://www.w3.org/2004/02/skos/core#example"), Literal(prop["example"])))
            if "identifier" in prop and prop["identifier"]:
                graph.add((prop_uri, URIRef("http://purl.org/dc/elements/1.1/identifier"), Literal(prop["identifier"])))

            # Property relationships
            if "domain" in prop and prop["domain"]:
                domain_uri = URIRef(f"{self.base_uri}#{prop['domain']}")
                graph.add((prop_uri, RDFS.domain, domain_uri))
            if "range" in prop and prop["range"]:
                if prop["range"] in [
                    "string",
                    "integer",
                    "float",
                    "boolean",
                    "dateTime",
                ]:
                    range_uri = XSD[prop["range"]]
                else:
                    range_uri = URIRef(f"{self.base_uri}#{prop['range']}")
                graph.add((prop_uri, RDFS.range, range_uri))
            if "subPropertyOf" in prop and prop["subPropertyOf"]:
                parent_uri = URIRef(prop["subPropertyOf"]) if prop["subPropertyOf"].startswith("http") else URIRef(f"{self.base_uri}#{prop['subPropertyOf']}")
                graph.add((prop_uri, RDFS.subPropertyOf, parent_uri))
            if "equivalentProperty" in prop and prop["equivalentProperty"]:
                equiv_uri = URIRef(prop["equivalentProperty"]) if prop["equivalentProperty"].startswith("http") else URIRef(f"{self.base_uri}#{prop['equivalentProperty']}")
                graph.add((prop_uri, OWL.equivalentProperty, equiv_uri))

            # Metadata properties
            if "creator" in prop and prop["creator"]:
                graph.add((prop_uri, URIRef("http://purl.org/dc/elements/1.1/creator"), Literal(prop["creator"])))
            if "created_date" in prop and prop["created_date"]:
                graph.add((prop_uri, URIRef("http://purl.org/dc/elements/1.1/date"), Literal(prop["created_date"])))
            if "last_modified_by" in prop and prop["last_modified_by"]:
                graph.add((prop_uri, URIRef("http://purl.org/dc/elements/1.1/contributor"), Literal(prop["last_modified_by"])))
            if "last_modified_date" in prop and prop["last_modified_date"]:
                graph.add((prop_uri, URIRef("http://purl.org/dc/terms/modified"), Literal(prop["last_modified_date"])))

            # Property characteristics
            if "functional" in prop and prop["functional"]:
                graph.add((prop_uri, RDF.type, OWL.FunctionalProperty))

        return graph

    def _clear_ontology_graph(self):
        """Clear the current ontology graph in Fuseki."""
        clear_query = f"""
        DELETE WHERE {{
            ?s ?p ?o .
            FILTER(STRSTARTS(STR(?s), "{self.base_uri}"))
        }}
        """
        return self._execute_sparql_update(clear_query)

    def _upload_rdf_to_fuseki(self, turtle_content: str) -> Dict[str, Any]:
        """Upload RDF content to Fuseki."""
        try:
            # Parse the turtle content into an RDF graph
            graph = Graph()
            graph.parse(data=turtle_content, format="turtle")

            # Convert to SPARQL INSERT DATA format
            insert_data = []
            for s, p, o in graph:
                if isinstance(o, Literal):
                    # Handle literals with proper escaping
                    if o.datatype:
                        insert_data.append(f'<{s}> <{p}> "{o}"^^<{o.datatype}> .')
                    elif o.language:
                        insert_data.append(f'<{s}> <{p}> "{o}"@{o.language} .')
                    else:
                        insert_data.append(f'<{s}> <{p}> "{o}" .')
                else:
                    insert_data.append(f"<{s}> <{p}> <{o}> .")

            if not insert_data:
                return {"success": True, "message": "No data to insert"}

            # Build SPARQL query with proper prefixes
            prefixes = []
            for prefix, namespace in graph.namespaces():
                prefixes.append(f"PREFIX {prefix}: <{namespace}>")

            prefixes_block = "\n".join(prefixes)
            data_block = "\n                ".join(insert_data)

            query = f"""
            {prefixes_block}
            INSERT DATA {{
                {data_block}
            }}
            """

            sparql = SPARQLWrapper(self.fuseki_update_url)
            sparql.setMethod(POST)
            sparql.setQuery(query)
            sparql.query()

            return {"success": True}

        except Exception as e:
            logger.error(f"Failed to upload RDF to Fuseki: {e}")
            return {"success": False, "error": str(e)}

    def _add_triples_to_fuseki(self, triples: List[tuple]) -> Dict[str, Any]:
        """Add individual triples to Fuseki."""
        try:
            # Convert triples to SPARQL INSERT format
            insert_data = []
            for s, p, o in triples:
                # Validate URIs are not empty or None
                if not s or not p:
                    logger.warning(f"Skipping triple with empty subject or predicate: {s}, {p}, {o}")
                    continue
                    
                if isinstance(o, Literal):
                    # Properly escape quotes in literal values for SPARQL
                    escaped_value = str(o).replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
                    if o.datatype:
                        insert_data.append(f'<{s}> <{p}> "{escaped_value}"^^<{o.datatype}> .')
                    elif o.language:
                        insert_data.append(f'<{s}> <{p}> "{escaped_value}"@{o.language} .')
                    else:
                        insert_data.append(f'<{s}> <{p}> "{escaped_value}" .')
                else:
                    # Validate object URI is not empty
                    if not o:
                        logger.warning(f"Skipping triple with empty object: {s}, {p}, {o}")
                        continue
                    insert_data.append(f"<{s}> <{p}> <{o}> .")

            if not insert_data:
                logger.warning("No valid triples to insert")
                return {"success": True, "message": "No valid triples to insert"}

            # Use current graph context if available - FIX: Use proper newline formatting
            if self.current_graph_uri:
                query = f"""
                INSERT DATA {{
                    GRAPH <{self.current_graph_uri}> {{
                        {chr(10).join(insert_data)}
                    }}
                }}
                """
            else:
                query = f"""
                INSERT DATA {{
                    {chr(10).join(insert_data)}
                }}
                """

            logger.info(f"🔍 Generated SPARQL query:\n{query}")
            return self._execute_sparql_update(query)

        except Exception as e:
            logger.error(f"Failed to add triples to Fuseki: {e}")
            return {"success": False, "error": str(e)}

    def _execute_sparql_update(self, query: str) -> Dict[str, Any]:
        """Execute a SPARQL UPDATE query."""
        try:
            logger.debug(f"Executing SPARQL UPDATE: {query}")
            sparql = SPARQLWrapper(self.fuseki_update_url)
            sparql.setMethod(POST)
            sparql.setQuery(query)
            result = sparql.query()
            logger.debug(f"SPARQL UPDATE result: {result}")

            return {"success": True}

        except Exception as e:
            logger.error(f"SPARQL UPDATE failed: {e}")
            logger.error(f"Query was: {query}")
            return {"success": False, "error": str(e)}

    def _class_exists(self, class_uri: URIRef) -> bool:
        """Check if a class already exists in the ontology."""
        query = f"""
        ASK {{ <{class_uri}> a owl:Class }}
        """
        # Implementation would check Fuseki
        return False  # Simplified for now

    def _property_exists(self, prop_uri: URIRef) -> bool:
        """Check if a property already exists in the ontology."""
        query = f"""
        ASK {{
            {{ <{prop_uri}> a owl:ObjectProperty }} UNION
            {{ <{prop_uri}> a owl:DatatypeProperty }} UNION
            {{ <{prop_uri}> a owl:AnnotationProperty }}
        }}
        """
        # Implementation would check Fuseki
        return False  # Simplified for now

    def _create_ontology_backup(self) -> str:
        """Create a backup of the current ontology."""
        backup_id = str(uuid.uuid4())
        # Implementation would save current state
        return backup_id

    def _restore_ontology_backup(self, backup_id: str):
        """Restore ontology from backup."""
        # Implementation would restore from backup
        pass

    def _log_ontology_change(self, user_id: str, backup_id: str, change_type: str):
        """Log ontology changes for audit trail."""
        # Implementation would log to database
        pass

    def get_layout_by_graph(self, graph_iri: str) -> Dict[str, Any]:
        """
        Retrieve layout data for a specific ontology graph.

        Args:
            graph_iri: The IRI of the named graph to retrieve layout for

        Returns:
            Dict containing layout data (nodes, edges, zoom, pan)
        """
        try:
            # Query for layout data in a separate layout graph
            layout_graph_iri = f"{graph_iri}#layout"
            query = f"""
            PREFIX layout: <{self.base_uri}/layout#>

            SELECT ?nodes ?edges ?zoom ?pan WHERE {{
                GRAPH <{layout_graph_iri}> {{
                    ?layout layout:nodes ?nodes ;
                            layout:edges ?edges ;
                            layout:zoom ?zoom ;
                            layout:pan ?pan .
                }}
            }}
            """

            sparql = SPARQLWrapper(self.fuseki_query_url)
            sparql.setQuery(query)
            sparql.setReturnFormat(SPARQL_JSON)
            results = sparql.query().convert()

            if results["results"]["bindings"]:
                binding = results["results"]["bindings"][0]
                return {
                    "graphIri": graph_iri,
                    "nodes": json.loads(binding.get("nodes", {}).get("value", "[]")),
                    "edges": json.loads(binding.get("edges", {}).get("value", "[]")),
                    "zoom": float(binding.get("zoom", {}).get("value", 1.0)),
                    "pan": json.loads(binding.get("pan", {}).get("value", '{"x": 0, "y": 0}')),
                }
            else:
                # Return default layout if none exists
                return {
                    "graphIri": graph_iri,
                    "nodes": [],
                    "edges": [],
                    "zoom": 1.0,
                    "pan": {"x": 0, "y": 0},
                }

        except Exception as e:
            logger.error(f"Failed to retrieve layout for {graph_iri}: {e}")
            # Return default layout on error
            return {
                "graphIri": graph_iri,
                "nodes": [],
                "edges": [],
                "zoom": 1.0,
                "pan": {"x": 0, "y": 0},
            }

    def save_layout_by_graph(self, graph_iri: str, layout_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save layout data for a specific ontology graph.

        Args:
            graph_iri: The IRI of the named graph to save layout for
            layout_data: Layout data including node positions, zoom, and pan

        Returns:
            Dict containing save operation result
        """
        try:
            layout_graph_iri = f"{graph_iri}#layout"
            layout_id = str(uuid.uuid4())

            # Clear existing layout data
            clear_query = f"""
            DELETE WHERE {{
                GRAPH <{layout_graph_iri}> {{
                    ?s ?p ?o .
                }}
            }}
            """

            # Insert new layout data
            nodes_json = json.dumps(layout_data.get("nodes", [])).replace('"', '\\"')
            edges_json = json.dumps(layout_data.get("edges", [])).replace('"', '\\"')
            zoom_value = layout_data.get("zoom", 1.0)
            pan_json = json.dumps(layout_data.get("pan", {"x": 0, "y": 0})).replace('"', '\\"')

            insert_query = f"""
            INSERT DATA {{
                GRAPH <{layout_graph_iri}> {{
                    <{layout_graph_iri}#{layout_id}> <{self.base_uri}/layout#nodes> "{nodes_json}" ;
                                                    <{self.base_uri}/layout#edges> "{edges_json}" ;
                                                    <{self.base_uri}/layout#zoom> "{zoom_value}"^^<http://www.w3.org/2001/XMLSchema#float> ;
                                                    <{self.base_uri}/layout#pan> "{pan_json}" .
                }}
            }}
            """

            # Execute clear and insert
            clear_result = self._execute_sparql_update(clear_query)
            if not clear_result["success"]:
                return {"success": False, "error": "Failed to clear existing layout"}

            insert_result = self._execute_sparql_update(insert_query)
            if insert_result["success"]:
                return {
                    "success": True,
                    "message": f"Layout saved successfully for {graph_iri}",
                    "layout_id": layout_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            else:
                return {"success": False, "error": "Failed to save layout data"}

        except Exception as e:
            logger.error(f"Failed to save layout for {graph_iri}: {e}")
            return {"success": False, "error": f"Save failed: {str(e)}"}

    def get_named_views_by_graph(self, graph_iri: str) -> List[Dict[str, Any]]:
        """
        Retrieve named views data for a specific ontology graph.

        Args:
            graph_iri: The IRI of the named graph to retrieve named views for

        Returns:
            List of named views data for the ontology
        """
        try:
            # Query for named views data in a separate named-views graph
            views_graph_iri = f"{graph_iri}#named-views"
            query = f"""
            PREFIX views: <{self.base_uri}/views#>

            SELECT ?views WHERE {{
                GRAPH <{views_graph_iri}> {{
                    ?viewsData views:data ?views .
                }}
            }}
            """

            sparql = SPARQLWrapper(self.fuseki_query_url)
            sparql.setQuery(query)
            sparql.setReturnFormat(SPARQL_JSON)
            results = sparql.query().convert()

            if results["results"]["bindings"]:
                binding = results["results"]["bindings"][0]
                views_json = binding.get("views", {}).get("value", "[]")
                return json.loads(views_json)
            else:
                # Return empty array if no named views exist
                return []

        except Exception as e:
            logger.error(f"Failed to retrieve named views for {graph_iri}: {e}")
            # Return empty array on error
            return []

    def save_named_views_by_graph(self, graph_iri: str, named_views_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Save named views data for a specific ontology graph.

        Args:
            graph_iri: The IRI of the named graph to save named views for
            named_views_data: Named views data including view definitions and settings

        Returns:
            Dict containing save operation result
        """
        try:
            views_graph_iri = f"{graph_iri}#named-views"
            views_id = str(uuid.uuid4())

            # Clear existing named views data
            clear_query = f"""
            DELETE WHERE {{
                GRAPH <{views_graph_iri}> {{
                    ?s ?p ?o .
                }}
            }}
            """

            # Insert new named views data
            views_json = json.dumps(named_views_data).replace('"', '\\"')

            insert_query = f"""
            INSERT DATA {{
                GRAPH <{views_graph_iri}> {{
                    <{views_graph_iri}#{views_id}> <{self.base_uri}/views#data> "{views_json}" .
                }}
            }}
            """

            # Execute clear and insert
            clear_result = self._execute_sparql_update(clear_query)
            if not clear_result["success"]:
                return {"success": False, "error": "Failed to clear existing named views"}

            insert_result = self._execute_sparql_update(insert_query)
            if insert_result["success"]:
                return {
                    "success": True,
                    "message": f"Named views saved successfully for {graph_iri}",
                    "views_id": views_id,
                    "views_count": len(named_views_data),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            else:
                return {"success": False, "error": "Failed to save named views data"}

        except Exception as e:
            logger.error(f"Failed to save named views for {graph_iri}: {e}")
            return {"success": False, "error": f"Save failed: {str(e)}"}

    def mint_unique_iri(self, base_name: str, entity_type: str, graph_iri: str = None) -> str:
        """
        Mint a unique IRI for a new entity, ensuring no conflicts exist.

        Args:
            base_name: Base name for the entity
            entity_type: Type of entity ('class', 'objectProperty', 'datatypeProperty')
            graph_iri: Optional graph IRI to check within

        Returns:
            Unique IRI string
        """
        # Clean the base name to be IRI-safe
        safe_name = self._sanitize_iri_name(base_name)

        # Use the graph IRI as base if provided, otherwise use default
        if graph_iri:
            base_uri = graph_iri
        else:
            base_uri = self.base_uri

        # Try the base name first
        candidate_iri = f"{base_uri}#{safe_name}"
        if not self._iri_exists(candidate_iri, entity_type, graph_iri):
            return candidate_iri

        # If base name exists, try with numbers
        counter = 1
        while counter < 1000:  # Prevent infinite loop
            candidate_iri = f"{base_uri}#{safe_name}_{counter}"
            if not self._iri_exists(candidate_iri, entity_type, graph_iri):
                return candidate_iri
            counter += 1

        # Fallback to UUID if all else fails
        unique_id = str(uuid.uuid4())[:8]
        return f"{base_uri}#{safe_name}_{unique_id}"

    def _sanitize_iri_name(self, name: str) -> str:
        """
        Sanitize a name to be safe for use in IRIs.

        Args:
            name: Raw name to sanitize

        Returns:
            Sanitized name safe for IRI use
        """
        # Remove or replace problematic characters
        import re

        # Replace spaces and special chars with underscores
        sanitized = re.sub(r"[^\w\-]", "_", name)
        # Remove multiple consecutive underscores
        sanitized = re.sub(r"_+", "_", sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip("_")
        # Ensure it starts with a letter or underscore
        if sanitized and not re.match(r"^[a-zA-Z_]", sanitized):
            sanitized = f"_{sanitized}"
        # Ensure it's not empty
        if not sanitized:
            sanitized = "entity"
        return sanitized

    def _iri_exists(self, iri: str, entity_type: str, graph_iri: str = None) -> bool:
        """
        Check if an IRI already exists in the ontology.

        Args:
            iri: IRI to check
            entity_type: Type of entity to check for
            graph_iri: Optional graph IRI to check within

        Returns:
            True if IRI exists, False otherwise
        """
        try:
            # Map entity types to RDF types
            type_mapping = {
                "class": str(OWL.Class),
                "objectProperty": str(OWL.ObjectProperty),
                "datatypeProperty": str(OWL.DatatypeProperty),
                "annotationProperty": str(OWL.AnnotationProperty),
            }

            rdf_type = type_mapping.get(entity_type, str(OWL.Class))

            # Build query
            if graph_iri:
                query = f"""
                ASK {{
                    GRAPH <{graph_iri}> {{
                        <{iri}> a <{rdf_type}> .
                    }}
                }}
                """
            else:
                query = f"""
                ASK {{
                    <{iri}> a <{rdf_type}> .
                }}
                """

            sparql = SPARQLWrapper(self.fuseki_query_url)
            sparql.setQuery(query)
            sparql.setReturnFormat(SPARQL_JSON)
            result = sparql.query().convert()

            return result.get("boolean", False)

        except Exception as e:
            logger.warn(f"Error checking if IRI exists: {e}")
            return False  # Assume it doesn't exist if we can't check

    def validate_iri_integrity(self, graph_iri: str) -> Dict[str, Any]:
        """
        Validate IRI integrity for an ontology graph.

        Args:
            graph_iri: Graph IRI to validate

        Returns:
            Validation results with warnings and errors
        """
        try:
            query = f"""
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

            SELECT ?s ?p ?o WHERE {{
                GRAPH <{graph_iri}> {{
                    ?s ?p ?o .
                }}
            }}
            """

            sparql = SPARQLWrapper(self.fuseki_query_url)
            sparql.setQuery(query)
            sparql.setReturnFormat(SPARQL_JSON)
            results = sparql.query().convert()

            warnings = []
            errors = []

            # Check for duplicate labels
            labels = {}
            for binding in results["results"]["bindings"]:
                if binding["p"]["value"] == str(RDFS.label):
                    label = binding["o"]["value"]
                    subject = binding["s"]["value"]
                    if label in labels:
                        warnings.append(
                            f"Duplicate label '{label}' found for {subject} and {labels[label]}"
                        )
                    else:
                        labels[label] = subject

            # Check for missing labels
            entities_without_labels = set()
            for binding in results["results"]["bindings"]:
                subject = binding["s"]["value"]
                if binding["p"]["value"] == str(RDF.type):
                    entities_without_labels.add(subject)

            for binding in results["results"]["bindings"]:
                if binding["p"]["value"] == str(RDFS.label):
                    subject = binding["s"]["value"]
                    entities_without_labels.discard(subject)

            for entity in entities_without_labels:
                warnings.append(f"Entity {entity} has no rdfs:label")

            return {
                "valid": len(errors) == 0,
                "warnings": warnings,
                "errors": errors,
                "entity_count": len(
                    set(binding["s"]["value"] for binding in results["results"]["bindings"])
                ),
            }

        except Exception as e:
            logger.error(f"Error validating IRI integrity: {e}")
            return {
                "valid": False,
                "warnings": [],
                "errors": [f"Validation failed: {str(e)}"],
                "entity_count": 0,
            }

    def get_class_properties_with_inherited(self, class_name: str, graph_iri: str) -> Dict[str, Any]:
        """
        Get all properties including inherited from multiple parents across projects.
        Handles multiple inheritance, property merging, and diamond pattern detection.
        """
        properties = {}  # Use dict to merge duplicates by name
        visited = set()  # Track visited classes for diamond detection
        inheritance_paths = {}  # Track paths to detect diamonds
        conflicts = []  # Track property conflicts
        
        # CRITICAL FIX: First resolve class name to actual URI in the graph
        actual_class_uri = self._resolve_class_name_to_uri(class_name, graph_iri)
        if not actual_class_uri:
            logger.warning(f"Could not resolve class name '{class_name}' to URI in graph {graph_iri}")
            return {
                'properties': [],
                'conflicts': [],
                'error': f"Class '{class_name}' not found in graph"
            }
        
        logger.info(f"🔍 Resolved class '{class_name}' to URI: {actual_class_uri}")
        
        def collect_properties(cls_name, cls_graph, path=[]):
            # Check for cycles/diamonds
            class_key = f"{cls_graph}#{cls_name}"
            if class_key in visited:
                # Check if this creates a diamond pattern
                if any(ancestor in path for ancestor in inheritance_paths.get(class_key, [])):
                    raise ValueError(f"Diamond inheritance detected via {cls_name}")
                return
            
            visited.add(class_key)
            inheritance_paths[class_key] = path[:]
            
            # Get direct properties for this class using actual URI
            direct_props = self._get_direct_properties_by_uri(cls_name, cls_graph)
            logger.info(f"🔍 Found {len(direct_props)} direct properties for {cls_name}")
            
            # Add/merge properties
            for prop in direct_props:
                prop_key = prop['name']
                if prop_key in properties:
                    # Property already exists - handle range conflicts gracefully
                    existing_range = properties[prop_key].get('range', '')
                    new_range = prop.get('range', '')
                    
                    if existing_range != new_range and existing_range and new_range:
                        conflict_info = {
                            'property': prop_key,
                            'existing_range': existing_range,
                            'new_range': new_range,
                            'existing_source': properties[prop_key].get('inheritedFrom', 'unknown'),
                            'new_source': path[0] if path else 'direct'
                        }
                        conflicts.append(conflict_info)
                        
                        # GRACEFUL CONFLICT RESOLUTION: Choose most specific range
                        chosen_range = self._choose_better_range(existing_range, new_range)
                        logger.info(f"🔍 Range conflict for '{prop_key}': {existing_range} vs {new_range} → chose {chosen_range}")
                        
                        # Update the property with the better range
                        properties[prop_key]['range'] = chosen_range
                        properties[prop_key]['conflict_resolved'] = True
                        # Don't throw error - continue processing
                else:
                    # Add new property
                    properties[prop_key] = {
                        **prop,
                        'inherited': len(path) > 0,
                        'inheritedFrom': path[0].split('#')[-1] if path else None,
                        'source': 'inherited' if len(path) > 0 else 'direct'
                    }
            
            # Get parent classes using actual URI
            parents = self._get_parent_classes_by_uri(cls_name, cls_graph)
            logger.info(f"🔍 Found {len(parents)} parent classes for {cls_name}")
            for parent in parents:
                parent_path = path + [f"{parent['graph']}#{parent['name']}"]
                collect_properties(parent['name'], parent['graph'], parent_path)
        
        try:
            # Use the actual class name for the initial call
            collect_properties(class_name, graph_iri)
            return {
                'properties': list(properties.values()),
                'conflicts': conflicts
            }
        except Exception as e:
            logger.error(f"Error collecting inherited properties: {e}")
            # Fallback to just direct properties
            direct_props = self._get_direct_properties_by_uri(class_name, graph_iri)
            return {
                'properties': [
                    {**prop, 'inherited': False, 'source': 'direct'} 
                    for prop in direct_props
                ],
                'conflicts': conflicts,
                'error': str(e)
            }

    def _resolve_class_name_to_uri(self, class_name: str, graph_iri: str) -> str:
        """
        Resolve display name to actual class URI in the graph.
        """
        try:
            # Query for classes and map display names to URIs
            query = f"""PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?class ?label WHERE {{
    GRAPH <{graph_iri}> {{
        ?class a owl:Class .
        OPTIONAL {{ ?class rdfs:label ?label }}
    }}
}}"""
            
            sparql = SPARQLWrapper(self.fuseki_query_url)
            sparql.setQuery(query)
            sparql.setReturnFormat(SPARQL_JSON)
            results = sparql.query().convert()
            
            for binding in results["results"]["bindings"]:
                class_uri = binding["class"]["value"]
                class_label = binding.get("label", {}).get("value", "")
                
                # Check if label matches the requested class name
                if class_label == class_name:
                    logger.info(f"🔍 Found class by label: {class_name} → {class_uri}")
                    return class_uri
                
                # Also check if URI fragment matches
                uri_fragment = class_uri.split("#")[-1] if "#" in class_uri else class_uri.split("/")[-1]
                if uri_fragment.lower() == class_name.lower():
                    logger.info(f"🔍 Found class by URI fragment: {class_name} → {class_uri}")
                    return class_uri
            
            # Fallback to constructing URI
            fallback_uri = f"{graph_iri}#{class_name.lower().replace(' ', '-')}"
            logger.info(f"🔍 Using fallback URI for {class_name}: {fallback_uri}")
            return fallback_uri
            
        except Exception as e:
            logger.error(f"Error resolving class name to URI: {e}")
            return f"{graph_iri}#{class_name.lower().replace(' ', '-')}"

    def _get_direct_properties_by_uri(self, class_name: str, graph_iri: str) -> List[Dict]:
        """
        Get direct properties using URI resolution.
        """
        class_uri = self._resolve_class_name_to_uri(class_name, graph_iri)
        
        try:
            query = f"""PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?property ?label ?comment ?range WHERE {{
    GRAPH <{graph_iri}> {{
        ?property a owl:DatatypeProperty .
        ?property rdfs:domain <{class_uri}> .
        
        OPTIONAL {{ ?property rdfs:label ?label }}
        OPTIONAL {{ ?property rdfs:comment ?comment }}
        OPTIONAL {{ ?property rdfs:range ?range }}
    }}
}}"""
            
            sparql = SPARQLWrapper(self.fuseki_query_url)
            sparql.setQuery(query)
            sparql.setReturnFormat(SPARQL_JSON)
            results = sparql.query().convert()
            
            properties = []
            for binding in results["results"]["bindings"]:
                property_uri = binding["property"]["value"]
                property_name = property_uri.split("#")[-1] if "#" in property_uri else property_uri.split("/")[-1]
                
                prop_dict = {
                    'name': property_name,
                    'uri': property_uri,
                    'label': binding.get("label", {}).get("value", property_name),
                    'comment': binding.get("comment", {}).get("value", ""),
                    'type': 'datatype',
                    'range': self._extract_range_name(binding.get("range", {}).get("value", "")),
                    'sortOrder': 0
                }
                properties.append(prop_dict)
                
            logger.info(f"🔍 Found {len(properties)} direct properties for {class_name} (URI: {class_uri})")
            return properties
            
        except Exception as e:
            logger.error(f"Error getting direct properties by URI for {class_name}: {e}")
            return []

    def _get_parent_classes_by_uri(self, class_name: str, graph_iri: str) -> List[Dict]:
        """
        Get parent classes using URI resolution.
        """
        class_uri = self._resolve_class_name_to_uri(class_name, graph_iri)
        
        try:
            query = f"""PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT ?parent WHERE {{
    GRAPH <{graph_iri}> {{
        <{class_uri}> rdfs:subClassOf ?parent .
    }}
}}"""
            
            sparql = SPARQLWrapper(self.fuseki_query_url)
            sparql.setQuery(query)
            sparql.setReturnFormat(SPARQL_JSON)
            results = sparql.query().convert()
            
            parents = []
            for binding in results["results"]["bindings"]:
                parent_uri = binding["parent"]["value"]
                
                # Convert parent URI back to display name
                parent_display_name = self._resolve_uri_to_class_name(parent_uri, graph_iri)
                
                parents.append({
                    'name': parent_display_name,
                    'uri': parent_uri,
                    'graph': graph_iri,
                    'type': 'local'
                })
                logger.info(f"🔍 Found parent: {parent_display_name} (URI: {parent_uri}) for {class_name}")
            
            return parents
            
        except Exception as e:
            logger.error(f"Error getting parent classes by URI for {class_name}: {e}")
            return []

    def _resolve_uri_to_class_name(self, class_uri: str, graph_iri: str) -> str:
        """
        Resolve class URI back to display name.
        """
        try:
            query = f"""PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?label WHERE {{
    GRAPH <{graph_iri}> {{
        <{class_uri}> a owl:Class .
        OPTIONAL {{ <{class_uri}> rdfs:label ?label }}
    }}
}}"""
            
            sparql = SPARQLWrapper(self.fuseki_query_url)
            sparql.setQuery(query)
            sparql.setReturnFormat(SPARQL_JSON)
            results = sparql.query().convert()
            
            for binding in results["results"]["bindings"]:
                label = binding.get("label", {}).get("value", "")
                if label:
                    return label
            
            # Fallback to URI fragment
            return class_uri.split("#")[-1] if "#" in class_uri else class_uri.split("/")[-1]
            
        except Exception as e:
            logger.error(f"Error resolving URI to class name: {e}")
            return class_uri.split("#")[-1] if "#" in class_uri else class_uri.split("/")[-1]

    def _choose_better_range(self, range1: str, range2: str) -> str:
        """
        Choose the better range when there's a conflict.
        Prefers more specific types over generic 'string'.
        """
        # Priority order: specific XSD types > generic types > string
        type_priority = {
            'xsd:integer': 10,
            'xsd:float': 9,
            'xsd:double': 9,
            'xsd:decimal': 8,
            'xsd:boolean': 7,
            'xsd:date': 6,
            'xsd:dateTime': 6,
            'xsd:time': 5,
            'xsd:anyURI': 4,
            'string': 1,
            'xsd:string': 1
        }
        
        priority1 = type_priority.get(range1, 2)
        priority2 = type_priority.get(range2, 2)
        
        if priority1 >= priority2:
            logger.info(f"🔍 Chose {range1} over {range2} (priority {priority1} vs {priority2})")
            return range1
        else:
            logger.info(f"🔍 Chose {range2} over {range1} (priority {priority2} vs {priority1})")
            return range2

    def _get_direct_properties(self, class_name: str, graph_iri: str) -> List[Dict]:
        """
        Get direct data properties for a specific class.
        """
        try:
            logger.info(f"🔍 Getting direct properties for class: {class_name} in graph: {graph_iri}")
            
            # First, let's see what properties exist in the graph at all
            debug_query = f"""PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?property ?domain ?range WHERE {{
    GRAPH <{graph_iri}> {{
        ?property a owl:DatatypeProperty .
        OPTIONAL {{ ?property rdfs:domain ?domain }}
        OPTIONAL {{ ?property rdfs:range ?range }}
    }}
}}"""
            
            sparql = SPARQLWrapper(self.fuseki_query_url)
            sparql.setQuery(debug_query)
            sparql.setReturnFormat(SPARQL_JSON)
            debug_results = sparql.query().convert()
            
            logger.info(f"🔍 Found {len(debug_results['results']['bindings'])} data properties in graph")
            for binding in debug_results['results']['bindings']:
                prop_uri = binding.get('property', {}).get('value', 'Unknown')
                domain_uri = binding.get('domain', {}).get('value', 'No domain')
                range_uri = binding.get('range', {}).get('value', 'No range')
                logger.info(f"🔍   Property: {prop_uri} -> Domain: {domain_uri}, Range: {range_uri}")
            
            # Now try multiple approaches to find properties for this class
            # Handle class names with spaces and special characters
            sanitized_name = class_name.lower().replace(' ', '-').replace('_', '-')
            class_uri_variations = [
                f"{graph_iri}#{sanitized_name}",               # sanitized (spaces to hyphens)
                f"{graph_iri}#{class_name.lower()}",           # lowercase
                f"{graph_iri}#{class_name}",                   # original case  
                f"{graph_iri}#{class_name.replace(' ', '')}",  # no spaces
                f"{graph_iri}#{class_name.replace(' ', '-')}", # spaces to hyphens
                f"{self.base_uri}#{class_name}",               # base URI
                f"{self.base_uri}#{sanitized_name}"            # base URI sanitized
            ]
            
            all_properties = []
            
            for class_uri in class_uri_variations:
                query = f"""PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX odras: <{self.base_uri}/>

SELECT ?property ?label ?comment ?range ?defaultValue ?required ?units ?sortOrder WHERE {{
    GRAPH <{graph_iri}> {{
        ?property a owl:DatatypeProperty .
        ?property rdfs:domain <{class_uri}> .
        
        OPTIONAL {{ ?property rdfs:label ?label }}
        OPTIONAL {{ ?property rdfs:comment ?comment }}
        OPTIONAL {{ ?property rdfs:range ?range }}
        
        OPTIONAL {{ ?property odras:defaultValue ?defaultValue }}
        OPTIONAL {{ ?property odras:required ?required }}
        OPTIONAL {{ ?property odras:units ?units }}
        OPTIONAL {{ ?property odras:sortOrder ?sortOrder }}
    }}
}}"""
                
                sparql.setQuery(query)
                sparql.setReturnFormat(SPARQL_JSON)
                results = sparql.query().convert()
                
                logger.info(f"🔍 Query for class URI {class_uri}: found {len(results['results']['bindings'])} properties")
                
                for binding in results["results"]["bindings"]:
                    property_uri = binding["property"]["value"]
                    property_name = property_uri.split("#")[-1] if "#" in property_uri else property_uri.split("/")[-1]
                    
                    prop_dict = {
                        'name': property_name,
                        'uri': property_uri,
                        'label': binding.get("label", {}).get("value", property_name),
                        'comment': binding.get("comment", {}).get("value", ""),
                        'type': 'datatype',
                        'range': self._extract_range_name(binding.get("range", {}).get("value", "")),
                        'defaultValue': binding.get("defaultValue", {}).get("value"),
                        'required': binding.get("required", {}).get("value") == "true",
                        'units': binding.get("units", {}).get("value"),
                        'sortOrder': int(binding.get("sortOrder", {}).get("value", 0)) if binding.get("sortOrder") else 0
                    }
                    all_properties.append(prop_dict)
                    logger.info(f"🔍 Found property: {property_name} for class URI: {class_uri}")
            
            # Remove duplicates based on property URI
            seen_uris = set()
            unique_properties = []
            for prop in all_properties:
                if prop['uri'] not in seen_uris:
                    unique_properties.append(prop)
                    seen_uris.add(prop['uri'])
            
            # Sort by sortOrder if specified
            unique_properties.sort(key=lambda x: x.get('sortOrder', 0))
            
            logger.info(f"🔍 Returning {len(unique_properties)} unique properties for class {class_name}")
            return unique_properties
            
        except Exception as e:
            logger.error(f"Error getting direct properties for {class_name}: {e}")
            return []

    def _get_parent_classes(self, class_name: str, graph_iri: str) -> List[Dict]:
        """
        Get all parent classes including from reference ontologies.
        Returns list of parent info with graph context.
        """
        try:
            # Handle class names with spaces - try multiple URI variations
            sanitized_name = class_name.lower().replace(' ', '-').replace('_', '-')
            class_uri_variations = [
                f"{graph_iri}#{sanitized_name}",               # sanitized (spaces to hyphens)
                f"{graph_iri}#{class_name.lower()}",           # lowercase
                f"{graph_iri}#{class_name}",                   # original case  
                f"{graph_iri}#{class_name.replace(' ', '')}",  # no spaces
                f"{graph_iri}#{class_name.replace(' ', '-')}", # spaces to hyphens
            ]
            
            parents = []
            for class_uri in class_uri_variations:
                query = f"""PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT DISTINCT ?parent ?parentGraph WHERE {{
    GRAPH <{graph_iri}> {{
        <{class_uri}> rdfs:subClassOf ?parent .
    }}
    
    OPTIONAL {{
        GRAPH ?parentGraph {{
            ?parent a owl:Class .
        }}
    }}
}}"""
                
                sparql = SPARQLWrapper(self.fuseki_query_url)
                sparql.setQuery(query)
                sparql.setReturnFormat(SPARQL_JSON)
                results = sparql.query().convert()
                
                logger.info(f"🔍 Parent query for class URI {class_uri}: found {len(results['results']['bindings'])} parents")
                
                for binding in results["results"]["bindings"]:
                    parent_uri = binding["parent"]["value"]
                    parent_graph = binding.get("parentGraph", {}).get("value", graph_iri)  # Default to same graph
                    
                    # Extract parent class name
                    parent_name = parent_uri.split("#")[-1] if "#" in parent_uri else parent_uri.split("/")[-1]
                    
                    # Verify this is from a reference ontology if cross-project
                    if parent_graph != graph_iri:
                        if self._is_reference_ontology(parent_graph):
                            parents.append({
                                'name': parent_name,
                                'uri': parent_uri,
                                'graph': parent_graph,
                                'type': 'reference'
                            })
                    else:
                        parents.append({
                            'name': parent_name,
                            'uri': parent_uri,
                            'graph': parent_graph,
                            'type': 'local'
                        })
                        logger.info(f"🔍 Found parent: {parent_name} (URI: {parent_uri})")
                
                # Break if we found parents with this URI variation
                if parents:
                    break
            
            return parents
            
        except Exception as e:
            logger.error(f"Error getting parent classes for {class_name}: {e}")
            return []

    def _is_reference_ontology(self, graph_iri: str) -> bool:
        """
        Check if the given graph IRI is a reference ontology.
        """
        try:
            from .db import DatabaseService
            db = DatabaseService(self.settings)
            
            # Get project_id for database query
            project_id = self.current_project_id
            if not project_id:
                project_id = self.uri_service.parse_project_from_uri(graph_iri) if self.uri_service else None
            
            if project_id:
                ref_ontologies = db.list_ontologies(project_id=project_id)
            else:
                logger.warning("No project_id available for checking reference ontology")
                try:
                    ref_ontologies = db.list_ontologies(project_id="")
                except:
                    ref_ontologies = []
            
            for ontology in ref_ontologies:
                if ontology.get('graph_iri') == graph_iri and ontology.get('is_reference', False):
                    return True
            return False
            
        except Exception as e:
            logger.error(f"Error checking if {graph_iri} is reference ontology: {e}")
            return False

    def _extract_range_name(self, range_uri: str) -> str:
        """
        Extract readable range name from URI.
        """
        if not range_uri:
            return ""
            
        if range_uri.startswith("http://www.w3.org/2001/XMLSchema#"):
            return range_uri.replace("http://www.w3.org/2001/XMLSchema#", "xsd:")
        elif "#" in range_uri:
            return range_uri.split("#")[-1]
        else:
            return range_uri.split("/")[-1]

    def get_available_parent_classes(self, current_graph: str) -> List[Dict]:
        """
        Get all classes available as parents:
        - Local classes from current ontology
        - All classes from reference ontologies
        """
        available = []
        
        try:
            # Get local classes
            local_classes = self._get_classes_in_graph(current_graph)
            available.extend([
                {"name": c["name"], "graph": current_graph, "type": "local"}
                for c in local_classes
            ])
            
            # Get reference ontology classes
            from .db import DatabaseService
            db = DatabaseService(self.settings)
            
            # Get project_id from current graph URI for database query
            project_id = self.current_project_id
            if not project_id:
                project_id = self.uri_service.parse_project_from_uri(current_graph) if self.uri_service else None
            
            if project_id:
                ref_ontologies = db.list_ontologies(project_id=project_id)
            else:
                logger.warning("No project_id available, using all ontologies")
                try:
                    ref_ontologies = db.list_ontologies(project_id="")
                except:
                    ref_ontologies = []
            
            for ref in ref_ontologies:
                if ref.get('is_reference', False) and ref.get('graph_iri') != current_graph:
                    ref_classes = self._get_classes_in_graph(ref["graph_iri"])
                    available.extend([
                        {
                            "name": c["name"], 
                            "graph": ref["graph_iri"],
                            "type": "reference",
                            "ontology_label": ref.get("label", "Unknown")
                        }
                        for c in ref_classes
                    ])
            
            return available
            
        except Exception as e:
            logger.error(f"Error getting available parent classes: {e}")
            return []

    def _get_classes_in_graph(self, graph_iri: str) -> List[Dict]:
        """
        Get all classes defined in a specific graph.
        """
        try:
            # Debug the query first
            logger.info(f"Getting classes from graph: {graph_iri}")
            logger.info(f"Using base_uri: {self.base_uri}")
            
            # First try a simple query to see what classes exist
            simple_query = f"""PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?class WHERE {{
    GRAPH <{graph_iri}> {{
        ?class a owl:Class .
    }}
}}"""
            
            sparql = SPARQLWrapper(self.fuseki_query_url)
            sparql.setQuery(simple_query)
            sparql.setReturnFormat(SPARQL_JSON)
            simple_results = sparql.query().convert()
            
            logger.info(f"Simple query found {len(simple_results['results']['bindings'])} classes")
            
            # Now try the full query with flexible abstract class detection
            query = f"""PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?class ?label ?comment ?isAbstract WHERE {{
    GRAPH <{graph_iri}> {{
        ?class a owl:Class .
        OPTIONAL {{ ?class rdfs:label ?label }}
        OPTIONAL {{ ?class rdfs:comment ?comment }}
        
        OPTIONAL {{ 
            {{ ?class <{self.base_uri}/isAbstract> ?isAbstract }} UNION
            {{ ?class <{graph_iri}/isAbstract> ?isAbstract }} UNION
            {{ ?class <http://odras.ai/ontology/isAbstract> ?isAbstract }}
        }}
    }}
}}"""
            
            sparql.setQuery(query)
            sparql.setReturnFormat(SPARQL_JSON)
            results = sparql.query().convert()
            
            logger.info(f"Full query found {len(results['results']['bindings'])} classes")
            
            classes = []
            for binding in results["results"]["bindings"]:
                class_uri = binding["class"]["value"]
                class_name = class_uri.split("#")[-1] if "#" in class_uri else class_uri.split("/")[-1]
                
                # Skip blank nodes or invalid URIs
                if not class_name or class_name.startswith('_:'):
                    continue
                
                # Use label as the display name if available, fall back to URI fragment
                class_label = binding.get("label", {}).get("value", "")
                display_name = class_label if class_label else class_name
                
                class_dict = {
                    'name': display_name,  # Use label for display if available
                    'id': class_name,      # Keep original ID for internal reference
                    'uri': class_uri,
                    'label': class_label,
                    'comment': binding.get("comment", {}).get("value", ""),
                    'isAbstract': binding.get("isAbstract", {}).get("value") == "true"
                }
                classes.append(class_dict)
                
                logger.info(f"Found class: {display_name} (ID: {class_name}, URI: {class_uri})")
            
            logger.info(f"Returning {len(classes)} classes from graph {graph_iri}")
            return classes
            
        except Exception as e:
            logger.error(f"Error getting classes in graph {graph_iri}: {e}")
            return []
