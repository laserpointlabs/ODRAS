# Ontology Workbench Upgrade Plan

**Version**: 1.0  
**Date**: 2025-01-27  
**Status**: Implementation Planning  

## Executive Summary

This document outlines the comprehensive upgrade plan for the ODRAS ontology workbench to align with our new namespace and project naming conventions, plus best practices for managing external ontology imports. The current system has several gaps that need to be addressed to fully leverage our organizational URI structure.

## Current State Analysis

### ✅ What's Working Well
1. **Project Namespace Inheritance**: Ontologies correctly inherit their project's namespace
2. **Simplified Creation**: Basic ontology creation modal with project namespace display
3. **External Import Support**: URL-based ontology import functionality exists
4. **Reference Ontology Management**: Admin can mark ontologies as reference for ODRAS users
5. **Import Best Practices**: URL-based imports with proper validation and conflict detection
6. **Fuseki Integration**: Proper RDF storage and retrieval
7. **Admin UI Controls**: Admin badge and workbench properly hidden for non-admin users

### ✅ Completed MVP Features (2025-09-10)

#### 1. **Visual Ontology Editor**
- **Completed**: Full Cytoscape-based visual editor with direct manipulation
- **Features**: Drag-to-create, inline editing, visual connections, multiple layouts
- **Impact**: Professional ontology development environment

#### 2. **Import Management System**  
- **Completed**: Complete external ontology import with read-only protection
- **Features**: URL imports, reference ontology library, proper IRI attribution
- **Impact**: Enables ontology reuse and collaboration

#### 3. **Rich Metadata Tracking**
- **Completed**: Comprehensive metadata with Dublin Core annotations
- **Features**: Creator tracking, creation/modification dates, automatic metadata updates
- **Impact**: Full provenance tracking for all ontology objects

#### 4. **Advanced UI Features**
- **Completed**: Professional interface with comprehensive controls
- **Features**: Visibility management, named views, note system, tree-canvas sync
- **Impact**: Enterprise-grade user experience

#### 5. **Layout and State Persistence**
- **Completed**: Server-synchronized layout and state management
- **Features**: Position persistence, view configurations, import state retention
- **Impact**: Reliable workspace preservation across sessions

### 🔄 Remaining Gaps for Post-MVP

#### 1. **OWL Code Editor Integration**
- **Gap**: No direct OWL/Turtle code editing capability
- **Impact**: Advanced users cannot directly edit OWL syntax
- **Planned**: Dual-mode editor with diagram ↔ code synchronization

#### 2. **SHACL Constraint System**
- **Gap**: No constraint definition or validation system
- **Impact**: Cannot validate individuals or enforce data quality
- **Planned**: Visual SHACL editor with Python validation backend

#### 3. **Individual/Instance Management**
- **Gap**: No dedicated system for managing ontology individuals
- **Impact**: Cannot efficiently handle hundreds of extracted requirement individuals
- **Planned**: Dedicated individuals workbench with filtering and bulk operations

#### 4. **DAS Integration**
- **Gap**: No API integration for Digital Assistant System
- **Impact**: DAS cannot create or manage ontology objects
- **Planned**: API endpoints with knowledge base integration

## Implementation Plan

### Phase 1: Core URI Generation Alignment (High Priority)

#### 1.1 Update Ontology URI Generation
- **Action**: Modify `create_ontology` endpoint to use project namespace
- **Implementation**: 
  - Query project's namespace from `namespace_registry`
  - Generate URI: `http://{org}/{namespace-path}/{project-id}/ontologies/{name}`
  - Update `NamespaceURIGenerator` to support project-scoped URIs
- **Files**: `backend/main.py`, `backend/services/namespace_uri_generator.py`

#### 1.2 Update Frontend URI Display
- **Action**: Show proper organizational URIs in ontology creation modal
- **Implementation**:
  - Display full project namespace path
  - Show generated ontology URI preview
  - Update URI generation in real-time
- **Files**: `frontend/app.html`

#### 1.3 Migrate Existing Ontologies
- **Action**: Update existing ontology URIs to new structure
- **Implementation**:
  - Create migration script for existing ontologies
  - Update Fuseki named graphs
  - Update `ontologies_registry` table
- **Files**: New migration script

### Phase 2: Enhanced Ontology Management (Medium Priority)

#### 2.1 Add Ontology Metadata Fields
- **Action**: Extend ontology model with organizational metadata
- **Implementation**:
  - Add `domain`, `version`, `status` fields to ontologies
  - Update database schema
  - Modify creation/editing interfaces
- **Files**: Database migration, `backend/main.py`, `frontend/app.html`

