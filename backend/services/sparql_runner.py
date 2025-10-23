"""
SPARQL Runner Service for CQ/MT Workbench
Provides parameter binding, graph confinement, and execution for competency questions.
"""

import logging
import re
import time
from typing import Dict, List, Any, Tuple, Optional
import httpx
from urllib.parse import quote

logger = logging.getLogger(__name__)


class SPARQLRunner:
    """
    SPARQL execution engine with parameter binding and graph confinement.
    Designed for running Competency Questions safely within specified named graphs.
    """
    
    def __init__(self, fuseki_url: str = "http://localhost:3030"):
        self.fuseki_url = fuseki_url.rstrip("/")
        # Note: fuseki_url from Settings already includes dataset (e.g., "http://localhost:3030/odras")
        self.query_url = f"{self.fuseki_url}/query"
        self.update_url = f"{self.fuseki_url}/update"
        
    def run_select_in_graph(self, graph_iri: str, sparql_template: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Bind parameters, wrap SPARQL with GRAPH clause, execute, return results.
        
        Args:
            graph_iri: Named graph IRI to confine query execution
            sparql_template: SPARQL SELECT template with {{var}} placeholders
            params: Parameter values for template binding
            
        Returns:
            {
                "columns": ["subject", "label"],
                "rows": [["ex:Thing1", "Thing One"], ["ex:Thing2", "Thing Two"]],
                "row_count": 2,
                "latency_ms": 45,
                "success": True,
                "error": None
            }
        """
        if params is None:
            params = {}
            
        try:
            # 1. Validate SPARQL template
            is_valid, error_msg = self.validate_sparql(sparql_template)
            if not is_valid:
                return {
                    "success": False,
                    "error": f"SPARQL validation failed: {error_msg}",
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "latency_ms": 0
                }
            
            # 2. Bind parameters to template
            try:
                bound_sparql = self._bind_params(sparql_template, params)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Parameter binding failed: {str(e)}",
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "latency_ms": 0
                }
            
            # 3. Wrap with GRAPH clause for confinement
            confined_sparql = self._confine_to_graph(bound_sparql, graph_iri)
            
            # 4. Execute query with latency measurement
            start_time = time.time()
            result = self._execute_sparql_select(confined_sparql)
            end_time = time.time()
            latency_ms = int((end_time - start_time) * 1000)
            
            # 5. Process results
            if result["success"]:
                columns, rows = self._process_sparql_results(result["data"])
                return {
                    "success": True,
                    "error": None,
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                    "latency_ms": latency_ms
                }
            else:
                return {
                    "success": False,
                    "error": result["error"],
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "latency_ms": latency_ms
                }
                
        except Exception as e:
            logger.error(f"SPARQL runner error: {e}")
            return {
                "success": False,
                "error": f"Execution error: {str(e)}",
                "columns": [],
                "rows": [],
                "row_count": 0,
                "latency_ms": 0
            }
    
    def _bind_params(self, sparql: str, params: Dict[str, Any]) -> str:
        """
        Replace {{var}} with escaped literal values.
        Replace {{iri var}} with IRI values (validated).
        
        Args:
            sparql: SPARQL template string
            params: Parameter values
            
        Returns:
            SPARQL string with parameters bound
        """
        bound_sparql = sparql
        
        # Find all {{iri var}} patterns first (more specific)
        iri_pattern = r'\{\{iri\s+(\w+)\}\}'
        iri_matches = re.findall(iri_pattern, bound_sparql)
        
        for var_name in iri_matches:
            if var_name in params:
                iri_value = str(params[var_name])
                # Validate IRI format (basic check)
                if not self._is_valid_iri(iri_value):
                    raise ValueError(f"Invalid IRI for parameter '{var_name}': {iri_value}")
                # Replace with angle brackets
                replacement = f"<{iri_value}>"
                bound_sparql = re.sub(f'\\{{\\{{iri\\s+{re.escape(var_name)}\\}}\\}}', replacement, bound_sparql)
            else:
                raise ValueError(f"Missing required IRI parameter: {var_name}")
        
        # Find all remaining {{var}} patterns
        literal_pattern = r'\{\{(\w+)\}\}'
        literal_matches = re.findall(literal_pattern, bound_sparql)
        
        for var_name in literal_matches:
            if var_name in params:
                literal_value = str(params[var_name])
                # Escape and quote literal value
                escaped_value = self._escape_sparql_literal(literal_value)
                bound_sparql = re.sub(f'\\{{\\{{{re.escape(var_name)}\\}}\\}}', escaped_value, bound_sparql)
            else:
                raise ValueError(f"Missing required parameter: {var_name}")
        
        return bound_sparql
    
    def _confine_to_graph(self, sparql: str, graph_iri: str) -> str:
        """
        Wrap SPARQL query with GRAPH clause to confine execution to named graph.
        Preserves PREFIX declarations from the original query.
        
        Args:
            sparql: Bound SPARQL SELECT query
            graph_iri: Named graph IRI
            
        Returns:
            SPARQL query wrapped with GRAPH clause
        """
        # Extract PREFIX declarations first
        # Note: \w* handles empty prefix (:) as well as named prefixes
        prefix_pattern = r'(PREFIX\s+\w*:\s*<[^>]+>\s*)'
        prefixes = re.findall(prefix_pattern, sparql, re.IGNORECASE)
        prefix_section = ''.join(prefixes)
        
        # Remove PREFIX declarations from the main query
        sparql_without_prefixes = re.sub(prefix_pattern, '', sparql, flags=re.IGNORECASE)
        
        # Pattern to match SELECT ... WHERE { ... }
        select_where_pattern = r'(SELECT\s+.*?)\s+WHERE\s*\{(.*)\}' 
        match = re.search(select_where_pattern, sparql_without_prefixes, re.IGNORECASE | re.DOTALL)
        
        if match:
            select_clause = match.group(1)
            where_body = match.group(2)
            
            # Reconstruct with PREFIX declarations preserved + GRAPH wrapper
            # Note: Class definitions are in the ontology graph, not the microtheory graph
            # So we need to allow the query to access the default graph for prefixes
            # but confine instance data to the microtheory graph
            confined_query = f"{prefix_section}\n{select_clause} WHERE {{ GRAPH <{graph_iri}> {{ {where_body} }} }}"
            logger.info(f"🔍 CONFINE_DEBUG: Confined query:\n{confined_query}")
            return confined_query
        else:
            # Fallback: try to wrap the entire WHERE clause while preserving prefixes
            logger.warning(f"Could not parse SPARQL structure, attempting fallback: {sparql[:100]}...")
            
            # Try to extract just the WHERE clause content
            where_pattern = r'WHERE\s*\{(.*)\}'
            where_match = re.search(where_pattern, sparql_without_prefixes, re.IGNORECASE | re.DOTALL)
            
            if where_match:
                where_content = where_match.group(1)
                return f"{prefix_section}\nSELECT * WHERE {{ GRAPH <{graph_iri}> {{ {where_content} }} }}"
            else:
                return f"{prefix_section}\nSELECT * WHERE {{ GRAPH <{graph_iri}> {{ ?s ?p ?o }} }}"
    
    def _execute_sparql_select(self, sparql: str) -> Dict[str, Any]:
        """
        Execute SPARQL SELECT query via Fuseki HTTP API.
        
        Args:
            sparql: Complete SPARQL query string
            
        Returns:
            {"success": bool, "data": dict or None, "error": str or None}
        """
        try:
            headers = {
                "Accept": "application/sparql-results+json",
                "Content-Type": "application/sparql-query"
            }
            
            # Use synchronous httpx for simplicity (can be made async later)
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    self.query_url,
                    content=sparql.encode('utf-8'),
                    headers=headers
                )
                response.raise_for_status()
                
                result_data = response.json()
                return {"success": True, "data": result_data, "error": None}
                
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.error(f"SPARQL HTTP error: {error_msg}")
            return {"success": False, "data": None, "error": error_msg}
            
        except Exception as e:
            error_msg = f"SPARQL execution error: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "data": None, "error": error_msg}
    
    def _process_sparql_results(self, result_data: Dict[str, Any]) -> Tuple[List[str], List[List[str]]]:
        """
        Process SPARQL JSON results into columns and rows format.
        
        Args:
            result_data: SPARQL results in JSON format from Fuseki
            
        Returns:
            (columns, rows) tuple
        """
        try:
            bindings = result_data.get("results", {}).get("bindings", [])
            vars_list = result_data.get("head", {}).get("vars", [])
            
            columns = vars_list
            rows = []
            
            for binding in bindings:
                row = []
                for var in columns:
                    if var in binding:
                        value = binding[var].get("value", "")
                        row.append(value)
                    else:
                        row.append("")  # NULL/missing value
                rows.append(row)
            
            return columns, rows
            
        except Exception as e:
            logger.error(f"Error processing SPARQL results: {e}")
            return [], []
    
    def validate_sparql(self, sparql: str) -> Tuple[bool, str]:
        """
        Basic SPARQL syntax validation.
        
        Args:
            sparql: SPARQL query string
            
        Returns:
            (is_valid, error_message)
        """
        try:
            # Basic checks
            if not sparql or not sparql.strip():
                return False, "Empty SPARQL query"
            
            sparql_upper = sparql.upper()
            
            # Must be a SELECT query
            if "SELECT" not in sparql_upper:
                return False, "Query must be a SELECT statement"
            
            # Must have a WHERE clause
            if "WHERE" not in sparql_upper:
                return False, "Query must have a WHERE clause"
            
            # Basic brace matching
            open_braces = sparql.count("{")
            close_braces = sparql.count("}")
            if open_braces != close_braces:
                return False, f"Mismatched braces: {open_braces} open, {close_braces} close"
            
            # Check for dangerous operations (UPDATE, DELETE, INSERT, DROP)
            dangerous_ops = ["UPDATE", "DELETE", "INSERT", "DROP", "CLEAR", "LOAD", "CREATE"]
            for op in dangerous_ops:
                if op in sparql_upper:
                    return False, f"Dangerous operation not allowed: {op}"
            
            return True, ""
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def _is_valid_iri(self, iri: str) -> bool:
        """
        Basic IRI validation.
        
        Args:
            iri: IRI string to validate
            
        Returns:
            True if IRI appears valid
        """
        if not iri:
            return False
            
        # Basic checks
        if " " in iri:
            return False
            
        # Must look like a URI
        if not (iri.startswith("http://") or iri.startswith("https://") or iri.startswith("urn:")):
            return False
            
        return True
    
    def _escape_sparql_literal(self, value: str) -> str:
        """
        Escape and quote a literal value for SPARQL.
        
        Args:
            value: Literal value to escape
            
        Returns:
            Properly escaped and quoted SPARQL literal
        """
        # Escape quotes and backslashes
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        
        # Return as quoted string literal
        return f'"{escaped}"'
    
    def create_named_graph(self, graph_iri: str) -> Dict[str, Any]:
        """
        Create a named graph in Fuseki.
        
        Args:
            graph_iri: IRI for the named graph
            
        Returns:
            {"success": bool, "error": str or None}
        """
        try:
            # SPARQL UPDATE to create empty named graph
            update_query = f"INSERT DATA {{ GRAPH <{graph_iri}> {{ }} }}"
            
            headers = {
                "Content-Type": "application/sparql-update"
            }
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    self.update_url,
                    content=update_query.encode('utf-8'),
                    headers=headers
                )
                response.raise_for_status()
                
                return {"success": True, "error": None}
                
        except Exception as e:
            error_msg = f"Failed to create named graph: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def drop_named_graph(self, graph_iri: str) -> Dict[str, Any]:
        """
        Drop a named graph from Fuseki.
        
        Args:
            graph_iri: IRI of the named graph to drop
            
        Returns:
            {"success": bool, "error": str or None}
        """
        try:
            # SPARQL UPDATE to drop named graph
            update_query = f"DROP GRAPH <{graph_iri}>"
            
            headers = {
                "Content-Type": "application/sparql-update"
            }
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    self.update_url,
                    content=update_query.encode('utf-8'),
                    headers=headers
                )
                response.raise_for_status()
                
                return {"success": True, "error": None}
                
        except Exception as e:
            error_msg = f"Failed to drop named graph: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def clone_named_graph(self, source_iri: str, target_iri: str) -> Dict[str, Any]:
        """
        Clone all triples from source named graph to target named graph.
        
        Args:
            source_iri: IRI of source named graph
            target_iri: IRI of target named graph
            
        Returns:
            {"success": bool, "error": str or None, "triples_copied": int or None}
        """
        try:
            # First create the target graph
            create_result = self.create_named_graph(target_iri)
            if not create_result["success"]:
                return create_result
            
            # SPARQL UPDATE to copy all triples from source to target
            update_query = f"""
            INSERT {{
                GRAPH <{target_iri}> {{ ?s ?p ?o }}
            }}
            WHERE {{
                GRAPH <{source_iri}> {{ ?s ?p ?o }}
            }}
            """
            
            headers = {
                "Content-Type": "application/sparql-update"
            }
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    self.update_url,
                    content=update_query.encode('utf-8'),
                    headers=headers
                )
                response.raise_for_status()
                
                # Count triples in target graph to verify
                count_result = self.count_triples_in_graph(target_iri)
                triples_copied = count_result.get("count", 0) if count_result["success"] else None
                
                return {"success": True, "error": None, "triples_copied": triples_copied}
                
        except Exception as e:
            error_msg = f"Failed to clone named graph: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "triples_copied": None}
    
    def count_triples_in_graph(self, graph_iri: str) -> Dict[str, Any]:
        """
        Count number of triples in a named graph.
        
        Args:
            graph_iri: IRI of the named graph
            
        Returns:
            {"success": bool, "count": int or None, "error": str or None}
        """
        try:
            count_query = f"SELECT (COUNT(*) AS ?count) WHERE {{ GRAPH <{graph_iri}> {{ ?s ?p ?o }} }}"
            
            result = self._execute_sparql_select(count_query)
            if result["success"]:
                bindings = result["data"].get("results", {}).get("bindings", [])
                if bindings and "count" in bindings[0]:
                    count = int(bindings[0]["count"]["value"])
                    return {"success": True, "count": count, "error": None}
                else:
                    return {"success": True, "count": 0, "error": None}
            else:
                return {"success": False, "count": None, "error": result["error"]}
                
        except Exception as e:
            error_msg = f"Failed to count triples: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "count": None, "error": error_msg}
    
    def get_all_triples_from_graph(self, graph_iri: str) -> Dict[str, Any]:
        """
        Get all triples from a named graph.
        
        Args:
            graph_iri: IRI of the named graph
            
        Returns:
            {"success": bool, "triples": list or None, "error": str or None}
            triples format: [{"subject": str, "predicate": str, "object": str}, ...]
        """
        try:
            select_query = f"SELECT ?s ?p ?o WHERE {{ GRAPH <{graph_iri}> {{ ?s ?p ?o }} }}"
            
            result = self._execute_sparql_select(select_query)
            if result["success"]:
                bindings = result["data"].get("results", {}).get("bindings", [])
                triples = []
                for binding in bindings:
                    triple = {
                        "subject": binding.get("s", {}).get("value", ""),
                        "predicate": binding.get("p", {}).get("value", ""),
                        "object": binding.get("o", {}).get("value", "")
                    }
                    triples.append(triple)
                return {"success": True, "triples": triples, "error": None}
            else:
                return {"success": False, "triples": None, "error": result["error"]}
                
        except Exception as e:
            error_msg = f"Failed to get triples: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "triples": None, "error": error_msg}
    
    def insert_sample_triples(self, graph_iri: str, triples: List[Tuple[str, str, str]]) -> Dict[str, Any]:
        """
        Insert sample triples into a named graph for testing.
        
        Args:
            graph_iri: IRI of the named graph
            triples: List of (subject, predicate, object) tuples
            
        Returns:
            {"success": bool, "error": str or None}
        """
        try:
            if not triples:
                return {"success": True, "error": None}
            
            # Build INSERT DATA query
            triples_str = ""
            for subject, predicate, obj in triples:
                # Simple formatting - assumes IRIs or literals are properly formatted
                if obj.startswith('"') and obj.endswith('"'):
                    # Already a quoted literal
                    triples_str += f"    <{subject}> <{predicate}> {obj} .\n"
                elif obj.startswith("http://") or obj.startswith("https://"):
                    # IRI
                    triples_str += f"    <{subject}> <{predicate}> <{obj}> .\n"
                else:
                    # Quote as literal
                    escaped_obj = obj.replace("\\", "\\\\").replace('"', '\\"')
                    triples_str += f'    <{subject}> <{predicate}> "{escaped_obj}" .\n'
            
            update_query = f"""
            INSERT DATA {{
                GRAPH <{graph_iri}> {{
{triples_str}
                }}
            }}
            """
            
            headers = {
                "Content-Type": "application/sparql-update"
            }
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    self.update_url,
                    content=update_query.encode('utf-8'),
                    headers=headers
                )
                response.raise_for_status()
                
                return {"success": True, "error": None}
                
        except Exception as e:
            error_msg = f"Failed to insert sample triples: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
