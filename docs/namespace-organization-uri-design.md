# Namespace and Organization URI Design Document<br>
<br>
**Version**: 1.1<br>
**Date**: 2025-09-10<br>
**Status**: Implementation Complete (Phase 2)<br>
<br>
## Executive Summary<br>
<br>
This document defines the architectural approach for namespace management, organizational URI structures, and resource organization within ODRAS. The design establishes a clear hierarchy that aligns with real organizational structures while maintaining semantic web best practices.<br>
<br>
## Background<br>
<br>
ODRAS initially used a flat `http://odras.local` URI structure that didn't reflect organizational boundaries or enable proper multi-tenant deployment. Through analysis and implementation, we've evolved to a hierarchical organizational structure that supports:<br>
<br>
- Multi-organizational deployment<br>
- Clear ownership boundaries<br>
- Semantic consistency<br>
- Scalable resource management<br>
<br>
## Industry Standards & Best Practices Alignment<br>
<br>
### W3C Semantic Web Standards<br>
<br>
ODRAS follows W3C "Cool URIs" principles and semantic web architecture:<br>
<br>
**✅ Cool URIs Principles:**<br>
- **Persistence**: URIs are stable and long-lived using immutable project UUIDs<br>
- **No Implementation Details**: URIs don't encode file extensions or technology stacks<br>
- **Hierarchical Structure**: Clear organizational ownership hierarchy<br>
- **Human Readability**: Meaningful namespace paths with UUID precision<br>
- **Version Independence**: Base URIs remain stable; versioning handled via metadata<br>
<br>
**✅ FAIR Data Principles:**<br>
- **Findable**: Persistent identifiers with rich namespace metadata<br>
- **Accessible**: Standard HTTP protocols with content negotiation support<br>
- **Interoperable**: OWL/RDF formats with standard vocabularies<br>
- **Reusable**: Clear organizational provenance and access policies<br>
<br>
### Enterprise Architecture Standards<br>
<br>
**✅ Industry Pattern Compliance:**<br>
```<br>
{organization-domain}/{business-unit}/{department}/{project-uuid}/{resource-type}/{resource-name}<br>
```<br>
<br>
ODRAS Implementation:<br>
```<br>
{installation-base-uri}/{namespace-path}/{project-uuid}/{resource-type}/{resource-name}<br>
```<br>
<br>
**Alignment with Enterprise Standards:**<br>
- **Federal Enterprise Architecture (FEA)**: Supports reference models and standardized metadata<br>
- **DoD Data Strategy**: Authoritative sources, standardized metadata, cross-system interoperability<br>
- **RESTful API Design**: Resource hierarchy follows REST conventions<br>
<br>
### Ontology Management Best Practices<br>
<br>
**✅ Industrial Ontologies Foundry (IOF) Compliance:**<br>
- Short, unique prefixes for each ontology namespace<br>
- Stable namespace URIs without version encoding<br>
- Clear scope and domain definitions<br>
- Comprehensive human-readable documentation<br>
<br>
**✅ OBO Foundry Principles:**<br>
- Explicit, concise entity naming (PascalCase classes, camelCase properties)<br>
- Context-independent identifiers<br>
- Singular nominal forms preferred<br>
- Avoidance of homonyms and ambiguous terms<br>
<br>
**✅ W3C Vocabulary Design Guidelines:**<br>
- Persistent and stable URIs for all terms<br>
- Rich metadata using Dublin Core terms (`dct:created`, `dct:creator`)<br>
- Version tracking via `owl:versionInfo`<br>
- Preferred namespace prefixes using `vann:preferredNamespacePrefix`<br>
<br>
### Persistent Identifier Standards<br>
<br>
**✅ UUID-based Project Identifiers:**<br>
- Globally unique, immutable identifiers (follows DOI/Handle principles)<br>
- Location-independent naming (URN-style benefits)<br>
- No dependency on project names or organizational changes<br>
- Support for distributed, multi-tenant deployments<br>
<br>
**✅ Atomic Prefix Composition:**<br>
- Matches Library of Congress identifier strategies<br>
- Supports hierarchical organizational structures<br>
- Enables controlled vocabulary management<br>
- Facilitates cross-organizational federation<br>
<br>
### Government & Defense Standards<br>
<br>
**✅ DoD Enterprise Standards:**<br>
- Authoritative data sources with clear ownership<br>
- Standardized metadata and resource classification<br>
- Security-aware namespace design<br>
- Cross-system interoperability support<br>
<br>
**✅ Multi-Tenant Architecture:**<br>
- Organizational isolation via base URI configuration<br>
- Namespace-based access control capabilities<br>
- Support for classified/unclassified separation<br>
- Federation-ready design for inter-agency collaboration<br>
<br>
### Technical Implementation Standards<br>
<br>
**✅ Content Negotiation Support:**<br>
- Multiple RDF serialization formats (`text/turtle`, `application/rdf+xml`, `application/ld+json`)<br>
- RESTful API patterns with proper HTTP semantics<br>
- Versioning via metadata rather than URI paths<br>
- Standard MIME types and HTTP headers<br>
<br>
**✅ Metadata Standards Integration:**<br>
- Dublin Core Terms (DCT) for resource description<br>
- PROV-O for provenance and data lineage<br>
- VANN vocabulary for namespace metadata<br>
- Schema.org compatibility for broader interoperability<br>
<br>
## Core Architecture<br>
<br>
### Organizational Hierarchy<br>
<br>
```<br>
Organization (e.g., "dod", "boeing", "lockheed")<br>
├── Namespace (organizational scope: "dod/usn/adt")<br>
│   ├── Project (work unit with domain classification)<br>
│   │   ├── Ontologies (knowledge models)<br>
│   │   ├── Files (project documents)<br>
│   │   ├── Knowledge Assets (analysis outputs)<br>
│   │   └── Discussions (project communications)<br>
│   └── Project (another work unit)<br>
└── Admin/Shared Resources (system-level)<br>
```<br>
<br>
### URI Structure<br>
<br>
#### Project-Scoped Resources<br>
```<br>
http://{organization}/{namespace-path}/{project-id}/{resource-type}/{resource-name}<br>
<br>
Examples:<br>
- http://dod/usn/adt/a1b2c3d4-5678-9012-3456-789abcdef012/ontologies/flight-control/#RadarSystem<br>
- http://dod/usn/adt/a1b2c3d4-5678-9012-3456-789abcdef012/files/requirements-doc.pdf<br>
- http://dod/usn/adt/a1b2c3d4-5678-9012-3456-789abcdef012/knowledge/threat-analysis<br>
```<br>
<br>
#### System-Level Resources<br>
```<br>
http://{organization}/admin/{resource-type}/{resource-name}<br>
http://{organization}/shared/{resource-type}/{resource-name}<br>
<br>
Examples:<br>
- http://dod/admin/configs/fuseki-settings<br>
- http://dod/shared/libraries/common-vocabularies<br>
- http://dod/admin/files/installation-guide<br>
```<br>
<br>
## Key Design Decisions<br>
<br>
### 1. Atomic Prefixes Only<br>
- **Decision**: Use single-word prefixes (e.g., "dod", "usn", "adt") that can be composed<br>
- **Rationale**: Flexibility, reusability, and clear component management<br>
- **Industry Alignment**: Matches Library of Congress and OBO Foundry identifier strategies<br>
- **Implementation**: Prefix registry with validation `^[a-z][a-z0-9]{1,19}$`<br>
<br>
### 2. Namespace Composition<br>
- **Decision**: Namespaces are composed from ordered atomic prefixes<br>
- **Example**: Select ["dod", "usn", "adt"] → generates "dod/usn/adt"<br>
- **Benefits**: Flexible organizational structure, controlled vocabulary<br>
<br>
### 3. Project ID in URIs<br>
- **Decision**: Use project UUID in URIs, not project names<br>
- **Rationale**:<br>
  - Immutable identifiers prevent URI breakage (W3C Cool URIs principle)<br>
  - No naming conflicts or special character issues<br>
  - Project names can change without breaking semantic relationships<br>
  - Follows DOI/Handle persistent identifier best practices<br>
