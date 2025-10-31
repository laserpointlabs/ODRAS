# CQ/MT Workbench Guide
*Test-Driven Ontology Development with Competency Questions and Microtheories*

## 🎯 Overview

The CQ/MT Workbench implements a **test-driven approach to ontology development** where you define what your ontology must answer (Competency Questions) before building it. This prevents over-engineering and ensures your ontology serves its intended purpose.

## 🔄 Test-Driven Workflow

### Traditional Approach (Bottom-Up)
```
Build Ontology → Hope it meets needs → Discover gaps later → Fix
```

### CQ/MT Approach (Test-Driven)
```
1. Define Competency Questions (requirements)
2. Create Microtheory (test environment) 
3. Run CQs → They FAIL (ontology incomplete)
4. Build ontology classes/properties
5. Re-run CQs → Track progress toward PASS
6. Iterate until all CQs pass
```

## 🏗️ Architecture

### Core Components

**Frontend:** `frontend/cqmt-workbench.html` - Full-featured UI with CQ editor, MT manager, run panel, and coverage analytics

**Backend Services:**
- `backend/services/sparql_runner.py` - SPARQL execution with parameter binding and graph confinement
- `backend/services/cqmt_service.py` - Business logic for CQ/MT operations
- `backend/api/cqmt.py` - REST API endpoints

**Data Storage:**
- PostgreSQL: CQ metadata, run history, MT metadata
- Fuseki: Microtheories as named graphs, shared ontology in TBox graphs

## 📊 Data Model

### Microtheories
Microtheories are implemented as **named graphs** in Fuseki:
- **Shared TBox graphs**: `<http://localhost:8000/ontology/{project_id}/base>` (read-only ontology classes)
- **MT ABox graphs**: `<http://localhost:8000/mt/{project_id}/{slug}>` (per-MT instance data)

### Competency Questions
Domain-agnostic with minimal contract structure:
```json
{
  "cq_name": "List All Aircraft",
  "problem_text": "What aircraft are defined in the system?",
  "sparql_text": "SELECT ?aircraft ?label WHERE { ... }",
  "contract_json": {
    "require_columns": ["aircraft", "label"],
    "min_rows": 1,
    "max_latency_ms": 1000
  },
  "status": "active"
}
```

### Contract Validation
**Pass Criteria:**
- Query compiles without errors
- Returns all `require_columns`
- Meets `min_rows` threshold (if specified)
- Completes within `max_latency_ms` (if specified)

## 🚀 Getting Started

### 1. Access the Workbench
- **Main ODRAS Interface**: Click the CQ/MT icon in the left navigation
- **Direct URL**: `http://localhost:8000/cqmt-workbench`
- **Credentials**: Use your ODRAS login (e.g., `das_service/das_service_2024!`)

### 2. Create Your First Project
1. Select an existing project or create new one
2. The CQ/MT Workbench should be your **starting point** for new projects

### 3. Define Competency Questions
Example CQs for an aviation domain:

```sparql
-- CQ 1: List All Aircraft
SELECT ?aircraft ?label WHERE {
    ?aircraft rdf:type ex:Aircraft .
    ?aircraft rdfs:label ?label .
}

-- CQ 2: Fighter Aircraft Only  
SELECT ?aircraft ?label WHERE {
    ?aircraft rdf:type ex:Aircraft .
    ?aircraft rdfs:label ?label .
    ?aircraft ex:hasRole ex:Fighter .
}

-- CQ 3: Aircraft Without Roles (Gap Analysis)
SELECT ?aircraft ?label WHERE {
    ?aircraft rdf:type ex:Aircraft .
    ?aircraft rdfs:label ?label .
    FILTER NOT EXISTS { ?aircraft ex:hasRole ?role }
}
```

### 4. Create Microtheories
- **Baseline MT**: Your main working microtheory
- **Test MTs**: For testing edge cases, alternative scenarios
- **Clone MTs**: For experimentation without affecting baseline

### 5. Run and Iterate
1. Run CQs → See what fails
2. Switch to Ontology Workbench → Add missing classes/properties
3. Return to CQ/MT Workbench → Re-run CQs
4. Continue until all CQs pass

## 🔧 API Reference

### Microtheory Endpoints

**Create Microtheory**
```http
POST /api/cqmt/projects/{project_id}/microtheories
{
  "label": "Baseline",
  "cloneFrom": "http://localhost:8000/mt/other-project/source",
  "setDefault": true
}
```

