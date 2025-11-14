/**
 * Cytoscape Initialization Module
 *
 * Functions for initializing and configuring the Cytoscape instance.
 * This is the core visualization engine for the ontology workbench.
 */

import { qs } from '../utils/ui-helpers.js';
import { getNoteTypeStyle } from '../utils/ui-helpers.js';

/**
 * Get Cytoscape style configuration
 * @returns {Array} Style configuration array
 */
function getCytoscapeStyles() {
  return [
    {
      selector: 'node',
      style: {
        'shape': 'round-rectangle',
        'background-color': '#1b2a45',
        'border-color': '#2a3b5f',
        'border-width': 1,
        'label': 'data(label)',
        'color': '#e5e7eb',
        'font-size': 12,
        'text-wrap': 'wrap',
        'text-max-width': 180,
        'text-valign': 'center',
        'text-halign': 'center'
      }
    },
    { selector: 'node[type = "class"]', style: { 'width': 180, 'height': 56 } },
    {
      selector: 'node[type = "dataProperty"]',
      style: {
        'width': 160,
        'height': 48,
        'background-color': '#154e5a',
        'border-color': '#2ea3b0'
      }
    },
    {
      selector: 'edge',
      style: {
        'curve-style': 'bezier',
        'width': 2,
        'line-color': '#3b4a6b',
        'target-arrow-shape': 'triangle',
        'target-arrow-color': '#3b4a6b',
        'arrow-scale': 1,
        'label': 'data(predicate)',
        'color': '#e5e7eb',
        'font-size': 10,
        'text-rotation': 'autorotate',
        'text-background-color': '#0b1220',
        'text-background-opacity': 0.6,
        'text-background-padding': 2,
        'target-label': 'data(multiplicityDisplay)',
        'target-text-offset': 15,
        'target-text-rotation': 0,
        'target-text-color': '#60a5fa',
        'target-text-background-color': '#0b1220',
        'target-text-background-opacity': 0.8,
        'target-text-background-padding': 3,
        'target-text-border-width': 1,
        'target-text-border-color': '#60a5fa',
        'target-text-border-opacity': 0.5
      }
    },
    {
      selector: 'edge[type = "note"], edge[predicate = "note_for"]',
      style: {
        'target-arrow-shape': 'circle',
        'target-arrow-color': '#9ca3af',
        'arrow-scale': 0.8,
        'source-arrow-shape': 'none'
      }
    },
    { selector: '.imported', style: { 'opacity': 0.55 } },
    { selector: 'edge.imported', style: { 'line-style': 'dashed' } },
    {
      selector: 'edge.imported-equivalence',
      style: {
        'line-style': 'dotted',
        'width': 1.5,
        'line-color': '#60a5fa',
        'label': '≡',
        'color': '#9ca3af',
        'font-size': 9,
        'text-background-opacity': 0
      }
    },
    {
      selector: 'node[type = "note"], .note',
      style: {
        'shape': 'rectangle',
        'background-color': function (ele) {
          const noteType = ele.data('attrs') && ele.data('attrs').noteType;
          return getNoteTypeStyle(noteType || 'Note').backgroundColor;
        },
        'border-color': function (ele) {
          const noteType = ele.data('attrs') && ele.data('attrs').noteType;
          return getNoteTypeStyle(noteType || 'Note').borderColor;
        },
        'border-style': 'solid',
        'border-width': 1,
        'label': function (ele) {
          const noteType = ele.data('attrs') && ele.data('attrs').noteType;
          const symbol = getNoteTypeStyle(noteType || 'Note').symbol;
          const content = ele.data('attrs') && ele.data('attrs').content;
          const text = content || ele.data('label') || 'Note';
          return symbol + ' ' + text;
        },
        'color': function (ele) {
          const noteType = ele.data('attrs') && ele.data('attrs').noteType;
          return getNoteTypeStyle(noteType || 'Note').textColor;
        },
        'font-size': 12,
        'text-wrap': 'wrap',
        'text-max-width': 220,
        'text-valign': 'center',
        'text-halign': 'center',
        'width': 220,
        'height': 80
      }
    },
    {
      selector: ':selected',
      style: {
        'border-color': '#60a5fa',
        'border-width': 2,
        'line-color': '#60a5fa',
        'target-arrow-color': '#60a5fa'
      }
    }
  ];
}

/**
 * Initialize Cytoscape instance
 * @param {HTMLElement} container - Container element
 * @param {Object} stateManager - State manager instance
 * @returns {Object|null} Cytoscape instance or null if initialization fails
 */
export function initializeCytoscape(container, stateManager) {
  if (!container) return null;

  // Make canvas focusable for keyboard events
  try {
    container.setAttribute('tabindex', '0');
    container.style.outline = 'none';
  } catch (error) {
    // Ignore errors
  }

  // Register edgehandles plugin if available
  try {
    if (window.cytoscape && (window.cytoscapeEdgehandles || window.edgehandles)) {
      const plugin = window.cytoscapeEdgehandles || window.edgehandles;
      if (plugin && typeof plugin === 'function') {
        window.cytoscape.use(plugin);
      }
    }
  } catch (error) {
    console.warn('Edgehandles plugin not available:', error);
  }

  // Initialize Cytoscape instance
  const cy = window.cytoscape({
    container,
    layout: {
      name: 'breadthfirst',
      directed: true,
      spacingFactor: 2.0,
      avoidOverlap: true,
      nodeDimensionsIncludeLabels: true,
      animate: true,
      animationDuration: 500,
      fit: true,
      padding: 50
    },
    wheelSensitivity: 0.15,
    minZoom: 0.1,
    maxZoom: 3,
    boxSelectionEnabled: true,
    selectionType: 'single',
    style: getCytoscapeStyles(),
    elements: []
  });

  // Store reference for debugging
  window._cy = cy;

  // Initialize edgehandles plugin if available
  let eh = null;
  if (typeof cy.edgehandles === 'function') {
    eh = cy.edgehandles({
      handleSize: 8,
      handleNodes: 'node[type = "class"], node[type = "note"]',
      handleColor: '#60a5fa',
      handleOutlineColor: '#0b1220',
      handleOutlineWidth: 2,
      toggleOffOnLeave: true,
      enabled: true,
      edgeParams: () => ({ data: { predicate: 'relatedTo', type: 'objectProperty' } })
    });
  }

  // Update state manager
  stateManager.set('cy', cy);
  stateManager.set('eh', eh);
  stateManager.set('nextId', 1);

  return cy;
}
