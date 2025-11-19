<!-- 73b38aa9-fc37-4f8b-9e3c-ef4698f941d3 bb830bad-b052-4b9e-976a-5e27c6fb6cd4 -->
# CQ/MT Workbench Implementation Plan

## Workflow Philosophy: Test-Driven Ontology Development

The CQ/MT Workbench enables a **requirements-first approach** to ontology development:

**Traditional Approach (Bottom-Up):**

```
Build Ontology → Hope it meets needs → Discover gaps later
```

**CQ/MT Approach (Test-Driven):**

```
1. Define Competency Questions (what must the ontology answer?)
2. Create baseline Microtheory (empty or minimal)
3. Run CQs → They FAIL (ontology incomplete)
4. Build ontology classes/properties in Ontology Workbench
5. Re-run CQs → Track progress toward PASS
6. Iterate until all CQs pass
```

**Benefits:**

- **Clear requirements**: CQs are executable specifications
- **Objective validation**: Pass/fail, not subjective review
- **Prevents over-engineering**: Build only what CQs require
- **Living documentation**: CQs document ontology capabilities
- **Change impact**: Re-run CQs to verify ontology changes

**User Journey:**

1. Create new project in ODRAS
2. Open CQ/MT Workbench (starting point)
3. Define 5-10 competency questions for the domain
4. Create baseline microtheory
5. Run CQs → See what's missing
6. Switch to Ontology Workbench → Build needed classes/properties
7. Return to CQ/MT Workbench → Verify CQs now pass
8. Continue iterating

## Architecture Overview

Build CQ/MT Workbench following existing ODRAS workbench patterns (similar to Ontology Workbench, Requirements Workbench):

**Data Flow:**

```
User → cqmt-workbench.html → /api/cqmt/* → CQMTService → Fuseki (MTs as named graphs)
                                             ↓
                                        PostgreSQL (CQ metadata, run history)
```

**Component Structure:**

```
backend/api/cqmt.py              # API routes (CQ CRUD, MT management, CQ runner)
backend/services/cqmt_service.py # Business logic (CQ execution, MT operations)
backend/services/sparql_runner.py # SPARQL runner with graph confinement
frontend/cqmt-workbench.html     # UI (matches ontology-editor.html patterns)
backend/migrations/020_cqmt_schema.sql # CQ/MT tables
scripts/seed_cqmt_demo.py        # Demo data seeder
tests/test_cqmt_workbench.py     # Integration tests
```

**Integration Points:**

- Shared: Auth (`get_user`), Projects, Fuseki connection
- Deep links: CQ → Ontology Workbench (pass IRIs as query params)
- Events: Redis pub/sub for `cq.run.completed`, `ontology.commit.completed`
- DAS assist: Stubs in DAS API for SPARQL suggestion

## Database Schema

### SQL Tables (PostgreSQL)

**`cqs` table:**

```sql
CREATE TABLE IF NOT EXISTS cqs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    cq_name VARCHAR(255) NOT NULL,
    problem_text TEXT NOT NULL,
    params_json JSONB DEFAULT '{}',
    sparql_text TEXT NOT NULL,
    mt_iri_default VARCHAR(1000),
    contract_json JSONB NOT NULL,  -- {require_columns, min_rows?, max_latency_ms?}
    status VARCHAR(50) DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'deprecated')),
    created_by UUID REFERENCES users(user_id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, cq_name)
);
```

**`cq_runs` table:**

```sql
CREATE TABLE IF NOT EXISTS cq_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cq_id UUID NOT NULL REFERENCES cqs(id) ON DELETE CASCADE,
    mt_iri VARCHAR(1000) NOT NULL,
    params_json JSONB DEFAULT '{}',
    pass BOOLEAN NOT NULL,
    reason TEXT,
    row_count INT,
    columns_json JSONB,
    rows_preview_json JSONB,
    latency_ms INT,
    executed_by UUID REFERENCES users(user_id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_cq_runs_cq_id ON cq_runs(cq_id);
CREATE INDEX idx_cq_runs_created_at ON cq_runs(created_at DESC);
```

**`microtheories` table:**

```sql
CREATE TABLE IF NOT EXISTS microtheories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    label VARCHAR(255) NOT NULL,
    iri VARCHAR(1000) UNIQUE NOT NULL,
    parent_iri VARCHAR(1000),  -- NULL or IRI of cloned source
    is_default BOOLEAN DEFAULT FALSE,
    created_by UUID REFERENCES users(user_id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(project_id, label)
);
CREATE INDEX idx_mt_project_id ON microtheories(project_id);
```

### Triplestore (Fuseki Named Graphs)

