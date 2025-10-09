"""
Individual Table Manager

Manages individual table generation, data mapping, and CRUD operations
for ontology instances. Works with any ontology structure dynamically.
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from .constraint_analyzer import ConstraintAnalyzer
import psycopg2

logger = logging.getLogger(__name__)

def get_db_connection():
    """Get raw database connection for complex queries."""
    from .config import Settings
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
        raise e

class IndividualTableManager:
    """
    Manages individual tables for ontology classes
    """
    
    def __init__(self):
        self.constraint_analyzer = ConstraintAnalyzer()
    
    def analyze_ontology_for_tables(self, ontology_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze ontology JSON to prepare for individual table generation
        """
        try:
            logger.info("🔍 Analyzing ontology for individual tables")
            
            # Transform to standard structure
            from ..api.individuals import transform_json_to_structure
            structure = transform_json_to_structure(ontology_json)
            
            # Analyze constraints for each property
            constraints = self.constraint_analyzer.analyze_property_constraints(structure)
            
            # Generate form configurations for each class
            class_configs = {}
            for cls in structure.get("classes", []):
                class_name = cls["name"]
                form_config = self.constraint_analyzer.generate_form_config(class_name, structure)
                class_configs[class_name] = form_config
            
            # Enhanced structure with constraint information
            enhanced_structure = structure.copy()
            enhanced_structure["constraints"] = constraints
            enhanced_structure["form_configs"] = class_configs
            enhanced_structure["enumerations"] = self.constraint_analyzer.get_enumeration_constraints(structure)
            
            logger.info(f"✅ Ontology analysis complete: {len(structure['classes'])} classes, {len(constraints)} property constraints")
            return enhanced_structure
            
        except Exception as e:
            logger.error(f"❌ Error analyzing ontology: {e}")
            raise e
    
    def get_requirements_mapping_config(self) -> Dict[str, str]:
        """
        Get default mapping configuration for importing Requirements Workbench data
        """
        return {
            "requirement_name": "rdfs:label",
            "requirement_text": "rdfs:comment", 
            "verification_method": "definition",
            "requirement_id": "dc:identifier",
            "priority": "priority",
            "status": "status"
        }
    
    async def import_requirements_as_individuals(
        self,
        project_id: str,
        graph_iri: str,
        requirement_ids: List[str],
        mapping_config: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Import requirements from Requirements Workbench as Requirement individuals
        """
        try:
            logger.info(f"🔍 Importing {len(requirement_ids)} requirements as individuals")
            
            if not mapping_config:
                mapping_config = self.get_requirements_mapping_config()
            
            imported_count = 0
            errors = []
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                for req_id in requirement_ids:
                    try:
                        # Get requirement data from Requirements Workbench
                        cursor.execute("""
                            SELECT requirement_name, requirement_text, verification_method,
                                   priority, created_at
                            FROM requirements_enhanced 
                            WHERE requirement_id = %s AND project_id = %s
                        """, (req_id, project_id))
                        
                        req_data = cursor.fetchone()
                        if not req_data:
                            errors.append(f"Requirement {req_id} not found")
                            continue
                        
                        # Map to individual properties using mapping config
                        individual_data = self._map_requirement_to_individual(req_data, req_id, mapping_config)
                        
                        # Store in individual_instances table
                        await self._store_individual_instance(
                            project_id, graph_iri, "Requirement", individual_data
                        )
                        
                        imported_count += 1
                        
                    except Exception as e:
                        logger.error(f"❌ Error importing requirement {req_id}: {e}")
                        errors.append(f"Failed to import {req_id}: {str(e)}")
            
            result = {
                "success": True,
                "imported_count": imported_count,
                "total_requested": len(requirement_ids),
                "errors": errors
            }
            
            logger.info(f"✅ Requirements import complete: {imported_count}/{len(requirement_ids)} successful")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error importing requirements: {e}")
            raise e
    
    def _map_requirement_to_individual(
        self, 
        req_data: tuple,
        req_id: str,
        mapping_config: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Map requirement data to individual properties
        """
        requirement_name, requirement_text, verification_method, priority, created_at = req_data
        
        # Basic mapping
        individual_data = {
            "name": requirement_name or f"Requirement_{req_id}",
            "properties": {
                "dc:identifier": req_id,
                "source_type": "requirements_workbench",
                "imported_at": datetime.utcnow().isoformat()
            }
        }
        
        # Apply mapping configuration
        if requirement_text and "rdfs:comment" in mapping_config.values():
            individual_data["properties"]["rdfs:comment"] = requirement_text
        
        if verification_method and "definition" in mapping_config.values():
            individual_data["properties"]["definition"] = verification_method
        
        if priority:
            individual_data["properties"]["priority"] = priority
        
        return individual_data
    
    async def _store_individual_instance(
        self,
        project_id: str,
        graph_iri: str, 
        class_name: str,
        individual_data: Dict[str, Any]
    ):
        """
        Store individual instance in database
        """
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
                        table_id, project_id, graph_iri, ontology_label, ontology_structure
                    ) VALUES (%s, %s, %s, %s, %s)
                """, (table_id, project_id, graph_iri, "Auto-created", "{}"))
            else:
                table_id = result[0]
            
            # Store individual instance
            instance_id = str(uuid.uuid4())
            instance_uri = f"{graph_iri}#{individual_data['name']}_{instance_id[:8]}"
            
            cursor.execute("""
                INSERT INTO individual_instances (
                    instance_id, table_id, class_name, instance_name,
                    instance_uri, properties, source_type
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                instance_id, table_id, class_name, individual_data["name"],
                instance_uri, json.dumps(individual_data["properties"]),
                "requirements_workbench"
            ))
            
            conn.commit()
    
    def generate_add_form_html(self, class_name: str, form_config: Dict[str, Any]) -> str:
        """
        Generate HTML form for adding individuals with constraint-aware controls
        """
        html = f"""
        <div class="add-individual-form">
            <h4>Add New {class_name}</h4>
            <form id="addIndividualForm" onsubmit="submitNewIndividual(event, '{class_name}')">
        """
        
        for field in form_config.get("fields", []):
            html += self._generate_field_html(field)
        
        html += """
            <div class="form-actions" style="margin-top: 20px; display: flex; gap: 8px;">
                <button type="submit" class="btn btn-success">Create Individual</button>
                <button type="button" class="btn" onclick="cancelAddIndividual()">Cancel</button>
            </div>
            </form>
        </div>
        """
        
        return html
    
    def _generate_field_html(self, field: Dict[str, Any]) -> str:
        """
        Generate HTML for individual form field based on constraints
        """
        field_name = field["name"]
        field_label = field.get("label", field_name)
        control_type = field.get("control_type", "text")
        required = field.get("required", False)
        
        html = f"""
        <div class="form-group" style="margin-bottom: 16px;">
            <label for="{field_name}" style="display: block; margin-bottom: 4px; color: var(--text);">
                {field_label}{' *' if required else ''}
            </label>
        """
        
        if control_type == "dropdown" and field.get("enumeration_values"):
            # Enumeration dropdown
            html += f'<select name="{field_name}" id="{field_name}" class="form-control" style="width: 100%; padding: 8px; background: var(--panel); color: var(--text); border: 1px solid var(--border);" {"required" if required else ""}>'
            
            if not required:
                html += '<option value="">-- Select --</option>'
            
            for enum_value in field["enumeration_values"]:
                selected = 'selected' if enum_value == field.get("default_value") else ''
                html += f'<option value="{enum_value}" {selected}>{enum_value}</option>'
            
            html += '</select>'
            
        elif control_type == "checkbox":
            # Boolean checkbox
            html += f"""
            <input type="checkbox" name="{field_name}" id="{field_name}" class="form-control">
            <label for="{field_name}" style="display: inline; margin-left: 8px;">{field.get("comment", "")}</label>
            """
            
        else:
            # Standard input fields
            input_type = field.get("input_type", "text")
            placeholder = field.get("placeholder", "")
            step = field.get("step", "")
            
            html += f"""
            <input 
                type="{input_type}" 
                name="{field_name}" 
                id="{field_name}"
                class="form-control"
                style="width: 100%; padding: 8px; background: var(--panel); color: var(--text); border: 1px solid var(--border);"
                placeholder="{placeholder}"
                {"step=" + step if step else ""}
                {"required" if required else ""}
            >
            """
        
        # Add field description if available
        if field.get("comment"):
            html += f'<small style="color: var(--muted); font-size: 12px;">{field["comment"]}</small>'
        
        html += '</div>'
        return html
