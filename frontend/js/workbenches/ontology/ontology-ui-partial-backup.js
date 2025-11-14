/**
 * Ontology Workbench UI Module
 * 
 * Complete ontology workbench functionality extracted from app.html
 * Handles ontology visualization, editing, tree navigation, and properties panel
 */

import { apiClient } from '../../core/api-client.js';
import { getAppState, updateAppState } from '../../core/state-manager.js';
import { subscribeToEvent, emitEvent } from '../../core/event-bus.js';

// Use apiClient as ApiClient
const ApiClient = apiClient;

// Ontology workbench state
const ontoState = {
  cy: null,
  eh: null,
  connectMode: false,
  clickConnectFrom: null,
  nextId: 1,
  currentPredicateType: 'objectProperty',
  isCanvasActive: false,
  suspendAutosave: false,
  autosaveBound: false,
  layoutRunning: false,
  snapToGrid: true,
  gridSize: 20,
  undoStack: [],
  redoStack: [],
  maxUndoLevels: 50,
  clipboard: null,
  visibilityState: {
    classes: true,
    dataProperties: true,
    notes: true,
    edges: true,
    imported: true
  },
  collapsedImports: new Set(),
  elementVisibility: {},
  activeNamedView: null,
  beforeViewState: null
};

let activeProject = null;
let suppressWorkbenchSwitch = false;
let activeOntologyIri = null;

// Context menu state
const cmState = { visible: false, sourceId: null, sourceType: null };

/**
 * Initialize ontology workbench
 */
export function initializeOntologyWorkbench() {
  console.log('🔷 Initializing Ontology Workbench...');
  
  // Ensure Cytoscape is initialized
  ensureOntologyInitialized();
  
  // Set up event listeners
  setupOntologyEventListeners();
  
  // Load initial ontology if project is active
  const state = getAppState();
  if (state.activeProject?.projectId) {
    console.log('🔷 Loading ontologies for active project on init:', state.activeProject.projectId);
    loadProjectOntologies(state.activeProject.projectId);
  } else {
    console.log('⚠️ No active project on ontology workbench init');
  }
  
  console.log('✅ Ontology Workbench initialized');
}

/**
 * Ensure Cytoscape canvas is initialized
 */
