# Ontology Workbench Upgrade Plan<br>
<br>
**Version**: 1.0<br>
**Date**: 2025-01-27<br>
**Status**: Implementation Planning<br>
<br>
## Executive Summary<br>
<br>
This document outlines the comprehensive upgrade plan for the ODRAS ontology workbench to align with our new namespace and project naming conventions, plus best practices for managing external ontology imports. The current system has several gaps that need to be addressed to fully leverage our organizational URI structure.<br>
<br>
## Current State Analysis<br>
<br>
### ✅ What's Working Well<br>
1. **Project Namespace Inheritance**: Ontologies correctly inherit their project's namespace<br>
2. **Simplified Creation**: Basic ontology creation modal with project namespace display<br>
3. **External Import Support**: URL-based ontology import functionality exists<br>
4. **Reference Ontology Management**: Admin can mark ontologies as reference for ODRAS users<br>
5. **Import Best Practices**: URL-based imports with proper validation and conflict detection<br>
6. **Fuseki Integration**: Proper RDF storage and retrieval<br>
7. **Admin UI Controls**: Admin badge and workbench properly hidden for non-admin users<br>
<br>
### ✅ Completed MVP Features (2025-09-10)<br>
<br>
#### 1. **Visual Ontology Editor**<br>
- **Completed**: Full Cytoscape-based visual editor with direct manipulation<br>
- **Features**: Drag-to-create, inline editing, visual connections, multiple layouts<br>
- **Impact**: Professional ontology development environment<br>
<br>
#### 2. **Import Management System**<br>
- **Completed**: Complete external ontology import with read-only protection<br>
- **Features**: URL imports, reference ontology library, proper IRI attribution<br>
- **Impact**: Enables ontology reuse and collaboration<br>
<br>
#### 3. **Rich Metadata Tracking**<br>
- **Completed**: Comprehensive metadata with Dublin Core annotations<br>
- **Features**: Creator tracking, creation/modification dates, automatic metadata updates<br>
- **Impact**: Full provenance tracking for all ontology objects<br>
<br>
#### 4. **Advanced UI Features**<br>
- **Completed**: Professional interface with comprehensive controls<br>
- **Features**: Visibility management, named views, note system, tree-canvas sync<br>
- **Impact**: Enterprise-grade user experience<br>
<br>
#### 5. **Layout and State Persistence**<br>
- **Completed**: Server-synchronized layout and state management<br>
- **Features**: Position persistence, view configurations, import state retention<br>
- **Impact**: Reliable workspace preservation across sessions<br>
<br>
### 🔄 Remaining Gaps for Post-MVP<br>
<br>
#### 1. **OWL Code Editor Integration**<br>
- **Gap**: No direct OWL/Turtle code editing capability<br>
- **Impact**: Advanced users cannot directly edit OWL syntax<br>
- **Planned**: Dual-mode editor with diagram ↔ code synchronization<br>
<br>
#### 2. **SHACL Constraint System**<br>
- **Gap**: No constraint definition or validation system<br>
- **Impact**: Cannot validate individuals or enforce data quality<br>
- **Planned**: Visual SHACL editor with Python validation backend<br>
<br>
#### 3. **Individual/Instance Management**<br>
- **Gap**: No dedicated system for managing ontology individuals<br>
- **Impact**: Cannot efficiently handle hundreds of extracted requirement individuals<br>
- **Planned**: Dedicated individuals workbench with filtering and bulk operations<br>
<br>
#### 4. **DAS Integration**<br>
- **Gap**: No API integration for Digital Assistant System<br>
- **Impact**: DAS cannot create or manage ontology objects<br>
- **Planned**: API endpoints with knowledge base integration<br>
<br>
## Implementation Plan<br>
<br>
### Phase 1: Core URI Generation Alignment (High Priority)<br>
<br>
#### 1.1 Update Ontology URI Generation<br>
- **Action**: Modify `create_ontology` endpoint to use project namespace<br>
- **Implementation**:<br>
  - Query project's namespace from `namespace_registry`<br>
  - Generate URI: `http://{org}/{namespace-path}/{project-id}/ontologies/{name}`<br>
  - Update `NamespaceURIGenerator` to support project-scoped URIs<br>
