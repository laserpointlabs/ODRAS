<!-- 6ccaca94-3bd3-4d03-974b-1c216d3327fe 0b202c5e-01b2-4577-bb89-8fd656be67b8 -->
# DAS-Driven Configuration Graph Visualization Implementation Plan

## Overview

Implement a graph-based configuration viewer that displays DAS-generated system architectures as interactive network graphs. This approach provides maximum flexibility for DAS to return any configuration structure while giving users powerful tools to visualize and understand complex system relationships at scale.

## Key Design Decisions

- **Visualization Library**: Use a high-performance graph library (e.g., Cytoscape.js, D3.js, or vis.js)
- **UI Pattern**: Master-detail pattern with filterable list/tree + graph canvas
- **Scale Management**: Progressive loading, clustering, and filtering for hundreds of configurations
- **Storage**: Configurations stored in Fuseki as RDF graphs with bi-directional sync

## Implementation Approach

### Phase 1: Backend Infrastructure

1. **Configuration API** (`backend/api/configurations.py`)

            - `GET /api/ontology/{project_id}/configurations` - List with pagination/filtering
            - `POST /api/ontology/{project_id}/configurations` - Create (DAS-friendly)
            - `GET /api/ontology/{project_id}/configurations/{config_id}` - Get specific
            - `GET /api/ontology/{project_id}/configurations/{config_id}/graph` - Get graph format
            - `POST /api/ontology/{project_id}/configurations/batch-generate` - DAS batch process
            - `GET /api/ontology/{project_id}/configurations/overview-graph` - Aggregated view

2. **Graph Data Format**
   ```json
   {
     "nodes": [
       {
         "id": "req-001",
         "type": "Requirement",
         "label": "System shall process data",
         "properties": {...},
         "dasMetadata": {
           "confidence": 0.95,
           "rationale": "Core requirement"
         }
       },
       {
         "id": "comp-001",
         "type": "Component",
         "label": "Processing Engine",
         "properties": {...}
       }
     ],
     "edges": [
       {
         "id": "e1",
         "source": "req-001",
         "target": "comp-001",
         "type": "specifies",
         "label": "specifies (1..*)"
       }
     ],
     "clusters": [
       {
         "id": "config-001",
         "label": "REQ-001 Configuration",
         "nodeIds": ["req-001", "comp-001", ...]
       }
     ]
   }
   ```


### Phase 2: Frontend Graph Architecture

1. **Master-Detail Layout**
   ```
   ┌─────────────────────────────────────────────────────┐
   │ Configurations                                      │
   ├────────────────┬────────────────────────────────────┤
   │ ▼ Filter       │  Graph Canvas                      │
   │ □ Requirements │  ┌─────┐      ┌─────┐             │
   │ □ DAS Generated│  │ REQ │─────>│ CMP │             │
   │ □ Manual       │  └─────┘      └─────┘             │
   │                │       │            │                │
   │ ▼ Configurations│      ▼            ▼               │
   │ ├─ REQ-001 ✓  │  ┌─────┐      ┌─────┐             │
   │ ├─ REQ-002    │  │ CNS │      │ PRC │             │
   │ ├─ REQ-003    │  └─────┘      └─────┘             │
   │ └─ ...        │                                    │
   │                │ [Zoom][Filter][Layout][Export]    │
   └────────────────┴────────────────────────────────────┘
   ```

2. **Configuration Browser Component**

            - **Left Panel**: Hierarchical tree or searchable table
                    - Group by requirement source
                    - Show DAS confidence scores
                    - Multi-select for comparison
                    - Search/filter capabilities
            - **Right Panel**: Graph canvas
                    - Interactive node/edge rendering
                    - Multiple layout algorithms
                    - Zoom/pan controls
                    - Node/edge filtering

3. **View Modes**

            - **Individual Configuration**: Show one configuration's full graph
            - **Comparison View**: Show 2-4 configurations side-by-side
            - **Overview Mode**: Aggregated view of all configurations
            - **Diff View**: Highlight differences between configurations

### Phase 3: Graph Visualization Features

1. **Node Representation**
   ```javascript
   {
     // Visual encoding by class type
     "Requirement": { shape: "roundrectangle", color: "#4A90E2" },
     "Component": { shape: "hexagon", color: "#50E3C2" },
     "Process": { shape: "diamond", color: "#F5A623" },
     "Constraint": { shape: "triangle", color: "#BD10E0" },
     "Interface": { shape: "ellipse", color: "#7ED321" },
     "Function": { shape: "star", color: "#9013FE" }
   }
   ```