function ensureOntologyInitialized() {
  if (ontoState.cy) return;
  
  const container = document.getElementById('cy');
  if (!container) {
    console.warn('⚠️ Cytoscape container (#cy) not found');
    return;
  }
  
  // Make canvas focusable for keyboard events
  try {
    container.setAttribute('tabindex', '0');
    container.style.outline = 'none';
  } catch (_) {}
  
  // Initialize Cytoscape plugins if available (MUST be done before creating cytoscape instance)
  try {
    if (window.cytoscape) {
      // Check for edgehandles plugin
      if (window.cytoscapeEdgehandles && typeof window.cytoscapeEdgehandles === 'function') {
        console.log('🔍 Registering cytoscape-edgehandles plugin...');
        window.cytoscape.use(window.cytoscapeEdgehandles);
        console.log('✅ cytoscape-edgehandles registered');
      } else if (window.edgehandles && typeof window.edgehandles === 'function') {
        console.log('🔍 Registering edgehandles plugin (alternative name)...');
        window.cytoscape.use(window.edgehandles);
        console.log('✅ edgehandles registered');
      } else {
        console.warn('⚠️ Edgehandles plugin not found. Available:', {
          cytoscapeEdgehandles: typeof window.cytoscapeEdgehandles,
          edgehandles: typeof window.edgehandles
        });
      }
    }
  } catch (err) {
    console.error('❌ Error registering Cytoscape plugins:', err);
  }
  
  // Initialize Cytoscape instance
  if (!window.cytoscape) {
    console.error('❌ Cytoscape library not loaded - ensure script is in index.html');
    console.error('   Expected: <script src="https://unpkg.com/cytoscape@3.28.1/dist/cytoscape.min.js"></script>');
    return;
  }
  
  ontoState.cy = window.cytoscape({
    container,
    layout: {
      name: 'breadthfirst',
      directed: true,
      spacingFactor: 2.0,
      avoidOverlap: true,
      nodeDimensionsIncludeLabels: true,
      animate: true,
      animationDuration: 500,
      fit: true,
      padding: 50
    },
    wheelSensitivity: 0.15,
    minZoom: 0.1,
    maxZoom: 3,
    boxSelectionEnabled: true,
    selectionType: 'single',
    style: [
      {
        selector: 'node',
        style: {
          'shape': 'round-rectangle',
          'background-color': '#1b2a45',
          'border-color': '#2a3b5f',
          'border-width': 1,
          'label': 'data(label)',
          'color': '#e5e7eb',
          'font-size': 12,
          'text-wrap': 'wrap',
          'text-max-width': 180,
          'text-valign': 'center',
          'text-halign': 'center'
        }
      },
      { selector: 'node[type = "class"]', style: { 'width': 180, 'height': 56 } },
      {
        selector: 'node[type = "dataProperty"]',
        style: {
          'width': 160,
          'height': 48,
          'background-color': '#154e5a',
          'border-color': '#2ea3b0'
        }
      },
      {
        selector: 'edge',
        style: {
          'curve-style': 'bezier',
          'width': 2,
          'line-color': '#3b4a6b',
          'target-arrow-shape': 'triangle',
          'target-arrow-color': '#3b4a6b',
          'arrow-scale': 1,
          'label': 'data(predicate)',
          'color': '#e5e7eb',
          'font-size': 10,
          'text-rotation': 'autorotate',
          'text-background-color': '#0b1220',
          'text-background-opacity': 0.6,
          'text-background-padding': 2,
          'target-label': 'data(multiplicityDisplay)',
          'target-text-offset': 15,
          'target-text-rotation': 0,
          'target-text-color': '#60a5fa',
          'target-text-background-color': '#0b1220',
          'target-text-background-opacity': 0.8,
          'target-text-background-padding': 3,
          'target-text-border-width': 1,
          'target-text-border-color': '#60a5fa',
          'target-text-border-opacity': 0.5
        }
      },
      {
        selector: 'edge[type = "note"], edge[predicate = "note_for"]',
        style: {
          'target-arrow-shape': 'circle',
          'target-arrow-color': '#9ca3af',
          'arrow-scale': 0.8,
          'source-arrow-shape': 'none'
        }
      },
      {
        selector: '.imported',
        style: {
          'opacity': 0.55
        }
      },
      { selector: 'edge.imported', style: { 'line-style': 'dashed' } },
      {
        selector: 'edge.imported-equivalence',
        style: {
          'line-style': 'dotted',
          'width': 1.5,
          'line-color': '#60a5fa',
          'label': '≡',
          'color': '#9ca3af',
          'font-size': 9,
          'text-background-opacity': 0
        }
      },
      {
        selector: 'node[type = "note"], .note',
        style: {
          'shape': 'rectangle',
          'background-color': '#2d3748',
          'border-color': '#4a5568',
          'border-style': 'solid',
          'border-width': 1,
          'label': 'data(label)',
          'color': '#e5e7eb',
          'font-size': 12,
          'text-wrap': 'wrap',
          'text-max-width': 220,
          'text-valign': 'center',
          'text-halign': 'center',
          'width': 220,
          'height': 80
        }
      },
      {
        selector: ':selected',
        style: {
          'border-color': '#60a5fa',
          'border-width': 2,
          'line-color': '#60a5fa',
          'target-arrow-color': '#60a5fa'
        }
      }
    ],
    elements: []
  });
  
  window._cy = ontoState.cy;
  ontoState.nextId = 1;
  
  // Focus canvas on interaction so Delete works reliably
  ontoState.cy.on('tap', () => { try { container.focus(); } catch (_) { } });
  ontoState.cy.on('select', () => { try { container.focus(); } catch (_) { } });
  
  // Mark canvas active on any interaction
  ontoState.cy.on('tap', () => { ontoState.isCanvasActive = true; });
  
  // Initialize edgehandles plugin if available
  console.log('🔍 Checking for edgehandles plugin...');
  console.log('  - window.cytoscape:', typeof window.cytoscape);
  console.log('  - window.cytoscapeEdgehandles:', typeof window.cytoscapeEdgehandles);
  console.log('  - window.edgehandles:', typeof window.edgehandles);
  console.log('  - window.cytoscape.edgehandles:', typeof window.cytoscape?.edgehandles);
  console.log('  - ontoState.cy.edgehandles:', typeof ontoState.cy?.edgehandles);
  
  // Check if edgehandles is available (might be on cytoscape prototype or instance)
  const hasEdgehandles = typeof ontoState.cy.edgehandles === 'function' || 
                         typeof window.cytoscape?.edgehandles === 'function';
  
  if (hasEdgehandles) {
    console.log('✅ Edgehandles plugin found, initializing...');
    try {
      // Use instance method (should be available after plugin registration)
      ontoState.eh = ontoState.cy.edgehandles({
        handleSize: 8,
        handleNodes: 'node[type = "class"], node[type = "note"]',
        handleColor: '#60a5fa',
        handleOutlineColor: '#0b1220',
        handleOutlineWidth: 2,
        toggleOffOnLeave: true,
        enabled: true,
        edgeParams: () => ({ data: { predicate: 'relatedTo', type: 'objectProperty' } })
      });
      console.log('✅ Edgehandles initialized:', ontoState.eh);
      
      ontoState.cy.on('ehcomplete', (event, sourceNode, targetNode, addedEdge) => {
        console.log('🔗 Edge created via edgehandles:', { sourceNode: sourceNode.id(), targetNode: targetNode.id() });
        try {
          const srcType = (sourceNode.data('type') || 'class');
          const tgtType = (targetNode.data('type') || 'class');
          const edgeType = (addedEdge && addedEdge.data('type')) || ontoState.currentPredicateType || 'objectProperty';
          let invalid = false;
          
          if ((srcType === 'note' && (tgtType === 'class' || tgtType === 'dataProperty')) || 
              ((srcType === 'class' || srcType === 'dataProperty') && tgtType === 'note')) {
            if ((srcType === 'class' || srcType === 'dataProperty') && tgtType === 'note') {
              addedEdge.data('source', targetNode.id());
              addedEdge.data('target', sourceNode.id());
            }
            addedEdge.data('predicate', 'note_for');
            addedEdge.data('type', 'note');
          } else {
            if (edgeType === 'objectProperty' && (srcType !== 'class' || tgtType !== 'class')) invalid = true;
            if (srcType === 'note' || tgtType === 'note') invalid = true;
            if (invalid && addedEdge) { 
              console.warn('⚠️ Invalid edge connection, removing:', { srcType, tgtType, edgeType });
              addedEdge.remove(); 
              return; 
            }
          }
          console.log('✅ Edge validated and added:', { srcType, tgtType, edgeType });
        } catch (err) {
          console.error('❌ Error in ehcomplete handler:', err);
        }
        requestAnimationFrame(() => { 
          refreshOntologyTree(); 
          if (typeof persistOntologyToLocalStorage === 'function') persistOntologyToLocalStorage(); 
        });
      });
    } catch (err) {
      console.error('❌ Error initializing edgehandles:', err);
    }
  } else {
    console.warn('⚠️ Edgehandles plugin not available - edges can only be created via click-to-connect mode');
    // Fallback: Use click-to-connect mode
    ontoState.cy.on('tap', 'node', (ev) => {
      if (!ontoState.connectMode) return;
      const node = ev.target;
      if (!ontoState.clickConnectFrom) {
        ontoState.clickConnectFrom = node.id();
        console.log('🔗 Connect mode: First node selected:', node.id());
      } else {
        const from = ontoState.clickConnectFrom;
        const to = node.id();
        if (from !== to) {
          const src = ontoState.cy.$(`#${from}`)[0];
          const tgt = ontoState.cy.$(`#${to}`)[0];
          const srcType = (src && (src.data('type') || 'class')) || 'class';
          const tgtType = (tgt && (tgt.data('type') || 'class')) || 'class';
          if (srcType !== 'note' && tgtType !== 'note' && srcType === 'class' && tgtType === 'class') {
            const edgeId = `e${Date.now()}`;
            ontoState.cy.add({ 
              group: 'edges', 
              data: { 
                id: edgeId, 
                source: from, 
                target: to, 
                predicate: 'relatedTo', 
                type: 'objectProperty'
              } 
            });
            console.log('✅ Edge created via click-to-connect:', edgeId);
            refreshOntologyTree();
            persistOntologyToLocalStorage();
          }
        }
        ontoState.clickConnectFrom = null;
      }
    });
  }
  
  // Set up comprehensive event handlers
  ontoState.cy.on('select unselect add remove data free', () => {
    updatePropertiesPanelFromSelection();
    persistOntologyToLocalStorage();
    
    // Highlight corresponding tree item when canvas selection changes
    const selected = ontoState.cy.$(':selected');
    if (selected.length === 1) {
      const element = selected[0];
      if (element.isNode()) {
        if (typeof highlightTreeItem === 'function') highlightTreeItem(element.id(), 'node');
      } else if (element.isEdge()) {
        if (typeof highlightTreeItem === 'function') highlightTreeItem(element.id(), 'edge');
      }
    } else {
      // Clear tree selection when nothing is selected on canvas
      qsa('.node-row').forEach(r => r.classList.remove('selected'));
    }
  });
  
  // Set up delete key handler
  setupDeleteHandlers();
  
  // Background click clears selection and shows model-level props
  ontoState.cy.on('tap', (ev) => {
    if (ev.target === ontoState.cy) {
      ontoState.cy.$(':selected').unselect();
      updatePropertiesPanelFromSelection();
      hideMenu();
      hideEdgeMenu();
      clearConnectState();
    }
  });
  
  // Right-click context menu for nodes
  ontoState.cy.on('cxttap', 'node', (ev) => {
    const n = ev.target;
    const t = (n.data('type') || 'class');
    const rect = container.getBoundingClientRect();
    const rp = ev.renderedPosition || n.renderedPosition();
    
    // Configure menu per node type
    const menu = qs('#ontoContextMenu');
    if (!menu) return;
    
    const btnRel = qs('#menuAddRel');
    const btnDP = qs('#menuAddDataProp');
    
    if (t === 'note') {
      if (btnRel) {
        btnRel.innerHTML = `
          <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="7" cy="12" r="3"/><circle cx="17" cy="12" r="3"/><path d="M10 12h4"/>
          </svg>
          Link to Class/Property
        `;
      }
      if (btnDP) btnDP.style.display = 'none';
    } else {
      if (btnRel) {
        btnRel.innerHTML = `
          <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="7" cy="12" r="3"/><circle cx="17" cy="12" r="3"/><path d="M10 12h4"/>
          </svg>
          Add Relationship
        `;
      }
      if (btnDP) btnDP.style.display = 'block';
    }
    
    showMenuAt(rect.left + rp.x + 6, rect.top + rp.y + 6);
    menu.dataset.nodeId = n.id();
    menu.dataset.nodeType = t;
  });
  
  // Clicking a target after 'Add relationship' completes the edge
  ontoState.cy.on('tap', 'node', (ev) => {
    if (!cmState.sourceId) return;
    const target = ev.target;
    const tgtType = (target.data('type') || 'class');
    const source = ontoState.cy.$('#' + cmState.sourceId)[0];
    if (!source) {
      clearConnectState();
      return;
    }
    const srcType = cmState.sourceType || (source.data('type') || 'class');
    
    if (source.id() !== target.id()) {
      if (srcType === 'note' && (tgtType === 'class' || tgtType === 'dataProperty')) {
        const edgeId = `enote${Date.now()}`;
        ontoState.cy.add({
          group: 'edges',
          data: {
            id: edgeId,
            source: source.id(),
            target: target.id(),
            predicate: 'note_for',
            type: 'note'
          }
        });
        console.log('✅ Edge created via context menu:', edgeId);
        refreshOntologyTree();
        persistOntologyToLocalStorage();
      } else if (srcType === 'class' && tgtType === 'class') {
        const edgeId = `e${Date.now()}`;
        ontoState.cy.add({
          group: 'edges',
          data: {
            id: edgeId,
            source: source.id(),
            target: target.id(),
            predicate: 'relatedTo',
            type: 'objectProperty'
          }
        });
        console.log('✅ Object property created via context menu:', edgeId);
        refreshOntologyTree();
        persistOntologyToLocalStorage();
      }
    }
    source.removeClass('connect-source');
    clearConnectState();
  });
  
  // Set up Cytoscape event handlers
  setupCytoscapeEventHandlers();
  
  console.log('✅ Cytoscape initialized');
}

