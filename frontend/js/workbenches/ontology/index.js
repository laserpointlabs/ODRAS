/**
 * Ontology Workbench - Main Entry Point
 *
 * This is the public API for the ontology workbench.
 * It provides a clean interface with dependency injection for all adapters.
 */

import { OntologyStateManager } from './core/state-manager.js';
import { createOdrasApiAdapter } from './adapters/odras-api-adapter.js';
import { createOdrasStateAdapter } from './adapters/odras-state-adapter.js';
import { createOdrasEventsAdapter } from './adapters/odras-events-adapter.js';
import { createOntologyWorkbenchHTML } from './ontology-ui-structure.js';
import { initializeCytoscape } from './core/cytoscape-init.js';
import { setupEventHandlers } from './core/event-handlers.js';
import { createContextMenuState } from './menus/context-menu.js';
import { loadGraphFromLocalOrAPI } from './graph/graph-loader.js';
import { selectElement, selectEdge } from './canvas/selection-handler.js';
import { refreshOntologyTree } from './tree/tree-renderer.js';
import { updatePropertiesPanelFromSelection } from './properties/properties-panel.js';
import { persistOntologyToLocalStorage } from './storage/local-storage.js';
import { loadLayoutFromServer } from './layout/layout-persistence.js';
import { qs } from './utils/ui-helpers.js';

/**
 * Ontology Workbench Class
 *
 * Main class for the ontology workbench. Provides initialization,
 * lifecycle management, and public API.
 */
export class OntologyWorkbench {
  /**
   * Create a new OntologyWorkbench instance
   * @param {Object} config - Configuration object
   * @param {HTMLElement} config.container - Container element for the workbench
   * @param {Object} config.apiAdapter - API adapter instance
   * @param {Object} config.stateAdapter - State adapter instance
   * @param {Object} config.eventAdapter - Event adapter instance
   * @param {Object} config.options - Optional configuration
   */
  constructor(config) {
    const { container, apiAdapter, stateAdapter, eventAdapter, options = {} } = config;

    if (!container) {
      throw new Error('Container element is required');
    }
    if (!apiAdapter) {
      throw new Error('API adapter is required');
    }
    if (!stateAdapter) {
      throw new Error('State adapter is required');
    }
    if (!eventAdapter) {
      throw new Error('Event adapter is required');
    }

    this.container = container;
    this.apiAdapter = apiAdapter;
    this.stateAdapter = stateAdapter;
    this.eventAdapter = eventAdapter;
    this.options = {
      autosave: true,
      snapToGrid: true,
      gridSize: 20,
      ...options
    };

    // Internal state manager
    this.stateManager = new OntologyStateManager();

    // Event handlers map
    this.eventHandlers = new Map();

    // Context menu state
    this.menuState = createContextMenuState();

    // Cytoscape instance
    this.cytoscapeInstance = null;

    // Active ontology IRI
    this.activeOntologyIri = null;

    // Initialization flag
    this.initialized = false;
  }

  /**
   * Initialize the workbench
   * @returns {Promise<void>}
   */
  async initialize() {
    if (this.initialized) {
      console.warn('Ontology workbench already initialized');
      return;
    }

    console.log('🔷 Initializing Ontology Workbench...');

    // Create HTML structure
    this.container.innerHTML = createOntologyWorkbenchHTML();

    // Wait for DOM to be ready
    await new Promise(resolve => setTimeout(resolve, 50));

    // Initialize Cytoscape
    const container = qs('#cy', this.container);
    if (container) {
      this.cytoscapeInstance = initializeCytoscape(container, this.stateManager);

      // Set up all event handlers
      setupEventHandlers({
        cytoscapeInstance: this.cytoscapeInstance,
        container,
        stateManager: this.stateManager,
        menuState: this.menuState,
        refreshTreeFn: () => refreshOntologyTree(this.cytoscapeInstance),
        updatePropertiesFn: () => updatePropertiesPanelFromSelection(this.cytoscapeInstance),
        persistFn: () => this.persistGraph(),
        highlightTreeFn: (elementId, elementType) => {
          // TODO: Implement tree highlighting
        },
        updatePositionInputsFn: () => {
          // TODO: Implement position inputs update
        },
        updateCanvasVisibilityFn: () => {
          // TODO: Implement canvas visibility update
        },
        updateElementIriDisplayFn: () => {
          // TODO: Implement element IRI display update
        },
        activeOntologyIri: this.activeOntologyIri,
        apiAdapter: this.apiAdapter,
        workbenchContainer: this.container
      });
    }

    // Set up ODRAS event listeners
    this.setupEventListeners();

    this.initialized = true;
    console.log('✅ Ontology Workbench initialized');
  }