- **Files**: `backend/main.py`, `backend/services/namespace_uri_generator.py`<br>
<br>
#### 1.2 Update Frontend URI Display<br>
- **Action**: Show proper organizational URIs in ontology creation modal<br>
- **Implementation**:<br>
  - Display full project namespace path<br>
  - Show generated ontology URI preview<br>
  - Update URI generation in real-time<br>
- **Files**: `frontend/app.html`<br>
<br>
#### 1.3 Migrate Existing Ontologies<br>
- **Action**: Update existing ontology URIs to new structure<br>
- **Implementation**:<br>
  - Create migration script for existing ontologies<br>
  - Update Fuseki named graphs<br>
  - Update `ontologies_registry` table<br>
- **Files**: New migration script<br>
<br>
### Phase 2: Enhanced Ontology Management (Medium Priority)<br>
<br>
#### 2.1 Add Ontology Metadata Fields<br>
- **Action**: Extend ontology model with organizational metadata<br>
- **Implementation**:<br>
  - Add `domain`, `version`, `status` fields to ontologies<br>
  - Update database schema<br>
  - Modify creation/editing interfaces<br>
- **Files**: Database migration, `backend/main.py`, `frontend/app.html`<br>
<br>
#### 2.2 Implement Ontology CRUD Operations<br>
- **Action**: Add full CRUD operations for ontologies<br>
- **Implementation**:<br>
  - GET, PUT, DELETE endpoints for individual ontologies<br>
  - Ontology editing modal with metadata<br>
  - Version management and history<br>
- **Files**: `backend/main.py`, `frontend/app.html`<br>
<br>
#### 2.3 Add Ontology Actions Menu<br>
- **Action**: Implement ontology actions (edit, archive, export, delete)<br>
- **Implementation**:<br>
  - Context menu for ontology nodes<br>
  - Action buttons in ontology list<br>
  - Confirmation dialogs for destructive actions<br>
- **Files**: `frontend/app.html`<br>
<br>
### Phase 3: Ontology Import and Sharing Management (High Priority)<br>
<br>
#### 3.1 Cross-Project Ontology Import<br>
- **Action**: Enable users to import ontologies from other projects<br>
- **Implementation**:<br>
  - Project ontology browser and selector<br>
  - Import permission checking<br>
  - Namespace resolution for cross-project imports<br>
- **Files**: `frontend/app.html`, `backend/api/ontology_imports.py`<br>
<br>
#### 3.2 Reference Ontology Import<br>
- **Action**: Allow users to import admin-managed reference ontologies<br>
- **Implementation**:<br>
  - Reference ontology library interface<br>
  - Import from reference ontology registry<br>
  - Automatic namespace mapping<br>
- **Files**: `frontend/app.html`, `backend/api/reference_ontologies.py`<br>
<br>
#### 3.3 Nested Import Support<br>
- **Action**: Support importing ontologies that have their own imports<br>
- **Implementation**:<br>
  - Recursive import resolution<br>
  - Show/hide nested imports in visualization<br>
  - Auto-link equivalent classes between imports<br>
  - Import dependency visualization<br>
- **Files**: `backend/services/nested_import_resolver.py`<br>
<br>
#### 3.4 Import Visualization in Cytoscape<br>
- **Action**: Show imported ontologies and their relationships in the canvas<br>
- **Implementation**:<br>
  - **Collapsed View**: Imported ontologies shown as single round entities by default<br>
  - **Expandable**: Users can expand imported ontologies to view internal details<br>
  - Import hierarchy visualization<br>
  - Different styling for imported vs. local elements<br>
  - Show/hide controls for nested imports<br>
  - Auto-linking of equivalent classes between imports<br>
  - **IMMUTABLE**: Imported ontologies cannot be edited (only visual positioning)<br>