#### 2.2 Implement Ontology CRUD Operations
- **Action**: Add full CRUD operations for ontologies
- **Implementation**:
  - GET, PUT, DELETE endpoints for individual ontologies
  - Ontology editing modal with metadata
  - Version management and history
- **Files**: `backend/main.py`, `frontend/app.html`

#### 2.3 Add Ontology Actions Menu
- **Action**: Implement ontology actions (edit, archive, export, delete)
- **Implementation**:
  - Context menu for ontology nodes
  - Action buttons in ontology list
  - Confirmation dialogs for destructive actions
- **Files**: `frontend/app.html`

### Phase 3: Ontology Import and Sharing Management (High Priority)

#### 3.1 Cross-Project Ontology Import
- **Action**: Enable users to import ontologies from other projects
- **Implementation**:
  - Project ontology browser and selector
  - Import permission checking
  - Namespace resolution for cross-project imports
- **Files**: `frontend/app.html`, `backend/api/ontology_imports.py`

#### 3.2 Reference Ontology Import
- **Action**: Allow users to import admin-managed reference ontologies
- **Implementation**:
  - Reference ontology library interface
  - Import from reference ontology registry
  - Automatic namespace mapping
- **Files**: `frontend/app.html`, `backend/api/reference_ontologies.py`

#### 3.3 Nested Import Support
- **Action**: Support importing ontologies that have their own imports
- **Implementation**:
  - Recursive import resolution
  - Show/hide nested imports in visualization
  - Auto-link equivalent classes between imports
  - Import dependency visualization
- **Files**: `backend/services/nested_import_resolver.py`

#### 3.4 Import Visualization in Cytoscape
- **Action**: Show imported ontologies and their relationships in the canvas
- **Implementation**:
  - **Collapsed View**: Imported ontologies shown as single round entities by default
  - **Expandable**: Users can expand imported ontologies to view internal details
  - Import hierarchy visualization
  - Different styling for imported vs. local elements
  - Show/hide controls for nested imports
  - Auto-linking of equivalent classes between imports
  - **IMMUTABLE**: Imported ontologies cannot be edited (only visual positioning)
- **Files**: `frontend/app.html` (Cytoscape integration)

#### 3.5 User-to-User Ontology Sharing
- **Action**: Enable users to share ontologies with specific users
- **Implementation**:
  - Ontology sharing permissions
  - User invitation system
  - Shared ontology workspace
- **Files**: `backend/api/ontology_sharing.py`, `frontend/app.html`

### Phase 4: Data Object Management (Medium Priority)

#### 4.1 Data Object Modeling Framework
- **Action**: Create clear patterns for managing data objects in ontologies
- **Implementation**:
  - Data object classification system
  - Relationship pattern templates
  - Data object lifecycle management
- **Files**: New data object management system

#### 4.2 Data Object Relationship Management
- **Action**: Provide tools for managing complex data object relationships
- **Implementation**:
  - Relationship type definitions
  - Cardinality constraints
  - Relationship validation
- **Files**: `backend/services/data_object_manager.py`

#### 4.3 Data Object Visualization
- **Action**: Specialized visualization for data objects and their relationships
- **Implementation**:
  - Data object-specific Cytoscape layouts
  - Relationship strength indicators
  - Data object clustering
- **Files**: `frontend/app.html` (Cytoscape extensions)

### Phase 5: External Ontology Management (Low Priority)

#### 5.1 Admin Interface for External Ontologies
- **Action**: Create admin panel for managing external ontologies
- **Implementation**:
  - External ontology registry
  - Import/export management
  - Version tracking and updates
- **Files**: New admin interface, `backend/api/external_ontologies.py`

#### 5.2 Import Validation and Conflict Detection
- **Action**: Implement best practices for external ontology imports
- **Implementation**:
  - Namespace conflict detection
  - Import validation rules
  - Dependency management
- **Files**: `backend/services/ontology_import_validator.py`

#### 5.3 Reference Ontology Library
- **Action**: Create curated library of reference ontologies
- **Implementation**:
  - Pre-configured external ontologies
  - Standard namespace mappings
  - Import templates and guides
- **Files**: New reference ontology management system

### Phase 6: OWL Code Editor Integration (High Priority - Post-MVP)

#### 6.1 Dual-Mode Ontology Editor
- **Action**: Add OWL/Turtle code editor alongside visual diagram
- **Implementation**:
  - Monaco Editor or CodeMirror integration
  - Real-time bidirectional synchronization (diagram ↔ OWL code)
  - OWL syntax highlighting and validation
  - Conflict resolution when both modes are edited