/**
 * Set up Cytoscape event handlers
 */
function setupCytoscapeEventHandlers() {
  if (!ontoState.cy) return;
  
  // Selection change
  ontoState.cy.on('select', 'node, edge', (evt) => {
    updatePropertiesPanelFromSelection();
  });
  
  ontoState.cy.on('unselect', 'node, edge', () => {
    updatePropertiesPanelFromSelection();
  });
  
  // Canvas click
  ontoState.cy.on('tap', (evt) => {
    if (evt.target === ontoState.cy) {
      // Clicked on empty canvas
      updatePropertiesPanelFromSelection();
    }
  });
  
  // Node/edge drag
  ontoState.cy.on('drag', 'node', () => {
    if (!ontoState.suspendAutosave && activeOntologyIri) {
      debounceAutosave();
    }
  });
}

/**
 * Set up ontology workbench event listeners
 */
function setupOntologyEventListeners() {
  // Listen for project selection (project manager emits 'project:selected' with projectId)
  subscribeToEvent('project:selected', (projectId) => {
    console.log('🔷 Ontology workbench: Project selected:', projectId);
    if (projectId) {
      loadProjectOntologies(projectId);
    }
  });
  
  // Also listen for project:changed for backward compatibility
  subscribeToEvent('project:changed', (project) => {
    console.log('🔷 Ontology workbench: Project changed:', project);
    activeProject = project;
    if (project?.projectId) {
      loadProjectOntologies(project.projectId);
    }
  });
  
  // Initialize menus
  initializeOntologyMenus();
  
  // Setup drag and drop
  if (ontoState.cy) {
    setupDragAndDrop();
  } else {
    // Wait for Cytoscape to initialize
    setTimeout(() => {
      if (ontoState.cy) {
        setupDragAndDrop();
      }
    }, 500);
  }

  // Wire up tab buttons
  const ontologyTab = qs('#ontologyTab');
  const individualsTab = qs('#individualsTab');
  const cqmtTab = qs('#cqmtTab');
  
  if (ontologyTab) {
    ontologyTab.addEventListener('click', () => switchWorkbenchTab('ontology'));
  }
  if (individualsTab) {
    individualsTab.addEventListener('click', () => switchWorkbenchTab('individuals'));
  }
  if (cqmtTab) {
    cqmtTab.addEventListener('click', () => switchWorkbenchTab('cqmt'));
  }

  // Wire up Cytoscape selection events (also handled in setupCytoscapeEventHandlers)
  if (ontoState.cy) {
    ontoState.cy.on('select', 'node, edge', () => {
      updatePropertiesPanelFromSelection();
    });
    ontoState.cy.on('unselect', 'node, edge', () => {
      updatePropertiesPanelFromSelection();
    });
  }
  
  // Listen for workbench switch
  subscribeToEvent('workbench:switched', (workbenchId) => {
    if (workbenchId === 'ontology' && ontoState.cy) {
      // Resize cytoscape when workbench becomes active
      setTimeout(() => {
        if (ontoState.cy) {
          ontoState.cy.resize();
        }
      }, 100);
    }
    
    // Load ontologies if project is active
    if (workbenchId === 'ontology') {
      const state = getAppState();
      if (state.activeProject?.projectId) {
        console.log('🔷 Loading ontologies for active project:', state.activeProject.projectId);
        loadProjectOntologies(state.activeProject.projectId);
      }
    }
  });
}

/**
 * Load ontologies for a project
 */
async function loadProjectOntologies(projectId) {
  if (!projectId) {
    console.warn('⚠️ No project ID provided to loadProjectOntologies');
    return;
  }
  
  console.log('🔷 Loading ontologies for project:', projectId);
  
  try {
    const response = await ApiClient.get(`/api/ontologies?project_id=${projectId}`);
    console.log('📦 Ontologies API response:', response);
    
    if (response && response.ontologies && response.ontologies.length > 0) {
      console.log(`✅ Found ${response.ontologies.length} ontologies`);
      // Update ontology tree
      updateOntologyTree(response.ontologies);
      // Show layout section and hide empty state
      const layoutSection = document.getElementById('ontoLayoutSection');
      const emptyState = document.getElementById('ontoEmpty');
      if (layoutSection) {
        layoutSection.style.display = 'grid';
        console.log('✅ Showing ontology layout section');
      }
      if (emptyState) {
        emptyState.style.display = 'none';
      }
    } else {
      console.log('📦 No ontologies found for project');
      // Hide layout section and show empty state
      const layoutSection = document.getElementById('ontoLayoutSection');
      const emptyState = document.getElementById('ontoEmpty');
      if (layoutSection) {
        layoutSection.style.display = 'none';
      }
      if (emptyState) {
        emptyState.style.display = 'block';
      }
      // Clear tree
      const treeContainer = document.getElementById('ontoTreeRoot');
      if (treeContainer) {
        treeContainer.innerHTML = '';
      }
    }
  } catch (error) {
    console.error('❌ Failed to load project ontologies:', error);
    // Show empty state on error
    const emptyState = document.getElementById('ontoEmpty');
    if (emptyState) {
      emptyState.style.display = 'block';
    }
  }
}

