#!/usr/bin/env python3
"""
Load a few example ontologies into a Fuseki dataset as separate named graphs.

Defaults assume Fuseki at http://localhost:3030/odras and project id 'demo'.
Each named graph will contain an owl:Ontology triple (so the UI discovery lists it)
and a couple of simple class/property triples for visibility.

Usage:
  python scripts/load_sample_ontologies.py \
    --fuseki http://localhost:3030/odras \
    --project demo \
    --graphs base_se_v1 base_se_v2 imports_geo

Notes:
  - Graph IRIs will be: http://odras.local/onto/{project}/{name}
  - Requires requests (already in requirements.txt)
"""

from __future__ import annotations

import argparse
import sys
from typing import Iterable, List
from urllib.parse import quote

import requests


def build_graph_iri(project_id: str, name: str) -> str:
    name = name.strip().strip('/')
    return f"http://odras.local/onto/{project_id}/{name}"


def ttl_for_ontology(graph_iri: str, label: str) -> str:
    """Generate minimal Turtle content for an ontology in its own named graph.

    Includes owl:Ontology and a couple of simple classes + one object property.
    """
    # Use fully-qualified IRIs to avoid relying on @base for simplicity
    req = f"<{graph_iri}#Requirement>"
    comp = f"<{graph_iri}#Component>"
    satisfied_by = f"<{graph_iri}#satisfied_by>"
    return f"""
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<{graph_iri}> a owl:Ontology ;
  rdfs:label "{label}" .

{req} a owl:Class ; rdfs:label "Requirement" .
{comp} a owl:Class ; rdfs:label "Component" .
{satisfied_by} a owl:ObjectProperty ; rdfs:label "satisfied by" ; rdfs:domain {req} ; rdfs:range {comp} .
""".strip()


def put_named_graph(fuseki_base: str, graph_iri: str, turtle: str, username: str | None, password: str | None) -> requests.Response:
    base = fuseki_base.rstrip('/')
    url = f"{base}/data?graph={quote(graph_iri, safe=':/#') }"
    headers = {"Content-Type": "text/turtle"}
    auth = (username, password) if username and password else None
    resp = requests.put(url, data=turtle.encode("utf-8"), headers=headers, auth=auth, timeout=20)
    return resp


def load_graphs(
    fuseki_base: str,
    project_id: str,
    graph_names: Iterable[str],
    username: str | None,
    password: str | None,
) -> List[str]:
    created: List[str] = []
    for name in graph_names:
        graph_iri = build_graph_iri(project_id, name)
        label = name.replace('_', ' ').strip() or name
        ttl = ttl_for_ontology(graph_iri, label)
        resp = put_named_graph(fuseki_base, graph_iri, ttl, username, password)
        if 200 <= resp.status_code < 300:
            print(f"OK  {graph_iri}")
            created.append(graph_iri)
        else:
            print(f"ERR {graph_iri} -> {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
    return created


def main() -> int:
    ap = argparse.ArgumentParser(description="Load sample ontologies into Fuseki as named graphs")
    ap.add_argument("--fuseki", default="http://localhost:3030/odras", help="Fuseki dataset base URL (e.g., http://localhost:3030/odras)")
    ap.add_argument("--project", default="demo", help="Project id to embed in graph IRIs (used by UI filter)")
    ap.add_argument("--user", dest="username", default=None, help="Fuseki username (optional)")
    ap.add_argument("--password", dest="password", default=None, help="Fuseki password (optional)")
    ap.add_argument(
        "--graphs",
        nargs="*",
        default=["base_se_v1", "base_se_v2", "imports_geo"],
        help="Graph name suffixes to create under /onto/{project}/ (space-separated)",
    )
    args = ap.parse_args()

    print(f"Loading {len(args.graphs)} ontologies into {args.fuseki} for project '{args.project}'...")
    created = load_graphs(args.fuseki, args.project, args.graphs, args.username, args.password)
    print(f"Created/updated: {len(created)} graphs")
    for g in created:
        print(" -", g)
    return 0 if created else 1


if __name__ == "__main__":
    raise SystemExit(main())