**Shared TBox graphs (read-only):**

- `<http://localhost:8000/ontology/core>` - Core ODRAS ontology
- `<http://localhost:8000/ontology/{project_id}/base>` - Project base ontology

**MT ABox graphs (read-write per project):**

- `<http://localhost:8000/mt/{project_id}/{mt_slug}>` - Per-MT named graph
- Example: `<http://localhost:8000/mt/abc-123/baseline>`

## API Design

### Microtheory Endpoints

**POST /api/cqmt/projects/{project_id}/microtheories**

- Body: `{ label, iri?, cloneFrom?, setDefault? }`
- Creates MT named graph in Fuseki
- If `cloneFrom` provided, copies all triples from source graph
- Returns: `{ id, label, iri, created_at }`

**GET /api/cqmt/projects/{project_id}/microtheories**

- Returns: `[{ id, label, iri, parent_iri, is_default, triple_count, created_at }]`
- Includes triple count from Fuseki for each MT

**DELETE /api/cqmt/microtheories/{mt_id}**

- Drops named graph from Fuseki
- Deletes SQL record
- Returns: `{ success: true }`

**POST /api/cqmt/microtheories/{mt_id}/set-default**

- Marks MT as project default for CQ runs
- Returns: `{ success: true }`

### Competency Question Endpoints

**POST /api/cqmt/projects/{project_id}/cqs**

- Body: `{ cq_name, problem_text, params_json?, sparql_text, mt_iri_default?, contract_json, status? }`
- Upsert CQ record
- Contract validation: `require_columns` must be array, `min_rows` >= 0, `max_latency_ms` > 0
- Returns: `{ id, cq_name, created_at }`

**GET /api/cqmt/projects/{project_id}/cqs**

- Query params: `?status=active&mt_iri={iri}`
- Returns: `[{ id, cq_name, problem_text, sparql_text, mt_iri_default, contract_json, status, last_run_status, last_run_at }]`

**GET /api/cqmt/cqs/{cq_id}**

- Returns full CQ details including last 5 runs

**POST /api/cqmt/cqs/{cq_id}/run**

- Body: `{ mt_iri?, params? }`
- Uses `mt_iri` or CQ's default MT
- Binds `params` to SPARQL template (Mustache-style: `{{var}}`)
- Executes SPARQL confined to MT named graph
- Validates contract (columns, min_rows, latency)
- Persists run record
- Publishes `cq.run.completed` event to Redis
- Returns: `{ pass, reason, columns, row_count, rows_preview, latency_ms, run_id }`

**GET /api/cqmt/cqs/{cq_id}/runs**

- Query params: `?limit=20&offset=0`
- Returns paginated run history

### DAS Assist Endpoints (Stubs)

**POST /api/cqmt/assist/suggest-sparql**

- Body: `{ problem_text }`
- Returns: `{ sparql_draft, confidence, notes }`
- Initial stub: Return basic SELECT skeleton with TODO comments

**POST /api/cqmt/assist/suggest-ontology-deltas**

- Body: `{ sparql_text, project_id }`
- Parses SPARQL, extracts referenced IRIs/QNames
- Queries Fuseki shared TBox to check existence
- Returns: `{ existing: [...], missing: [...] }`

## Core Services

### `backend/services/sparql_runner.py`

**`SPARQLRunner` class:**

```python
class SPARQLRunner:
    def __init__(self, fuseki_url: str):
        self.fuseki_url = fuseki_url
        
    def run_select_in_graph(self, graph_iri: str, sparql_template: str, params: dict) -> dict:
        """
        Bind params, wrap SPARQL with GRAPH clause, execute, return results.
        Returns: { columns: [...], rows: [...], latency_ms: int }
        """
        # 1. Bind params (Mustache-style {{var}} replacement with escaping)
        bound_sparql = self._bind_params(sparql_template, params)
        
        # 2. Wrap with GRAPH clause to confine to MT
        confined_sparql = f"SELECT * WHERE {{ GRAPH <{graph_iri}> {{ {bound_sparql} }} }}"
        
        # 3. Execute via Fuseki HTTP API
        # 4. Measure latency
        # 5. Return structured results
        
    def _bind_params(self, sparql: str, params: dict) -> str:
        """
        Replace {{var}} with escaped literal values.
        Replace {{iri var}} with IRI values (validated).
        """
        # Use regex to find {{...}} and {{iri ...}}
        # Validate and escape appropriately
        
    def validate_sparql(self, sparql: str) -> tuple[bool, str]:
        """
        Basic SPARQL syntax validation (try parse).
        Returns: (is_valid, error_message)
        """
```

