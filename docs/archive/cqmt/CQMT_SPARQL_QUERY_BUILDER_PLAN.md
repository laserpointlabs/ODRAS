# CQ/MT SPARQL Query Builder - Implementation Plan

## Current State Analysis

### Existing Capabilities
1. **SPARQL Suggestion API** (`/api/cqmt/assist/suggest-sparql`)
   - Current: Returns basic template with hardcoded prefixes
   - Problem: Uses `ex:` and example namespace, not project-specific
   - Issue: Users must manually replace prefixes and IRIs

2. **Ontology Delta Analysis** (`/api/cqmt/assist/suggest-ontology-deltas`)
   - Current: Stub that extracts IRIs from SPARQL but doesn't check Fuseki
   - Future: Should validate against actual ontology

3. **CQ Execution** (`/api/cqmt/cqs/{cq_id}/run`)
   - Works: Executes SPARQL against Fuseki with microtheory context
   - Returns: Pass/fail, columns, row count, data preview

### Identified Problems

1. **Prefix Management**
   - Users manually type prefixes (error-prone)
   - No automatic prefix injection based on project/ontology
   - Prefix namespace varies by project

2. **Query Testing**
   - No way to test SPARQL during CQ creation
   - Must save CQ first, then run it
   - Slow feedback loop for debugging

3. **Query Building Assistance**
   - "Suggest SPARQL" returns generic template
   - No interactive help or DAS integration
   - No validation against ontology during authoring

## User Workflows

### Workflow 1: Creating a New CQ
```
1. User clicks "Create CQ"
2. Fills in: Name, Problem Statement
3. Clicks "Suggest SPARQL" or types manually
4. Want to test query before saving
5. Wants to insert classes/properties from ontology
6. Saves CQ when satisfied
```

### Workflow 2: Testing During Development
```
1. User writing SPARQL query
2. Wants to test against specific microtheory
3. Sees results immediately
4. Adjusts query based on results
5. Repeats until correct
```

### Workflow 3: AI-Assisted Query Building
```
1. User describes problem in natural language
2. DAS analyzes ontology structure
3. DAS suggests SPARQL query
4. User reviews and modifies
5. Tests against microtheory
```

## Proposed Solutions

### Solution 1: SPARQL Query Builder Modal

**Purpose**: Interactive SPARQL query building with DAS assistance and live testing

**Features**:
1. **Automatic Prefix Injection**
   - Detect ontology from project context
   - Auto-inject correct prefixes (from ontology metadata)
   - Show available prefixes in sidebar

2. **Live Query Testing**
   - "Test Query" button executes against selected microtheory
   - Shows results in modal below editor
   - Real-time validation feedback

3. **DAS Integration**
   - "Suggest with DAS" button sends problem statement + ontology context
   - DAS generates SPARQL using ontology classes/properties
   - Returns query with actual IRIs from project ontology

4. **Ontology Browser Integration**
   - Browse classes/properties and insert into query
   - Show tooltips with IRI for each term
   - Auto-complete based on ontology terms

**Modal Layout**:
```
┌─────────────────────────────────────────────────────┐
│ SPARQL Query Builder                              [X]│
├─────────────────────────────────────────────────────┤
│ Problem: [What aircraft are available?]          │
│                                                     │
│ Toolbar: [Suggest with DAS] [Browse Ontology]     │
│          [Test Query ▼] [Insert Prefixes]        │
│                                                     │
│ Query Editor:                                      │
│ ┌─────────────────────────────────────────────┐   │
│ │ PREFIX : <http://xma-adt.usnc.mil/projects/  │   │
│ │         12cd447e-c8c3-40c9-8192-2928bf7f81a8│   │
│ │         /ontologies/test-ontology#>         │   │
│ │ PREFIX rdf: <http://www.w3.org/1999/02/22/  │   │
│ │         rdf-syntax-ns#>                     │   │
│ │ PREFIX rdfs: <http://www.w3.org/2000/01/    │   │
│ │         rdf-schema#>                        │   │
│ │                                             │   │
│ │ SELECT ?aircraft ?label WHERE {            │   │
│ │     ?aircraft rdf:type :Aircraft .         │   │
│ │     ?aircraft rdfs:label ?label .          │   │
│ │ }                                          │   │
│ └─────────────────────────────────────────────┘   │
│                                                     │
│ Test Results:                                       │
│ ┌─────────────────────────────────────────────┐   │
│ │ Microtheory: [Baseline ▼] [Test]           │   │
│ │                                             │   │
│ │ ✅ Query executed successfully              │   │
│ │ Rows: 4 | Time: 12ms                       │   │
│ │                                             │   │
│ │ aircraft        | label                    │   │
│ │ ────────────────────────────────────────   │   │
│ │ :F22            | F-22 Raptor              │   │
│ │ :F35            | F-35 Lightning II        │   │
│ │ :C130           | C-130 Hercules           │   │
│ │ :C17            | C-17 Globemaster III    │   │
│ └─────────────────────────────────────────────┘   │
│                                                     │
│                  [Cancel] [Use This Query]        │
└─────────────────────────────────────────────────────┘
```

