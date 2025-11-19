<!-- 1a95a09b-a7e2-4ff5-a50a-f5e341886056 f1bff7e0-c99e-4bda-8e2c-4b36b18c0bdb -->
# ODRAS Plugin Architecture Implementation

## Overview

Transform ODRAS from a monolithic application into a plugin-based architecture where workbenches, DAS systems, and workers are independently managed, registered, and loaded. This enables hot-swappable components and dramatically simplifies adding new workbenches or upgrading DAS without core system changes.

## Workbench Inventory & Migration Roadmap

### Current ODRAS Workbenches (Existing)

1. **Requirements Workbench** - Requirements extraction, management, and analysis
2. **Ontology Workbench** - Visual ontology editing, class/property management
3. **Knowledge Workbench** - Document management, RAG, knowledge search
4. **Conceptualizer Workbench** - System architecture visualization and configuration
5. **Files Workbench** - Document upload and organization
6. **Project Workbench** - Project settings and management
7. **Graph Workbench** - Neo4j graph visualization
8. **Thread Manager Workbench** - DAS conversation thread management
9. **Admin Workbench** - User and system administration
10. **Settings Workbench** - User preferences

### Planned Workbenches (From DADMS Reference)

11. **BPMN Workbench** - Process design, BPMN diagram editor (replacing Process Workbench)
12. **Process Thread Manager** - Process-specific thread management
13. **Context Manager Workbench** - Persona, prompt, tool, and team management
14. **SysML Workbench** - Systems Modeling Language integration
15. **JupyterLab Integration** - Embedded Jupyter notebooks for analysis
16. **VS Code Editor Integration** - Embedded code editor
17. **Project Dashboard** - Comprehensive project overview and metrics
18. **Thread Impact Analysis** - Analyze thread relationships and impacts
19. **Data Manager Workbench** - Data pipelines, connectors, transformations (Core decoupling component)

### Additional Workbenches (Stretch Goals)

**Systems Engineering & Analysis:**

20. **Traceability Matrix Workbench** - Requirements-to-design-to-test traceability visualization and management
21. **Trade Study Workbench** - Multi-criteria decision analysis, alternatives comparison, weighted scoring
22. **Impact Analysis Workbench** - Change impact analysis across requirements, design, and implementation
23. **Verification & Validation Workbench** - Test planning, execution tracking, V&V matrix management
24. **Risk Management Workbench** - Risk identification, assessment, mitigation tracking
25. **Interface Management Workbench** - System interface definition, ICD generation and management

**Analysis & Simulation:**

26. **Tabelizer Workbench** - Pull data from published/external sources, create dynamic comparison tables, vendor solution evaluation against ontology individuals and requirements
27. **Simulation Workbench** - Model execution, scenario analysis, performance prediction
28. **Sensitivity Analysis Workbench** - Parameter sensitivity studies, Monte Carlo analysis
29. **Cost & Schedule Analysis Workbench** - Project costing, schedule analysis, earned value management
30. **Performance Analysis Workbench** - System performance metrics, KPI tracking, benchmarking

**Documentation & Reporting:**

30. **Document Generation Workbench** - Automated document generation from ontology/requirements data
31. **Report Builder Workbench** - Custom report templates, automated reporting pipelines
32. **Export/Import Workbench** - Data exchange with external tools (ReqIF, OSLC, CSV, Excel)
33. **Version Control Workbench** - Document versioning, baseline management, comparison views

**Collaboration & Review:**

34. **Review & Approval Workbench** - Structured review workflows, approval chains, commenting
35. **Collaborative Editing Workbench** - Real-time multi-user editing with conflict resolution
36. **Stakeholder Management Workbench** - Stakeholder identification, RACI matrices, communication plans
37. **Change Management Workbench** - Change request tracking, impact assessment, approval workflows

**Data Quality & Governance:**

38. **Data Quality Dashboard** - Data completeness, consistency, accuracy metrics
39. **Audit Log Workbench** - Comprehensive audit trail visualization and analysis
40. **Compliance Workbench** - Regulatory compliance tracking, standards mapping
41. **Metadata Management Workbench** - Data dictionary, lineage tracking, catalog management

**Integration & Automation:**

42. **API Management Workbench** - API testing, documentation, usage analytics
43. **Webhook & Event Manager** - Event subscription management, webhook configuration
44. **Automation Studio** - No-code/low-code automation builder for common tasks
45. **ETL Workbench** - Extract-Transform-Load pipelines for external data sources

**Advanced Features:**

46. **Machine Learning Workbench** - Model training, deployment, inference on ODRAS data
47. **Natural Language Processing Workbench** - Text analysis, entity extraction, classification
48. **Visualization Studio** - Custom visualization builder, chart templates, dashboards
49. **Search & Discovery Workbench** - Advanced search with facets, saved searches, recommendations
50. **Configuration Management Workbench** - Configuration items, baseline management, CM plans

