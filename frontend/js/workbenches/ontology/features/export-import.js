/**
 * Export/Import Module
 *
 * Functions for exporting and importing ontology data.
 * Uses RDF helpers for Turtle conversion.
 */

import { toTurtle } from '../utils/rdf-helpers.js';

/**
 * Export ontology to JSON
 * @param {Object} cytoscapeInstance - Cytoscape instance
 * @returns {Object} JSON representation
 */
export function exportOntologyJSON(cytoscapeInstance) {
  if (!cytoscapeInstance) return null;

  const nodes = cytoscapeInstance.nodes()
    .filter(n => !n.hasClass('imported'))
    .map(n => ({ data: n.data(), position: n.position() }));

  const edges = cytoscapeInstance.edges()
    .filter(e => !e.hasClass('imported'))
    .map(e => ({ data: e.data() }));

  return { nodes, edges };
}

/**
 * Import ontology from JSON
 * @param {Object} cytoscapeInstance - Cytoscape instance
 * @param {Object} jsonData - JSON data
 */
export function importOntologyJSON(cytoscapeInstance, jsonData) {
  if (!cytoscapeInstance || !jsonData) return;

  if (jsonData.nodes && jsonData.nodes.length > 0) {
    cytoscapeInstance.add(jsonData.nodes);
  }
  if (jsonData.edges && jsonData.edges.length > 0) {
    cytoscapeInstance.add(jsonData.edges);
  }
}

/**
 * Export ontology to Turtle format
 * @param {string} graphIri - Graph IRI
 * @param {Object} cytoscapeInstance - Cytoscape instance
 * @returns {string} Turtle format string
 */
export function exportOntologyToTurtle(graphIri, cytoscapeInstance) {
  // TODO: Full implementation when extracting from app.html
  return toTurtle(graphIri, {}, {});
}