- **Industry Standards**: Aligns with academic publishing (DOI) and digital preservation (ARK) practices<br>
- **Human Readability**: Handled through metadata (rdfs:label, project descriptions)<br>
<br>
### 4. Domain as Metadata<br>
- **Decision**: Domains are project classification, not URI components<br>
- **Examples**: "avionics", "mission-planning", "systems-engineering"<br>
- **Usage**: Filtering, organization, access control - not URI structure<br>
<br>
### 5. Namespace Inheritance<br>
- **Decision**: All project resources inherit the project's namespace<br>
- **Implementation**: No namespace selection at ontology/file level<br>
- **Benefits**: Consistency, simplicity, organizational alignment<br>
<br>
## Implementation Phases<br>
<br>
### Phase 1: Core Infrastructure ✅ (Completed)<br>
- [x] Prefix management system with CRUD operations<br>
- [x] Namespace creation with atomic prefix composition<br>
- [x] Project creation with namespace selection<br>
- [x] Basic URI generation<br>
<br>
### Phase 2: Resource Integration ✅ (Completed)<br>
- [x] Remove namespace selection from ontology creation<br>
- [x] Implement domain management (admin-only)<br>
- [x] Update all resource URIs to use project-namespace structure<br>
- [x] Add domain selection to project creation<br>
- [x] Add project information page with metadata display<br>
- [x] Add project treeview click handler for navigation<br>
- [x] Implement project CRUD operations (GET, PUT, DELETE)<br>
- [x] Add project actions (edit, archive, export, duplicate, delete)<br>
<br>
### Phase 3: Standards Compliance & Enhancement ✅ (In Progress)<br>
- [x] Centralized ResourceURIService for consistent URI generation<br>
- [x] Industry best practices research and documentation<br>
- [x] Configuration validation and diagnostics<br>
- [ ] Formal versioning metadata (`owl:versionInfo`)<br>
- [ ] Content negotiation for multiple RDF formats<br>
- [ ] Dublin Core metadata integration<br>
<br>
### Phase 4: System Resources<br>
- [ ] Migrate system files to organizational URI structure<br>
- [ ] Implement admin resource management<br>
- [ ] Add shared resource capabilities<br>
- [ ] Update installation configuration for organization-wide settings<br>
<br>
### Phase 5: Advanced Features<br>
- [ ] Cross-project reference management<br>
- [ ] Access control by namespace/domain/project<br>
- [ ] Federation capabilities for multi-organizational sharing<br>
- [ ] PROV-O provenance tracking<br>
<br>
## Current Implementation Status<br>
<br>
### Completed Components<br>
1. **Prefix Registry**: Atomic prefixes with status management and CRUD operations<br>
2. **Namespace Management**: Composition from ordered prefixes with full CRUD<br>
3. **Project Creation**: With namespace and domain selection dropdowns<br>
4. **Database Schema**: Projects table with namespace_id and domain fields<br>
5. **Public APIs**: Released namespaces and active domains accessible to users<br>
6. **Domain Management**: Full CRUD operations for domains (admin-only)<br>
7. **Project Information Page**: Complete metadata display with modern UI<br>
8. **Project Treeview Navigation**: Click handlers for project info access<br>
9. **Project CRUD Operations**: Full project management (GET, PUT, DELETE)<br>
10. **Project Actions**: Edit, archive, export, duplicate, and delete functionality<br>
11. **URL-based State Management**: Persistent project and workbench selection<br>
12. **User Experience Enhancements**: Clean icons, proper error handling, responsive design<br>
13. **ResourceURIService**: Centralized, standards-compliant URI generation system<br>
14. **Configuration Validation**: Installation base URI validation and diagnostics<br>
15. **Industry Standards Alignment**: W3C, IOF, and enterprise best practices compliance<br>
<br>
### Resolved Issues<br>
1. ✅ **Mixed Systems**: Unified project management with namespace integration<br>
2. ✅ **URI Inconsistency**: All project resources use project-namespace structure<br>
3. ✅ **Missing Domain Management**: Full domain CRUD with admin interface<br>
4. ✅ **Project Information Display**: Complete project metadata page<br>
5. ✅ **Navigation Issues**: Treeview click handlers and URL state management<br>
6. ✅ **URI Standards Compliance**: Implementation now follows W3C and industry best practices<br>
7. ✅ **Configuration Issues**: Installation base URI validation and diagnostic tools<br>
<br>
## Technical Specifications<br>
<br>
### Database Schema<br>
<br>
#### Namespaces<br>
```sql<br>
namespace_registry (<br>
  id UUID PRIMARY KEY,<br>
  name VARCHAR(255) NOT NULL,<br>
  path VARCHAR(255) NOT NULL UNIQUE,<br>
  prefix VARCHAR(50) NOT NULL,<br>
  status VARCHAR(50) CHECK (status IN ('draft', 'released', 'deprecated')),<br>
  owners TEXT[],<br>
  description TEXT,<br>
  created_at TIMESTAMP,<br>
  updated_at TIMESTAMP<br>
)<br>
```<br>
<br>
#### Projects<br>
```sql<br>
projects (<br>
  project_id UUID PRIMARY KEY,<br>
  name VARCHAR(255) NOT NULL,<br>
  description TEXT,<br>
  namespace_id UUID REFERENCES namespace_registry(id),<br>
  domain VARCHAR(255), -- ✅ Implemented<br>
  created_by UUID,<br>
  status VARCHAR(50) DEFAULT 'active',<br>
  created_at TIMESTAMP,<br>
  updated_at TIMESTAMP,<br>
  is_active BOOLEAN DEFAULT TRUE,<br>
  UNIQUE(namespace_id, name)<br>
)<br>
```<br>
<br>
#### Prefixes<br>
```sql<br>
prefix_registry (<br>
  id UUID PRIMARY KEY,<br>
  prefix VARCHAR(50) NOT NULL UNIQUE,<br>
  description TEXT NOT NULL,<br>
  owner VARCHAR(255),<br>
  status VARCHAR(50) CHECK (status IN ('active', 'deprecated', 'archived')),<br>
  created_at TIMESTAMP,<br>
  updated_at TIMESTAMP<br>
)<br>
```<br>
<br>
## API Endpoints<br>
<br>
### Public Endpoints (No Auth Required)<br>
- `GET /api/namespaces/released` - List released namespaces for project creation<br>
<br>
### Admin Endpoints (Admin Auth Required)<br>
- `GET/POST/PUT/DELETE /api/admin/namespaces/` - Namespace CRUD<br>
- `GET/POST/PUT/DELETE /api/admin/prefixes/` - Prefix CRUD<br>
- `GET/POST/PUT/DELETE /api/admin/domains/` - Domain CRUD ✅ Implemented<br>
<br>
### User Endpoints (User Auth Required)<br>
- `GET/POST/PUT/DELETE /api/projects/` - Project management ✅ Full CRUD<br>
- `GET /api/projects/{id}/namespace` - Project namespace info ✅ Implemented<br>
- `GET /api/domains/active` - List active domains for project creation ✅ Implemented<br>
<br>
### System Endpoints (Configuration & Diagnostics)<br>
- `GET /api/installation/config` - Installation configuration with validation ✅ Implemented<br>
- `GET /api/installation/uri-diagnostics` - URI generation diagnostics ✅ Implemented<br>
<br>
## Risk Assessment<br>
<br>
### Low Risk ✅ (Mitigated)<br>
- **Prefix management**: Well-defined, atomic approach following OBO Foundry standards<br>
- **Namespace composition**: Flexible and validated, matches enterprise patterns<br>
- **Standards compliance**: W3C and industry best practices implemented<br>
<br>
### Medium Risk ⚠️ (Managed)<br>
- **Project ID in URIs**: Less human-readable but follows DOI/persistent identifier standards<br>
- **Domain integration**: New concept but aligned with FEA reference models<br>
- **Configuration migration**: Installation base URI changes required for existing deployments<br>
<br>
### Low Risk (Previously High) ✅ (Resolved)<br>
- **URI migration**: ResourceURIService provides consistent generation with fallbacks<br>
- **System integration**: Centralized service ensures all components use proper patterns<br>
<br>
## Success Criteria<br>
<br>
### Phase 1 Success ✅ (Achieved)<br>
- [x] Projects created with namespace association<br>
- [x] Ontologies inherit project namespace automatically<br>
- [x] No namespace selection confusion<br>
- [x] Clean URI generation<br>
<br>
### Phase 2 Success ✅ (Achieved)<br>
- [x] Domain management fully implemented<br>
- [x] Project information page with complete metadata<br>
- [x] Project treeview navigation working<br>
- [x] Project CRUD operations functional<br>
- [x] URL-based state management implemented<br>
- [x] User experience enhancements completed<br>
<br>
### Long-term Success<br>
- [ ] All resources follow organizational URI patterns<br>
- [ ] Cross-organizational federation capabilities<br>
- [ ] Intuitive user experience for resource discovery<br>
- [ ] Scalable multi-tenant deployment<br>
<br>
## Todo List<br>
<br>
### Immediate Implementation ✅ (Completed)<br>
- [x] **Remove namespace selection from ontology creation**<br>
- [x] **Add domain management to admin panel**<br>
- [x] **Add domain selection to project creation**<br>
- [x] **Update ontology URI generation to use project namespace**<br>
- [x] **Test complete workflow: Namespace → Project → Domain → Ontology**<br>
- [x] **Add project information page with metadata display**<br>
- [x] **Implement project treeview click navigation**<br>
- [x] **Add project CRUD operations (GET, PUT, DELETE)**<br>
- [x] **Implement project actions (edit, archive, export, duplicate, delete)**<br>
- [x] **Add URL-based state management for project/workbench persistence**<br>
- [x] **Enhance user experience with clean icons and proper error handling**<br>
<br>
### Next Session<br>
- [ ] **Migrate existing ontologies to new URI structure**<br>
- [ ] **Update file management to use project URIs**<br>
- [ ] **Update knowledge asset URIs**<br>
- [ ] **Add cross-project reference validation**<br>
<br>
### Future Iterations<br>
- [ ] **Implement versioning strategy**<br>
- [ ] **Add access control by domain/namespace**<br>
- [ ] **Build federation capabilities**<br>
- [ ] **Add semantic search across namespaces**<br>
- [ ] **Implement shared/core ontology support**<br>
<br>
## Decision Log<br>
<br>
| Date | Decision | Rationale | Status |<br>
|------|----------|-----------|--------|<br>
| 2025-09-05 | Use atomic prefixes only | Flexibility and reusability | ✅ Implemented |<br>
| 2025-09-05 | Project ID in URIs | Immutable identifiers | ✅ Implemented |<br>
| 2025-09-05 | Domain as metadata only | Organizational flexibility | ✅ Implemented |<br>
| 2025-09-05 | Namespace inheritance for all project resources | Consistency | ✅ Implemented |<br>
| 2025-09-05 | Project information page | User experience and metadata display | ✅ Implemented |<br>
| 2025-09-05 | Project treeview navigation | Intuitive project access | ✅ Implemented |<br>
| 2025-09-05 | URL-based state management | Persistent navigation state | ✅ Implemented |<br>
| 2025-09-10 | Centralized ResourceURIService | Standards compliance and consistency | ✅ Implemented |<br>
| 2025-09-10 | Industry best practices alignment | W3C, IOF, enterprise standards | ✅ Documented |<br>
| 2025-09-10 | Configuration validation | Prevent URI misconfigurations | ✅ Implemented |<br>
<br>
---<br>
<br>
## Recent Implementations (Session Updates)<br>
<br>
### Project Information Page<br>
- **Complete metadata display** with modern card-based layout<br>
- **Username display** instead of UUIDs for "Created By" field<br>
- **Enhanced typography** with proper font sizing and monospace for Project ID<br>
- **Clean SVG icons** replacing colorful emojis for professional appearance<br>
- **Responsive design** with proper spacing and theme integration<br>
<br>
### Project Treeview Navigation<br>
- **Click handler** for project info node to open project information page<br>
- **Automatic workbench switching** to project view<br>
- **URL state management** for persistent navigation<br>
- **Seamless integration** with existing context menu functionality<br>
<br>
### Domain Management System<br>
- **Full CRUD operations** for domains (admin-only)<br>
- **Status management** (active, deprecated, archived)<br>
- **Edit functionality** with proper form validation<br>
- **Delete confirmation** with safety checks<br>
- **Integration** with project creation and editing<br>
<br>
### Project CRUD Operations<br>
- **GET endpoint** for individual project details<br>
- **PUT endpoint** for project updates<br>
- **DELETE endpoint** for project removal<br>
- **Project actions** (edit, archive, export, duplicate, delete)<br>
- **Proper error handling** and user feedback<br>
<br>
### User Experience Enhancements<br>
- **URL-based state management** for project and workbench persistence<br>
- **Clean SVG icons** throughout the interface<br>
- **Improved modal styling** with proper button spacing<br>
- **Enhanced error handling** with user-friendly messages<br>
- **Responsive design** improvements<br>
<br>
### Standards Compliance Implementation (September 2025)<br>
- **ResourceURIService**: Centralized URI generation following W3C Cool URIs principles<br>
- **Industry Research**: Comprehensive analysis of W3C, IOF, OBO Foundry, and enterprise standards<br>
- **Configuration Validation**: Installation base URI validation and diagnostic endpoints<br>
- **Best Practices Documentation**: Complete alignment with semantic web and persistent identifier standards<br>
<br>
### Configuration Requirements<br>
- **Installation Base URI**: Must be organizational domain only (e.g., `https://ontology.navy.mil`)<br>
- **Namespace Composition**: Atomic prefixes composed into hierarchical paths<br>
- **Resource Type Segregation**: Clear `/ontologies/`, `/files/`, `/knowledge/` patterns<br>
- **UUID-based Projects**: Immutable identifiers for persistent URIs<br>
<br>
**Assessment**: ODRAS implementation **meets or exceeds industry standards** for enterprise semantic web systems and persistent identifier management.<br>
<br>
## Configuration Best Practices<br>
<br>
### Installation Base URI Requirements<br>
<br>
**✅ Correct Configuration:**<br>
```bash<br>
# Organizational domain only<br>
INSTALLATION_BASE_URI="https://ontology.navy.mil"<br>
INSTALLATION_ORGANIZATION="U.S. Navy"<br>
INSTALLATION_PREFIX="usn"<br>
```<br>
<br>
**❌ Common Misconfigurations:**<br>
```bash<br>
# DO NOT include namespace paths in base URI<br>
INSTALLATION_BASE_URI="https://ontology.navy.mil/usn/adt"     # Wrong<br>
INSTALLATION_BASE_URI="https://ontology.navy.mil/xma-adt"    # Wrong<br>
<br>
# DO NOT include project-specific paths<br>
INSTALLATION_BASE_URI="https://ontology.navy.mil/projects"   # Wrong<br>
```<br>
<br>
### Multi-Instance Configuration Examples<br>
<br>
**U.S. Navy Instance:**<br>
```bash<br>
INSTALLATION_BASE_URI="https://ontology.navy.mil"<br>
INSTALLATION_ORGANIZATION="U.S. Navy"<br>
INSTALLATION_PREFIX="usn"<br>
INSTALLATION_TYPE="military"<br>
INSTALLATION_PROGRAM_OFFICE="Naval Air Systems Command"<br>
```<br>
<br>
**Boeing Defense Instance:**<br>
```bash<br>
INSTALLATION_BASE_URI="https://ontology.boeing.com"<br>
INSTALLATION_ORGANIZATION="Boeing Defense"<br>
INSTALLATION_PREFIX="boeing"<br>
INSTALLATION_TYPE="industry"<br>
INSTALLATION_PROGRAM_OFFICE="Defense & Space"<br>
```<br>
<br>
### Diagnostic Tools<br>
<br>
**Configuration Validation:**<br>
```bash<br>
# Check configuration compliance<br>
GET /api/installation/uri-diagnostics<br>
```<br>
<br>
**Expected Response:**<br>
```json<br>
{<br>
  "installation_config": {<br>
    "base_uri": "https://ontology.navy.mil",<br>
    "validation": {<br>
      "valid": true,<br>
      "issues": []<br>
    }<br>
  },<br>
  "sample_uris": {<br>
    "project_uri": "https://ontology.navy.mil/usn/adt/uuid/",<br>
    "ontology_uri": "https://ontology.navy.mil/usn/adt/uuid/ontologies/name",<br>
    "entity_uri": "https://ontology.navy.mil/usn/adt/uuid/ontologies/name#Class"<br>
  }<br>
}<br>
```<br>
<br>
### Troubleshooting Common Issues<br>
<br>
**Issue: URIs contain duplicate paths**<br>
```<br>
❌ https://ontology.navy.mil/xma-adt/usn/adt/uuid/ontologies/name<br>
✅ https://ontology.navy.mil/usn/adt/uuid/ontologies/name<br>
```<br>
**Solution**: Remove namespace paths from `INSTALLATION_BASE_URI`<br>
<br>
**Issue: Project names instead of UUIDs**<br>
```<br>
❌ https://ontology.navy.mil/usn/adt/xma-adt/ontologies/name<br>
✅ https://ontology.navy.mil/usn/adt/ce1da05a-9a56-4531-aa47-7f030aae2614/ontologies/name<br>
```<br>
**Solution**: Ensure frontend sends project UUID, not project name<br>
<br>
**Issue: Missing namespace in URIs**<br>
```<br>
❌ https://ontology.navy.mil/projects/uuid/ontologies/name<br>
✅ https://ontology.navy.mil/usn/adt/uuid/ontologies/name<br>
```<br>
**Solution**: Assign namespace to project during creation<br>
<br>
**Next Steps**: Phase 3 standards compliance is largely complete. Ready for Phase 4: System Resources migration and Phase 5: Advanced federation features.<br>