**List Microtheories**
```http
GET /api/cqmt/projects/{project_id}/microtheories
→ [{"id": "uuid", "label": "Baseline", "triple_count": 42, ...}]
```

### Competency Question Endpoints

**Create CQ**
```http
POST /api/cqmt/projects/{project_id}/cqs
{
  "cq_name": "List All Aircraft",
  "problem_text": "What aircraft are in the system?",
  "sparql_text": "SELECT ?aircraft ?label WHERE { ... }",
  "contract_json": {
    "require_columns": ["aircraft", "label"],
    "min_rows": 1
  }
}
```

**Run CQ**
```http
POST /api/cqmt/cqs/{cq_id}/run
{
  "mt_iri": "http://localhost:8000/mt/project/baseline",
  "params": {"aircraft_type": "Fighter"}
}
→ {"pass": true, "columns": [...], "row_count": 3, "latency_ms": 45}
```

## 🤖 DAS Assist Features

### SPARQL Suggestion
**Input**: Natural language problem statement  
**Output**: Template SPARQL with TODO comments

```javascript
// Frontend usage
await fetch('/api/cqmt/assist/suggest-sparql', {
  method: 'POST',
  body: JSON.stringify({problem_text: "Find all aircraft types"})
})
```

### Ontology Delta Analysis
**Input**: SPARQL query  
**Output**: Lists of existing and missing ontology terms

```javascript
// Frontend usage  
await fetch('/api/cqmt/assist/suggest-ontology-deltas', {
  method: 'POST',
  body: JSON.stringify({
    sparql_text: "SELECT ?aircraft WHERE { ?aircraft ex:hasRole ?role }",
    project_id: "project-uuid"
  })
})
→ {"existing": ["ex:hasRole"], "missing": ["ex:Aircraft", "ex:Fighter"]}
```

## 🔗 Integration with Other Workbenches

### Deep Links to Ontology Workbench
When a CQ fails due to missing terms:
```
/ontology-editor.html?project={project_id}&iris={missing_iri1},{missing_iri2}
```
The Ontology Workbench can filter to show those specific classes/properties.

### Deep Links from Ontology Workbench
When editing ontology terms:
```
/cqmt-workbench.html?project={project_id}&filter_iris={modified_iri}
```
The CQ/MT Workbench shows CQs that reference those terms.

### Event Integration
- **Published**: `cq.run.completed` events when CQs finish executing
- **Consumed**: `ontology.commit.completed` events to re-run impacted CQs

## 🎛️ Parameter Binding

CQs support **Mustache-style parameter binding** in SPARQL templates:

```sparql
-- Template
SELECT ?aircraft ?label WHERE {
    ?aircraft rdf:type ex:Aircraft .
    ?aircraft rdfs:label ?label .
    ?aircraft ex:hasRole {{iri role_type}} .
    FILTER(CONTAINS(LCASE(?label), LCASE({{aircraft_name}})))
}

-- Parameters
{
  "role_type": "http://example.org/ontology/Fighter",
  "aircraft_name": "falcon"
}

-- Bound Result
SELECT ?aircraft ?label WHERE {
    ?aircraft rdf:type ex:Aircraft .
    ?aircraft rdfs:label ?label .
    ?aircraft ex:hasRole <http://example.org/ontology/Fighter> .
    FILTER(CONTAINS(LCASE(?label), LCASE("falcon")))
}
```

**Binding Syntax:**
- `{{var}}` → Escaped string literal: `"value"`
- `{{iri var}}` → IRI with validation: `<http://example.org/value>`

## 📈 Coverage Analysis

The Coverage tab provides project-wide analytics:

**Per Microtheory:**
- Total CQs that use this MT
- CQs passing vs failing  
- Coverage percentage
- Visual progress bars

**Overall Project:**
- Total CQs defined
- Active vs draft CQs
- Recently passing vs failing
- Trend analysis

## 🧪 Testing and Demo Data

### Quick Demo Setup
1. **Seed demo data**:
   ```bash
   python scripts/seed_cqmt_demo.py
   ```

2. **Login**: Use `das_service/das_service_2024!`

3. **Select**: "CQ/MT Demo" project

4. **Explore**: 
   - 5 sample CQs (aviation domain)
   - 2 microtheories (baseline with data, empty for testing)
   - Pre-populated run history

