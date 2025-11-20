#!/usr/bin/env python3
"""
Test for Lattice Input Blocking

Verifies that projects with multiple inputs wait for ALL inputs before processing.
"""

import pytest
import asyncio
from typing import Dict, List, Set


class MockLatticeWorkflow:
    """Mock workflow engine to test input blocking logic."""
    
    def __init__(self):
        self.data_store: Dict[str, Dict] = {}
        self.processing_queue: Set[str] = set()
        self.completed_projects: Set[str] = set()
        self.processing_order: List[str] = []
    
    def get_inputs_for_project(self, project_name: str, project_data: Dict, lattice: Dict) -> Dict:
        """Get inputs for a project and check if all are available."""
        inputs = {}
        missing_inputs = []
        
        # Check parent input
        if project_data.get('parent_name'):
            if project_data['parent_name'] in self.data_store:
                inputs['parent_data'] = self.data_store[project_data['parent_name']]
            else:
                missing_inputs.append(f"parent:{project_data['parent_name']}")
        
        # Check data flow inputs
        upstream_flows = [f for f in lattice.get('data_flows', []) 
                         if f['to_project'] == project_name]
        
        for flow in upstream_flows:
            if flow['from_project'] in self.data_store:
                inputs[flow['data_type']] = self.data_store[flow['from_project']]
            else:
                missing_inputs.append(f"flow:{flow['data_type']} from {flow['from_project']}")
        
        # Check requirements for L1 projects
        if project_data.get('layer') == 1:
            if 'requirements' in self.data_store:
                inputs['requirements'] = self.data_store['requirements']
            else:
                missing_inputs.append('requirements')
        
        all_inputs_ready = len(missing_inputs) == 0
        
        return {
            'inputs': inputs,
            'missing_inputs': missing_inputs,
            'all_inputs_ready': all_inputs_ready
        }
    
    async def process_project(self, project_name: str, project_data: Dict, lattice: Dict):
        """Process a project - blocks if inputs not ready."""
        
        # Prevent duplicate processing
        if project_name in self.processing_queue:
            print(f"⏸️ {project_name} already processing, skipping")
            return
        
        if project_name in self.completed_projects:
            print(f"✅ {project_name} already completed, skipping")
            return
        
        # Check inputs
        input_check = self.get_inputs_for_project(project_name, project_data, lattice)
        
        if not input_check['all_inputs_ready']:
            print(f"⏳ {project_name} waiting for: {input_check['missing_inputs']}")
            return False  # Block - inputs not ready
        
        # All inputs ready - process
        self.processing_queue.add(project_name)
        self.processing_order.append(project_name)
        print(f"🔄 Processing {project_name}...")
        
        # Simulate processing
        await asyncio.sleep(0.1)
        
        # Store results
        self.data_store[project_name] = {
            'project_name': project_name,
            'results': f"Results from {project_name}",
            'status': 'complete'
        }
        
        # Mark complete
        self.processing_queue.remove(project_name)
        self.completed_projects.add(project_name)
        
        print(f"✅ {project_name} complete")
        return True
    
    async def trigger_downstream(self, completed_project: str, lattice: Dict):
        """Trigger downstream projects after completion."""
        downstream = []
        
        for project in lattice['projects']:
            # Check if this project depends on the completed one
            is_downstream = (
                project.get('parent_name') == completed_project or
                any(f['from_project'] == completed_project and f['to_project'] == project['name']
                    for f in lattice.get('data_flows', []))
            )
            
            if is_downstream and project['name'] not in self.completed_projects:
                downstream.append(project)
        
        # Try to process downstream projects
        for project in downstream:
            await self.process_project(project['name'], project, lattice)
    
    async def execute_workflow(self, lattice: Dict):
        """Execute entire workflow."""
        # Set requirements for L1 projects
        self.data_store['requirements'] = "Test requirements"
        
        # Process by layer
        for layer in [1, 2, 3]:
            layer_projects = [p for p in lattice['projects'] if p['layer'] == layer]
            
            # Process all projects in layer
            for project in layer_projects:
                await self.process_project(project['name'], project, lattice)
            
            # Trigger downstream after each layer completes
            for project in layer_projects:
                if project['name'] in self.completed_projects:
                    await self.trigger_downstream(project['name'], lattice)
            
            # Small delay between layers
            await asyncio.sleep(0.1)


