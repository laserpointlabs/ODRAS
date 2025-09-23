## Ontology Workbench: State & Persistence<br>
<br>
This document describes how the Ontology Workbench manages UI state and persistence across refreshes and project switches. It focuses on what is stored, when it is updated, and how it is restored to keep the canvas, ontology tree, and properties panel in sync.<br>
<br>
### Scope and Principles<br>
- Each user works within a selected project. All ontology UI state is scoped per project.<br>
- Graphs (ontologies) are identified by their IRI. A project can have multiple IRIs.<br>
- We persist only the base graph nodes/edges locally; imported overlays are reconstructed dynamically.<br>
- On selection or refresh, we restore the saved graph first, then update UI panels. Autosave is suspended during restore to avoid clobbering drafts.<br>
<br>
### Local Storage Keys<br>
<br>
- Project-scoped selection<br>
  - `onto_active_iri__{projectId}`: Last active ontology IRI for the project.<br>
  - `onto_model_name__{projectId}`: Display label for the active ontology (used in properties panel).<br>
  - `onto_model_attrs__{projectId}`: JSON object of model-level attributes (includes `displayLabel`, `graphIri`).<br>
  - `onto_label_map__{projectId}`: Map of graphIRI → label. Mirrors server labels and local edits.<br>
<br>
- Graph content (per project + graph)<br>
  - `onto_graph__{projectId}__{encodeURIComponent(graphIri)}`: JSON payload `{ nodes, edges }` for base graph only. Each node includes `{ data, position }`; edges include `{ data }`.<br>
<br>
- Imports & overlay positions (per base graph)<br>
  - `onto_imports__{encodeURIComponent(baseGraphIri)}`: Array of imported graph IRIs marked visible.<br>
  - `onto_overlay_pos__{encodeURIComponent(baseGraphIri)}__{encodeURIComponent(importGraphIri)}`: Map of elementId → position used to restore imported overlay node positions.<br>
<br>
- UI layout<br>
  - `ui_main_tree_w`: Left main tree width (px)<br>
  - `onto_tree_w`: Ontology left tree width (px)<br>
  - `onto_props_w`: Ontology right properties width (px)<br>
  - `onto_tree_collapsed`: "1" when left ontology panel is collapsed<br>
  - `onto_props_collapsed`: "1" when right properties panel is collapsed<br>
  - `active_project_id`: Currently selected project id in the header selector<br>
<br>
### Persist Operations (When We Save)<br>
<br>
- Autosave on canvas edits: `add`, `remove`, `data`, `position` events write the base graph to `onto_graph__{projectId}__{graphIri}` (debounced).<br>
- Explicit UI actions also trigger save:<br>
  - Adding class/data/note nodes, connecting nodes, deleting selection, or changing properties.<br>
  - Switching ontologies saves the previous ontology before loading the next.<br>
  - Before page unload we attempt a final save for the active ontology.<br>
- We do not persist imported overlays to the base graph. Overlays store only positions via the `onto_overlay_pos__...` key.<br>
<br>
### Restore Operations (When We Load)<br>
<br>
On login/refresh:<br>
1) Initialize Cytoscape immediately so the canvas exists before restoration.<br>
2) Load projects; `renderTree(selectedProject)` runs.<br>
3) In `renderTree`:<br>
   - Read `onto_active_iri__{projectId}`; if present, set `activeOntologyIri` and update the graph label.<br>
   - Temporarily set `ontoState.suspendAutosave = true`, clear the canvas, and load `onto_graph__{projectId}__{graphIri}`.<br>
   - Re-enable autosave after a short delay to avoid saving an empty graph mid-restore.<br>
   - Select the ontology node in the main tree to synchronize the properties panel and ontology tree labels.<br>
<br>
On ontology selection (from main tree):<br>
1) Save the previous ontology to local storage.<br>
2) Update `onto_active_iri__{projectId}`, `onto_model_name__{projectId}`, and `onto_model_attrs__{projectId}` for the new selection.<br>
3) Suspend autosave, clear the canvas, load graph from local storage, then re-enable autosave.<br>
4) Refresh the ontology tree and properties panel.<br>
<br>
On imports toggle:<br>
- Overlay nodes/edges (with class `imported`) are added/removed dynamically based on `onto_imports__{baseGraphIri}`.<br>
- Overlay node positions are restored from `onto_overlay_pos__{baseGraphIri}__{importGraphIri}` when overlays are shown.<br>
- Overlays are not saved into `onto_graph__...` and do not affect base graph persistence.<br>
<br>
### Canvas Content Rules<br>
<br>
- Base graph elements are those without the `imported` class:<br>
  - Nodes: `(n) => !n.hasClass('imported')`<br>
  - Edges: `(e) => !e.hasClass('imported')`<br>
- Imported overlays (for visualization only) carry `imported` and may also have `imported-equivalence` for `owl:equivalentClass` visuals.<br>
- The tree view lists:<br>
  - Classes: visible base class nodes<br>
  - Notes: visible base note nodes<br>
<br>
### Error Prevention<br>
<br>
- Unsupported Cytoscape selectors are avoided. We use collection filters instead of `:not(...)` or `:visible` pseudo-selectors.<br>
- During restore, `ontoState.suspendAutosave` prevents an empty/transition state from overwriting the saved graph.<br>
- Legacy global `onto_active_iri` is not used. Selection is strictly per project.<br>
<br>
### Server Integration<br>
<br>
- Ontology discovery and labels come from `/api/ontologies?project={projectId}`. Server labels are written into the per-project `onto_label_map__{projectId}`.<br>
- Saving to Fuseki is explicit via `/api/ontology/save?graph={graphIri}`; local drafts remain client-side until saved.<br>
<br>
### Quick Reference<br>
<br>
- Save: on edits, selection change, delete, and beforeunload<br>
- Restore: at login/refresh via renderTree; at selection via handleTreeSelection<br>
- Keys: `onto_active_iri__{pid}`, `onto_graph__{pid}__{iri}`, `onto_label_map__{pid}`, `onto_model_*__{pid}`, imports + overlay positions<br>
<br>
This approach keeps drafts fast and local, isolates state per project and ontology, and avoids accidental data loss during navigation or refresh.<br>
<br>
<br>