- **Inspiration**: Similar to Camunda's BPMN modeler with XML view
- **Files**: `frontend/app.html`, new OWL parser/serializer modules

#### 6.2 OWL Format Support
- **Action**: Support multiple OWL serialization formats
- **Implementation**:
  - Turtle, RDF/XML, JSON-LD import/export
  - Format conversion utilities
  - Syntax validation for all formats
- **Files**: Backend OWL processing services

### Phase 7: SHACL Constraints and Validation (High Priority - Post-MVP)

#### 7.1 Visual SHACL Shape Editor
- **Action**: Create GUI for defining SHACL constraints
- **Implementation**:
  - Visual constraint builder for classes and properties
  - Template-based constraint creation
  - Unit validation with QUDT integration
  - Multiplicity and value bounding constraints
- **Files**: New SHACL editor components

#### 7.2 Python OWL/SHACL Integration
- **Action**: Integrate Python OWL ecosystem for advanced validation
- **Implementation**:
  - **owlready2**: OWL ontology manipulation
  - **pyshacl**: SHACL validation engine  
  - **rdflib**: RDF graph operations
  - **pint**: Unit conversion and validation
- **Files**: `backend/services/shacl_validator.py`, requirements.txt

#### 7.3 Real-time Validation System
- **Action**: Validate individuals and constraints in real-time
- **Implementation**:
  - Live validation as users create individuals
  - Batch validation for existing data
  - Validation reports with error locations and suggestions
  - Engineering-specific constraints (units, bounds, patterns)
- **Files**: Backend validation services, frontend validation UI

### Phase 8: Individual/Instance Management (High Priority - Post-MVP)

#### 8.1 Individuals Workbench
- **Action**: Create dedicated interface for managing ontology individuals
- **Challenge**: Handle hundreds of requirement-extracted individuals efficiently
- **Implementation Options**:
  - **Option A**: Extend ontology tree with grouped individuals
  - **Option B**: Separate individuals tab with table/search interface (RECOMMENDED)
  - **Option C**: Hybrid approach with tree summary and detailed table
- **Files**: New individuals workbench tab

#### 8.2 Individual Management Features
- **Action**: Comprehensive individual lifecycle management
- **Implementation**:
  - Table view with sorting, filtering, pagination
  - Full-text search across individual properties
  - Bulk operations (validate, export, classify, delete)
  - Individual-requirement traceability
  - Confidence scoring and review workflows
- **Files**: Individuals management system

#### 8.3 LLM-Generated Individual Processing
- **Action**: Handle LLM-extracted requirement individuals
- **Implementation**:
  - Batch import of LLM-generated individuals
  - Confidence-based review workflows
  - Automatic class assignment and validation
  - Component/Interface/Process/Function generation from requirements
- **Files**: LLM integration services

### Phase 9: Digital Assistant System (DAS) Integration (Medium Priority - Post-MVP)

#### 9.1 DAS-Ontology API Design
- **Action**: Create API endpoints for DAS to manage ontology objects
- **Implementation**:
  - `POST /api/das/ontology/create-class`
  - `POST /api/das/ontology/create-individual`
  - `POST /api/das/ontology/validate`
  - `GET /api/das/ontology/query`
- **Files**: `backend/api/das_ontology.py`

#### 9.2 DAS Knowledge Base for API Instructions
- **Action**: Create comprehensive API knowledge base in Qdrant
- **Implementation**:
  - API documentation with examples in Qdrant
  - Ontology operation patterns and best practices
  - Error handling and troubleshooting guides
  - Integration with RAG system for API guidance
- **Files**: DAS knowledge base population scripts

#### 9.3 RAG Integration for Ontology Operations
- **Action**: Enable RAG system to detect and handle ontology requests
- **Implementation**:
  - Query classification for ontology operations
  - Context retrieval from API knowledge base
  - Action guidance with executable code examples
  - End-to-end requirement-to-individual workflows
- **Files**: RAG system ontology integration

### Phase 10: Advanced Features (Low Priority)

#### 10.1 Ontology Versioning
- **Action**: Implement proper ontology versioning
- **Implementation**:
  - Version IRIs and tracking
  - Change history and diff
  - Rollback capabilities
- **Files**: Version management system

#### 10.2 Ontology Dependencies
- **Action**: Manage ontology import dependencies
- **Implementation**:
  - Dependency graph visualization
  - Circular dependency detection
  - Automatic dependency updates
- **Files**: Dependency management system

#### 10.3 Ontology Publishing
- **Action**: Publish ontologies to external endpoints
- **Implementation**:
  - Public ontology endpoints
  - Content negotiation
  - API documentation generation
