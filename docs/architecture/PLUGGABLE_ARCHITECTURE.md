# ODRAS Pluggable Architecture

## Overview

This document outlines the transformation of ODRAS from a monolithic application into a plugin-based architecture where workbenches, DAS systems, and workers are independently managed, registered, and loaded. This enables hot-swappable components and dramatically simplifies adding new workbenches or upgrading DAS without core system changes.

## Current State

### Monolithic Architecture Issues
- **Hard-coded components**: All workbenches and services hard-coded in main.py
- **Difficult to extend**: Adding new workbenches requires core system changes
- **No hot-swapping**: Cannot add/remove components without restart
- **Tight coupling**: Components tightly coupled to core system
- **Difficult testing**: Hard to test components in isolation

### Target Architecture
- **Plugin-based**: All components as independent plugins
- **Hot-swappable**: Add/remove components without restart
- **Loose coupling**: Components communicate via well-defined interfaces
- **Easy testing**: Components can be tested in isolation
- **Extensible**: Easy to add new workbenches and services

## Plugin Architecture Design

### Plugin Types

#### 1. Workbench Plugins
- **Purpose**: UI workbenches for user interaction
- **Examples**: Requirements, Ontology, Knowledge, Conceptualizer
- **Interface**: WorkbenchPlugin
- **Location**: `backend/plugins/workbenches/`

#### 2. DAS Engine Plugins
- **Purpose**: AI reasoning and conversation engines
- **Examples**: DAS2, DAS3, Custom AI engines
- **Interface**: DASEnginePlugin
- **Location**: `backend/plugins/das_engines/`

#### 3. Worker Plugins
- **Purpose**: Background processing and task execution
- **Examples**: External Task Worker, Ingestion Worker, Event Capture
- **Interface**: WorkerPlugin
- **Location**: `backend/plugins/workers/`

#### 4. Middleware Plugins
- **Purpose**: Request/response processing and cross-cutting concerns
- **Examples**: Authentication, Logging, Rate Limiting
- **Interface**: MiddlewarePlugin
- **Location**: `backend/plugins/middleware/`

### Plugin Structure

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

## Core Infrastructure

### 1. Plugin Manifest System

```yaml
# manifest.yaml
id: requirements_workbench
name: Requirements Workbench
version: 1.2.3
type: workbench
description: Requirements extraction, management, and analysis
author: ODRAS Team
license: MIT
homepage: https://odras.org

# Dependencies and compatibility
dependencies:
  - ontology_workbench
  - knowledge_workbench
python_requires: ">=3.10"
odras_api_version: "1.0"

# API and routing
api_prefix: /api/requirements
enabled: true

# Configuration and validation
config_schema:
  type: object
  properties:
    enable_auto_extraction:
      type: boolean
      default: true
    max_requirements:
      type: integer
      default: 1000

# Security and isolation
trusted: false
sandbox_enabled: true
max_memory_mb: 512
max_execution_time_sec: 300

# Health and monitoring
health_check_endpoint: /health
metrics_enabled: true
```

### 2. Plugin Registry

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

### 3. Plugin Loader

```python
class PluginLoader:
    def discover_plugins(self, plugin_dirs: List[Path]) -> List[PluginManifest]
    def load_plugin(self, manifest: PluginManifest) -> Plugin
    def validate_plugin(self, plugin: Plugin) -> bool
```

### 4. API Gateway

```python
class APIGateway:
    def __init__(self, app: FastAPI):
        self.app = app
        self.plugin_routes: Dict[str, APIRouter] = {}
        self.route_metadata: Dict[str, RouteMetadata] = {}
    
    async def register_plugin_api(self, plugin: Plugin):
        """Dynamically register plugin's API routes"""
        if hasattr(plugin, 'get_api_router'):
            router = plugin.get_api_router()
            prefix = f"/api/{plugin.manifest.id}"
            self.app.include_router(router, prefix=prefix, tags=[plugin.manifest.name])
            self.plugin_routes[plugin.manifest.id] = router
```

## Plugin Interfaces

### Workbench Plugin Interface

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

### DAS Engine Plugin Interface

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

### Worker Plugin Interface

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

## Process Engine Integration

### Native ODRAS Process Engine

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
```

### DAS Process Creation

```python
class DASProcessCreator:
    """Service for DAS to create, test, and deploy processes"""
    
    async def create_process_from_description(self, description: str) -> ProcessDefinition:
        """DAS uses LLM to convert natural language description into process definition"""
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
```

## Data Manager Workbench

### Central Data Orchestration

```python
class DataManagerPlugin(WorkbenchPlugin):
    """Central data orchestration and transformation layer"""
    
    def __init__(self):
        self.connectors: Dict[str, DataConnector] = {}
        self.pipelines: Dict[str, DataPipeline] = {}
        self.subscriptions: Dict[str, DataSubscription] = {}
```

### Data Connectors

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
```

## Event System

### Event Bus

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

## Migration Strategy

### Phase 1: Core Infrastructure (Week 1-2)
1. Implement plugin manifest system
2. Create plugin registry and loader
3. Implement API gateway
4. Create base plugin interfaces
5. Add configuration system

