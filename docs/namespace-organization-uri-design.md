# Namespace and Organization URI Design Document

**Version**: 1.0  
**Date**: 2025-09-05  
**Status**: Implementation Planning  

## Executive Summary

This document defines the architectural approach for namespace management, organizational URI structures, and resource organization within ODRAS. The design establishes a clear hierarchy that aligns with real organizational structures while maintaining semantic web best practices.

## Background

ODRAS initially used a flat `http://odras.local` URI structure that didn't reflect organizational boundaries or enable proper multi-tenant deployment. Through analysis and implementation, we've evolved to a hierarchical organizational structure that supports:

- Multi-organizational deployment
- Clear ownership boundaries
- Semantic consistency
- Scalable resource management

## Core Architecture

### Organizational Hierarchy

```
Organization (e.g., "dod", "boeing", "lockheed")
├── Namespace (organizational scope: "dod/usn/adt")
│   ├── Project (work unit with domain classification)
│   │   ├── Ontologies (knowledge models)
│   │   ├── Files (project documents)
│   │   ├── Knowledge Assets (analysis outputs)
│   │   └── Discussions (project communications)
│   └── Project (another work unit)
└── Admin/Shared Resources (system-level)
```

### URI Structure

#### Project-Scoped Resources
```
http://{organization}/{namespace-path}/{project-id}/{resource-type}/{resource-name}

Examples:
- http://dod/usn/adt/a1b2c3d4-5678-9012-3456-789abcdef012/ontologies/flight-control/#RadarSystem
- http://dod/usn/adt/a1b2c3d4-5678-9012-3456-789abcdef012/files/requirements-doc.pdf
- http://dod/usn/adt/a1b2c3d4-5678-9012-3456-789abcdef012/knowledge/threat-analysis
```

#### System-Level Resources
```
http://{organization}/admin/{resource-type}/{resource-name}
http://{organization}/shared/{resource-type}/{resource-name}

Examples:
- http://dod/admin/configs/fuseki-settings
- http://dod/shared/libraries/common-vocabularies
- http://dod/admin/files/installation-guide
```

## Key Design Decisions

### 1. Atomic Prefixes Only
- **Decision**: Use single-word prefixes (e.g., "dod", "usn", "adt") that can be composed
- **Rationale**: Flexibility, reusability, and clear component management
- **Implementation**: Prefix registry with validation `^[a-z][a-z0-9]{1,19}$`

### 2. Namespace Composition
- **Decision**: Namespaces are composed from ordered atomic prefixes
- **Example**: Select ["dod", "usn", "adt"] → generates "dod/usn/adt"
- **Benefits**: Flexible organizational structure, controlled vocabulary

### 3. Project ID in URIs
- **Decision**: Use project UUID in URIs, not project names
- **Rationale**: 
  - Immutable identifiers prevent URI breakage
  - No naming conflicts or special character issues
  - Project names can change without breaking semantic relationships
- **Human Readability**: Handled through metadata (rdfs:label, project descriptions)

### 4. Domain as Metadata
- **Decision**: Domains are project classification, not URI components
- **Examples**: "avionics", "mission-planning", "systems-engineering"
- **Usage**: Filtering, organization, access control - not URI structure

### 5. Namespace Inheritance
- **Decision**: All project resources inherit the project's namespace
- **Implementation**: No namespace selection at ontology/file level
- **Benefits**: Consistency, simplicity, organizational alignment

## Implementation Phases

### Phase 1: Core Infrastructure ✅ (Completed)
- [x] Prefix management system with CRUD operations
- [x] Namespace creation with atomic prefix composition
- [x] Project creation with namespace selection
- [x] Basic URI generation

### Phase 2: Resource Integration ✅ (Completed)
- [x] Remove namespace selection from ontology creation
- [x] Implement domain management (admin-only)
- [x] Update all resource URIs to use project-namespace structure
- [x] Add domain selection to project creation
- [x] Add project information page with metadata display
- [x] Add project treeview click handler for navigation
- [x] Implement project CRUD operations (GET, PUT, DELETE)
- [x] Add project actions (edit, archive, export, duplicate, delete)

