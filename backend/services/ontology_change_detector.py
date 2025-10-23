"""
Ontology Change Detection Service

Detects changes to ontology elements when ontologies are saved.
Compares old and new versions to identify:
- Added elements
- Deleted elements
- Renamed elements (detected via heuristics)
- Modified elements (properties, types, etc.)
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from SPARQLWrapper import SPARQLWrapper, JSON
from backend.services.db import DatabaseService
from backend.services.sparql_runner import SPARQLRunner
from backend.services.cqmt_dependency_tracker import CQMTDependencyTracker
from backend.services.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class ElementChange:
    """Represents a change to an ontology element."""
    
    element_iri: str
    change_type: str  # 'added', 'deleted', 'renamed', 'modified'
    old_iri: Optional[str] = None  # For renames
    new_iri: Optional[str] = None  # For renames
    element_type: Optional[str] = None  # 'Class', 'ObjectProperty', 'DatatypeProperty', 'Individual'
    change_details: Optional[Dict] = None  # Additional metadata


@dataclass
class ChangeDetectionResult:
    """Result of change detection process."""
    
    graph_iri: str
    changes: List[ElementChange]
    affected_mts: List[str]  # List of MT IDs affected by changes
    total_added: int = 0
    total_deleted: int = 0
    total_renamed: int = 0
    total_modified: int = 0


class OntologyChangeDetector:
    """
    Detects changes to ontology elements when ontologies are saved.
    
    Compares the current state in Fuseki with incoming Turtle content
    to identify what changed.
    """
    
    def __init__(self, db_service: DatabaseService, fuseki_url: str = "http://localhost:3030"):
        self.db = db_service
        self.runner = SPARQLRunner(fuseki_url)
        self.dependency_tracker = CQMTDependencyTracker(db_service, fuseki_url)
        self.settings = Settings()
    
    def detect_changes(self, graph_iri: str, new_turtle_content: str) -> ChangeDetectionResult:
        """
        Detect changes by comparing old ontology with new content.
        
        Args:
            graph_iri: The ontology graph IRI
            new_turtle_content: The new Turtle content being saved
            
        Returns:
            ChangeDetectionResult with detected changes and affected MTs
        """
        try:
            # Get current state from Fuseki
            old_elements = self._get_current_elements(graph_iri)
            
            # Parse new content to get elements
            new_elements = self._parse_turtle_elements(new_turtle_content)
            
            # Compare and detect changes
            changes = self._compare_elements(old_elements, new_elements)
            
            # Find affected MTs
            affected_mts = self._find_affected_mts(graph_iri, changes)
            
            # Create result
            result = ChangeDetectionResult(
                graph_iri=graph_iri,
                changes=changes,
                affected_mts=affected_mts,
                total_added=len([c for c in changes if c.change_type == 'added']),
                total_deleted=len([c for c in changes if c.change_type == 'deleted']),
                total_renamed=len([c for c in changes if c.change_type == 'renamed']),
                total_modified=len([c for c in changes if c.change_type == 'modified'])
            )
            
            logger.info(f"Detected {len(changes)} changes to {graph_iri}: "
                       f"{result.total_added} added, {result.total_deleted} deleted, "
                       f"{result.total_renamed} renamed, {result.total_modified} modified")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to detect changes for {graph_iri}: {e}")
            # Return empty result on error
            return ChangeDetectionResult(
                graph_iri=graph_iri,
                changes=[],
                affected_mts=[]
            )
    
    def _get_current_elements(self, graph_iri: str) -> Dict[str, Dict]:
        """
        Get current ontology elements from Fuseki.
        
        Returns:
            Dict mapping element IRI to element metadata
        """
        try:
            # Query for classes, properties, and individuals
            query = f"""
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            SELECT ?iri ?type ?label ?comment WHERE {{
                GRAPH <{graph_iri}> {{
                    {{
                        ?iri a owl:Class .
                        BIND("Class" as ?type)
                    }} UNION {{
                        ?iri a owl:ObjectProperty .
                        BIND("ObjectProperty" as ?type)
                    }} UNION {{
                        ?iri a owl:DatatypeProperty .
                        BIND("DatatypeProperty" as ?type)
                    }} UNION {{
                        ?iri rdf:type ?class .
                        ?class a owl:Class .
                        BIND("Individual" as ?type)
                    }}
                    OPTIONAL {{ ?iri rdfs:label ?label }}
                    OPTIONAL {{ ?iri rdfs:comment ?comment }}
                }}
            }}
            """
            
            result = self.runner._execute_sparql_select(query)
            if not result["success"]:
                logger.warning(f"Failed to query current elements for {graph_iri}")
                return {}
            
            elements = {}
            bindings = result["data"].get("results", {}).get("bindings", [])
            
            for binding in bindings:
                iri = binding.get("iri", {}).get("value", "")
                if iri:
                    elements[iri] = {
                        "type": binding.get("type", {}).get("value", "Other"),
                        "label": binding.get("label", {}).get("value", ""),
                        "comment": binding.get("comment", {}).get("value", "")
                    }
                    # Debug logging
                    logger.debug(f"Found element: {iri}, type: {elements[iri]['type']}, label: '{elements[iri]['label']}'")
            
            logger.info(f"Total elements found: {len(elements)}")
            return elements
            
        except Exception as e:
            logger.error(f"Error getting current elements: {e}")
            return {}
    
    def _parse_turtle_elements(self, turtle_content: str) -> Dict[str, Dict]:
        """
        Parse Turtle content to extract element IRIs.
        
        This parser handles:
        - Prefix declarations (@prefix)
        - Class declarations
        - Property declarations  
        - Individual declarations
        - Labels and comments
        
        Returns:
            Dict mapping element IRI to element metadata
        """
        elements = {}
        
        try:
            import re
            
            # Step 1: Extract prefix declarations
            prefixes = {}
            prefix_pattern = r'@prefix\s+(\w+):\s+<([^>]+)>'
            for match in re.finditer(prefix_pattern, turtle_content):
                prefix_name = match.group(1)
                prefix_value = match.group(2)
                prefixes[prefix_name] = prefix_value
            
            # Also handle default (empty) prefix
            default_prefix_pattern = r'@prefix\s+:\s+<([^>]+)>'
            for match in re.finditer(default_prefix_pattern, turtle_content):
                prefix_value = match.group(1)
                prefixes[''] = prefix_value
            
            # Step 2: Helper function to resolve IRIs
            def resolve_iri(iri_str: str) -> str:
                """Resolve shorthand IRI to full IRI."""
                # If already full IRI, return as-is
                if iri_str.startswith('<') and iri_str.endswith('>'):
                    return iri_str[1:-1]
                
                # If shorthand with prefix (e.g., owl:Class)
                if ':' in iri_str:
                    parts = iri_str.split(':', 1)
                    prefix_name = parts[0]
                    local_name = parts[1]
                    
                    if prefix_name in prefixes:
                        return f"{prefixes[prefix_name]}{local_name}"
                    # Well-known prefixes
                    if prefix_name == 'owl':
                        return f"http://www.w3.org/2002/07/owl#{local_name}"
                    if prefix_name == 'rdfs':
                        return f"http://www.w3.org/2000/01/rdf-schema#{local_name}"
                    if prefix_name == 'rdf':
                        return f"http://www.w3.org/1999/02/22-rdf-syntax-ns#{local_name}"
                
                # If shorthand without prefix (e.g., :Person) - use default prefix
                if iri_str.startswith(':'):
                    local_name = iri_str[1:]
                    if '' in prefixes:
                        return f"{prefixes['']}{local_name}"
                
                return iri_str
            
            # Step 3: Find class declarations
            class_patterns = [
                r'<([^>]+)>\s+a\s+owl:Class',  # Full IRI
                r':(\w+)\s+a\s+owl:Class',     # Shorthand
            ]
            for pattern in class_patterns:
                for match in re.finditer(pattern, turtle_content):
                    iri_raw = match.group(1)
                    iri = resolve_iri(iri_raw)
                    elements[iri] = {"type": "Class", "label": "", "comment": ""}
            
            # Step 4: Find object property declarations
            obj_prop_patterns = [
                r'<([^>]+)>\s+a\s+owl:ObjectProperty',
                r':(\w+)\s+a\s+owl:ObjectProperty',
            ]
            for pattern in obj_prop_patterns:
                for match in re.finditer(pattern, turtle_content):
                    iri_raw = match.group(1)
                    iri = resolve_iri(iri_raw)
                    elements[iri] = {"type": "ObjectProperty", "label": "", "comment": ""}
            
            # Step 5: Find datatype property declarations
            data_prop_patterns = [
                r'<([^>]+)>\s+a\s+owl:DatatypeProperty',
                r':(\w+)\s+a\s+owl:DatatypeProperty',
            ]
            for pattern in data_prop_patterns:
                for match in re.finditer(pattern, turtle_content):
                    iri_raw = match.group(1)
                    iri = resolve_iri(iri_raw)
                    elements[iri] = {"type": "DatatypeProperty", "label": "", "comment": ""}
            
            # Step 6: Find individual type declarations (but don't override classes/properties)
            individual_patterns = [
                r'<([^>]+)>\s+a\s+<([^>]+)>',
                r':(\w+)\s+a\s+:(\w+)',
            ]
            for pattern in individual_patterns:
                for match in re.finditer(pattern, turtle_content):
                    iri_raw = match.group(1)
                    iri = resolve_iri(iri_raw)
                    if iri not in elements:
                        elements[iri] = {"type": "Individual", "label": "", "comment": ""}
            
            # Step 7: Extract labels
            label_patterns = [
                r'<([^>]+)>\s+rdfs:label\s+"([^"]+)"',
                r':(\w+)\s+rdfs:label\s+"([^"]+)"',
            ]
            for pattern in label_patterns:
                for match in re.finditer(pattern, turtle_content):
                    iri_raw = match.group(1)
                    iri = resolve_iri(iri_raw)
                    label = match.group(2)
                    if iri in elements:
                        elements[iri]["label"] = label
            
            # Step 8: Extract comments
            comment_patterns = [
                r'<([^>]+)>\s+rdfs:comment\s+"([^"]+)"',
                r':(\w+)\s+rdfs:comment\s+"([^"]+)"',
            ]
            for pattern in comment_patterns:
                for match in re.finditer(pattern, turtle_content):
                    iri_raw = match.group(1)
                    iri = resolve_iri(iri_raw)
                    comment = match.group(2)
                    if iri in elements:
                        elements[iri]["comment"] = comment
                    
        except Exception as e:
            logger.error(f"Error parsing Turtle content: {e}")
        
        return elements
    
    def _compare_elements(self, old_elements: Dict[str, Dict], new_elements: Dict[str, Dict]) -> List[ElementChange]:
        """
        Compare old and new elements to detect changes.
        
        Returns:
            List of ElementChange objects
        """
        changes = []
        
        old_iris = set(old_elements.keys())
        new_iris = set(new_elements.keys())
        
        # Detect additions
        for iri in new_iris - old_iris:
            new_elem = new_elements[iri]
            changes.append(ElementChange(
                element_iri=iri,
                change_type='added',
                element_type=new_elem.get("type"),
                change_details=new_elem
            ))
        
        # Detect deletions
        for iri in old_iris - new_iris:
            old_elem = old_elements[iri]
            changes.append(ElementChange(
                element_iri=iri,
                change_type='deleted',
                element_type=old_elem.get("type"),
                change_details=old_elem
            ))
        
        # Detect modifications (label changes, etc.)
        for old_iri in old_iris & new_iris:
            old_elem = old_elements[old_iri]
            new_elem = new_elements[old_iri]
            
            # Check if label changed
            old_label = old_elem.get("label", "")
            new_label = new_elem.get("label", "")
            
            # Only report as modified if we have non-empty labels that differ
            if old_label and new_label and old_label != new_label:
                changes.append(ElementChange(
                    element_iri=old_iri,
                    change_type='modified',
                    element_type=old_elem.get("type"),
                    change_details={
                        "old_label": old_label,
                        "new_label": new_label
                    }
                ))
            # Also report if label was added (was empty, now has value)
            elif not old_label and new_label:
                changes.append(ElementChange(
                    element_iri=old_iri,
                    change_type='modified',
                    element_type=old_elem.get("type"),
                    change_details={
                        "old_label": "",
                        "new_label": new_label,
                        "change": "label_added"
                    }
                ))
            # Or removed (had value, now empty)
            elif old_label and not new_label:
                changes.append(ElementChange(
                    element_iri=old_iri,
                    change_type='modified',
                    element_type=old_elem.get("type"),
                    change_details={
                        "old_label": old_label,
                        "new_label": "",
                        "change": "label_removed"
                    }
                ))
        
        return changes
    
    def _find_affected_mts(self, graph_iri: str, changes: List[ElementChange]) -> List[str]:
        """
        Find MTs affected by the changes.
        
        Args:
            graph_iri: The ontology graph IRI
            changes: List of detected changes
            
        Returns:
            List of affected MT IDs
        """
        affected_mts = set()
        
        try:
            for change in changes:
                # Query dependency table for MTs referencing this element
                query = """
                SELECT DISTINCT mt_id FROM mt_ontology_dependencies
                WHERE ontology_graph_iri = %s AND referenced_element_iri = %s
                """
                
                conn = self.db._conn()
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(query, (graph_iri, change.element_iri))
                        rows = cursor.fetchall()
                        
                        for row in rows:
                            affected_mts.add(str(row[0]))
                finally:
                    self.db.pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Error finding affected MTs: {e}")
        
        return list(affected_mts)
    
    def classify_change(self, change: ElementChange) -> str:
        """
        Classify a change as breaking, compatible, or enhancement.
        
        Returns:
            'breaking', 'compatible', or 'enhancement'
        """
        if change.change_type == 'deleted':
            return 'breaking'
        elif change.change_type == 'renamed':
            return 'breaking'
        elif change.change_type == 'added':
            return 'enhancement'
        else:
            return 'compatible'
