<!-- cca7a6a1-193f-4c2b-b7c5-a04e28824b4d 3789b1e5-5cd5-4bbb-86f1-bed3919cdf48 -->
# Ontology Workbench Modularization Plan

## Goal

Transform the ontology workbench into a highly modular, product-grade component that can function independently while maintaining clean integration with ODRAS through well-defined interfaces.

## Current State Analysis

### Current File Structure

- `frontend/js/workbenches/ontology/ontology-ui.js` (~1523 lines) - Monolithic implementation
- Multiple backup/broken versions cluttering directory
- Dependencies: `apiClient`, `getAppState`, `event-bus`, `ontology-ui-structure.js`

### Current Dependencies on ODRAS Core

- `apiClient` from `core/api-client.js` - HTTP requests
- `getAppState/updateAppState` from `core/state-manager.js` - Application state
- `subscribeToEvent/emitEvent` from `core/event-bus.js` - Event communication
- Direct DOM manipulation and global state

## Target Architecture

### Directory Structure

```
frontend/js/workbenches/ontology/
├── index.js                          # Main entry point & public API
├── ontology-ui-structure.js          # HTML structure (existing)
│
├── core/
│   ├── cytoscape-init.js            # Cytoscape initialization (~600 lines)
│   ├── state-manager.js             # Internal state management (~200 lines)
│   └── event-handlers.js            # Global event handlers (~300 lines)
│
├── graph/
│   ├── graph-loader.js              # loadGraphFromLocalOrAPI (~200 lines)
│   ├── graph-converter.js           # convertOntologyToCytoscape (~300 lines)
│   ├── graph-persistence.js         # Local storage functions (~200 lines)
│   └── metadata-fetcher.js          # fetchRichMetadata (~200 lines)
│
├── canvas/
│   ├── canvas-operations.js         # addClassNode, delete, etc. (~300 lines)
│   ├── drag-drop.js                 # Drag-and-drop handlers (~200 lines)
│   ├── inline-editor.js             # Inline label editor (~150 lines)
│   └── selection-handler.js          # Selection management (~150 lines)
│
├── tree/
│   ├── tree-renderer.js             # refreshOntologyTree (~400 lines)
│   └── tree-selection.js            # Tree selection handlers (~200 lines)
│
├── properties/
│   ├── properties-panel.js          # updatePropertiesPanelFromSelection (~400 lines)
│   ├── constraints-editor.js       # SHACL constraints (~300 lines)
│   ├── inheritance-editor.js        # Class inheritance (~200 lines)
│   └── metadata-editor.js           # Attribute editor (~200 lines)
│
├── layout/
│   ├── layout-manager.js            # runAdvancedLayout (~200 lines)
│   └── layout-persistence.js        # Load/save layout (~150 lines)
│
├── menus/
│   ├── context-menu.js              # Context menu handlers (~200 lines)
│   └── edge-menu.js                 # Edge context menu (~150 lines)
│
├── storage/
│   ├── local-storage.js             # All localStorage functions (~300 lines)
│   └── state-persistence.js         # State save/load (~200 lines)
│
├── utils/
│   ├── metadata-helpers.js          # Metadata functions (~150 lines)
│   ├── ui-helpers.js                # UI utility functions (~200 lines)
│   └── rdf-helpers.js               # RDF/Turtle conversion (~300 lines)
│
├── features/
│   ├── imports-manager.js           # Import overlay management (~300 lines)
│   ├── named-views.js               # Named views (~200 lines)
│   ├── undo-redo.js                 # Undo/redo stack (~200 lines)
│   └── export-import.js             # Export/import functions (~400 lines)
│
└── adapters/
    ├── odras-api-adapter.js         # ODRAS API integration layer (~150 lines)
    ├── odras-state-adapter.js       # ODRAS state integration (~100 lines)
    └── odras-events-adapter.js      # ODRAS event integration (~100 lines)
```

## Key Design Principles

### 1. Dependency Inversion

- Core workbench code has NO direct dependencies on ODRAS
- All ODRAS integration through adapter layer
- Adapters implement interfaces that workbench expects

### 2. Product Independence

- Workbench can be tested in isolation
- Clear public API (`index.js`)
- Internal modules are private (not exported)
- Adapters are swappable for different host environments

### 3. Interface-Based Design