- **Files**: `frontend/app.html` (Cytoscape integration)<br>
<br>
#### 3.5 User-to-User Ontology Sharing<br>
- **Action**: Enable users to share ontologies with specific users<br>
- **Implementation**:<br>
  - Ontology sharing permissions<br>
  - User invitation system<br>
  - Shared ontology workspace<br>
- **Files**: `backend/api/ontology_sharing.py`, `frontend/app.html`<br>
<br>
### Phase 4: Data Object Management (Medium Priority)<br>
<br>
#### 4.1 Data Object Modeling Framework<br>
- **Action**: Create clear patterns for managing data objects in ontologies<br>
- **Implementation**:<br>
  - Data object classification system<br>
  - Relationship pattern templates<br>
  - Data object lifecycle management<br>
- **Files**: New data object management system<br>
<br>
#### 4.2 Data Object Relationship Management<br>
- **Action**: Provide tools for managing complex data object relationships<br>
- **Implementation**:<br>
  - Relationship type definitions<br>
  - Cardinality constraints<br>
  - Relationship validation<br>
- **Files**: `backend/services/data_object_manager.py`<br>
<br>
#### 4.3 Data Object Visualization<br>
- **Action**: Specialized visualization for data objects and their relationships<br>
- **Implementation**:<br>
  - Data object-specific Cytoscape layouts<br>
  - Relationship strength indicators<br>
  - Data object clustering<br>
- **Files**: `frontend/app.html` (Cytoscape extensions)<br>
<br>
### Phase 5: External Ontology Management (Low Priority)<br>
<br>
#### 5.1 Admin Interface for External Ontologies<br>
- **Action**: Create admin panel for managing external ontologies<br>
- **Implementation**:<br>
  - External ontology registry<br>
  - Import/export management<br>
  - Version tracking and updates<br>
- **Files**: New admin interface, `backend/api/external_ontologies.py`<br>
<br>
#### 5.2 Import Validation and Conflict Detection<br>
- **Action**: Implement best practices for external ontology imports<br>
- **Implementation**:<br>
  - Namespace conflict detection<br>
  - Import validation rules<br>
  - Dependency management<br>
- **Files**: `backend/services/ontology_import_validator.py`<br>
<br>
#### 5.3 Reference Ontology Library<br>
- **Action**: Create curated library of reference ontologies<br>
- **Implementation**:<br>
  - Pre-configured external ontologies<br>
  - Standard namespace mappings<br>
  - Import templates and guides<br>
- **Files**: New reference ontology management system<br>
<br>
### Phase 6: OWL Code Editor Integration (High Priority - Post-MVP)<br>
<br>
#### 6.1 Dual-Mode Ontology Editor<br>
- **Action**: Add OWL/Turtle code editor alongside visual diagram<br>
- **Implementation**:<br>
  - Monaco Editor or CodeMirror integration<br>
  - Real-time bidirectional synchronization (diagram ↔ OWL code)<br>
  - OWL syntax highlighting and validation<br>
  - Conflict resolution when both modes are edited<br>
- **Inspiration**: Similar to Camunda's BPMN modeler with XML view<br>
- **Files**: `frontend/app.html`, new OWL parser/serializer modules<br>
<br>
#### 6.2 OWL Format Support<br>
- **Action**: Support multiple OWL serialization formats<br>
- **Implementation**:<br>
  - Turtle, RDF/XML, JSON-LD import/export<br>
  - Format conversion utilities<br>
  - Syntax validation for all formats<br>
- **Files**: Backend OWL processing services<br>
<br>
### Phase 7: SHACL Constraints and Validation (High Priority - Post-MVP)<br>
<br>
#### 7.1 Visual SHACL Shape Editor<br>
- **Action**: Create GUI for defining SHACL constraints<br>
- **Implementation**:<br>
  - Visual constraint builder for classes and properties<br>
  - Template-based constraint creation<br>
  - Unit validation with QUDT integration<br>
  - Multiplicity and value bounding constraints<br>
