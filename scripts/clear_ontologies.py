import sys
import requests


def main():
    base = "http://localhost:3030/odras"
    query_url = f"{base.rstrip('/')}/query"
    update_url = f"{base.rstrip('/')}/update"

    # 1) Find graphs with owl:Ontology
    sparql = (
        "PREFIX owl: <http://www.w3.org/2002/07/owl#>\n"
        "SELECT DISTINCT ?g WHERE { GRAPH ?g { ?o a owl:Ontology } }"
    )
    r = requests.post(
        query_url,
        data={"query": sparql},
        headers={"Accept": "application/sparql-results+json"},
        timeout=15,
    )
    r.raise_for_status()
    graphs = [b["g"]["value"] for b in r.json().get("results", {}).get("bindings", [])]
    if not graphs:
        print("No ontology graphs found.")
        return 0

    print(f"Found {len(graphs)} graphs")
    # 2) Drop each graph
    for g in graphs:
        upd = f"DROP GRAPH <{g}>"
        ru = requests.post(
            update_url,
            data=upd.encode("utf-8"),
            headers={"Content-Type": "application/sparql-update"},
            timeout=15,
        )
        print(f"DROP {g} -> {ru.status_code}")

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