### Phase 2: Process Engine (Week 3-4)
1. Implement native process engine
2. Add DAS process creation
3. Create process workbench plugin
4. Implement event system
5. Add schema registry

### Phase 3: Data Manager (Week 5-6)
1. Create Data Manager workbench
2. Implement data connectors
3. Add data pipelines
4. Create data subscriptions
5. Implement data contracts

### Phase 4: Plugin Migration (Week 7-8)
1. Migrate Requirements workbench
2. Migrate Ontology workbench
3. Migrate Knowledge workbench
4. Migrate DAS2 engine
5. Migrate workers

### Phase 5: Frontend Integration (Week 9-10)
1. Implement dynamic plugin discovery
2. Add plugin UI registration
3. Create plugin management interface
4. Implement hot-swapping
5. Add plugin monitoring

### Phase 6: Testing & Documentation (Week 11)
1. Create comprehensive test suite
2. Add plugin testing framework
3. Create migration documentation
4. Add developer guides
5. Create troubleshooting guides

## Configuration

### Plugin Configuration

```yaml
# config/plugins.yaml
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
    performance:
      max_concurrent_extractions: 5
  das2_engine:
    model_settings:
      temperature: 0.7
      max_tokens: 2000
    performance:
      max_concurrent_requests: 10
```

## Benefits

### For Development
- **Modular development**: Work on individual plugins independently
- **Easy testing**: Test plugins in isolation
- **Faster iteration**: Hot-swap plugins without restart
- **Better debugging**: Isolated plugin errors
- **Cleaner code**: Clear separation of concerns

### For Users
- **Customizable**: Enable/disable plugins as needed
- **Extensible**: Add new workbenches easily
- **Reliable**: Plugin failures don't crash entire system
- **Performance**: Load only needed plugins
- **Updates**: Update individual plugins independently

### For Maintenance
- **Easier debugging**: Isolated plugin issues
- **Better monitoring**: Plugin-specific metrics
- **Simplified deployment**: Deploy plugins independently
- **Reduced risk**: Changes isolated to specific plugins
- **Better documentation**: Plugin-specific docs

## Security Considerations

### Plugin Isolation
- **Sandboxing**: Run plugins in isolated contexts
- **Resource limits**: Memory and CPU limits per plugin
- **Permission system**: Granular permissions per plugin
- **Audit logging**: Track plugin activities
- **Validation**: Validate plugin code before loading

### Security Features
- **Code signing**: Verify plugin authenticity
- **Dependency scanning**: Check for vulnerabilities
- **Access control**: Restrict plugin access to resources
- **Encryption**: Encrypt plugin communications
- **Monitoring**: Monitor plugin security events

## Performance Considerations

### Optimization Strategies
- **Lazy loading**: Load plugins on demand
- **Caching**: Cache plugin metadata and configurations
- **Resource pooling**: Share resources between plugins
- **Performance monitoring**: Track plugin performance
- **Load balancing**: Distribute plugin load

### Scalability
- **Horizontal scaling**: Scale plugins independently
- **Resource management**: Manage plugin resources efficiently
- **Load distribution**: Distribute load across plugin instances
- **Auto-scaling**: Scale plugins based on demand
- **Performance tuning**: Optimize plugin performance

## Testing Strategy

### Plugin Testing
- **Unit tests**: Test individual plugin functionality
- **Integration tests**: Test plugin interactions
- **Performance tests**: Test plugin performance
- **Security tests**: Test plugin security
- **End-to-end tests**: Test complete workflows

### Testing Framework
- **Plugin test harness**: Test plugins in isolation
- **Mock services**: Mock external dependencies
- **Test data**: Provide test data for plugins
- **Automated testing**: Automate plugin testing
- **Continuous integration**: Test plugins in CI/CD

## Monitoring & Observability

### Plugin Monitoring
- **Health checks**: Monitor plugin health
- **Performance metrics**: Track plugin performance
- **Error tracking**: Monitor plugin errors
- **Usage analytics**: Track plugin usage
- **Resource monitoring**: Monitor plugin resources

### Observability Features
- **Logging**: Comprehensive plugin logging
- **Tracing**: Track plugin execution
- **Metrics**: Plugin-specific metrics
- **Alerting**: Alert on plugin issues
- **Dashboards**: Plugin monitoring dashboards

## Future Enhancements

### Advanced Features
- **Plugin marketplace**: Share and distribute plugins
- **Plugin versioning**: Manage plugin versions
- **Plugin dependencies**: Handle complex dependencies
- **Plugin configuration**: Advanced configuration management
- **Plugin lifecycle**: Full plugin lifecycle management

### Integration Features
- **External plugins**: Load plugins from external sources
- **Plugin APIs**: Expose plugin APIs externally
- **Plugin communication**: Inter-plugin communication
- **Plugin events**: Plugin event system
- **Plugin workflows**: Plugin-based workflows

## Conclusion

The pluggable architecture will transform ODRAS into a highly modular, extensible, and maintainable system. It provides the foundation for rapid development, easy testing, and seamless integration of new features.

The benefits far outweigh the implementation complexity, and the modular approach ensures ODRAS can evolve and grow without architectural constraints.

## Last Updated
$(date)