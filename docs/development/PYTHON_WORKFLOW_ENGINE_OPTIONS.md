# Python Workflow Engine Options for ODRAS

## Problem Statement

The intelligent lattice demo currently uses JavaScript-based simulation that doesn't properly block on multiple inputs. Projects with multiple upstream dependencies start processing as soon as ANY input arrives, rather than waiting for ALL required inputs.

## Requirements

- **Python-native** (not Java-based like Camunda)
- **Well-established** with active community
- **Low overhead** - minimal dependencies, fast startup
- **Proper dependency management** - blocks until all inputs available
- **Event-driven** - can trigger downstream tasks when inputs complete
- **Lightweight** - suitable for demo/prototype, not enterprise-scale

## Research Summary

### 1. **Prefect** ⭐ Recommended

**Pros:**
- Modern, Pythonic API
- Built-in dependency management
- Excellent for data pipelines
- Good documentation
- Active development
- Can run standalone or with Prefect Cloud
- Handles complex dependencies naturally

**Cons:**
- Requires Prefect server (or cloud) for full features
- More focused on data pipelines than general workflows
- Some overhead for simple use cases

**Installation:**
```bash
pip install prefect
```

**Example:**
```python
from prefect import flow, task

@task
def process_project(project_name, inputs):
    # Process project with LLM
    return results

@flow
def lattice_workflow(lattice):
    # Process L1 projects first
    l1_results = [process_project(p.name, inputs) for p in l1_projects]
    
    # Process L2 projects (waits for L1 dependencies)
    l2_results = [process_project(p.name, l1_results) for p in l2_projects]
    
    # Automatically handles dependencies
```

**Best for:** Data-intensive workflows, complex dependencies, production use

---

### 2. **SpiffWorkflow** ⭐ Best for BPMN

**Pros:**
- Pure Python (no external dependencies)
- BPMN support (can read BPMN files)
- Very lightweight
- Handles complex workflows
- Good for event-driven processes
- Can define workflows in Python or BPMN

**Cons:**
- Smaller community than Prefect/Airflow
- Less documentation
- More manual setup

**Installation:**
```bash
pip install SpiffWorkflow
```

**Example:**
```python
from SpiffWorkflow.workflow import Workflow
from SpiffWorkflow.task import Task

# Define workflow with dependencies
workflow = Workflow()
task1 = workflow.add_task('process_l1', requires=['requirements'])
task2 = workflow.add_task('process_l2', requires=[task1])
task3 = workflow.add_task('process_l3', requires=[task1, task2])  # Multiple inputs

# Automatically blocks until all dependencies ready
workflow.run()
```

**Best for:** BPMN workflows, lightweight orchestration, event-driven processes

---

### 3. **Celery** (Task Queue)

**Pros:**
- Very lightweight
- Excellent for async tasks
- Can chain tasks with dependencies
- Well-established
- Minimal overhead

**Cons:**
- Not a full workflow engine
- Requires message broker (Redis/RabbitMQ)
- Manual dependency management
- More suited for task queues than complex workflows

**Installation:**
```bash
pip install celery redis
```

**Example:**
```python
from celery import chain, group

# Chain tasks with dependencies
workflow = chain(
    process_l1.s(project1),
    process_l2.s(project2),  # Waits for l1
    process_l3.s(project3)   # Waits for l2
)
```

**Best for:** Simple task chains, async processing, distributed tasks

---

### 4. **Luigi** (Spotify)

**Pros:**
- Handles dependency resolution well
- Good for batch pipelines
- Built-in visualization
- Well-established

**Cons:**
- More focused on batch jobs
- Requires Luigi daemon
- Less suitable for interactive workflows
- Heavier than needed for this use case

**Best for:** Batch data processing, ETL pipelines

---

### 5. **Apache Airflow**

**Pros:**
- Industry standard
- Excellent UI
- Very powerful
- Great for complex workflows

**Cons:**
- **Too heavy** for this use case
- Requires database, scheduler, webserver
- Complex setup
- Overkill for demo/prototype

**Best for:** Enterprise data pipelines, complex scheduling

---