### Workbench Migration Priority

**Phase 1 - Core Decoupling** (Migrate First):

- Data Manager Workbench (NEW - critical for decoupling)
- BPMN Workbench (NEW - replaces current process system)
- Process Thread Manager (integration point)

**Phase 2 - Primary Workbenches** (High Usage):

- Requirements Workbench
- Ontology Workbench  
- Knowledge Workbench
- Project Dashboard (enhanced version of Project Workbench)

**Phase 3 - Specialized Workbenches**:

- Conceptualizer Workbench
- Context Manager Workbench
- Thread Manager/Impact Analysis
- SysML Workbench

**Phase 4 - Development Tools**:

- JupyterLab Integration
- VS Code Editor Integration
- Graph Workbench
- Admin/Settings Workbenches

### Workbench Plugin Structure Template

Each workbench follows this structure:

```
backend/plugins/workbenches/{workbench_name}/
├── manifest.yaml              # Plugin metadata
├── __init__.py
├── plugin.py                  # WorkbenchPlugin implementation
├── api/
│   ├── __init__.py
│   └── routes.py             # FastAPI routes
├── services/
│   ├── __init__.py
│   └── {service}.py          # Business logic
├── models/
│   ├── __init__.py
│   └── schemas.py            # Pydantic models
├── frontend/
│   ├── {workbench}-ui.js     # UI rendering
│   ├── {workbench}-api.js    # API client
│   └── {workbench}-logic.js  # Business logic
└── migrations/
    └── {version}_{desc}.sql  # Database migrations
```

## PRE-PHASE: Critical Refactoring (Prerequisite)

**Problem**: Current architecture has massive monolithic files that will be difficult to work with during plugin migration:

- `backend/main.py`: 3,764 lines - all startup, routing, and endpoint definitions
- `frontend/app.html`: 31,522 lines - all UI, workbenches, and JavaScript

**Solution**: Refactor into modular structure BEFORE implementing plugin system.

### Pre-0.1: Backend Refactoring Strategy

Create modular structure from `backend/main.py`:

```
backend/
├── main.py                    # Slim entry point (~200 lines)
├── app_factory.py             # FastAPI app creation and config
├── startup/
│   ├── __init__.py
│   ├── database.py            # DB initialization
│   ├── services.py            # Service initialization (RAG, embeddings, etc.)
│   ├── middleware.py          # Middleware setup
│   └── routers.py             # Router registration (temporary until plugin system)
├── api/
│   └── [existing router files remain]
└── services/
    └── [existing service files remain]
```

Refactored `backend/main.py` structure:

```python
from backend.app_factory import create_app
from backend.startup import initialize_application

app = create_app()

@app.on_event("startup")
async def startup():
    await initialize_application(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Pre-0.2: Frontend Refactoring Strategy

Break up `frontend/app.html` (31,522 lines) into modular structure:

```
frontend/
├── index.html                 # Main entry point (~200 lines)
├── js/
│   ├── core/
│   │   ├── app-init.js        # Application initialization
│   │   ├── state-manager.js   # Global state management
│   │   ├── event-bus.js       # Frontend event system
│   │   └── router.js          # Client-side routing
│   ├── components/
│   │   ├── toolbar.js         # Main toolbar
│   │   ├── panel-manager.js   # Panel/workbench management
│   │   └── modal-dialogs.js   # Shared dialogs
│   ├── workbenches/
│   │   ├── requirements/
│   │   │   ├── requirements-ui.js
│   │   │   ├── requirements-api.js
│   │   │   └── requirements-logic.js
│   │   ├── ontology/
│   │   │   ├── ontology-ui.js
│   │   │   ├── ontology-tree.js
│   │   │   ├── ontology-canvas.js
│   │   │   └── ontology-api.js
│   │   ├── knowledge/
│   │   │   ├── knowledge-ui.js
│   │   │   └── knowledge-api.js
│   │   └── [other workbenches...]
│   ├── das/
│   │   ├── das-ui.js          # DAS dock interface
│   │   └── das-api.js         # DAS communication
│   └── utils/
│       ├── api-client.js      # Centralized API client
│       └── helpers.js         # Utility functions
└── css/
    ├── main.css               # Base styles
    ├── workbenches.css        # Workbench-specific styles
    └── components.css         # Component styles