  /**
   * Set up event listeners for ODRAS events
   */
  setupEventListeners() {
    // Listen to project tree events
    this.eventAdapter.subscribe('ontology:selected', (data) => {
      this.handleOntologySelection(data);
    });

    this.eventAdapter.subscribe('ontology:element:selected', (data) => {
      this.handleElementSelection(data);
    });

    this.eventAdapter.subscribe('ontology:edge:selected', (data) => {
      this.handleEdgeSelection(data);
    });

    this.eventAdapter.subscribe('ontology:reset', () => {
      this.handleOntologyReset();
    });

    this.eventAdapter.subscribe('ontology:renamed', (data) => {
      this.handleOntologyRenamed(data);
    });

    this.eventAdapter.subscribe('ontology:deleted', (data) => {
      this.handleOntologyDeleted(data);
    });
  }

  /**
   * Handle ontology selection event
   * @param {Object} data - Event data
   */
  async handleOntologySelection(data) {
    const { iri, label, projectId } = data;
    this.activeOntologyIri = iri;
    this.updateGraphLabel();

    if (this.cytoscapeInstance) {
      this.stateManager.set('suspendAutosave', true);
      try {
        this.cytoscapeInstance.elements().remove();
      } catch (error) {
        // Ignore errors
      }
      await this.loadOntology(iri);
      setTimeout(() => {
        this.stateManager.set('suspendAutosave', false);
      }, 50);
    }

    updatePropertiesPanelFromSelection(this.cytoscapeInstance);
    refreshOntologyTree(this.cytoscapeInstance);
  }

  /**
   * Handle element selection event
   * @param {Object} data - Event data
   */
  handleElementSelection(data) {
    const { nodeId, type } = data;
    if (nodeId && this.cytoscapeInstance) {
      selectElement(this.cytoscapeInstance, nodeId, () => {
        updatePropertiesPanelFromSelection(this.cytoscapeInstance);
      });
    }
  }

  /**
   * Handle edge selection event
   * @param {Object} data - Event data
   */
  handleEdgeSelection(data) {
    const { edgeId } = data;
    if (edgeId && this.cytoscapeInstance) {
      selectEdge(this.cytoscapeInstance, edgeId, () => {
        updatePropertiesPanelFromSelection(this.cytoscapeInstance);
      });
    }
  }

  /**
   * Handle ontology reset event
   */
  handleOntologyReset() {
    this.activeOntologyIri = null;
    this.updateGraphLabel();
    if (this.cytoscapeInstance) {
      try {
        this.cytoscapeInstance.elements().remove();
      } catch (error) {
        // Ignore errors
      }
    }
    refreshOntologyTree(this.cytoscapeInstance);
  }

  /**
   * Handle ontology renamed event
   * @param {Object} data - Event data
   */
  handleOntologyRenamed(data) {
    const { graphIri, label } = data;
    if (this.activeOntologyIri === graphIri) {
      this.updateGraphLabel();
      refreshOntologyTree(this.cytoscapeInstance);
    }
  }

  /**
   * Handle ontology deleted event
   * @param {Object} data - Event data
   */
  handleOntologyDeleted(data) {
    const { graphIri } = data;
    if (this.activeOntologyIri === graphIri) {
      this.handleOntologyReset();
    }
  }

  /**
   * Load an ontology
   * @param {string} iri - Ontology IRI
   * @returns {Promise<void>}
   */
  async loadOntology(iri) {
    if (!this.cytoscapeInstance) return;

    await loadGraphFromLocalOrAPI(
      iri,
      this.cytoscapeInstance,
      this.stateManager,
      this.stateAdapter,
      this.apiAdapter,
      (graphIri) => loadLayoutFromServer(graphIri, this.cytoscapeInstance, this.apiAdapter, this.stateAdapter),
      () => {
        // TODO: Implement canvas visibility update
      },
      () => refreshOntologyTree(this.cytoscapeInstance)
    );
  }

  /**
   * Save current ontology
   * @returns {Promise<void>}
   */
  async saveOntology() {
    this.persistGraph();
  }