2. **Interactive Features**

            - Click node: Show properties panel
            - Double-click: Focus/expand subgraph
            - Hover: Show DAS rationale tooltip
            - Drag: Rearrange layout
            - Multi-select: Compare properties

3. **Graph Controls**
   ```javascript
   // Toolbar actions
   - Layout: Force-directed, Hierarchical, Circular, Grid
   - Filter: By class type, confidence level, relationship type
   - Search: Find nodes by name/property
   - Cluster: Group by configuration, class type
   - Export: PNG, SVG, JSON, GraphML
   ```


### Phase 4: Scale Management

1. **Performance Optimizations**

            - **Progressive Loading**: Load configurations on-demand
            - **Node Clustering**: Group related nodes at high zoom levels
            - **Edge Bundling**: Reduce visual clutter for many edges
            - **Virtualization**: Only render visible nodes/edges
            - **WebGL Rendering**: Use GPU acceleration for large graphs

2. **Data Management**
   ```javascript
   // Configuration list pagination
   {
     "configurations": [...],
     "pagination": {
       "page": 1,
       "pageSize": 50,
       "total": 500,
       "filters": {
         "source": "DAS",
         "dateRange": "last-7-days",
         "requirementPrefix": "REQ-"
       }
     }
   }
   ```

3. **Caching Strategy**

            - Cache rendered graphs in browser
            - Lazy-load configuration details
            - Preload adjacent configurations

### Phase 5: DAS Integration

1. **Batch Generation UI**
   ```
   ┌─────────────────────────────────────┐
   │ Generate Configurations from DAS    │
   ├─────────────────────────────────────┤
   │ Select Requirements:                │
   │ ☑ All (245 requirements)           │
   │ ☐ Selected only                    │
   │ ☐ Unprocessed only                 │
   │                                     │
   │ DAS Options:                        │
   │ ☐ Include rationale                │
   │ ☐ Generate alternatives            │
   │ Confidence threshold: [0.7 ▼]      │
   │                                     │
   │ [Cancel] [Generate]                 │
   └─────────────────────────────────────┘
   ```

2. **Progress Tracking**

            - Real-time progress bar
            - Streaming results display
            - Error handling and retry

### Phase 6: Bi-directional Sync

1. **Graph → Individual Tables**

            - Batch create individuals from graph
            - Update existing individuals
            - Maintain relationship integrity

2. **Individual Tables → Graph**

            - Reflect individual changes in graph
            - Highlight manual vs DAS-generated

## Technical Stack

### Frontend Libraries

```javascript
// Option 1: Cytoscape.js (Recommended)
- Excellent performance with large graphs
- Rich plugin ecosystem
- Good documentation

// Option 2: vis.js/vis-network
- Easy to integrate
- Good for medium-scale graphs
- Built-in physics simulation

// Option 3: D3.js with force-graph
- Maximum flexibility
- Requires more custom code
- Best for custom visualizations
```

### Graph Layout Algorithms

- **Hierarchical**: For tree-like structures
- **Force-Directed**: Natural clustering
- **Circular**: Show cycles clearly
- **Grid**: Organized placement
- **Custom**: DAS-aware layouts

## Files to Create/Modify

- `frontend/app.html` - Add graph visualization components
- `frontend/js/configuration-graph.js` - Graph rendering logic
- `frontend/js/configuration-browser.js` - List/tree navigation
- `backend/api/configurations.py` - Graph-aware endpoints
- `backend/services/graph_builder.py` - Convert configs to graph format
- `backend/services/configuration_manager.py` - Enhanced for graph ops
- Add Cytoscape.js or chosen library to requirements

### To-dos

- [ ] Create graph-aware configuration API with pagination and filtering for scale
- [ ] Build service to convert configurations to graph format with nodes/edges
- [ ] Implement master-detail UI layout with configuration browser and graph canvas
- [ ] Integrate Cytoscape.js or chosen graph library with ODRAS
- [ ] Build graph rendering component with interactive features
- [ ] Implement performance optimizations for hundreds of configs
- [ ] Create different view modes (individual, comparison, overview)
- [ ] Build DAS batch generation UI with progress tracking
- [ ] Add graph control toolbar (layout, filter, search, export)
- [ ] Implement sync between graph view and individual tables