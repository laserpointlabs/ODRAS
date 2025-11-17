# Ontology Workbench Architecture Analysis

## Overview

The Ontology Workbench is a complex, feature-rich component that deserves careful architectural planning. This document analyzes its structure and proposes a modular architecture.

## Current State Analysis

### Function Categories (from app.html analysis)

#### 1. **Core Initialization & Setup** (~800 lines)
- `ensureOntologyInitialized()` - Cytoscape initialization with all event handlers
- `setupOntologyEventListeners()` - Global event handlers
- State initialization

#### 2. **Graph Management** (~600 lines)
- `loadGraphFromLocalOrAPI()` - Load ontology from storage or API
- `loadGraphFromLocal()` - Load from localStorage
- `saveGraphToLocal()` - Save to localStorage
- `convertOntologyToCytoscape()` - Convert API format to Cytoscape
- `convertOntologyToCytoscapeWithMetadata()` - Convert with rich metadata
- `fetchRichMetadata()` - SPARQL queries for metadata
- `importOntologyJSON()` - Import ontology from JSON
- `exportOntologyJSON()` - Export ontology to JSON

#### 3. **Tree Panel** (~600 lines)
- `refreshOntologyTree()` - Render tree view of ontology elements
- `highlightTreeItem()` - Highlight tree item when canvas selection changes
- `handleTreeSelection()` - Handle tree item clicks
- Tree node creation and manipulation

#### 4. **Properties Panel** (~800 lines)
- `updatePropertiesPanelFromSelection()` - Update panel based on selection
- `updateMultiplicityFields()` - Update multiplicity constraint fields
- `updateDatatypeFields()` - Update datatype constraint fields
- `updateEnumerationFields()` - Update enumeration constraint fields
- `updatePositionInputs()` - Update CAD-like position inputs
- `populateParentClasses()` - Populate parent class selector
- `updateElementIriDisplay()` - Update IRI display
- `loadAdditionalMetadataForElement()` - Lazy load metadata
- `updateAttributeEditor()` - Update attribute editor
- `saveShaclConstraintsToBackend()` - Save SHACL constraints
- `saveClassInheritanceToBackend()` - Save class inheritance
- `saveModelMetadataToBackend()` - Save model metadata

#### 5. **Canvas Operations** (~400 lines)
- `addClassNode()` - Add class node
- `addClassNodeAt()` - Add class node at position
- `performDelete()` - Delete selected elements
- `handleDeleteKey()` - Keyboard delete handler
- `showInlineEditor()` - Inline label editor (F2/double-click)
- Drag-and-drop handlers

#### 6. **Layout Management** (~300 lines)
- `runAdvancedLayout()` - Run layout algorithm (cose, dagre, grid, etc.)
- `runAutoLayout()` - Legacy auto layout
- `loadLayoutFromServer()` - Load saved layout
- `saveLayoutToServer()` - Save layout to server
- Layout persistence

#### 7. **Context Menus** (~200 lines)
- `showMenuAt()` - Show node context menu
- `hideMenu()` - Hide node context menu
- `showEdgeMenuAt()` - Show edge context menu
- `hideEdgeMenu()` - Hide edge context menu
- `startConnectFrom()` - Start connection from node
- `clearConnectState()` - Clear connection state
- `updateEdgeMultiplicity()` - Update edge multiplicity
- `showCustomMultiplicityDialog()` - Custom multiplicity dialog

#### 8. **Local Storage & State** (~400 lines)
- `storageKeyForGraph()` - Generate storage key
- `persistOntologyToLocalStorage()` - Persist graph to localStorage
- `loadCollapsedImports()` - Load collapsed imports state
- `saveCollapsedImports()` - Save collapsed imports state
- `loadVisibilityState()` - Load visibility state
- `saveVisibilityState()` - Save visibility state
- `loadElementVisibility()` - Load element visibility
- `saveElementVisibility()` - Save element visibility
- `loadOverlayPositions()` - Load overlay positions
- `saveOverlayPositions()` - Save overlay positions
- `loadPseudoNodePositions()` - Load pseudo node positions
- `savePseudoNodePositions()` - Save pseudo node positions
- `loadVisibleImports()` - Load visible imports
- `saveVisibleImports()` - Save visible imports
- `loadIriMap()` - Load IRI mapping
- `saveIriMap()` - Save IRI mapping

#### 9. **Metadata Management** (~200 lines)
- `addCreationMetadata()` - Add creation metadata
- `updateModificationMetadata()` - Update modification metadata
- `getCurrentUsername()` - Get current user
- `getCurrentTimestamp()` - Get timestamp
- `getCurrentDate()` - Get date
- `ensureAttributesExist()` - Ensure all elements have attrs
- `recomputeNextId()` - Recompute next class ID

#### 10. **UI Utilities** (~300 lines)
- `showTemporaryMessage()` - Show temporary message
- `updateOntoGraphLabel()` - Update graph label display
- `showOntologyLoadingIndicator()` - Show loading overlay
- `hideOntologyLoadingIndicator()` - Hide loading overlay
- `updateOntologyLoadingProgress()` - Update loading progress
- `getTypeDisplayName()` - Get type display name
- `getNoteTypeStyle()` - Get note type style
- `snapToGrid()` - Snap position to grid
- `toggleSnapToGrid()` - Toggle snap-to-grid
- `updateGridSize()` - Update grid size

