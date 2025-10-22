"""
CQ/MT Service for Competency Question and Microtheory Management
Provides business logic for the CQ/MT Workbench including CQ execution and contract validation.
"""

import logging
import json
import redis
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from uuid import UUID
import uuid

from .sparql_runner import SPARQLRunner
from .db import DatabaseService
from .config import Settings

logger = logging.getLogger(__name__)


class CQMTService:
    """
    Core service for CQ/MT Workbench operations.
    Handles Competency Question CRUD, execution, and Microtheory management.
    """
    
    def __init__(self, db_service: DatabaseService, fuseki_url: str = "http://localhost:3030"):
        self.db = db_service
        self.runner = SPARQLRunner(fuseki_url)
        self.settings = Settings()
        
        # Initialize Redis for event publishing (optional)
        self.redis_client = None
        try:
            self.redis_client = redis.Redis(
                host=getattr(self.settings, 'redis_host', 'localhost'),
                port=getattr(self.settings, 'redis_port', 6379),
                db=0,
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis not available for events: {e}")
            self.redis_client = None
    
    # =====================================
    # MICROTHEORY MANAGEMENT
    # =====================================
    
    def create_microtheory(
        self, 
        project_id: str, 
        label: str, 
        iri: Optional[str] = None,
        clone_from: Optional[str] = None, 
        set_default: bool = False,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new microtheory (named graph) with optional cloning.
        
        Args:
            project_id: Project UUID
            label: Human-readable label
            iri: Custom IRI (generated if not provided)
            clone_from: Source MT IRI to clone from
            set_default: Whether to set as project default
            created_by: User UUID
            
        Returns:
            {"success": bool, "data": dict or None, "error": str or None}
        """
        try:
            # Generate IRI if not provided
            if not iri:
                # Format: http://localhost:8000/mt/{project_id}/{slug}
                slug = label.lower().replace(" ", "-").replace("_", "-")
                # Remove special characters
                slug = "".join(c for c in slug if c.isalnum() or c == "-")
                iri = f"http://localhost:8000/mt/{project_id}/{slug}"
            
            # Check for duplicate IRI
            conn = self.db._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id FROM microtheories WHERE iri = %s",
                        (iri,)
                    )
                    if cur.fetchone():
                        return {
                            "success": False,
                            "data": None,
                            "error": f"Microtheory with IRI {iri} already exists"
                        }
                    
                    # Check for duplicate label within project
                    cur.execute(
                        "SELECT id FROM microtheories WHERE project_id = %s AND label = %s",
                        (project_id, label)
                    )
                    if cur.fetchone():
                        return {
                            "success": False,
                            "data": None,
                            "error": f"Microtheory with label '{label}' already exists in this project"
                        }
                    
                    # Insert SQL record
                    mt_id = uuid.uuid4()
                    cur.execute("""
                        INSERT INTO microtheories (
                            id, project_id, label, iri, parent_iri, is_default, created_by
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        str(mt_id), project_id, label, iri, clone_from, set_default, created_by
                    ))
                    
                    conn.commit()
                    
            finally:
                self.db._return(conn)
            
            # Create named graph in Fuseki
            graph_result = self.runner.create_named_graph(iri)
            if not graph_result["success"]:
                # Rollback SQL on Fuseki failure
                self._delete_mt_from_sql(str(mt_id))
                return {
                    "success": False,
                    "data": None,
                    "error": f"Failed to create Fuseki graph: {graph_result['error']}"
                }
            
            # Clone triples if source provided
            if clone_from:
                clone_result = self.runner.clone_named_graph(clone_from, iri)
                if not clone_result["success"]:
                    logger.warning(f"Failed to clone triples from {clone_from} to {iri}: {clone_result['error']}")
                    # Don't fail the whole operation, just log the warning
            
            return {
                "success": True,
                "data": {
                    "id": str(mt_id),
                    "label": label,
                    "iri": iri,
                    "parent_iri": clone_from,
                    "is_default": set_default,
                    "created_at": datetime.now().isoformat()
                },
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error creating microtheory: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"Failed to create microtheory: {str(e)}"
            }
    
    def list_microtheories(self, project_id: str) -> Dict[str, Any]:
        """
        List all microtheories for a project with triple counts.
        
        Args:
            project_id: Project UUID
            
        Returns:
            {"success": bool, "data": list or None, "error": str or None}
        """
        try:
            conn = self.db._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            id, label, iri, parent_iri, is_default, 
                            created_by, created_at
                        FROM microtheories 
                        WHERE project_id = %s 
                        ORDER BY created_at DESC
                    """, (project_id,))
                    
                    rows = cur.fetchall()
                    
            finally:
                self.db._return(conn)
            
            # Enrich with triple counts from Fuseki
            microtheories = []
            for row in rows:
                mt_data = {
                    "id": str(row[0]),
                    "label": row[1],
                    "iri": row[2],
                    "parent_iri": row[3],
                    "is_default": row[4],
                    "created_by": str(row[5]) if row[5] else None,
                    "created_at": row[6].isoformat() if row[6] else None,
                    "triple_count": 0
                }
                
                # Get triple count from Fuseki
                count_result = self.runner.count_triples_in_graph(row[2])  # iri
                if count_result["success"]:
                    mt_data["triple_count"] = count_result["count"]
                
                microtheories.append(mt_data)
            
            return {
                "success": True,
                "data": microtheories,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error listing microtheories: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"Failed to list microtheories: {str(e)}"
            }
    
    def get_microtheory(self, mt_id: str) -> Dict[str, Any]:
        """
        Get a single microtheory with its triples.
        
        Args:
            mt_id: Microtheory UUID
            
        Returns:
            {"success": bool, "data": dict or None, "error": str or None}
        """
        try:
            conn = self.db._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            id, label, iri, parent_iri, is_default, 
                            created_by, created_at
                        FROM microtheories 
                        WHERE id = %s
                    """, (mt_id,))
                    
                    row = cur.fetchone()
                    
            finally:
                self.db._return(conn)
            
            if not row:
                return {
                    "success": False,
                    "data": None,
                    "error": "Microtheory not found"
                }
            
            mt_data = {
                "id": str(row[0]),
                "label": row[1],
                "iri": row[2],
                "parent_iri": row[3],
                "is_default": row[4],
                "created_by": str(row[5]) if row[5] else None,
                "created_at": row[6].isoformat() if row[6] else None,
                "triple_count": 0,
                "triples": []
            }
            
            # Get triples from Fuseki
            triples_result = self.runner.get_all_triples_from_graph(row[2])  # iri
            if triples_result["success"]:
                mt_data["triple_count"] = len(triples_result["triples"])
                mt_data["triples"] = triples_result["triples"]
            else:
                # Get count at least
                count_result = self.runner.count_triples_in_graph(row[2])
                if count_result["success"]:
                    mt_data["triple_count"] = count_result["count"]
            
            return {
                "success": True,
                "data": mt_data,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error getting microtheory: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"Failed to get microtheory: {str(e)}"
            }
    
    def update_microtheory(
        self,
        mt_id: str,
        label: str,
        description: Optional[str] = None,
        triples: Optional[List[Dict[str, str]]] = None,
        set_default: bool = False,
        updated_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update a microtheory's metadata and triples.
        
        Args:
            mt_id: Microtheory UUID
            label: New label
            description: New description
            triples: List of triples to replace existing triples
            set_default: Whether to set as project default
            updated_by: User ID
            
        Returns:
            {"success": bool, "data": dict or None, "error": str or None}
        """
        try:
            conn = self.db._conn()
            try:
                with conn.cursor() as cur:
                    # Get MT details first
                    cur.execute("""
                        SELECT iri, project_id FROM microtheories WHERE id = %s
                    """, (mt_id,))
                    row = cur.fetchone()
                    
                    if not row:
                        return {
                            "success": False,
                            "data": None,
                            "error": "Microtheory not found"
                        }
                    
                    mt_iri = row[0]
                    project_id = row[1]
                    
                    # Update triples in Fuseki if provided
                    if triples is not None:
                        # Drop existing triples
                        drop_result = self.runner.drop_named_graph(mt_iri)
                        if not drop_result["success"]:
                            logger.warning(f"Failed to drop graph {mt_iri}: {drop_result['error']}")
                        
                        # Create new graph
                        create_result = self.runner.create_named_graph(mt_iri)
                        if not create_result["success"]:
                            return {
                                "success": False,
                                "data": None,
                                "error": f"Failed to recreate graph: {create_result['error']}"
                            }
                        
                        # Insert new triples
                        if triples:
                            triple_tuples = [(t["subject"], t["predicate"], t["object"]) for t in triples]
                            insert_result = self.runner.insert_sample_triples(mt_iri, triple_tuples)
                            if not insert_result["success"]:
                                logger.warning(f"Failed to insert some triples: {insert_result['error']}")
                    
                    # Update metadata in PostgreSQL
                    cur.execute("""
                        UPDATE microtheories 
                        SET label = %s, 
                            description = %s,
                            updated_by = %s,
                            updated_at = NOW()
                        WHERE id = %s
                    """, (label, description, updated_by, mt_id))
                    
                    conn.commit()
                    
                    # Handle set_default if requested
                    if set_default:
                        set_result = self.set_default_microtheory(mt_id, project_id)
                        if not set_result["success"]:
                            logger.warning(f"Failed to set default: {set_result['error']}")
                    
                    # Return updated MT data
                    return {
                        "success": True,
                        "data": {"id": mt_id, "label": label, "iri": mt_iri},
                        "error": None
                    }
                    
            finally:
                self.db._return(conn)
                
        except Exception as e:
            logger.error(f"Error updating microtheory: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"Failed to update microtheory: {str(e)}"
            }
    
    def delete_microtheory(self, mt_id: str) -> Dict[str, Any]:
        """
        Delete a microtheory and its named graph.
        
        Args:
            mt_id: Microtheory UUID
            
        Returns:
            {"success": bool, "error": str or None}
        """
        try:
            # Get MT details first
            conn = self.db._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT iri FROM microtheories WHERE id = %s",
                        (mt_id,)
                    )
                    row = cur.fetchone()
                    if not row:
                        return {
                            "success": False,
                            "error": "Microtheory not found"
                        }
                    
                    mt_iri = row[0]
                    
            finally:
                self.db._return(conn)
            
            # Drop named graph from Fuseki
            graph_result = self.runner.drop_named_graph(mt_iri)
            if not graph_result["success"]:
                logger.warning(f"Failed to drop Fuseki graph {mt_iri}: {graph_result['error']}")
                # Continue with SQL deletion anyway
            
            # Delete SQL record
            self._delete_mt_from_sql(mt_id)
            
            return {"success": True, "error": None}
            
        except Exception as e:
            logger.error(f"Error deleting microtheory: {e}")
            return {
                "success": False,
                "error": f"Failed to delete microtheory: {str(e)}"
            }
    
    def set_default_microtheory(self, mt_id: str, project_id: str) -> Dict[str, Any]:
        """
        Set a microtheory as the project default.
        
        Args:
            mt_id: Microtheory UUID
            project_id: Project UUID (for validation)
            
        Returns:
            {"success": bool, "error": str or None}
        """
        try:
            conn = self.db._conn()
            try:
                with conn.cursor() as cur:
                    # Verify MT exists in project
                    cur.execute(
                        "SELECT id FROM microtheories WHERE id = %s AND project_id = %s",
                        (mt_id, project_id)
                    )
                    if not cur.fetchone():
                        return {
                            "success": False,
                            "error": "Microtheory not found in project"
                        }
                    
                    # Set as default (trigger will handle unsetting others)
                    cur.execute(
                        "UPDATE microtheories SET is_default = TRUE WHERE id = %s",
                        (mt_id,)
                    )
                    
                    conn.commit()
                    
            finally:
                self.db._return(conn)
            
            return {"success": True, "error": None}
            
        except Exception as e:
            logger.error(f"Error setting default microtheory: {e}")
            return {
                "success": False,
                "error": f"Failed to set default microtheory: {str(e)}"
            }
    
    def _delete_mt_from_sql(self, mt_id: str):
        """Helper to delete MT from SQL."""
        conn = self.db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM microtheories WHERE id = %s", (mt_id,))
                conn.commit()
        finally:
            self.db._return(conn)
    
    # =====================================
    # COMPETENCY QUESTION MANAGEMENT
    # =====================================
    
    def create_or_update_cq(
        self,
        project_id: str,
        cq_data: Dict[str, Any],
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create or update a competency question.
        
        Args:
            project_id: Project UUID
            cq_data: CQ data dict with cq_name, problem_text, sparql_text, etc.
            created_by: User UUID
            
        Returns:
            {"success": bool, "data": dict or None, "error": str or None}
        """
        try:
            # Validate required fields
            required_fields = ["cq_name", "problem_text", "sparql_text", "contract_json"]
            for field in required_fields:
                if field not in cq_data:
                    return {
                        "success": False,
                        "data": None,
                        "error": f"Missing required field: {field}"
                    }
            
            # Validate contract JSON
            try:
                contract = cq_data["contract_json"]
                if isinstance(contract, str):
                    contract = json.loads(contract)
                
                # Validate contract structure
                validation_result = self._validate_cq_contract_structure(contract)
                if not validation_result["valid"]:
                    return {
                        "success": False,
                        "data": None,
                        "error": f"Invalid contract: {validation_result['error']}"
                    }
                    
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "data": None,
                    "error": "Invalid JSON in contract_json"
                }
            
            # Validate SPARQL syntax
            sparql_valid, sparql_error = self.runner.validate_sparql(cq_data["sparql_text"])
            if not sparql_valid:
                return {
                    "success": False,
                    "data": None,
                    "error": f"Invalid SPARQL: {sparql_error}"
                }
            
            conn = self.db._conn()
            try:
                with conn.cursor() as cur:
                    # Check if CQ exists (upsert logic)
                    cur.execute(
                        "SELECT id FROM cqs WHERE project_id = %s AND cq_name = %s",
                        (project_id, cq_data["cq_name"])
                    )
                    existing = cur.fetchone()
                    
                    if existing:
                        # Update existing CQ
                        cq_id = existing[0]
                        cur.execute("""
                            UPDATE cqs SET 
                                problem_text = %s,
                                params_json = %s,
                                sparql_text = %s,
                                mt_iri_default = %s,
                                contract_json = %s,
                                status = %s,
                                updated_at = NOW()
                            WHERE id = %s
                        """, (
                            cq_data["problem_text"],
                            json.dumps(cq_data.get("params_json", {})),
                            cq_data["sparql_text"],
                            cq_data.get("mt_iri_default"),
                            json.dumps(contract),
                            cq_data.get("status", "draft"),
                            cq_id
                        ))
                    else:
                        # Insert new CQ
                        cq_id = uuid.uuid4()
                        cur.execute("""
                            INSERT INTO cqs (
                                id, project_id, cq_name, problem_text, params_json,
                                sparql_text, mt_iri_default, contract_json, status, created_by
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            str(cq_id), project_id, cq_data["cq_name"],
                            cq_data["problem_text"],
                            json.dumps(cq_data.get("params_json", {})),
                            cq_data["sparql_text"],
                            cq_data.get("mt_iri_default"),
                            json.dumps(contract),
                            cq_data.get("status", "draft"),
                            created_by
                        ))
                    
                    conn.commit()
                    
            finally:
                self.db._return(conn)
            
            return {
                "success": True,
                "data": {
                    "id": str(cq_id),
                    "cq_name": cq_data["cq_name"],
                    "created_at": datetime.now().isoformat()
                },
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error creating/updating CQ: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"Failed to create/update CQ: {str(e)}"
            }
    
    def update_cq(
        self,
        cq_id: str,
        cq_data: Dict[str, Any],
        updated_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing competency question.
        
        Args:
            cq_id: CQ UUID
            cq_data: CQ data dict with cq_name, problem_text, sparql_text, etc.
            updated_by: User UUID
            
        Returns:
            {"success": bool, "data": dict or None, "error": str or None}
        """
        try:
            # Validate required fields
            required_fields = ["cq_name", "problem_text", "sparql_text", "contract_json"]
            for field in required_fields:
                if field not in cq_data:
                    return {
                        "success": False,
                        "data": None,
                        "error": f"Missing required field: {field}"
                    }
            
            # Validate contract JSON
            try:
                contract = cq_data["contract_json"]
                if isinstance(contract, str):
                    contract = json.loads(contract)
                
                # Validate contract structure
                validation_result = self._validate_cq_contract_structure(contract)
                if not validation_result["valid"]:
                    return {
                        "success": False,
                        "data": None,
                        "error": f"Invalid contract: {validation_result['error']}"
                    }
                    
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "data": None,
                    "error": "Invalid JSON in contract_json"
                }
            
            # Validate SPARQL syntax
            sparql_valid, sparql_error = self.runner.validate_sparql(cq_data["sparql_text"])
            if not sparql_valid:
                return {
                    "success": False,
                    "data": None,
                    "error": f"Invalid SPARQL: {sparql_error}"
                }
            
            conn = self.db._conn()
            try:
                with conn.cursor() as cur:
                    # Update existing CQ
                    cur.execute("""
                        UPDATE cqs SET 
                            cq_name = %s,
                            problem_text = %s,
                            params_json = %s,
                            sparql_text = %s,
                            mt_iri_default = %s,
                            contract_json = %s,
                            status = %s,
                            updated_at = NOW()
                        WHERE id = %s
                    """, (
                        cq_data["cq_name"],
                        cq_data["problem_text"],
                        json.dumps(cq_data.get("params_json", {})),
                        cq_data["sparql_text"],
                        cq_data.get("mt_iri_default"),
                        json.dumps(contract),
                        cq_data.get("status", "draft"),
                        cq_id
                    ))
                    
                    if cur.rowcount == 0:
                        return {
                            "success": False,
                            "data": None,
                            "error": "CQ not found"
                        }
                    
                    conn.commit()
                    
                    # Return updated CQ data
                    cur.execute("""
                        SELECT id, cq_name, problem_text, sparql_text, mt_iri_default,
                               contract_json, status, created_at, updated_at
                        FROM cqs WHERE id = %s
                    """, (cq_id,))
                    
                    row = cur.fetchone()
                    if row:
                        return {
                            "success": True,
                            "data": {
                                "id": str(row[0]),
                                "cq_name": row[1],
                                "problem_text": row[2],
                                "sparql_text": row[3],
                                "mt_iri_default": row[4],
                                "contract_json": row[5],
                                "status": row[6],
                                "created_at": row[7].isoformat() if row[7] else None,
                                "updated_at": row[8].isoformat() if row[8] else None
                            }
                        }
                    else:
                        return {
                            "success": False,
                            "data": None,
                            "error": "Failed to retrieve updated CQ"
                        }
                        
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Error updating CQ: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"Failed to update CQ: {str(e)}"
            }
    
    def delete_cq(self, cq_id: str) -> Dict[str, Any]:
        """
        Delete a competency question and all its run records.
        
        Args:
            cq_id: CQ UUID
            
        Returns:
            {"success": bool, "error": str or None}
        """
        try:
            conn = self.db._conn()
            try:
                with conn.cursor() as cur:
                    # Check if CQ exists
                    cur.execute("SELECT id FROM cqs WHERE id = %s", (cq_id,))
                    if not cur.fetchone():
                        return {
                            "success": False,
                            "error": "CQ not found"
                        }
                    
                    # Delete CQ (cascade will delete run records)
                    cur.execute("DELETE FROM cqs WHERE id = %s", (cq_id,))
                    
                    if cur.rowcount == 0:
                        return {
                            "success": False,
                            "error": "CQ not found"
                        }
                    
                    conn.commit()
                    
                    return {
                        "success": True,
                        "error": None
                    }
                    
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Error deleting CQ: {e}")
            return {
                "success": False,
                "error": f"Failed to delete CQ: {str(e)}"
            }
    
    def get_cqs(
        self,
        project_id: str,
        status: Optional[str] = None,
        mt_iri: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get competency questions for a project with optional filters.
        
        Args:
            project_id: Project UUID
            status: Filter by status (draft, active, deprecated)
            mt_iri: Filter by default microtheory IRI
            
        Returns:
            {"success": bool, "data": list or None, "error": str or None}
        """
        try:
            conn = self.db._conn()
            try:
                with conn.cursor() as cur:
                    # Build query with filters
                    where_clauses = ["project_id = %s"]
                    params = [project_id]
                    
                    if status:
                        where_clauses.append("status = %s")
                        params.append(status)
                    
                    if mt_iri:
                        where_clauses.append("mt_iri_default = %s")
                        params.append(mt_iri)
                    
                    where_sql = " AND ".join(where_clauses)
                    
                    cur.execute(f"""
                        SELECT 
                            c.id, c.cq_name, c.problem_text, c.sparql_text,
                            c.mt_iri_default, c.contract_json, c.status,
                            c.created_at, c.updated_at,
                            r.pass as last_run_status,
                            r.created_at as last_run_at
                        FROM cqs c
                        LEFT JOIN LATERAL (
                            SELECT pass, created_at 
                            FROM cq_runs 
                            WHERE cq_id = c.id 
                            ORDER BY created_at DESC 
                            LIMIT 1
                        ) r ON true
                        WHERE {where_sql}
                        ORDER BY c.created_at DESC
                    """, params)
                    
                    rows = cur.fetchall()
                    
            finally:
                self.db._return(conn)
            
            cqs = []
            for row in rows:
                cq_data = {
                    "id": str(row[0]),
                    "cq_name": row[1],
                    "problem_text": row[2],
                    "sparql_text": row[3],
                    "mt_iri_default": row[4],
                    "contract_json": row[5],
                    "status": row[6],
                    "created_at": row[7].isoformat() if row[7] else None,
                    "updated_at": row[8].isoformat() if row[8] else None,
                    "last_run_status": row[9],
                    "last_run_at": row[10].isoformat() if row[10] else None
                }
                cqs.append(cq_data)
            
            return {
                "success": True,
                "data": cqs,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error getting CQs: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"Failed to get CQs: {str(e)}"
            }
    
    def get_cq_details(self, cq_id: str) -> Dict[str, Any]:
        """
        Get detailed CQ information including last 5 runs.
        
        Args:
            cq_id: CQ UUID
            
        Returns:
            {"success": bool, "data": dict or None, "error": str or None}
        """
        try:
            conn = self.db._conn()
            try:
                with conn.cursor() as cur:
                    # Get CQ details
                    cur.execute("""
                        SELECT 
                            id, project_id, cq_name, problem_text, params_json,
                            sparql_text, mt_iri_default, contract_json, status,
                            created_by, created_at, updated_at
                        FROM cqs WHERE id = %s
                    """, (cq_id,))
                    
                    cq_row = cur.fetchone()
                    if not cq_row:
                        return {
                            "success": False,
                            "data": None,
                            "error": "CQ not found"
                        }
                    
                    # Get last 5 runs
                    cur.execute("""
                        SELECT 
                            id, mt_iri, params_json, pass, reason,
                            row_count, columns_json, latency_ms, created_at
                        FROM cq_runs 
                        WHERE cq_id = %s 
                        ORDER BY created_at DESC 
                        LIMIT 5
                    """, (cq_id,))
                    
                    run_rows = cur.fetchall()
                    
            finally:
                self.db._return(conn)
            
            # Build response
            cq_data = {
                "id": str(cq_row[0]),
                "project_id": str(cq_row[1]),
                "cq_name": cq_row[2],
                "problem_text": cq_row[3],
                "params_json": cq_row[4],
                "sparql_text": cq_row[5],
                "mt_iri_default": cq_row[6],
                "contract_json": cq_row[7],
                "status": cq_row[8],
                "created_by": str(cq_row[9]) if cq_row[9] else None,
                "created_at": cq_row[10].isoformat() if cq_row[10] else None,
                "updated_at": cq_row[11].isoformat() if cq_row[11] else None,
                "recent_runs": []
            }
            
            for run_row in run_rows:
                run_data = {
                    "id": str(run_row[0]),
                    "mt_iri": run_row[1],
                    "params_json": run_row[2],
                    "pass": run_row[3],
                    "reason": run_row[4],
                    "row_count": run_row[5],
                    "columns_json": run_row[6],
                    "latency_ms": run_row[7],
                    "created_at": run_row[8].isoformat() if run_row[8] else None
                }
                cq_data["recent_runs"].append(run_data)
            
            return {
                "success": True,
                "data": cq_data,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error getting CQ details: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"Failed to get CQ details: {str(e)}"
            }
    
    # =====================================
    # CQ EXECUTION
    # =====================================
    
    def run_cq(
        self,
        cq_id: str,
        mt_iri: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        executed_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a competency question and validate against its contract.
        
        Args:
            cq_id: CQ UUID
            mt_iri: Microtheory IRI (uses CQ default if not provided)
            params: Parameter values for SPARQL template
            executed_by: User UUID
            
        Returns:
            {
                "success": bool,
                "pass": bool,
                "reason": str,
                "columns": list,
                "row_count": int,
                "rows_preview": list,
                "latency_ms": int,
                "run_id": str,
                "error": str or None
            }
        """
        try:
            if params is None:
                params = {}
            
            # Get CQ details
            cq_result = self.get_cq_details(cq_id)
            if not cq_result["success"]:
                return {
                    "success": False,
                    "pass": False,
                    "reason": "CQ not found",
                    "columns": [],
                    "row_count": 0,
                    "rows_preview": [],
                    "latency_ms": 0,
                    "run_id": None,
                    "error": cq_result["error"]
                }
            
            cq_data = cq_result["data"]
            
            # Resolve MT IRI (use provided or CQ default)
            target_mt_iri = mt_iri or cq_data["mt_iri_default"]
            if not target_mt_iri:
                # Try to get project default MT
                project_id = cq_data["project_id"]
                default_mt = self._get_default_mt_iri(project_id)
                if default_mt:
                    target_mt_iri = default_mt
                else:
                    return {
                        "success": False,
                        "pass": False,
                        "reason": "No microtheory specified and no project default",
                        "columns": [],
                        "row_count": 0,
                        "rows_preview": [],
                        "latency_ms": 0,
                        "run_id": None,
                        "error": "No microtheory specified"
                    }
            
            # Execute SPARQL via runner
            execution_result = self.runner.run_select_in_graph(
                target_mt_iri,
                cq_data["sparql_text"],
                params
            )
            
            if not execution_result["success"]:
                # Persist failed run record
                run_id = self._persist_run_record(
                    cq_id, target_mt_iri, params, False, 
                    execution_result["error"], 0, [], [], 0, executed_by
                )
                
                return {
                    "success": True,
                    "pass": False,
                    "reason": f"compile_error: {execution_result['error']}",
                    "columns": [],
                    "row_count": 0,
                    "rows_preview": [],
                    "latency_ms": execution_result["latency_ms"],
                    "run_id": str(run_id),
                    "error": None
                }
            
            # Validate against contract
            contract = cq_data["contract_json"]
            columns = execution_result["columns"]
            rows = execution_result["rows"]
            row_count = execution_result["row_count"]
            latency_ms = execution_result["latency_ms"]
            
            validation_result = self.validate_cq_contract(
                {"columns": columns, "row_count": row_count, "latency_ms": latency_ms},
                contract
            )
            
            # Create preview (first 10 rows)
            rows_preview = rows[:10] if rows else []
            
            # Persist run record
            run_id = self._persist_run_record(
                cq_id, target_mt_iri, params, validation_result[0],
                validation_result[1], row_count, columns, rows_preview,
                latency_ms, executed_by
            )
            
            # Publish event
            self._publish_cq_run_event(
                cq_data["project_id"], cq_id, cq_data["cq_name"],
                target_mt_iri, validation_result[0], validation_result[1], latency_ms
            )
            
            return {
                "success": True,
                "pass": validation_result[0],
                "reason": validation_result[1],
                "columns": columns,
                "row_count": row_count,
                "rows_preview": rows_preview,
                "latency_ms": latency_ms,
                "run_id": str(run_id),
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error running CQ: {e}")
            return {
                "success": False,
                "pass": False,
                "reason": f"execution_error: {str(e)}",
                "columns": [],
                "row_count": 0,
                "rows_preview": [],
                "latency_ms": 0,
                "run_id": None,
                "error": str(e)
            }
    
    def validate_cq_contract(self, result: Dict[str, Any], contract: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check CQ execution result against contract requirements.
        
        Args:
            result: Execution result with columns, row_count, latency_ms
            contract: Contract with require_columns, min_rows?, max_latency_ms?
            
        Returns:
            (pass, reason) tuple
        """
        try:
            # Check required columns
            require_columns = contract.get("require_columns", [])
            actual_columns = result.get("columns", [])
            
            missing_columns = []
            for required_col in require_columns:
                if required_col not in actual_columns:
                    missing_columns.append(required_col)
            
            if missing_columns:
                return False, f"missing_required_columns: {', '.join(missing_columns)}"
            
            # Check minimum rows
            min_rows = contract.get("min_rows")
            if min_rows is not None and result.get("row_count", 0) < min_rows:
                return False, f"min_rows_not_met: expected {min_rows}, got {result.get('row_count', 0)}"
            
            # Check maximum latency
            max_latency_ms = contract.get("max_latency_ms")
            if max_latency_ms is not None and result.get("latency_ms", 0) > max_latency_ms:
                return False, f"latency_budget_exceeded: expected <={max_latency_ms}ms, got {result.get('latency_ms', 0)}ms"
            
            return True, "pass"
            
        except Exception as e:
            return False, f"contract_validation_error: {str(e)}"
    
    def get_cq_runs(self, cq_id: str, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """
        Get paginated run history for a CQ.
        
        Args:
            cq_id: CQ UUID
            limit: Maximum number of runs to return
            offset: Offset for pagination
            
        Returns:
            {"success": bool, "data": list or None, "error": str or None}
        """
        try:
            conn = self.db._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            id, mt_iri, params_json, pass, reason,
                            row_count, columns_json, rows_preview_json,
                            latency_ms, executed_by, created_at
                        FROM cq_runs 
                        WHERE cq_id = %s 
                        ORDER BY created_at DESC 
                        LIMIT %s OFFSET %s
                    """, (cq_id, limit, offset))
                    
                    rows = cur.fetchall()
                    
            finally:
                self.db._return(conn)
            
            runs = []
            for row in rows:
                run_data = {
                    "id": str(row[0]),
                    "mt_iri": row[1],
                    "params_json": row[2],
                    "pass": row[3],
                    "reason": row[4],
                    "row_count": row[5],
                    "columns_json": row[6],
                    "rows_preview_json": row[7],
                    "latency_ms": row[8],
                    "executed_by": str(row[9]) if row[9] else None,
                    "created_at": row[10].isoformat() if row[10] else None
                }
                runs.append(run_data)
            
            return {
                "success": True,
                "data": runs,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error getting CQ runs: {e}")
            return {
                "success": False,
                "data": None,
                "error": f"Failed to get CQ runs: {str(e)}"
            }
    
    # =====================================
    # HELPER METHODS
    # =====================================
    
    def _validate_cq_contract_structure(self, contract: Dict[str, Any]) -> Dict[str, Any]:
        """Validate CQ contract JSON structure."""
        try:
            # require_columns must be array
            if "require_columns" not in contract:
                return {"valid": False, "error": "Missing require_columns field"}
            
            if not isinstance(contract["require_columns"], list):
                return {"valid": False, "error": "require_columns must be an array"}
            
            # min_rows must be non-negative integer if present
            if "min_rows" in contract:
                min_rows = contract["min_rows"]
                if not isinstance(min_rows, int) or min_rows < 0:
                    return {"valid": False, "error": "min_rows must be a non-negative integer"}
            
            # max_latency_ms must be positive integer if present
            if "max_latency_ms" in contract:
                max_latency = contract["max_latency_ms"]
                if not isinstance(max_latency, int) or max_latency <= 0:
                    return {"valid": False, "error": "max_latency_ms must be a positive integer"}
            
            return {"valid": True, "error": None}
            
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    def _get_default_mt_iri(self, project_id: str) -> Optional[str]:
        """Get default MT IRI for a project."""
        try:
            conn = self.db._conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT iri FROM microtheories WHERE project_id = %s AND is_default = TRUE",
                        (project_id,)
                    )
                    row = cur.fetchone()
                    return row[0] if row else None
            finally:
                self.db._return(conn)
        except Exception as e:
            logger.error(f"Error getting default MT: {e}")
            return None
    
    def _persist_run_record(
        self, cq_id: str, mt_iri: str, params: Dict[str, Any], 
        passed: bool, reason: str, row_count: int, columns: List[str], 
        rows_preview: List[List[str]], latency_ms: int, executed_by: Optional[str]
    ) -> UUID:
        """Persist CQ run record to database."""
        run_id = uuid.uuid4()
        
        conn = self.db._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO cq_runs (
                        id, cq_id, mt_iri, params_json, pass, reason,
                        row_count, columns_json, rows_preview_json,
                        latency_ms, executed_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    str(run_id), cq_id, mt_iri, json.dumps(params), passed, reason,
                    row_count, json.dumps(columns), json.dumps(rows_preview),
                    latency_ms, executed_by
                ))
                conn.commit()
        finally:
            self.db._return(conn)
        
        return run_id
    
    def _publish_cq_run_event(
        self, project_id: str, cq_id: str, cq_name: str,
        mt_iri: str, passed: bool, reason: str, latency_ms: int
    ):
        """Publish CQ run completion event to Redis."""
        if not self.redis_client:
            return
        
        try:
            event = {
                "event": "cq.run.completed",
                "timestamp": datetime.now().isoformat(),
                "project_id": project_id,
                "cq_id": cq_id,
                "cq_name": cq_name,
                "mt_iri": mt_iri,
                "pass": passed,
                "reason": reason,
                "latency_ms": latency_ms
            }
            
            self.redis_client.publish("odras.events", json.dumps(event))
            
        except Exception as e:
            logger.warning(f"Failed to publish CQ run event: {e}")