### Solution 2: Prefix Auto-Injection API

**New Endpoint**: `GET /api/cqmt/projects/{project_id}/prefixes`

**Returns**:
```json
{
  "prefixes": [
    {"prefix": ":", "iri": "http://xma-adt.usnc.mil/projects/.../ontologies/test-ontology#"},
    {"prefix": "rdf:", "iri": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"},
    {"prefix": "rdfs:", "iri": "http://www.w3.org/2000/01/rdf-schema#"},
    {"prefix": "owl:", "iri": "http://www.w3.org/2002/07/owl#"}
  ],
  "default_ns": "http://xma-adt.usnc.mil/projects/.../ontologies/test-ontology#"
}
```

**Usage**:
- Query Builder modal calls this on load
- Auto-injects prefixes into editor
- Shows prefix list in sidebar for reference

### Solution 3: Enhanced DAS SPARQL Suggestion

**Endpoint Update**: `POST /api/cqmt/assist/suggest-sparql`

**Request**:
```json
{
  "problem_text": "What aircraft are available?",
  "project_id": "uuid",
  "ontology_graph_iri": "http://...",
  "use_das": true
}
```

**Process**:
1. Load ontology classes/properties using existing `/api/ontology/` endpoint
2. Send to DAS with context: problem + ontology structure
3. DAS generates SPARQL using actual ontology terms
4. Return query with correct prefixes and IRIs

### Solution 4: Test Query Endpoint

**New Endpoint**: `POST /api/cqmt/test-query`

**Request**:
```json
{
  "sparql": "SELECT ?s WHERE { ?s rdf:type :Aircraft }",
  "mt_iri": "http://...baseline",
  "project_id": "uuid"
}
```

**Returns**:
```json
{
  "success": true,
  "columns": ["s"],
  "rows": [...],
  "row_count": 4,
  "execution_time_ms": 12,
  "errors": []
}
```

**Usage**:
- Called from Query Builder modal when "Test Query" clicked
- Returns immediate results without saving CQ
- Shows errors clearly if query fails

## Implementation Steps

### Phase 1: Prefix Management (Quick Win)
1. Create `GET /api/cqmt/projects/{project_id}/prefixes` endpoint
2. Update "Suggest SPARQL" to inject project prefixes
3. Add "Insert Prefixes" button in CQ modal

### Phase 2: Test Query Endpoint
1. Create `POST /api/cqmt/test-query` endpoint
2. Reuse existing CQ execution logic
3. Add "Test Query" button to CQ modal
4. Show results inline below SPARQL editor

### Phase 3: Query Builder Modal
1. Create new modal component
2. Integrate prefix auto-injection
3. Integrate test query functionality
4. Replace current "Suggest SPARQL" behavior

### Phase 4: DAS Integration
1. Enhance `/api/cqmt/assist/suggest-sparql` endpoint
2. Add ontology loading and context passing
3. Integrate with DAS for intelligent suggestions
4. Update Query Builder to use DAS suggestions

## Technical Considerations

### Prefix Handling
- Extract namespace from ontology graph IRI
- Use URI service to get project namespace
- Handle both project ontologies and reference ontologies
- Support multiple ontologies per project

### Query Execution
- Reuse existing Fuseki integration
- Handle named graph context properly
- Timeout long-running queries
- Validate SPARQL syntax before execution

### DAS Integration
- Keep DAS prompts focused on ontology context
- Limit query complexity to prevent hallucinations
- Return confidence scores
- Suggest multiple query variations

## Success Criteria

1. ✅ Users can test SPARQL queries before saving CQ
2. ✅ Prefixes are automatically injected based on project
3. ✅ DAS generates queries using actual ontology terms
4. ✅ Query execution provides immediate feedback
5. ✅ No manual prefix typing required
6. ✅ Faster CQ development workflow

## Open Questions

1. Should test queries persist in history? (Probably not for ephemeral testing)
2. How to handle multiple ontologies in one project?
3. Should we show query optimization suggestions?
4. How to handle very large result sets in test view?
