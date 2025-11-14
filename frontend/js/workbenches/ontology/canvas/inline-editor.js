/**
 * Inline Editor Module
 *
 * Functions for inline editing of element labels (F2 or double-click).
 */

import { qs } from '../utils/ui-helpers.js';
import { updateModificationMetadata } from '../utils/metadata-helpers.js';

/**
 * Show inline editor for an element
 * @param {Object} target - Cytoscape element (node or edge)
 * @param {HTMLElement} container - Cytoscape container element
 * @param {Function} refreshTreeFn - Function to refresh tree
 * @param {Function} persistFn - Function to persist changes
 * @param {Function} getStateFn - Optional function to get app state for metadata
 */
export function showInlineEditor(target, container, refreshTreeFn, persistFn, getStateFn = null) {
  if (target.hasClass('imported')) {
    console.log('🔍 Cannot edit imported element:', target.data('label'));
    return;
  }

  const input = qs('#ontoInlineEdit');
  if (!input) return;

  const pos = target.renderedPosition();
  const rect = container.getBoundingClientRect();
  let current = '';

  if (target.isNode()) {
    const nodeType = target.data('type') || 'class';
    if (nodeType === 'note') {
      const attrs = target.data('attrs') || {};
      current = attrs.content || '';
    } else {
      current = target.data('label') || '';
    }
  } else {
    current = target.data('predicate') || '';
  }

  input.value = current;
  input.style.left = (rect.left + pos.x - Math.min(100, rect.width * 0.2)) + 'px';
  input.style.top = (rect.top + pos.y - 12) + 'px';
  input.style.display = 'block';
  input.focus();
  input.select();

  function commit(save) {
    if (save) {
      const v = input.value.trim();
      if (target.isNode()) {
        const nodeType = target.data('type') || 'class';
        if (nodeType === 'note') {
          const currentAttrs = target.data('attrs') || {};
          currentAttrs.content = v || current;
          const updatedAttrs = updateModificationMetadata(currentAttrs, getStateFn);
          target.data('attrs', updatedAttrs);
        } else {
          target.data('label', v || current);
          const currentAttrs = target.data('attrs') || {};
          const updatedAttrs = updateModificationMetadata(currentAttrs, getStateFn);
          target.data('attrs', updatedAttrs);
        }
      } else {
        target.data('predicate', v || current);
        const currentAttrs = target.data('attrs') || {};
        const updatedAttrs = updateModificationMetadata(currentAttrs, getStateFn);
        target.data('attrs', updatedAttrs);
      }

      if (refreshTreeFn) {
        refreshTreeFn();
      }
      if (persistFn) {
        persistFn();
      }
    }

    input.style.display = 'none';
    input.onkeydown = null;
    input.onblur = null;
  }

  input.onkeydown = (e) => {
    if (e.key === 'Enter') commit(true);
    else if (e.key === 'Escape') commit(false);
  };

  input.onblur = () => commit(true);
}
