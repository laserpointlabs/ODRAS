/**
 * Edge Menu Module
 *
 * Functions for showing and handling edge context menus.
 */

import { qs } from '../utils/ui-helpers.js';

/**
 * Show edge context menu at position
 * @param {number} x - X position
 * @param {number} y - Y position
 * @param {Function} hideNodeMenuFn - Function to hide node menu
 */
export function showEdgeMenuAt(x, y, hideNodeMenuFn) {
  const m = qs('#edgeContextMenu');
  if (!m) return;
  m.style.left = x + 'px';
  m.style.top = y + 'px';
  m.style.display = 'block';

  if (hideNodeMenuFn) {
    hideNodeMenuFn();
  }

  setTimeout(() => {
    const hideOnOutsideClick = (e) => {
      if (!m.contains(e.target)) {
        hideEdgeMenu();
        document.removeEventListener('click', hideOnOutsideClick);
      }
    };
    document.addEventListener('click', hideOnOutsideClick);
  }, 0);
}

/**
 * Hide edge context menu
 */
export function hideEdgeMenu() {
  const m = qs('#edgeContextMenu');
  if (!m) return;
  m.style.display = 'none';
}

/**
 * Show custom multiplicity dialog
 * @param {Object} edge - Cytoscape edge element
 * @param {Function} updateMultiplicityFn - Function to update multiplicity
 */
export function showCustomMultiplicityDialog(edge, updateMultiplicityFn) {
  // TODO: Extract from app.html - custom multiplicity input dialog
  // For now, use prompt as fallback
  const min = prompt('Minimum count (leave empty for no minimum):', edge.data('minCount') || '');
  const max = prompt('Maximum count (leave empty for no maximum):', edge.data('maxCount') || '');
  const minCount = min === '' || min === null ? null : parseInt(min);
  const maxCount = max === '' || max === null ? null : parseInt(max);

  if (!isNaN(minCount) || !isNaN(maxCount) || min === '' || max === '') {
    if (updateMultiplicityFn) {
      updateMultiplicityFn(edge, minCount, maxCount);
    }
  }
}
