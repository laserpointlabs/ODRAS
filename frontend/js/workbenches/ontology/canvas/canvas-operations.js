/**
 * Canvas Operations Module
 *
 * Functions for adding, deleting, and modifying canvas elements.
 */

import { addCreationMetadata } from '../utils/metadata-helpers.js';
import { qs } from '../utils/ui-helpers.js';

/**
 * Add a class node at specified position
 * @param {Object} cytoscapeInstance - Cytoscape instance
 * @param {Object} stateManager - State manager instance
 * @param {string} label - Class label
 * @param {Object} position - Position object with x and y
 * @param {string} activeOntologyIri - Active ontology IRI
 * @param {Object} apiAdapter - API adapter instance
 * @returns {string} Node ID
 */
export async function addClassNodeAt(cytoscapeInstance, stateManager, label, position, activeOntologyIri, apiAdapter) {
  if (!cytoscapeInstance) return null;

  const nextId = stateManager.get('nextId');
  const id = `Class${nextId}`;
  stateManager.set('nextId', nextId + 1);

  const attrs = addCreationMetadata({});
  cytoscapeInstance.add({
    group: 'nodes',
    data: { id, label, type: 'class', attrs },
    position
  });

  // Call backend API to persist to Fuseki
  if (activeOntologyIri && apiAdapter) {
    try {
      const url = `/api/ontology/classes?graph=${encodeURIComponent(activeOntologyIri)}`;
      const response = await apiAdapter.post(url, {
        name: id,
        label: label,
        comment: ''
      });
      if (response.ok) {
        console.log('✅ Class created in Fuseki:', label);
      }
    } catch (error) {
      console.error('❌ Error creating class in Fuseki:', error);
    }
  }

  return id;
}

/**
 * Add a data property node
 * @param {Object} cytoscapeInstance - Cytoscape instance
 * @param {Object} stateManager - State manager instance
 * @param {string} label - Property label
 * @param {Object} position - Position object
 * @param {string} sourceClassId - Source class ID
 * @returns {string} Node ID
 */
export function addDataPropertyNode(cytoscapeInstance, stateManager, label, position, sourceClassId) {
  if (!cytoscapeInstance) return null;

  const pid = `DP${Date.now()}`;
  const attrs = addCreationMetadata({});

  cytoscapeInstance.add({
    group: 'nodes',
    data: { id: pid, label, type: 'dataProperty', attrs },
    position
  });

  if (sourceClassId) {
    const edgeAttrs = addCreationMetadata({});
    cytoscapeInstance.add({
      group: 'edges',
      data: {
        id: `edp${Date.now()}`,
        source: sourceClassId,
        target: pid,
        predicate: label,
        type: 'objectProperty',
        attrs: edgeAttrs
      }
    });
  }

  return pid;
}

/**
 * Add a note node
 * @param {Object} cytoscapeInstance - Cytoscape instance
 * @param {Object} stateManager - State manager instance
 * @param {string} text - Note text
 * @param {Object} position - Position object
 * @param {string} targetClassId - Optional target class ID
 * @param {Function} getCurrentUsernameFn - Function to get current username
 * @returns {string} Node ID
 */
export function addNoteNode(cytoscapeInstance, stateManager, text, position, targetClassId, getCurrentUsernameFn) {
  if (!cytoscapeInstance) return null;

  const nid = `Note${Date.now()}`;
  const attrs = addCreationMetadata({
    noteType: 'Note',
    author: getCurrentUsernameFn ? getCurrentUsernameFn() : 'system'
  });

  cytoscapeInstance.add({
    group: 'nodes',
    data: { id: nid, label: text, type: 'note', attrs },
    position,
    classes: 'note'
  });

  if (targetClassId) {
    const edgeAttrs = addCreationMetadata({});
    cytoscapeInstance.add({
      group: 'edges',
      data: {
        id: `enote${Date.now()}`,
        source: nid,
        target: targetClassId,
        predicate: 'note_for',
        type: 'note',
        attrs: edgeAttrs
      }
    });
  }

  return nid;
}

/**
 * Perform delete operation on selected elements
 * @param {Object} cytoscapeInstance - Cytoscape instance
 * @param {HTMLElement} workbenchContainer - Workbench container element
 * @param {Function} refreshTreeFn - Function to refresh tree
 * @param {Function} persistFn - Function to persist changes
 * @returns {boolean} True if deletion occurred
 */
export function performDelete(cytoscapeInstance, workbenchContainer, refreshTreeFn, persistFn) {
  if (!workbenchContainer || !workbenchContainer.classList.contains('active')) {
    return false;
  }
  if (!cytoscapeInstance) return false;

  const sel = cytoscapeInstance.$(':selected');
  if (!sel || sel.length === 0) return false;

  cytoscapeInstance.remove(sel);

  if (refreshTreeFn) {
    refreshTreeFn();
  }
  if (persistFn) {
    persistFn();
  }

  return true;
}

/**
 * Handle delete key press
 * @param {KeyboardEvent} e - Keyboard event
 * @param {Object} cytoscapeInstance - Cytoscape instance
 * @param {HTMLElement} workbenchContainer - Workbench container element
 * @param {Function} refreshTreeFn - Function to refresh tree
 * @param {Function} persistFn - Function to persist changes
 */
export function handleDeleteKey(e, cytoscapeInstance, workbenchContainer, refreshTreeFn, persistFn) {
  const key = e.key || e.code;
  const tgt = e.target;
  const isTyping = tgt && (tgt.tagName === 'INPUT' || tgt.tagName === 'TEXTAREA' || tgt.isContentEditable);
  const inline = qs('#ontoInlineEdit');
  const inlineVisible = inline ? (getComputedStyle(inline).display !== 'none') : false;

  if (isTyping || inlineVisible) return;

  if ((key === 'Delete' || key === 'Backspace') && cytoscapeInstance) {
    const ok = performDelete(cytoscapeInstance, workbenchContainer, refreshTreeFn, persistFn);
    if (ok) {
      e.preventDefault();
      e.stopPropagation();
    }
  }
}