```

### Pre-0.3: Refactoring Implementation Steps

**Step 1: Extract Backend Startup Logic** (1-2 days)

1. Create `backend/app_factory.py` with FastAPI app creation
2. Create `backend/startup/` modules for initialization logic
3. Move router registration to `backend/startup/routers.py`
4. Move service initialization to `backend/startup/services.py`
5. Slim down `backend/main.py` to ~200 lines
6. Test: Verify all existing functionality works

**Step 2: Extract Frontend Core** (2-3 days)

1. Create `frontend/js/core/` with initialization and state management
2. Extract toolbar and panel management to `frontend/js/components/`
3. Create centralized API client in `frontend/js/utils/api-client.js`
4. Update `frontend/index.html` to load modular JavaScript
5. Test: Verify all UI functionality works

**Step 3: Extract Workbench Modules** (3-4 days)

1. Extract Requirements Workbench to `frontend/js/workbenches/requirements/`
2. Extract Ontology Workbench to `frontend/js/workbenches/ontology/`
3. Extract Knowledge Workbench to `frontend/js/workbenches/knowledge/`
4. Extract remaining workbenches
5. Each workbench should have: UI module, API module, business logic module
6. Test each workbench independently

**Step 4: Extract DAS Module** (1 day)

1. Move DAS-specific code to `frontend/js/das/`
2. Separate UI rendering from API communication
3. Test DAS functionality

**Step 5: Validation & Documentation** (1 day)

1. Full system integration test
2. Update developer documentation with new structure
3. Create module dependency diagram
4. Commit refactored codebase

### Pre-0.4: Benefits of Refactoring First

**For Plugin Implementation:**

- Each workbench already isolated in its own module - easier to wrap in plugin
- Clear API boundaries already established
- Startup logic separated - easier to replace with plugin loader
- Frontend components modular - easier to make plugin-discoverable

**For Development:**

- Easier to grep specific functionality (single file per feature)
- Reduced cognitive load (work on one module at a time)
- Better testing isolation
- Cleaner git diffs and code reviews

**For Plugin Migration:**

- `frontend/js/workbenches/requirements/` → `backend/plugins/workbenches/requirements/frontend/`
- Backend routers already separated - easy to move into plugin structure
- Startup sequence already modular - easy to replace with plugin loader

### Pre-0.5: Testing Strategy During Refactoring

**Critical**: After each refactoring step, verify existing functionality:

```bash
# Full stack test after each step
./odras.sh clean -y
./odras.sh init-db
./odras.sh start

# Manual verification checklist:
# - Open all workbenches
# - Test DAS communication
# - Upload a file
# - Create an ontology
# - Extract requirements
# - Test knowledge search
```

**Automated testing**: Run existing test suite after each step to catch regressions.

## Phase 0: Core Execution Infrastructure

### 0.0 ODRAS Process Engine (BPMN-Compatible Native Execution)

**Problem with Camunda**: External dependency, complex integration, difficult to debug, hard for DAS to programmatically create processes.

**Solution**: Build lightweight, native ODRAS Process Engine that:

- **Uses BPMN 2.0 XML as definition format** (standard modeling language)
- **Executes natively in ODRAS** (no external Camunda dependency)
- **Supports BPMN visual glyphs** (humans and DAS communicate using standard notation)
- **Enables DAS process creation** (LLM generates valid BPMN XML)
- **Integrates with plugin system** (tasks can call any plugin API)

Create `backend/services/process_engine.py`:

```python
class ProcessDefinition(BaseModel):
    """Process definition - can be created by users or DAS"""
    id: str
    name: str
    version: str
    description: str
    created_by: str  # user_id or "das"
    tasks: List[TaskDefinition]
    transitions: List[TransitionRule]
    variables: Dict[str, Any] = {}
    metadata: Dict = {}

class TaskDefinition(BaseModel):
    """Individual task in a process"""
    id: str
    name: str
    type: TaskType  # PLUGIN_API_CALL, WORKER_TASK, HUMAN_TASK, SCRIPT, DECISION
    plugin_id: Optional[str]  # Which plugin executes this task
    api_endpoint: Optional[str]  # For PLUGIN_API_CALL tasks
    worker_type: Optional[str]  # For WORKER_TASK tasks
    script: Optional[str]  # For SCRIPT tasks (Python code)
    input_mapping: Dict[str, str]  # Map process variables to task inputs
    output_mapping: Dict[str, str]  # Map task outputs to process variables
    retry_policy: RetryPolicy
    timeout_seconds: int = 300

class TaskType(Enum):
    PLUGIN_API_CALL = "plugin_api_call"  # Call plugin API endpoint
    WORKER_TASK = "worker_task"  # Execute via worker
    HUMAN_TASK = "human_task"  # Wait for human input
    SCRIPT = "script"  # Execute Python script
    DECISION = "decision"  # Conditional branch
    PARALLEL_GATEWAY = "parallel"  # Fork/join parallel execution
    EVENT_WAIT = "event_wait"  # Wait for event from event bus

class ProcessInstance(BaseModel):
    """Running instance of a process"""
    id: str
    definition_id: str
    state: ProcessState
    current_tasks: List[str]  # Active task IDs
    variables: Dict[str, Any]
    history: List[ProcessEvent]
    created_at: datetime
    updated_at: datetime
    created_by: str
    project_id: Optional[str]

