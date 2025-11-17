/**
 * Tree Selection Module
 *
 * Functions for handling tree panel selection events.
 */

/**
 * Handle tree item selection
 * @param {string} elementId - Element ID
 * @param {string} elementType - Element type
 * @param {Object} cytoscapeInstance - Cytoscape instance
 * @param {Function} selectElementFn - Function to select element in canvas
 */
export function handleTreeSelection(elementId, elementType, cytoscapeInstance, selectElementFn) {
  if (selectElementFn) {
    selectElementFn(elementId, elementType);
  }
}