def test_single_input_project():
    """Test project with single input processes immediately."""
    workflow = MockLatticeWorkflow()
    
    lattice = {
        'projects': [
            {'name': 'project_a', 'layer': 1, 'parent_name': None},
            {'name': 'project_b', 'layer': 2, 'parent_name': 'project_a'}
        ],
        'data_flows': []
    }
    
    asyncio.run(workflow.execute_workflow(lattice))
    
    # Project A should process first (L1, has requirements)
    assert 'project_a' in workflow.completed_projects
    assert 'project_b' in workflow.completed_projects
    
    # Project B should process after A
    assert workflow.processing_order.index('project_a') < workflow.processing_order.index('project_b')


def test_multiple_inputs_blocking():
    """Test project with multiple inputs waits for ALL inputs."""
    workflow = MockLatticeWorkflow()
    
    lattice = {
        'projects': [
            {'name': 'project_a', 'layer': 1, 'parent_name': None},
            {'name': 'project_b', 'layer': 1, 'parent_name': None},
            {'name': 'project_c', 'layer': 2, 'parent_name': None}  # No parent, but needs both A and B
        ],
        'data_flows': [
            {'from_project': 'project_a', 'to_project': 'project_c', 'data_type': 'data_a'},
            {'from_project': 'project_b', 'to_project': 'project_c', 'data_type': 'data_b'}
        ]
    }
    
    asyncio.run(workflow.execute_workflow(lattice))
    
    # All projects should complete
    assert 'project_a' in workflow.completed_projects
    assert 'project_b' in workflow.completed_projects
    assert 'project_c' in workflow.completed_projects
    
    # Project C should process AFTER both A and B
    a_index = workflow.processing_order.index('project_a')
    b_index = workflow.processing_order.index('project_b')
    c_index = workflow.processing_order.index('project_c')
    
    assert c_index > a_index, "Project C should process after A"
    assert c_index > b_index, "Project C should process after B"
    
    # Project C should only process once (not multiple times)
    assert workflow.processing_order.count('project_c') == 1, "Project C should only process once"


def test_parent_and_data_flow_inputs():
    """Test project that needs both parent and data flow inputs."""
    workflow = MockLatticeWorkflow()
    
    lattice = {
        'projects': [
            {'name': 'parent_project', 'layer': 1, 'parent_name': None},
            {'name': 'sibling_project', 'layer': 1, 'parent_name': None},
            {'name': 'child_project', 'layer': 2, 'parent_name': 'parent_project'}
        ],
        'data_flows': [
            {'from_project': 'sibling_project', 'to_project': 'child_project', 'data_type': 'sibling_data'}
        ]
    }
    
    asyncio.run(workflow.execute_workflow(lattice))
    
    # All should complete
    assert 'parent_project' in workflow.completed_projects
    assert 'sibling_project' in workflow.completed_projects
    assert 'child_project' in workflow.completed_projects
    
    # Child should process after both parent and sibling
    parent_index = workflow.processing_order.index('parent_project')
    sibling_index = workflow.processing_order.index('sibling_project')
    child_index = workflow.processing_order.index('child_project')
    
    assert child_index > parent_index, "Child should process after parent"
    assert child_index > sibling_index, "Child should process after sibling"


def test_no_duplicate_processing():
    """Test that projects don't get processed multiple times."""
    workflow = MockLatticeWorkflow()
    
    lattice = {
        'projects': [
            {'name': 'project_a', 'layer': 1, 'parent_name': None},
            {'name': 'project_b', 'layer': 2, 'parent_name': 'project_a'},
            {'name': 'project_c', 'layer': 2, 'parent_name': 'project_a'},
            {'name': 'project_d', 'layer': 3, 'parent_name': 'project_b'}
        ],
        'data_flows': [
            {'from_project': 'project_c', 'to_project': 'project_d', 'data_type': 'data_c'}
        ]
    }
    
    asyncio.run(workflow.execute_workflow(lattice))
    
    # Each project should appear exactly once in processing order
    for project in lattice['projects']:
        count = workflow.processing_order.count(project['name'])
        assert count == 1, f"{project['name']} processed {count} times, expected 1"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
