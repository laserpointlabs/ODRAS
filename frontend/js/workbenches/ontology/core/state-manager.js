/**
 * Ontology Workbench State Manager
 *
 * Internal state management for the ontology workbench.
 * This is isolated from ODRAS state and manages workbench-specific state.
 */

/**
 * Creates the initial ontology workbench state
 * @returns {Object} Initial state object
 */
export function createOntologyState() {
  return {
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
    beforeViewState: null,
    activeOntologyIri: null
  };
}

/**
 * State manager class for ontology workbench
 */
export class OntologyStateManager {
  constructor() {
    this.state = createOntologyState();
    this.listeners = new Set();
  }

  /**
   * Get current state
   * @returns {Object} Current state
   */
  getState() {
    return { ...this.state };
  }

  /**
   * Get a specific state property
   * @param {string} key - State key
   * @returns {*} State value
   */
  get(key) {
    return this.state[key];
  }

  /**
   * Set a state property
   * @param {string} key - State key
   * @param {*} value - State value
   */
  set(key, value) {
    this.state[key] = value;
    this.notifyListeners();
  }

  /**
   * Update multiple state properties
   * @param {Object} updates - Partial state updates
   */
  update(updates) {
    Object.assign(this.state, updates);
    this.notifyListeners();
  }

  /**
   * Subscribe to state changes
   * @param {Function} callback - Callback function
   * @returns {Function} Unsubscribe function
   */
  subscribe(callback) {
    this.listeners.add(callback);
    return () => {
      this.listeners.delete(callback);
    };
  }

  /**
   * Notify all listeners of state changes
   */
  notifyListeners() {
    const state = this.getState();
    this.listeners.forEach(listener => {
      try {
        listener(state);
      } catch (error) {
        console.error('Error in state listener:', error);
      }
    });
  }

  /**
   * Reset state to initial values
   */
  reset() {
    this.state = createOntologyState();
    this.notifyListeners();
  }
}
