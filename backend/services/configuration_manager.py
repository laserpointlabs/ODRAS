"""
Configuration Manager Service
Handles CRUD operations and business logic for configurations
"""

import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from SPARQLWrapper import SPARQLWrapper, JSON as SPARQL_JSON

from backend.services.config import Settings
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection"""
    settings = Settings()
    return psycopg2.connect(
        host=settings.postgres_host,
        user=settings.postgres_user,
        password=settings.postgres_password,
        database=settings.postgres_database,
        port=settings.postgres_port
    )

class ConfigurationManager:
    """
    Manages configuration CRUD operations and Fuseki integration
    """
    
    def __init__(self):
        self.settings = Settings()
    
    async def list_root_individuals(
        self,
        project_id: str,
        ontology_graph: str,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        List root individuals for conceptualization (individuals from top-level classes)
        """
        try:
            # First, detect the root classes in the ontology
            root_classes = await self._detect_root_classes(ontology_graph)
            
            if not root_classes:
                return {
                    "configurations": [],
                    "total": 0,
                    "root_classes": [],
                    "message": "No root classes found in ontology"
                }
            
            # Get individuals from root classes
            offset = (page - 1) * page_size
            
            with get_db_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                # Build query to get individuals from root classes
                class_filter = ','.join([f"'{cls}'" for cls in root_classes])
                
                # Count query
                count_query = f"""
                    SELECT COUNT(*) as total
                    FROM individual_instances ii
                    JOIN individual_tables_config itc ON ii.table_id = itc.table_id
                    WHERE itc.project_id = %s 
                    AND itc.graph_iri = %s
                    AND ii.class_name IN ({class_filter})
                """
                
                cursor.execute(count_query, (project_id, ontology_graph))
                total = cursor.fetchone()["total"]
                
                # Data query
                data_query = f"""
                    SELECT 
                        ii.instance_id as config_id,
                        ii.instance_name as name,
                        ii.class_name,
                        ii.properties,
                        ii.created_at,
                        ii.updated_at,
                        'individual' as source_type
                    FROM individual_instances ii
                    JOIN individual_tables_config itc ON ii.table_id = itc.table_id
                    WHERE itc.project_id = %s 
                    AND itc.graph_iri = %s
                    AND ii.class_name IN ({class_filter})
                    ORDER BY ii.created_at DESC
                    LIMIT %s OFFSET %s
                """
                
                cursor.execute(data_query, (project_id, ontology_graph, page_size, offset))
                individuals = cursor.fetchall()
                
                # Format as configurations for the UI
                configurations = []
                for individual in individuals:
                    config = {
                        "config_id": individual["config_id"],
                        "name": individual["name"],
                        "class_name": individual["class_name"],
                        "properties": individual["properties"],
                        "created_at": individual["created_at"],
                        "modified_at": individual["updated_at"],
                        "source_type": "root_individual",
                        "das_generated": False
                    }
                    configurations.append(config)
                
                return {
                    "configurations": configurations,
                    "total": total,
                    "root_classes": root_classes
                }
                
        except Exception as e:
            logger.error(f"❌ Error listing root individuals: {e}")
            raise e
    
    async def list_configurations(
        self,
        project_id: str,
        page: int = 1,
        page_size: int = 50,
        filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        List configurations with pagination and filtering
        """
        try:
            filters = filters or {}
            offset = (page - 1) * page_size
            
            # Base query
            base_query = """
                SELECT c.config_id, c.name, c.ontology_graph, c.source_requirement,
                       c.created_at, c.modified_at, c.das_metadata, c.structure
                FROM configurations c
                WHERE c.project_id = %s
            """
            count_query = """
                SELECT COUNT(*) as total
                FROM configurations c
                WHERE c.project_id = %s
            """
            
            params = [project_id]
            
            # Apply filters
            if filters.get("source"):
                if filters["source"] == "DAS":
                    base_query += " AND c.das_metadata IS NOT NULL"
                    count_query += " AND c.das_metadata IS NOT NULL"
                elif filters["source"] == "Manual":
                    base_query += " AND c.das_metadata IS NULL"
                    count_query += " AND c.das_metadata IS NULL"
            
            if filters.get("requirement_prefix"):
                base_query += " AND c.source_requirement LIKE %s"
                count_query += " AND c.source_requirement LIKE %s"
                params.append(f"{filters['requirement_prefix']}%")
            
            if filters.get("confidence_min") is not None:
                base_query += " AND JSON_EXTRACT(c.das_metadata, '$.confidence') >= %s"
                count_query += " AND JSON_EXTRACT(c.das_metadata, '$.confidence') >= %s"
                params.append(filters["confidence_min"])
            
            if filters.get("date_range"):
                # Handle date range filtering
                if filters["date_range"] == "last-7-days":
                    base_query += " AND c.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
                    count_query += " AND c.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
                elif filters["date_range"] == "last-30-days":
                    base_query += " AND c.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)"
                    count_query += " AND c.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)"
            
            # Add ordering and pagination
            base_query += " ORDER BY c.created_at DESC LIMIT %s OFFSET %s"
            params.extend([page_size, offset])
            
            with get_db_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                # Get total count
                count_params = params[:-2]  # Remove limit and offset for count
                cursor.execute(count_query, count_params)
                total = cursor.fetchone()["total"]
                
                # Get configurations
                cursor.execute(base_query, params)
                configs = cursor.fetchall()
                
                # Parse JSON fields (PostgreSQL JSONB columns return as dict already)
                for config in configs:
                    if config["das_metadata"] and isinstance(config["das_metadata"], str):
                        config["das_metadata"] = json.loads(config["das_metadata"])
                    if config["structure"] and isinstance(config["structure"], str):
                        config["structure"] = json.loads(config["structure"])
                
                return {
                    "configurations": configs,
                    "total": total
                }
                
        except Exception as e:
            logger.error(f"❌ Error listing configurations: {e}")
            raise e
    
    async def create_configuration(
        self,
        project_id: str,
        config_data: Dict[str, Any],
        user_id: str
    ) -> str:
        """
        Create new configuration
        """
        try:
            config_id = str(uuid.uuid4())
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Insert configuration
                cursor.execute("""
                    INSERT INTO configurations (
                        config_id, project_id, name, ontology_graph, 
                        source_requirement, structure, das_metadata,
                        created_by, created_at, modified_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    config_id, project_id, config_data["name"],
                    config_data["ontology_graph"],
                    config_data.get("source_requirement"),
                    json.dumps(config_data["structure"]),
                    json.dumps(config_data["das_metadata"]) if config_data.get("das_metadata") else None,
                    user_id, datetime.now(timezone.utc), datetime.now(timezone.utc)
                ))
                
                conn.commit()
            
            # Store in Fuseki as well
            await self._store_configuration_in_fuseki(config_id, config_data)
            
            return config_id
            
        except Exception as e:
            logger.error(f"❌ Error creating configuration: {e}")
            raise e
    
    async def get_configuration(self, project_id: str, config_id: str) -> Optional[Dict[str, Any]]:
        """
        Get specific configuration
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                cursor.execute("""
                    SELECT * FROM configurations 
                    WHERE project_id = %s AND config_id = %s
                """, (project_id, config_id))
                
                config = cursor.fetchone()
                
                if config:
                    # Parse JSON fields (PostgreSQL JSONB columns return as dict already)
                    if config["das_metadata"] and isinstance(config["das_metadata"], str):
                        config["das_metadata"] = json.loads(config["das_metadata"])
                    if config["structure"] and isinstance(config["structure"], str):
                        config["structure"] = json.loads(config["structure"])
                
                return config
                
        except Exception as e:
            logger.error(f"❌ Error getting configuration: {e}")
            raise e
    
    async def update_configuration(
        self,
        project_id: str,
        config_id: str,
        update_data: Dict[str, Any],
        user_id: str
    ) -> bool:
        """
        Update existing configuration
        """
        try:
            if not update_data:
                return True
            
            set_clauses = []
            params = []
            
            if "name" in update_data:
                set_clauses.append("name = %s")
                params.append(update_data["name"])
            
            if "structure" in update_data:
                set_clauses.append("structure = %s")
                params.append(json.dumps(update_data["structure"]))
            
            if not set_clauses:
                return True
            
            set_clauses.append("modified_at = %s")
            params.append(datetime.now(timezone.utc))
            
            params.extend([project_id, config_id])
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                query = f"""
                    UPDATE configurations 
                    SET {', '.join(set_clauses)}
                    WHERE project_id = %s AND config_id = %s
                """
                
                cursor.execute(query, params)
                success = cursor.rowcount > 0
                conn.commit()
                
                return success
                
        except Exception as e:
            logger.error(f"❌ Error updating configuration: {e}")
            raise e
    
    async def delete_configuration(self, project_id: str, config_id: str) -> bool:
        """
        Delete configuration
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM configurations 
                    WHERE project_id = %s AND config_id = %s
                """, (project_id, config_id))
                
                success = cursor.rowcount > 0
                conn.commit()
                
                # Also remove from Fuseki
                if success:
                    await self._delete_configuration_from_fuseki(config_id)
                
                return success
                
        except Exception as e:
            logger.error(f"❌ Error deleting configuration: {e}")
            raise e
    
    async def validate_configuration(
        self,
        project_id: str,
        config_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate configuration against ontology constraints
        """
        try:
            validation_result = {
                "valid": True,
                "errors": [],
                "warnings": []
            }
            
            ontology_graph = config_data["ontology_graph"]
            structure = config_data["structure"]
            
            # Get ontology constraints - placeholder for now
            constraints = {"classes": {}}
            
            # Validate structure against ontology
            await self._validate_structure(structure, constraints, validation_result)
            
            return validation_result
            
        except Exception as e:
            logger.error(f"❌ Error validating configuration: {e}")
            return {
                "valid": False,
                "errors": [f"Validation failed: {str(e)}"],
                "warnings": []
            }
    
    async def _validate_structure(
        self,
        structure: Dict[str, Any],
        constraints: Dict[str, Any],
        result: Dict[str, Any],
        path: str = ""
    ):
        """
        Recursively validate structure against constraints
        """
        try:
            class_name = structure.get("class")
            if not class_name:
                result["errors"].append(f"Missing class at {path}")
                result["valid"] = False
                return
            
            # Check if class exists in ontology
            if class_name not in constraints.get("classes", {}):
                result["warnings"].append(f"Unknown class '{class_name}' at {path}")
            
            # Validate relationships
            relationships = structure.get("relationships", [])
            for i, rel in enumerate(relationships):
                rel_path = f"{path}.relationships[{i}]"
                property_name = rel.get("property")
                
                if not property_name:
                    result["errors"].append(f"Missing property name at {rel_path}")
                    result["valid"] = False
                    continue
                
                # Check multiplicity if available
                multiplicity = rel.get("multiplicity")
                targets = rel.get("targets", [])
                
                if multiplicity and not self._validate_multiplicity(multiplicity, len(targets)):
                    result["errors"].append(
                        f"Multiplicity violation for {property_name} at {rel_path}: "
                        f"expected {multiplicity}, got {len(targets)} targets"
                    )
                    result["valid"] = False
                
                # Validate target structures recursively
                for j, target in enumerate(targets):
                    if isinstance(target, dict) and "class" in target:
                        target_path = f"{rel_path}.targets[{j}]"
                        await self._validate_structure(target, constraints, result, target_path)
            
        except Exception as e:
            result["errors"].append(f"Validation error at {path}: {str(e)}")
            result["valid"] = False
    
    def _validate_multiplicity(self, multiplicity: str, count: int) -> bool:
        """
        Validate count against multiplicity constraint
        """
        try:
            if ".." not in multiplicity:
                return True
            
            parts = multiplicity.split("..")
            if len(parts) != 2:
                return True
            
            min_val = int(parts[0]) if parts[0] != "*" else 0
            max_val = int(parts[1]) if parts[1] != "*" else float('inf')
            
            return min_val <= count <= max_val
            
        except:
            return True  # If we can't parse, assume valid
    
    async def _store_configuration_in_fuseki(self, config_id: str, config_data: Dict[str, Any]):
        """
        Store configuration in Fuseki triplestore
        """
        try:
            graph_iri = f"{config_data['ontology_graph']}/configurations/{config_id}"
            
            sparql = SPARQLWrapper(f"{self.settings.fuseki_url}/update")
            
            # Build SPARQL triples for the configuration
            triples = [
                f"<{graph_iri}> a <http://odras.io/ontology/Configuration> .",
                f"<{graph_iri}> <http://odras.io/ontology/configName> \"{config_data['name']}\" .",
                f"<{graph_iri}> <http://odras.io/ontology/sourceOntology> <{config_data['ontology_graph']}> ."
            ]
            
            if config_data.get("source_requirement"):
                triples.append(
                    f"<{graph_iri}> <http://odras.io/ontology/sourceRequirement> \"{config_data['source_requirement']}\" ."
                )
            
            # Add structure as JSON-LD or serialized RDF
            structure_json = json.dumps(config_data["structure"]).replace('"', '\\"')
            triples.append(
                f"<{graph_iri}> <http://odras.io/ontology/configStructure> \"{structure_json}\" ."
            )
            
            query = f"""
                INSERT DATA {{
                    GRAPH <{graph_iri}> {{
                        {' '.join(triples)}
                    }}
                }}
            """
            
            sparql.setQuery(query)
            sparql.method = "POST"
            sparql.query()
            
            logger.info(f"✅ Configuration {config_id} stored in Fuseki")
            
        except Exception as e:
            logger.error(f"❌ Error storing configuration in Fuseki: {e}")
            # Don't raise - allow configuration to be created even if Fuseki fails
    
    async def _delete_configuration_from_fuseki(self, config_id: str):
        """
        Delete configuration from Fuseki
        """
        try:
            sparql = SPARQLWrapper(f"{self.settings.fuseki_url}/update")
            
            # Delete all triples for this configuration
            query = f"""
                DELETE WHERE {{
                    GRAPH ?g {{
                        ?s ?p ?o .
                        FILTER(CONTAINS(STR(?g), "{config_id}"))
                    }}
                }}
            """
            
            sparql.setQuery(query)
            sparql.method = "POST"
            sparql.query()
            
            logger.info(f"✅ Configuration {config_id} deleted from Fuseki")
            
        except Exception as e:
            logger.error(f"❌ Error deleting configuration from Fuseki: {e}")
            # Don't raise - allow deletion to proceed even if Fuseki fails
    
    async def sync_configuration_to_individuals(
        self, 
        project_id: str, 
        config_id: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """
        Sync configuration to individual tables
        """
        try:
            # Get the configuration
            config = await self.get_configuration(project_id, config_id)
            if not config:
                raise ValueError(f"Configuration {config_id} not found")
            
            # Extract individuals from configuration structure
            individuals = self._extract_individuals_from_structure(config["structure"])
            
            # Create/update individuals in tables
            sync_results = {
                "created": 0,
                "updated": 0,
                "errors": []
            }
            
            for individual in individuals:
                try:
                    await self._sync_individual_to_table(
                        project_id, config_id, individual, user_id
                    )
                    sync_results["created"] += 1
                except Exception as e:
                    logger.error(f"❌ Error syncing individual {individual.get('name')}: {e}")
                    sync_results["errors"].append({
                        "individual": individual.get("name", "unknown"),
                        "error": str(e)
                    })
            
            return sync_results
            
        except Exception as e:
            logger.error(f"❌ Error syncing configuration to individuals: {e}")
            raise e
    
    async def get_sync_status(self, project_id: str, config_id: str) -> Dict[str, Any]:
        """
        Get sync status between configuration and individual tables
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_sync_records,
                        COUNT(CASE WHEN sync_status = 'synced' THEN 1 END) as synced_count,
                        COUNT(CASE WHEN sync_status = 'modified' THEN 1 END) as modified_count,
                        COUNT(CASE WHEN sync_status = 'deleted' THEN 1 END) as deleted_count,
                        MAX(last_sync_at) as last_sync
                    FROM configuration_individual_sync
                    WHERE config_id = %s
                """, (config_id,))
                
                sync_status = cursor.fetchone()
                
                return dict(sync_status) if sync_status else {
                    "total_sync_records": 0,
                    "synced_count": 0, 
                    "modified_count": 0,
                    "deleted_count": 0,
                    "last_sync": None
                }
                
        except Exception as e:
            logger.error(f"❌ Error getting sync status: {e}")
            raise e
    
    def _extract_individuals_from_structure(self, structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract individual instances from configuration structure
        """
        individuals = []
        
        def extract_recursive(node, path=""):
            if not isinstance(node, dict):
                return
                
            # Extract this node as an individual
            if "class" in node and "instanceId" in node:
                individual = {
                    "class": node["class"],
                    "instance_id": node["instanceId"],
                    "name": node.get("properties", {}).get("name", node["instanceId"]),
                    "properties": node.get("properties", {}),
                    "path": path
                }
                individuals.append(individual)
            
            # Recurse into relationships
            relationships = node.get("relationships", [])
            for i, rel in enumerate(relationships):
                targets = rel.get("targets", [])
                for j, target in enumerate(targets):
                    if isinstance(target, dict) and "class" in target:
                        new_path = f"{path}.relationships[{i}].targets[{j}]"
                        extract_recursive(target, new_path)
        
        extract_recursive(structure)
        return individuals
    
    async def _sync_individual_to_table(
        self, 
        project_id: str, 
        config_id: str, 
        individual: Dict[str, Any], 
        user_id: str
    ):
        """
        Sync single individual to appropriate table
        """
        # This is a placeholder implementation
        # In a full implementation, this would:
        # 1. Find or create the appropriate individual table
        # 2. Create/update the individual instance
        # 3. Update the sync tracking table
        logger.info(f"Syncing individual {individual['name']} of class {individual['class']}")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Create sync tracking record
            sync_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO configuration_individual_sync (
                    sync_id, config_id, table_id, instance_id, node_id,
                    sync_status, last_sync_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (config_id, instance_id) 
                DO UPDATE SET 
                    sync_status = EXCLUDED.sync_status,
                    last_sync_at = EXCLUDED.last_sync_at
            """, (
                sync_id, config_id, 
                str(uuid.uuid4()),  # placeholder table_id
                str(uuid.uuid4()),  # placeholder instance_id
                f"{config_id}_{individual['instance_id']}",
                'synced', datetime.now(timezone.utc)
            ))
            
            conn.commit()
    
    async def _detect_root_classes(self, ontology_graph: str) -> List[str]:
        """
        Detect root classes (classes with no incoming object properties)
        """
        try:
            sparql = SPARQLWrapper(f"{self.settings.fuseki_url}/query")
            
            # SPARQL query to find classes that are never the range of object properties
            query = f"""
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            
            SELECT DISTINCT ?class ?label WHERE {{
                GRAPH <{ontology_graph}> {{
                    # Get all classes
                    ?class rdf:type owl:Class .
                    OPTIONAL {{ ?class rdfs:label ?label }}
                    
                    # Exclude classes that are the range of any object property
                    FILTER NOT EXISTS {{
                        ?property rdf:type owl:ObjectProperty .
                        ?property rdfs:range ?class .
                    }}
                    
                    # Exclude classes that are connected via domain/range constraints
                    FILTER NOT EXISTS {{
                        ?restriction rdf:type owl:Restriction .
                        ?restriction owl:onClass ?class .
                    }}
                }}
            }}
            ORDER BY ?label
            """
            
            sparql.setQuery(query)
            sparql.setReturnFormat(SPARQL_JSON)
            results = sparql.query().convert()
            
            root_classes = []
            for binding in results["results"]["bindings"]:
                # Use label if available, otherwise extract from URI
                if "label" in binding and binding["label"]["value"]:
                    class_name = binding["label"]["value"]
                else:
                    class_uri = binding["class"]["value"]
                    class_name = class_uri.split('#')[-1].split('/')[-1]
                
                root_classes.append(class_name)
            
            logger.info(f"🔍 Detected {len(root_classes)} root classes: {root_classes}")
            return root_classes
            
        except Exception as e:
            logger.error(f"❌ Error detecting root classes: {e}")
            # Return empty list on error - UI can handle gracefully
            return []
