/**
 * Event Handlers Module
 *
 * Functions for setting up all Cytoscape and DOM event handlers.
 * This module wires together all the canvas operations, menus, and UI interactions.
 */

import { qs, qsa, debounce } from '../utils/ui-helpers.js';
import { addCreationMetadata, updateModificationMetadata } from '../utils/metadata-helpers.js';
import { snapToGrid, showTemporaryMessage } from '../utils/ui-helpers.js';
import { showInlineEditor } from '../canvas/inline-editor.js';
import { handleDeleteKey } from '../canvas/canvas-operations.js';
import { showMenuAt, hideMenu, startConnectFrom, clearConnectState } from '../menus/context-menu.js';
import { showEdgeMenuAt, hideEdgeMenu, showCustomMultiplicityDialog } from '../menus/edge-menu.js';
import { updateEdgeMultiplicity } from '../layout/layout-manager.js';
import { setupDragStartHandlers, setupDropHandlers } from '../canvas/drag-drop.js';
import { addClassNodeAt, addDataPropertyNode, addNoteNode } from '../canvas/canvas-operations.js';
import { getCurrentUsername } from '../utils/metadata-helpers.js';

/**
 * Set up all event handlers for the ontology workbench
 * @param {Object} config - Configuration object
 * @param {Object} config.cytoscapeInstance - Cytoscape instance
 * @param {HTMLElement} config.container - Container element
 * @param {Object} config.stateManager - State manager instance
 * @param {Object} config.menuState - Context menu state
 * @param {Function} config.refreshTreeFn - Function to refresh tree
 * @param {Function} config.updatePropertiesFn - Function to update properties panel
 * @param {Function} config.persistFn - Function to persist changes
 * @param {Function} config.highlightTreeFn - Function to highlight tree item
 * @param {Function} config.updatePositionInputsFn - Function to update position inputs
 * @param {Function} config.updateCanvasVisibilityFn - Function to update canvas visibility
 * @param {Function} config.updateElementIriDisplayFn - Function to update element IRI display
 * @param {string} config.activeOntologyIri - Active ontology IRI
 * @param {Object} config.apiAdapter - API adapter instance
 * @param {HTMLElement} config.workbenchContainer - Workbench container element
 */