### `backend/services/cqmt_service.py`

**`CQMTService` class:**

```python
class CQMTService:
    def __init__(self, db: DatabaseService, fuseki_url: str):
        self.db = db
        self.runner = SPARQLRunner(fuseki_url)
        
    # MT Management
    def create_microtheory(self, project_id, label, iri, clone_from=None, created_by=None) -> dict:
        # 1. Insert SQL record
        # 2. Create Fuseki named graph
        # 3. If clone_from, copy triples via SPARQL CONSTRUCT/INSERT
        
    def list_microtheories(self, project_id) -> list:
        # Query SQL + enrich with triple counts from Fuseki
        
    def delete_microtheory(self, mt_id) -> bool:
        # 1. Drop Fuseki named graph
        # 2. Delete SQL record
        
    # CQ Management
    def create_or_update_cq(self, project_id, cq_data) -> dict:
        # Upsert SQL record with validation
        
    def get_cqs(self, project_id, filters) -> list:
        # Query with optional status/MT filters
        
    # CQ Execution
    def run_cq(self, cq_id, mt_iri, params, executed_by) -> dict:
        # 1. Load CQ from SQL
        # 2. Resolve MT IRI (use provided or default)
        # 3. Bind params and run SPARQL via runner
        # 4. Validate contract
        # 5. Persist run record
        # 6. Publish event
        # 7. Return result
        
    def validate_cq_contract(self, result, contract) -> tuple[bool, str]:
        """
        Check require_columns, min_rows, max_latency_ms.
        Returns: (pass, reason)
        """
```

## Frontend UI

### `frontend/cqmt-workbench.html`

**Structure (matches `ontology-editor.html` patterns):**

```html
<!DOCTYPE html>
<html>
<head>
    <title>CQ/MT Workbench - ODRAS</title>
    <style>
        /* Reuse ODRAS styling patterns */
        .tabs { ... }
        .tab-content { ... }
        .cq-list { ... }
        .cq-editor { ... }
        .run-panel { ... }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>CQ/MT Workbench</h1>
            <select id="project-selector"><!-- Projects --></select>
        </div>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab('cqs')">Competency Questions</button>
            <button class="tab" onclick="showTab('microtheories')">Microtheories</button>
            <button class="tab" onclick="showTab('coverage')">Coverage</button>
        </div>
        
        <!-- CQ Tab -->
        <div id="cqs-tab" class="tab-content active">
            <div class="cq-list">
                <button onclick="createNewCQ()">+ New CQ</button>
                <div id="cq-items"><!-- CQ cards --></div>
            </div>
            <div class="cq-editor" id="cq-editor" style="display:none;">
                <input id="cq-name" placeholder="CQ Name">
                <textarea id="problem-text" placeholder="Problem statement"></textarea>
                <textarea id="sparql-text" placeholder="SPARQL query"></textarea>
                <button onclick="suggestSPARQL()">🤖 Suggest SPARQL</button>
                <select id="mt-default"><!-- MT options --></select>
                <textarea id="contract-json" placeholder='{"require_columns": ["id"]}'></textarea>
                <button onclick="saveCQ()">Save</button>
            </div>
            <div class="run-panel" id="run-panel" style="display:none;">
                <select id="run-mt"><!-- MT options --></select>
                <textarea id="run-params" placeholder='{"var1": "value"}'></textarea>
                <button onclick="runCQ()">▶ Run CQ</button>
                <div id="run-results"><!-- Results table, pass/fail badge --></div>
                <div id="run-history"><!-- Last 5 runs --></div>
                <a id="ontology-link" target="_blank" style="display:none;">🔗 Open in Ontology Workbench</a>
            </div>
        </div>
        
        <!-- MT Tab -->
        <div id="microtheories-tab" class="tab-content">
            <button onclick="createNewMT()">+ New Microtheory</button>
            <div id="mt-list"><!-- MT cards with triple counts --></div>
        </div>
        
        <!-- Coverage Tab -->
        <div id="coverage-tab" class="tab-content">
            <div id="coverage-summary">
                <!-- Per-MT: total CQs, passing, failing, % passing -->
            </div>
        </div>
    </div>
    
    <script>
        let currentProjectId = null;
        let selectedCQId = null;
        
        // Initialize
        async function init() {
            await loadProjects();
            await loadMicrotheories();
            await loadCQs();
        }
        
        // CQ Functions
        async function loadCQs() { /* GET /api/cqmt/projects/{pid}/cqs */ }
        async function saveCQ() { /* POST /api/cqmt/projects/{pid}/cqs */ }
        async function runCQ() { /* POST /api/cqmt/cqs/{id}/run */ }
        async function suggestSPARQL() { /* POST /api/cqmt/assist/suggest-sparql */ }
        
        // MT Functions
        async function loadMicrotheories() { /* GET /api/cqmt/projects/{pid}/microtheories */ }
        async function createNewMT() { /* POST /api/cqmt/projects/{pid}/microtheories */ }
        async function deleteMT(mtId) { /* DELETE /api/cqmt/microtheories/{id} */ }
        
        // Coverage
        async function loadCoverage() { /* Aggregate run results */ }
        
        // Deep link to Ontology Workbench
        function buildOntologyLink(iris) {
            // URL: /ontology-editor.html?iris=<iri1>,<iri2>
        }
    </script>
</body>
</html>
```

