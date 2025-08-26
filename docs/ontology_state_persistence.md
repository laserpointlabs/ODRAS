## Ontology Workbench: State & Persistence

This document describes how the Ontology Workbench manages UI state and persistence across refreshes and project switches. It focuses on what is stored, when it is updated, and how it is restored to keep the canvas, ontology tree, and properties panel in sync.

### Scope and Principles
- Each user works within a selected project. All ontology UI state is scoped per project.
- Graphs (ontologies) are identified by their IRI. A project can have multiple IRIs.
- We persist only the base graph nodes/edges locally; imported overlays are reconstructed dynamically.
- On selection or refresh, we restore the saved graph first, then update UI panels. Autosave is suspended during restore to avoid clobbering drafts.

### Local Storage Keys

- Project-scoped selection
  - `onto_active_iri__{projectId}`: Last active ontology IRI for the project.
  - `onto_model_name__{projectId}`: Display label for the active ontology (used in properties panel).
  - `onto_model_attrs__{projectId}`: JSON object of model-level attributes (includes `displayLabel`, `graphIri`).
  - `onto_label_map__{projectId}`: Map of graphIRI → label. Mirrors server labels and local edits.

- Graph content (per project + graph)
  - `onto_graph__{projectId}__{encodeURIComponent(graphIri)}`: JSON payload `{ nodes, edges }` for base graph only. Each node includes `{ data, position }`; edges include `{ data }`.

- Imports & overlay positions (per base graph)
  - `onto_imports__{encodeURIComponent(baseGraphIri)}`: Array of imported graph IRIs marked visible.
  - `onto_overlay_pos__{encodeURIComponent(baseGraphIri)}__{encodeURIComponent(importGraphIri)}`: Map of elementId → position used to restore imported overlay node positions.

- UI layout
  - `ui_main_tree_w`: Left main tree width (px)
  - `onto_tree_w`: Ontology left tree width (px)
  - `onto_props_w`: Ontology right properties width (px)
  - `onto_tree_collapsed`: "1" when left ontology panel is collapsed
  - `onto_props_collapsed`: "1" when right properties panel is collapsed
  - `active_project_id`: Currently selected project id in the header selector

### Persist Operations (When We Save)

- Autosave on canvas edits: `add`, `remove`, `data`, `position` events write the base graph to `onto_graph__{projectId}__{graphIri}` (debounced).
- Explicit UI actions also trigger save:
  - Adding class/data/note nodes, connecting nodes, deleting selection, or changing properties.
  - Switching ontologies saves the previous ontology before loading the next.
  - Before page unload we attempt a final save for the active ontology.
- We do not persist imported overlays to the base graph. Overlays store only positions via the `onto_overlay_pos__...` key.

### Restore Operations (When We Load)

On login/refresh:
1) Initialize Cytoscape immediately so the canvas exists before restoration.
2) Load projects; `renderTree(selectedProject)` runs.
3) In `renderTree`:
   - Read `onto_active_iri__{projectId}`; if present, set `activeOntologyIri` and update the graph label.
   - Temporarily set `ontoState.suspendAutosave = true`, clear the canvas, and load `onto_graph__{projectId}__{graphIri}`.
   - Re-enable autosave after a short delay to avoid saving an empty graph mid-restore.
   - Select the ontology node in the main tree to synchronize the properties panel and ontology tree labels.

On ontology selection (from main tree):
1) Save the previous ontology to local storage.
2) Update `onto_active_iri__{projectId}`, `onto_model_name__{projectId}`, and `onto_model_attrs__{projectId}` for the new selection.
3) Suspend autosave, clear the canvas, load graph from local storage, then re-enable autosave.
4) Refresh the ontology tree and properties panel.

On imports toggle:
- Overlay nodes/edges (with class `imported`) are added/removed dynamically based on `onto_imports__{baseGraphIri}`.
- Overlay node positions are restored from `onto_overlay_pos__{baseGraphIri}__{importGraphIri}` when overlays are shown.
- Overlays are not saved into `onto_graph__...` and do not affect base graph persistence.

### Canvas Content Rules

- Base graph elements are those without the `imported` class:
  - Nodes: `(n) => !n.hasClass('imported')`
  - Edges: `(e) => !e.hasClass('imported')`
- Imported overlays (for visualization only) carry `imported` and may also have `imported-equivalence` for `owl:equivalentClass` visuals.
- The tree view lists:
  - Classes: visible base class nodes
  - Notes: visible base note nodes

### Error Prevention

- Unsupported Cytoscape selectors are avoided. We use collection filters instead of `:not(...)` or `:visible` pseudo-selectors.
- During restore, `ontoState.suspendAutosave` prevents an empty/transition state from overwriting the saved graph.
- Legacy global `onto_active_iri` is not used. Selection is strictly per project.

### Server Integration

- Ontology discovery and labels come from `/api/ontologies?project={projectId}`. Server labels are written into the per-project `onto_label_map__{projectId}`.
- Saving to Fuseki is explicit via `/api/ontology/save?graph={graphIri}`; local drafts remain client-side until saved.

### Quick Reference

- Save: on edits, selection change, delete, and beforeunload
- Restore: at login/refresh via renderTree; at selection via handleTreeSelection
- Keys: `onto_active_iri__{pid}`, `onto_graph__{pid}__{iri}`, `onto_label_map__{pid}`, `onto_model_*__{pid}`, imports + overlay positions

This approach keeps drafts fast and local, isolates state per project and ontology, and avoids accidental data loss during navigation or refresh.


