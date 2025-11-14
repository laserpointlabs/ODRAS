/**
 * Drag and Drop Module
 *
 * Functions for handling drag-and-drop operations from tool icons to canvas.
 */

import { addCreationMetadata } from '../utils/metadata-helpers.js';
import { snapToGrid } from '../utils/ui-helpers.js';

/**
 * Set up drag-and-drop handlers for tool icons
 * @param {NodeList|Array} iconElements - Icon elements to make draggable
 */
export function setupDragStartHandlers(iconElements) {
  Array.from(iconElements).forEach(icon => {
    icon.addEventListener('dragstart', (ev) => {
      ev.dataTransfer.setData('text/onto-type', icon.getAttribute('data-onto-type') || 'class');
      try {
        ev.dataTransfer.effectAllowed = 'copy';
      } catch (error) {
        // Ignore errors
      }
    });
  });
}

/**
 * Set up drop handlers for canvas container
 * @param {HTMLElement} container - Canvas container element
 * @param {Object} cytoscapeInstance - Cytoscape instance
 * @param {Object} stateManager - State manager instance
 * @param {Function} addClassNodeFn - Function to add class node
 * @param {Function} setConnectModeFn - Function to set connect mode
 * @param {Function} addDataPropertyFn - Function to add data property
 * @param {Function} addNoteFn - Function to add note
 * @param {Function} refreshTreeFn - Function to refresh tree
 * @param {Function} persistFn - Function to persist changes
 * @param {Function} getCurrentUsernameFn - Function to get current username
 */
export function setupDropHandlers(
  container,
  cytoscapeInstance,
  stateManager,
  addClassNodeFn,
  setConnectModeFn,
  addDataPropertyFn,
  addNoteFn,
  refreshTreeFn,
  persistFn,
  getCurrentUsernameFn
) {
  container.addEventListener('dragenter', (ev) => {
    ev.preventDefault();
  });

  container.addEventListener('dragover', (ev) => {
    ev.preventDefault();
    stateManager.set('isCanvasActive', true);
    try {
      ev.dataTransfer.dropEffect = 'copy';
    } catch (error) {
      // Ignore errors
    }
  });

  container.addEventListener('drop', async (ev) => {
    ev.preventDefault();
    stateManager.set('isCanvasActive', true);

    const ontoType = ev.dataTransfer.getData('text/onto-type') || 'class';
    const rect = container.getBoundingClientRect();
    const renderedPos = { x: ev.clientX - rect.left, y: ev.clientY - rect.top };
    const pan = cytoscapeInstance.pan();
    const zoom = cytoscapeInstance.zoom();
    const pos = {
      x: (renderedPos.x - pan.x) / zoom,
      y: (renderedPos.y - pan.y) / zoom
    };

    if (ontoType === 'class') {
      const nextId = stateManager.get('nextId');
      const label = `Class ${nextId}`;
      const id = await addClassNodeFn(label, pos);
      if (id) {
        cytoscapeInstance.$(`#${id}`).select();
      }
    } else if (ontoType === 'objectProperty') {
      stateManager.set('currentPredicateType', 'objectProperty');
      if (setConnectModeFn) {
        setConnectModeFn(true);
      }
    } else if (ontoType === 'dataProperty') {
      const sel = cytoscapeInstance.nodes(':selected').filter(n => (n.data('type') || 'class') === 'class');
      if (sel.length !== 1) {
        return;
      }
      const prop = `Data Property ${Date.now() % 1000}`;
      const pid = addDataPropertyFn(prop, pos, sel[0].id());
      if (refreshTreeFn) {
        refreshTreeFn();
      }
    } else if (ontoType === 'note') {
      const nid = `Note${Date.now()}`;
      const text = `Note ${nid.slice(-4)}`;
      const sel = cytoscapeInstance.nodes(':selected').filter(n => (n.data('type') || 'class') === 'class');
      const targetClassId = sel && sel.length === 1 ? sel[0].id() : null;
      addNoteFn(text, pos, targetClassId, getCurrentUsernameFn);
      if (refreshTreeFn) {
        refreshTreeFn();
      }
      if (persistFn) {
        persistFn();
      }
    }

    if (persistFn) {
      persistFn();
    }
  });
}