- **Files**: New SHACL editor components<br>
<br>
#### 7.2 Python OWL/SHACL Integration<br>
- **Action**: Integrate Python OWL ecosystem for advanced validation<br>
- **Implementation**:<br>
  - **owlready2**: OWL ontology manipulation<br>
  - **pyshacl**: SHACL validation engine<br>
  - **rdflib**: RDF graph operations<br>
  - **pint**: Unit conversion and validation<br>
- **Files**: `backend/services/shacl_validator.py`, requirements.txt<br>
<br>
#### 7.3 Real-time Validation System<br>
- **Action**: Validate individuals and constraints in real-time<br>
- **Implementation**:<br>
  - Live validation as users create individuals<br>
  - Batch validation for existing data<br>
  - Validation reports with error locations and suggestions<br>
  - Engineering-specific constraints (units, bounds, patterns)<br>
- **Files**: Backend validation services, frontend validation UI<br>
<br>
### Phase 8: Individual/Instance Management (High Priority - Post-MVP)<br>
<br>
#### 8.1 Individuals Workbench<br>
- **Action**: Create dedicated interface for managing ontology individuals<br>
- **Challenge**: Handle hundreds of requirement-extracted individuals efficiently<br>
- **Implementation Options**:<br>
  - **Option A**: Extend ontology tree with grouped individuals<br>
  - **Option B**: Separate individuals tab with table/search interface (RECOMMENDED)<br>
  - **Option C**: Hybrid approach with tree summary and detailed table<br>
- **Files**: New individuals workbench tab<br>
<br>
#### 8.2 Individual Management Features<br>
- **Action**: Comprehensive individual lifecycle management<br>
- **Implementation**:<br>
  - Table view with sorting, filtering, pagination<br>
  - Full-text search across individual properties<br>
  - Bulk operations (validate, export, classify, delete)<br>
  - Individual-requirement traceability<br>
  - Confidence scoring and review workflows<br>
- **Files**: Individuals management system<br>
<br>
#### 8.3 LLM-Generated Individual Processing<br>
- **Action**: Handle LLM-extracted requirement individuals<br>
- **Implementation**:<br>
  - Batch import of LLM-generated individuals<br>
  - Confidence-based review workflows<br>
  - Automatic class assignment and validation<br>
  - Component/Interface/Process/Function generation from requirements<br>
- **Files**: LLM integration services<br>
<br>
### Phase 9: Digital Assistant System (DAS) Integration (Medium Priority - Post-MVP)<br>
<br>
#### 9.1 DAS-Ontology API Design<br>
- **Action**: Create API endpoints for DAS to manage ontology objects<br>
- **Implementation**:<br>
  - `POST /api/das/ontology/create-class`<br>
  - `POST /api/das/ontology/create-individual`<br>
  - `POST /api/das/ontology/validate`<br>
  - `GET /api/das/ontology/query`<br>
- **Files**: `backend/api/das_ontology.py`<br>
<br>
#### 9.2 DAS Knowledge Base for API Instructions<br>
- **Action**: Create comprehensive API knowledge base in Qdrant<br>
- **Implementation**:<br>
  - API documentation with examples in Qdrant<br>
  - Ontology operation patterns and best practices<br>
  - Error handling and troubleshooting guides<br>
  - Integration with RAG system for API guidance<br>
- **Files**: DAS knowledge base population scripts<br>
<br>
#### 9.3 RAG Integration for Ontology Operations<br>
- **Action**: Enable RAG system to detect and handle ontology requests<br>
- **Implementation**:<br>
  - Query classification for ontology operations<br>
  - Context retrieval from API knowledge base<br>
  - Action guidance with executable code examples<br>
  - End-to-end requirement-to-individual workflows<br>