/**
 * Update ontology tree UI
 */
function updateOntologyTree(ontologies) {
  const treeContainer = document.getElementById('ontoTreeRoot');
  if (!treeContainer) return;
  
  // Clear existing tree
  treeContainer.innerHTML = '';
  
  // Build tree structure
  ontologies.forEach(ontology => {
    const li = document.createElement('li');
    li.dataset.iri = ontology.graph_iri || ontology.iri;
    li.dataset.label = ontology.label || ontology.name;
    li.textContent = ontology.label || ontology.name || 'Unnamed Ontology';
    li.addEventListener('click', () => handleOntologySelection(ontology));
    treeContainer.appendChild(li);
  });
}

/**
 * Handle ontology selection from tree
 */
async function handleOntologySelection(ontology) {
  const iri = ontology.graph_iri || ontology.iri;
  if (!iri) return;
  
  // Save previous ontology state
  const prevIri = activeOntologyIri;
  ensureOntologyInitialized();
  
  if (ontoState.cy && prevIri) {
    saveGraphToLocal(prevIri);
  }
  
  // Switch active ontology
  activeOntologyIri = iri;
  updateOntoGraphLabel();
  
  // Load graph
  if (ontoState.cy) {
    ontoState.suspendAutosave = true;
    try {
      ontoState.cy.elements().remove();
    } catch (_) {}
    
    await loadGraphFromLocalOrAPI(iri);
    setTimeout(() => {
      ontoState.suspendAutosave = false;
    }, 50);
  }
  
  // Update properties panel
  updatePropertiesPanelFromSelection();
  
  // Refresh tree after graph loads
  setTimeout(() => {
    refreshOntologyTree();
  }, 200);
}

/**
 * Update graph label display
 */
function updateOntoGraphLabel() {
  const el = document.getElementById('ontoGraphLabel');
  if (!el) return;
  
  if (activeOntologyIri) {
    el.textContent = 'Graph: ' + activeOntologyIri;
    el.title = activeOntologyIri;
  } else {
    el.textContent = 'No graph selected';
    el.title = '';
  }
  
  // Toggle empty state
  const empty = document.getElementById('ontoEmpty');
  const layout = document.getElementById('ontoLayoutSection');
  if (empty && layout) {
    const showEmpty = !activeOntologyIri;
    empty.style.display = showEmpty ? 'block' : 'none';
    layout.style.display = showEmpty ? 'none' : 'grid';
  }
}

/**
 * Load graph from local storage or API
 */
async function loadGraphFromLocalOrAPI(iri) {
  console.log('🔍 loadGraphFromLocalOrAPI called for:', iri);
  
  // First try to load from local storage
  const loadedFromLocal = loadGraphFromLocal(iri);
  if (loadedFromLocal) {
    console.log('✅ Loaded from local storage');
    // Refresh tree after loading
    setTimeout(() => {
      refreshOntologyTree();
    }, 100);
    return;
  }
  
  // If not in local storage, load from API
  console.log('📡 Loading from API...');
  await loadGraphFromAPI(iri);
}

/**
 * Load graph from API
 */
async function loadGraphFromAPI(iri) {
  try {
    console.log('🔍 Loading graph from API:', iri);
    const response = await ApiClient.get(`/api/ontology/?graph=${encodeURIComponent(iri)}`);
    if (response && response.data) {
      convertOntologyToCytoscape(response.data);
    } else {
      console.warn('⚠️ No data in API response');
    }
  } catch (error) {
    console.error('❌ Failed to load graph from API:', error);
  }
}

/**
 * Convert ontology data to Cytoscape format
 */
function convertOntologyToCytoscape(ontologyData) {
  if (!ontoState.cy || !ontologyData) {
    console.warn('⚠️ Cannot convert: Cytoscape not initialized or no data');
    return;
  }
  
  console.log('🔄 Converting ontology data to Cytoscape format');
  
  const nodes = [];
  const edges = [];
  
  // Create nodes for classes
  const classes = ontologyData.classes || [];
  const classNameToId = {}; // Map class names to IDs
  
  classes.forEach((cls, index) => {
    // Use the original URI as ID if available, otherwise fall back to simple ID
    const classId = cls.iri || `Class${index + 1}`;
    classNameToId[cls.name] = classId;
    
    // Arrange in a grid layout
    const row = Math.floor(index / 4);
    const col = index % 4;
    
    const node = {
      group: 'nodes',
      data: {
        id: classId,
        iri: cls.iri || classId,
        label: cls.label || cls.name,
        type: 'class',
        attrs: {}
      },
      position: {
        x: 150 + (col * 200),
        y: 100 + (row * 150)
      }
    };
    nodes.push(node);
  });
  
  // Create edges for object properties
  let edgeId = 1;
  const objectProps = ontologyData.object_properties || [];
  objectProps.forEach(prop => {
    if (prop.domain && prop.range && classNameToId[prop.domain] && classNameToId[prop.range]) {
      // Format multiplicity constraints for display
      const minCount = prop.min_count;
      const maxCount = prop.max_count;
      let multiplicity = '';
      if (minCount !== null && minCount !== undefined || maxCount !== null && maxCount !== undefined) {
        if (minCount === 1 && maxCount === 1) multiplicity = ' (1)';
        else if (minCount === 0 && (maxCount === null || maxCount === undefined)) multiplicity = ' (0..*)';
        else if (minCount === 1 && (maxCount === null || maxCount === undefined)) multiplicity = ' (1..*)';
        else if (minCount === 0 && maxCount === 1) multiplicity = ' (0..1)';
        else if (minCount !== null && minCount !== undefined && maxCount !== null && maxCount !== undefined && minCount === maxCount)
          multiplicity = ` (${minCount})`;
        else if (minCount !== null && minCount !== undefined && maxCount !== null && maxCount !== undefined)
          multiplicity = ` (${minCount}..${maxCount})`;
        else if (minCount !== null && minCount !== undefined) multiplicity = ` (${minCount}..*)`;
        else if (maxCount !== null && maxCount !== undefined) multiplicity = ` (0..${maxCount})`;
      }
      
      const displayLabel = prop.label || prop.name;
      
      const edge = {
        group: 'edges',
        data: {
          id: `e${edgeId}`,
          source: classNameToId[prop.domain],
          target: classNameToId[prop.range],
          predicate: prop.name,
          label: displayLabel,
          type: 'objectProperty',
          minCount: minCount,
          maxCount: maxCount,
          multiplicityDisplay: multiplicity.trim(),
          attrs: {}
        }
      };
      edges.push(edge);
      edgeId++;
    }
  });
  
  // Create data property nodes and connect them to their domain classes
  let dpId = 1;
  const dataProps = ontologyData.datatype_properties || [];
  dataProps.forEach(prop => {
    if (prop.domain && classNameToId[prop.domain]) {
      const dataPropertyId = `DP${dpId}`;
      
      // Create data property node
      const domainClassId = classNameToId[prop.domain];
      const domainNode = nodes.find(n => n.data.id === domainClassId);
      let dpX = 150, dpY = 100; // fallback position
      
      if (domainNode) {
        // Position data property near its domain class
        dpX = domainNode.position.x + 180;
        dpY = domainNode.position.y + (dpId % 3 - 1) * 60; // stagger vertically
      }
      
      const dpNode = {
        group: 'nodes',
        data: {
          id: dataPropertyId,
          label: prop.label || prop.name,
          type: 'dataProperty',
          attrs: {}
        },
        position: {
          x: dpX,
          y: dpY
        }
      };
      nodes.push(dpNode);
      
      // Create edge connecting class to data property
      const dpEdge = {
        group: 'edges',
        data: {
          id: `edp${dpId}`,
          source: domainClassId,
          target: dataPropertyId,
          predicate: prop.name,
          type: 'objectProperty',
          attrs: {}
        }
      };
      edges.push(dpEdge);
      
      dpId++;
    }
  });
  
  // Clear existing elements and add new ones
  ontoState.cy.elements().remove();
  if (nodes.length > 0) {
    ontoState.cy.add(nodes);
  }
  if (edges.length > 0) {
    ontoState.cy.add(edges);
  }
  
  // Run layout
  ontoState.cy.layout({ name: 'preset' }).run();
  
  console.log(`✅ Converted: ${nodes.length} nodes, ${edges.length} edges`);
  
  // Ensure attributes exist and save to local storage
  ensureAttributesExist();
  if (activeOntologyIri) {
    persistOntologyToLocalStorage();
  }
  
  // Refresh tree after loading
  setTimeout(() => {
    refreshOntologyTree();
  }, 100);
}