- **Files**: Publishing system

## Detailed Implementation Actions

### Immediate Actions (This Session)

#### 1. Update Ontology URI Generation
```python
# In backend/main.py create_ontology function
# Replace current URI generation with:
project_namespace = get_project_namespace(project)
if project_namespace:
    graph_iri = f"{settings.installation_base_uri}/{project_namespace['path']}/{project}/{name}"
else:
    # Fallback for projects without namespace
    graph_iri = f"{settings.installation_base_uri}/projects/{project}/{name}"
```

#### 2. Add Project Namespace Display
```javascript
// In frontend/app.html showCreateOntologyModal function
// Update namespace display to show full organizational path
async function loadCurrentProjectNamespace(displayElement) {
  const currentProjectId = localStorage.getItem('active_project_id');
  const response = await fetch(`/api/projects/${currentProjectId}/namespace`);
  const namespaceData = await response.json();
  displayElement.textContent = namespaceData.namespace_path || 'No namespace assigned';
}
```

#### 3. Update URI Preview
```javascript
// Add real-time URI preview in ontology creation modal
function updateOntologyUriPreview() {
  const name = document.getElementById('simpleOntologyName').value;
  const namespaceDisplay = document.getElementById('modalNamespaceDisplay').textContent;
  const projectId = localStorage.getItem('active_project_id');
  
  if (name && namespaceDisplay && projectId) {
    const uri = `http://${namespaceDisplay}/${projectId}/ontologies/${name}`;
    document.getElementById('ontologyUriPreview').textContent = uri;
  }
}
```

### Next Session Actions

#### 1. Database Schema Updates
```sql
-- Add ontology metadata fields
ALTER TABLE public.ontologies_registry ADD COLUMN IF NOT EXISTS domain VARCHAR(255);
ALTER TABLE public.ontologies_registry ADD COLUMN IF NOT EXISTS version VARCHAR(50) DEFAULT '1.0.0';
ALTER TABLE public.ontologies_registry ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'active';
ALTER TABLE public.ontologies_registry ADD COLUMN IF NOT EXISTS description TEXT;
```

#### 2. Ontology CRUD Endpoints
```python
# Add to backend/main.py
@app.get("/api/ontologies/{ontology_id}")
async def get_ontology(ontology_id: str, user=Depends(get_user)):
    """Get individual ontology details"""

@app.put("/api/ontologies/{ontology_id}")
async def update_ontology(ontology_id: str, body: Dict, user=Depends(get_user)):
    """Update ontology metadata"""

@app.delete("/api/ontologies/{ontology_id}")
async def delete_ontology(ontology_id: str, user=Depends(get_user)):
    """Delete ontology"""
```

#### 3. External Ontology Management
```python
# New file: backend/api/external_ontologies.py
@router.get("/api/admin/external-ontologies")
async def list_external_ontologies(admin_user=Depends(get_admin_user)):
    """List all external/reference ontologies"""

@router.post("/api/admin/external-ontologies")
async def add_external_ontology(body: Dict, admin_user=Depends(get_admin_user)):
    """Add new external ontology to registry"""
```

## Best Practices Implementation

### 1. Namespace Management
- **Principle**: All ontologies inherit their project's namespace
- **Implementation**: Automatic namespace inheritance, no manual selection
- **Validation**: Ensure project has valid namespace before ontology creation

### 2. External Ontology Imports
- **Principle**: Controlled imports with validation and conflict detection
- **Implementation**: 
  - Admin-managed external ontology registry
  - Import validation before adding to projects
  - Namespace conflict detection
  - **IMMUTABILITY**: Imported ontologies are read-only
- **Validation**: Check for naming conflicts, circular dependencies

### 2.1 Import Immutability Rules
- **Principle**: Imported ontologies cannot be modified by importers
- **Implementation**:
  - Read-only access to imported ontology content
  - Visual positioning only for Cytoscape nodes
  - Show/hide controls for nested imports
  - Auto-linking of equivalent classes
- **Rationale**: Prevents corruption of shared reference ontologies

### 3. URI Consistency
- **Principle**: All URIs follow organizational hierarchy
- **Implementation**: 
  - Project URIs: `http://{org}/{namespace}/{project-id}/ontologies/{name}`
  - External URIs: Preserved as-is for imports
  - System URIs: `http://{org}/admin/ontologies/{name}`

### 4. Metadata Completeness
- **Principle**: Rich metadata for discoverability and management
- **Implementation**:
  - Domain association from project
  - Version tracking and history
  - Status management (active, deprecated, archived)
  - Description and documentation

## Current Discussion Points (2025-01-27)

