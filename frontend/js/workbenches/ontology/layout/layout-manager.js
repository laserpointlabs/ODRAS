/**
 * Layout Manager Module
 *
 * Functions for managing Cytoscape layout algorithms.
 */

/**
 * Run advanced layout algorithm
 * @param {Object} cytoscapeInstance - Cytoscape instance
 * @param {Object} stateManager - State manager instance
 * @param {string} layoutType - Layout type ('cose', 'dagre', 'grid', 'breadthfirst', etc.)
 */
export function runAdvancedLayout(cytoscapeInstance, stateManager, layoutType) {
  if (!cytoscapeInstance) return;
  if (stateManager.get('layoutRunning')) return;

  stateManager.set('layoutRunning', true);

  const layoutOptions = {
    name: layoutType || 'cose',
    animate: true,
    animationDuration: 800
  };

  cytoscapeInstance.layout(layoutOptions).run();

  setTimeout(() => {
    stateManager.set('layoutRunning', false);
  }, 1000);
}

/**
 * Format multiplicity display string
 * @param {number|null} minCount - Minimum count
 * @param {number|null} maxCount - Maximum count
 * @returns {string} Multiplicity display string
 */
function formatMultiplicity(minCount, maxCount) {
  if (minCount === null && maxCount === null) return '';
  if (minCount === 1 && maxCount === 1) return ' (1)';
  if (minCount === 0 && maxCount === null) return ' (0..*)';
  if (minCount === 1 && maxCount === null) return ' (1..*)';
  if (minCount === 0 && maxCount === 1) return ' (0..1)';
  if (minCount !== null && maxCount !== null && minCount === maxCount) {
    return ` (${minCount})`;
  }
  if (minCount !== null && maxCount !== null) {
    return ` (${minCount}..${maxCount})`;
  }
  if (minCount !== null) {
    return ` (${minCount}..*)`;
  }
  if (maxCount !== null) {
    return ` (0..${maxCount})`;
  }
  return '';
}

/**
 * Update edge multiplicity
 * @param {Object} edge - Cytoscape edge element
 * @param {number|null} minCount - Minimum count
 * @param {number|null} maxCount - Maximum count
 * @param {Function} refreshTreeFn - Function to refresh tree
 * @param {Function} persistFn - Function to persist changes
 */
export function updateEdgeMultiplicity(edge, minCount, maxCount, refreshTreeFn, persistFn) {
  edge.data('minCount', minCount);
  edge.data('maxCount', maxCount);

  const multiplicity = formatMultiplicity(minCount, maxCount);
  edge.data('multiplicityDisplay', multiplicity.trim());

  if (refreshTreeFn) {
    refreshTreeFn();
  }
  if (persistFn) {
    persistFn();
  }
}
