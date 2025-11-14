/**
 * Context Menu Module
 *
 * Functions for showing and handling node context menus.
 */

import { qs } from '../utils/ui-helpers.js';

/**
 * Context menu state
 */
class ContextMenuState {
  constructor() {
    this.visible = false;
    this.sourceId = null;
    this.sourceType = null;
  }
}

/**
 * Show context menu at position
 * @param {number} x - X position
 * @param {number} y - Y position
 * @param {Object} menuState - Context menu state object
 */
export function showMenuAt(x, y, menuState) {
  const m = qs('#ontoContextMenu');
  if (!m) return;
  m.style.left = x + 'px';
  m.style.top = y + 'px';
  m.style.display = 'block';
  menuState.visible = true;
}

/**
 * Hide context menu
 * @param {Object} menuState - Context menu state object
 */
export function hideMenu(menuState) {
  const m = qs('#ontoContextMenu');
  if (!m) return;
  m.style.display = 'none';
  menuState.visible = false;
}

/**
 * Start connection from node
 * @param {Object} node - Cytoscape node element
 * @param {Object} menuState - Context menu state object
 */
export function startConnectFrom(node, menuState) {
  menuState.sourceId = node.id();
  node.addClass('connect-source');
}

/**
 * Clear connection state
 * @param {Object} cytoscapeInstance - Cytoscape instance
 * @param {Object} menuState - Context menu state object
 */
export function clearConnectState(cytoscapeInstance, menuState) {
  if (menuState.sourceId && cytoscapeInstance) {
    const n = cytoscapeInstance.$('#' + menuState.sourceId);
    if (n) {
      n.removeClass('connect-source');
    }
  }
  menuState.sourceId = null;
}

/**
 * Create context menu state instance
 * @returns {ContextMenuState} Context menu state
 */
export function createContextMenuState() {
  return new ContextMenuState();
}
