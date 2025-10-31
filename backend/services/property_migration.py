"""
Property Migration Service

Handles migration of individual property data when ontology properties are renamed.
"""
import logging
import json
import psycopg2
from typing import Dict, List, Optional, Any
from datetime import datetime
from backend.services.config import Settings
from SPARQLWrapper import SPARQLWrapper, JSON

def get_db_connection():
    """Get raw database connection for complex queries."""
    settings = Settings()
    try:
        conn = psycopg2.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_database,
            user=settings.postgres_user,
            password=settings.postgres_password,
            connect_timeout=10
        )
        conn.autocommit = False  # Use transactions
        return conn
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise

logger = logging.getLogger(__name__)


class PropertyMigrationService:
    """Manages property migrations for individual instances"""
    
    def __init__(self):
        self.settings = Settings()
    
    def create_mapping(
        self,
        project_id: str,
        graph_iri: str,
        class_name: str,
        old_property_name: str,
        new_property_name: str,
        old_property_iri: Optional[str] = None,
        new_property_iri: Optional[str] = None,
        change_type: str = "rename",
        change_details: Optional[Dict] = None
    ) -> str:
        """
        Create a property mapping record
        
        Returns:
            mapping_id UUID
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO property_mappings (
                        project_id, graph_iri, class_name,
                        old_property_name, new_property_name,
                        old_property_iri, new_property_iri,
                        change_type, change_details, migration_status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (project_id, graph_iri, class_name, old_property_name, new_property_name)
                    DO UPDATE SET
                        migration_status = 'pending',
                        updated_at = NOW()
                    RETURNING mapping_id
                """, (
                    project_id, graph_iri, class_name,
                    old_property_name, new_property_name,
                    old_property_iri, new_property_iri,
                    change_type, json.dumps(change_details or {}), 'pending'
                ))
                
                mapping_id = cursor.fetchone()[0]
                conn.commit()
                
                logger.info(f"Created property mapping: {old_property_name} -> {new_property_name}")
                return str(mapping_id)
                
        except Exception as e:
            logger.error(f"Error creating property mapping: {e}")
            raise
    
    def get_pending_mappings(
        self,
        project_id: str,
        graph_iri: str,
        class_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get pending property mappings"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                if class_name:
                    cursor.execute("""
                        SELECT * FROM property_mappings
                        WHERE project_id = %s AND graph_iri = %s AND class_name = %s
                        AND migration_status = 'pending'
                        ORDER BY created_at DESC
                    """, (project_id, graph_iri, class_name))
                else:
                    cursor.execute("""
                        SELECT * FROM property_mappings
                        WHERE project_id = %s AND graph_iri = %s
                        AND migration_status = 'pending'
                        ORDER BY created_at DESC
                    """, (project_id, graph_iri))
                
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                
                mappings = []
                for row in rows:
                    mapping = dict(zip(columns, row))
                    # Convert JSONB fields
                    if mapping.get('change_details'):
                        mapping['change_details'] = json.loads(mapping['change_details'])
                    mappings.append(mapping)
                
                return mappings
                
        except Exception as e:
            logger.error(f"Error getting pending mappings: {e}")
            return []
    
    def migrate_individuals(
        self,
        project_id: str,
        graph_iri: str,
        class_name: str,
        old_property_name: str,
        new_property_name: str,
        property_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Migrate individual property data from old name to new name
        
        Args:
            property_type: "DatatypeProperty" or "ObjectProperty". If None, checks mapping table.
        
        Returns:
            Dict with migration results
        """
        try:
            # Determine property type if not provided
            if not property_type:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT change_details FROM property_mappings
                        WHERE project_id = %s AND graph_iri = %s AND class_name = %s
                        AND old_property_name = %s AND new_property_name = %s
                    """, (project_id, graph_iri, class_name, old_property_name, new_property_name))
                    
                    result = cursor.fetchone()
                    if result and result[0]:
                        change_details = result[0]
                        if isinstance(change_details, str):
                            change_details = json.loads(change_details)
                        property_type = change_details.get('property_type')
            
            # Route to appropriate migration method
            if property_type == 'ObjectProperty':
                # Get IRIs from mapping
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT old_property_iri, new_property_iri FROM property_mappings
                        WHERE project_id = %s AND graph_iri = %s AND class_name = %s
                        AND old_property_name = %s AND new_property_name = %s
                    """, (project_id, graph_iri, class_name, old_property_name, new_property_name))
                    
                    result = cursor.fetchone()
                    old_property_iri = result[0] if result else None
                    new_property_iri = result[1] if result else None
                
                return self.migrate_object_property(
                    project_id, graph_iri, old_property_name, new_property_name,
                    old_property_iri, new_property_iri
                )
            
            # Default: data property migration (existing logic)
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Find all individuals for this class (or all classes if wildcard)
                if class_name == "*":
                    # Wildcard: migrate for all classes
                    cursor.execute("""
                        SELECT ii.instance_id, ii.properties, ii.class_name
                        FROM individual_instances ii
                        JOIN individual_tables_config itc ON ii.table_id = itc.table_id
                        WHERE itc.project_id = %s
                        AND itc.graph_iri = %s
                    """, (project_id, graph_iri))
                else:
                    # Specific class: migrate only for that class
                    cursor.execute("""
                        SELECT ii.instance_id, ii.properties, ii.class_name
                        FROM individual_instances ii
                        JOIN individual_tables_config itc ON ii.table_id = itc.table_id
                        WHERE itc.project_id = %s
                        AND itc.graph_iri = %s
                        AND ii.class_name = %s
                    """, (project_id, graph_iri, class_name))
                
                rows = cursor.fetchall()
                
                migrated_count = 0
                skipped_count = 0
                
                for row in rows:
                    instance_id = row[0]
                    properties_json = row[1]
                    instance_class = row[2] if len(row) > 2 else class_name
                    # Parse properties
                    if isinstance(properties_json, str):
                        properties = json.loads(properties_json)
                    else:
                        properties = properties_json
                    
                    # Check if old property exists (try both with and without spaces)
                    logger.info(f"Checking individual {instance_id} for property '{old_property_name}'")
                    logger.info(f"Available properties: {list(properties.keys())}")
                    
                    # Try with spaces first (from labels)
                    # Then try without spaces (from IRI)
                    old_prop_no_spaces = old_property_name.replace(" ", "")
                    new_prop_no_spaces = new_property_name.replace(" ", "")
                    
                    property_found = False
                    actual_old_key = None
                    
                    if old_property_name in properties:
                        actual_old_key = old_property_name
                        property_found = True
                    elif old_prop_no_spaces in properties:
                        actual_old_key = old_prop_no_spaces
                        property_found = True
                    
                    if property_found:
                        # Determine new key based on what's in database
                        if actual_old_key == old_property_name:
                            # Database has spaces, use new property name with spaces
                            actual_new_key = new_property_name
                        else:
                            # Database has no spaces, use new property name without spaces
                            actual_new_key = new_prop_no_spaces
                        
                        # Rename the property
                        properties[actual_new_key] = properties.pop(actual_old_key)
                        
                        # Update the individual
                        cursor.execute("""
                            UPDATE individual_instances
                            SET properties = %s, updated_at = NOW()
                            WHERE instance_id = %s
                        """, (json.dumps(properties), instance_id))
                        
                        logger.info(f"✅ Migrated property '{actual_old_key}' -> '{actual_new_key}' for {instance_id}")
                        migrated_count += 1
                    else:
                        logger.info(f"⚠️ Property '{old_property_name}' (or '{old_prop_no_spaces}') not found in individual {instance_id}")
                        skipped_count += 1
                
                # Update mapping status (handle wildcard by matching on property names only)
                if class_name == "*":
                    cursor.execute("""
                        UPDATE property_mappings
                        SET migration_status = 'applied',
                            migration_date = NOW()
                        WHERE project_id = %s AND graph_iri = %s AND class_name = '*'
                        AND old_property_name = %s AND new_property_name = %s
                    """, (project_id, graph_iri, old_property_name, new_property_name))
                else:
                    cursor.execute("""
                        UPDATE property_mappings
                        SET migration_status = 'applied',
                            migration_date = NOW()
                        WHERE project_id = %s AND graph_iri = %s AND class_name = %s
                        AND old_property_name = %s AND new_property_name = %s
                    """, (project_id, graph_iri, class_name, old_property_name, new_property_name))
                
                conn.commit()
                
                result = {
                    "success": True,
                    "migrated_count": migrated_count,
                    "skipped_count": skipped_count,
                    "total_checked": len(rows)
                }
                
                logger.info(f"Migrated {migrated_count} individuals for {class_name}.{old_property_name} -> {new_property_name}")
                return result
                
        except Exception as e:
            logger.error(f"Error migrating individuals: {e}")
            # Update mapping status to failed
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE property_mappings
                        SET migration_status = 'failed'
                        WHERE project_id = %s AND graph_iri = %s AND class_name = %s
                        AND old_property_name = %s AND new_property_name = %s
                    """, (project_id, graph_iri, class_name, old_property_name, new_property_name))
                    conn.commit()
            except:
                pass
            
            return {
                "success": False,
                "error": str(e),
                "migrated_count": 0,
                "skipped_count": 0
            }
    
    def get_affected_individuals_count(
        self,
        project_id: str,
        graph_iri: str,
        class_name: str,
        old_property_name: str
    ) -> int:
        """Get count of individuals that would be affected by migration"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM individual_instances ii
                    JOIN individual_tables_config itc ON ii.table_id = itc.table_id
                    WHERE itc.project_id = %s
                    AND itc.graph_iri = %s
                    AND ii.class_name = %s
                    AND ii.properties ? %s
                """, (project_id, graph_iri, class_name, old_property_name))
                
                return cursor.fetchone()[0]
                
        except Exception as e:
            logger.error(f"Error counting affected individuals: {e}")
            return 0
    
    def skip_mapping(
        self,
        project_id: str,
        graph_iri: str,
        class_name: str,
        old_property_name: str,
        new_property_name: str
    ):
        """Mark a mapping as skipped"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE property_mappings
                    SET migration_status = 'skipped'
                    WHERE project_id = %s AND graph_iri = %s AND class_name = %s
                    AND old_property_name = %s AND new_property_name = %s
                """, (project_id, graph_iri, class_name, old_property_name, new_property_name))
                
                conn.commit()
                logger.info(f"Skipped property mapping: {old_property_name} -> {new_property_name}")
                
        except Exception as e:
            logger.error(f"Error skipping mapping: {e}")
    
    def migrate_class_rename(
        self,
        project_id: str,
        graph_iri: str,
        old_class_name: str,
        new_class_name: str
    ) -> Dict[str, Any]:
        """
        Migrate individuals from old class name to new class name
        
        Returns:
            Dict with migration results
        """
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Update all individuals with the old class name
                cursor.execute("""
                    UPDATE individual_instances ii
                    SET class_name = %s, updated_at = NOW()
                    FROM individual_tables_config itc
                    WHERE ii.table_id = itc.table_id
                    AND itc.project_id = %s
                    AND itc.graph_iri = %s
                    AND ii.class_name = %s
                """, (new_class_name, project_id, graph_iri, old_class_name))
                
                migrated_count = cursor.rowcount
                conn.commit()
                
                result = {
                    "success": True,
                    "migrated_count": migrated_count,
                    "old_class_name": old_class_name,
                    "new_class_name": new_class_name
                }
                
                logger.info(f"Migrated {migrated_count} individuals from {old_class_name} to {new_class_name}")
                return result
                
        except Exception as e:
            logger.error(f"Error migrating class rename: {e}")
            return {
                "success": False,
                "error": str(e),
                "migrated_count": 0
            }
    
    def migrate_object_property(
        self,
        project_id: str,
        graph_iri: str,
        old_property_name: str,
        new_property_name: str,
        old_property_iri: Optional[str] = None,
        new_property_iri: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Migrate object property relationships in Fuseki
        
        Returns:
            Dict with migration results
        """
        try:
            # Construct IRIs if not provided
            if not old_property_iri:
                old_property_iri = f"{graph_iri}#{old_property_name.replace(' ', '')}"
            if not new_property_iri:
                new_property_iri = f"{graph_iri}#{new_property_name.replace(' ', '')}"
            
            # Create SPARQL UPDATE query to rename all triples
            sparql_query = f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

DELETE {{
  GRAPH <{graph_iri}> {{
    ?s <{old_property_iri}> ?o .
  }}
}}
INSERT {{
  GRAPH <{graph_iri}> {{
    ?s <{new_property_iri}> ?o .
  }}
}}
WHERE {{
  GRAPH <{graph_iri}> {{
    ?s <{old_property_iri}> ?o .
  }}
}}
"""
            
            # Execute SPARQL update
            sparql = SPARQLWrapper(self.settings.fuseki_url + "/update")
            sparql.setQuery(sparql_query)
            sparql.method = "POST"
            sparql.query()
            
            # Count affected triples
            count_query = f"""
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT (COUNT(*) as ?count)
WHERE {{
  GRAPH <{graph_iri}> {{
    ?s <{new_property_iri}> ?o .
  }}
}}
"""
            
            sparql = SPARQLWrapper(self.settings.fuseki_url + "/query")
            sparql.setQuery(count_query)
            sparql.setReturnFormat(JSON)
            results = sparql.query().convert()
            
            migrated_count = int(results["results"]["bindings"][0]["count"]["value"])
            
            logger.info(f"Migrated {migrated_count} object property relationships: {old_property_name} -> {new_property_name}")
            
            return {
                "success": True,
                "migrated_count": migrated_count,
                "skipped_count": 0,
                "total_checked": migrated_count
            }
            
        except Exception as e:
            logger.error(f"Error migrating object property: {e}")
            return {
                "success": False,
                "error": str(e),
                "migrated_count": 0,
                "skipped_count": 0
            }
