/**
 * Graph Converter Module
 *
 * Functions for converting ontology data formats to Cytoscape format.
 * Pure functions with no dependencies on ODRAS or DOM.
 */

/**
 * Format multiplicity display string
 * @param {number|null} minCount - Minimum count
 * @param {number|null} maxCount - Maximum count
 * @returns {string} Multiplicity display string
 */
function formatMultiplicity(minCount, maxCount) {
  if (minCount === null && maxCount === null) return '';

  if (minCount === 1 && maxCount === 1) return ' (1)';
  if (minCount === 0 && maxCount === null) return ' (0..*)';
  if (minCount === 1 && maxCount === null) return ' (1..*)';
  if (minCount === 0 && maxCount === 1) return ' (0..1)';
  if (minCount !== null && maxCount !== null && minCount === maxCount) {
    return ` (${minCount})`;
  }
  if (minCount !== null && maxCount !== null) {
    return ` (${minCount}..${maxCount})`;
  }
  if (minCount !== null) {
    return ` (${minCount}..*)`;
  }
  if (maxCount !== null) {
    return ` (0..${maxCount})`;
  }
  return '';
}

/**
 * Convert ontology data to Cytoscape format
 * @param {Object} ontologyData - Ontology data from API
 * @returns {Object} Cytoscape data with nodes and edges arrays
 */
export function convertOntologyToCytoscape(ontologyData) {
  const nodes = [];
  const edges = [];
  const classes = ontologyData.classes || [];
  const classNameToId = {};

  // Convert classes to nodes
  classes.forEach((cls, index) => {
    const classId = cls.iri || `Class${index + 1}`;
    classNameToId[cls.name] = classId;
    const row = Math.floor(index / 4);
    const col = index % 4;
    nodes.push({
      data: {
        id: classId,
        iri: cls.iri || classId,
        label: cls.label || cls.name,
        type: 'class',
        attrs: {}
      },
      position: {
        x: 150 + (col * 200),
        y: 100 + (row * 150)
      }
    });
  });

  // Convert object properties to edges
  let edgeId = 1;
  const objectProps = ontologyData.object_properties || [];
  objectProps.forEach(prop => {
    if (prop.domain && prop.range && classNameToId[prop.domain] && classNameToId[prop.range]) {
      const minCount = prop.min_count;
      const maxCount = prop.max_count;
      const multiplicity = formatMultiplicity(minCount, maxCount);
      const displayLabel = prop.label || prop.name;

      edges.push({
        data: {
          id: `e${edgeId}`,
          source: classNameToId[prop.domain],
          target: classNameToId[prop.range],
          predicate: prop.name,
          label: displayLabel,
          type: 'objectProperty',
          minCount: minCount,
          maxCount: maxCount,
          multiplicityDisplay: multiplicity.trim(),
          attrs: {}
        }
      });
      edgeId++;
    }
  });

  // Convert datatype properties to nodes and edges
  let dpId = 1;
  const dataProps = ontologyData.datatype_properties || [];
  dataProps.forEach(prop => {
    if (prop.domain && classNameToId[prop.domain]) {
      const dataPropertyId = `DP${dpId}`;
      const domainClassId = classNameToId[prop.domain];
      const domainNode = nodes.find(n => n.data.id === domainClassId);
      let dpX = 150, dpY = 100;
      if (domainNode) {
        dpX = domainNode.position.x + 180;
        dpY = domainNode.position.y + (dpId % 3 - 1) * 60;
      }
      nodes.push({
        data: {
          id: dataPropertyId,
          label: prop.label || prop.name,
          type: 'dataProperty',
          attrs: {}
        },
        position: { x: dpX, y: dpY }
      });
      edges.push({
        data: {
          id: `edp${dpId}`,
          source: domainClassId,
          target: dataPropertyId,
          predicate: prop.name,
          type: 'objectProperty',
          attrs: {}
        }
      });
      dpId++;
    }
  });

  return { nodes, edges };
}

/**
 * Convert ontology data to Cytoscape format with rich metadata
 * @param {Object} ontologyData - Ontology data from API
 * @param {Object} richMetadata - Rich metadata from SPARQL queries
 * @returns {Object} Cytoscape data with nodes and edges arrays
 */
export function convertOntologyToCytoscapeWithMetadata(ontologyData, richMetadata) {
  // Simplified version - use basic conversion for now
  return convertOntologyToCytoscape(ontologyData);
}
