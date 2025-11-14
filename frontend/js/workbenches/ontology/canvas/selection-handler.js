/**
 * Selection Handler Module
 *
 * Functions for managing canvas selection and selection-related operations.
 */

import { qs } from '../utils/ui-helpers.js';

/**
 * Handle element selection from external source (e.g., tree panel)
 * @param {Object} cytoscapeInstance - Cytoscape instance
 * @param {string} nodeId - Node ID to select
 * @param {Function} updatePropertiesFn - Function to update properties panel
 */
export function selectElement(cytoscapeInstance, nodeId, updatePropertiesFn) {
  if (!cytoscapeInstance || !nodeId) return;

  cytoscapeInstance.$(':selected').unselect();
  const node = cytoscapeInstance.$(`#${CSS.escape(nodeId)}`);
  if (node.length > 0) {
    node.select();
    cytoscapeInstance.animate({
      center: { eles: node },
      zoom: Math.max(cytoscapeInstance.zoom(), 0.8)
    }, { duration: 300 });

    if (updatePropertiesFn) {
      updatePropertiesFn();
    }
  }
}

/**
 * Handle edge selection from external source
 * @param {Object} cytoscapeInstance - Cytoscape instance
 * @param {string} edgeId - Edge ID to select
 * @param {Function} updatePropertiesFn - Function to update properties panel
 */
export function selectEdge(cytoscapeInstance, edgeId, updatePropertiesFn) {
  if (!cytoscapeInstance || !edgeId) return;

  cytoscapeInstance.$(':selected').unselect();
  const edge = cytoscapeInstance.$(`#${CSS.escape(edgeId)}`);
  if (edge.length > 0) {
    edge.select();
    cytoscapeInstance.animate({
      center: { eles: edge },
      zoom: Math.max(cytoscapeInstance.zoom(), 0.8)
    }, { duration: 300 });

    if (updatePropertiesFn) {
      updatePropertiesFn();
    }
  }
}

/**
 * Clear all selections
 * @param {Object} cytoscapeInstance - Cytoscape instance
 */
export function clearSelection(cytoscapeInstance) {
  if (!cytoscapeInstance) return;
  cytoscapeInstance.$(':selected').unselect();
}

/**
 * Get currently selected elements
 * @param {Object} cytoscapeInstance - Cytoscape instance
 * @returns {Object} Selected elements collection
 */
export function getSelectedElements(cytoscapeInstance) {
  if (!cytoscapeInstance) return null;
  return cytoscapeInstance.$(':selected');
}

/**
 * Highlight tree item when canvas selection changes
 * @param {string} elementId - Element ID
 * @param {string} elementType - Element type ('node' or 'edge')
 */
export function highlightTreeItem(elementId, elementType) {
  // TODO: Extract from app.html line 16736
  // For now, just clear all highlights
  const rows = document.querySelectorAll('.onto-node-row');
  rows.forEach(row => row.classList.remove('selected'));
}