  /**
   * Persist graph to localStorage
   */
  persistGraph() {
    if (!this.cytoscapeInstance || !this.activeOntologyIri) return;
    persistOntologyToLocalStorage(
      this.cytoscapeInstance,
      this.activeOntologyIri,
      this.stateAdapter,
      this.stateManager.get('suspendAutosave')
    );
  }

  /**
   * Update graph label display
   */
  updateGraphLabel() {
    const el = qs('#ontoGraphLabel', this.container);
    if (!el) return;
    if (this.activeOntologyIri) {
      el.textContent = 'Graph: ' + this.activeOntologyIri;
      el.title = this.activeOntologyIri;
    } else {
      el.textContent = 'No graph selected';
      el.title = '';
    }

    const empty = qs('#ontoEmpty', this.container);
    const layout = qs('#ontoLayoutSection', this.container);
    if (empty && layout) {
      const showEmpty = !this.activeOntologyIri;
      empty.style.display = showEmpty ? 'block' : 'none';
      layout.style.display = showEmpty ? 'none' : 'grid';
    }
  }

  /**
   * Subscribe to workbench events
   * @param {string} event - Event name
   * @param {Function} handler - Event handler
   * @returns {Function} Unsubscribe function
   */
  on(event, handler) {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set());
    }
    this.eventHandlers.get(event).add(handler);

    return () => {
      const handlers = this.eventHandlers.get(event);
      if (handlers) {
        handlers.delete(handler);
        if (handlers.size === 0) {
          this.eventHandlers.delete(event);
        }
      }
    };
  }

  /**
   * Unsubscribe from workbench events
   * @param {string} event - Event name
   * @param {Function} handler - Event handler (optional, if not provided removes all handlers for event)
   */
  off(event, handler) {
    if (!handler) {
      this.eventHandlers.delete(event);
    } else {
      const handlers = this.eventHandlers.get(event);
      if (handlers) {
        handlers.delete(handler);
        if (handlers.size === 0) {
          this.eventHandlers.delete(event);
        }
      }
    }
  }

  /**
   * Emit a workbench event
   * @param {string} event - Event name
   * @param {*} data - Event data
   */
  emit(event, data) {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(data);
        } catch (error) {
          console.error(`Error in event handler for ${event}:`, error);
        }
      });
    }
  }

  /**
   * Destroy the workbench instance
   */
  destroy() {
    // Clean up event listeners
    this.eventAdapter.unsubscribeAll();

    // Clear event handlers
    this.eventHandlers.clear();

    // Destroy Cytoscape instance
    if (this.cytoscapeInstance) {
      try {
        this.cytoscapeInstance.destroy();
      } catch (error) {
        // Ignore errors
      }
      this.cytoscapeInstance = null;
    }

    // Reset state
    this.stateManager.reset();

    // Clear container
    this.container.innerHTML = '';

    this.activeOntologyIri = null;
    this.initialized = false;
    console.log('✅ Ontology Workbench destroyed');
  }

  /**
   * Get internal state manager (for advanced use cases)
   * @returns {OntologyStateManager} State manager instance
   */
  getStateManager() {
    return this.stateManager;
  }
}

/**
 * Factory function to create an ontology workbench instance
 * @param {Object} config - Configuration object
 * @returns {OntologyWorkbench} Workbench instance
 */
export function createOntologyWorkbench(config) {
  return new OntologyWorkbench(config);
}

/**
 * Factory function to create ODRAS adapters (convenience function)
 * @param {Object} odrasModules - ODRAS module instances
 * @param {Object} odrasModules.apiClient - ODRAS API client
 * @param {Function} odrasModules.getAppState - Get app state function
 * @param {Function} odrasModules.updateAppState - Update app state function
 * @param {Function} odrasModules.subscribeToEvent - Subscribe to event function
 * @param {Function} odrasModules.emitEvent - Emit event function
 * @returns {Object} Adapter instances
 */
export function createOdrasAdapters(odrasModules) {
  const { apiClient, getAppState, updateAppState, subscribeToEvent, emitEvent } = odrasModules;

  return {
    apiAdapter: createOdrasApiAdapter(apiClient),
    stateAdapter: createOdrasStateAdapter(getAppState, updateAppState),
    eventAdapter: createOdrasEventsAdapter(subscribeToEvent, emitEvent)
  };
}
