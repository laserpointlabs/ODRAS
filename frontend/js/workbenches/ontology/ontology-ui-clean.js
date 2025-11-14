/**
 * Ontology Workbench UI Module (CLEAN VERSION)
 * 
 * This is a clean version with ONLY ontology canvas functionality.
 * NO project management, NO authentication code.
 * 
 * Extracted from app.html lines 7378-17348 (ontology workbench section)
 * 
 * Key Functions to Extract:
 * - ensureOntologyInitialized() - Cytoscape initialization
 * - loadGraphFromLocalOrAPI() - Graph loading
 * - convertOntologyToCytoscape() - Ontology conversion
 * - refreshOntologyTree() - Tree panel updates
 * - updatePropertiesPanelFromSelection() - Properties panel
 * - Menu handlers (Layout, View, Tools, Edit, File)
 * - Drag and drop handlers
 * - Context menu handlers
 * - Delete functionality
 * - Local storage persistence
 * - Individual Tables functionality
 * - CQ/MT functionality
 */

import { apiClient } from '../../core/api-client.js';
import { getAppState, updateAppState } from '../../core/state-manager.js';
import { subscribeToEvent, emitEvent } from '../../core/event-bus.js';
import { createOntologyWorkbenchHTML } from './ontology-ui-structure.js';

const ApiClient = apiClient;

// Helper functions
function qs(selector) {
  return document.querySelector(selector);
}

function qsa(selector) {
  return Array.from(document.querySelectorAll(selector));
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Ontology workbench state
export const ontoState = {
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

let activeOntologyIri = null;

// Initialize ontology workbench
export async function initializeOntologyWorkbench() {
  console.log('🔷 Initializing Ontology Workbench...');
  
  const workbenchContainer = qs('#wb-ontology');
  if (!workbenchContainer) {
    console.error('❌ Ontology workbench container not found');
    return;
  }

  // Create HTML structure dynamically
  workbenchContainer.innerHTML = createOntologyWorkbenchHTML();
  
  // Wait for DOM to be ready
  await new Promise(resolve => setTimeout(resolve, 50));
  
  // Initialize Cytoscape
  ensureOntologyInitialized();
  
  // Set up event listeners
  setupOntologyEventListeners();
  
  // Listen to project tree events
  subscribeToEvent('ontology:selected', handleOntologySelection);
  subscribeToEvent('ontology:element:selected', handleElementSelection);
  subscribeToEvent('ontology:edge:selected', handleEdgeSelection);
  subscribeToEvent('ontology:reset', handleOntologyReset);
  subscribeToEvent('ontology:renamed', handleOntologyRenamed);
  subscribeToEvent('ontology:deleted', handleOntologyDeleted);
  
  console.log('✅ Ontology Workbench initialized');
}

// Event handlers
async function handleOntologySelection(data) {
  const { iri, label, projectId } = data;
  activeOntologyIri = iri;
  updateOntoGraphLabel();
  
  // Load graph
  if (ontoState.cy) {
    ontoState.suspendAutosave = true;
    try {
      ontoState.cy.elements().remove();
    } catch (_) { }
    await loadGraphFromLocalOrAPI(iri);
    setTimeout(() => { ontoState.suspendAutosave = false; }, 50);
  }
  
  // Update properties panel
  updatePropertiesPanelFromSelection();
  
  // Refresh tree
  refreshOntologyTree();
}

function handleElementSelection(data) {
  const { nodeId, type } = data;
  if (nodeId && ontoState.cy) {
    ontoState.cy.$(':selected').unselect();
    const node = ontoState.cy.$(`#${CSS.escape(nodeId)}`);
    if (node.length > 0) {
      node.select();
      ontoState.cy.animate({
        center: { eles: node },
        zoom: Math.max(ontoState.cy.zoom(), 0.8)
      }, { duration: 300 });
      updatePropertiesPanelFromSelection();
    }
  }
}

function handleEdgeSelection(data) {
  const { edgeId } = data;
  if (edgeId && ontoState.cy) {
    ontoState.cy.$(':selected').unselect();
    const edge = ontoState.cy.$(`#${CSS.escape(edgeId)}`);
    if (edge.length > 0) {
      edge.select();
      ontoState.cy.animate({
        center: { eles: edge },
        zoom: Math.max(ontoState.cy.zoom(), 0.8)
      }, { duration: 300 });
      updatePropertiesPanelFromSelection();
    }
  }
}

function handleOntologyReset() {
  activeOntologyIri = null;
  updateOntoGraphLabel();
  if (ontoState.cy) {
    try {
      ontoState.cy.elements().remove();
    } catch (_) { }
  }
  refreshOntologyTree();
}

function handleOntologyRenamed(data) {
  const { graphIri, label } = data;
  if (activeOntologyIri === graphIri) {
    updateOntoGraphLabel();
    refreshOntologyTree();
  }
}

function handleOntologyDeleted(data) {
  const { graphIri } = data;
  if (activeOntologyIri === graphIri) {
    handleOntologyReset();
  }
}

// Update graph label display
function updateOntoGraphLabel() {
  const el = qs('#ontoGraphLabel');
  if (!el) return;
  if (activeOntologyIri) {
    el.textContent = 'Graph: ' + activeOntologyIri;
    el.title = activeOntologyIri;
  } else {
    el.textContent = 'No graph selected';
    el.title = '';
  }

  const empty = qs('#ontoEmpty');
  const layout = qs('#ontoLayoutSection');
  if (empty && layout) {
    const showEmpty = !activeOntologyIri;
    empty.style.display = showEmpty ? 'block' : 'none';
    layout.style.display = showEmpty ? 'none' : 'grid';
  }
}

// Placeholder functions - these need to be extracted from app.html
function ensureOntologyInitialized() {
  // TODO: Extract from app.html line 7378
  console.log('⚠️ ensureOntologyInitialized() needs to be extracted from app.html');
}

async function loadGraphFromLocalOrAPI(graphIri) {
  // TODO: Extract from app.html line 15965
  console.log('⚠️ loadGraphFromLocalOrAPI() needs to be extracted from app.html');
}

function convertOntologyToCytoscape(ontologyData) {
  // TODO: Extract from app.html line 15458
  console.log('⚠️ convertOntologyToCytoscape() needs to be extracted from app.html');
}

function refreshOntologyTree() {
  // TODO: Extract from app.html line 12920
  console.log('⚠️ refreshOntologyTree() needs to be extracted from app.html');
}

function updatePropertiesPanelFromSelection() {
  // TODO: Extract from app.html line 14205
  console.log('⚠️ updatePropertiesPanelFromSelection() needs to be extracted from app.html');
}

function setupOntologyEventListeners() {
  // TODO: Set up all menu handlers, drag/drop, context menus, etc.
  console.log('⚠️ setupOntologyEventListeners() needs to be implemented');
}

// Export for external access
export { activeOntologyIri };