### Phase 3: System Resources
- [ ] Migrate system files to organizational URI structure
- [ ] Implement admin resource management
- [ ] Add shared resource capabilities
- [ ] Update installation configuration for organization-wide settings

### Phase 4: Advanced Features
- [ ] Cross-project reference management
- [ ] Versioning strategy implementation
- [ ] Access control by namespace/domain/project
- [ ] Federation capabilities for multi-organizational sharing

## Current Implementation Status

### Completed Components
1. **Prefix Registry**: Atomic prefixes with status management and CRUD operations
2. **Namespace Management**: Composition from ordered prefixes with full CRUD
3. **Project Creation**: With namespace and domain selection dropdowns
4. **Database Schema**: Projects table with namespace_id and domain fields
5. **Public APIs**: Released namespaces and active domains accessible to users
6. **Domain Management**: Full CRUD operations for domains (admin-only)
7. **Project Information Page**: Complete metadata display with modern UI
8. **Project Treeview Navigation**: Click handlers for project info access
9. **Project CRUD Operations**: Full project management (GET, PUT, DELETE)
10. **Project Actions**: Edit, archive, export, duplicate, and delete functionality
11. **URL-based State Management**: Persistent project and workbench selection
12. **User Experience Enhancements**: Clean icons, proper error handling, responsive design

### Resolved Issues
1. ✅ **Mixed Systems**: Unified project management with namespace integration
2. ✅ **URI Inconsistency**: All project resources use project-namespace structure
3. ✅ **Missing Domain Management**: Full domain CRUD with admin interface
4. ✅ **Project Information Display**: Complete project metadata page
5. ✅ **Navigation Issues**: Treeview click handlers and URL state management

## Technical Specifications

### Database Schema

#### Namespaces
```sql
namespace_registry (
  id UUID PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  path VARCHAR(255) NOT NULL UNIQUE,
  prefix VARCHAR(50) NOT NULL,
  status VARCHAR(50) CHECK (status IN ('draft', 'released', 'deprecated')),
  owners TEXT[],
  description TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)
```

#### Projects
```sql
projects (
  project_id UUID PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  namespace_id UUID REFERENCES namespace_registry(id),
  domain VARCHAR(255), -- ✅ Implemented
  created_by UUID,
  status VARCHAR(50) DEFAULT 'active',
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  is_active BOOLEAN DEFAULT TRUE,
  UNIQUE(namespace_id, name)
)
```

#### Prefixes
```sql
prefix_registry (
  id UUID PRIMARY KEY,
  prefix VARCHAR(50) NOT NULL UNIQUE,
  description TEXT NOT NULL,
  owner VARCHAR(255),
  status VARCHAR(50) CHECK (status IN ('active', 'deprecated', 'archived')),
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)
```

## API Endpoints

### Public Endpoints (No Auth Required)
- `GET /api/namespaces/released` - List released namespaces for project creation

### Admin Endpoints (Admin Auth Required)  
- `GET/POST/PUT/DELETE /api/admin/namespaces/` - Namespace CRUD
- `GET/POST/PUT/DELETE /api/admin/prefixes/` - Prefix CRUD
- `GET/POST/PUT/DELETE /api/admin/domains/` - Domain CRUD ✅ Implemented

### User Endpoints (User Auth Required)
- `GET/POST/PUT/DELETE /api/projects/` - Project management ✅ Full CRUD
- `GET /api/projects/{id}/namespace` - Project namespace info ✅ Implemented
- `GET /api/domains/active` - List active domains for project creation ✅ Implemented

## Risk Assessment

### Low Risk
- **Prefix management**: Well-defined, atomic approach
- **Namespace composition**: Flexible and validated

### Medium Risk  
- **Project ID in URIs**: Less human-readable, requires good tooling
- **Domain integration**: New concept, needs user adoption

### High Risk
- **URI migration**: Changing existing URIs breaks semantic relationships
- **System integration**: Ensuring all components use new URI patterns