### Reference Ontology Management
- **Status**: ✅ **COMPLETED** - Admin can mark ontologies as reference for ODRAS users
- **Implementation**: Admin workbench with reference ontology toggle
- **Next Steps**: Focus on import capabilities rather than editing reference ontologies

### Import Capabilities Priority
- **Cross-Project Imports**: Users need to import ontologies from other projects
- **Reference Ontology Imports**: Users need to import admin-managed reference ontologies
- **Nested Imports**: Support for ontologies that import other ontologies
- **Visualization**: Show imported ontologies in Cytoscape canvas with proper styling

### Import Constraints and Rules
- **IMMUTABILITY**: Imported ontologies are read-only - users cannot edit their content
- **Visual Positioning Only**: Users can only adjust Cytoscape node positions for imported elements
- **Nested Import Controls**: Show/hide nested imports with toggle controls
- **Auto-linking**: Automatically link equivalent classes between different imports
- **Namespace Preservation**: Imported ontologies maintain their original namespaces

### Nice to Have: Collapsible Import Visualization
- **Collapsed View**: Imported ontologies appear as single round entities showing all equivalent relationships
- **Expandable Detail**: Users can expand imported ontologies to view their internal structure and details
- **Clean Canvas**: Keeps the main workspace uncluttered while preserving full access to imported content
- **Progressive Disclosure**: Users see high-level relationships first, then drill down as needed

### Data Object Management
- **Status**: 🔄 **PLANNING** - Identified as confusing area requiring multiple iterations
- **Approach**: Add to work list and iterate to get it right
- **Focus**: Clear patterns for modeling and managing data objects in ontologies

### User Sharing
- **Status**: 📋 **PLANNED** - Enable users to share ontologies with each other
- **Priority**: Medium - Important for collaboration but not critical for MVP

## Success Criteria

### Phase 1 Success
- [ ] All new ontologies use project namespace URIs
- [ ] Existing ontologies migrated to new URI structure
- [ ] Frontend displays proper organizational URIs
- [ ] URI generation is consistent across the system

### Phase 2 Success
- [ ] Full ontology CRUD operations implemented
- [ ] Rich metadata support added
- [ ] Ontology actions menu functional
- [ ] Version management working

### Phase 3 Success (Import & Sharing)
- [ ] Cross-project ontology import functionality
- [ ] Reference ontology import from admin-managed library
- [ ] Nested import support with dependency resolution
- [ ] Import visualization in Cytoscape canvas
- [ ] User-to-user ontology sharing capabilities
- [ ] **Nice to Have**: Collapsible import visualization (single entities with expand/collapse)

### Phase 4 Success (Data Objects)
- [ ] Data object modeling framework established
- [ ] Clear patterns for data object relationships
- [ ] Data object visualization in Cytoscape
- [ ] Data object lifecycle management

### Long-term Success
- [ ] Complete ontology lifecycle management
- [ ] Seamless external ontology integration
- [ ] Professional ontology publishing capabilities
- [ ] Full compliance with organizational URI standards
- [ ] Robust data object management system

## Risk Assessment

### High Risk
- **URI Migration**: Changing existing ontology URIs may break references
- **Fuseki Integration**: Named graph updates require careful coordination

### Medium Risk
- **External Ontology Conflicts**: Import validation complexity
- **User Experience**: Changes to familiar interfaces

### Low Risk
- **Metadata Addition**: Non-breaking schema changes
- **Admin Interface**: New functionality, no existing dependencies

## Next Steps

1. **Immediate**: Update ontology URI generation to use project namespaces
2. **This Session**: Implement project namespace display in creation modal
3. **Next Session**: Add ontology metadata fields and CRUD operations
4. **Priority Focus**: Implement cross-project and reference ontology import capabilities
5. **Iterative Development**: Data object management - plan, implement, test, iterate
6. **Future**: User sharing and advanced features

---

**Priority**: High - This aligns the ontology workbench with our organizational URI structure and enables proper namespace management.

**Estimated Effort**: 
- Phase 1: 2-3 hours
- Phase 2: 4-6 hours  
- Phase 3 (Import & Sharing): 8-12 hours
- Phase 4 (Data Objects): 6-10 hours (iterative)
- Phase 5 (External Management): 6-8 hours
- Phase 6 (Advanced Features): 8-12 hours

**Dependencies**: Requires completed namespace and project management systems (✅ Done)

**Key Focus Areas**:
- **Import Capabilities**: Critical for user productivity and ontology reuse
- **Data Object Management**: Requires careful planning and iteration to get right
- **Reference Ontology Integration**: Leverage existing admin capabilities