- **Files**: RAG system ontology integration<br>
<br>
### Phase 10: Advanced Features (Low Priority)<br>
<br>
#### 10.1 Ontology Versioning<br>
- **Action**: Implement proper ontology versioning<br>
- **Implementation**:<br>
  - Version IRIs and tracking<br>
  - Change history and diff<br>
  - Rollback capabilities<br>
- **Files**: Version management system<br>
<br>
#### 10.2 Ontology Dependencies<br>
- **Action**: Manage ontology import dependencies<br>
- **Implementation**:<br>
  - Dependency graph visualization<br>
  - Circular dependency detection<br>
  - Automatic dependency updates<br>
- **Files**: Dependency management system<br>
<br>
#### 10.3 Ontology Publishing<br>
- **Action**: Publish ontologies to external endpoints<br>
- **Implementation**:<br>
  - Public ontology endpoints<br>
  - Content negotiation<br>
  - API documentation generation<br>
- **Files**: Publishing system<br>
<br>
## Detailed Implementation Actions<br>
<br>
### Immediate Actions (This Session)<br>
<br>
#### 1. Update Ontology URI Generation<br>
```python<br>
# In backend/main.py create_ontology function<br>
# Replace current URI generation with:<br>
project_namespace = get_project_namespace(project)<br>
if project_namespace:<br>
    graph_iri = f"{settings.installation_base_uri}/{project_namespace['path']}/{project}/{name}"<br>
else:<br>
    # Fallback for projects without namespace<br>
    graph_iri = f"{settings.installation_base_uri}/projects/{project}/{name}"<br>
```<br>
<br>
#### 2. Add Project Namespace Display<br>
```javascript<br>
// In frontend/app.html showCreateOntologyModal function<br>
// Update namespace display to show full organizational path<br>
async function loadCurrentProjectNamespace(displayElement) {<br>
  const currentProjectId = localStorage.getItem('active_project_id');<br>
  const response = await fetch(`/api/projects/${currentProjectId}/namespace`);<br>
  const namespaceData = await response.json();<br>
  displayElement.textContent = namespaceData.namespace_path || 'No namespace assigned';<br>
}<br>
```<br>
<br>
#### 3. Update URI Preview<br>
```javascript<br>
// Add real-time URI preview in ontology creation modal<br>
function updateOntologyUriPreview() {<br>
  const name = document.getElementById('simpleOntologyName').value;<br>
  const namespaceDisplay = document.getElementById('modalNamespaceDisplay').textContent;<br>
  const projectId = localStorage.getItem('active_project_id');<br>
<br>
  if (name && namespaceDisplay && projectId) {<br>
    const uri = `http://${namespaceDisplay}/${projectId}/ontologies/${name}`;<br>
    document.getElementById('ontologyUriPreview').textContent = uri;<br>
  }<br>
}<br>
```<br>
<br>
### Next Session Actions<br>
<br>
#### 1. Database Schema Updates<br>
```sql<br>
-- Add ontology metadata fields<br>
ALTER TABLE public.ontologies_registry ADD COLUMN IF NOT EXISTS domain VARCHAR(255);<br>
ALTER TABLE public.ontologies_registry ADD COLUMN IF NOT EXISTS version VARCHAR(50) DEFAULT '1.0.0';<br>
ALTER TABLE public.ontologies_registry ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'active';<br>
ALTER TABLE public.ontologies_registry ADD COLUMN IF NOT EXISTS description TEXT;<br>
```<br>
<br>
#### 2. Ontology CRUD Endpoints<br>
```python<br>
# Add to backend/main.py<br>
@app.get("/api/ontologies/{ontology_id}")<br>
async def get_ontology(ontology_id: str, user=Depends(get_user)):<br>
    """Get individual ontology details"""<br>
<br>
@app.put("/api/ontologies/{ontology_id}")<br>
async def update_ontology(ontology_id: str, body: Dict, user=Depends(get_user)):<br>
    """Update ontology metadata"""<br>
<br>
@app.delete("/api/ontologies/{ontology_id}")<br>
async def delete_ontology(ontology_id: str, user=Depends(get_user)):<br>
    """Delete ontology"""<br>
