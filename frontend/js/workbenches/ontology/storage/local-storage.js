/**
 * Local Storage Module
 *
 * Functions for managing localStorage operations for the ontology workbench.
 * Uses adapter pattern to get project context from state adapter.
 */

/**
 * Generate storage key for a graph
 * @param {string} iri - Graph IRI
 * @param {Object} stateAdapter - State adapter instance
 * @returns {string} Storage key
 */
export function storageKeyForGraph(iri, stateAdapter) {
  try {
    const state = stateAdapter.getState ? stateAdapter.getState() : stateAdapter.get();
    const pid = state?.activeProject?.projectId || state?.activeProject?.id || 'default';
    return `onto_graph__${pid}__${encodeURIComponent(iri)}`;
  } catch (error) {
    console.error('Error getting storage key:', error);
    return `onto_graph__default__${encodeURIComponent(iri)}`;
  }
}

/**
 * Persist ontology graph to localStorage
 * @param {Object} cytoscapeInstance - Cytoscape instance
 * @param {string} activeOntologyIri - Active ontology IRI
 * @param {Object} stateAdapter - State adapter instance
 * @param {boolean} suspendAutosave - Whether autosave is suspended
 */
export function persistOntologyToLocalStorage(cytoscapeInstance, activeOntologyIri, stateAdapter, suspendAutosave = false) {
  if (!cytoscapeInstance) return;
  if (suspendAutosave) return;
  if (!activeOntologyIri) return;

  try {
    const nodes = cytoscapeInstance.nodes()
      .filter(n => !n.hasClass('imported'))
      .map(n => ({ data: n.data(), position: n.position() }));

    const edges = cytoscapeInstance.edges()
      .filter(e => !e.hasClass('imported'))
      .map(e => ({ data: e.data() }));

    const storageData = {
      nodes,
      edges,
      timestamp: Date.now(),
      source: 'local'
    };

    const key = storageKeyForGraph(activeOntologyIri, stateAdapter);
    localStorage.setItem(key, JSON.stringify(storageData));
  } catch (error) {
    console.error('Error persisting ontology to localStorage:', error);
  }
}

/**
 * Load ontology graph from localStorage
 * @param {string} iri - Graph IRI
 * @param {Object} stateAdapter - State adapter instance
 * @returns {Object|null} Graph data or null if not found
 */
export function loadOntologyFromLocalStorage(iri, stateAdapter) {
  try {
    const key = storageKeyForGraph(iri, stateAdapter);
    const json = localStorage.getItem(key);
    if (!json) return null;

    const data = JSON.parse(json);
    if (data && (data.nodes || data.edges) && data.nodes?.length > 0) {
      return data;
    }
    return null;
  } catch (error) {
    console.error('Error loading ontology from localStorage:', error);
    return null;
  }
}

/**
 * Load collapsed imports state
 * @param {string} baseIri - Base ontology IRI
 * @param {Object} stateAdapter - State adapter instance
 * @returns {Set} Set of collapsed import IRIs
 */
export function loadCollapsedImports(baseIri, stateAdapter) {
  try {
    const state = stateAdapter.getState ? stateAdapter.getState() : stateAdapter.get();
    const pid = state?.activeProject?.projectId || state?.activeProject?.id || 'default';
    const key = `onto_collapsed_imports__${pid}__${encodeURIComponent(baseIri)}`;
    const json = localStorage.getItem(key);
    if (json) {
      const array = JSON.parse(json);
      return new Set(array || []);
    }
  } catch (error) {
    console.error('Error loading collapsed imports:', error);
  }
  return new Set();
}

/**
 * Save collapsed imports state
 * @param {string} baseIri - Base ontology IRI
 * @param {Set} collapsedImports - Set of collapsed import IRIs
 * @param {Object} stateAdapter - State adapter instance
 */
export function saveCollapsedImports(baseIri, collapsedImports, stateAdapter) {
  try {
    const state = stateAdapter.getState ? stateAdapter.getState() : stateAdapter.get();
    const pid = state?.activeProject?.projectId || state?.activeProject?.id || 'default';
    const key = `onto_collapsed_imports__${pid}__${encodeURIComponent(baseIri)}`;
    const array = Array.from(collapsedImports || []);
    localStorage.setItem(key, JSON.stringify(array));
  } catch (error) {
    console.error('Error saving collapsed imports:', error);
  }
}

/**
 * Load visibility state
 * @param {string} baseIri - Base ontology IRI
 * @param {Object} stateAdapter - State adapter instance
 * @returns {Object} Visibility state object
 */
export function loadVisibilityState(baseIri, stateAdapter) {
  try {
    const state = stateAdapter.getState ? stateAdapter.getState() : stateAdapter.get();
    const pid = state?.activeProject?.projectId || state?.activeProject?.id || 'default';
    const key = `onto_visibility_state__${pid}__${encodeURIComponent(baseIri)}`;
    const json = localStorage.getItem(key);
    if (json) {
      return JSON.parse(json);
    }
  } catch (error) {
    console.error('Error loading visibility state:', error);
  }
  return {
    classes: true,
    dataProperties: true,
    notes: true,
    edges: true,
    imported: true
  };
}

