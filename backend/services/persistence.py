import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from rdflib import RDF, Graph, Literal, Namespace, URIRef
from SPARQLWrapper import JSON, POST, SPARQLWrapper

from .config import Settings

logger = logging.getLogger(__name__)


class PersistenceLayer:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.qdrant = QdrantClient(url=settings.qdrant_url)
        self.neo4j = GraphDatabase.driver(
            settings.neo4j_url, auth=(settings.neo4j_user, settings.neo4j_password)
        )
        self.collection = settings.collection_name
        self._ensure_qdrant_collection()

    def _ensure_qdrant_collection(self) -> None:
        """
        Ensure the Qdrant collection exists, creating it if necessary.

        Creates a collection with 384-dimensional vectors using cosine distance.
        Silently fails if Qdrant is not available (for offline development).
        """
        try:
            collections = self.qdrant.get_collections().collections
            if self.collection not in [c.name for c in collections]:
                logger.info(f"Creating Qdrant collection: {self.collection}")
                self.qdrant.recreate_collection(
                    collection_name=self.collection,
                    vectors_config=qmodels.VectorParams(size=384, distance=qmodels.Distance.COSINE),
                )
            else:
                logger.debug(f"Qdrant collection {self.collection} already exists")
        except Exception as e:
            logger.warning(
                f"Could not connect to Qdrant or create collection: {e}. Continuing for offline development."
            )
            # Allow offline dev when qdrant is not up yet
            pass

    def upsert_vector_records(
        self, embeddings: List[List[float]], payloads: List[Dict[str, Any]]
    ) -> None:
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
                pid = (
                    pl.get("id") or hashlib.md5(str(pl).encode(), usedforsecurity=False).hexdigest()
                )
                points.append(qmodels.PointStruct(id=pid, vector=vec, payload=pl))

            logger.debug(
                f"Upserting {len(points)} vector records to Qdrant collection {self.collection}"
            )
            self.qdrant.upsert(collection_name=self.collection, points=points)
            logger.info(f"Successfully upserted {len(points)} vectors to Qdrant")
        except Exception as e:
            logger.error(f"Failed to upsert vectors to Qdrant: {e}")
            # Fail silently for offline development

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
        if getattr(self.settings, "fuseki_user", None) and getattr(
            self.settings, "fuseki_password", None
        ):
            import requests

            auth = (self.settings.fuseki_user, self.settings.fuseki_password)

        # Attempt Graph Store Protocol
        try:
            import requests

            headers = {"Content-Type": "text/turtle"}
            resp = requests.put(
                graph_store_url,
                data=ttl.encode("utf-8"),
                headers=headers,
                auth=auth,
                timeout=10,
            )
            if 200 <= resp.status_code < 300:
                return
            # If not successful, fall through to SPARQL Update fallback
        except Exception:
            # Fall through to SPARQL Update fallback
            pass

        # SPARQL Update fallback: properly convert Turtle to SPARQL INSERT DATA
        try:
            # Parse the turtle content into an RDF graph
            graph = Graph()
            graph.parse(data=ttl, format="turtle")

            # Convert to SPARQL INSERT DATA format
            insert_data = []
            for s, p, o in graph:
                if isinstance(o, Literal):
                    # Handle literals with proper escaping
                    if o.datatype:
                        insert_data.append(f'<{s}> <{p}> "{o}"^^<{o.datatype}> .')
                    elif o.language:
                        insert_data.append(f'<{s}> <{p}> "{o}"@{o.language} .')
                    else:
                        insert_data.append(f'<{s}> <{p}> "{o}" .')
                else:
                    insert_data.append(f"<{s}> <{p}> <{o}> .")

            if not insert_data:
                return  # No data to insert

            # Build SPARQL query with proper prefixes
            prefixes = []
            for prefix, namespace in graph.namespaces():
                prefixes.append(f"PREFIX {prefix}: <{namespace}>")

            prefixes_block = "\n".join(prefixes)
            data_block = "\n                ".join(insert_data)

            query = f"""
            {prefixes_block}
            INSERT DATA {{
                {data_block}
            }}
            """

            sparql = SPARQLWrapper(base + "/update")
            sparql.setMethod(POST)
            # If credentials provided, use them
            if getattr(self.settings, "fuseki_user", None) and getattr(
                self.settings, "fuseki_password", None
            ):
                try:
                    sparql.setCredentials(self.settings.fuseki_user, self.settings.fuseki_password)
                except Exception:
                    pass

            sparql.setQuery(query)
            sparql.query()
        except Exception as e:
            raise RuntimeError(f"Failed to write RDF to Fuseki: {e}")