export function setupEventHandlers(config) {
  const {
    cytoscapeInstance,
    container,
    stateManager,
    menuState,
    refreshTreeFn,
    updatePropertiesFn,
    persistFn,
    highlightTreeFn,
    updatePositionInputsFn,
    updateCanvasVisibilityFn,
    updateElementIriDisplayFn,
    activeOntologyIri,
    apiAdapter,
    workbenchContainer
  } = config;

  if (!cytoscapeInstance) return;

  // Focus canvas on interaction so Delete works reliably
  cytoscapeInstance.on('tap', () => {
    try {
      container.focus();
    } catch (error) {
      // Ignore errors
    }
  });

  cytoscapeInstance.on('select', () => {
    try {
      container.focus();
    } catch (error) {
      // Ignore errors
    }
  });

  // Mark canvas active on any interaction
  cytoscapeInstance.on('tap', () => {
    stateManager.set('isCanvasActive', true);
  });

  // Delete key handler
  try {
    container.addEventListener('keydown', (e) => {
      handleDeleteKey(e, cytoscapeInstance, workbenchContainer, refreshTreeFn, persistFn);
    });
  } catch (error) {
    // Ignore errors
  }

  // Edgehandles plugin event handlers
  const eh = stateManager.get('eh');
  if (eh) {
    cytoscapeInstance.on('ehcomplete', (event, sourceNode, targetNode, addedEdge) => {
      try {
        const srcType = (sourceNode.data('type') || 'class');
        const tgtType = (targetNode.data('type') || 'class');
        const edgeType = (addedEdge && addedEdge.data('type')) || stateManager.get('currentPredicateType') || 'objectProperty';
        let invalid = false;

        // Allow note -> class as 'note_for'
        if ((srcType === 'note' && (tgtType === 'class' || tgtType === 'dataProperty')) ||
            ((srcType === 'class' || srcType === 'dataProperty') && tgtType === 'note')) {
          if ((srcType === 'class' || srcType === 'dataProperty') && tgtType === 'note') {
            addedEdge.data('source', targetNode.id());
            addedEdge.data('target', sourceNode.id());
          }
          addedEdge.data('predicate', 'note_for');
          addedEdge.data('type', 'note');
        } else {
          if (edgeType === 'objectProperty' && (srcType !== 'class' || tgtType !== 'class')) invalid = true;
          if (srcType === 'note' || tgtType === 'note') invalid = true;
          if (invalid && addedEdge) {
            addedEdge.remove();
            return;
          }
        }
      } catch (error) {
        // Ignore errors
      }
      requestAnimationFrame(() => {
        if (refreshTreeFn) refreshTreeFn();
        if (persistFn) persistFn();
      });
    });
  } else {
    // Fallback click-to-connect mode if edgehandles not available
    cytoscapeInstance.on('tap', 'node', (ev) => {
      if (!stateManager.get('connectMode')) return;
      const node = ev.target;
      const clickConnectFrom = stateManager.get('clickConnectFrom');
      if (!clickConnectFrom) {
        stateManager.set('clickConnectFrom', node.id());
      } else {
        const from = clickConnectFrom;
        const to = node.id();
        if (from !== to) {
          const src = cytoscapeInstance.$(`#${from}`)[0];
          const tgt = cytoscapeInstance.$(`#${to}`)[0];
          const srcType = (src && (src.data('type') || 'class')) || 'class';
          const tgtType = (tgt && (tgt.data('type') || 'class')) || 'class';
          if (srcType !== 'note' && tgtType !== 'note' && srcType === 'class' && tgtType === 'class') {
            const edgeAttrs = addCreationMetadata({});
            cytoscapeInstance.add({
              group: 'edges',
              data: {
                id: `e${Date.now()}`,
                source: from,
                target: to,
                predicate: 'relatedTo',
                type: 'objectProperty',
                attrs: edgeAttrs
              }
            });
            if (refreshTreeFn) refreshTreeFn();
            if (persistFn) persistFn();
          }
        }
        stateManager.set('clickConnectFrom', null);
      }
    });
  }

  // Selection change handlers
  cytoscapeInstance.on('select unselect add remove data free', () => {
    if (updatePropertiesFn) updatePropertiesFn();
    if (persistFn) persistFn();

    // Highlight corresponding tree item when canvas selection changes
    const selected = cytoscapeInstance.$(':selected');
    if (selected.length === 1) {
      const element = selected[0];
      if (element.isNode()) {
        if (highlightTreeFn) highlightTreeFn(element.id(), 'node');
      } else if (element.isEdge()) {
        if (highlightTreeFn) highlightTreeFn(element.id(), 'edge');
      }
    } else {
      qsa('.onto-node-row').forEach(r => r.classList.remove('selected'));
    }
  });

  // Background click clears selection
  cytoscapeInstance.on('tap', (ev) => {
    if (ev.target === cytoscapeInstance) {
      cytoscapeInstance.$(':selected').unselect();
      if (updatePropertiesFn) updatePropertiesFn();
      hideMenu(menuState);
      hideEdgeMenu();
      clearConnectState(cytoscapeInstance, menuState);
    }
  });

  // Right-click context menu for nodes
  cytoscapeInstance.on('cxttap', 'node', (ev) => {
    const n = ev.target;
    const t = (n.data('type') || 'class');
    const rect = qs('#cy').getBoundingClientRect();
    const rp = ev.renderedPosition || n.renderedPosition();
    const menu = qs('#ontoContextMenu');
    if (!menu) return;
    const btnRel = qs('#menuAddRel');
    const btnDP = qs('#menuAddDataProp');
    if (t === 'note') {
      if (btnRel) {
        btnRel.innerHTML = `
          <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="7" cy="12" r="3"/><circle cx="17" cy="12" r="3"/><path d="M10 12h4"/>
          </svg>
          Link to Class/Property
        `;
      }
      if (btnDP) btnDP.style.display = 'none';
    } else {
      if (btnRel) {
        btnRel.innerHTML = `
          <svg class="menu-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="7" cy="12" r="3"/><circle cx="17" cy="12" r="3"/><path d="M10 12h4"/>
          </svg>
          Add Relationship
        `;
      }
      if (btnDP) btnDP.style.display = 'block';
    }
    showMenuAt(rect.left + rp.x + 6, rect.top + rp.y + 6, menuState);
    menu.dataset.nodeId = n.id();
    menu.dataset.nodeType = t;
  });

  // Right-click context menu for edges
  cytoscapeInstance.on('cxttap', 'edge', (ev) => {
    const edge = ev.target;
    const edgeData = edge.data();
    if (edgeData.type !== 'objectProperty') return;
    if (edge.hasClass('imported')) {
      console.log('🔍 Cannot edit imported edge:', edge.data('predicate'));
      return;
    }
    const rect = qs('#cy').getBoundingClientRect();
    const rp = ev.renderedPosition || edge.renderedMidpoint();
    showEdgeMenuAt(rect.left + rp.x + 6, rect.top + rp.y + 6, () => hideMenu(menuState));
    const edgeMenu = qs('#edgeContextMenu');
    if (edgeMenu) {
      edgeMenu.dataset.edgeId = edge.id();
    }
  });

  // Inline editor (F2 or double-click)
  cytoscapeInstance.on('keydown', 'node,edge', (ev) => {
    if (ev.originalEvent && ev.originalEvent.key === 'F2') {
      showInlineEditor(ev.target, container, refreshTreeFn, persistFn);
    }
  });
  cytoscapeInstance.on('dblclick', 'node,edge', (ev) => {
    showInlineEditor(ev.target, container, refreshTreeFn, persistFn);
  });

  // Snap-to-grid on drag end
  cytoscapeInstance.on('dragfree', 'node', (ev) => {
    const node = ev.target;
    const snapToGridEnabled = stateManager.get('snapToGrid');
    const gridSize = stateManager.get('gridSize');
    if (snapToGridEnabled && !node.hasClass('imported')) {
      const snappedPos = snapToGrid(node.position(), snapToGridEnabled, gridSize);
      node.position(snappedPos);
      showTemporaryMessage(`Snapped to grid (${snappedPos.x}, ${snappedPos.y})`, 800);
    }
  });

  // Update position inputs when nodes are moved
  cytoscapeInstance.on('position', 'node', (ev) => {
    const node = ev.target;
    if (node.selected() && updatePositionInputsFn) {
      updatePositionInputsFn();
    }
  });

  // Context menu actions
  document.addEventListener('click', (e) => {
    const menu = qs('#ontoContextMenu');
    if (!menu) return;
    if (e.target === qs('#menuCancel')) {
      hideMenu(menuState);
      return;
    }
    if (e.target === qs('#menuAddRel')) {
      hideMenu(menuState);
      const id = menu.dataset.nodeId;
      if (!id) return;
      const node = cytoscapeInstance.$('#' + id)[0];
      if (!node) return;
      const t = menu.dataset.nodeType || 'class';
      clearConnectState(cytoscapeInstance, menuState);
      startConnectFrom(node, menuState);
      menuState.sourceType = t;
      return;
    }
    if (e.target === qs('#menuAddDataProp')) {
      hideMenu(menuState);
      const id = menu.dataset.nodeId;
      if (!id) return;
      const node = cytoscapeInstance.$('#' + id)[0];
      if (!node) return;
      const pos = node.position();
      const label = `Data Property ${Date.now() % 1000}`;
      const pid = addDataPropertyNode(cytoscapeInstance, stateManager, label, { x: pos.x + 120, y: pos.y }, id);
      if (refreshTreeFn) refreshTreeFn();
      if (persistFn) persistFn();
      return;
    }
  });

  // Edge context menu actions
  document.addEventListener('click', (e) => {
    const edgeMenu = qs('#edgeContextMenu');
    if (!edgeMenu || edgeMenu.style.display === 'none') return;
    const action = e.target.dataset.action;
    if (!action && e.target.id !== 'edgeMenuCancel') return;
    if (e.target.id === 'edgeMenuCancel') {
      hideEdgeMenu();
      return;
    }
    const edgeId = edgeMenu.dataset.edgeId;
    const edge = edgeId ? cytoscapeInstance.$('#' + edgeId)[0] : null;
    if (!edge) {
      hideEdgeMenu();
      return;
    }
    let minCount = null, maxCount = null;
    switch (action) {
      case 'mult-none': minCount = null; maxCount = null; break;
      case 'mult-1': minCount = 1; maxCount = 1; break;
      case 'mult-0-1': minCount = 0; maxCount = 1; break;
      case 'mult-0-*': minCount = 0; maxCount = null; break;
      case 'mult-1-*': minCount = 1; maxCount = null; break;
      case 'mult-custom':
        hideEdgeMenu();
        showCustomMultiplicityDialog(edge, (e, min, max) => updateEdgeMultiplicity(e, min, max, refreshTreeFn, persistFn));
        return;
      case 'edit-edge':
        hideEdgeMenu();
        showInlineEditor(edge, container, refreshTreeFn, persistFn);
        return;
      default: return;
    }
    updateEdgeMultiplicity(edge, minCount, maxCount, refreshTreeFn, persistFn);
    hideEdgeMenu();
  });

  // Clicking a target after 'Add relationship' completes the edge
  cytoscapeInstance.on('tap', 'node', (ev) => {
    const target = ev.target;
    if (!menuState.sourceId) return;
    const tgtType = (target.data('type') || 'class');
    const source = cytoscapeInstance.$('#' + menuState.sourceId)[0];
    if (!source) {
      clearConnectState(cytoscapeInstance, menuState);
      return;
    }
    const srcType = menuState.sourceType || (source.data('type') || 'class');
    if (source.id() !== target.id()) {
      if (srcType === 'note' && (tgtType === 'class' || tgtType === 'dataProperty')) {
        const edgeAttrs = addCreationMetadata({});
        cytoscapeInstance.add({
          group: 'edges',
          data: {
            id: `enote${Date.now()}`,
            source: source.id(),
            target: target.id(),
            predicate: 'note_for',
            type: 'note',
            attrs: edgeAttrs
          }
        });
        if (refreshTreeFn) refreshTreeFn();
        if (persistFn) persistFn();
      } else if (srcType === 'class' && tgtType === 'class') {
        const edgeAttrs = addCreationMetadata({});
        cytoscapeInstance.add({
          group: 'edges',
          data: {
            id: `e${Date.now()}`,
            source: source.id(),
            target: target.id(),
            predicate: 'relatedTo',
            type: 'objectProperty',
            attrs: edgeAttrs
          }
        });
        if (refreshTreeFn) refreshTreeFn();
        if (persistFn) persistFn();
      }
    }
    source.removeClass('connect-source');
    clearConnectState(cytoscapeInstance, menuState);
  });

  // Drag-and-drop handlers
  const icons = Array.from(document.querySelectorAll('.onto-icon'));
  setupDragStartHandlers(icons);

  setupDropHandlers(
    container,
    cytoscapeInstance,
    stateManager,
    (label, pos) => addClassNodeAt(cytoscapeInstance, stateManager, label, pos, activeOntologyIri, apiAdapter),
    (enabled) => stateManager.set('connectMode', enabled),
    (label, pos, sourceId) => addDataPropertyNode(cytoscapeInstance, stateManager, label, pos, sourceId),
    (text, pos, targetId) => addNoteNode(cytoscapeInstance, stateManager, text, pos, targetId, getCurrentUsername),
    refreshTreeFn,
    persistFn,
    getCurrentUsername
  );

  // Bind autosave on edits
  try {
    const autosave = debounce(() => {
      try {
        if (activeOntologyIri && persistFn) {
          persistFn();
        }
      } catch (error) {
        // Ignore errors
      }
    }, 250);
    cytoscapeInstance.on('add remove data', autosave);

    const localStorageSave = debounce(() => {
      try {
        if (activeOntologyIri && !stateManager.get('layoutRunning') && persistFn) {
          persistFn();
        }
      } catch (error) {
        // Ignore errors
      }
    }, 100);

    cytoscapeInstance.on('position', localStorageSave);
    stateManager.set('autosaveBound', true);

    cytoscapeInstance.on('position', 'node', (evt) => {
      try {
        const node = evt.target;
        if (!node.hasClass('imported')) {
          const currentAttrs = node.data('attrs') || {};
          const updatedAttrs = updateModificationMetadata(currentAttrs);
          node.data('attrs', updatedAttrs);
        }
      } catch (error) {
        // Ignore errors
      }
    });
  } catch (error) {
    // Ignore errors
  }

  // Initialize element IRI display
  if (updateElementIriDisplayFn) {
    updateElementIriDisplayFn();
  }
}