/**
 * Save visibility state
 * @param {string} baseIri - Base ontology IRI
 * @param {Object} visibilityState - Visibility state object
 * @param {Object} stateAdapter - State adapter instance
 */
export function saveVisibilityState(baseIri, visibilityState, stateAdapter) {
  try {
    const state = stateAdapter.getState ? stateAdapter.getState() : stateAdapter.get();
    const pid = state?.activeProject?.projectId || state?.activeProject?.id || 'default';
    const key = `onto_visibility_state__${pid}__${encodeURIComponent(baseIri)}`;
    localStorage.setItem(key, JSON.stringify(visibilityState));
  } catch (error) {
    console.error('Error saving visibility state:', error);
  }
}

/**
 * Load element visibility map
 * @param {string} baseIri - Base ontology IRI
 * @param {Object} stateAdapter - State adapter instance
 * @returns {Object} Element visibility map
 */
export function loadElementVisibility(baseIri, stateAdapter) {
  try {
    const state = stateAdapter.getState ? stateAdapter.getState() : stateAdapter.get();
    const pid = state?.activeProject?.projectId || state?.activeProject?.id || 'default';
    const key = `onto_element_visibility__${pid}__${encodeURIComponent(baseIri)}`;
    const json = localStorage.getItem(key);
    if (json) {
      return JSON.parse(json);
    }
  } catch (error) {
    console.error('Error loading element visibility:', error);
  }
  return {};
}

/**
 * Save element visibility map
 * @param {string} baseIri - Base ontology IRI
 * @param {Object} elementVisibility - Element visibility map
 * @param {Object} stateAdapter - State adapter instance
 */
export function saveElementVisibility(baseIri, elementVisibility, stateAdapter) {
  try {
    const state = stateAdapter.getState ? stateAdapter.getState() : stateAdapter.get();
    const pid = state?.activeProject?.projectId || state?.activeProject?.id || 'default';
    const key = `onto_element_visibility__${pid}__${encodeURIComponent(baseIri)}`;
    localStorage.setItem(key, JSON.stringify(elementVisibility));
  } catch (error) {
    console.error('Error saving element visibility:', error);
  }
}

/**
 * Load layout data from localStorage
 * @param {string} graphIri - Graph IRI
 * @param {Object} stateAdapter - State adapter instance
 * @returns {Object|null} Layout data or null
 */
export function loadLayoutFromLocalStorage(graphIri, stateAdapter) {
  try {
    const key = `onto_layout_${encodeURIComponent(graphIri)}`;
    const json = localStorage.getItem(key);
    if (json) {
      const layoutData = JSON.parse(json);
      // Only use layout if it's less than 30 seconds old
      if (layoutData.timestamp && (Date.now() - layoutData.timestamp) < 30000) {
        return layoutData;
      }
    }
  } catch (error) {
    console.error('Error loading layout from localStorage:', error);
  }
  return null;
}

/**
 * Save layout data to localStorage
 * @param {string} graphIri - Graph IRI
 * @param {Object} layoutData - Layout data (nodes, zoom, pan)
 * @param {Object} stateAdapter - State adapter instance
 */
export function saveLayoutToLocalStorage(graphIri, layoutData, stateAdapter) {
  try {
    const key = `onto_layout_${encodeURIComponent(graphIri)}`;
    const data = {
      ...layoutData,
      timestamp: Date.now()
    };
    localStorage.setItem(key, JSON.stringify(data));
  } catch (error) {
    console.error('Error saving layout to localStorage:', error);
  }
}

/**
 * Load IRI mapping
 * @param {string} graphIri - Graph IRI
 * @param {Object} stateAdapter - State adapter instance
 * @returns {Object} IRI mapping object
 */
export function loadIriMap(graphIri, stateAdapter) {
  try {
    const state = stateAdapter.getState ? stateAdapter.getState() : stateAdapter.get();
    const pid = state?.activeProject?.projectId || state?.activeProject?.id || 'default';
    const key = `onto_iri_map__${pid}__${encodeURIComponent(graphIri)}`;
    const json = localStorage.getItem(key);
    if (json) {
      return JSON.parse(json);
    }
  } catch (error) {
    console.error('Error loading IRI map:', error);
  }
  return {};
}

/**
 * Save IRI mapping
 * @param {string} graphIri - Graph IRI
 * @param {Object} iriMap - IRI mapping object
 * @param {Object} stateAdapter - State adapter instance
 */
export function saveIriMap(graphIri, iriMap, stateAdapter) {
  try {
    const state = stateAdapter.getState ? stateAdapter.getState() : stateAdapter.get();
    const pid = state?.activeProject?.projectId || state?.activeProject?.id || 'default';
    const key = `onto_iri_map__${pid}__${encodeURIComponent(graphIri)}`;
    localStorage.setItem(key, JSON.stringify(iriMap));
  } catch (error) {
    console.error('Error saving IRI map:', error);
  }
}