### Integration Tests
Run comprehensive tests:
```bash
pytest tests/test_cqmt_workbench.py -v -s
```

**Test Coverage:**
- Microtheory CRUD lifecycle
- CQ creation, editing, execution
- Contract validation (pass/fail scenarios)
- Parameter binding
- DAS assist stubs
- Error handling

## 🔍 Troubleshooting

### Common Issues

**CQ Always Fails**
- Check SPARQL syntax in CQ editor
- Verify microtheory has relevant triples
- Check contract requirements are achievable
- Review parameter binding ({{var}} syntax)

**Microtheory Creation Fails**
- Verify Fuseki is running (`http://localhost:3030`)
- Check for duplicate MT labels in project
- Ensure valid IRI format if custom IRI provided

**No Results in Coverage**
- Ensure CQs have been run at least once
- Check that microtheories have data
- Verify project has both CQs and MTs

### Debug Tools

**Check Fuseki Graphs**:
```sparql
# List all named graphs
SELECT DISTINCT ?g WHERE { GRAPH ?g { ?s ?p ?o } }

# Count triples in specific MT
SELECT (COUNT(*) AS ?count) WHERE { 
  GRAPH <http://localhost:8000/mt/project-id/baseline> { ?s ?p ?o } 
}
```

**Database Queries**:
```sql
-- List CQs by project
SELECT cq_name, status, created_at FROM cqs WHERE project_id = 'your-project-id';

-- Recent CQ runs
SELECT c.cq_name, r.pass, r.reason, r.created_at 
FROM cqs c JOIN cq_runs r ON c.id = r.cq_id 
WHERE c.project_id = 'your-project-id' 
ORDER BY r.created_at DESC;
```

## 🎯 Best Practices

### Writing Effective CQs

**1. Start Simple**
```sparql
-- Good: Basic listing
SELECT ?item ?label WHERE {
  ?item rdf:type ex:YourClass .
  ?item rdfs:label ?label .
}
```

**2. Add Complexity Gradually**
```sparql
-- Better: With filtering
SELECT ?item ?label ?category WHERE {
  ?item rdf:type ex:YourClass .
  ?item rdfs:label ?label .
  ?item ex:hasCategory ?category .
  FILTER(?category = ex:SpecificType)
}
```

**3. Design for Failure**
```sparql
-- Excellent: Gap detection
SELECT ?item WHERE {
  ?item rdf:type ex:YourClass .
  FILTER NOT EXISTS { ?item ex:requiredProperty ?value }
}
```

### Microtheory Strategy

**Baseline MT**: Core production data and ontology
**Development MTs**: Clone baseline for experimental changes  
**Test MTs**: Edge cases, boundary conditions
**Archive MTs**: Snapshots for specific milestones

### Contract Design

**Minimal Contracts** (prefer these):
```json
{"require_columns": ["subject", "label"]}
```

**Strict Contracts** (use sparingly):
```json
{
  "require_columns": ["aircraft", "type", "status"],
  "min_rows": 10,
  "max_latency_ms": 500
}
```

## 🚀 Advanced Features

### Cross-Workbench Integration
- **Failed CQ** → Click "Open in Ontology Workbench" → Add missing terms
- **Ontology change** → Auto re-run related CQs → Verify no regression
- **Project dashboard** → CQ pass/fail metrics feed into project health

### Event-Driven Updates
- CQ runs publish `cq.run.completed` events
- Other systems can subscribe to track ontology validation progress
- Future: Auto-trigger CQ runs when ontology changes

### Extensibility Points
- **Custom contract validators**: Beyond min_rows/latency 
- **Advanced parameter binding**: Complex object parameters
- **Enhanced DAS assist**: LLM-powered SPARQL generation
- **Performance optimization**: Parallel CQ execution

## 📚 Related Documentation

- **[Ontology Workbench Guide](ONTOLOGY_WORKBENCH_GUIDE.md)** - Building the ontology to satisfy CQs
- **[Requirements Workbench Guide](REQUIREMENTS_WORKBENCH_GUIDE.md)** - Requirements that drive CQ creation  
- **[DAS Comprehensive Guide](../architecture/DAS_COMPREHENSIVE_GUIDE.md)** - DAS assist integration
- **[Testing Guide](../development/TESTING_GUIDE.md)** - Running integration tests

---

**🎯 Success Metric**: When all your CQs pass, you have confidence that your ontology serves its intended purpose and can answer the questions your stakeholders care about.