class ProcessState(Enum):
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ProcessEngine:
    """Core process execution engine"""
    
    def __init__(self, event_bus: EventBus, plugin_registry: PluginRegistry):
        self.event_bus = event_bus
        self.plugin_registry = plugin_registry
        self.definitions: Dict[str, ProcessDefinition] = {}
        self.instances: Dict[str, ProcessInstance] = {}
    
    async def register_definition(self, definition: ProcessDefinition):
        """Register a process definition (from user or DAS)"""
        self.definitions[definition.id] = definition
        await self.event_bus.publish(Event(
            type=EventType.PROCESS_REGISTERED,
            source_plugin="process_engine",
            data={"definition_id": definition.id}
        ))
    
    async def start_process(self, definition_id: str, variables: Dict = {}) -> ProcessInstance:
        """Start a new process instance"""
        pass
    
    async def execute_task(self, instance_id: str, task_id: str):
        """Execute a specific task"""
        instance = self.instances[instance_id]
        definition = self.definitions[instance.definition_id]
        task = next(t for t in definition.tasks if t.id == task_id)
        
        if task.type == TaskType.PLUGIN_API_CALL:
            # Call plugin API endpoint
            result = await self._execute_plugin_api_call(task, instance.variables)
        elif task.type == TaskType.WORKER_TASK:
            # Queue task for worker
            result = await self._queue_worker_task(task, instance.variables)
        elif task.type == TaskType.SCRIPT:
            # Execute Python script in sandbox
            result = await self._execute_script(task, instance.variables)
        elif task.type == TaskType.EVENT_WAIT:
            # Wait for event from event bus
            result = await self._wait_for_event(task, instance.variables)
        
        # Update process variables with task output
        instance.variables.update(task.output_mapping)
        
        # Transition to next task(s)
        await self._transition(instance, task)
    
    async def _execute_plugin_api_call(self, task: TaskDefinition, variables: Dict):
        """Execute task by calling plugin API"""
        plugin = self.plugin_registry.get(task.plugin_id)
        # Make API call to plugin endpoint
        pass
    
    async def get_process_state(self, instance_id: str) -> ProcessInstance:
        """Get current state of process instance"""
        return self.instances[instance_id]
    
    async def cancel_process(self, instance_id: str):
        """Cancel a running process"""
        pass
```

### 0.0.1 DAS Process Creation

Allow DAS to programmatically create and test processes:

```python
class DASProcessCreator:
    """Service for DAS to create, test, and deploy processes"""
    
    async def create_process_from_description(self, description: str) -> ProcessDefinition:
        """
        DAS uses LLM to convert natural language description into process definition.
        Example: "Extract requirements from uploaded PDF, then create individuals in ontology"
        """
        # Use LLM to generate process definition
        prompt = f"""Convert this process description into a ProcessDefinition:
        {description}
        
        Available plugins: {self.get_available_plugins()}
        Available API endpoints: {self.get_api_endpoints()}
        """
        
        # LLM generates JSON process definition
        definition_json = await llm.generate(prompt)
        definition = ProcessDefinition.parse_raw(definition_json)
        
        return definition
    
    async def test_process(self, definition: ProcessDefinition, test_data: Dict) -> TestResult:
        """Test process with sample data before deploying"""
        pass
    
    async def deploy_process(self, definition: ProcessDefinition):
        """Deploy tested process to production"""
        await process_engine.register_definition(definition)
```

### 0.0.2 Process Workbench Plugin

Create workbench for visualizing and managing processes:

`backend/plugins/workbenches/process_workbench/`:

- Visual process designer (drag-and-drop tasks)
- Process instance monitoring
- Process state visualization
- Process testing interface
- DAS-created process review and approval

## Phase 0.1: Event Bus & Data Fabric Infrastructure

### 0.1 Event Bus Architecture

Leverage existing Redis infrastructure and extend for comprehensive event-driven communication:

Create `backend/services/event_bus.py`:

```python
class EventType(Enum):
    DATA_CREATED = "data.created"
    DATA_UPDATED = "data.updated"
    DATA_DELETED = "data.deleted"
    WORKFLOW_STARTED = "workflow.started"
    PLUGIN_REGISTERED = "plugin.registered"