```javascript
// Adapter interfaces (defined in adapters/)
interface ApiAdapter {
  get(uri: string): Promise<Response>
  post(uri: string, data: any): Promise<Response>
  put(uri: string, data: any): Promise<Response>
  delete(uri: string): Promise<Response>
}

interface StateAdapter {
  getState(): AppState
  updateState(updates: Partial<AppState>): void
  subscribe(callback: (state: AppState) => void): Unsubscribe
}

interface EventAdapter {
  subscribe(event: string, handler: Function): Unsubscribe
  emit(event: string, data: any): void
}
```

## Implementation Phases

### Phase 1: Create Infrastructure & Adapters

**Goal**: Establish adapter layer and core infrastructure

1. Create directory structure
2. Create `adapters/odras-api-adapter.js` - Wraps `apiClient` with interface
3. Create `adapters/odras-state-adapter.js` - Wraps `getAppState/updateAppState`
4. Create `adapters/odras-events-adapter.js` - Wraps event-bus
5. Create `core/state-manager.js` - Internal state management (isolated from ODRAS)
6. Create `index.js` - Main entry point with dependency injection

**Files Created**: 6 new files

**Files Modified**: None (yet)

### Phase 2: Extract Utilities & Helpers

**Goal**: Extract reusable utilities with no dependencies

1. Extract `utils/metadata-helpers.js` - Pure functions for metadata
2. Extract `utils/ui-helpers.js` - DOM utilities (no ODRAS dependencies)
3. Extract `utils/rdf-helpers.js` - RDF/Turtle conversion (pure functions)

**Files Created**: 3 new files

**Files Modified**: `ontology-ui.js` (remove extracted functions)

### Phase 3: Extract Storage Layer

**Goal**: Isolate storage operations

1. Extract `storage/local-storage.js` - All localStorage operations
2. Extract `storage/state-persistence.js` - State save/load logic
3. Update to use adapter pattern for any ODRAS-specific storage

**Files Created**: 2 new files

**Files Modified**: `ontology-ui.js` (remove storage functions)

### Phase 4: Extract Graph Management

**Goal**: Modularize graph loading and conversion

1. Extract `graph/graph-persistence.js` - Local storage graph functions
2. Extract `graph/graph-converter.js` - Conversion functions
3. Extract `graph/metadata-fetcher.js` - SPARQL metadata fetching
4. Extract `graph/graph-loader.js` - Main loading orchestration
5. Wire through adapters for API calls

**Files Created**: 4 new files

**Files Modified**: `ontology-ui.js` (remove graph functions)

### Phase 5: Extract Canvas Operations

**Goal**: Modularize canvas interactions

1. Extract `canvas/selection-handler.js` - Selection management
2. Extract `canvas/canvas-operations.js` - Add/delete operations
3. Extract `canvas/drag-drop.js` - Drag-and-drop handlers
4. Extract `canvas/inline-editor.js` - Inline editing (F2/double-click)

**Files Created**: 4 new files

**Files Modified**: `ontology-ui.js` (remove canvas functions)

### Phase 6: Extract UI Panels

**Goal**: Modularize tree and properties panels

1. Extract `tree/tree-renderer.js` - Tree panel rendering
2. Extract `tree/tree-selection.js` - Tree selection handlers
3. Extract `properties/properties-panel.js` - Properties panel main
4. Extract `properties/constraints-editor.js` - SHACL constraints
5. Extract `properties/inheritance-editor.js` - Class inheritance
6. Extract `properties/metadata-editor.js` - Attribute editing

**Files Created**: 6 new files

**Files Modified**: `ontology-ui.js` (remove panel functions)

### Phase 7: Extract Layout & Menus

**Goal**: Modularize layout and context menus

1. Extract `layout/layout-manager.js` - Layout algorithms
2. Extract `layout/layout-persistence.js` - Layout save/load
3. Extract `menus/context-menu.js` - Node context menus
4. Extract `menus/edge-menu.js` - Edge context menus

**Files Created**: 4 new files

**Files Modified**: `ontology-ui.js` (remove layout/menu functions)

### Phase 8: Extract Advanced Features

**Goal**: Modularize advanced features

1. Extract `features/imports-manager.js` - Import overlay management
2. Extract `features/named-views.js` - Named views system
3. Extract `features/undo-redo.js` - Undo/redo stack
4. Extract `features/export-import.js` - Export/import functions

**Files Created**: 4 new files

**Files Modified**: `ontology-ui.js` (remove feature functions)

### Phase 9: Extract Core Initialization

**Goal**: Modularize Cytoscape initialization