```<br>
<br>
#### 3. External Ontology Management<br>
```python<br>
# New file: backend/api/external_ontologies.py<br>
@router.get("/api/admin/external-ontologies")<br>
async def list_external_ontologies(admin_user=Depends(get_admin_user)):<br>
    """List all external/reference ontologies"""<br>
<br>
@router.post("/api/admin/external-ontologies")<br>
async def add_external_ontology(body: Dict, admin_user=Depends(get_admin_user)):<br>
    """Add new external ontology to registry"""<br>
```<br>
<br>
## Best Practices Implementation<br>
<br>
### 1. Namespace Management<br>
- **Principle**: All ontologies inherit their project's namespace<br>
- **Implementation**: Automatic namespace inheritance, no manual selection<br>
- **Validation**: Ensure project has valid namespace before ontology creation<br>
<br>
### 2. External Ontology Imports<br>
- **Principle**: Controlled imports with validation and conflict detection<br>
- **Implementation**:<br>
  - Admin-managed external ontology registry<br>
  - Import validation before adding to projects<br>
  - Namespace conflict detection<br>
  - **IMMUTABILITY**: Imported ontologies are read-only<br>
- **Validation**: Check for naming conflicts, circular dependencies<br>
<br>
### 2.1 Import Immutability Rules<br>
- **Principle**: Imported ontologies cannot be modified by importers<br>
- **Implementation**:<br>
  - Read-only access to imported ontology content<br>
  - Visual positioning only for Cytoscape nodes<br>
  - Show/hide controls for nested imports<br>
  - Auto-linking of equivalent classes<br>
- **Rationale**: Prevents corruption of shared reference ontologies<br>
<br>
### 3. URI Consistency<br>
- **Principle**: All URIs follow organizational hierarchy<br>
- **Implementation**:<br>
  - Project URIs: `http://{org}/{namespace}/{project-id}/ontologies/{name}`<br>
  - External URIs: Preserved as-is for imports<br>
  - System URIs: `http://{org}/admin/ontologies/{name}`<br>
<br>
### 4. Metadata Completeness<br>
- **Principle**: Rich metadata for discoverability and management<br>
- **Implementation**:<br>
  - Domain association from project<br>
  - Version tracking and history<br>
  - Status management (active, deprecated, archived)<br>
  - Description and documentation<br>