## Integration & Events

### Redis Pub/Sub Events

**Event: `cq.run.completed`**

```json
{
  "event": "cq.run.completed",
  "timestamp": "2025-10-21T12:34:56Z",
  "project_id": "abc-123",
  "cq_id": "uuid",
  "cq_name": "Get all missions",
  "mt_iri": "http://localhost:8000/mt/abc-123/baseline",
  "pass": false,
  "reason": "min_rows_not_met",
  "latency_ms": 45
}
```

**Event: `ontology.commit.completed`** (consumed)

- Trigger: Re-run impacted CQs (those referencing changed IRIs)
- Implementation: Background task that queries CQs using changed IRIs

### Deep Links

**From CQ to Ontology Workbench:**

- Extract referenced IRIs from SPARQL (regex parse)
- Build URL: `/ontology-editor.html?project={pid}&iris={iri1},{iri2}`
- Ontology Workbench filters to show those classes/properties

**From Ontology Workbench to CQ/MT Workbench:**

- Add link: `/cqmt-workbench.html?project={pid}&filter_iris={iri}`
- CQ Workbench shows CQs that reference the IRI

## DAS Assist Implementation

### Suggest SPARQL (Initial Stub)

```python
async def suggest_sparql(problem_text: str, project_id: str) -> dict:
    """
    V1: Return template SELECT with TODO comments.
    V2 (future): Use LLM to draft SPARQL from problem text + ontology context.
    """
    template = f"""
# Problem: {problem_text}
# TODO: Replace variables and IRIs with project-specific values

PREFIX ex: <http://example.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?subject ?label WHERE {{
    # TODO: Add triple patterns here
    ?subject rdfs:label ?label .
}}
LIMIT 10
"""
    return {
        "sparql_draft": template,
        "confidence": 0.3,
        "notes": "This is a basic template. Review and customize for your ontology."
    }
```

### Suggest Ontology Deltas

```python
async def suggest_ontology_deltas(sparql_text: str, project_id: str) -> dict:
    """
    Parse SPARQL, extract IRIs, check against project ontology in Fuseki.
    """
    # 1. Extract IRIs from SPARQL (regex: <http://...> and QName resolution)
    referenced_iris = extract_iris_from_sparql(sparql_text)
    
    # 2. Query Fuseki TBox graphs for project
    existing_iris = query_fuseki_for_iris(project_id, referenced_iris)
    
    # 3. Diff
    missing_iris = set(referenced_iris) - set(existing_iris)
    
    return {
        "existing": list(existing_iris),
        "missing": list(missing_iris)
    }
```

## DevOps & Testing

### Docker Compose (Already in place)

- Fuseki: `http://localhost:3030` (existing service)
- PostgreSQL: `http://localhost:5432` (existing service)
- Redis: `http://localhost:6379` (existing service)
- ODRAS API: `http://localhost:8000` (mount new routes)

### Migration Integration

Add to `odras.sh` `init-db` function:

```bash
# CQ/MT Workbench schema
psql -U postgres -d odras -f backend/migrations/020_cqmt_schema.sql
```

Add to `backend/migrations/migration_order.txt`:

```
020_cqmt_schema.sql
```

### Seed Script: `scripts/seed_cqmt_demo.py`

```python
"""
Create demo project, MT, sample triples, and CQ.
Usage: python scripts/seed_cqmt_demo.py
"""

async def seed_demo():
    # 1. Create project "CQ-Demo"
    # 2. Create MT "baseline" with demo triples (3 example triples)
    # 3. Create CQ "List all subjects" with minimal contract
    # 4. Run CQ → should PASS
    # 5. Create empty MT "empty-test"
    # 6. Run CQ in "empty-test" → should FAIL (min_rows_not_met)
    # 7. Print summary
```

### Tests: `tests/test_cqmt_workbench.py`

