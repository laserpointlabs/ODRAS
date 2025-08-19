# TODO – UI Restart (MVP Refresh)

This document tracks the MVP-critical tasks for the UI restart. We will not commit changes until explicitly approved.

## Covered
- Layout/navigation: top/bottom toolbars, left icon bar, resizable tree
- Projects/auth (MVP): in-memory login, project create/select, project-scoped tree
- Graph DB: Graph Explorer with SPARQL summary and ad‑hoc queries

## Missing for MVP
- Ontology Workbench
  - Inline JSON editor
  - "Push to Fuseki" (per project)
  - Basic validation

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
1. Ontology editor in Ontology Workbench with "Push to Fuseki".
2. Files Workbench: upload/list with "document type" toggle; update tree live.
3. Requirements Workbench: hook to existing review flow (start, poll, edit/approve).
4. Status bar: wire live checks to existing status APIs.
5. Playground: button to create/save a "White Paper" artifact and reflect in tree.

## Notes
- Keep changes small, review diffs before commit.
- Prioritize project scoping and minimal persistence paths during MVP.