class Event(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType
    source_plugin: str        # Plugin ID that published event
    timestamp: datetime
    data: Dict[str, Any]
    schema_version: str       # For schema evolution
    correlation_id: Optional[str]  # Track related events
    metadata: Dict = {}

class EventBus:
    async def publish(self, event: Event)
    async def subscribe(self, event_type: EventType, handler: Callable)
    async def get_event_history(self, correlation_id: str) -> List[Event]
```

### 0.2 Schema Registry

Create `backend/services/schema_registry.py`:

```python
class SchemaRegistry:
    """Manages data contracts between plugins"""
    
    def register_schema(self, name: str, version: str, schema: Dict)
    def validate(self, data: Dict, schema_name: str, version: str) -> bool
    def get_schema(self, name: str, version: str) -> Dict
    def check_compatibility(self, old_version: str, new_version: str) -> bool
```

Plugins register their data schemas (e.g., "requirement", "ontology_class") so the Data Manager can validate and transform data correctly.

### 0.3 Data Contract Definitions

Create `backend/schemas/data_contracts/`:

```
data_contracts/
├── requirement_v1.json
├── ontology_class_v1.json
├── individual_v1.json
├── knowledge_chunk_v1.json
└── das_message_v1.json
```

Example `requirement_v1.json`:

```json
{
  "type": "object",
  "properties": {
    "id": {"type": "string"},
    "text": {"type": "string"},
    "source": {"type": "string"},
    "metadata": {"type": "object"}
  },
  "required": ["id", "text"]
}
```

## Phase 1: Core Plugin Infrastructure

### 1.1 Plugin Manifest System

Create `backend/plugins/plugin_manifest.py` defining the plugin contract:

```python
class PluginType(Enum):
    WORKBENCH = "workbench"
    DAS_ENGINE = "das_engine"
    WORKER = "worker"
    MIDDLEWARE = "middleware"

class PluginManifest(BaseModel):
    id: str                           # Unique identifier (e.g., "requirements_workbench")
    name: str                         # Display name
    version: str                      # Semantic version (e.g., "1.2.3")
    type: PluginType
    description: str
    author: str
    license: Optional[str]
    homepage: Optional[str]
    
    # Dependencies and compatibility
    dependencies: List[str] = []      # Other plugin IDs required
    python_requires: str = ">=3.10"   # Python version requirement
    odras_api_version: str = "1.0"    # Compatible ODRAS API version
    
    # API and routing
    api_prefix: Optional[str]         # For workbench plugins (/api/requirements)
    enabled: bool = True
    
    # Configuration and validation
    config_schema: Optional[Dict]     # JSON schema for plugin-specific config
    permissions: List[str] = []       # Required permissions
    
    # Security and isolation
    trusted: bool = False             # Allow elevated privileges
    sandbox_enabled: bool = True      # Run in isolated context
    max_memory_mb: int = 512          # Memory limit
    max_execution_time_sec: int = 300 # Timeout for plugin operations
    
    # Health and monitoring
    health_check_endpoint: Optional[str]  # Plugin health check path
    metrics_enabled: bool = True
```

### 1.2 Plugin Registry

Create `backend/plugins/plugin_registry.py`:

```python
class PluginRegistry:
    def __init__(self):
        self._plugins: Dict[str, Plugin] = {}
        self._startup_hooks: List[Callable] = []
        self._shutdown_hooks: List[Callable] = []
    
    def register(self, manifest: PluginManifest, module: Any)
    def get_plugins_by_type(self, plugin_type: PluginType) -> List[Plugin]
    def resolve_dependencies(self) -> List[Plugin]  # Topological sort
    async def initialize_all(self, app: FastAPI, settings: Settings)
    async def shutdown_all()
```

### 1.3 Plugin Discovery & Loader

Create `backend/plugins/plugin_loader.py`:

```python
class PluginLoader:
    def discover_plugins(self, plugin_dirs: List[Path]) -> List[PluginManifest]
    def load_plugin(self, manifest: PluginManifest) -> Plugin
    def validate_plugin(self, plugin: Plugin) -> bool
```

Plugins will be discovered from:

- `backend/plugins/workbenches/`
- `backend/plugins/das_engines/`
- `backend/plugins/workers/`

### 1.4 Configuration System

Add to `backend/services/config.py`:

```python
# Plugin Configuration
plugins_enabled: bool = True
plugins_directory: str = "backend/plugins"
plugins_config_file: str = "config/plugins.yaml"
plugin_compatibility_mode: bool = True  # Support old hard-coded routes during migration
```

Create `config/plugins.yaml`:

```yaml
enabled_plugins:
  - requirements_workbench
  - ontology_workbench
  - knowledge_workbench
  - das2_engine
  - external_task_worker
  
plugin_settings:
  requirements_workbench:
    feature_flags:
      enable_auto_extraction: true
```

## Phase 1.5: Data Manager Workbench (Core Decoupling Layer)

### 1.5.1 Data Manager Workbench Plugin

Create the central data orchestration layer inspired by DeepLynx patterns:

`backend/plugins/workbenches/data_manager/`:

```python
class DataManagerPlugin(WorkbenchPlugin):
    """Central data orchestration and transformation layer"""
    
    def __init__(self):
        self.connectors: Dict[str, DataConnector] = {}
        self.pipelines: Dict[str, DataPipeline] = {}
        self.subscriptions: Dict[str, DataSubscription] = {}
```

### 1.5.2 Data Connectors

```python
class DataConnector(ABC):
    """Base class for data connectors between plugins"""
    
    source_plugin: str
    target_plugin: str
    source_schema: str        # e.g., "requirement_v1"
    target_schema: str        # e.g., "individual_v1"
    transform_rules: List[TransformRule]
    
    @abstractmethod
    async def sync(self, data: Dict) -> Dict
    
    @abstractmethod
    async def validate_compatibility(self) -> bool

class RequirementsToIndividualsConnector(DataConnector):
    """Example: Sync requirements to ontology individuals table"""
    
    async def sync(self, requirement: Dict) -> Dict:
        # Transform requirement to individual format
        # Publish event for ontology workbench to consume
        pass
```

### 1.5.3 Data Pipelines

```python
class DataPipeline:
    """Multi-step data transformation pipeline"""
    
    id: str
    steps: List[PipelineStep]
    trigger: EventType        # What event triggers this pipeline
    enabled: bool
    
    async def execute(self, event: Event) -> PipelineResult
    async def validate(self) -> bool
```

### 1.5.4 Data Subscriptions

```python
class DataSubscription:
    """Plugin subscription to data changes"""
    
    subscriber_plugin: str
    event_types: List[EventType]
    filters: Dict              # Filter events by criteria
    transform: Optional[Callable]  # Transform before delivery
    
    async def deliver(self, event: Event)
```

## Phase 1.6: API Gateway & Dynamic Route Registration

### 1.6.1 API Gateway Architecture

Create `backend/api/gateway.py`:

```python
class APIGateway:
    """Central API gateway managing all plugin routes"""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.plugin_routes: Dict[str, APIRouter] = {}
        self.route_metadata: Dict[str, RouteMetadata] = {}
    
    async def register_plugin_api(self, plugin: Plugin):
        """Dynamically register plugin's API routes"""
        if hasattr(plugin, 'get_api_router'):
            router = plugin.get_api_router()
            prefix = f"/api/{plugin.manifest.id}"
            
            # Add route metadata for OpenAPI generation
            self.route_metadata[plugin.manifest.id] = RouteMetadata(
                plugin_id=plugin.manifest.id,
                version=plugin.manifest.version,
                api_version=plugin.manifest.odras_api_version,
                tags=[plugin.manifest.type.value]
            )
            
            # Register with versioning support
            self.app.include_router(router, prefix=prefix, tags=[plugin.manifest.name])
            self.plugin_routes[plugin.manifest.id] = router
    
    async def unregister_plugin_api(self, plugin_id: str):
        """Remove plugin routes (for hot-swapping)"""
        pass
    
    def get_openapi_schema(self) -> Dict:
        """Generate comprehensive OpenAPI 3.x schema including all plugins"""
        pass
```

### 1.6.2 Enhanced OpenAPI Generation for LLMs

Create `backend/api/openapi_enhancer.py`:

```python
class OpenAPIEnhancer:
    """Enhance OpenAPI schemas for LLM consumption"""
    
    def enhance_for_llm_tools(self, openapi_schema: Dict) -> Dict:
        """
        Transform OpenAPI schema into LLM-friendly format with:
        - Clear operation descriptions for function calling
        - Parameter descriptions optimized for LLM understanding
        - Examples for each endpoint
        - Semantic tags for operation grouping
        """
        pass
    
    def generate_plugin_specific_schema(self, plugin_id: str) -> Dict:
        """Generate OpenAPI schema for specific plugin only"""
        pass
    
    def generate_mcp_tools_manifest(self) -> Dict:
        """Generate MCP (Model Context Protocol) tools manifest"""
        pass
```

### 1.6.3 API Versioning Strategy

Implement semantic versioning at both plugin and API levels:

```python
class APIVersion:
    major: int  # Breaking changes
    minor: int  # New features, backward compatible
    patch: int  # Bug fixes
    
    # URL patterns:
    # /api/v1/requirements/...          (Major version in URL)
    # /api/requirements/... (Accept: application/vnd.odras.v1+json)  (Header-based)

class PluginAPIRouter(APIRouter):
    """Extended router with versioning support"""
    
    def __init__(self, plugin_id: str, version: str):
        super().__init__(
            prefix=f"/api/{plugin_id}",
            tags=[plugin_id]
        )
        self.api_version = APIVersion.parse(version)
    
    def route_versioned(self, path: str, **kwargs):
        """Register route with version support"""
        pass
```

## Phase 2: Plugin Interfaces & Base Classes

### 2.1 Workbench Plugin Interface

Create `backend/plugins/interfaces/workbench_plugin.py`:

```python
class WorkbenchPlugin(ABC):
    manifest: PluginManifest
    router: APIRouter
    
    @abstractmethod
    async def initialize(self, app: FastAPI, settings: Settings, db: DatabaseService)
    
    @abstractmethod
    async def shutdown(self)
    
    @abstractmethod
    def get_frontend_config(self) -> Dict  # UI panel config, icons, shortcuts
    
    def get_database_migrations(self) -> List[str]  # Optional migrations
    def get_permissions(self) -> List[str]  # Required permissions
```

### 2.2 DAS Engine Plugin Interface

Create `backend/plugins/interfaces/das_plugin.py`:

```python
class DASEnginePlugin(ABC):
    manifest: PluginManifest
    
    @abstractmethod
    async def initialize(self, settings: Settings, rag_service, db_service, redis_client)
    
    @abstractmethod
    async def process_message(self, message: str, context: Dict) -> DASResponse
    
    @abstractmethod
    async def get_suggestions(self, context: Dict) -> List[str]
    
    def get_api_router(self) -> Optional[APIRouter]
```

### 2.3 Worker Plugin Interface

Create `backend/plugins/interfaces/worker_plugin.py`:

```python
class WorkerPlugin(ABC):
    manifest: PluginManifest
    
    @abstractmethod
    async def start(self)
    
    @abstractmethod
    async def stop(self)
    
    @abstractmethod
    def get_task_handlers(self) -> Dict[str, Callable]
    
    def get_health_check(self) -> Callable
```

## Phase 3: Migrate Existing Components to Plugins

### 3.1 Migrate Requirements Workbench

Create `backend/plugins/workbenches/requirements_workbench/`:

```
requirements_workbench/
├── manifest.yaml
├── __init__.py
├── plugin.py          # WorkbenchPlugin implementation
├── api.py            # Existing backend/api/requirements.py
├── services.py       # Workbench-specific services
└── migrations/       # SQL migrations for this workbench
```

In `plugin.py`:

```python
class RequirementsWorkbenchPlugin(WorkbenchPlugin):
    def __init__(self):
        self.manifest = load_manifest("manifest.yaml")
        self.router = create_router_from_api()
    
    async def initialize(self, app, settings, db):
        # Register routes, initialize services
        pass
```

### 3.2 Migrate Ontology, Knowledge, Conceptualizer Workbenches

Following the same pattern as Requirements Workbench, create plugin directories for:

- `backend/plugins/workbenches/ontology_workbench/`
- `backend/plugins/workbenches/knowledge_workbench/`
- `backend/plugins/workbenches/conceptualizer_workbench/`

Each includes manifest.yaml, plugin.py implementing WorkbenchPlugin, and existing API code.

### 3.3 Migrate DAS2 Engine

Create `backend/plugins/das_engines/das2_engine/`:

```
das2_engine/
├── manifest.yaml
├── __init__.py
├── plugin.py                    # DASEnginePlugin implementation
├── core_engine.py              # Existing das2_core_engine.py
├── api.py                      # Existing backend/api/das2.py
├── rag_service.py
└── project_intelligence.py
```

### 3.4 Migrate Workers

Create plugin directories:

- `backend/plugins/workers/external_task_worker/`
- `backend/plugins/workers/eventcapture2_worker/`
- `backend/plugins/workers/ingestion_worker/`

Each implements WorkerPlugin interface with start/stop lifecycle and task handlers.

## Phase 4: Update Application Bootstrap

### 4.1 Modify `backend/main.py`

Replace hard-coded router includes with plugin system:

```python
# NEW: Plugin-based initialization
from backend.plugins.plugin_registry import PluginRegistry
from backend.plugins.plugin_loader import PluginLoader

app = FastAPI(title="ODRAS API", version="0.1.0")
plugin_registry = PluginRegistry()

@app.on_event("startup")
async def startup():
    if settings.plugins_enabled:
        loader = PluginLoader()
        plugins = loader.discover_plugins([Path(settings.plugins_directory)])
        
        for manifest in plugins:
            if manifest.id in settings.enabled_plugins:
                plugin = loader.load_plugin(manifest)
                plugin_registry.register(manifest, plugin)
        
        await plugin_registry.initialize_all(app, settings)
    
    # COMPATIBILITY MODE: Support old hard-coded routes
    if settings.plugin_compatibility_mode:
        app.include_router(requirements_router)  # Keep during migration
        # ... other legacy routers
```

### 4.2 Update `odras.sh` Worker Management

Modify worker startup to use plugin registry:

```bash
start_plugin_workers() {
    print_status "Starting plugin-based workers..."
    python3 scripts/start_plugin_workers.py
}
```

Create `scripts/start_plugin_workers.py`:

```python
# Discovers and starts all registered WorkerPlugin instances
registry = load_plugin_registry()
workers = registry.get_plugins_by_type(PluginType.WORKER)
for worker in workers:
    await worker.start()
```

## Phase 5: Database Schema Updates

### 5.1 Plugin Metadata Table

Add migration `backend/migrations/add_plugin_system.sql`:

```sql
CREATE TABLE plugins (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    type VARCHAR(50) NOT NULL,
    enabled BOOLEAN DEFAULT true,
    config JSONB,
    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE plugin_dependencies (
    plugin_id VARCHAR(255) REFERENCES plugins(id),
    dependency_id VARCHAR(255) REFERENCES plugins(id),
    PRIMARY KEY (plugin_id, dependency_id)
);
```

Add to `odras.sh init-db` function after existing migrations.

## Phase 6: Frontend Plugin Discovery

### 6.1 Plugin Metadata Endpoint

Add to plugin system `backend/api/plugins.py`:

```python
@router.get("/plugins/active")
async def get_active_plugins():
    """Returns all active plugins with frontend configuration"""
    plugins = plugin_registry.get_all()
    return [
        {
            "id": p.manifest.id,
            "name": p.manifest.name,
            "type": p.manifest.type,
            "frontend_config": p.get_frontend_config() if hasattr(p, 'get_frontend_config') else None
        }
        for p in plugins if p.manifest.enabled
    ]
```

### 6.2 Dynamic UI Panel Registration

Update `frontend/app.html` to dynamically load workbench panels:

```javascript
async function loadPluginWorkbenches() {
    const response = await fetch('/api/plugins/active?type=workbench');
    const plugins = await response.json();
    
    plugins.forEach(plugin => {
        registerWorkbenchPanel(plugin.id, plugin.frontend_config);
    });
}
```

## Phase 7: Testing & Validation

### 7.1 Plugin Testing Framework

Create `tests/plugins/test_plugin_system.py`:

```python
def test_plugin_discovery()
def test_plugin_loading()
def test_plugin_dependency_resolution()
def test_workbench_plugin_initialization()
def test_das_plugin_initialization()
def test_worker_plugin_lifecycle()
```

### 7.2 Integration Tests

Update existing tests to work with both compatibility mode and pure plugin mode:

```python
@pytest.mark.parametrize("plugin_mode", [True, False])
async def test_requirements_api(plugin_mode):
    # Test requirements workbench via plugin or legacy route
    pass
```

## Phase 8: Documentation & Migration Guide

### 8.1 Plugin Development Guide

Create `docs/development/PLUGIN_DEVELOPMENT_GUIDE.md`:

- How to create a new workbench plugin
- How to create a DAS engine plugin
- Plugin manifest specification
- Testing plugins
- Debugging plugins

### 8.2 Migration Checklist

Create `docs/architecture/PLUGIN_MIGRATION_CHECKLIST.md`:

- Component-by-component migration status
- Compatibility mode vs pure plugin mode
- Breaking changes and deprecation timeline

## Implementation Priority

1. **Phase 1-2** (Week 1-2): Core infrastructure, interfaces, configuration
2. **Phase 3** (Week 3-4): Migrate 2-3 workbenches as proof of concept
3. **Phase 4** (Week 5): Update bootstrap, compatibility mode
4. **Phase 5** (Week 6): Database schema, remaining workbenches
5. **Phase 6** (Week 7): DAS and worker migration
6. **Phase 7-8** (Week 8): Frontend integration, testing, documentation

## Key Files to Modify

- `backend/main.py` (lines 82-122) - Replace hard-coded includes with plugin loader
- `backend/services/config.py` - Add plugin configuration settings
- `odras.sh` (lines 687-732) - Replace worker startup with plugin system
- `frontend/app.html` - Add dynamic plugin discovery
- Add new `backend/plugins/` directory structure
- Add new `config/plugins.yaml` configuration file

## Backward Compatibility Strategy

- **Compatibility mode flag**: `plugin_compatibility_mode=true` keeps old routes active
- **Dual registration**: Both plugin and legacy routes work during transition
- **Gradual migration**: Migrate one workbench at a time, test thoroughly
- **Deprecation timeline**: 2-3 releases with compatibility mode before removal
- **Migration scripts**: Automated tools to help convert old code to plugins

### To-dos

- [ ] Implement core plugin infrastructure (manifest system, registry, loader, configuration)
- [ ] Create base classes and interfaces for WorkbenchPlugin, DASEnginePlugin, WorkerPlugin
- [ ] Migrate existing workbenches (Requirements, Ontology, Knowledge) to plugin architecture
- [ ] Migrate DAS2 engine to plugin architecture
- [ ] Migrate workers (external task, ingestion, eventcapture2) to plugin architecture
- [ ] Update main.py and odras.sh to use plugin system with compatibility mode
- [ ] Add plugin metadata tables and update migration system
- [ ] Implement dynamic plugin discovery and UI panel registration in frontend
- [ ] Create plugin testing framework and update integration tests
- [ ] Write plugin development guide and migration checklist documentation