"""
Neo4j Graph Database Integration Service.

Provides high-level interface for graph operations including:
- Node and relationship management
- Knowledge graph construction
- Requirements traceability queries
- Impact analysis and graph traversal
"""

import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from uuid import UUID
import json
from datetime import datetime

try:
    from neo4j import GraphDatabase, Driver, Session
    from neo4j.exceptions import ServiceUnavailable, AuthError, DriverError

    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    GraphDatabase = None

from .config import Settings

logger = logging.getLogger(__name__)


class Neo4jService:
    """
    High-level Neo4j graph database service.

    Provides operations for knowledge graph management including node creation,
    relationship establishment, and graph traversal queries.
    """

    def __init__(self, settings: Settings = None):
        """Initialize Neo4j service with configuration."""
        if not NEO4J_AVAILABLE:
            raise RuntimeError("Neo4j driver not available. Install with: pip install neo4j")

        self.settings = settings or Settings()
        self.driver: Optional[Driver] = None

        # Initialize connection
        self._init_driver()

    def _init_driver(self):
        """Initialize Neo4j driver connection."""
        try:
            # Use Neo4j URL from settings (default to localhost)
            neo4j_uri = getattr(self.settings, "neo4j_uri", "bolt://localhost:7687")
            neo4j_user = getattr(self.settings, "neo4j_user", "neo4j")
            neo4j_password = getattr(self.settings, "neo4j_password", "password")

            logger.info(f"Connecting to Neo4j at {neo4j_uri}")
            self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")

            logger.info("Neo4j connection established successfully")

        except (ServiceUnavailable, AuthError, DriverError) as e:
            logger.error(f"Failed to connect to Neo4j: {str(e)}")
            raise RuntimeError(f"Neo4j connection failed: {str(e)}")

    def close(self):
        """Close Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def setup_schema(self) -> bool:
        """
        Set up Neo4j schema with constraints and indexes.

        Returns:
            True if schema setup was successful
        """
        try:
            with self.driver.session() as session:
                # Read and execute schema setup from cypher file
                schema_queries = [
                    # Document nodes
                    "CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
                    "CREATE INDEX doc_project_id IF NOT EXISTS FOR (d:Document) ON (d.project_id)",
                    "CREATE INDEX doc_type IF NOT EXISTS FOR (d:Document) ON (d.document_type)",
                    # Knowledge Asset nodes
                    "CREATE CONSTRAINT asset_id IF NOT EXISTS FOR (a:KnowledgeAsset) REQUIRE a.id IS UNIQUE",
                    "CREATE INDEX asset_project_id IF NOT EXISTS FOR (a:KnowledgeAsset) ON (a.project_id)",
                    "CREATE INDEX asset_type IF NOT EXISTS FOR (a:KnowledgeAsset) ON (a.document_type)",
                    "CREATE INDEX asset_title IF NOT EXISTS FOR (a:KnowledgeAsset) ON (a.title)",
                    # Chunk nodes
                    "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE",
                    "CREATE INDEX chunk_type IF NOT EXISTS FOR (c:Chunk) ON (c.chunk_type)",
                    "CREATE INDEX chunk_sequence IF NOT EXISTS FOR (c:Chunk) ON (c.sequence_number)",
                    # Requirement nodes
                    "CREATE CONSTRAINT req_id IF NOT EXISTS FOR (r:Requirement) REQUIRE r.id IS UNIQUE",
                    "CREATE INDEX req_type IF NOT EXISTS FOR (r:Requirement) ON (r.requirement_type)",
                    "CREATE INDEX req_priority IF NOT EXISTS FOR (r:Requirement) ON (r.priority)",
                    # Component nodes
                    "CREATE CONSTRAINT comp_id IF NOT EXISTS FOR (c:Component) REQUIRE c.id IS UNIQUE",
                    "CREATE INDEX comp_type IF NOT EXISTS FOR (c:Component) ON (c.component_type)",
                    # Process nodes
                    "CREATE CONSTRAINT proc_id IF NOT EXISTS FOR (p:Process) REQUIRE p.id IS UNIQUE",
                    "CREATE INDEX proc_type IF NOT EXISTS FOR (p:Process) ON (p.process_type)",
                    # Function nodes
                    "CREATE CONSTRAINT func_id IF NOT EXISTS FOR (f:Function) REQUIRE f.id IS UNIQUE",
                    "CREATE INDEX func_type IF NOT EXISTS FOR (f:Function) ON (f.function_type)",
                    # Interface nodes
                    "CREATE CONSTRAINT iface_id IF NOT EXISTS FOR (i:Interface) REQUIRE i.id IS UNIQUE",
                    "CREATE INDEX iface_type IF NOT EXISTS FOR (i:Interface) ON (i.interface_type)",
                    # Condition nodes
                    "CREATE CONSTRAINT cond_id IF NOT EXISTS FOR (c:Condition) REQUIRE c.id IS UNIQUE",
                    "CREATE INDEX cond_type IF NOT EXISTS FOR (c:Condition) ON (c.condition_type)",
                ]

                # Execute each schema query
                for query in schema_queries:
                    try:
                        session.run(query)
                        logger.debug(f"Executed schema query: {query[:50]}...")
                    except Exception as e:
                        logger.warning(
                            f"Schema query failed (may already exist): {query[:50]}... - {str(e)}"
                        )

                logger.info("Neo4j schema setup completed successfully")
                return True

        except Exception as e:
            logger.error(f"Failed to setup Neo4j schema: {str(e)}")
            return False

    def create_document_node(self, document_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a Document node in the graph.

        Args:
            document_data: Document properties including id, filename, project_id, etc.

        Returns:
            Document node ID if successful, None otherwise
        """
        try:
            with self.driver.session() as session:
                query = """
                CREATE (d:Document {
                    id: $id,
                    filename: $filename,
                    project_id: $project_id,
                    document_type: $document_type,
                    file_size: $file_size,
                    content_type: $content_type,
                    upload_date: $upload_date,
                    created_at: datetime()
                })
                RETURN d.id as id
                """

                result = session.run(query, **document_data)
                record = result.single()

                if record:
                    doc_id = record["id"]
                    logger.info(f"Created Document node: {doc_id}")
                    return doc_id

                return None

        except Exception as e:
            logger.error(f"Failed to create Document node: {str(e)}")
            return None

    def create_knowledge_asset_node(self, asset_data: Dict[str, Any]) -> Optional[str]:
        """
        Create a KnowledgeAsset node in the graph.

        Args:
            asset_data: Asset properties including id, title, document_type, etc.

        Returns:
            Asset node ID if successful, None otherwise
        """
        try:
            with self.driver.session() as session:
                query = """
                CREATE (a:KnowledgeAsset {
                    id: $id,
                    title: $title,
                    project_id: $project_id,
                    document_type: $document_type,
                    chunk_count: $chunk_count,
                    token_count: $token_count,
                    processing_status: $processing_status,
                    created_at: datetime()
                })
                RETURN a.id as id
                """

                result = session.run(query, **asset_data)
                record = result.single()

                if record:
                    asset_id = record["id"]
                    logger.info(f"Created KnowledgeAsset node: {asset_id}")
                    return asset_id

                return None

        except Exception as e:
            logger.error(f"Failed to create KnowledgeAsset node: {str(e)}")
            return None

    def create_chunk_nodes(self, chunks_data: List[Dict[str, Any]]) -> List[str]:
        """
        Create multiple Chunk nodes in the graph.

        Args:
            chunks_data: List of chunk properties

        Returns:
            List of created chunk node IDs
        """
        try:
            created_ids = []

            with self.driver.session() as session:
                for chunk_data in chunks_data:
                    query = """
                    CREATE (c:Chunk {
                        id: $id,
                        content: $content,
                        chunk_type: $chunk_type,
                        sequence_number: $sequence_number,
                        token_count: $token_count,
                        qdrant_point_id: $qdrant_point_id,
                        created_at: datetime()
                    })
                    RETURN c.id as id
                    """

                    result = session.run(query, **chunk_data)
                    record = result.single()

                    if record:
                        created_ids.append(record["id"])

            logger.info(f"Created {len(created_ids)} Chunk nodes")
            return created_ids

        except Exception as e:
            logger.error(f"Failed to create Chunk nodes: {str(e)}")
            return []

    def create_relationship(
        self,
        from_node_id: str,
        to_node_id: str,
        relationship_type: str,
        from_label: str = None,
        to_label: str = None,
        properties: Dict[str, Any] = None,
    ) -> Optional[int]:
        """
        Create a relationship between two nodes.

        Args:
            from_node_id: Source node ID
            to_node_id: Target node ID
            relationship_type: Type of relationship (e.g., CONTAINS, REFERENCES)
            from_label: Optional node label for source (for performance)
            to_label: Optional node label for target (for performance)
            properties: Optional relationship properties

        Returns:
            Relationship ID if successful, None otherwise
        """
        try:
            with self.driver.session() as session:
                # Build match clauses with optional labels
                from_match = (
                    f"(from:{from_label} {{id: $from_id}})"
                    if from_label
                    else "(from {id: $from_id})"
                )
                to_match = f"(to:{to_label} {{id: $to_id}})" if to_label else "(to {id: $to_id})"

                # Build properties clause
                props_str = ""
                if properties:
                    props_list = [f"{k}: ${k}" for k in properties.keys()]
                    props_str = f" {{{', '.join(props_list)}}}"

                query = f"""
                MATCH {from_match}, {to_match}
                CREATE (from)-[r:{relationship_type}{props_str}]->(to)
                RETURN id(r) as rel_id
                """

                # Combine parameters
                params = {
                    "from_id": from_node_id,
                    "to_id": to_node_id,
                    **(properties or {}),
                }

                result = session.run(query, params)
                record = result.single()

                if record:
                    rel_id = record["rel_id"]
                    logger.info(
                        f"Created relationship: {from_node_id} -[{relationship_type}]-> {to_node_id}"
                    )
                    return rel_id

                return None

        except Exception as e:
            logger.error(f"Failed to create relationship: {str(e)}")
            return None

    def find_paths(
        self,
        start_node_id: str,
        end_node_id: str = None,
        relationship_types: List[str] = None,
        max_depth: int = 3,
        direction: str = "outgoing",  # outgoing, incoming, both
    ) -> List[Dict[str, Any]]:
        """
        Find paths between nodes in the graph.

        Args:
            start_node_id: Starting node ID
            end_node_id: Optional ending node ID (if None, finds all reachable nodes)
            relationship_types: Optional list of relationship types to traverse
            max_depth: Maximum traversal depth
            direction: Direction of traversal

        Returns:
            List of path information
        """
        try:
            with self.driver.session() as session:
                # Build relationship pattern
                if relationship_types:
                    rel_types = "|".join(relationship_types)
                    rel_pattern = f"[r:{rel_types}]"
                else:
                    rel_pattern = "[r]"

                # Build direction pattern
                if direction == "incoming":
                    path_pattern = f"<-{rel_pattern}-"
                elif direction == "both":
                    path_pattern = f"-{rel_pattern}-"
                else:  # outgoing
                    path_pattern = f"-{rel_pattern}->"

                # Build query
                if end_node_id:
                    # Specific end node
                    query = f"""
                    MATCH path = (start {{id: $start_id}}){path_pattern}*(end {{id: $end_id}})
                    WHERE length(path) <= $max_depth AND length(path) > 0
                    RETURN path, length(path) as depth
                    ORDER BY depth
                    """
                    params = {
                        "start_id": start_node_id,
                        "end_id": end_node_id,
                        "max_depth": max_depth,
                    }
                else:
                    # All reachable nodes
                    query = f"""
                    MATCH path = (start {{id: $start_id}}){path_pattern}(end)
                    WHERE length(path) <= $max_depth AND length(path) > 0
                    RETURN path, length(path) as depth, end
                    ORDER BY depth
                    """
                    params = {"start_id": start_node_id, "max_depth": max_depth}

                result = session.run(query, params)

                paths = []
                for record in result:
                    path_data = {
                        "depth": record["depth"],
                        "nodes": [],
                        "relationships": [],
                    }

                    path = record["path"]
                    for node in path.nodes:
                        path_data["nodes"].append(
                            {
                                "id": node.get("id"),
                                "labels": list(node.labels),
                                "properties": dict(node.items()),
                            }
                        )

                    for rel in path.relationships:
                        path_data["relationships"].append(
                            {"type": rel.type, "properties": dict(rel.items())}
                        )

                    paths.append(path_data)

                logger.info(
                    f"Found {len(paths)} paths from {start_node_id} (max depth: {max_depth})"
                )
                return paths

        except Exception as e:
            logger.error(f"Failed to find paths: {str(e)}")
            return []

    def impact_analysis(
        self, node_id: str, analysis_type: str = "downstream", max_depth: int = 3
    ) -> Dict[str, Any]:
        """
        Perform impact analysis for a given node.

        Args:
            node_id: Target node ID (e.g., requirement ID)
            analysis_type: Type of analysis (downstream, upstream, bidirectional)
            max_depth: Maximum traversal depth

        Returns:
            Impact analysis results
        """
        try:
            with self.driver.session() as session:
                if analysis_type == "downstream":
                    # Find what depends on this node
                    query = """
                    MATCH path = (start {id: $node_id})-[r:DEPENDS_ON|IMPLEMENTS|DERIVES_FROM*1..3]->(affected)
                    RETURN affected, r, length(path) as depth
                    ORDER BY depth
                    """
                elif analysis_type == "upstream":
                    # Find what this node depends on
                    query = """
                    MATCH path = (dependency)-[r:DEPENDS_ON|IMPLEMENTS|DERIVES_FROM*1..3]->(start {id: $node_id})
                    RETURN dependency, r, length(path) as depth
                    ORDER BY depth
                    """
                else:  # bidirectional
                    query = """
                    MATCH path = (start {id: $node_id})-[r:DEPENDS_ON|IMPLEMENTS|DERIVES_FROM*1..3]-(connected)
                    RETURN connected, r, length(path) as depth
                    ORDER BY depth
                    """

                result = session.run(query, {"node_id": node_id, "max_depth": max_depth})

                affected_nodes = []
                for record in result:
                    node_key = (
                        "affected"
                        if analysis_type == "downstream"
                        else ("dependency" if analysis_type == "upstream" else "connected")
                    )
                    node = record.get(node_key)

                    if node:
                        affected_nodes.append(
                            {
                                "id": node.get("id"),
                                "labels": list(node.labels),
                                "properties": dict(node.items()),
                                "depth": record["depth"],
                            }
                        )

                return {
                    "target_node_id": node_id,
                    "analysis_type": analysis_type,
                    "max_depth": max_depth,
                    "affected_count": len(affected_nodes),
                    "affected_nodes": affected_nodes,
                }

        except Exception as e:
            logger.error(f"Impact analysis failed for {node_id}: {str(e)}")
            return {"error": str(e)}

    def execute_cypher(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Execute a custom Cypher query.

        Args:
            query: Cypher query string
            parameters: Optional query parameters

        Returns:
            Query results as list of dictionaries
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})

                records = []
                for record in result:
                    records.append(dict(record))

                logger.info(f"Executed Cypher query, returned {len(records)} records")
                return records

        except Exception as e:
            logger.error(f"Cypher query execution failed: {str(e)}")
            raise RuntimeError(f"Query execution failed: {str(e)}")

    def get_graph_stats(self) -> Dict[str, Any]:
        """
        Get graph database statistics.

        Returns:
            Statistics about nodes, relationships, etc.
        """
        try:
            with self.driver.session() as session:
                # Get node counts by label
                node_stats = session.run(
                    """
                    MATCH (n) 
                    RETURN labels(n) as labels, count(n) as count 
                    ORDER BY count DESC
                """
                ).data()

                # Get relationship counts by type
                rel_stats = session.run(
                    """
                    MATCH ()-[r]->() 
                    RETURN type(r) as type, count(r) as count 
                    ORDER BY count DESC
                """
                ).data()

                # Get total counts
                total_nodes = session.run("MATCH (n) RETURN count(n) as total").single()["total"]
                total_rels = session.run("MATCH ()-[r]->() RETURN count(r) as total").single()[
                    "total"
                ]

                return {
                    "total_nodes": total_nodes,
                    "total_relationships": total_rels,
                    "node_counts_by_label": node_stats,
                    "relationship_counts_by_type": rel_stats,
                }

        except Exception as e:
            logger.error(f"Failed to get graph stats: {str(e)}")
            return {"error": str(e)}

    def health_check(self) -> Dict[str, Any]:
        """
        Check Neo4j service health.

        Returns:
            Health status information
        """
        try:
            with self.driver.session() as session:
                # Simple connectivity test
                result = session.run("RETURN 1 as test")
                test_value = result.single()["test"]

                if test_value == 1:
                    stats = self.get_graph_stats()
                    return {
                        "status": "healthy",
                        "neo4j_available": True,
                        "total_nodes": stats.get("total_nodes", 0),
                        "total_relationships": stats.get("total_relationships", 0),
                    }
                else:
                    return {"status": "unhealthy", "error": "Unexpected test result"}

        except Exception as e:
            logger.error(f"Neo4j health check failed: {str(e)}")
            return {"status": "unhealthy", "error": str(e), "neo4j_available": False}


# ========================================
# UTILITY FUNCTIONS
# ========================================


def get_neo4j_service(settings: Settings = None) -> Neo4jService:
    """Get configured Neo4j service instance."""
    return Neo4jService(settings)


def setup_knowledge_graph_schema(neo4j_service: Neo4jService) -> bool:
    """
    Set up the knowledge graph schema with all constraints and indexes.

    Args:
        neo4j_service: Configured Neo4j service

    Returns:
        True if schema setup was successful
    """
    try:
        return neo4j_service.setup_schema()

    except Exception as e:
        logger.error(f"Failed to setup knowledge graph schema: {str(e)}")
        return False
