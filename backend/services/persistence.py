import hashlib
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from rdflib import RDF, Graph, Literal, Namespace, URIRef
from SPARQLWrapper import JSON, POST, SPARQLWrapper

from .config import Settings


class PersistenceLayer:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.qdrant = QdrantClient(url=settings.qdrant_url)
        self.neo4j = GraphDatabase.driver(settings.neo4j_url, auth=(settings.neo4j_user, settings.neo4j_password))
        self.collection = settings.collection_name
        self._ensure_qdrant_collection()

    def _ensure_qdrant_collection(self) -> None:
        """
        Ensure the Qdrant collection exists, creating it if necessary.
        
        Creates a collection with 384-dimensional vectors using cosine distance.
        Silently fails if Qdrant is not available (for offline development).
        """
        try:
            if self.collection not in [c.name for c in self.qdrant.get_collections().collections]:
                self.qdrant.recreate_collection(
                    collection_name=self.collection,
                    vectors_config=qmodels.VectorParams(size=384, distance=qmodels.Distance.COSINE),
                )
        except Exception:
            # Allow offline dev when qdrant is not up yet
            pass

    def upsert_vector_records(self, embeddings: List[List[float]], payloads: List[Dict[str, Any]]) -> None:
        """
        Upsert vector embeddings with metadata into Qdrant.
        
        Args:
            embeddings: List of vector embeddings (each a list of floats)
            payloads: List of metadata dictionaries corresponding to each embedding
            
        Note:
            Silently fails if Qdrant is not available (for offline development).
        """
        try:
            points = []
            for idx, (vec, pl) in enumerate(zip(embeddings, payloads)):
                pid = pl.get("id") or hashlib.md5(str(pl).encode()).hexdigest()
                points.append(qmodels.PointStruct(id=pid, vector=vec, payload=pl))
            self.qdrant.upsert(collection_name=self.collection, points=points)
        except Exception:
            pass

    def write_graph(self, triples: List[Tuple[str, str, str]]) -> None:
        """
        Write RDF triples to Neo4j graph database.
        
        Args:
            triples: List of (subject, predicate, object) tuples to store as graph relationships
            
        Note:
            Creates Entity nodes and REL relationships in Neo4j.
        """
        with self.neo4j.session() as session:
            for subj, pred, obj in triples:
                session.run(
                    "MERGE (s:Entity {iri:$s}) MERGE (o:Entity {iri:$o}) MERGE (s)-[r:REL {type:$p}]->(o)",
                    s=subj,
                    o=obj,
                    p=pred,
                )

    def write_rdf(self, ttl: str) -> None:
        """
        Write Turtle content to Fuseki.

        Strategy:
        1) Preferred: Graph Store Protocol (PUT text/turtle to /data?default) to replace default graph
        2) Fallback: SPARQL Update with PREFIX + INSERT DATA

        Raises an exception if both strategies fail.
        """
        # Normalize base dataset URL
        base = self.settings.fuseki_url.rstrip("/")
        graph_store_url = f"{base}/data?default"

        # Build auth if configured
        auth = None
        if getattr(self.settings, "fuseki_user", None) and getattr(self.settings, "fuseki_password", None):
            import requests

            auth = (self.settings.fuseki_user, self.settings.fuseki_password)

        # Attempt Graph Store Protocol
        try:
            import requests

            headers = {"Content-Type": "text/turtle"}
            resp = requests.put(graph_store_url, data=ttl.encode("utf-8"), headers=headers, auth=auth, timeout=10)
            if 200 <= resp.status_code < 300:
                return
            # If not successful, fall through to SPARQL Update fallback
        except Exception:
            # Fall through to SPARQL Update fallback
            pass

        # SPARQL Update fallback: convert @prefix -> PREFIX and insert TTL body
        try:
            prefix_lines = []
            body_lines = []
            for line in ttl.splitlines():
                stripped = line.strip()
                if stripped.startswith("@prefix"):
                    # Example: @prefix ex: <http://example/> .
                    # Convert to: PREFIX ex: <http://example/>
                    try:
                        # Remove trailing '.' and replace '@prefix' with 'PREFIX'
                        without_dot = stripped[:-1] if stripped.endswith(".") else stripped
                        prefix_lines.append(without_dot.replace("@prefix", "PREFIX"))
                    except Exception:
                        # If parsing fails, just skip; SPARQL may still work if QNames are not used
                        pass
                else:
                    body_lines.append(line)

            prefixes_block = "\n".join(prefix_lines)
            body_block = "\n".join(body_lines)

            sparql = SPARQLWrapper(base + "/update")
            sparql.setMethod(POST)
            # If credentials provided, use them
            if getattr(self.settings, "fuseki_user", None) and getattr(self.settings, "fuseki_password", None):
                try:
                    sparql.setCredentials(self.settings.fuseki_user, self.settings.fuseki_password)
                except Exception:
                    pass

            query = f"""
                {prefixes_block}
                INSERT DATA {{
                {body_block}
                }}
            """
            sparql.setQuery(query)
            sparql.query()
        except Exception as e:
            raise RuntimeError(f"Failed to write RDF to Fuseki: {e}")
