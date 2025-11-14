/**
 * Layout Persistence Module
 *
 * Functions for loading and saving layout data from server and localStorage.
 */

import * as localStorage from '../storage/local-storage.js';

/**
 * Load layout from server
 * @param {string} graphIri - Graph IRI
 * @param {Object} cytoscapeInstance - Cytoscape instance
 * @param {Object} apiAdapter - API adapter instance
 * @param {Object} stateAdapter - State adapter instance
 * @returns {Promise<boolean>} True if layout was loaded
 */
export async function loadLayoutFromServer(graphIri, cytoscapeInstance, apiAdapter, stateAdapter) {
  try {
    // First try localStorage
    const localLayout = localStorage.loadLayoutFromLocalStorage(graphIri, stateAdapter);
    if (localLayout && localLayout.nodes) {
      localLayout.nodes.forEach(nodeLayout => {
        const node = cytoscapeInstance.$(`#${nodeLayout.iri}`);
        if (node.length > 0) {
          node.position({ x: nodeLayout.x, y: nodeLayout.y });
        }
      });
      if (localLayout.zoom && localLayout.pan) {
        cytoscapeInstance.zoom(localLayout.zoom);
        cytoscapeInstance.pan(localLayout.pan);
      }
      return true;
    }

    // Try server
    const response = await apiAdapter.get(`/api/ontology/layout?graph=${encodeURIComponent(graphIri)}`);
    if (response.ok && response.data) {
      const layoutData = response.data;
      if (layoutData.nodes && layoutData.nodes.length > 0) {
        layoutData.nodes.forEach(nodeLayout => {
          const node = cytoscapeInstance.$(`#${nodeLayout.iri}`);
          if (node.length > 0) {
            node.position({ x: nodeLayout.x, y: nodeLayout.y });
          }
        });
        if (layoutData.zoom && layoutData.pan) {
          cytoscapeInstance.zoom(layoutData.zoom);
          cytoscapeInstance.pan(layoutData.pan);
        }
        return true;
      }
    }
  } catch (error) {
    console.warn('Error loading layout from server:', error);
  }
  return false;
}

/**
 * Save layout to server
 * @param {string} graphIri - Graph IRI
 * @param {Object} cytoscapeInstance - Cytoscape instance
 * @param {Object} apiAdapter - API adapter instance
 * @param {Object} stateAdapter - State adapter instance
 * @returns {Promise<void>}
 */
export async function saveLayoutToServer(graphIri, cytoscapeInstance, apiAdapter, stateAdapter) {
  try {
    const nodes = cytoscapeInstance.nodes()
      .filter(n => !n.hasClass('imported'))
      .map(n => ({
        iri: n.data('id'),
        x: n.position('x'),
        y: n.position('y')
      }));

    const pan = cytoscapeInstance.pan();
    const zoom = cytoscapeInstance.zoom();

    const layoutData = { nodes, zoom, pan };

    // Save to localStorage first
    localStorage.saveLayoutToLocalStorage(graphIri, layoutData, stateAdapter);

    // TODO: Save to server when endpoint is available
    // await apiAdapter.post(`/api/ontology/layout?graph=${encodeURIComponent(graphIri)}`, layoutData);
    console.log('💾 Layout save to server not yet implemented');
  } catch (error) {
    console.error('Error saving layout to server:', error);
  }
}
