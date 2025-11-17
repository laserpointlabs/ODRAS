/**
 * Ontology Workbench UI Module - Compatibility Wrapper
 *
 * This file provides backward compatibility with the old initialization pattern
 * while using the new modular architecture under the hood.
 *
 * For new code, use the OntologyWorkbench class from index.js directly.
 */

import { createOntologyWorkbench, createOdrasAdapters } from './index.js';
import { apiClient } from '../../core/api-client.js';
import { getAppState, updateAppState } from '../../core/state-manager.js';
import { subscribeToEvent, emitEvent } from '../../core/event-bus.js';
import { qs } from './utils/ui-helpers.js';

// Store workbench instance for backward compatibility
let workbenchInstance = null;

/**
 * Initialize ontology workbench (backward compatibility function)
 * @returns {Promise<void>}
 */
export async function initializeOntologyWorkbench() {
  console.log('🔷 Initializing Ontology Workbench (compatibility mode)...');

  const workbenchContainer = qs('#wb-ontology');
  if (!workbenchContainer) {
    console.error('❌ Ontology workbench container not found');
    return;
  }

  // Create adapters from ODRAS modules
  const adapters = createOdrasAdapters({
    apiClient,
    getAppState,
    updateAppState,
    subscribeToEvent,
    emitEvent
  });

  // Create workbench instance
  workbenchInstance = createOntologyWorkbench({
    container: workbenchContainer,
    ...adapters,
    options: {
      autosave: true,
      snapToGrid: true,
      gridSize: 20
    }
  });

  // Initialize the workbench
  await workbenchInstance.initialize();

  console.log('✅ Ontology Workbench initialized (compatibility mode)');
}

// Export state for backward compatibility (if needed)
export const ontoState = {
  get cy() {
    return workbenchInstance?.cytoscapeInstance || null;
  },
  get eh() {
    return workbenchInstance?.stateManager?.get('eh') || null;
  },
  get connectMode() {
    return workbenchInstance?.stateManager?.get('connectMode') || false;
  },
  set connectMode(value) {
    if (workbenchInstance) {
      workbenchInstance.stateManager.set('connectMode', value);
    }
  },
  get nextId() {
    return workbenchInstance?.stateManager?.get('nextId') || 1;
  },
  set nextId(value) {
    if (workbenchInstance) {
      workbenchInstance.stateManager.set('nextId', value);
    }
  },
  get snapToGrid() {
    return workbenchInstance?.stateManager?.get('snapToGrid') || true;
  },
  set snapToGrid(value) {
    if (workbenchInstance) {
      workbenchInstance.stateManager.set('snapToGrid', value);
    }
  },
  get gridSize() {
    return workbenchInstance?.stateManager?.get('gridSize') || 20;
  },
  set gridSize(value) {
    if (workbenchInstance) {
      workbenchInstance.stateManager.set('gridSize', value);
    }
  }
};

// Export active ontology IRI for backward compatibility
export let activeOntologyIri = null;

// Update activeOntologyIri when workbench loads an ontology
if (workbenchInstance) {
  workbenchInstance.on('ontology:loaded', (iri) => {
    activeOntologyIri = iri;
  });
}
