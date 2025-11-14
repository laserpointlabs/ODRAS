/**
 * Graph Loader Module
 *
 * Main orchestration for loading ontology graphs.
 * Coordinates between localStorage, API, and layout loading.
 */

import { convertOntologyToCytoscape } from './graph-converter.js';
import * as graphPersistence from './graph-persistence.js';
import * as localStorage from '../storage/local-storage.js';

/**
 * Load graph from localStorage or API
 * @param {string} graphIri - Graph IRI
 * @param {Object} cytoscapeInstance - Cytoscape instance
 * @param {Object} stateManager - State manager instance
 * @param {Object} stateAdapter - State adapter instance
 * @param {Object} apiAdapter - API adapter instance
 * @param {Function} loadLayoutFn - Function to load layout
 * @param {Function} updateCanvasVisibilityFn - Function to update canvas visibility
 * @param {Function} refreshTreeFn - Function to refresh tree
 * @returns {Promise<void>}
 */
export async function loadGraphFromLocalOrAPI(
  graphIri,
  cytoscapeInstance,
  stateManager,
  stateAdapter,
  apiAdapter,
  loadLayoutFn,
  updateCanvasVisibilityFn,
  refreshTreeFn
) {
  try {
    console.log('🔍 loadGraphFromLocalOrAPI called for:', graphIri);

    // Load state for this ontology
    const collapsedImports = localStorage.loadCollapsedImports(graphIri, stateAdapter);
    const visibilityState = localStorage.loadVisibilityState(graphIri, stateAdapter);
    const elementVisibility = localStorage.loadElementVisibility(graphIri, stateAdapter);

    stateManager.update({
      collapsedImports,
      visibilityState,
      elementVisibility,
      activeOntologyIri: graphIri
    });

    // First, try to load from local storage
    const localData = graphPersistence.loadGraphFromLocalStorage(graphIri, stateAdapter);
    if (localData && localData.nodes && localData.nodes.length > 0) {
      if (!cytoscapeInstance) return;

      graphPersistence.applyGraphToCytoscape(cytoscapeInstance, localData, stateManager);

      // Load layout
      if (loadLayoutFn) {
        await loadLayoutFn(graphIri);
      }

      // Update UI
      if (updateCanvasVisibilityFn) {
        updateCanvasVisibilityFn();
      }
      if (refreshTreeFn) {
        refreshTreeFn();
      }

      console.log('✅ Graph loaded from local storage');
      return;
    }

    // Fetch from API if local storage is empty
    console.log('🔍 No local storage found, fetching from API');
    const response = await apiAdapter.get(`/api/ontology/?graph=${encodeURIComponent(graphIri)}`);

    if (response.ok && response.data) {
      // API returns { success: true, data: ontology_json, message: "..." }
      const ontologyData = response.data.success ? response.data.data : response.data;

      // Convert to Cytoscape format
      const cytoscapeData = convertOntologyToCytoscape(ontologyData);

      if (!cytoscapeInstance) return;

      // Apply to Cytoscape
      graphPersistence.applyGraphToCytoscape(cytoscapeInstance, cytoscapeData, stateManager);

      // Save to local storage
      graphPersistence.saveGraphToLocalStorage(cytoscapeInstance, graphIri, stateAdapter, false);

      // Try to load layout from server
      let layoutLoaded = false;
      if (loadLayoutFn) {
        layoutLoaded = await loadLayoutFn(graphIri);
      }

      if (!layoutLoaded) {
        requestAnimationFrame(() => {
          if (cytoscapeInstance) {
            cytoscapeInstance.fit();
          }
        });
      }

      // Update UI
      if (updateCanvasVisibilityFn) {
        updateCanvasVisibilityFn();
      }
      if (refreshTreeFn) {
        refreshTreeFn();
      }

      console.log('✅ Ontology loaded from API with', cytoscapeData.nodes?.length || 0, 'nodes and', cytoscapeData.edges?.length || 0, 'edges');
    } else {
      console.error('Failed to load ontology from API:', response.status);
    }
  } catch (err) {
    console.error('Error loading ontology:', err);
  }
}