```python
@pytest.mark.integration
class TestCQMTWorkbench:
    def test_create_microtheory(self, auth_token):
        # POST /api/cqmt/projects/{pid}/microtheories
        # Verify SQL record and Fuseki graph created
        
    def test_clone_microtheory(self, auth_token):
        # Create MT with triples, clone, verify triples copied
        
    def test_create_cq(self, auth_token):
        # POST /api/cqmt/projects/{pid}/cqs
        # Verify SQL record
        
    def test_run_cq_pass(self, auth_token):
        # Create MT with data, create CQ, run → PASS
        # Verify run record persisted
        
    def test_run_cq_fail_min_rows(self, auth_token):
        # Run CQ in empty MT → FAIL with min_rows_not_met
        
    def test_run_cq_fail_missing_columns(self, auth_token):
        # CQ requires ["id", "label"], SPARQL returns only ["id"] → FAIL
        
    def test_sparql_confinement(self, auth_token):
        # Verify SPARQL only accesses specified MT graph, not others
        
    def test_suggest_sparql_stub(self, auth_token):
        # POST /api/cqmt/assist/suggest-sparql
        # Verify template returned
        
    def test_suggest_ontology_deltas(self, auth_token):
        # POST /api/cqmt/assist/suggest-ontology-deltas
        # Verify missing/existing IRIs identified
```

## Implementation Sequence

1. **Database migration** (`020_cqmt_schema.sql`) with 3 tables
2. **SPARQL runner service** (`backend/services/sparql_runner.py`) with param binding and graph confinement
3. **CQMT service** (`backend/services/cqmt_service.py`) with MT and CQ operations
4. **API routes** (`backend/api/cqmt.py`) for all endpoints
5. **Frontend UI** (`frontend/cqmt-workbench.html`) with CQ/MT/Coverage tabs
6. **DAS assist stubs** in existing DAS API or new cqmt assist routes
7. **Event publishing** to Redis for `cq.run.completed`
8. **Seed script** (`scripts/seed_cqmt_demo.py`)
9. **Integration tests** (`tests/test_cqmt_workbench.py`)
10. **Update navigation** in `frontend/app.html` to link to CQ/MT Workbench
11. **Documentation** in `docs/features/CQMT_WORKBENCH_GUIDE.md`

## File Deliverables

1. `backend/migrations/020_cqmt_schema.sql` - CQ/MT tables
2. `backend/services/sparql_runner.py` - SPARQL execution engine
3. `backend/services/cqmt_service.py` - Business logic
4. `backend/api/cqmt.py` - API routes (FastAPI router)
5. `frontend/cqmt-workbench.html` - Full UI
6. `scripts/seed_cqmt_demo.py` - Demo data seeder
7. `tests/test_cqmt_workbench.py` - Integration tests
8. `docs/features/CQMT_WORKBENCH_GUIDE.md` - User guide
9. Update `backend/main.py` to include cqmt router
10. Update `odras.sh` init-db to run migration
11. Update `backend/migrations/migration_order.txt`

## Acceptance Criteria

✅ Create project, create MT, load 3 demo triples

✅ Create CQ with `require_columns: ["subject"]`, `min_rows: 1`

✅ Run CQ in populated MT → PASS

✅ Run CQ in empty cloned MT → FAIL with `min_rows_not_met`

✅ Delete cloned MT without affecting source

✅ From failed CQ, show deep link to Ontology Workbench

✅ Assist deltas return `{missing: [...], existing: [...]}`

✅ All tests pass with das_service credentials

✅ UI accessible at `/cqmt-workbench.html`

## Success Metrics

- 11 new files created, all in appropriate directories
- Zero modifications to core Ontology Workbench code
- CQ/MT Workbench fully functional standalone
- Integration via events and deep links only
- All tests pass against full ODRAS stack

### To-dos

- [ ] Create database migration 020_cqmt_schema.sql with cqs, cq_runs, and microtheories tables
- [ ] Implement SPARQLRunner service with parameter binding, graph confinement, and validation
- [ ] Implement CQMTService with MT CRUD, CQ CRUD, CQ execution, and contract validation
- [ ] Create FastAPI router with all CQ/MT endpoints and DAS assist stubs
- [ ] Build cqmt-workbench.html with CQ editor, MT manager, run panel, and coverage view
- [ ] Create seed_cqmt_demo.py to populate demo project, MT with triples, and sample CQ
- [ ] Write comprehensive integration tests for all CQ/MT operations
- [ ] Wire CQ/MT API into main.py, update odras.sh init-db, add navigation link
- [ ] Create CQMT_WORKBENCH_GUIDE.md with usage examples and architecture overview