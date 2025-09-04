#!/usr/bin/env python3
"""
BPMN Diagram Validation Script
Validates that all BPMN files have complete diagram information for visual review.
"""

import os
import sys
from pathlib import Path
import xml.etree.ElementTree as ET


def validate_bpmn_diagram(bpmn_file_path: str) -> dict:
    """
    Validate that a BPMN file has complete diagram information.
    
    Args:
        bpmn_file_path: Path to the BPMN file
        
    Returns:
        Dict with validation results
    """
    result = {
        'file': bpmn_file_path,
        'valid': True,
        'has_diagram': False,
        'has_shapes': False,
        'has_edges': False,
        'process_elements': 0,
        'diagram_shapes': 0,
        'diagram_edges': 0,
        'missing_elements': [],
        'warnings': []
    }
    
    try:
        # Parse XML
        tree = ET.parse(bpmn_file_path)
        root = tree.getroot()
        
        # Define namespaces
        namespaces = {
            'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
            'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
            'dc': 'http://www.omg.org/spec/DD/20100524/DC',
            'di': 'http://www.omg.org/spec/DD/20100524/DI'
        }
        
        # Check for process elements
        process_elements = []
        for element_type in ['startEvent', 'endEvent', 'serviceTask', 'userTask', 'exclusiveGateway', 'parallelGateway', 'sequenceFlow']:
            elements = root.findall(f'.//bpmn:{element_type}', namespaces)
            process_elements.extend(elements)
        
        result['process_elements'] = len(process_elements)
        
        # Check for diagram section
        diagram = root.find('.//bpmndi:BPMNDiagram', namespaces)
        if diagram is not None:
            result['has_diagram'] = True
            
            # Check for shapes
            shapes = root.findall('.//bpmndi:BPMNShape', namespaces)
            result['diagram_shapes'] = len(shapes)
            result['has_shapes'] = len(shapes) > 0
            
            # Check for edges
            edges = root.findall('.//bpmndi:BPMNEdge', namespaces)
            result['diagram_edges'] = len(edges)
            result['has_edges'] = len(edges) > 0
            
            # Check if all process elements have corresponding diagram elements
            process_element_ids = {elem.get('id') for elem in process_elements if elem.get('id') and elem.tag.endswith('sequenceFlow') is False}
            shape_element_ids = {shape.get('bpmnElement') for shape in shapes if shape.get('bpmnElement')}
            
            sequence_flows = [elem for elem in process_elements if elem.tag.endswith('sequenceFlow')]
            sequence_flow_ids = {flow.get('id') for flow in sequence_flows if flow.get('id')}
            edge_element_ids = {edge.get('bpmnElement') for edge in edges if edge.get('bpmnElement')}
            
            # Find missing shapes
            missing_shapes = process_element_ids - shape_element_ids
            if missing_shapes:
                result['missing_elements'].extend([f"Missing shape for: {id}" for id in missing_shapes])
                result['valid'] = False
            
            # Find missing edges
            missing_edges = sequence_flow_ids - edge_element_ids
            if missing_edges:
                result['missing_elements'].extend([f"Missing edge for: {id}" for id in missing_edges])
                result['valid'] = False
                
        else:
            result['valid'] = False
            result['missing_elements'].append("No BPMNDiagram section found")
        
        # Additional validations
        if result['process_elements'] == 0:
            result['warnings'].append("No process elements found")
        
        if result['has_diagram'] and result['diagram_shapes'] == 0:
            result['warnings'].append("Diagram section exists but no shapes defined")
            
        if result['has_diagram'] and result['diagram_edges'] == 0 and len(sequence_flows) > 0:
            result['warnings'].append("Diagram section exists but no edges defined for sequence flows")
            
    except Exception as e:
        result['valid'] = False
        result['missing_elements'].append(f"Error parsing file: {str(e)}")
    
    return result


def print_validation_result(result: dict):
    """Print validation result in a readable format."""
    filename = os.path.basename(result['file'])
    
    if result['valid']:
        print(f"✅ {filename}")
        print(f"   Process elements: {result['process_elements']}")
        print(f"   Diagram shapes: {result['diagram_shapes']}")
        print(f"   Diagram edges: {result['diagram_edges']}")
    else:
        print(f"❌ {filename}")
        for missing in result['missing_elements']:
            print(f"   - {missing}")
    
    if result['warnings']:
        print(f"⚠️  Warnings for {filename}:")
        for warning in result['warnings']:
            print(f"   - {warning}")
    
    print()


def main():
    """Main validation function."""
    bpmn_dir = Path(__file__).parent.parent / "bpmn"
    
    print("🔍 BPMN Diagram Validation")
    print("=" * 40)
    
    if not bpmn_dir.exists():
        print(f"❌ BPMN directory not found: {bpmn_dir}")
        sys.exit(1)
    
    bpmn_files = list(bpmn_dir.glob("*.bpmn"))
    
    if not bpmn_files:
        print("❌ No BPMN files found")
        sys.exit(1)
    
    print(f"Found {len(bpmn_files)} BPMN files:")
    for bpmn_file in bpmn_files:
        print(f"  - {bpmn_file.name}")
    print()
    
    # Validate each file
    all_valid = True
    results = []
    
    for bpmn_file in bpmn_files:
        result = validate_bpmn_diagram(str(bpmn_file))
        results.append(result)
        print_validation_result(result)
        
        if not result['valid']:
            all_valid = False
    
    # Summary
    print("📊 Validation Summary")
    print("-" * 20)
    valid_count = sum(1 for r in results if r['valid'])
    print(f"Valid files: {valid_count}/{len(results)}")
    
    if all_valid:
        print("🎉 All BPMN files have complete diagram information!")
    else:
        print("⚠️  Some BPMN files need diagram information updates")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())




