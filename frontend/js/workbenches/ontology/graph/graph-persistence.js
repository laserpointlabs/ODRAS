/**
 * Graph Persistence Module
 *
 * Functions for persisting and loading graph data.
 * Coordinates between localStorage and API.
 */

import * as localStorage from '../storage/local-storage.js';
import { ensureAttributesExist, recomputeNextId } from '../storage/state-persistence.js';

/**
 * Save graph data to localStorage
 * @param {Object} cytoscapeInstance - Cytoscape instance
 * @param {string} graphIri - Graph IRI
 * @param {Object} stateAdapter - State adapter instance
 * @param {boolean} suspendAutosave - Whether autosave is suspended
 */
export function saveGraphToLocalStorage(cytoscapeInstance, graphIri, stateAdapter, suspendAutosave = false) {
  localStorage.persistOntologyToLocalStorage(cytoscapeInstance, graphIri, stateAdapter, suspendAutosave);
}

/**
 * Load graph data from localStorage
 * @param {string} graphIri - Graph IRI
 * @param {Object} stateAdapter - State adapter instance
 * @returns {Object|null} Graph data or null
 */
export function loadGraphFromLocalStorage(graphIri, stateAdapter) {
  return localStorage.loadOntologyFromLocalStorage(graphIri, stateAdapter);
}

/**
 * Apply graph data to Cytoscape instance
 * @param {Object} cytoscapeInstance - Cytoscape instance
 * @param {Object} graphData - Graph data with nodes and edges
 * @param {Object} stateManager - State manager instance
 */
export function applyGraphToCytoscape(cytoscapeInstance, graphData, stateManager) {
  if (!cytoscapeInstance || !graphData) return;

  try {
    cytoscapeInstance.elements().remove();
    if (graphData.nodes && graphData.nodes.length > 0) {
      cytoscapeInstance.add(graphData.nodes);
    }
    if (graphData.edges && graphData.edges.length > 0) {
      cytoscapeInstance.add(graphData.edges);
    }

    ensureAttributesExist(cytoscapeInstance);
    recomputeNextId(cytoscapeInstance, stateManager);
  } catch (error) {
    console.error('Error applying graph to Cytoscape:', error);
  }
}
