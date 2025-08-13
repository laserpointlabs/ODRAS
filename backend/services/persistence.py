from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from neo4j import GraphDatabase
from rdflib import Graph, Namespace, Literal, RDF, URIRef
from SPARQLWrapper import SPARQLWrapper, POST, JSON
import numpy as np
import hashlib

from .config import Settings


class PersistenceLayer:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.qdrant = QdrantClient(url=settings.qdrant_url)
        self.neo4j = GraphDatabase.driver(settings.neo4j_url, auth=(settings.neo4j_user, settings.neo4j_password))
        self.collection = settings.collection_name
        self._ensure_qdrant_collection()

    def _ensure_qdrant_collection(self):
        try:
            if self.collection not in [c.name for c in self.qdrant.get_collections().collections]:
                self.qdrant.recreate_collection(
                    collection_name=self.collection,
                    vectors_config=qmodels.VectorParams(size=384, distance=qmodels.Distance.COSINE),
                )
        except Exception:
            # Allow offline dev when qdrant is not up yet
            pass

    def upsert_vector_records(self, embeddings: List[List[float]], payloads: List[Dict[str, Any]]):
        try:
            points = []
            for idx, (vec, pl) in enumerate(zip(embeddings, payloads)):
                pid = pl.get("id") or hashlib.md5(str(pl).encode()).hexdigest()
                points.append(qmodels.PointStruct(id=pid, vector=vec, payload=pl))
            self.qdrant.upsert(collection_name=self.collection, points=points)
        except Exception:
            pass

    def write_graph(self, triples: List[tuple[str, str, str]]):
        with self.neo4j.session() as session:
            for subj, pred, obj in triples:
                session.run(
                    "MERGE (s:Entity {iri:$s}) MERGE (o:Entity {iri:$o}) MERGE (s)-[r:REL {type:$p}]->(o)",
                    s=subj, o=obj, p=pred
                )

    def write_rdf(self, ttl: str):
        try:
            sparql = SPARQLWrapper(self.settings.fuseki_url + "/update")
            sparql.setMethod(POST)
            # Using SPARQL Update to insert data
            sparql.setQuery(f"""
                INSERT DATA {{
                    {ttl}
                }}
            """)
            sparql.query()
        except Exception:
            pass