1. Extract `core/cytoscape-init.js` - Cytoscape setup (~600 lines)
2. Extract `core/event-handlers.js` - Global event handlers
3. Update `index.js` to orchestrate initialization

**Files Created**: 2 new files

**Files Modified**: `ontology-ui.js` (remove initialization, becomes thin wrapper)

### Phase 10: Final Integration & Cleanup

**Goal**: Complete migration and cleanup

1. Update `index.js` to be the main entry point
2. Update `ontology-ui.js` to be a thin compatibility wrapper (or remove)
3. Update `frontend/index.html` to import from `index.js`
4. Remove all backup/broken files
5. Add JSDoc comments to public API
6. Create `README.md` for ontology workbench

**Files Created**: 1 new file (README.md)

**Files Modified**: `ontology-ui.js` (thin wrapper or removal), `frontend/index.html`

## Public API Design

### Main Entry Point (`index.js`)

```javascript
export class OntologyWorkbench {
  constructor(config) {
    // Dependency injection: adapters, container element, etc.
  }
  
  async initialize() { }
  async loadOntology(iri) { }
  async saveOntology() { }
  destroy() { }
  
  // Public events
  on(event, handler) { }
  off(event, handler) { }
}

export function createOntologyWorkbench(config) {
  return new OntologyWorkbench(config);
}
```

### Configuration Interface

```javascript
interface WorkbenchConfig {
  container: HTMLElement
  apiAdapter: ApiAdapter
  stateAdapter: StateAdapter
  eventAdapter: EventAdapter
  options?: {
    autosave?: boolean
    snapToGrid?: boolean
    gridSize?: number
  }
}
```

## Testing Strategy

### Unit Tests

- Each module tested in isolation
- Mock adapters for testing
- Pure functions tested without mocks

### Integration Tests

- Test with real ODRAS adapters
- Test module interactions
- Test public API

### E2E Tests

- Test full workbench initialization
- Test user workflows
- Test ODRAS integration

## Migration Safety

### Backward Compatibility

- Keep `ontology-ui.js` as compatibility wrapper during migration
- Gradual migration - each phase is independently testable
- No breaking changes until final phase

### Rollback Strategy

- Each phase can be rolled back independently
- Git commits per phase
- Keep original file until migration complete

## Success Criteria

1. **Modularity**: Each module < 500 lines, single responsibility
2. **Independence**: Core workbench has zero direct ODRAS dependencies
3. **Testability**: Each module can be tested in isolation
4. **Maintainability**: Clear structure, easy to navigate
5. **Product Quality**: Can function as standalone product with adapters
6. **Performance**: No degradation from modularization
7. **Documentation**: Public API documented, internal modules documented

## File Size Targets

- **Target**: 200-400 lines per file
- **Maximum**: 500 lines per file
- **Exception**: `core/cytoscape-init.js` can be ~600 lines due to Cytoscape config

## Estimated Impact

- **Files Created**: ~35 new modular files
- **Files Removed**: ~6 backup/broken files
- **Files Modified**: `ontology-ui.js` (becomes thin wrapper), `frontend/index.html`
- **Lines of Code**: ~1500 lines reorganized into ~35 modules
- **Dependencies**: Reduced to adapter layer only

### To-dos

- [ ] Phase 1: Create directory structure, adapter layer (API, state, events), core state manager, and main index.js entry point with dependency injection
- [ ] Phase 2: Extract utility modules (metadata-helpers, ui-helpers, rdf-helpers) as pure functions with no dependencies
- [ ] Phase 3: Extract storage layer (local-storage.js, state-persistence.js) and update to use adapter pattern
- [ ] Phase 4: Extract graph management modules (graph-loader, graph-converter, metadata-fetcher, graph-persistence) and wire through adapters
- [ ] Phase 5: Extract canvas operations (selection-handler, canvas-operations, drag-drop, inline-editor)
- [ ] Phase 6: Extract UI panels (tree-renderer, tree-selection, properties-panel, constraints-editor, inheritance-editor, metadata-editor)
- [ ] Phase 7: Extract layout management (layout-manager, layout-persistence) and menus (context-menu, edge-menu)
- [ ] Phase 8: Extract advanced features (imports-manager, named-views, undo-redo, export-import)
- [ ] Phase 9: Extract core initialization (cytoscape-init.js, event-handlers.js) and update index.js orchestration
- [ ] Phase 10: Final integration - update index.js as main entry point, update frontend/index.html, remove backup files, add documentation