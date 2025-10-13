"""
Graph Builder Service
Converts configurations to graph format for visualization
"""

import json
import logging
import hashlib
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)

class GraphBuilder:
    """
    Converts configuration structures to graph format (nodes/edges)
    """
    
    # Dynamic color palette for node types
    COLOR_PALETTE = [
        "#4A90E2", "#50E3C2", "#F5A623", "#BD10E0", "#7ED321", "#9013FE",
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD",
        "#FFA07A", "#98D8E8", "#F7DC6F", "#BB8FCE", "#85C1E9", "#F8C471"
    ]
    
    # Shape options for different node types  
    SHAPE_OPTIONS = [
        "ellipse", "roundrectangle", "hexagon", "diamond", 
        "triangle", "star", "pentagon", "octagon"
    ]
    
    def __init__(self):
        self._type_color_cache = {}  # Cache colors for consistency
        self._type_shape_cache = {}  # Cache shapes for consistency
    
    async def build_graph_from_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert a single configuration to graph format
        """
        try:
            logger.info(f"🔍 Building graph for configuration {config.get('config_id')}")
            
            nodes = []
            edges = []
            clusters = []
            
            # Extract structure
            structure = config.get("structure", {})
            config_id = config.get("config_id")
            config_name = config.get("name", "Unnamed Configuration")
            
            # Process the configuration structure
            node_ids = set()
            await self._process_structure_node(
                structure, nodes, edges, node_ids, 
                config_id=config_id, parent_id=None
            )
            
            # Create cluster for this configuration
            clusters.append({
                "id": f"cluster-{config_id}",
                "label": config_name,
                "node_ids": list(node_ids)
            })
            
            result = {
                "nodes": nodes,
                "edges": edges,
                "clusters": clusters,
                "metadata": {
                    "config_id": config_id,
                    "config_name": config_name,
                    "node_count": len(nodes),
                    "edge_count": len(edges)
                }
            }
            
            logger.info(f"✅ Graph built: {len(nodes)} nodes, {len(edges)} edges")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error building graph from configuration: {e}")
            raise e
    
    async def build_overview_graph(self, configurations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build aggregated graph from multiple configurations
        """
        try:
            logger.info(f"🔍 Building overview graph from {len(configurations)} configurations")
            
            all_nodes = []
            all_edges = []
            all_clusters = []
            
            # Node deduplication tracking
            node_map = {}  # node_key -> merged_node
            edge_map = {}  # edge_key -> merged_edge
            
            for config in configurations:
                # Build individual graph
                graph_data = await self.build_graph_from_configuration(config)
                
                # Merge nodes (deduplicate similar nodes across configurations)
                for node in graph_data["nodes"]:
                    node_key = self._get_node_key(node)
                    
                    if node_key in node_map:
                        # Merge with existing node
                        existing_node = node_map[node_key]
                        existing_node = self._merge_nodes(existing_node, node)
                        node_map[node_key] = existing_node
                    else:
                        # Add new node
                        node_map[node_key] = node
                
                # Merge edges
                for edge in graph_data["edges"]:
                    edge_key = self._get_edge_key(edge)
                    
                    if edge_key in edge_map:
                        # Merge with existing edge
                        existing_edge = edge_map[edge_key]
                        existing_edge = self._merge_edges(existing_edge, edge)
                        edge_map[edge_key] = existing_edge
                    else:
                        # Add new edge
                        edge_map[edge_key] = edge
                
                # Add clusters
                all_clusters.extend(graph_data["clusters"])
            
            # Convert maps to lists
            all_nodes = list(node_map.values())
            all_edges = list(edge_map.values())
            
            # Add overview metadata to nodes
            self._add_overview_metadata(all_nodes, all_edges, configurations)
            
            result = {
                "nodes": all_nodes,
                "edges": all_edges,
                "clusters": all_clusters,
                "metadata": {
                    "overview": True,
                    "config_count": len(configurations),
                    "node_count": len(all_nodes),
                    "edge_count": len(all_edges),
                    "cluster_count": len(all_clusters)
                }
            }
            
            logger.info(f"✅ Overview graph built: {len(all_nodes)} nodes, {len(all_edges)} edges")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error building overview graph: {e}")
            raise e
    
    async def _process_structure_node(
        self,
        node_data: Dict[str, Any],
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        node_ids: Set[str],
        config_id: str,
        parent_id: Optional[str] = None
    ):
        """
        Recursively process structure nodes and create graph elements
        """
        try:
            # Extract node information
            node_type = node_data.get("class")
            instance_id = node_data.get("instanceId", node_data.get("instance"))
            properties = node_data.get("properties", {})
            
            if not node_type or not instance_id:
                logger.warning("Skipping node with missing type or instance ID")
                return None
            
            # Create unique node ID
            node_id = f"{config_id}_{instance_id}"
            node_ids.add(node_id)
            
            # Get dynamic node style
            style = self._get_node_style(node_type)
            
            # Create node
            node = {
                "id": node_id,
                "type": node_type,
                "label": properties.get("name", instance_id),
                "properties": properties,
                "style": style,
                "metadata": {
                    "config_id": config_id,
                    "instance_id": instance_id,
                    "node_type": node_type
                }
            }
            
            # Add DAS metadata if available
            if "dasRationale" in properties:
                node["das_metadata"] = {
                    "rationale": properties["dasRationale"],
                    "confidence": properties.get("dasConfidence", 0.8)
                }
            
            nodes.append(node)
            
            # Process relationships
            relationships = node_data.get("relationships", [])
            for relationship in relationships:
                await self._process_relationship(
                    node_id, relationship, nodes, edges, node_ids, config_id
                )
            
            return node_id
            
        except Exception as e:
            logger.error(f"❌ Error processing structure node: {e}")
            return None
    
    async def _process_relationship(
        self,
        source_id: str,
        relationship: Dict[str, Any],
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]],
        node_ids: Set[str],
        config_id: str
    ):
        """
        Process relationship and create edges
        """
        try:
            property_name = relationship.get("property")
            multiplicity = relationship.get("multiplicity", "1")
            targets = relationship.get("targets", [])
            
            if not property_name:
                logger.warning("Skipping relationship with missing property name")
                return
            
            for i, target in enumerate(targets):
                target_id = None
                
                # Handle different target types
                if isinstance(target, dict):
                    if "componentRef" in target or "instanceRef" in target:
                        # Reference to another node
                        ref_id = target.get("componentRef") or target.get("instanceRef")
                        target_id = f"{config_id}_{ref_id}"
                    elif "class" in target:
                        # Nested structure - process recursively
                        target_id = await self._process_structure_node(
                            target, nodes, edges, node_ids, config_id, source_id
                        )
                elif isinstance(target, str):
                    # Simple reference
                    target_id = f"{config_id}_{target}"
                
                if target_id:
                    # Create edge
                    edge_id = f"{source_id}_{property_name}_{target_id}_{i}"
                    
                    edge = {
                        "id": edge_id,
                        "source": source_id,
                        "target": target_id,
                        "type": property_name,
                        "label": f"{property_name} ({multiplicity})",
                        "properties": {
                            "relationship_type": property_name,
                            "multiplicity": multiplicity
                        }
                    }
                    
                    # Add rationale if available
                    if isinstance(target, dict) and "rationale" in target:
                        edge["das_metadata"] = {
                            "rationale": target["rationale"]
                        }
                    
                    edges.append(edge)
            
        except Exception as e:
            logger.error(f"❌ Error processing relationship: {e}")
    
    def _get_node_key(self, node: Dict[str, Any]) -> str:
        """
        Generate key for node deduplication in overview
        """
        # Use type + label for deduplication
        node_type = node.get("type", "")
        label = node.get("label", "")
        return f"{node_type}:{label}"
    
    def _get_edge_key(self, edge: Dict[str, Any]) -> str:
        """
        Generate key for edge deduplication in overview
        """
        source = edge.get("source", "").split("_")[-1] if edge.get("source") else ""
        target = edge.get("target", "").split("_")[-1] if edge.get("target") else ""
        edge_type = edge.get("type", "")
        
        return f"{source}->{edge_type}->{target}"
    
    def _merge_nodes(self, existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge two similar nodes
        """
        # Keep the existing node but merge metadata
        if "configurations" not in existing.get("metadata", {}):
            existing["metadata"]["configurations"] = []
        
        existing["metadata"]["configurations"].append(
            new.get("metadata", {}).get("config_id", "unknown")
        )
        
        # Merge DAS metadata if both have it
        if "das_metadata" in existing and "das_metadata" in new:
            existing_confidence = existing.get("das_metadata", {}).get("confidence", 0)
            new_confidence = new.get("das_metadata", {}).get("confidence", 0)
            
            # Use higher confidence
            if new_confidence > existing_confidence:
                existing["das_metadata"] = new["das_metadata"]
        
        return existing
    
    def _merge_edges(self, existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge two similar edges
        """
        # Keep the existing edge but increment count
        if "count" not in existing.get("metadata", {}):
            existing["metadata"]["count"] = 1
        
        existing["metadata"]["count"] += 1
        
        # Update label to show count
        base_label = existing.get("label", "").split(" (")[0]
        count = existing["metadata"]["count"]
        existing["label"] = f"{base_label} ({count}x)"
        
        return existing
    
    def _add_overview_metadata(
        self, 
        nodes: List[Dict[str, Any]], 
        edges: List[Dict[str, Any]], 
        configurations: List[Dict[str, Any]]
    ):
        """
        Add overview-specific metadata to nodes and edges
        """
        # Add configuration count to each node type
        type_counts = defaultdict(int)
        for node in nodes:
            node_type = node.get("type", "Unknown")
            type_counts[node_type] += 1
        
        # Update node labels with counts
        for node in nodes:
            node_type = node.get("type", "Unknown")
            total_of_type = type_counts[node_type]
            
            # Add type statistics to metadata
            node["metadata"]["type_statistics"] = {
                "total_of_type": total_of_type,
                "percentage": round((total_of_type / len(nodes)) * 100, 1)
            }
    
    def get_supported_export_formats(self) -> List[str]:
        """
        Get list of supported export formats
        """
        return ["json", "graphml", "gexf", "cytoscape"]
    
    async def export_graph(
        self, 
        graph_data: Dict[str, Any], 
        format_type: str
    ) -> str:
        """
        Export graph data in specified format
        """
        try:
            if format_type == "json":
                return json.dumps(graph_data, indent=2)
            elif format_type == "graphml":
                return self._export_graphml(graph_data)
            elif format_type == "gexf":
                return self._export_gexf(graph_data)
            elif format_type == "cytoscape":
                return self._export_cytoscape(graph_data)
            else:
                raise ValueError(f"Unsupported export format: {format_type}")
                
        except Exception as e:
            logger.error(f"❌ Error exporting graph: {e}")
            raise e
    
    def _export_graphml(self, graph_data: Dict[str, Any]) -> str:
        """Export graph in GraphML format"""
        # Simplified GraphML export
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
            '  <key id="label" for="node" attr.name="label" attr.type="string"/>',
            '  <key id="type" for="node" attr.name="type" attr.type="string"/>',
            '  <graph id="G" edgedefault="directed">'
        ]
        
        # Add nodes
        for node in nodes:
            xml_lines.extend([
                f'    <node id="{node["id"]}">',
                f'      <data key="label">{node.get("label", "")}</data>',
                f'      <data key="type">{node.get("type", "")}</data>',
                '    </node>'
            ])
        
        # Add edges
        for edge in edges:
            xml_lines.extend([
                f'    <edge source="{edge["source"]}" target="{edge["target"]}" id="{edge["id"]}"/>',
            ])
        
        xml_lines.extend([
            '  </graph>',
            '</graphml>'
        ])
        
        return '\n'.join(xml_lines)
    
    def _export_gexf(self, graph_data: Dict[str, Any]) -> str:
        """Export graph in GEXF format"""
        # Simplified GEXF export
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<gexf xmlns="http://www.gexf.net/1.2draft" version="1.2">',
            '  <graph mode="static" defaultedgetype="directed">',
            '    <nodes>'
        ]
        
        # Add nodes
        for node in nodes:
            xml_lines.append(
                f'      <node id="{node["id"]}" label="{node.get("label", "")}"/>'
            )
        
        xml_lines.append('    </nodes>')
        xml_lines.append('    <edges>')
        
        # Add edges
        for edge in edges:
            xml_lines.append(
                f'      <edge id="{edge["id"]}" source="{edge["source"]}" target="{edge["target"]}"/>'
            )
        
        xml_lines.extend([
            '    </edges>',
            '  </graph>',
            '</gexf>'
        ])
        
        return '\n'.join(xml_lines)
    
    def _get_node_style(self, node_type: str) -> Dict[str, Any]:
        """
        Get or generate style for a node type dynamically (fully generic)
        """
        # Check cache first
        if node_type in self._type_color_cache:
            return {
                "shape": self._type_shape_cache[node_type],
                "color": self._type_color_cache[node_type],
                "icon": "⚫"  # Generic icon for all types
            }
        
        # Generate new style based on node type name
        type_hash = hash(node_type)
        color_index = abs(type_hash) % len(self.COLOR_PALETTE)
        shape_index = abs(type_hash) % len(self.SHAPE_OPTIONS)
        
        color = self.COLOR_PALETTE[color_index]
        shape = self.SHAPE_OPTIONS[shape_index]
        
        # Cache for consistency
        self._type_color_cache[node_type] = color
        self._type_shape_cache[node_type] = shape
        
        return {
            "shape": shape,
            "color": color,
            "icon": "⚫"  # Generic icon for all types
        }
    
    def get_legend_data(self, graph_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate legend data based on actual node types in the graph
        """
        if not graph_data or "nodes" not in graph_data:
            return []
        
        # Get unique node types
        node_types = set()
        for node in graph_data["nodes"]:
            if "type" in node:
                node_types.add(node["type"])
        
        # Generate legend entries
        legend_entries = []
        for node_type in sorted(node_types):
            style = self._get_node_style(node_type)
            legend_entries.append({
                "type": node_type,
                "color": style["color"],
                "shape": style["shape"],
                "icon": style["icon"]
            })
        
        return legend_entries
    
    def _export_cytoscape(self, graph_data: Dict[str, Any]) -> str:
        """Export graph in Cytoscape.js format"""
        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])
        
        cytoscape_data = {
            "elements": {
                "nodes": [
                    {
                        "data": {
                            "id": node["id"],
                            "label": node.get("label", ""),
                            "type": node.get("type", "")
                        }
                    } for node in nodes
                ],
                "edges": [
                    {
                        "data": {
                            "id": edge["id"],
                            "source": edge["source"],
                            "target": edge["target"],
                            "label": edge.get("label", "")
                        }
                    } for edge in edges
                ]
            }
        }
        
        return json.dumps(cytoscape_data, indent=2)