/**
 * Debounced autosave
 */
let autosaveTimeout = null;
function debounceAutosave() {
  if (autosaveTimeout) {
    clearTimeout(autosaveTimeout);
  }
  
  autosaveTimeout = setTimeout(() => {
    if (activeOntologyIri && ontoState.cy) {
      saveGraphToLocal(activeOntologyIri);
    }
  }, 1000); // 1 second debounce
}

// Helper functions (from app.html)
const qs = (s, r = document) => r.querySelector(s);
const qsa = (s, r = document) => Array.from(r.querySelectorAll(s));
function debounce(fn, wait) {
  let t;
  return function (...args) {
    clearTimeout(t);
    t = setTimeout(() => fn.apply(this, args), wait);
  };
}

/**
 * Switch workbench tab (Ontologies, Individuals, CQ/MT)
 */
export function switchWorkbenchTab(tabName) {
  console.log('🔍 Switching workbench tab to:', tabName);

  // Update tab buttons
  const ontologyTab = document.getElementById('ontologyTab');
  const individualsTab = document.getElementById('individualsTab');
  const cqmtTab = document.getElementById('cqmtTab');

  if (ontologyTab) ontologyTab.classList.toggle('active', tabName === 'ontology');
  if (individualsTab) individualsTab.classList.toggle('active', tabName === 'individuals');
  if (cqmtTab) cqmtTab.classList.toggle('active', tabName === 'cqmt');

  // Show/hide content areas
  const ontoLayout = document.getElementById('ontoLayoutSection');
  const individualsContent = document.getElementById('individualsContent');
  const cqmtContent = document.getElementById('cqmtContent');

  if (tabName === 'ontology') {
    if (ontoLayout) ontoLayout.style.display = 'grid';
    if (individualsContent) individualsContent?.classList.remove('active');
    if (cqmtContent) {
      cqmtContent.classList.remove('active');
      cqmtContent.style.display = 'none';
    }
  } else if (tabName === 'individuals') {
    if (ontoLayout) ontoLayout.style.display = 'none';
    if (individualsContent) {
      individualsContent.classList.add('active');
      individualsContent.style.display = 'block';
    }
    if (cqmtContent) {
      cqmtContent.classList.remove('active');
      cqmtContent.style.display = 'none';
    }
    // Load individuals for currently selected ontology
    if (typeof loadIndividualTablesForCurrentOntology === 'function') {
      loadIndividualTablesForCurrentOntology();
    }
  } else if (tabName === 'cqmt') {
    if (ontoLayout) ontoLayout.style.display = 'none';
    if (individualsContent) individualsContent?.classList.remove('active');
    if (cqmtContent) {
      cqmtContent.classList.add('active');
      cqmtContent.style.display = 'block';
    }
    // Initialize CQ/MT workbench if needed
    if (typeof initializeCQMTWorkbench === 'function') {
      initializeCQMTWorkbench();
    }
  }
}

/**
 * Initialize ontology menu buttons
 */
function initializeOntologyMenus() {
  const menuButtons = ['ontoLayoutMenuBtn', 'ontoViewMenuBtn', 'ontoEditMenuBtn', 'ontoFileMenuBtn', 'cadToolsMenuBtn'];
  menuButtons.forEach(btnId => {
    const btn = document.getElementById(btnId);
    if (btn) {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const dropdown = btn.nextElementSibling;
        if (dropdown) {
          // Close other menus
          document.querySelectorAll('.menu-dropdown').forEach(menu => {
            if (menu !== dropdown) {
              menu.style.display = 'none';
            }
          });
          // Toggle current menu
          dropdown.style.display = dropdown.style.display === 'block' ? 'none' : 'block';
        }
      });
    }
  });
}

/**
 * Select node in tree
 */
function selectNode(li) {
  qsa('.onto-node-row').forEach(r => r.classList.remove('selected'));
  const row = li.querySelector('.onto-node-row');
  if (row) row.classList.add('selected');
}

/**
 * Handle tree selection
 */
async function handleTreeSelection(li) {
  if (!li || !li.dataset) return;
  const type = li.dataset.nodeType || '';

  if (type === 'class' || type === 'dataProperty' || type === 'note') {
    const nodeId = li.dataset.nodeId;
    if (nodeId && ontoState.cy) {
      const node = ontoState.cy.$(`#${CSS.escape(nodeId)}`);
      if (node.length > 0) {
        ontoState.cy.$(':selected').unselect();
        node.select();
        updatePropertiesPanelFromSelection();
        // Center on node
        ontoState.cy.animate({
          center: { eles: node },
          zoom: Math.min(ontoState.cy.zoom(), 1.5)
        }, { duration: 300 });
      }
    }
  } else if (type === 'edge') {
    const edgeId = li.dataset.edgeId;
    if (edgeId && ontoState.cy) {
      const edge = ontoState.cy.$(`#${CSS.escape(edgeId)}`);
      if (edge.length > 0) {
        ontoState.cy.$(':selected').unselect();
        edge.select();
        updatePropertiesPanelFromSelection();
      }
    }
  }
}

