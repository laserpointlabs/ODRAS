# Ontology Endpoints Guide

## Overview
ODRAS has **two different ontology endpoint systems** that serve different purposes. Understanding the difference is critical for proper automation and integration.

## Endpoint Systems

### 1. `/api/ontology/*` - Legacy Ontology Operations
**Router**: `backend/api/ontology.py`  
**Prefix**: `/api/ontology`  
**Status**: Active for READ operations, DEPRECATED for WRITE operations

#### Purpose
- Operations on a **single ontology** identified by graph IRI
- Used for visualization, inspection, and management of existing ontologies
- Graph-agnostic context switching

#### Key Endpoints
- `GET /api/ontology/?graph={graph_iri}` - Get ontology details (JSON format)
- `POST /api/ontology/classes` - Add class to ontology (DEPRECATED)
- `POST /api/ontology/properties` - Add property to ontology (DEPRECATED)
- `POST /api/ontology/import` - Import RDF/Turtle content (DEPRECATED)
- `GET /api/ontology/statistics` - Get ontology statistics
- `GET /api/ontology/layout` - Get visualization layout

#### Usage Pattern
```python
# Get ontology details
GET /api/ontology/?graph=http://localhost:8000/odras/projects/{project_id}/ontologies/{name}

# This endpoint expects graph IRI as query parameter
# It returns complete ontology JSON including classes, properties, etc.
```

### 2. `/api/ontologies` - Ontology Registry & CRUD
**Router**: `backend/main.py` (main app routes)  
**Prefix**: `/api/ontologies`  
**Status**: ✅ CURRENT FOR ALL OPERATIONS

#### Purpose
- Manage **ontology registry** (which ontologies exist in projects)
- CRUD operations on ontology entities
- Project-based ontology lifecycle management

#### Key Endpoints
- `GET /api/ontologies?project={project_id}` - List ontologies in project
- `POST /api/ontologies` - Create new ontology ✅
- `DELETE /api/ontologies?graph={graph_iri}` - Delete ontology
- `PUT /api/ontologies/label` - Update ontology label
- `GET /api/ontologies/reference` - List reference ontologies

#### Create Ontology Request Format
```python
POST /api/ontologies
{
  "project": "project-uuid",
  "name": "TestOntology",
  "label": "Test Ontology",
  "is_reference": false
}

# Response:
{
  "graphIri": "http://localhost:8000/odras/projects/{project_id}/ontologies/test-ontology",
  "label": "Test Ontology"
}
```

## Adding Classes and Properties

### Current State (DEPRECATED)
The `/api/ontology/classes` and `/api/ontology/properties` endpoints are **deprecated**. They still work but should not be used for new automation.

### Recommended Approach
Add classes and properties **directly to Fuseki** using SPARQL INSERT, or use the ontology manager service directly.

#### Option 1: Direct SPARQL (Recommended for Automation)
```python
import requests

# Insert class triple
fuseki_url = "http://localhost:3030/odras/update"
graph_iri = "http://localhost:8000/odras/projects/{project_id}/ontologies/test-ontology"

sparql = f"""
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

INSERT DATA {{
    GRAPH <{graph_iri}> {{
        <{graph_iri}#Aircraft> a owl:Class ;
            rdfs:label "Aircraft" .
    }}
}}
"""

requests.post(fuseki_url, 
    data=sparql.encode('utf-8'),
    headers={'Content-Type': 'application/sparql-update'}
)
```

#### Option 2: Use OntologyManager Service
```python
from backend.services.ontology_manager import OntologyManager
from backend.services.config import Settings

manager = OntologyManager(Settings())
manager.add_class_to_graph(
    graph_iri=graph_iri,
    class_name="Aircraft",
    label="Aircraft",
    comment="Base aircraft class"
)
```

## Automation Workflow

### Correct Pattern for Creating Complete Ontology

```python
# Step 1: Create ontology registry entry
POST /api/ontologies
{
  "project": project_id,
  "name": "TestOntology",
  "label": "Test Ontology",
  "is_reference": false
}
# Returns: graphIri

# Step 2: Add classes via direct SPARQL
# Use graphIri from step 1
INSERT DATA { GRAPH <{graphIri}> { ... } }

# Step 3: Add properties via direct SPARQL
INSERT DATA { GRAPH <{graphIri}> { ... } }

# Step 4: Query for verification
GET /api/ontology/?graph={graphIri}
```

## Common Mistakes

### ❌ Wrong: Using deprecated endpoints
```python
# DON'T DO THIS
POST /api/ontology/classes
{
  "name": "Aircraft",
  "graph": "http://..."
}
```

### ✅ Correct: Create ontology first, then add classes
```python
# DO THIS
# 1. Create ontology
POST /api/ontologies
{
  "project": project_id,
  "name": "TestOntology"
}

# 2. Add classes directly to Fuseki
INSERT DATA { GRAPH <graphIri> { ... } }
```

## Future Plans

### Planned Unification
- Consolidate endpoints under `/api/ontologies`
- Remove deprecated `/api/ontology` write operations
- Keep `/api/ontology/*` for read-only inspection operations
- Create proper RESTful CRUD under `/api/ontologies/{ontology_id}/classes`

### Current Recommendation
For automation scripts:
1. ✅ Use `/api/ontologies` for creating ontologies
2. ✅ Use direct SPARQL INSERT for adding classes/properties
3. ✅ Use `/api/ontology/?graph={iri}` for reading ontology details
4. ❌ Don't use deprecated `/api/ontology/classes` or `/api/ontology/properties`

## Example: Full Automation Script

```python
import requests

# 1. Create ontology
resp = requests.post("http://localhost:8000/api/ontologies", 
    json={
        "project": project_id,
        "name": "TestOntology",
        "label": "Test Ontology"
    },
    headers={"Authorization": f"Bearer {token}"}
)
graph_iri = resp.json()["graphIri"]

# 2. Add classes via SPARQL
classes_sparql = f"""
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

INSERT DATA {{
    GRAPH <{graph_iri}> {{
        <{graph_iri}#Aircraft> a owl:Class ;
            rdfs:label "Aircraft" .
        <{graph_iri}#FighterJet> a owl:Class ;
            rdfs:subClassOf <{graph_iri}#Aircraft> ;
            rdfs:label "Fighter Jet" .
    }}
}}
"""

requests.post("http://localhost:3030/odras/update",
    data=classes_sparql.encode('utf-8'),
    headers={'Content-Type': 'application/sparql-update'}
)

# 3. Verify
resp = requests.get(f"http://localhost:8000/api/ontology/?graph={graph_iri}",
    headers={"Authorization": f"Bearer {token}"}
)
print(f"Created ontology with {len(resp.json()['classes'])} classes")
```

## Summary

| Operation | Endpoint | Status |
|-----------|----------|--------|
| List ontologies | `GET /api/ontologies?project={id}` | ✅ Current |
| Create ontology | `POST /api/ontologies` | ✅ Current |
| Delete ontology | `DELETE /api/ontologies?graph={iri}` | ✅ Current |
| Get ontology details | `GET /api/ontology/?graph={iri}` | ✅ Current |
| Add class | Direct SPARQL INSERT | ✅ Recommended |
| Add property | Direct SPARQL INSERT | ✅ Recommended |
| Add class (old) | `POST /api/ontology/classes` | ❌ Deprecated |
| Add property (old) | `POST /api/ontology/properties` | ❌ Deprecated |
