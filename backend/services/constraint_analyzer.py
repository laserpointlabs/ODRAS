"""
Constraint Analyzer Service

Analyzes ontology properties to extract constraints for individual table generation:
- Enumeration constraints -> Dropdown controls
- Multiplicity constraints -> Required/optional field validation  
- Data type constraints -> Input type selection
- Range constraints -> Validation rules
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class ConstraintAnalyzer:
    """
    Analyzes ontology structure to extract constraints for individual table generation
    """
    
    def analyze_property_constraints(self, ontology_structure: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Analyze all properties in ontology to extract constraints
        
        Returns:
            Dict mapping property names to constraint information
        """
        constraints = {}
        
        # Analyze object properties
        for prop in ontology_structure.get("object_properties", []):
            constraints[prop["name"]] = self._analyze_property(prop)
        
        # Analyze datatype properties  
        for prop in ontology_structure.get("datatype_properties", []):
            constraints[prop["name"]] = self._analyze_property(prop)
        
        return constraints
    
    def _analyze_property(self, property_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze individual property to extract constraints
        """
        constraints = {
            "property_name": property_data.get("name", ""),
            "property_type": property_data.get("type", "datatype"),
            "domain": property_data.get("domain", ""),
            "range": property_data.get("range", ""),
            "comment": property_data.get("comment", ""),
        }
        
        # Extract enumeration constraints
        enumeration = property_data.get("constraints", {}).get("enumeration", [])
        if enumeration and isinstance(enumeration, list) and len(enumeration) > 0:
            constraints.update({
                "control_type": "dropdown",
                "enumeration_values": enumeration,
                "default_value": enumeration[0] if enumeration else None,
                "validation_type": "enumeration",
                "input_type": "select"  # Override input type for enumerations
            })
        
        # Extract multiplicity constraints
        min_count = property_data.get("constraints", {}).get("min_count")
        max_count = property_data.get("constraints", {}).get("max_count")
        
        if min_count is not None or max_count is not None:
            constraints.update({
                "min_count": min_count,
                "max_count": max_count,
                "required": (min_count or 0) > 0,
                "multiplicity_display": self._format_multiplicity(min_count, max_count)
            })
        
        # Extract data type constraints
        data_range = property_data.get("range", "")
        if data_range:
            constraints.update(self._analyze_data_type(data_range))
        
        return constraints
    
    def _format_multiplicity(self, min_count: Optional[int], max_count: Optional[int]) -> str:
        """
        Format multiplicity constraints for display
        """
        if min_count is None and max_count is None:
            return "(0..*)"
        elif min_count is not None and max_count is None:
            return f"({min_count}..*)"
        elif min_count is None and max_count is not None:
            return f"(0..{max_count})"
        elif min_count == max_count:
            return f"({min_count})"
        else:
            return f"({min_count}..{max_count})"
    
    def _analyze_data_type(self, data_range: str) -> Dict[str, Any]:
        """
        Analyze data type to determine appropriate input control
        """
        range_lower = data_range.lower()
        
        if "string" in range_lower:
            return {
                "control_type": "text",
                "input_type": "text",
                "validation_type": "string"
            }
        elif "int" in range_lower:
            return {
                "control_type": "number",
                "input_type": "number",
                "validation_type": "integer"
            }
        elif "decimal" in range_lower or "double" in range_lower:
            return {
                "control_type": "number",
                "input_type": "number",
                "validation_type": "decimal",
                "step": "0.01"
            }
        elif "boolean" in range_lower:
            return {
                "control_type": "checkbox",
                "input_type": "checkbox",
                "validation_type": "boolean"
            }
        elif "date" in range_lower:
            return {
                "control_type": "date",
                "input_type": "date",
                "validation_type": "date"
            }
        elif "uri" in range_lower or "url" in range_lower:
            return {
                "control_type": "url",
                "input_type": "url", 
                "validation_type": "url",
                "placeholder": "https://example.com/resource"
            }
        else:
            # Default to text
            return {
                "control_type": "text",
                "input_type": "text",
                "validation_type": "string"
            }
    
    def generate_form_config(self, class_name: str, ontology_structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate complete form configuration for a class
        """
        constraints = self.analyze_property_constraints(ontology_structure)
        
        # Get properties for this class
        class_properties = []
        
        for prop in ontology_structure.get("object_properties", []):
            if prop.get("domain") == class_name:
                class_properties.append(prop["name"])
        
        for prop in ontology_structure.get("datatype_properties", []):
            if prop.get("domain") == class_name:
                class_properties.append(prop["name"])
        
        # Build form configuration
        form_config = {
            "class_name": class_name,
            "fields": []
        }
        
        # Always include name field
        form_config["fields"].append({
            "name": "name",
            "label": "Name",
            "control_type": "text",
            "required": True,
            "validation_type": "string"
        })
        
        # Add property-based fields
        for prop_name in class_properties:
            if prop_name in constraints:
                field_config = constraints[prop_name].copy()
                field_config["name"] = prop_name
                field_config["label"] = field_config.get("property_name", prop_name).replace("_", " ").title()
                
                # Override control type based on enumeration presence
                if field_config.get("enumeration_values"):
                    field_config["control_type"] = "dropdown"
                    field_config["input_type"] = "select"
                
                form_config["fields"].append(field_config)
        
        return form_config
    
    def validate_individual_data(
        self,
        individual_data: Dict[str, Any],
        constraints: Dict[str, Dict[str, Any]]
    ) -> Tuple[bool, List[str]]:
        """
        Validate individual data against extracted constraints
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        for field_name, field_value in individual_data.items():
            if field_name in constraints:
                constraint = constraints[field_name]
                
                # Required field validation
                if constraint.get("required", False) and not field_value:
                    errors.append(f"Field '{field_name}' is required")
                    continue
                
                # Skip further validation if field is empty and not required
                if not field_value:
                    continue
                
                # Enumeration validation
                if constraint.get("validation_type") == "enumeration":
                    allowed_values = constraint.get("enumeration_values", [])
                    if field_value not in allowed_values:
                        errors.append(
                            f"Field '{field_name}' value '{field_value}' not in allowed values: {', '.join(allowed_values)}"
                        )
                
                # Data type validation
                validation_type = constraint.get("validation_type", "string")
                if not self._validate_data_type(field_value, validation_type):
                    errors.append(f"Field '{field_name}' has invalid {validation_type} format")
        
        return len(errors) == 0, errors
    
    def _validate_data_type(self, value: Any, validation_type: str) -> bool:
        """
        Validate value against data type constraint
        """
        if validation_type == "string":
            return isinstance(value, str)
        elif validation_type == "integer":
            try:
                int(value)
                return True
            except (ValueError, TypeError):
                return False
        elif validation_type == "decimal":
            try:
                float(value)
                return True
            except (ValueError, TypeError):
                return False
        elif validation_type == "boolean":
            return isinstance(value, bool) or str(value).lower() in ['true', 'false', '1', '0']
        elif validation_type == "url":
            import re
            url_pattern = r'^https?://.+'
            return bool(re.match(url_pattern, str(value)))
        elif validation_type == "date":
            import re
            date_pattern = r'^\d{4}-\d{2}-\d{2}$'
            return bool(re.match(date_pattern, str(value)))
        else:
            return True  # Unknown type, assume valid
    
    def get_enumeration_constraints(self, ontology_structure: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Extract just enumeration constraints for quick reference
        
        Returns:
            Dict mapping property names to their enumeration values
        """
        enumerations = {}
        
        # Check object properties
        for prop in ontology_structure.get("object_properties", []):
            enumeration = prop.get("constraints", {}).get("enumeration", [])
            if enumeration:
                enumerations[prop["name"]] = enumeration
        
        # Check datatype properties
        for prop in ontology_structure.get("datatype_properties", []):
            enumeration = prop.get("constraints", {}).get("enumeration", [])
            if enumeration:
                enumerations[prop["name"]] = enumeration
        
        return enumerations
