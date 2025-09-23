# Ontology Workbench Post-MVP Development Plan<br>
<br>
**Version**: 1.0<br>
**Date**: 2025-09-10<br>
**Status**: Planning Phase<br>
<br>
## Executive Summary<br>
<br>
With the Ontology Workbench MVP successfully completed, this document outlines the next phase of development focusing on advanced ontology management, SHACL validation, individual/instance management, and Digital Assistant System (DAS) integration.<br>
<br>
## MVP Achievements Summary<br>
<br>
### ✅ Completed Core Features<br>
- **Visual Ontology Editor**: Cytoscape-based canvas with direct manipulation<br>
- **Import Management**: External ontology imports with read-only protection<br>
- **Rich Metadata**: Comprehensive tracking with Dublin Core annotations<br>
- **Named Views**: Save/restore complete canvas configurations with toggle functionality<br>
- **Advanced UI**: Professional interface with visibility controls and tree-canvas synchronization<br>
<br>
### ✅ Technical Implementation<br>
- **Full CRUD Operations**: Create, read, update, delete ontologies<br>
- **Layout Persistence**: Server-synchronized positioning and zoom states<br>
- **Properties Management**: Template-based attribute editing with validation<br>
- **Note System**: 7 note types with visual indicators and automatic metadata<br>
- **Professional UX**: SVG icons, accessibility support, keyboard navigation<br>
<br>
## Ontology Architecture for LLM Integration<br>
<br>
### Project Ontology Hierarchy<br>
**Understanding**: Projects use hierarchical ontology structure for requirement-driven individual generation<br>
<br>
```<br>
Project Ontologies:<br>
├── Main Ontology (primary for LLM interaction) ⭐<br>
├── Additional Project Ontologies (secondary)<br>
└── Imports:<br>
    ├── Core Imports (above) - BFO, foundational ontologies<br>
    │   └── Purpose: Structure, validation, location - NOT for individuals<br>
    └── Working Imports (below) - Reliability, Safety, Domain-specific<br>
        └── Purpose: Templates for individual/instance creation<br>
```<br>
<br>
### LLM Integration Context<br>
**Requirement Node Processing**:<br>
- **Input**: Requirement text + Main Ontology + Working Imports<br>
- **Output**: Component/Process/Interface/Function individuals<br>
- **Validation**: Against Core Import constraints (BFO, etc.)<br>
- **Attribution**: Link individuals back to source requirements<br>
<br>
### Main Ontology Selection<br>
**Need**: Projects with multiple ontologies require main ontology designation<br>
- **Purpose**: Main ontology + working imports provide LLM context<br>
- **Implementation**: Add main ontology selector in project settings<br>
- **Impact**: Ensures consistent LLM analysis across requirements<br>
<br>
## Post-MVP Development Phases<br>
<br>
### Phase 0: Server-Side State Management (High Priority)<br>
<br>
#### 0.1 Named Views Server Storage<br>
**Current Issue**: Named views stored in localStorage cause synchronization and duplication issues<br>
**Solution**: Move named views to PostgreSQL for proper persistence and sharing<br>
<br>
**Database Schema**:<br>
```sql<br>
-- Named views table<br>
CREATE TABLE IF NOT EXISTS ontology_named_views (<br>
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),<br>
    project_id UUID NOT NULL REFERENCES projects(project_id),<br>
    ontology_iri VARCHAR(500) NOT NULL,<br>
    name VARCHAR(255) NOT NULL,<br>
    creator VARCHAR(255) NOT NULL,<br>
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,<br>
<br>
    -- View configuration<br>
    zoom DECIMAL(10,6) NOT NULL,<br>
    pan_x DECIMAL(10,6) NOT NULL,<br>
    pan_y DECIMAL(10,6) NOT NULL,<br>
<br>
    -- Visibility states (JSON)<br>
    visibility_state JSONB NOT NULL,<br>
    element_visibility JSONB NOT NULL,<br>
    collapsed_imports JSONB NOT NULL,<br>
    visible_imports JSONB NOT NULL,<br>
<br>
    UNIQUE(project_id, ontology_iri, name)<br>
);<br>
<br>
-- Index for performance<br>
CREATE INDEX idx_named_views_project_ontology<br>
ON ontology_named_views(project_id, ontology_iri);<br>
```<br>
<br>
**API Endpoints**:<br>
```python<br>
# New endpoints for named views<br>
@app.get("/api/ontology/named-views")<br>
async def get_named_views(project_id: str, ontology_iri: str):<br>
    """Get all named views for an ontology"""<br>
<br>
@app.post("/api/ontology/named-views")<br>
async def create_named_view(body: NamedViewRequest):<br>
    """Create new named view"""<br>
<br>
@app.put("/api/ontology/named-views/{view_id}")<br>
async def update_named_view(view_id: str, body: NamedViewRequest):<br>
    """Update named view (rename)"""<br>
<br>
@app.delete("/api/ontology/named-views/{view_id}")<br>
async def delete_named_view(view_id: str):<br>
    """Delete named view"""<br>
```<br>
<br>
#### 0.2 Import Configuration Server Storage<br>
**Current Issue**: Import settings stored in localStorage cause duplication and sync issues<br>
**Solution**: Move import configurations to PostgreSQL<br>
<br>
**Database Schema**:<br>
```sql<br>
-- Ontology imports configuration table<br>
CREATE TABLE IF NOT EXISTS ontology_import_configs (<br>
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),<br>
    project_id UUID NOT NULL REFERENCES projects(project_id),<br>
    base_ontology_iri VARCHAR(500) NOT NULL,<br>
    import_ontology_iri VARCHAR(500) NOT NULL,<br>
<br>
    -- Import classification<br>
    import_type VARCHAR(50) NOT NULL CHECK (import_type IN ('core', 'working')),<br>
    -- core: BFO, foundational (for validation only)<br>
    -- working: Domain ontologies (for individual creation)<br>
<br>
    -- Import state<br>
    is_visible BOOLEAN DEFAULT true,<br>
    is_collapsed BOOLEAN DEFAULT false,<br>
<br>
    -- Layout positions for imported elements (JSON)<br>
    element_positions JSONB,<br>
<br>
    -- Metadata<br>
    creator VARCHAR(255) NOT NULL,<br>
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,<br>
<br>
    UNIQUE(project_id, base_ontology_iri, import_ontology_iri)<br>
);<br>
<br>
-- Index for performance<br>
CREATE INDEX idx_import_configs_base_ontology<br>
ON ontology_import_configs(project_id, base_ontology_iri);<br>
```<br>
<br>
**Benefits**:<br>
- **No Duplication**: Single source of truth for import configurations<br>
- **Cross-Device Sync**: Import settings sync across different browsers/devices<br>
- **Team Collaboration**: Shared import configurations for project teams<br>
- **Audit Trail**: Track who added/removed imports and when<br>
- **Performance**: Faster loading without localStorage parsing<br>
<br>
#### 0.3 Server-Side API Migration<br>
**Implementation Strategy**:<br>
```javascript<br>
// Migrate from localStorage to server API<br>
async function migrateNamedViewsToServer() {<br>
  const projects = await getProjects();<br>
<br>
  for (const project of projects) {<br>
    const ontologies = await getProjectOntologies(project.id);<br>
<br>
    for (const ontology of ontologies) {<br>
      // Get localStorage named views<br>
      const localViews = loadNamedViews(ontology.iri);<br>
<br>
      // Upload to server<br>
      for (const view of localViews) {<br>
        await createNamedViewOnServer(project.id, ontology.iri, view);<br>
      }<br>
<br>
      // Clear localStorage after successful migration<br>
      localStorage.removeItem(namedViewsKey(ontology.iri));<br>
    }<br>
  }<br>
}<br>
```<br>
<br>
### Phase 1: Ontology Architecture Enhancement (Immediate Priority)<br>
<br>
#### 0.1 Import Classification System<br>
**Action**: Classify imports as Core (above) vs Working (below)<br>
- **Core Imports (above)**: BFO, foundational ontologies for structure/validation<br>
- **Working Imports (below)**: Domain ontologies for individual creation templates<br>
- **Implementation**: Add import type classification to import management<br>
- **UI Enhancement**: Visual distinction in tree (above/below main ontology)<br>
<br>
#### 0.2 Main Ontology Selection<br>
**Action**: Add main ontology designation for projects with multiple ontologies<br>
```javascript<br>
// Project settings for main ontology<br>
const projectOntologyConfig = {<br>
  mainOntologyIri: "http://org/project/ontologies/systems", // Primary for LLM<br>
  additionalOntologies: [], // Secondary ontologies<br>
  coreImports: [], // Above - for validation (BFO, etc.)<br>
  workingImports: [] // Below - for individual creation<br>
};<br>
```<br>
<br>
**Features**:<br>
- **Main Ontology Selector**: UI to designate primary ontology per project<br>
- **Import Classification**: Mark imports as core vs working<br>
- **LLM Context Builder**: Combine main ontology + working imports for LLM analysis<br>
- **Visual Hierarchy**: Tree shows above/below relationship to main ontology<br>
<br>
#### 0.3 Requirement-Ontology Integration<br>
**Purpose**: Connect requirement nodes to ontology-driven individual generation<br>
```javascript<br>
// Requirement processing context<br>
const requirementContext = {<br>
  requirementId: "req_001",<br>
  requirementText: "The system shall have a navigation component...",<br>
  ontologyContext: {<br>
    mainOntology: "systems_ontology",<br>
    workingImports: ["reliability_ontology", "safety_ontology"],<br>
    availableClasses: ["Component", "Process", "Interface", "Function"]<br>
  }<br>
};<br>
```<br>
<br>
### Phase 1: OWL Code Editor Integration (High Priority)<br>
<br>
#### 1.1 Dual-Mode Editing System<br>
**Goal**: Enable users to switch between visual diagram and OWL text editing<br>
<br>
**Implementation**:<br>
```javascript<br>
// Add OWL editor tab to ontology workbench<br>
const owlEditor = {<br>
  mode: 'diagram', // 'diagram' | 'owl'<br>
  editor: null, // CodeMirror or Monaco editor instance<br>
  syncInProgress: false<br>
};<br>
<br>
// Bidirectional synchronization<br>
function syncDiagramToOWL() {<br>
  const owlCode = serializeCanvasToTurtle();<br>
  owlEditor.editor.setValue(owlCode);<br>
}<br>
<br>
function syncOWLToDiagram() {<br>
  const owlCode = owlEditor.editor.getValue();<br>
  const parsedData = parseOWLToCanvasData(owlCode);<br>
  updateCanvasFromOWL(parsedData);<br>
}<br>
```<br>
<br>
**Features**:<br>
- **Toggle View**: Switch between diagram and OWL code editor<br>
- **Real-time Sync**: Changes in diagram update OWL code and vice versa<br>
- **Syntax Highlighting**: OWL/Turtle syntax highlighting with error detection<br>
- **Validation**: OWL syntax validation with error reporting<br>
- **Split View**: Optional side-by-side diagram and code view<br>
<br>
**Technical Requirements**:<br>
- **OWL Parser**: JavaScript OWL/Turtle parser (use existing or implement)<br>
- **Code Editor**: Monaco Editor or CodeMirror for syntax highlighting<br>
- **Synchronization**: Conflict resolution when both sides are edited<br>
- **Validation**: Real-time OWL syntax checking<br>
<br>
#### 1.2 OWL Export/Import<br>
**Features**:<br>
- **Export**: Download OWL files in multiple formats (Turtle, RDF/XML, JSON-LD)<br>
- **Import**: Upload OWL files to create new ontologies<br>
- **Format Conversion**: Support multiple OWL serialization formats<br>
- **Validation**: Pre-import OWL validation and conflict checking<br>
<br>
### Phase 2: SHACL Constraints and Validation (High Priority)<br>
<br>
#### 2.1 SHACL Shape Editor<br>
**Goal**: Visual editor for creating SHACL constraints<br>
<br>
**Implementation**:<br>
```javascript<br>
// Add SHACL shapes to ontology model<br>
const shaclShapes = {<br>
  nodeShapes: [], // sh:NodeShape definitions<br>
  propertyShapes: [], // sh:PropertyShape definitions<br>
  validationReports: [] // Validation results<br>
};<br>
<br>
// SHACL shape templates<br>
const shaclTemplates = {<br>
  classShape: {<br>
    type: 'NodeShape',<br>
    targetClass: null,<br>
    properties: []<br>
  },<br>
  propertyConstraints: {<br>
    datatype: ['xsd:string', 'xsd:integer', 'xsd:decimal', 'xsd:boolean'],<br>
    cardinality: ['minCount', 'maxCount', 'exactCount'],<br>
    valueConstraints: ['minValue', 'maxValue', 'pattern', 'in']<br>
  }<br>
};<br>
```<br>
<br>
**Features**:<br>
- **Shape Templates**: Pre-built SHACL shape patterns for common constraints<br>
- **Visual Constraint Editor**: GUI for defining constraints on classes and properties<br>
- **Unit Validation**: Integration with QUDT for unit checking<br>
- **Multiplicity Constraints**: Min/max cardinality validation<br>
- **Value Bounding**: Numeric range and pattern validation<br>
- **Custom Constraints**: SPARQL-based custom validation rules<br>
<br>
#### 2.2 SHACL Validation Engine<br>
**Backend Integration**:<br>
```python<br>
# New file: backend/services/shacl_validator.py<br>
from pyshacl import validate<br>
from rdflib import Graph<br>
<br>
class SHACLValidator:<br>
    def validate_ontology(self, ontology_graph: str, shapes_graph: str):<br>
        """Validate ontology instances against SHACL shapes"""<br>
<br>
    def validate_individuals(self, individuals_graph: str, shapes_graph: str):<br>
        """Validate specific individuals against constraints"""<br>
<br>
    def generate_validation_report(self, results):<br>
        """Generate human-readable validation report"""<br>
```<br>
<br>
**Features**:<br>
- **Real-time Validation**: Validate as users create/edit ontology elements<br>
- **Batch Validation**: Validate all individuals against current shapes<br>
- **Validation Reports**: Detailed reports with error locations and suggestions<br>
- **Constraint Checking**: Unit checks, multiplicity, value bounds, custom rules<br>
<br>
#### 2.3 Python OWL Integration<br>
**Libraries to Consider**:<br>
- **owlready2**: Python OWL ontology manipulation<br>
- **rdflib**: RDF graph operations and SPARQL<br>
- **pyshacl**: SHACL validation engine<br>
- **pint**: Unit conversion and validation<br>
<br>
### Phase 3: Individual/Instance Management (High Priority)<br>
<br>
#### 3.1 Individual Management Architecture<br>
**Challenge**: Managing hundreds of extracted requirement individuals<br>
<br>
**Option A: Integrated Tree View**<br>
```javascript<br>
// Extend ontology tree with individuals section<br>
const individualsTree = {<br>
  groupBy: 'class', // Group individuals by their class<br>
  filters: {<br>
    class: null,<br>
    creator: null,<br>
    dateRange: null,<br>
    searchText: null<br>
  },<br>
  pagination: {<br>
    pageSize: 50,<br>
    currentPage: 1<br>
  }<br>
};<br>
```<br>
<br>
**Option B: Separate Individuals Tab**<br>
```javascript<br>
// New workbench tab for individual management<br>
const individualsWorkbench = {<br>
  view: 'table', // 'table' | 'cards' | 'graph'<br>
  filters: {<br>
    class: [],<br>
    requirements: [],<br>
    confidence: [0.0, 1.0],<br>
    creator: null<br>
  },<br>
  search: {<br>
    text: '',<br>
    fields: ['label', 'description', 'requirement_id']<br>
  }<br>
};<br>
```<br>
<br>
**Recommended Approach**: **Option B - Separate Individuals Tab**<br>
- **Rationale**: Hundreds of individuals would overwhelm the tree view<br>
- **Benefits**: Dedicated space for filtering, searching, and bulk operations<br>
- **Features**: Table view with sorting, filtering, search, and bulk actions<br>
<br>
#### 3.2 Individual Management Features<br>
**Core Functionality**:<br>
- **Table View**: Sortable, filterable table with individual details<br>
- **Search**: Full-text search across individual properties<br>
- **Filtering**: Filter by class, creator, confidence, requirement source<br>
- **Bulk Operations**: Select multiple individuals for bulk actions<br>
- **Graph View**: Optional graph visualization of individual relationships<br>
<br>
**Individual Lifecycle**:<br>
```javascript<br>
// Individual data structure<br>
const individual = {<br>
  id: "req_001_component_001",<br>
  iri: "http://org/project/ontologies/name#Component_001",<br>
  type: "Component",<br>
  label: "Primary Navigation System",<br>
  description: "Main navigation system for vessel guidance",<br>
  confidence: 0.85,<br>
  source_requirement: "req_001",<br>
  creator: "admin",<br>
  created_date: "2025-09-10",<br>
  properties: {<br>
    hasName: "Primary Navigation System",<br>
    hasSerialNumber: "NAV-001-PRI",<br>
    hasMass: {<br>
      numericValue: 45.5,<br>
      unit: "kg"<br>
    }<br>
  }<br>
};<br>
```<br>
<br>
#### 3.3 LLM Integration for Individual Creation<br>
**Workflow**:<br>
1. **Requirement Analysis**: Extract entities from requirement text<br>
2. **Ontology Mapping**: Map extracted entities to ontology classes<br>
3. **Individual Creation**: Create individuals with confidence scores<br>
4. **Validation**: Validate against SHACL constraints<br>
5. **Review**: Present for SME review and approval<br>
<br>
### Phase 4: Digital Assistant System (DAS) Integration (Medium Priority)<br>
<br>
#### 4.1 DAS-Ontology API Integration<br>
**Goal**: Enable DAS to create and manage ontology objects through API<br>
<br>
**API Design**:<br>
```python<br>
# New file: backend/api/das_ontology.py<br>
@router.post("/api/das/ontology/create-class")<br>
async def das_create_class(body: DASClassRequest):<br>
    """DAS endpoint for creating ontology classes"""<br>
<br>
@router.post("/api/das/ontology/create-individual")<br>
async def das_create_individual(body: DASIndividualRequest):<br>
    """DAS endpoint for creating individuals"""<br>
<br>
@router.post("/api/das/ontology/validate")<br>
async def das_validate_ontology(body: DASValidationRequest):<br>
    """DAS endpoint for SHACL validation"""<br>
```<br>
<br>
**DAS Request Models**:<br>
```python<br>
class DASClassRequest(BaseModel):<br>
    ontology_iri: str<br>
    class_name: str<br>
    label: str<br>
    description: Optional[str]<br>
    parent_class: Optional[str]<br>
    properties: Optional[Dict[str, Any]]<br>
<br>
class DASIndividualRequest(BaseModel):<br>
    ontology_iri: str<br>
    class_iri: str<br>
    individual_name: str<br>
    properties: Dict[str, Any]<br>
    confidence: Optional[float]<br>
    source_requirement: Optional[str]<br>
```<br>
<br>
#### 4.2 DAS Knowledge Base for API Instructions<br>
**Implementation Strategy**:<br>
```python<br>
# DAS API knowledge base in Qdrant<br>
das_api_knowledge = {<br>
    "ontology_operations": {<br>
        "create_class": {<br>
            "description": "Create new ontology class",<br>
            "endpoint": "POST /api/das/ontology/create-class",<br>
            "parameters": {...},<br>
            "examples": [...]<br>
        },<br>
        "create_individual": {<br>
            "description": "Create ontology individual/instance",<br>
            "endpoint": "POST /api/das/ontology/create-individual",<br>
            "parameters": {...},<br>
            "examples": [...]<br>
        }<br>
    }<br>
};<br>
```<br>
<br>
**Knowledge Base Structure**:<br>
- **API Documentation**: Complete API reference with examples<br>
- **Ontology Patterns**: Common ontology modeling patterns<br>
- **SHACL Examples**: Constraint definition examples<br>
- **Validation Guides**: How to validate individuals and handle errors<br>
- **Best Practices**: Ontology development guidelines<br>
<br>
#### 4.3 DAS-RAG Integration Check<br>
**Implementation**:<br>
```python<br>
# Add ontology API check to RAG system<br>
def check_for_ontology_requests(user_query: str) -> bool:<br>
    """Check if user query involves ontology operations"""<br>
    ontology_keywords = [<br>
        "create class", "add individual", "ontology",<br>
        "validate constraints", "SHACL", "create component"<br>
    ]<br>
    return any(keyword in user_query.lower() for keyword in ontology_keywords)<br>
<br>
def get_ontology_api_context(query: str) -> List[str]:<br>
    """Retrieve relevant API documentation from knowledge base"""<br>
    # Query Qdrant for relevant ontology API instructions<br>
    # Return as context for DAS response<br>
```<br>
<br>
**Features**:<br>
- **Query Classification**: Detect when user wants ontology operations<br>
- **Context Retrieval**: Get relevant API documentation from knowledge base<br>
- **Action Guidance**: Provide step-by-step API usage instructions<br>
- **Error Handling**: Guide users through common API errors and solutions<br>
<br>
## Requirement-Driven Individual Generation<br>
<br>
### LLM-Ontology Integration Architecture<br>
**Core Concept**: Requirements drive individual generation using structured ontology hierarchy<br>
<br>
**Processing Pipeline**:<br>
```mermaid<br>
graph TD<br>
    A[Requirement Node] --> B[Main Ontology Context]<br>
    B --> C[Working Imports Classes]<br>
    C --> D[LLM Analysis]<br>
    D --> E[Individual Generation]<br>
    E --> F[Core Import Validation]<br>
    F --> G[Individual Review]<br>
<br>
    H[Core Imports - BFO] --> F<br>
    I[Working Imports - Reliability] --> C<br>
    J[Working Imports - Safety] --> C<br>
```<br>
<br>
### Individual Generation Strategy<br>
**Key Principles**:<br>
1. **Main Ontology**: Provides primary context for LLM analysis<br>
2. **Working Imports**: Provide class templates for individual creation<br>
3. **Core Imports**: Provide validation constraints (not individual templates)<br>
4. **Requirement Attribution**: All individuals link back to source requirements<br>
<br>
**Individual Data Structure**:<br>
```javascript<br>
const generatedIndividual = {<br>
  // Core identification<br>
  id: "req_001_component_nav_001",<br>
  iri: "http://org/project/ontologies/systems#NavigationComponent_001",<br>
<br>
  // Classification<br>
  type: "Component", // From working import<br>
  classSource: "reliability_ontology", // Which working import provided the class<br>
<br>
  // Content<br>
  label: "Primary Navigation System",<br>
  description: "Main navigation system for vessel guidance",<br>
<br>
  // Requirement linkage<br>
  sourceRequirement: "req_001",<br>
  requirementText: "The system shall provide navigation...",<br>
  confidence: 0.85, // LLM confidence in this individual<br>
<br>
  // Validation<br>
  validationStatus: "passed", // Against core import constraints<br>
  validationDetails: { /* SHACL results */ },<br>
<br>
  // Relationships (inferred from requirement)<br>
  relationships: [<br>
    {<br>
      predicate: "realizes",<br>
      target: "navigation_function_001",<br>
      confidence: 0.9,<br>
      source: "llm_inference"<br>
    }<br>
  ]<br>
};<br>
```<br>
<br>
## Implementation Roadmap<br>
<br>
### Sprint 1: OWL Code Editor (2 weeks)<br>
- [ ] Add OWL text editor tab to workbench<br>
- [ ] Implement diagram-to-OWL serialization<br>
- [ ] Implement OWL-to-diagram parsing<br>
- [ ] Add bidirectional synchronization<br>
- [ ] OWL syntax validation and error reporting<br>
<br>
### Sprint 2: SHACL Foundation (2 weeks)<br>
- [ ] Add SHACL shape data model<br>
- [ ] Implement basic constraint templates<br>
- [ ] Create SHACL shape editor UI<br>
- [ ] Backend SHACL validation service<br>
- [ ] Integration with Python OWL libraries<br>
<br>
### Sprint 3: Individual Management (2 weeks)<br>
- [ ] Design individuals workbench tab<br>
- [ ] Implement individual table view with filtering<br>
- [ ] Add individual creation and editing<br>
- [ ] Bulk operations for individuals<br>
- [ ] Individual-ontology relationship management<br>
<br>
### Sprint 4: DAS Integration (2 weeks)<br>
- [ ] Design DAS-ontology API endpoints<br>
- [ ] Create DAS knowledge base for API instructions<br>
- [ ] Implement RAG integration check<br>
- [ ] Add DAS API documentation to Qdrant<br>
- [ ] Test end-to-end DAS-ontology workflows<br>
<br>
## Technical Architecture<br>
<br>
### OWL Editor Integration<br>
```mermaid<br>
graph TD<br>
    A[Ontology Workbench] --> B[Diagram View]<br>
    A --> C[OWL Editor View]<br>
    B <--> D[Cytoscape Canvas]<br>
    C <--> E[Monaco Editor]<br>
    D <--> F[OWL Serializer]<br>
    E <--> G[OWL Parser]<br>
    F <--> G<br>
    D --> H[Layout Persistence]<br>
    E --> I[OWL Validation]<br>
```<br>
<br>
### SHACL Validation Pipeline<br>
```mermaid<br>
graph TD<br>
    A[Ontology Elements] --> B[SHACL Shape Editor]<br>
    B --> C[Shape Generation]<br>
    C --> D[Python SHACL Validator]<br>
    D --> E[Validation Report]<br>
    E --> F[UI Feedback]<br>
    A --> G[Individual Creation]<br>
    G --> D<br>
    D --> H[Constraint Violations]<br>
    H --> I[Error Highlighting]<br>
```<br>
<br>
### Individual Management System<br>
```mermaid<br>
graph TD<br>
    A[Requirements Extraction] --> B[LLM Analysis]<br>
    B --> C[Individual Generation]<br>
    C --> D[Individuals Workbench]<br>
    D --> E[Table View]<br>
    D --> F[Search & Filter]<br>
    D --> G[Bulk Operations]<br>
    E --> H[Individual Editor]<br>
    F --> I[Filtered Results]<br>
    G --> J[Batch Validation]<br>
```<br>
<br>
### DAS Integration Architecture<br>
```mermaid<br>
graph TD<br>
    A[DAS Query] --> B[Query Classification]<br>
    B --> C{Ontology Operation?}<br>
    C -->|Yes| D[Retrieve API Context]<br>
    C -->|No| E[Standard RAG]<br>
    D --> F[Qdrant API Knowledge]<br>
    F --> G[DAS Response with API Instructions]<br>
    G --> H[User Executes API Calls]<br>
    H --> I[Ontology Workbench Updates]<br>
```<br>
<br>
## Detailed Implementation Plans<br>
<br>
### 1. OWL Code Editor Integration<br>
<br>
#### 1.1 Editor Setup<br>
```html<br>
<!-- Add to ontology workbench --><br>
<div class="owl-editor-container"><br>
  <div class="editor-tabs"><br>
    <button id="diagramTab" class="tab active">Diagram</button><br>
    <button id="owlTab" class="tab">OWL Code</button><br>
  </div><br>
  <div id="diagramView" class="editor-view"><br>
    <!-- Existing Cytoscape canvas --><br>
  </div><br>
  <div id="owlView" class="editor-view hidden"><br>
    <div id="owlCodeEditor"></div><br>
  </div><br>
</div><br>
```<br>
<br>
#### 1.2 Synchronization Strategy<br>
**Diagram → OWL**:<br>
- Trigger on: Element creation, deletion, property changes<br>
- Method: Serialize Cytoscape data to Turtle format<br>
- Validation: Ensure valid OWL syntax before updating editor<br>
<br>
**OWL → Diagram**:<br>
- Trigger on: OWL editor change (debounced)<br>
- Method: Parse OWL/Turtle to extract classes, properties, individuals<br>
- Layout: Preserve existing layout, auto-layout new elements<br>
<br>
#### 1.3 Conflict Resolution<br>
- **Last Edit Wins**: Track which editor was last modified<br>
- **Change Detection**: Compare timestamps and content hashes<br>
- **User Confirmation**: Prompt user when conflicts detected<br>
- **Backup**: Maintain undo history for both modes<br>
<br>
### 2. SHACL Constraints and Validation<br>
<br>
#### 2.1 Constraint Types to Support<br>
**Basic Constraints**:<br>
- **Cardinality**: minCount, maxCount, exactCount<br>
- **Datatype**: xsd:string, xsd:integer, xsd:decimal, xsd:boolean, xsd:dateTime<br>
- **Value Constraints**: minValue, maxValue, minLength, maxLength<br>
- **Pattern Matching**: Regular expressions for string validation<br>
- **Enumeration**: Closed lists of allowed values<br>
<br>
**Advanced Constraints**:<br>
- **Unit Validation**: QUDT-based unit checking<br>
- **Cross-Property**: Constraints involving multiple properties<br>
- **Conditional**: If-then constraint logic<br>
- **Custom SPARQL**: User-defined SPARQL constraint queries<br>
<br>
#### 2.2 Validation Integration<br>
**Real-time Validation**:<br>
```javascript<br>
// Validate as users create individuals<br>
async function validateIndividual(individual) {<br>
  const response = await fetch('/api/shacl/validate', {<br>
    method: 'POST',<br>
    headers: { 'Content-Type': 'application/json' },<br>
    body: JSON.stringify({<br>
      ontology_iri: activeOntologyIri,<br>
      individual_data: individual,<br>
      shapes_iri: `${activeOntologyIri}/shapes`<br>
    })<br>
  });<br>
<br>
  const report = await response.json();<br>
  displayValidationResults(report);<br>
}<br>
```<br>
<br>
**Batch Validation**:<br>
- **Validate All**: Check all individuals against current constraints<br>
- **Validation Reports**: Detailed reports with error locations<br>
- **Fix Suggestions**: Automated suggestions for constraint violations<br>
- **Export Reports**: CSV/JSON export of validation results<br>
<br>
### 3. Individual/Instance Management<br>
<br>
#### 3.1 Individuals Workbench Design<br>
**Tab Structure**:<br>
```html<br>
<section id="wb-individuals" class="workbench"><br>
  <div class="individuals-toolbar"><br>
    <div class="view-controls"><br>
      <button class="btn" data-view="table">Table</button><br>
      <button class="btn" data-view="cards">Cards</button><br>
      <button class="btn" data-view="graph">Graph</button><br>
    </div><br>
    <div class="filter-controls"><br>
      <select id="classFilter">Classes</select><br>
      <input id="searchIndividuals" placeholder="Search..."><br>
      <button class="btn" id="bulkActions">Bulk Actions</button><br>
    </div><br>
  </div><br>
<br>
  <div class="individuals-content"><br>
    <div id="individualsTable" class="view-panel"><br>
      <!-- Sortable table with individual data --><br>
    </div><br>
    <div id="individualsCards" class="view-panel hidden"><br>
      <!-- Card layout for individuals --><br>
    </div><br>
    <div id="individualsGraph" class="view-panel hidden"><br>
      <!-- Graph visualization of individuals --><br>
    </div><br>
  </div><br>
</section><br>
```<br>
<br>
#### 3.2 Individual Data Management<br>
**Data Structure**:<br>
```javascript<br>
const individual = {<br>
  // Core identification<br>
  id: "req_001_component_001",<br>
  iri: "http://org/project/ontologies/name#Component_001",<br>
  type: "Component", // Class type<br>
<br>
  // Basic properties<br>
  label: "Primary Navigation System",<br>
  description: "Main navigation system for vessel guidance",<br>
<br>
  // Extraction metadata<br>
  confidence: 0.85,<br>
  source_requirement: "req_001",<br>
  extraction_method: "llm_analysis",<br>
<br>
  // Ontology properties<br>
  properties: {<br>
    hasName: "Primary Navigation System",<br>
    hasSerialNumber: "NAV-001-PRI",<br>
    hasMass: {<br>
      numericValue: 45.5,<br>
      unit: "kg",<br>
      quantityKind: "Mass"<br>
    }<br>
  },<br>
<br>
  // Provenance<br>
  creator: "admin",<br>
  created_date: "2025-09-10",<br>
  last_modified_by: "admin",<br>
  last_modified_date: "2025-09-10",<br>
<br>
  // Relationships<br>
  relationships: [<br>
    {<br>
      predicate: "realizes",<br>
      target: "function_001",<br>
      confidence: 0.9<br>
    }<br>
  ]<br>
};<br>
```<br>
<br>
#### 3.3 Bulk Operations<br>
**Features Needed**:<br>
- **Bulk Validation**: Validate selected individuals against SHACL<br>
- **Bulk Export**: Export individuals to various formats<br>
- **Bulk Classification**: Change class assignments<br>
- **Bulk Property Updates**: Update common properties<br>
- **Bulk Deletion**: Remove individuals with confirmation<br>
<br>
### 4. Digital Assistant System (DAS) Integration<br>
<br>
#### 4.1 DAS API Knowledge Base Structure<br>
**Qdrant Collection**: `das_ontology_api_knowledge`<br>
<br>
**Knowledge Documents**:<br>
```json<br>
{<br>
  "id": "create_ontology_class",<br>
  "title": "Create Ontology Class",<br>
  "content": "To create a new class in an ontology, use POST /api/das/ontology/create-class with parameters: ontology_iri (required), class_name (required), label (optional), description (optional), parent_class (optional)",<br>
  "category": "ontology_operations",<br>
  "examples": [<br>
    {<br>
      "description": "Create a Component class",<br>
      "request": {<br>
        "ontology_iri": "http://org/project/ontologies/systems",<br>
        "class_name": "Component",<br>
        "label": "System Component",<br>
        "description": "A physical or logical component of a system"<br>
      }<br>
    }<br>
  ],<br>
  "related_operations": ["create_individual", "add_property"],<br>
  "metadata": {<br>
    "last_updated": "2025-09-10",<br>
    "version": "1.0"<br>
  }<br>
}<br>
```<br>
<br>
#### 4.2 DAS Integration Points<br>
**Query Processing**:<br>
```python<br>
# Add to RAG system<br>
def process_ontology_query(query: str, context: Dict):<br>
    """Process ontology-related DAS queries"""<br>
<br>
    # 1. Detect ontology operations<br>
    if is_ontology_operation(query):<br>
        # 2. Retrieve relevant API documentation<br>
        api_docs = retrieve_ontology_api_docs(query)<br>
<br>
        # 3. Generate response with API instructions<br>
        response = generate_ontology_api_response(query, api_docs, context)<br>
<br>
        # 4. Include executable code examples<br>
        response.code_examples = generate_api_examples(query, context)<br>
<br>
        return response<br>
<br>
    return standard_rag_response(query, context)<br>
```<br>
<br>
**API Documentation Categories**:<br>
- **Class Management**: Create, modify, delete ontology classes<br>
- **Property Management**: Object and data property operations<br>
- **Individual Management**: Create, validate, query individuals<br>
- **Import Operations**: Add, remove, manage imported ontologies<br>
- **Validation Operations**: SHACL validation and constraint checking<br>
- **Query Operations**: SPARQL queries and data retrieval<br>
<br>
#### 4.3 DAS Workflow Integration<br>
**Requirement Processing Workflow**:<br>
1. **DAS receives requirement** text from user<br>
2. **DAS queries ontology API knowledge** for relevant operations<br>
3. **DAS generates API calls** to create individuals and relationships<br>
4. **DAS validates created individuals** against SHACL constraints<br>
5. **DAS reports results** back to user with confidence scores<br>
6. **User reviews and approves** in Individuals workbench<br>
<br>
## Risk Assessment and Mitigation<br>
<br>
### High Risk Items<br>
1. **OWL Synchronization Complexity**<br>
   - **Risk**: Bidirectional sync between diagram and code<br>
   - **Mitigation**: Implement robust conflict detection and user guidance<br>