/**
 * Refresh ontology tree view
 */
async function refreshOntologyTree() {
  const root = qs('#ontoTreeRoot');
  if (!root || !ontoState.cy) return;

  // Filter nodes based on visibility settings
  const classes = ontoState.cy.nodes().filter(n => {
    const nodeType = n.data('type') || 'class';
    const isImported = n.hasClass('imported');
    return !isImported && nodeType === 'class';
  });

  const dataProperties = ontoState.cy.nodes().filter(n => {
    const nodeType = n.data('type') || 'class';
    const isImported = n.hasClass('imported');
    return !isImported && nodeType === 'dataProperty';
  });

  const importedClasses = ontoState.cy.nodes().filter(n => {
    const nodeType = n.data('type') || 'class';
    const isImported = n.hasClass('imported');
    return isImported && nodeType === 'class';
  });

  const notes = ontoState.cy.nodes().filter(n => {
    const nodeType = n.data('type') || '';
    const isImported = n.hasClass('imported');
    return !isImported && nodeType === 'note';
  });

  // Build tree structure
  root.innerHTML = '';
  const makeItem = (label, expanded = true, children = []) => {
    const li = document.createElement('li');
    li.setAttribute('role', 'treeitem');
    if (children.length) li.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    const row = document.createElement('div');
    row.className = 'onto-node-row';
    row.tabIndex = 0;
    const twist = document.createElement('span');
    twist.className = 'onto-twist';
    if (children.length) {
      twist.onclick = (e) => {
        e.stopPropagation();
        li.setAttribute('aria-expanded', li.getAttribute('aria-expanded') === 'true' ? 'false' : 'true');
      };
    }
    const text = document.createElement('span');
    text.className = 'onto-node-label';
    text.textContent = label;
    row.appendChild(twist);
    row.appendChild(text);
    li.appendChild(row);

    // Add click handler for tree item selection
    row.onclick = async (e) => {
      if (e.target.tagName === 'BUTTON') return;
      selectNode(li);
      await handleTreeSelection(li);
    };
    row.onkeydown = (e) => {
      const ENTER = 13, SPACE = 32;
      if (e.keyCode === ENTER || e.keyCode === SPACE) {
        selectNode(li);
        handleTreeSelection(li).catch(console.error);
        e.preventDefault();
      }
    };

    if (children.length) {
      const ul = document.createElement('ul');
      ul.setAttribute('role', 'group');
      children.forEach(c => ul.appendChild(c));
      li.appendChild(ul);
    }
    return li;
  };

  const items = [];
  
  // Add classes with relationships
  classes.forEach(cls => {
    const label = cls.data('label') || cls.id();
    const outEdges = cls.outgoers('edge');
    const rels = outEdges.map(e => {
      const other = e.target();
      const pred = e.data('predicate') || 'relatedTo';
      const type = e.data('type') || 'objectProperty';
      const item = makeItem(`${pred} → ${(other.data('label') || other.id())} (${type})`, false, []);
      item.dataset.edgeId = e.id();
      item.dataset.nodeType = 'edge';
      return item;
    });
    const classItem = makeItem(label, false, rels);
    classItem.dataset.nodeId = cls.id();
    classItem.dataset.nodeType = 'class';
    items.push(classItem);
  });

  // Add data properties
  if (dataProperties.length) {
    const dataPropertyChildren = dataProperties.map(dp => {
      const item = makeItem(dp.data('label') || dp.id(), false, []);
      item.dataset.nodeId = dp.id();
      item.dataset.nodeType = 'dataProperty';
      return item;
    });
    items.push(makeItem('Data Properties', true, dataPropertyChildren));
  }

  // Add imported classes
  if (importedClasses.length) {
    const importedChildren = importedClasses.map(cls => {
      const item = makeItem((cls.data('label') || cls.id()) + ' (imported)', false, []);
      item.dataset.nodeId = cls.id();
      item.dataset.nodeType = 'class';
      return item;
    });
    items.push(makeItem('Imported Classes', true, importedChildren));
  }

  // Add notes
  if (notes.length) {
    const noteChildren = notes.map(n => {
      const item = makeItem(n.data('label') || n.id(), false, []);
      item.dataset.nodeId = n.id();
      item.dataset.nodeType = 'note';
      return item;
    });
    items.push(makeItem('Notes', true, noteChildren));
  }

  // Append all items to root
  items.forEach(item => root.appendChild(item));
}

/**
 * Update properties panel from selection
 */
function updatePropertiesPanelFromSelection() {
  const form = qs('#ontoPropsForm');
  if (!form || !ontoState.cy) return;
  
  const sel = ontoState.cy.$(':selected');
  const nameEl = qs('#propName');
  const typeValueEl = qs('#propTypeValue');

  if (!nameEl || !typeValueEl) return;

  if (sel.length === 1 && sel[0].isNode()) {
    const n = sel[0];
    const isImported = n.hasClass('imported');
    nameEl.value = n.data('label') || n.id();
    nameEl.disabled = isImported;
    const nodeType = n.data('type') || 'class';
    typeValueEl.textContent = getTypeDisplayName(nodeType) + (isImported ? ' (Imported)' : '');
    
    // Show/hide sections based on node type
    const parentClassesGroup = qs('#parentClassesGroup');
    const abstractGroup = qs('#abstractGroup');
    if (nodeType === 'class') {
      if (parentClassesGroup) parentClassesGroup.style.display = 'block';
      if (abstractGroup) abstractGroup.style.display = 'block';
    } else {
      if (parentClassesGroup) parentClassesGroup.style.display = 'none';
      if (abstractGroup) abstractGroup.style.display = 'none';
    }
  } else if (sel.length === 1 && sel[0].isEdge()) {
    const e = sel[0];
    nameEl.value = e.data('predicate') || e.id();
    const edgeType = e.data('type') || 'objectProperty';
    typeValueEl.textContent = getTypeDisplayName(edgeType);
    
    // Show SHACL constraints for properties
    const shaclSection = qs('#shaclConstraintsSection');
    if (shaclSection && (edgeType === 'objectProperty' || edgeType === 'dataProperty')) {
      shaclSection.style.display = 'block';
    } else if (shaclSection) {
      shaclSection.style.display = 'none';
    }
  } else {
    // No selection
    nameEl.value = '';
    typeValueEl.textContent = 'No selection';
    const parentClassesGroup = qs('#parentClassesGroup');
    const abstractGroup = qs('#abstractGroup');
    const shaclSection = qs('#shaclConstraintsSection');
    if (parentClassesGroup) parentClassesGroup.style.display = 'none';
    if (abstractGroup) abstractGroup.style.display = 'none';
    if (shaclSection) shaclSection.style.display = 'none';
  }
}

/**
 * Get type display name
 */
