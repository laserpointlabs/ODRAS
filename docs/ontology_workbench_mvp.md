# Ontology Workbench MVP<br>
<br>
This document outlines a minimal, robust plan for an ontology workbench that follows ontological best practices while keeping the user experience simple for an MVP.<br>
<br>
## Goals and scope (MVP)<br>
- Edit a single base ontology at a time (ignore external upper ontologies for now).<br>
- Source of truth in Fuseki (named graph per ontology).<br>
- Visual editing in a browser (tree + canvas + properties), then save back to Fuseki.<br>
- Store diagram layout separately from OWL/RDF triples.<br>
- Keep imports/read-only overlays for a later iteration.<br>
<br>
## High-level architecture<br>
```mermaid<br>
graph TD<br>
  U["User"] --> UI["Browser: Ontology Workbench\n(Tree | Canvas | Properties)"]<br>
  UI --> API["API Server"]<br>
  API --> F["Fuseki (SPARQL)"]<br>
  API --> L["Layout Store (JSON)"]<br>
```<br>
<br>
- Fuseki: stores ontology triples. One named graph per editable ontology (e.g., GRAPH <http://odras.local/onto/my-ontology>).<br>
- Layout Store: stores UI-only layout JSON (node positions, zoom/pan). For MVP, a simple REST endpoint; can be backed by Fuseki in a separate layout graph or a file store.<br>
- Workbench UI:<br>
  - Tree shows classes/properties for the active ontology only.<br>
  - Canvas presents nodes/edges derived from ontology.<br>
  - Properties panel edits labels, domains/ranges, types, etc.<br>
<br>
## Data model<br>
- Ontology triples (RDF/OWL) in Fuseki named graph: GRAPH <baseOntologyIRI> { … }.<br>
  - owl:Class (or rdfs:Class)<br>
  - owl:ObjectProperty<br>
  - owl:DatatypeProperty<br>
  - rdfs:label, rdfs:domain, rdfs:range<br>
- Layout JSON (separate from ontology):<br>
```json<br>
{<br>
  "graphIri": "http://odras.local/onto/my-ontology",<br>
  "nodes": [<br>
    { "iri": "http://odras.local/onto/my-ontology#Order", "x": 320, "y": 180 },<br>
    { "iri": "http://odras.local/onto/my-ontology#Customer", "x": 120, "y": 220 }<br>
  ],<br>
  "edges": [<br>
    { "iri": "http://odras.local/onto/my-ontology#placedBy" }<br>
  ],<br>
  "zoom": 1.0,<br>
  "pan": { "x": 0, "y": 0 }<br>
}<br>
```<br>
<br>
Rationale: never mingle UI-only layout into the ontology graph; keep separation of concerns and enable clean SPARQL operations on the ontology.<br>
<br>
## Loading flow<br>
```mermaid<br>
sequenceDiagram<br>
  participant U as User<br>
  participant UI as Workbench UI<br>
  participant API as API<br>
  participant F as Fuseki<br>
  participant L as Layout Store<br>
<br>
  U->>UI: Select ontology in main tree<br>
  UI->>API: GET /ontology?graph=<iri><br>
  API->>F: SPARQL CONSTRUCT GRAPH <iri><br>
  F-->>API: RDF triples (Turtle/JSON-LD)<br>
  API-->>UI: Triples<br>
  UI->>API: GET /layout?graph=<iri><br>
  API-->>UI: Layout JSON (or 404)<br>
  UI->>UI: Render tree+canvas (auto-layout if no layout)<br>
```<br>
<br>
## Editing model (MVP)<br>
- One active ontology loaded (base ontology only). Imports postponed for simplicity.<br>
- Visual mapping:<br>
  - Node: owl:Class<br>
  - Edge: owl:ObjectProperty (label = rdfs:label or local name)<br>
  - Data property: either as an edge annotation or a node+edge to the class (MVP can render a small node labeled with the property and an edge from the class)<br>
- Properties panel edits:<br>
  - Class: rdfs:label (and optionally rdfs:subClassOf)<br>
  - Object property: rdfs:label, rdfs:domain, rdfs:range<br>
  - Data property: rdfs:label, rdfs:domain, rdfs:range (to a literal type later)<br>
- IRI minting: generate in the base namespace (e.g., <http://odras.local/onto/{project}#Name>) and ensure uniqueness.<br>
<br>
## Interaction and editing UX (no popups)<br>
Design for direct manipulation and uninterrupted flow. Avoid modal prompts/popups for core creation and editing actions.<br>
<br>
- Creation (no popups):<br>
  - Drag from palette to canvas to create a class or data property. Node appears under cursor; immediately selected.<br>
  - Connect classes using edge-handles to create an object property. Edge appears; its label is editable in place.<br>
- In-place rename (nodes/edges):<br>
  - Click (or F2/double-click) on a node label or edge label to enter inline edit mode.<br>
  - Show a small inline text input aligned with the label. Commit: Enter/blur. Cancel: Escape.<br>
  - Update rdfs:label and regenerate local names (optional) while preserving IRIs (or propose IRI remap with confirmation later).<br>
- Selection and deletion:<br>
  - Click to select; Shift-click to multi-select; marquee select via drag on empty canvas (optional later).<br>
  - Delete/Backspace to remove selected elements. No confirmation modal; provide Undo.<br>
- Properties panel (non-modal):<br>
  - Selecting any element populates the properties panel for structured edits (domain/range, types, custom attributes). Inline edits and panel edits stay in sync.<br>
- Keyboard shortcuts (MVP set):<br>
  - Delete/Backspace: delete selection<br>
  - Ctrl/Cmd+S: Save ontology + layout<br>
  - Ctrl/Cmd+Z / Ctrl/Cmd+Shift+Z: Undo/Redo (at least recent operations in-memory)<br>
  - Esc: cancel inline edit; clear selection if not editing<br>
- Direct manipulation:<br>
  - Drag nodes to reposition (no prompts). Snap-to-grid optional.<br>
  - Pan with space+drag or middle mouse; zoom with wheel (with Ctrl/Cmd).<br>
  - Auto-layout button for quick arrangement; preserves manual positions unless re-run.<br>
- Feedback and affordances:<br>
  - Hover hints/tooltips are fine; avoid blocking modals.<br>
  - Dirty indicator (unsaved changes) in toolbar; guard on navigation.<br>
<br>
Rationale: Direct, inline editing minimizes cognitive load and respects Fitts’s Law; keyboard support is expected in editors; Undo is safer than confirmation modals.<br>
<br>
## Conceptualization loop (single pass MVP)<br>
Populate the ontology with candidate individuals per requirement, and mirror into a property graph.<br>
<br>
```mermaid<br>
sequenceDiagram<br>
  participant UI as Workbench UI<br>
  participant API as API<br>
  participant V as Vector Store<br>
  participant LLM as LLM<br>
  participant F as Fuseki (RDF)<br>
  participant N as Neo4j (Property Graph)<br>
<br>
  UI->>API: Start conceptualization (project, baseOntologyIRI)<br>
  API->>F: Get extracted requirements (RDF or JSON)<br>
  API->>V: Retrieve relevant knowledge chunks per requirement<br>
  API->>LLM: Prompt(requirement + retrieved knowledge + ontology schema)<br>
  LLM-->>API: Candidate individuals + relations (+confidence)<br>
  API->>F: Upsert individuals (owl:NamedIndividual) and object/data properties<br>
  API->>N: Upsert nodes/edges (mirror): labels/types/props; link to requirement<br>
  API-->>UI: Summary (created/updated, warnings, confidences)<br>
```<br>
<br>
Data conventions (MVP):<br>
- Each requirement R becomes/links to an RDF node (e.g., `odras:Requirement` with IRI `...#R-001`).<br>
- For each candidate entity E: create `E` as `owl:NamedIndividual` of a base class (e.g., `:Component`, `:Process`), with<br>
  - `rdfs:label` (from LLM), optional `odras:confidence` (xsd:decimal), `odras:derivedFrom` -> requirement IRI.<br>
  - Relations between new/existing individuals via base object properties.<br>
- Property-graph mirror (Neo4j): node keys = RDF IRI; node label = class local name; edge type = object property local name; properties include `label`, `confidence`, `requirementId`.<br>
- Idempotent upsert by IRI; never duplicate individuals if IRIs match.<br>
<br>
Notes:<br>
- Keep the loop single-pass (no iterative refinement) for MVP; show a review summary with confidences.<br>
- Do not modify imported ontologies; only instantiate in the active base ontology graph.<br>
<br>
## Requirements and knowledge ingestion (RAG)<br>
Process both Requirements and Knowledge documents; use Knowledge as a priori context during review.<br>
<br>
Pipeline (MVP):<br>
- Parse & chunk (pdf/docx/md): preserve source, project, section headers.<br>
- Embed to vector store with metadata: { projectId, docType: requirements|knowledge, docId, section, page }.<br>
- During requirement review and conceptualization, retrieve K relevant knowledge chunks; inject into prompts with citations.<br>
- Persist extracted requirements as structured items and optionally as RDF (e.g., `odras:Requirement`).<br>
<br>
Prompts should:<br>
- Include ontology schema summary (classes/properties) and any key value lists.<br>
- Include top-k knowledge chunks (with citation ids) and the requirement text.<br>
- Ask for typed individuals, relations, confidences, and clear failure modes (unknown/needs SME).<br>
<br>
## LLM Playground – interactions area (context-first)<br>
Support exploration with project context before creating artifacts (white paper, concept architecture, gap analysis).<br>
<br>
Features (MVP):<br>
- Context selectors: Requirements (pick subset), Knowledge (scoped filters), Ontology (classes/individuals).<br>
- Chat transcript with citations; ability to pin relevant messages.<br>
- Actions: “Add as individual” (creates RDF individual), “Link to requirement”, “Save snippet to Knowledge”.<br>
- Artifact seeds: collect pinned messages into a draft; persist as project artifact.<br>
<br>
Non-goals (MVP):<br>
- Full workflow orchestration; we’ll keep a simple chat + actions.<br>
<br>
## Integration readiness (BPMN/DAS awareness)<br>
- Provide an API hook to trigger conceptualization and to report results (future BPMN task integration).<br>
- Emit lightweight events (started/completed) with counts and warnings for testing.<br>
- Keep module boundaries: ingestion, review (LLM+RAG), conceptualization writer (RDF+Neo4j), UI.<br>
<br>
## Save flow<br>
```mermaid<br>
sequenceDiagram<br>
  participant UI as Workbench UI<br>
  participant API as API<br>
  participant F as Fuseki<br>
  participant L as Layout Store<br>
<br>
  UI->>API: PUT /ontology?graph=<iri> (triples)<br>
  API->>F: SPARQL UPDATE (DROP GRAPH <iri>; INSERT DATA { GRAPH <iri> { ... } })<br>
  F-->>API: 200 OK<br>
  UI->>API: PUT /layout?graph=<iri> (layout JSON)<br>
  L-->>API: 200 OK<br>
```<br>
<br>
### Minimal SPARQL<br>
- Load:<br>
```sparql<br>
CONSTRUCT { ?s ?p ?o }<br>
WHERE { GRAPH <http://odras.local/onto/my-ontology> { ?s ?p ?o } }<br>
```<br>
- Save (simple replacement):<br>
```sparql<br>
DROP GRAPH <http://odras.local/onto/my-ontology> ;<br>
INSERT DATA {<br>
  GRAPH <http://odras.local/onto/my-ontology> {<br>
    # … serialized triples (Turtle) …<br>
  }<br>
}<br>
```<br>
<br>
Notes: For MVP, full replacement is acceptable. Later, adopt diff-based updates or versioning.<br>
<br>
## Imports (later iteration)<br>
- Represent imports as separate named graphs; load as read-only overlays.<br>
- Toggle visibility on canvas; distinct style.<br>
- Edits only affect the base graph; never merge imported triples into the base.<br>
<br>
## UI/UX best practices<br>
- Single-edit context: one active base ontology at a time.<br>
- Three synchronized panels:<br>
  - Tree: classes (and optionally properties) of the active base ontology only.<br>
  - Canvas: graph view with direct manipulation (add class, connect, delete, auto-layout).<br>
  - Properties: edit selected class/property; show model-level metadata when background is selected.<br>
- Clear save semantics: Save writes both triples and layout; Revert reloads from Fuseki and layout store.<br>
- Dirty indicator and navigation guard when unsaved changes exist.<br>
<br>
## Validation & safety (MVP)<br>
- Ensure unique IRIs upon create/rename.<br>
- Basic integrity checks: object property must have domain and range set before save (or warn and allow save with TODO markers).<br>
- Optionally, run SHACL validation later.<br>
<br>
## Versioning (later)<br>
- Option A: write to GRAPH <iri>/<timestamp> and update a pointer triple to “current”.<br>
- Option B: store versions in a companion metadata graph.<br>
<br>
## API sketch<br>
- GET /ontology?graph=<iri> → 200 { triples: Turtle/JSON-LD }<br>
- PUT /ontology?graph=<iri> (body: Turtle/JSON-LD) → 200<br>
- GET /layout?graph=<iri> → 200 JSON or 404<br>
- PUT /layout?graph=<iri> (body: JSON) → 200<br>
<br>
## Ontology discovery & registry (MVP)<br>
Source the main ontology tree from Fuseki, not placeholders.<br>
<br>
- Discovery (baseline): list named graphs that contain an `owl:Ontology` declaration.<br>
- Registry (recommended): maintain a small metadata graph to categorize Base vs Imports.<br>
<br>
Discovery query:<br>
```sparql<br>
SELECT DISTINCT ?graph ?ontology ?label WHERE {<br>
  GRAPH ?graph {<br>
    ?ontology a owl:Ontology .<br>
    OPTIONAL { ?ontology rdfs:label ?label }<br>
  }<br>
}<br>
```<br>
<br>
Fallback (any non-empty named graph):<br>
```sparql<br>
SELECT DISTINCT ?graph WHERE { GRAPH ?graph { ?s ?p ?o } }<br>
```<br>
<br>
Registry graph (example): `GRAPH <http://odras.local/meta/ontologies>`<br>
```turtle<br>
@prefix odras: <http://odras.local/ns#> .<br>
<br>
[] odras:graphIri <http://odras.local/onto/{project}/systems> ;<br>
   odras:projectId "{project}" ;<br>
   odras:role "base" ;              # base | import<br>
   odras:label "Systems Ontology" .<br>
```<br>
<br>
New endpoints:<br>
- GET /ontologies?project=<id> → 200 [{ graphIri, label, role: base|import|unknown, tripleCount? }]<br>
- PUT /ontologies/registry (body: entries) → 200 (set base/import per project)<br>
<br>
## Implementation checklist<br>
- Load active base ontology from the main tree into the workbench.<br>
- Map triples → elements (classes → nodes, object properties → edges, data properties → small nodes/edges).<br>
- Serialize elements → triples on save.<br>
- Persist and load layout JSON per ontology IRI.<br>
- Enforce IRI minting and label editing.<br>
- Postpone imports; keep UI hooks for future read-only overlays.<br>
 - Inline rename for nodes/edges (click/F2 → input → Enter/Esc).<br>
 - Edge creation via drag handles; label editable in place (no prompts).<br>
 - Keyboard: Delete removes selection; Ctrl/Cmd+S saves; basic Undo/Redo in-memory.<br>
 - Palette drag-and-drop creation; immediate selection; no popups.<br>
 - Keep editing non-modal; use properties panel for structured fields (domain/range).<br>
<br>
## Why this is simple and safe (MVP)<br>
- Clear separation: ontology vs. layout.<br>
- Easy rollback: re-load from Fuseki.<br>
- Minimal surface area: one ontology at a time; no heavy import logic yet.<br>
- Straightforward API contract and SPARQL operations.<br>
<br>
## MVP TODO checklist (Ontology Workbench) - ✅ COMPLETED<br>
<br>
- [x] OW-0: Wire workbench route and selection<br>
  - [x] Create `Ontology Workbench` route/page and mount under the existing layout<br>
  - [x] Read the active ontology IRI from the project-scoped tree/selection<br>
  - [x] Show empty state with selected IRI<br>
<br>
- [x] OW-0.5: Ontology discovery and registry<br>
  - [x] API: GET `/ontologies?project=<id>` lists named graphs with `owl:Ontology` (+label)<br>
  - [x] API: registry support for tagging `role=base|import|reference`<br>
  - [x] UI: populate main ontology tree from discovery results<br>
  - [x] UI: allow selecting base ontology and imports from discovered list<br>
  - [x] Persist selection per project<br>
<br>
- [x] OW-1: API contracts and adapters<br>
  - [x] Implement `GET /ontology?graph=<iri>` (SPARQL CONSTRUCT passthrough)<br>
  - [x] Implement `PUT /ontology?graph=<iri>` (DROP+INSERT DATA)<br>
  - [x] Implement `GET/PUT /layout?graph=<iri>` (JSON store with server persistence)<br>
  - [x] Create authenticated fetch wrapper with error handling<br>
<br>
- [x] OW-2: RDF parsing and mapping<br>
  - [x] Parse API JSON into in-memory model for classes, object props, datatype props<br>
  - [x] Map classes → nodes; object props → edges; data props → nodes with edges<br>
  - [x] Derive display labels from `rdfs:label` or local name fallback<br>
  - [x] Rich metadata support with SPARQL queries<br>
<br>
- [x] OW-3: Canvas (Cytoscape) baseline<br>
  - [x] Initialize Cytoscape with comprehensive styles and layouts<br>
  - [x] Render nodes/edges from mapped ontology model<br>
  - [x] Support pan/zoom; fit-to-view; multiple auto-layout algorithms<br>
<br>
- [x] OW-4: Layout persistence<br>
  - [x] On load: fetch layout JSON; apply positions/zoom/pan; fallback to auto-layout<br>
  - [x] On save: persist node positions + zoom/pan via server API<br>
  - [x] Local storage caching with server synchronization<br>
<br>
- [x] OW-5: Direct manipulation editing<br>
  - [x] Palette: drag-to-create Class, Data Property, and Notes<br>
  - [x] Edge handles: connect classes to create Object Properties<br>
  - [x] Inline rename: double-click/F2 to edit labels and predicates<br>
  - [x] Keyboard: Delete removes selection; comprehensive shortcuts<br>
  - [x] Drag to reposition; selection with visual feedback<br>
<br>
- [x] OW-6: Properties panel<br>
  - [x] Bind selection to panel; edit labels, attributes, and metadata<br>
  - [x] Template-based attribute editing for different object types<br>
  - [x] Inline edits and panel fields stay synchronized<br>
  - [x] Model metadata display when no selection<br>
<br>
- [x] OW-7: IRI minting and validation<br>
  - [x] Generate IRIs in base namespace with proper URI structure<br>
  - [x] Preserve original IRIs for imported elements<br>
  - [x] IRI display with ownership attribution<br>
<br>
- [x] OW-8: Serialization and save flow<br>
  - [x] Serialize UI model → RDF triples (Turtle format)<br>
  - [x] Save: Backend persistence to Fuseki<br>
  - [x] Save layout JSON with server synchronization<br>
  - [x] Auto-save functionality with debouncing<br>
<br>
- [x] OW-9: UX polish and advanced features<br>
  - [x] Professional context menus with SVG icons<br>
  - [x] Comprehensive visibility controls (global and individual)<br>
  - [x] Error handling and user feedback<br>
  - [x] Accessibility support with keyboard navigation<br>
<br>
- [x] OW-10: Import management and collaboration<br>
  - [x] External ontology import from URLs<br>
  - [x] Reference ontology library with admin management<br>
  - [x] Import visualization with read-only protection<br>
  - [x] Layout persistence for imported elements<br>
  - [x] Proper IRI ownership display for imports<br>
<br>
- [x] OW-0.6: Enhanced ontology functionality<br>
  - [x] API: Full CRUD operations for ontologies<br>
  - [x] UI: Comprehensive tree interactions<br>
  - [x] UI: Advanced canvas interactions with metadata tracking<br>
  - [x] Local persistence with server synchronization<br>
  - [x] Complete save & layout functionality<br>
<br>
## ✅ COMPLETED MVP FEATURES<br>
<br>
### Core Ontology Management<br>
- [x] **Ontology Creation/Deletion/Renaming** - Full CRUD operations<br>
- [x] **Project-Scoped Organization** - Ontologies organized by project<br>
- [x] **Rich Metadata Tracking** - Creator, creation/modification dates for all objects<br>
- [x] **Professional UI** - Clean, accessible interface with proper navigation<br>
<br>
### Visual Ontology Editor<br>
- [x] **Cytoscape Canvas** - Professional graph visualization with multiple layouts<br>
- [x] **Direct Manipulation** - Drag-to-create, inline editing, visual connections<br>
- [x] **Properties Panel** - Template-based attribute editing with validation<br>
- [x] **Layout Persistence** - Server-synchronized position and zoom state<br>
<br>
### Advanced Features<br>
- [x] **Import Management** - External ontology imports with read-only protection<br>
- [x] **Visibility Controls** - Global and individual element show/hide<br>
- [x] **Named Views** - Save and restore complete canvas configurations<br>
- [x] **Note System** - 7 note types with visual indicators and metadata<br>
- [x] **Tree-Canvas Synchronization** - Bi-directional selection between tree and canvas<br>
<br>
### Import and Collaboration<br>
- [x] **External Imports** - URL-based ontology import with validation<br>
- [x] **Reference Ontologies** - Admin-managed ontology library<br>
- [x] **Import Visualization** - Proper attribution and visual distinction<br>
- [x] **Layout Retention** - Imported element positions persist across sessions<br>
<br>
### Acceptance criteria (MVP)<br>
- Load/render from a Fuseki named graph and apply stored layout (or auto-layout if absent).<br>
- Create classes, datatype/object properties via direct manipulation; rename inline.<br>
- Edit labels/domain/range/types in the properties panel; changes reflect immediately.<br>
- Save writes both triples (DROP+INSERT) and layout JSON; reload reproduces the view.<br>
- IRI minting uses base namespace and guarantees uniqueness; integrity warnings shown.<br>
- Keyboard shortcuts work; undo/redo available for recent steps; dirty indicator present.<br>