## Success Criteria

### Phase 1 Success ✅ (Achieved)
- [x] Projects created with namespace association
- [x] Ontologies inherit project namespace automatically  
- [x] No namespace selection confusion
- [x] Clean URI generation

### Phase 2 Success ✅ (Achieved)
- [x] Domain management fully implemented
- [x] Project information page with complete metadata
- [x] Project treeview navigation working
- [x] Project CRUD operations functional
- [x] URL-based state management implemented
- [x] User experience enhancements completed

### Long-term Success
- [ ] All resources follow organizational URI patterns
- [ ] Cross-organizational federation capabilities
- [ ] Intuitive user experience for resource discovery
- [ ] Scalable multi-tenant deployment

## Todo List

### Immediate Implementation ✅ (Completed)
- [x] **Remove namespace selection from ontology creation**
- [x] **Add domain management to admin panel**
- [x] **Add domain selection to project creation**
- [x] **Update ontology URI generation to use project namespace**
- [x] **Test complete workflow: Namespace → Project → Domain → Ontology**
- [x] **Add project information page with metadata display**
- [x] **Implement project treeview click navigation**
- [x] **Add project CRUD operations (GET, PUT, DELETE)**
- [x] **Implement project actions (edit, archive, export, duplicate, delete)**
- [x] **Add URL-based state management for project/workbench persistence**
- [x] **Enhance user experience with clean icons and proper error handling**

### Next Session
- [ ] **Migrate existing ontologies to new URI structure**
- [ ] **Update file management to use project URIs**
- [ ] **Update knowledge asset URIs**
- [ ] **Add cross-project reference validation**

### Future Iterations
- [ ] **Implement versioning strategy**
- [ ] **Add access control by domain/namespace**
- [ ] **Build federation capabilities**
- [ ] **Add semantic search across namespaces**
- [ ] **Implement shared/core ontology support**

## Decision Log

| Date | Decision | Rationale | Status |
|------|----------|-----------|--------|
| 2025-09-05 | Use atomic prefixes only | Flexibility and reusability | ✅ Implemented |
| 2025-09-05 | Project ID in URIs | Immutable identifiers | ✅ Implemented |
| 2025-09-05 | Domain as metadata only | Organizational flexibility | ✅ Implemented |
| 2025-09-05 | Namespace inheritance for all project resources | Consistency | ✅ Implemented |
| 2025-09-05 | Project information page | User experience and metadata display | ✅ Implemented |
| 2025-09-05 | Project treeview navigation | Intuitive project access | ✅ Implemented |
| 2025-09-05 | URL-based state management | Persistent navigation state | ✅ Implemented |

---

## Recent Implementations (Session Updates)

### Project Information Page
- **Complete metadata display** with modern card-based layout
- **Username display** instead of UUIDs for "Created By" field
- **Enhanced typography** with proper font sizing and monospace for Project ID
- **Clean SVG icons** replacing colorful emojis for professional appearance
- **Responsive design** with proper spacing and theme integration

### Project Treeview Navigation
- **Click handler** for project info node to open project information page
- **Automatic workbench switching** to project view
- **URL state management** for persistent navigation
- **Seamless integration** with existing context menu functionality

### Domain Management System
- **Full CRUD operations** for domains (admin-only)
- **Status management** (active, deprecated, archived)
- **Edit functionality** with proper form validation
- **Delete confirmation** with safety checks
- **Integration** with project creation and editing

### Project CRUD Operations
- **GET endpoint** for individual project details
- **PUT endpoint** for project updates
- **DELETE endpoint** for project removal
- **Project actions** (edit, archive, export, duplicate, delete)
- **Proper error handling** and user feedback

### User Experience Enhancements
- **URL-based state management** for project and workbench persistence
- **Clean SVG icons** throughout the interface
- **Improved modal styling** with proper button spacing
- **Enhanced error handling** with user-friendly messages
- **Responsive design** improvements

**Next Steps**: Phase 2 implementation is complete. Ready to begin Phase 3: System Resources migration and advanced features.