<br>
2. **Performance with Large Individual Sets**<br>
   - **Risk**: Hundreds of individuals may impact UI performance<br>
   - **Mitigation**: Implement pagination, virtual scrolling, and efficient filtering<br>
<br>
3. **SHACL Validation Performance**<br>
   - **Risk**: Complex constraints may slow down real-time validation<br>
   - **Mitigation**: Asynchronous validation with progress indicators<br>
<br>
### Medium Risk Items<br>
1. **DAS API Complexity**<br>
   - **Risk**: Complex API surface area for DAS to understand<br>
   - **Mitigation**: Comprehensive knowledge base with clear examples<br>
<br>
2. **Python Library Integration**<br>
   - **Risk**: Dependency management and version conflicts<br>
   - **Mitigation**: Careful library selection and testing<br>
<br>
## Success Criteria<br>
<br>
### Phase 1 Success (OWL Editor)<br>
- [ ] Users can switch seamlessly between diagram and OWL code<br>
- [ ] Changes in either mode sync automatically to the other<br>
- [ ] OWL syntax validation prevents invalid code<br>
- [ ] Export/import OWL files in multiple formats<br>
<br>
### Phase 2 Success (SHACL)<br>
- [ ] Visual SHACL constraint editor integrated<br>
- [ ] Real-time validation of individuals against constraints<br>
- [ ] Comprehensive validation reports with actionable feedback<br>
- [ ] Unit checking and engineering constraint support<br>
<br>
### Phase 3 Success (Individuals)<br>
- [ ] Dedicated individuals management interface<br>
- [ ] Efficient handling of hundreds of individuals<br>
- [ ] Advanced search and filtering capabilities<br>
- [ ] Bulk operations for individual management<br>
<br>
### Phase 4 Success (DAS Integration)<br>
- [ ] DAS can create ontology objects through API<br>
- [ ] Comprehensive API knowledge base in Qdrant<br>
- [ ] RAG system detects and handles ontology requests<br>
- [ ] End-to-end requirement-to-individual workflow<br>
<br>
## Next Steps<br>
<br>
### Immediate (Next Session)<br>
1. **OWL Editor**: Begin implementation of text editor integration<br>
2. **SHACL Research**: Investigate Python SHACL libraries and integration options<br>
3. **Individual Design**: Create detailed mockups for individuals workbench<br>
<br>
### Short-term (1-2 weeks)<br>
1. **OWL Editor**: Complete bidirectional synchronization<br>
2. **SHACL Prototype**: Basic constraint editor and validation<br>
3. **DAS Planning**: Detailed API design and knowledge base structure<br>
<br>
### Medium-term (1-2 months)<br>
1. **Full SHACL Implementation**: Complete constraint system<br>
2. **Individuals Workbench**: Production-ready individual management<br>
3. **DAS Integration**: Full API integration with knowledge base<br>
<br>
---<br>
<br>
**Priority**: High - These features will transform the ontology workbench from an MVP to a production-ready ontology development environment.<br>
<br>
**Estimated Effort**:<br>
- Phase 1 (OWL Editor): 3-4 weeks<br>
- Phase 2 (SHACL): 4-5 weeks<br>
- Phase 3 (Individuals): 3-4 weeks<br>
- Phase 4 (DAS Integration): 2-3 weeks<br>
<br>
**Dependencies**:<br>
- Completed MVP (✅ Done)<br>
- Python environment setup for OWL/SHACL libraries<br>
- DAS system architecture (in development)<br>
- Qdrant knowledge base infrastructure (✅ Available)<br>

