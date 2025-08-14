"""
Ontology Manager Service for ODRAS
Handles JSON-based ontology editing, validation, and synchronization with Fuseki server.
"""

import json
import uuid
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone
from rdflib import Graph, Namespace, Literal, RDF, RDFS, OWL, URIRef, XSD
from rdflib.namespace import NamespaceManager
from SPARQLWrapper import SPARQLWrapper, POST, GET, JSON as SPARQL_JSON
import requests
import logging

from .config import Settings

logger = logging.getLogger(__name__)

class OntologyManager:
    """
    Manages ontology operations including:
    - JSON-based ontology editing
    - RDF serialization/deserialization  
    - Fuseki server synchronization
    - Ontology validation
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.fuseki_url = settings.fuseki_url
        self.fuseki_query_url = f"{self.fuseki_url}/query"
        self.fuseki_update_url = f"{self.fuseki_url}/update"
        
        # Define ODRAS namespace
        self.odras_ns = Namespace("http://odras.system/ontology#")
        self.base_uri = "http://odras.system/ontology"
        
        # Initialize RDF graph for working copy
        self.graph = Graph()
        self.graph.bind("odras", self.odras_ns)
        self.graph.bind("owl", OWL)
        self.graph.bind("rdfs", RDFS)
        
    def get_current_ontology_json(self) -> Dict[str, Any]:
        """
        Retrieve the current ontology from Fuseki and convert to JSON format.
        
        Returns:
            Dict containing the ontology in JSON format
        """
        try:
            # Query all classes, properties, and individuals from Fuseki
            query = """
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX odras: <http://odras.system/ontology#>
            
            SELECT ?s ?p ?o WHERE {
                ?s ?p ?o .
                FILTER(STRSTARTS(STR(?s), "http://odras.system/ontology"))
            }
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
    
    def update_ontology_from_json(self, ontology_json: Dict[str, Any], user_id: str = "system") -> Dict[str, Any]:
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
                    "validation_errors": validation_result["errors"]
                }
            
            # Convert JSON to RDF
            rdf_graph = self._json_to_rdf(ontology_json)
            
            # Create backup of current ontology
            backup_id = self._create_ontology_backup()
            
            # Clear current ontology in Fuseki
            self._clear_ontology_graph()
            
            # Upload new ontology to Fuseki
            turtle_content = rdf_graph.serialize(format='turtle')
            update_result = self._upload_rdf_to_fuseki(turtle_content)
            
            if update_result["success"]:
                # Log the change
                self._log_ontology_change(user_id, backup_id, "full_update")
                
                return {
                    "success": True,
                    "message": "Ontology updated successfully",
                    "backup_id": backup_id,
                    "triples_count": len(rdf_graph),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                # Restore backup if upload failed
                self._restore_ontology_backup(backup_id)
                return {
                    "success": False,
                    "error": "Failed to upload to Fuseki",
                    "details": update_result.get("error", "Unknown error")
                }
                
        except Exception as e:
            logger.error(f"Failed to update ontology: {e}")
            return {
                "success": False,
                "error": f"Update failed: {str(e)}"
            }
    
    def add_class(self, class_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new class to the ontology.
        
        Args:
            class_data: Dict containing class information
            
        Returns:
            Dict containing operation result
        """
        try:
            class_uri = URIRef(f"{self.base_uri}#{class_data['name']}")
            
            # Check if class already exists
            if self._class_exists(class_uri):
                return {
                    "success": False,
                    "error": f"Class {class_data['name']} already exists"
                }
            
            # Create RDF triples for the new class
            triples = [
                (class_uri, RDF.type, OWL.Class),
                (class_uri, RDFS.label, Literal(class_data.get('label', class_data['name']))),
            ]
            
            if class_data.get('comment'):
                triples.append((class_uri, RDFS.comment, Literal(class_data['comment'])))
            
            if class_data.get('subclass_of'):
                parent_uri = URIRef(f"{self.base_uri}#{class_data['subclass_of']}")
                triples.append((class_uri, RDFS.subClassOf, parent_uri))
            
            # Add to Fuseki
            result = self._add_triples_to_fuseki(triples)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"Class {class_data['name']} added successfully",
                    "class_uri": str(class_uri)
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Failed to add class: {e}")
            return {
                "success": False,
                "error": f"Failed to add class: {str(e)}"
            }
    
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
                    "error": f"Property {property_data['name']} already exists"
                }
            
            # Determine property type
            prop_type = OWL.ObjectProperty
            if property_data.get('type') == 'datatype':
                prop_type = OWL.DatatypeProperty
            elif property_data.get('type') == 'annotation':
                prop_type = OWL.AnnotationProperty
            
            # Create RDF triples for the new property
            triples = [
                (prop_uri, RDF.type, prop_type),
                (prop_uri, RDFS.label, Literal(property_data.get('label', property_data['name']))),
            ]
            
            if property_data.get('comment'):
                triples.append((prop_uri, RDFS.comment, Literal(property_data['comment'])))
            
            if property_data.get('domain'):
                domain_uri = URIRef(f"{self.base_uri}#{property_data['domain']}")
                triples.append((prop_uri, RDFS.domain, domain_uri))
            
            if property_data.get('range'):
                if property_data['type'] == 'datatype':
                    range_uri = XSD[property_data['range']]
                else:
                    range_uri = URIRef(f"{self.base_uri}#{property_data['range']}")
                triples.append((prop_uri, RDFS.range, range_uri))
            
            # Add to Fuseki
            result = self._add_triples_to_fuseki(triples)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"Property {property_data['name']} added successfully",
                    "property_uri": str(prop_uri)
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Failed to add property: {e}")
            return {
                "success": False,
                "error": f"Failed to add property: {str(e)}"
            }
    
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
            
            # Delete all triples involving this entity
            delete_query = f"""
            DELETE WHERE {{
                <{entity_uri}> ?p ?o .
            }} ;
            DELETE WHERE {{
                ?s ?p <{entity_uri}> .
            }}
            """
            
            result = self._execute_sparql_update(delete_query)
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"{entity_type.capitalize()} {entity_name} deleted successfully"
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Failed to delete entity: {e}")
            return {
                "success": False,
                "error": f"Failed to delete entity: {str(e)}"
            }
    
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
                "datatype_properties": int(bindings.get("datatypePropertyCount", {}).get("value", 0)),
                "individuals": int(bindings.get("individualCount", {}).get("value", 0)),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get ontology statistics: {e}")
            return {
                "classes": 0,
                "object_properties": 0,
                "datatype_properties": 0,
                "individuals": 0,
                "error": str(e)
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
                "created": datetime.now(timezone.utc).isoformat()
            },
            "classes": [
                {
                    "name": "Requirement",
                    "label": "Requirement",
                    "comment": "A statement that identifies a necessary attribute, capability, characteristic, or quality of a system"
                },
                {
                    "name": "Constraint",
                    "label": "Constraint",
                    "comment": "A restriction or limitation on system behavior or design"
                },
                {
                    "name": "Component",
                    "label": "Component",
                    "comment": "A modular part of a system that encapsulates specific functionality"
                },
                {
                    "name": "Interface",
                    "label": "Interface",
                    "comment": "A shared boundary between system components"
                },
                {
                    "name": "Function",
                    "label": "Function",
                    "comment": "A specific purpose or activity that the system must perform"
                },
                {
                    "name": "Process",
                    "label": "Process",
                    "comment": "A series of actions or steps taken to achieve a particular end"
                },
                {
                    "name": "Condition",
                    "label": "Condition",
                    "comment": "A circumstance or situation that must be met for a function to execute"
                },
                {
                    "name": "Stakeholder",
                    "label": "Stakeholder",
                    "comment": "An individual or organization with an interest in the system"
                },
                {
                    "name": "SourceDocument",
                    "label": "Source Document",
                    "comment": "A document from which requirements are extracted"
                }
            ],
            "object_properties": [
                {
                    "name": "constrained_by",
                    "label": "constrained by",
                    "domain": "Requirement",
                    "range": "Constraint",
                    "comment": "Links a requirement to constraints that apply to it"
                },
                {
                    "name": "satisfied_by",
                    "label": "satisfied by",
                    "domain": "Requirement",
                    "range": "Component",
                    "comment": "Links a requirement to components that satisfy it"
                },
                {
                    "name": "has_interface",
                    "label": "has interface",
                    "domain": "Component",
                    "range": "Interface",
                    "comment": "Links a component to its interfaces"
                },
                {
                    "name": "realizes",
                    "label": "realizes",
                    "domain": "Process",
                    "range": "Function",
                    "comment": "Links a process to the function it realizes"
                },
                {
                    "name": "triggered_by",
                    "label": "triggered by",
                    "domain": "Function",
                    "range": "Condition",
                    "comment": "Links a function to conditions that trigger it"
                },
                {
                    "name": "originates_from",
                    "label": "originates from",
                    "domain": "Requirement",
                    "range": "SourceDocument",
                    "comment": "Links a requirement to its source document"
                }
            ],
            "datatype_properties": [
                {
                    "name": "id",
                    "label": "identifier",
                    "domain": "Requirement",
                    "range": "string",
                    "comment": "Unique identifier for the requirement"
                },
                {
                    "name": "text",
                    "label": "text",
                    "domain": "Requirement",
                    "range": "string",
                    "comment": "The textual content of the requirement"
                },
                {
                    "name": "state",
                    "label": "state",
                    "domain": "Requirement",
                    "range": "string",
                    "comment": "Current state of the requirement (Draft, Reviewed, Approved)"
                },
                {
                    "name": "priority",
                    "label": "priority",
                    "domain": "Requirement",
                    "range": "string",
                    "comment": "Priority level of the requirement"
                },
                {
                    "name": "created_at",
                    "label": "created at",
                    "range": "dateTime",
                    "comment": "Timestamp when the entity was created"
                },
                {
                    "name": "updated_at",
                    "label": "updated at", 
                    "range": "dateTime",
                    "comment": "Timestamp when the entity was last updated"
                }
            ]
        }
    
    def _sparql_results_to_json(self, results: Dict) -> Dict[str, Any]:
        """Convert SPARQL query results to structured JSON ontology format."""
        ontology_json = {
            "metadata": {
                "name": "ODRAS Ontology",
                "namespace": self.base_uri,
                "retrieved": datetime.now(timezone.utc).isoformat()
            },
            "classes": [],
            "object_properties": [],
            "datatype_properties": [],
            "individuals": []
        }
        
        # Process SPARQL results to extract classes, properties, etc.
        # This is a simplified version - you may want to expand this
        # based on the specific structure of your ontology
        
        entities = {}
        
        for binding in results["results"]["bindings"]:
            subject = binding["s"]["value"]
            predicate = binding["p"]["value"]
            obj = binding["o"]["value"]
            
            if subject not in entities:
                entities[subject] = {"triples": []}
            
            entities[subject]["triples"].append((predicate, obj))
        
        # Convert entities to JSON structure
        for uri, data in entities.items():
            entity_name = uri.split("#")[-1]
            entity_type = None
            
            for pred, obj in data["triples"]:
                if pred == str(RDF.type):
                    if obj == str(OWL.Class):
                        entity_type = "class"
                    elif obj == str(OWL.ObjectProperty):
                        entity_type = "object_property"
                    elif obj == str(OWL.DatatypeProperty):
                        entity_type = "datatype_property"
            
            if entity_type == "class":
                ontology_json["classes"].append({"name": entity_name, "uri": uri})
            elif entity_type == "object_property":
                ontology_json["object_properties"].append({"name": entity_name, "uri": uri})
            elif entity_type == "datatype_property":
                ontology_json["datatype_properties"].append({"name": entity_name, "uri": uri})
        
        return ontology_json
    
    def _validate_ontology_json(self, ontology_json: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the structure and content of ontology JSON."""
        errors = []
        
        # Check required top-level keys
        required_keys = ["metadata", "classes", "object_properties", "datatype_properties"]
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
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def _json_to_rdf(self, ontology_json: Dict[str, Any]) -> Graph:
        """Convert JSON ontology to RDF graph."""
        graph = Graph()
        graph.bind("odras", self.odras_ns)
        graph.bind("owl", OWL)
        graph.bind("rdfs", RDFS)
        
        # Add ontology metadata
        ontology_uri = URIRef(self.base_uri)
        graph.add((ontology_uri, RDF.type, OWL.Ontology))
        
        if "metadata" in ontology_json:
            metadata = ontology_json["metadata"]
            if "name" in metadata:
                graph.add((ontology_uri, RDFS.label, Literal(metadata["name"])))
            if "description" in metadata:
                graph.add((ontology_uri, RDFS.comment, Literal(metadata["description"])))
        
        # Add classes
        for cls in ontology_json.get("classes", []):
            class_uri = URIRef(f"{self.base_uri}#{cls['name']}")
            graph.add((class_uri, RDF.type, OWL.Class))
            graph.add((class_uri, RDFS.label, Literal(cls.get("label", cls["name"]))))
            
            if "comment" in cls:
                graph.add((class_uri, RDFS.comment, Literal(cls["comment"])))
            
            if "subclass_of" in cls:
                parent_uri = URIRef(f"{self.base_uri}#{cls['subclass_of']}")
                graph.add((class_uri, RDFS.subClassOf, parent_uri))
        
        # Add object properties
        for prop in ontology_json.get("object_properties", []):
            prop_uri = URIRef(f"{self.base_uri}#{prop['name']}")
            graph.add((prop_uri, RDF.type, OWL.ObjectProperty))
            graph.add((prop_uri, RDFS.label, Literal(prop.get("label", prop["name"]))))
            
            if "comment" in prop:
                graph.add((prop_uri, RDFS.comment, Literal(prop["comment"])))
            
            if "domain" in prop:
                domain_uri = URIRef(f"{self.base_uri}#{prop['domain']}")
                graph.add((prop_uri, RDFS.domain, domain_uri))
            
            if "range" in prop:
                range_uri = URIRef(f"{self.base_uri}#{prop['range']}")
                graph.add((prop_uri, RDFS.range, range_uri))
        
        # Add datatype properties
        for prop in ontology_json.get("datatype_properties", []):
            prop_uri = URIRef(f"{self.base_uri}#{prop['name']}")
            graph.add((prop_uri, RDF.type, OWL.DatatypeProperty))
            graph.add((prop_uri, RDFS.label, Literal(prop.get("label", prop["name"]))))
            
            if "comment" in prop:
                graph.add((prop_uri, RDFS.comment, Literal(prop["comment"])))
            
            if "domain" in prop:
                domain_uri = URIRef(f"{self.base_uri}#{prop['domain']}")
                graph.add((prop_uri, RDFS.domain, domain_uri))
            
            if "range" in prop:
                if prop["range"] in ["string", "integer", "float", "boolean", "dateTime"]:
                    range_uri = XSD[prop["range"]]
                else:
                    range_uri = URIRef(f"{self.base_uri}#{prop['range']}")
                graph.add((prop_uri, RDFS.range, range_uri))
        
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
            sparql = SPARQLWrapper(self.fuseki_update_url)
            sparql.setMethod(POST)
            
            # Insert data using SPARQL UPDATE
            query = f"""
            INSERT DATA {{
                {turtle_content}
            }}
            """
            
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
                if isinstance(o, Literal):
                    insert_data.append(f"<{s}> <{p}> \"{o}\" .")
                else:
                    insert_data.append(f"<{s}> <{p}> <{o}> .")
            
            query = f"""
            INSERT DATA {{
                {' '.join(insert_data)}
            }}
            """
            
            return self._execute_sparql_update(query)
            
        except Exception as e:
            logger.error(f"Failed to add triples to Fuseki: {e}")
            return {"success": False, "error": str(e)}
    
    def _execute_sparql_update(self, query: str) -> Dict[str, Any]:
        """Execute a SPARQL UPDATE query."""
        try:
            sparql = SPARQLWrapper(self.fuseki_update_url)
            sparql.setMethod(POST)
            sparql.setQuery(query)
            sparql.query()
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"SPARQL UPDATE failed: {e}")
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