function getTypeDisplayName(type) {
  const typeMap = {
    'class': 'Class',
    'dataProperty': 'Data Property',
    'objectProperty': 'Object Property',
    'note': 'Note',
    'model': 'Ontology Model'
  };
  return typeMap[type] || type;
}

/**
 * Setup drag and drop handlers for iconbar icons
 */
// Store drag-and-drop handlers to prevent duplicates
let dragDropHandlers = {
  dragstart: null,
  dragenter: null,
  dragover: null,
  drop: null
};

function setupDragAndDrop() {
  const container = qs('#cy');
  if (!container || !ontoState.cy) return;

  // Remove existing handlers if they exist
  if (dragDropHandlers.dragstart) {
    qsa('.onto-icon').forEach(icon => {
      icon.removeEventListener('dragstart', dragDropHandlers.dragstart);
    });
  }
  if (dragDropHandlers.dragenter) {
    container.removeEventListener('dragenter', dragDropHandlers.dragenter);
  }
  if (dragDropHandlers.dragover) {
    container.removeEventListener('dragover', dragDropHandlers.dragover);
  }
  if (dragDropHandlers.drop) {
    container.removeEventListener('drop', dragDropHandlers.drop);
  }

  // Create new handlers
  dragDropHandlers.dragstart = (ev) => {
    ev.dataTransfer.setData('text/onto-type', ev.target.closest('.onto-icon')?.getAttribute('data-onto-type') || 'class');
    try {
      ev.dataTransfer.effectAllowed = 'copy';
    } catch (_) {}
  };

  dragDropHandlers.dragenter = (ev) => {
    ev.preventDefault();
  };

  dragDropHandlers.dragover = (ev) => {
    ev.preventDefault();
    ontoState.isCanvasActive = true;
    try {
      ev.dataTransfer.dropEffect = 'copy';
    } catch (_) {}
  };

  dragDropHandlers.drop = async (ev) => {
    ev.preventDefault();
    ontoState.isCanvasActive = true;
    const ontoType = ev.dataTransfer.getData('text/onto-type') || 'class';
    const rect = container.getBoundingClientRect();
    const renderedPos = { x: ev.clientX - rect.left, y: ev.clientY - rect.top };
    const pan = ontoState.cy.pan();
    const zoom = ontoState.cy.zoom();
    const pos = { x: (renderedPos.x - pan.x) / zoom, y: (renderedPos.y - pan.y) / zoom };

    if (ontoType === 'class') {
      const label = `Class ${ontoState.nextId++}`;
      const id = await addClassNodeAt(label, pos);
      if (id) {
        ontoState.cy.$('#' + id).select();
        refreshOntologyTree();
      }
    } else if (ontoType === 'dataProperty') {
      const sel = ontoState.cy.nodes(':selected').filter(n => (n.data('type') || 'class') === 'class');
      if (sel.length !== 1) {
        alert('Please select a class first');
        return;
      }
      const prop = `Data Property ${Date.now() % 1000}`;
      const pid = `DP${Date.now()}`;
      ontoState.cy.add({
        group: 'nodes',
        data: { id: pid, label: prop, type: 'dataProperty' },
        position: pos
      });
      ontoState.cy.add({
        group: 'edges',
        data: {
          id: `edp${Date.now()}`,
          source: sel[0].id(),
          target: pid,
          predicate: prop,
          type: 'objectProperty'
        }
      });
      refreshOntologyTree();
    } else if (ontoType === 'note') {
      const nid = `Note${Date.now()}`;
      const text = `Note ${nid.slice(-4)}`;
      ontoState.cy.add({
        group: 'nodes',
        data: { id: nid, label: text, type: 'note' },
        position: pos,
        classes: 'note'
      });
      refreshOntologyTree();
    }
  };

  // Attach new handlers
  qsa('.onto-icon').forEach(icon => {
    icon.addEventListener('dragstart', dragDropHandlers.dragstart);
  });

  container.addEventListener('dragenter', dragDropHandlers.dragenter);
  container.addEventListener('dragover', dragDropHandlers.dragover);
  container.addEventListener('drop', dragDropHandlers.drop);
  
  // Set up context menu click handlers
  setupContextMenuHandlers();
}

/**
 * Add class node at position
 */
async function addClassNodeAt(label, pos) {
  ensureOntologyInitialized();
  if (!ontoState.cy) return null;
  
  const id = `C${Date.now()}`;
  ontoState.cy.add({
    group: 'nodes',
    data: { id, label, type: 'class' },
    position: pos
  });
  
  refreshOntologyTree();
  return id;
}

/**
 * Set up context menu click handlers
 */
function setupContextMenuHandlers() {
  // Context menu actions
  document.addEventListener('click', (e) => {
    const menu = qs('#ontoContextMenu');
    if (!menu) return;
    
    if (e.target === qs('#menuCancel')) {
      hideMenu();
      return;
    }
    
    if (e.target === qs('#menuAddRel')) {
      hideMenu();
      const id = menu.dataset.nodeId;
      if (!id) return;
      const node = ontoState.cy.$('#' + id)[0];
      if (!node) return;
      const t = menu.dataset.nodeType || 'class';
      clearConnectState();
      startConnectFrom(node);
      cmState.sourceType = t;
      return;
    }
    
    if (e.target === qs('#menuAddDataProp')) {
      hideMenu();
      const id = menu.dataset.nodeId;
      if (!id) return;
      const node = ontoState.cy.$('#' + id)[0];
      if (!node) return;
      
      // Add a default data property node near the class
      const pos = node.position();
      const pid = `DP${Date.now()}`;
      const label = `Data Property ${Date.now() % 1000}`;
      
      ontoState.cy.add({
        group: 'nodes',
        data: { id: pid, label, type: 'dataProperty' },
        position: { x: pos.x + 120, y: pos.y }
      });
      
      // Use objectProperty for the visual connector edge
      ontoState.cy.add({
        group: 'edges',
        data: {
          id: `edp${Date.now()}`,
          source: id,
          target: pid,
          predicate: label,
          type: 'objectProperty'
        }
      });
      
      console.log('✅ Data property created via context menu:', pid);
      refreshOntologyTree();
      persistOntologyToLocalStorage();
      return;
    }
  });
  
  // Hide menu on outside click
  document.addEventListener('click', (e) => {
    const menu = qs('#ontoContextMenu');
    if (menu && menu.style.display !== 'none' && !menu.contains(e.target)) {
      hideMenu();
    }
  });
}

/**
 * Show context menu at position
 */
function showMenuAt(x, y) {
  const m = qs('#ontoContextMenu');
  if (!m) return;
  m.style.left = x + 'px';
  m.style.top = y + 'px';
  m.style.display = 'block';
  cmState.visible = true;
}

/**
 * Hide context menu
 */
function hideMenu() {
  const m = qs('#ontoContextMenu');
  if (!m) return;
  m.style.display = 'none';
  cmState.visible = false;
}

/**
 * Hide edge context menu
 */
function hideEdgeMenu() {
  const m = qs('#edgeContextMenu');
  if (!m) return;
  m.style.display = 'none';
}

/**
 * Start connect mode from node
 */
