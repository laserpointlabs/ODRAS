"""
CQMT Dependency Tracker Service
Tracks dependencies between Microtheories and ontology elements (classes, properties).
"""

import logging
import re
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from datetime import datetime

from .db import DatabaseService
from .sparql_runner import SPARQLRunner
from .config import Settings

logger = logging.getLogger(__name__)


@dataclass
class Dependency:
    """Represents a dependency between an MT and an ontology element."""
    mt_id: str
    ontology_graph_iri: str
    referenced_element_iri: str
    element_type: str  # 'Class', 'ObjectProperty', 'DatatypeProperty', 'Individual', 'Other'
    is_valid: bool = True


class CQMTDependencyTracker:
    """
    Tracks dependencies between Microtheories and ontology elements.
    
    Extracts IRIs from MT triples, stores dependencies, and validates them.
    """
    
    def __init__(self, db_service: DatabaseService, fuseki_url: str = "http://localhost:3030"):
        self.db = db_service
        self.runner = SPARQLRunner(fuseki_url)
        self.settings = Settings()
    
    def extract_dependencies(self, mt_iri: str) -> List[Dependency]:
        """
        Parse MT triples and extract referenced ontology IRIs.
        
        Args:
            mt_iri: Microtheory IRI
            
        Returns:
            List of Dependency objects
        """
        try:
            # Get all triples from the microtheory
            triples_result = self.runner.get_all_triples_from_graph(mt_iri)
            
            if not triples_result["success"]:
                logger.warning(f"Failed to get triples from MT {mt_iri}")
                return []
            
            triples = triples_result["triples"]
            dependencies = []
            seen_iris = set()
            
            # Extract IRIs from triples
            for triple in triples:
                # Check subject
                subj_iri = self._extract_iri(triple.get("subject", ""))
                if subj_iri and subj_iri not in seen_iris:
                    element_type = self._classify_element(subj_iri)
                    dependencies.append(Dependency(
                        mt_id="",  # Will be filled when storing
                        ontology_graph_iri=self._extract_graph_iri(subj_iri),
                        referenced_element_iri=subj_iri,
                        element_type=element_type
                    ))
                    seen_iris.add(subj_iri)
                
                # Check predicate
                pred_iri = self._extract_iri(triple.get("predicate", ""))
                if pred_iri and pred_iri not in seen_iris:
                    element_type = self._classify_element(pred_iri)
                    dependencies.append(Dependency(
                        mt_id="",
                        ontology_graph_iri=self._extract_graph_iri(pred_iri),
                        referenced_element_iri=pred_iri,
                        element_type=element_type
                    ))
                    seen_iris.add(pred_iri)
                
                # Check object
                obj_iri = self._extract_iri(triple.get("object", ""))
                if obj_iri and obj_iri not in seen_iris:
                    element_type = self._classify_element(obj_iri)
                    dependencies.append(Dependency(
                        mt_id="",
                        ontology_graph_iri=self._extract_graph_iri(obj_iri),
                        referenced_element_iri=obj_iri,
                        element_type=element_type
                    ))
                    seen_iris.add(obj_iri)
            
            logger.info(f"Extracted {len(dependencies)} dependencies from MT {mt_iri}")
            return dependencies
            
        except Exception as e:
            logger.error(f"Error extracting dependencies from MT {mt_iri}: {e}")
            return []
    
    def store_dependencies(self, mt_id: str, dependencies: List[Dependency]) -> bool:
        """
        Store dependencies in the database.
        
        Args:
            mt_id: Microtheory UUID
            dependencies: List of Dependency objects
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self.db._conn()
            try:
                with conn.cursor() as cur:
                    # Clear existing dependencies for this MT
                    cur.execute(
                        "DELETE FROM mt_ontology_dependencies WHERE mt_id = %s",
                        (mt_id,)
                    )
                    
                    # Insert new dependencies
                    for dep in dependencies:
                        cur.execute("""
                            INSERT INTO mt_ontology_dependencies 
                            (mt_id, ontology_graph_iri, referenced_element_iri, element_type, is_valid)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            mt_id,
                            dep.ontology_graph_iri,
                            dep.referenced_element_iri,
                            dep.element_type,
                            dep.is_valid
                        ))
                    
                    conn.commit()
                    logger.info(f"Stored {len(dependencies)} dependencies for MT {mt_id}")
                    return True
                    
            finally:
                self.db._return(conn)
                
        except Exception as e:
            logger.error(f"Error storing dependencies for MT {mt_id}: {e}")
            return False
    
    def validate_dependencies(self, mt_id: str) -> Dict[str, Any]:
        """
        Validate that all dependencies still exist in their respective ontologies.
        
        Args:
            mt_id: Microtheory UUID
            
        Returns:
            {
                "valid": bool,
                "total": int,
                "valid_count": int,
                "invalid_count": int,
                "invalid_dependencies": list
            }
        """
        try:
            conn = self.db._conn()
            try:
                with conn.cursor() as cur:
                    # Get all dependencies for this MT
                    cur.execute("""
                        SELECT id, ontology_graph_iri, referenced_element_iri, element_type
                        FROM mt_ontology_dependencies
                        WHERE mt_id = %s
                    """, (mt_id,))
                    
                    deps = cur.fetchall()
                    
                    total = len(deps)
                    valid_count = 0
                    invalid_count = 0
                    invalid_deps = []
                    
                    # Validate each dependency
                    for dep in deps:
                        dep_id, graph_iri, element_iri, element_type = dep
                        
                        # Check if element exists in ontology
                        exists = self._check_element_exists(graph_iri, element_iri, element_type)
                        
                        if exists:
                            valid_count += 1
                            # Update to valid
                            cur.execute("""
                                UPDATE mt_ontology_dependencies
                                SET is_valid = TRUE, last_validated_at = NOW()
                                WHERE id = %s
                            """, (dep_id,))
                        else:
                            invalid_count += 1
                            invalid_deps.append({
                                "element_iri": element_iri,
                                "element_type": element_type,
                                "graph_iri": graph_iri
                            })
                            # Update to invalid
                            cur.execute("""
                                UPDATE mt_ontology_dependencies
                                SET is_valid = FALSE, last_validated_at = NOW()
                                WHERE id = %s
                            """, (dep_id,))
                    
                    conn.commit()
                    
                    return {
                        "valid": invalid_count == 0,
                        "total": total,
                        "valid_count": valid_count,
                        "invalid_count": invalid_count,
                        "invalid_dependencies": invalid_deps
                    }
                    
            finally:
                self.db._return(conn)
                
        except Exception as e:
            logger.error(f"Error validating dependencies for MT {mt_id}: {e}")
            return {
                "valid": False,
                "total": 0,
                "valid_count": 0,
                "invalid_count": 0,
                "invalid_dependencies": []
            }
    
    def get_affected_mts(self, ontology_graph_iri: str, changed_element_iri: str) -> List[str]:
        """
        Find MTs that reference a changed ontology element.
        
        Args:
            ontology_graph_iri: Ontology graph IRI
            changed_element_iri: IRI of changed element
            
        Returns:
            List of MT IDs that reference this element
        """
        try:
            conn = self.db._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT DISTINCT mt_id
                        FROM mt_ontology_dependencies
                        WHERE ontology_graph_iri = %s 
                        AND referenced_element_iri = %s
                    """, (ontology_graph_iri, changed_element_iri))
                    
                    rows = cur.fetchall()
                    return [str(row[0]) for row in rows]
                    
            finally:
                self.db._return(conn)
                
        except Exception as e:
            logger.error(f"Error getting affected MTs: {e}")
            return []
    
    def get_dependencies(self, mt_id: str) -> List[Dict[str, Any]]:
        """
        Get all dependencies for a microtheory.
        
        Args:
            mt_id: Microtheory UUID
            
        Returns:
            List of dependency dictionaries
        """
        try:
            conn = self.db._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            ontology_graph_iri,
                            referenced_element_iri,
                            element_type,
                            is_valid,
                            first_detected_at,
                            last_validated_at
                        FROM mt_ontology_dependencies
                        WHERE mt_id = %s
                        ORDER BY element_type, referenced_element_iri
                    """, (mt_id,))
                    
                    rows = cur.fetchall()
                    return [
                        {
                            "ontology_graph_iri": row[0],
                            "referenced_element_iri": row[1],
                            "element_type": row[2],
                            "is_valid": row[3],
                            "first_detected_at": row[4].isoformat() if row[4] else None,
                            "last_validated_at": row[5].isoformat() if row[5] else None
                        }
                        for row in rows
                    ]
                    
            finally:
                self.db._return(conn)
                
        except Exception as e:
            logger.error(f"Error getting dependencies for MT {mt_id}: {e}")
            return []
    
    # Helper methods
    
    def _extract_iri(self, value: str) -> Optional[str]:
        """Extract IRI from a triple value."""
        if not value:
            return None
        
        # Handle QNames like "prefix:name"
        if ":" in value and not value.startswith("http"):
            # This is a QName, we'd need prefix resolution to get full IRI
            # For now, skip QNames as we can't resolve them
            return None
        
        # Handle full IRIs in angle brackets
        if value.startswith("<") and value.endswith(">"):
            return value[1:-1]
        
        # Handle bare IRIs
        if value.startswith("http"):
            return value
        
        return None
    
    def _extract_graph_iri(self, iri: str) -> str:
        """Extract graph IRI from element IRI."""
        # Simple heuristic: strip fragment identifier
        if "#" in iri:
            return iri.rsplit("#", 1)[0] + "#"
        return iri.rsplit("/", 1)[0] + "/"
    
    def _classify_element(self, iri: str) -> str:
        """Classify element type based on IRI."""
        # Check common ontology vocabularies
        if "owl#Class" in iri or "rdfs#Class" in iri:
            return "Class"
        elif "owl#ObjectProperty" in iri or "owl#DatatypeProperty" in iri:
            return "ObjectProperty" if "ObjectProperty" in iri else "DatatypeProperty"
        elif "owl#NamedIndividual" in iri or "#" in iri:
            # Check if this looks like an individual (has local name after #)
            local_part = iri.split("#")[-1] if "#" in iri else iri.split("/")[-1]
            if local_part and local_part[0].isupper():
                return "Individual"
        
        return "Other"
    
    def _check_element_exists(self, graph_iri: str, element_iri: str, element_type: str) -> bool:
        """Check if an element exists in the ontology."""
        try:
            # For Class
            if element_type == "Class":
                query = f"""
                PREFIX owl: <http://www.w3.org/2002/07/owl#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                
                ASK {{
                    GRAPH <{graph_iri}> {{
                        <{element_iri}> a/rdfs:subClassOf* owl:Class .
                    }}
                }}
                """
            
            # For ObjectProperty
            elif element_type == "ObjectProperty":
                query = f"""
                PREFIX owl: <http://www.w3.org/2002/07/owl#>
                
                ASK {{
                    GRAPH <{graph_iri}> {{
                        <{element_iri}> a owl:ObjectProperty .
                    }}
                }}
                """
            
            # For DatatypeProperty
            elif element_type == "DatatypeProperty":
                query = f"""
                PREFIX owl: <http://www.w3.org/2002/07/owl#>
                
                ASK {{
                    GRAPH <{graph_iri}> {{
                        <{element_iri}> a owl:DatatypeProperty .
                    }}
                }}
                """
            
            # For Individual or Other
            else:
                query = f"""
                ASK {{
                    GRAPH <{graph_iri}> {{
                        <{element_iri}> ?p ?o .
                    }}
                }}
                """
            
            result = self.runner.run_ask(query)
            return result.get("success", False) and result.get("result", False)
            
        except Exception as e:
            logger.warning(f"Error checking element existence: {e}")
            return False
