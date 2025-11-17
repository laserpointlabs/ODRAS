/**
 * State Persistence Module
 *
 * Functions for persisting and loading workbench state.
 * Coordinates between localStorage and state manager.
 */

/**
 * Ensure all elements have attributes object
 * @param {Object} cytoscapeInstance - Cytoscape instance
 */
export function ensureAttributesExist(cytoscapeInstance) {
  if (!cytoscapeInstance) return;

  cytoscapeInstance.nodes().forEach(n => {
    if (!n.data('attrs')) {
      n.data('attrs', {});
    }
  });

  cytoscapeInstance.edges().forEach(e => {
    if (!e.data('attrs')) {
      e.data('attrs', {});
    }
  });
}

/**
 * Recompute next class ID from existing nodes
 * @param {Object} cytoscapeInstance - Cytoscape instance
 * @param {Object} stateManager - State manager instance
 */
export function recomputeNextId(cytoscapeInstance, stateManager) {
  try {
    if (!cytoscapeInstance || !stateManager) return;

    let maxNum = 0;
    cytoscapeInstance.nodes().forEach(n => {
      try {
        const nid = (n && typeof n.id === 'function') ? n.id() : '';
        const m = /^Class(\d+)$/.exec(String(nid || ''));
        if (m) {
          const num = parseInt(m[1], 10);
          if (!isNaN(num)) {
            maxNum = Math.max(maxNum, num);
          }
        }
      } catch (error) {
        // Ignore errors for individual nodes
      }
    });

    stateManager.set('nextId', Math.max(1, maxNum + 1));
  } catch (error) {
    console.error('Error recomputing next ID:', error);
  }
}

/**
 * Save workbench state to localStorage
 * @param {Object} stateManager - State manager instance
 * @param {string} graphIri - Graph IRI
 * @param {Object} stateAdapter - State adapter instance
 */
export function saveWorkbenchState(stateManager, graphIri, stateAdapter) {
  try {
    const state = stateManager.getState();
    const stateToSave = {
      connectMode: state.connectMode,
      currentPredicateType: state.currentPredicateType,
      snapToGrid: state.snapToGrid,
      gridSize: state.gridSize,
      visibilityState: state.visibilityState,
      collapsedImports: Array.from(state.collapsedImports || []),
      elementVisibility: state.elementVisibility,
      activeNamedView: state.activeNamedView
    };

    const appState = stateAdapter.getState ? stateAdapter.getState() : stateAdapter.get();
    const pid = appState?.activeProject?.projectId || appState?.activeProject?.id || 'default';
    const key = `onto_workbench_state__${pid}__${encodeURIComponent(graphIri)}`;
    localStorage.setItem(key, JSON.stringify(stateToSave));
  } catch (error) {
    console.error('Error saving workbench state:', error);
  }
}

/**
 * Load workbench state from localStorage
 * @param {Object} stateManager - State manager instance
 * @param {string} graphIri - Graph IRI
 * @param {Object} stateAdapter - State adapter instance
 */
export function loadWorkbenchState(stateManager, graphIri, stateAdapter) {
  try {
    const appState = stateAdapter.getState ? stateAdapter.getState() : stateAdapter.get();
    const pid = appState?.activeProject?.projectId || appState?.activeProject?.id || 'default';
    const key = `onto_workbench_state__${pid}__${encodeURIComponent(graphIri)}`;
    const json = localStorage.getItem(key);

    if (json) {
      const savedState = JSON.parse(json);
      stateManager.update({
        connectMode: savedState.connectMode || false,
        currentPredicateType: savedState.currentPredicateType || 'objectProperty',
        snapToGrid: savedState.snapToGrid !== undefined ? savedState.snapToGrid : true,
        gridSize: savedState.gridSize || 20,
        visibilityState: savedState.visibilityState || {
          classes: true,
          dataProperties: true,
          notes: true,
          edges: true,
          imported: true
        },
        collapsedImports: new Set(savedState.collapsedImports || []),
        elementVisibility: savedState.elementVisibility || {},
        activeNamedView: savedState.activeNamedView || null
      });
    }
  } catch (error) {
    console.error('Error loading workbench state:', error);
  }
}