function startConnectFrom(node) {
  cmState.sourceId = node.id();
  node.addClass('connect-source');
  console.log('🔗 Connect mode started from:', node.id());
}

/**
 * Clear connect state
 */
function clearConnectState() {
  if (cmState.sourceId && ontoState.cy) {
    const n = ontoState.cy.$('#' + cmState.sourceId);
    if (n.length) {
      n.removeClass('connect-source');
    }
  }
  cmState.sourceId = null;
  cmState.sourceType = null;
}

/**
 * Get storage key for graph IRI
 */
function storageKeyForGraph(iri) {
  const pid = (activeProject && (activeProject.id || activeProject.project_id)) ? (activeProject.id || activeProject.project_id) : 'default';
  return `onto_graph__${pid}__` + encodeURIComponent(iri);
}

/**
 * Persist ontology to local storage
 */
function persistOntologyToLocalStorage() {
  if (!ontoState.cy) return;
  if (ontoState.suspendAutosave) return;
  try {
    const nodes = ontoState.cy.nodes().filter(n => !n.hasClass('imported')).map(n => ({ data: n.data(), position: n.position() }));
    const edges = ontoState.cy.edges().filter(e => !e.hasClass('imported')).map(e => ({ data: e.data() }));
    if (activeOntologyIri) {
      const storageData = {
        nodes,
        edges,
        timestamp: Date.now(),
        source: 'local' // Mark that this data was saved locally
      };
      localStorage.setItem(storageKeyForGraph(activeOntologyIri), JSON.stringify(storageData));
      console.log('💾 Saved to local storage:', { nodeCount: nodes.length, edgeCount: edges.length });
    }
  } catch (err) {
    console.error('❌ Error persisting to local storage:', err);
  }
}

/**
 * Save graph to local storage
 */
function saveGraphToLocal(graphIri) {
  try {
    const nodes = ontoState.cy ? ontoState.cy.nodes().jsons() : [];
    const edges = ontoState.cy ? ontoState.cy.edges().jsons() : [];
    const storageData = {
      nodes,
      edges,
      timestamp: Date.now(),
      source: 'local' // Mark that this data was saved locally
    };
    localStorage.setItem(storageKeyForGraph(graphIri), JSON.stringify(storageData));
    console.log('💾 Saved graph to local storage:', graphIri);
  } catch (err) {
    console.error('❌ Error saving graph to local storage:', err);
  }
}

/**
 * Load graph from local storage
 */
function loadGraphFromLocal(graphIri) {
  try {
    const json = localStorage.getItem(storageKeyForGraph(graphIri));
    if (!json) {
      console.log('📦 No local storage data found for:', graphIri);
      return false;
    }
    const data = JSON.parse(json);
    if (!ontoState.cy) return false;
    
    console.log('📦 Loading from local storage:', { nodeCount: data.nodes?.length || 0, edgeCount: data.edges?.length || 0 });
    
    ontoState.cy.elements().remove();
    if (data.nodes && data.nodes.length > 0) {
      ontoState.cy.add(data.nodes);
    }
    if (data.edges && data.edges.length > 0) {
      ontoState.cy.add(data.edges);
    }
    
    // Ensure all loaded elements have attrs property
    ensureAttributesExist();
    // After loading, ensure nextId is advanced beyond existing ClassNNN
    recomputeNextId();
    requestAnimationFrame(() => { 
      if (ontoState.cy) {
        ontoState.cy.fit();
      }
    });
    return true;
  } catch (err) {
    console.error('❌ Error loading graph from local storage:', err);
    return false;
  }
}

/**
 * Ensure all elements have attrs property
 */
function ensureAttributesExist() {
  if (!ontoState.cy) return;
  // Ensure all nodes have an attrs property
  ontoState.cy.nodes().forEach(n => {
    if (!n.data('attrs')) {
      n.data('attrs', {});
    }
  });
  // Ensure all edges have an attrs property
  ontoState.cy.edges().forEach(e => {
    if (!e.data('attrs')) {
      e.data('attrs', {});
    }
  });
}

/**
 * Recompute next ID based on existing nodes
 */
function recomputeNextId() {
  try {
    if (!ontoState || !ontoState.cy) return;
    let maxNum = 0;
    ontoState.cy.nodes().forEach(n => {
      try {
        const nid = (n && typeof n.id === 'function') ? n.id() : '';
        const m = /^Class(\d+)$/.exec(String(nid || ''));
        if (m) {
          const num = parseInt(m[1], 10);
          if (!isNaN(num)) maxNum = Math.max(maxNum, num);
        }
      } catch (_) { }
    });
    ontoState.nextId = Math.max(1, maxNum + 1);
    console.log('🔢 Recomputed nextId:', ontoState.nextId);
  } catch (err) {
    console.error('❌ Error recomputing nextId:', err);
  }
}

/**
 * Perform delete operation
 */
function performDelete() {
  const ontologyWorkbench = qs('#wb-ontology');
  if (!ontologyWorkbench || !ontologyWorkbench.classList.contains('active')) {
    return false;
  }
  if (!ontoState.cy) return false;
  const sel = ontoState.cy.$(':selected');
  if (!sel || sel.length === 0) return false;
  
  console.log('🗑️ Deleting', sel.length, 'selected element(s)');
  ontoState.cy.remove(sel);
  refreshOntologyTree();
  persistOntologyToLocalStorage();
  return true;
}

/**
 * Handle delete key press
 */
function handleDeleteKey(e) {
  const key = e.key || e.code;
  const tgt = e.target;
  const isTyping = tgt && (tgt.tagName === 'INPUT' || tgt.tagName === 'TEXTAREA' || tgt.isContentEditable);
  const inline = qs('#ontoInlineEdit');
  const inlineVisible = inline ? (getComputedStyle(inline).display !== 'none') : false;
  
  if (isTyping || inlineVisible) return;
  
  if ((key === 'Delete' || key === 'Backspace') && ontoState.cy) {
    const ok = performDelete();
    if (ok) {
      e.preventDefault();
      e.stopPropagation();
    }
  }
}

/**
 * Set up delete handlers
 */
function setupDeleteHandlers() {
  // Keyboard delete handlers
  document.addEventListener('keydown', handleDeleteKey, false);
  window.addEventListener('keydown', handleDeleteKey, true);
  // Keyup fallback in case keydown is intercepted by browser/OS
  document.addEventListener('keyup', handleDeleteKey, false);
  
  // Toolbar delete button
  document.addEventListener('click', (e) => {
    if (e.target === qs('#ontoDeleteBtn')) {
      performDelete();
    }
  });
  
  console.log('✅ Delete handlers set up');
}

// Export for use in workbench manager
export { ensureOntologyInitialized, ontoState, refreshOntologyTree, updatePropertiesPanelFromSelection };

// Make available globally for compatibility during migration
window.ensureOntologyInitialized = ensureOntologyInitialized;
window.ontoState = ontoState;
window.switchWorkbenchTab = switchWorkbenchTab;
window.refreshOntologyTree = refreshOntologyTree;
window.updatePropertiesPanelFromSelection = updatePropertiesPanelFromSelection;