## Recommendation: **Prefect** or **SpiffWorkflow**

### For Quick Implementation: **Prefect**
- Modern Python API
- Excellent dependency handling
- Good documentation
- Can start simple, scale later

### For Lightweight/BPMN: **SpiffWorkflow**
- Pure Python, minimal dependencies
- BPMN support if needed
- Very lightweight
- Good for event-driven workflows

## Implementation Approach

### Option 1: Prefect Integration

```python
# backend/services/lattice_workflow.py
from prefect import flow, task
from typing import Dict, List

@task
async def process_project_task(project: Dict, requirements: str, upstream_data: Dict):
    """Process a single project with LLM."""
    # Call LLM service
    response = await llm_service.process_project(project, requirements, upstream_data)
    return response['result']

@flow
async def execute_lattice_workflow(lattice: Dict, requirements: str):
    """Execute lattice workflow with proper dependency management."""
    
    # Store results by project name
    results = {}
    
    # Process by layer (ensures dependencies ready)
    for layer in [1, 2, 3]:
        layer_projects = [p for p in lattice['projects'] if p['layer'] == layer]
        
        # Process all projects in layer (can run in parallel)
        layer_tasks = []
        for project in layer_projects:
            # Collect upstream data
            upstream_data = {}
            
            # Get parent data
            if project.get('parent_name') and project['parent_name'] in results:
                upstream_data['parent_data'] = results[project['parent_name']]
            
            # Get data flow inputs
            for flow in lattice['data_flows']:
                if flow['to_project'] == project['name']:
                    if flow['from_project'] in results:
                        upstream_data[flow['data_type']] = results[flow['from_project']]
            
            # Create task (Prefect handles dependencies automatically)
            task = process_project_task(
                project=project,
                requirements=requirements,
                upstream_data=upstream_data
            )
            layer_tasks.append((project['name'], task))
        
        # Wait for all tasks in layer to complete
        for project_name, task_result in layer_tasks:
            results[project_name] = await task_result
    
    return results
```

### Option 2: SpiffWorkflow Integration

```python
# backend/services/lattice_workflow.py
from SpiffWorkflow.workflow import Workflow
from SpiffWorkflow.task import Task

class LatticeWorkflowEngine:
    def __init__(self):
        self.workflow = Workflow()
        self.project_tasks = {}
    
    def build_workflow(self, lattice: Dict):
        """Build workflow from lattice structure."""
        
        # Create tasks for each project
        for project in lattice['projects']:
            task = self.workflow.add_task(
                name=project['name'],
                task_class=ProjectProcessingTask,
                project_data=project
            )
            self.project_tasks[project['name']] = task
            
            # Set dependencies
            dependencies = []
            
            # Parent dependency
            if project.get('parent_name'):
                dependencies.append(self.project_tasks[project['parent_name']])
            
            # Data flow dependencies
            for flow in lattice['data_flows']:
                if flow['to_project'] == project['name']:
                    dependencies.append(self.project_tasks[flow['from_project']])
            
            # Set dependencies (blocks until all ready)
            task.requires = dependencies
        
        return self.workflow
    
    async def execute(self, requirements: str):
        """Execute workflow."""
        self.workflow.run()
```

## Current Fix (JavaScript)

I've already fixed the immediate issue in the JavaScript code:

1. **Input validation** - `getInputDataForProject` now returns `{inputs, missingInputs, allInputsReady}`
2. **Blocking logic** - `processProject` checks if all inputs are ready before processing
3. **Waiting state** - Projects show "waiting" state when inputs aren't ready
4. **Smart triggering** - `triggerDownstreamProjects` checks if downstream projects are ready before starting

## Next Steps

1. **Immediate:** Current JavaScript fix handles input blocking
2. **Short-term:** Consider Prefect for backend workflow orchestration
3. **Long-term:** Evaluate SpiffWorkflow if BPMN support needed

## References

- Prefect: https://www.prefect.io/
- SpiffWorkflow: https://github.com/sartography/SpiffWorkflow
- Celery: https://docs.celeryproject.org/
- Luigi: https://github.com/spotify/luigi