<br>
## Current Discussion Points (2025-01-27)<br>
<br>
### Reference Ontology Management<br>
- **Status**: ✅ **COMPLETED** - Admin can mark ontologies as reference for ODRAS users<br>
- **Implementation**: Admin workbench with reference ontology toggle<br>
- **Next Steps**: Focus on import capabilities rather than editing reference ontologies<br>
<br>
### Import Capabilities Priority<br>
- **Cross-Project Imports**: Users need to import ontologies from other projects<br>
- **Reference Ontology Imports**: Users need to import admin-managed reference ontologies<br>
- **Nested Imports**: Support for ontologies that import other ontologies<br>
- **Visualization**: Show imported ontologies in Cytoscape canvas with proper styling<br>
<br>
### Import Constraints and Rules<br>
- **IMMUTABILITY**: Imported ontologies are read-only - users cannot edit their content<br>
- **Visual Positioning Only**: Users can only adjust Cytoscape node positions for imported elements<br>
- **Nested Import Controls**: Show/hide nested imports with toggle controls<br>
- **Auto-linking**: Automatically link equivalent classes between different imports<br>
- **Namespace Preservation**: Imported ontologies maintain their original namespaces<br>
<br>
### Nice to Have: Collapsible Import Visualization<br>
- **Collapsed View**: Imported ontologies appear as single round entities showing all equivalent relationships<br>
- **Expandable Detail**: Users can expand imported ontologies to view their internal structure and details<br>
- **Clean Canvas**: Keeps the main workspace uncluttered while preserving full access to imported content<br>
- **Progressive Disclosure**: Users see high-level relationships first, then drill down as needed<br>
<br>
### Data Object Management<br>
- **Status**: 🔄 **PLANNING** - Identified as confusing area requiring multiple iterations<br>
- **Approach**: Add to work list and iterate to get it right<br>
- **Focus**: Clear patterns for modeling and managing data objects in ontologies<br>
<br>
### User Sharing<br>
- **Status**: 📋 **PLANNED** - Enable users to share ontologies with each other<br>
- **Priority**: Medium - Important for collaboration but not critical for MVP<br>
<br>
## Success Criteria<br>
<br>
### Phase 1 Success<br>
- [ ] All new ontologies use project namespace URIs<br>
- [ ] Existing ontologies migrated to new URI structure<br>
- [ ] Frontend displays proper organizational URIs<br>
- [ ] URI generation is consistent across the system<br>
<br>
### Phase 2 Success<br>
- [ ] Full ontology CRUD operations implemented<br>
- [ ] Rich metadata support added<br>
- [ ] Ontology actions menu functional<br>
- [ ] Version management working<br>
<br>
### Phase 3 Success (Import & Sharing)<br>
- [ ] Cross-project ontology import functionality<br>
- [ ] Reference ontology import from admin-managed library<br>
- [ ] Nested import support with dependency resolution<br>
- [ ] Import visualization in Cytoscape canvas<br>
- [ ] User-to-user ontology sharing capabilities<br>
- [ ] **Nice to Have**: Collapsible import visualization (single entities with expand/collapse)<br>
<br>
### Phase 4 Success (Data Objects)<br>
- [ ] Data object modeling framework established<br>
- [ ] Clear patterns for data object relationships<br>
- [ ] Data object visualization in Cytoscape<br>
- [ ] Data object lifecycle management<br>
<br>
### Long-term Success<br>
- [ ] Complete ontology lifecycle management<br>
- [ ] Seamless external ontology integration<br>
- [ ] Professional ontology publishing capabilities<br>
- [ ] Full compliance with organizational URI standards<br>
- [ ] Robust data object management system<br>
<br>
## Risk Assessment<br>
<br>
### High Risk<br>
- **URI Migration**: Changing existing ontology URIs may break references<br>
- **Fuseki Integration**: Named graph updates require careful coordination<br>
<br>
### Medium Risk<br>
- **External Ontology Conflicts**: Import validation complexity<br>
- **User Experience**: Changes to familiar interfaces<br>
<br>
### Low Risk<br>
- **Metadata Addition**: Non-breaking schema changes<br>
- **Admin Interface**: New functionality, no existing dependencies<br>
<br>
## Next Steps<br>
<br>
1. **Immediate**: Update ontology URI generation to use project namespaces<br>
2. **This Session**: Implement project namespace display in creation modal<br>
3. **Next Session**: Add ontology metadata fields and CRUD operations<br>
4. **Priority Focus**: Implement cross-project and reference ontology import capabilities<br>
5. **Iterative Development**: Data object management - plan, implement, test, iterate<br>
6. **Future**: User sharing and advanced features<br>
<br>
---<br>
<br>
**Priority**: High - This aligns the ontology workbench with our organizational URI structure and enables proper namespace management.<br>
<br>
**Estimated Effort**:<br>
- Phase 1: 2-3 hours<br>
- Phase 2: 4-6 hours<br>
- Phase 3 (Import & Sharing): 8-12 hours<br>
- Phase 4 (Data Objects): 6-10 hours (iterative)<br>
- Phase 5 (External Management): 6-8 hours<br>
- Phase 6 (Advanced Features): 8-12 hours<br>
<br>
**Dependencies**: Requires completed namespace and project management systems (✅ Done)<br>
<br>
**Key Focus Areas**:<br>
- **Import Capabilities**: Critical for user productivity and ontology reuse<br>
- **Data Object Management**: Requires careful planning and iteration to get right<br>
- **Reference Ontology Integration**: Leverage existing admin capabilities<br>

