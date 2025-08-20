# TODO – UI Restart (MVP Refresh)

This document tracks the MVP-critical tasks for the UI restart. We will not commit changes until explicitly approved.

## Covered
- Layout/navigation: top/bottom toolbars, left icon bar, resizable tree
- Projects/auth (MVP): in-memory login, project create/select, project-scoped tree
- Graph DB: Graph Explorer with SPARQL summary and ad‑hoc queries

## Missing for MVP
- Ontology Workbench (Cytoscape-based editor)
  - Load/save ontology from/to Fuseki named graph (per selected ontology in main tree)
    - Load: CONSTRUCT GRAPH <iri> → UI model; Load layout JSON if present
    - Save: DROP GRAPH <iri>; INSERT DATA { GRAPH <iri> { ... } } and PUT layout JSON
    - Save to Fuseki (MVP steps)
      - Frontend
        - Add Save button and Ctrl/Cmd+S to trigger save for the active ontology
        - Serialize canvas → Turtle (MVP)
          - Classes: <graph#ClassName> a owl:Class; rdfs:label "Label"
          - Object properties: <graph#prop> a owl:ObjectProperty; rdfs:label "name"; rdfs:domain <graph#Source>; rdfs:range <graph#Target>
          - Datatype properties: <graph#prop> a owl:DatatypeProperty; rdfs:label "name"; rdfs:domain <graph#Class>; (range: xsd:string for MVP)
          - Notes are UI-only; exclude from Turtle
        - Mint stable IRIs per graph (slug from label) and persist a per-graph id→IRI map in localStorage so IRIs don’t churn on rename
        - POST text/turtle to backend `/api/ontology/save?graph=<iri>`; on success show toast and clear dirty flag
      - Backend
        - Implement POST `/api/ontology/save?graph=<iri>` (body: text/turtle)
          - Validate `graph` param; PUT to Fuseki Graph Store `/data?graph=<iri>` with `Content-Type: text/turtle`
          - Handle auth/timeouts; return 200/4xx/5xx with message
        - Optional: `PUT /layout?graph=<iri>` to persist layout JSON (positions, zoom/pan)
      - Tests/UX
        - Save separate models in `base_se_v1` and `base_se_v2`; verify isolation and no cross-bleed
        - Error toasts on failure; retry path; confirm saved triple counts later
  - Separate layout persistence (node positions, zoom/pan) per graph IRI
  - Simple, direct manipulation editing (no popups)
    - Drag from palette to create Class/Data Property
    - Edge-handles to create Object Property
    - Inline rename of node/edge labels (click/F2 → input → Enter/Esc)
    - Keyboard: Delete removes selection; Ctrl/Cmd+S saves; Esc cancels inline edit
    - Drag to reposition; pan/zoom; auto-layout
  - Properties panel
    - Show/edit rdfs:label, rdfs:domain, rdfs:range, type, attrs (JSON)
    - Sync with inline edits; background shows model metadata
  - IRI minting & validation
    - Create IRIs in base namespace; ensure uniqueness; basic integrity checks
  - Imports (defer)
    - Read-only overlays in later iteration; hidden in MVP

- Files Workbench
  - Upload/list with categories
    - Requirements Documents (project-scoped)
    - Knowledge Documents (project-scoped)
  - Update tree on change

- Embedding Workbench
  - Chunk size/overlap/model settings
  - "Process" action; persist to vector store
  - Status feedback

- Requirements Workbench
  - Wire to current extraction + SME review flow
    - Start extraction per document/project
    - Show pending user task; allow edit/approve
    - Push requirements + metadata to RDF/GraphDB/Vector store

- Process Workbench
  - BPMN deploy/reset/start
  - List and open user tasks
  - Per-project runs

- GraphDB Workbench
  - Visual editor for nodes and relationships
    - Add/edit/delete nodes (with labels/properties)
    - Add/edit/delete relationships (with types/properties)
  - "Push to Neo4j" (per project)
  - Import/export as JSON or Cypher
  - Live sync with project-scoped graph
    - Keep in sync with RDF
  - Show changes before commit (diff/preview)
  - Basic validation (e.g., required properties, relationship constraints)
  - Maintain memory from user and processes

- Thread Workbench
  - Capture all process tasks, user actions, and system events in a continuous, project-scoped thread
  - Display thread as a chronological, filterable conversation (user, system, LLM)
  - Allow post-processing and annotation of thread items
  - Enable user and LLM interactions directly in the thread (comments, clarifications, follow-ups)
  - Support exporting thread for audit or further analysis
  - Create Artifacts like white-papers from this thread by asking the llm for review and write.

- LLM Playground
  - Simple chat
  - "Generate artifact" (e.g., white paper) saved to project
  - Show in tree under Artifacts

- Context Workbench
  - Personas/prompts UI (rehost existing endpoints)

- Uncertainty Workbench
  - Probabilistic extraction settings/preview (placeholder acceptable for MVP)

- Admin
  - Basic users/projects list (read-only initially)
  - Plan persistence beyond in-memory

- Status bar
  - Live service checks (Camunda/Fuseki/Vector) wired to existing endpoints

- Project scoping
  - Pass `project_id` through file/extraction endpoints
  - Enforce scoping on backend

## Suggested next 5 tasks (to hit MVP)
1. Ontology editor in Ontology Workbench with load/save to Fuseki and layout persistence.
2. Files Workbench: upload/list Requirements and Knowledge; embed Knowledge to vector store; update tree live.
3. Requirements Workbench: review using RAG (retrieve Knowledge), confirm/save structured requirements.
4. Conceptualization loop (single pass): given extracted requirements, create RDF individuals + relations and mirror to Neo4j; show review summary.
5. Playground: interactions area with context selectors (Requirements/Knowledge/Ontology); actions to add/link individuals; seed artifacts.

## Notes
- Keep changes small, review diffs before commit.
- Prioritize project scoping and minimal persistence paths during MVP.