#### 11. **Advanced Features** (~500 lines)
- `overlayImportsRefresh()` - Refresh imported ontology overlays
- `fetchImportGraphSnapshot()` - Fetch imported graph
- `showReferenceOntologySelector()` - Show import selector
- Named views management
- Undo/redo stack
- Copy/paste
- Alignment tools
- Zoom controls

#### 12. **Export/Import** (~400 lines)
- `toTurtle()` - Convert to Turtle format
- `generateAttributeTriples()` - Generate RDF triples
- `extractRdfPropertyFromLabel()` - Extract RDF property
- `getAttributeToRdfMapping()` - Get attribute mapping
- `computeLinkedByPairs()` - Compute linked pairs

## Proposed Modular Architecture

### Directory Structure

```
frontend/js/workbenches/ontology/
├── ontology-ui.js                    # Main entry point & orchestration
├── ontology-ui-structure.js          # HTML structure (already exists)
│
├── core/
│   ├── cytoscape-init.js            # Cytoscape initialization (~600 lines)
│   ├── state-manager.js             # ontoState management (~200 lines)
│   └── event-handlers.js            # Global event handlers (~300 lines)
│
├── graph/
│   ├── graph-loader.js              # loadGraphFromLocalOrAPI (~200 lines)
│   ├── graph-converter.js           # convertOntologyToCytoscape (~300 lines)
│   ├── graph-persistence.js         # Local storage functions (~200 lines)
│   └── metadata-fetcher.js         # fetchRichMetadata (~200 lines)
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
│   ├── constraints-editor.js        # SHACL constraints (~300 lines)
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
│   └── state-persistence.js        # State save/load (~200 lines)
│
├── utils/
│   ├── metadata-helpers.js          # Metadata functions (~150 lines)
│   ├── ui-helpers.js                # UI utility functions (~200 lines)
│   └── rdf-helpers.js               # RDF/Turtle conversion (~300 lines)
│
└── features/
    ├── imports-manager.js           # Import overlay management (~300 lines)
    ├── named-views.js               # Named views (~200 lines)
    ├── undo-redo.js                 # Undo/redo stack (~200 lines)
    └── export-import.js             # Export/import functions (~400 lines)
```

### Module Dependencies

```
ontology-ui.js (orchestrator)
├── core/cytoscape-init.js
├── core/state-manager.js
├── core/event-handlers.js
├── graph/graph-loader.js
│   ├── graph/graph-converter.js
│   ├── graph/graph-persistence.js
│   └── graph/metadata-fetcher.js
├── canvas/canvas-operations.js
│   ├── canvas/drag-drop.js
│   ├── canvas/inline-editor.js
│   └── canvas/selection-handler.js
├── tree/tree-renderer.js
│   └── tree/tree-selection.js
├── properties/properties-panel.js
│   ├── properties/constraints-editor.js
│   ├── properties/inheritance-editor.js
│   └── properties/metadata-editor.js
├── layout/layout-manager.js
│   └── layout/layout-persistence.js
├── menus/context-menu.js
│   └── menus/edge-menu.js
├── storage/local-storage.js
│   └── storage/state-persistence.js
├── utils/metadata-helpers.js
├── utils/ui-helpers.js
└── utils/rdf-helpers.js
```

## Benefits of This Architecture

1. **Maintainability**: Each module has a single responsibility
2. **Testability**: Modules can be tested independently
3. **Reusability**: Utility modules can be reused
4. **Readability**: Clear organization makes code easier to understand
5. **Scalability**: Easy to add new features without bloating files
6. **Collaboration**: Multiple developers can work on different modules

## Migration Strategy

### Phase 1: Extract Core Infrastructure
1. Create directory structure
2. Extract `core/state-manager.js` - ontoState management
3. Extract `utils/metadata-helpers.js` - Metadata utilities
4. Extract `utils/ui-helpers.js` - UI utilities

### Phase 2: Extract Graph Management
1. Extract `graph/graph-persistence.js` - Local storage functions
2. Extract `graph/graph-converter.js` - Conversion functions
3. Extract `graph/graph-loader.js` - Loading logic

### Phase 3: Extract Canvas Operations
1. Extract `canvas/canvas-operations.js` - Add/delete operations
2. Extract `canvas/drag-drop.js` - Drag-and-drop
3. Extract `canvas/inline-editor.js` - Inline editing

### Phase 4: Extract UI Panels
1. Extract `tree/tree-renderer.js` - Tree panel
2. Extract `properties/properties-panel.js` - Properties panel

### Phase 5: Extract Advanced Features
1. Extract `layout/layout-manager.js` - Layout algorithms
2. Extract `menus/context-menu.js` - Context menus
3. Extract `features/imports-manager.js` - Import overlays

### Phase 6: Extract Core Initialization
1. Extract `core/cytoscape-init.js` - Cytoscape setup
2. Wire everything together in `ontology-ui.js`

## File Size Guidelines

- **Target**: 200-400 lines per file
- **Maximum**: 500 lines per file
- **Exception**: Core initialization can be larger (~600 lines) due to Cytoscape config

## Next Steps

1. Review and approve this architecture
2. Create the directory structure
3. Begin Phase 1 extraction
4. Test incrementally after each phase




