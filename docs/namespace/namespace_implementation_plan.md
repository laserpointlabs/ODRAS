# ODRAS Namespace Management Implementation Plan<br>
<br>
## Executive Summary<br>
<br>
This document outlines the implementation plan for ODRAS namespace management system with versioning, addressing the current local storage vs Fuseki inconsistencies and establishing a robust, scalable namespace architecture for defense and industry ontologies.<br>
<br>
## 1. Current State Analysis<br>
<br>
### 1.1 Problems Identified<br>
- **Data Inconsistency**: Local storage and Fuseki contain different class labels<br>
- **No Namespace Management**: Ad-hoc IRI generation without proper governance<br>
- **Import System Issues**: Reference ontology imports fail due to data source mismatches<br>
- **No Versioning**: No version control for ontology evolution<br>
- **Single Source of Truth Missing**: Fuseki should be authoritative but isn't consistently used<br>
<br>
### 1.2 Root Causes<br>
- Frontend properties panel updates only local storage, not Fuseki<br>
- Import system uses mixed data sources (local storage + API)<br>
- No centralized namespace registry<br>
- No versioning strategy for ontology evolution<br>
<br>
## 2. Target Architecture<br>
<br>
### 2.1 Core Principles<br>
1. **Fuseki as Single Source of Truth**: All ontology data originates from and is validated against Fuseki<br>
2. **Admin-Controlled Namespaces**: Only admins can create and manage reference ontologies<br>
3. **Versioned Evolution**: All changes tracked through proper versioning<br>
4. **Hierarchical Governance**: Enforce namespace hierarchy rules from namespace MVP spec<br>
5. **Quality Gates**: Automated validation before release<br>
<br>
### 2.2 Namespace Structure<br>
```<br>
https://w3id.org/defense/{type}/{name}#          # Stable namespace URI<br>
https://w3id.org/defense/{type}/{name}           # Stable module IRI<br>
https://w3id.org/defense/{type}/{name}/{version} # Version IRI<br>
```<br>
<br>
**Types**: `core`, `domain`, `program`, `project`, `industry`, `vocab`, `shapes`, `align`<br>
<br>
## 3. Implementation Phases<br>
<br>
### Phase 1: Core Namespace Management (MVP)<br>
**Timeline**: 2-3 weeks<br>
**Goal**: Establish basic namespace management with Fuseki as source of truth<br>
<br>
#### 3.1.1 Backend Implementation<br>
<br>
**Database Schema**:<br>
```sql<br>
-- Namespace registry<br>
CREATE TABLE namespace_registry (<br>
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),<br>
    name VARCHAR(255) NOT NULL,<br>
    type VARCHAR(50) NOT NULL, -- core, domain, program, project, industry<br>
    path VARCHAR(500) NOT NULL, -- dod/core, usn/core, etc.<br>
    prefix VARCHAR(100) NOT NULL,<br>
    status VARCHAR(50) DEFAULT 'draft', -- draft, released, deprecated<br>
    owners TEXT[], -- email addresses<br>
    created_at TIMESTAMP DEFAULT NOW(),<br>
    updated_at TIMESTAMP DEFAULT NOW(),<br>
    UNIQUE(name, type)<br>
);<br>
<br>
-- Version management<br>
CREATE TABLE namespace_versions (<br>
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),<br>
    namespace_id UUID REFERENCES namespace_registry(id),<br>
    version VARCHAR(50) NOT NULL, -- 2025-09-01, v1.0.0<br>
    version_iri VARCHAR(1000) NOT NULL,<br>
    status VARCHAR(50) DEFAULT 'draft', -- draft, released, deprecated<br>
    created_at TIMESTAMP DEFAULT NOW(),<br>
    released_at TIMESTAMP NULL,<br>
    UNIQUE(namespace_id, version)<br>
);<br>
<br>
-- Class definitions (versioned)<br>
CREATE TABLE namespace_classes (<br>
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),<br>
    version_id UUID REFERENCES namespace_versions(id),<br>
    local_name VARCHAR(255) NOT NULL, -- Class1, AirVehicle<br>
    label VARCHAR(500) NOT NULL, -- "Air Vehicle", "Mission"<br>
    iri VARCHAR(1000) NOT NULL, -- Full IRI<br>
    comment TEXT,<br>
    created_at TIMESTAMP DEFAULT NOW(),<br>
    updated_at TIMESTAMP DEFAULT NOW()<br>
);<br>
```<br>
<br>
**API Endpoints**:<br>
```python<br>
# Namespace Management<br>
POST   /api/admin/namespaces                    # Create namespace<br>
GET    /api/admin/namespaces                    # List namespaces<br>
GET    /api/admin/namespaces/{id}               # Get namespace details<br>
PUT    /api/admin/namespaces/{id}               # Update namespace metadata<br>
DELETE /api/admin/namespaces/{id}               # Delete namespace<br>
<br>
# Version Management<br>
POST   /api/admin/namespaces/{id}/versions      # Create new version<br>
GET    /api/admin/namespaces/{id}/versions      # List versions<br>
GET    /api/admin/namespaces/{id}/versions/{version}  # Get version details<br>
PUT    /api/admin/namespaces/{id}/versions/{version}  # Update version<br>
DELETE /api/admin/namespaces/{id}/versions/{version}  # Delete version (if draft)<br>
<br>
# Class Management (versioned)<br>
POST   /api/admin/namespaces/{id}/versions/{version}/classes     # Add class<br>
GET    /api/admin/namespaces/{id}/versions/{version}/classes     # List classes<br>
PUT    /api/admin/namespaces/{id}/versions/{version}/classes/{class_id}  # Update class<br>
DELETE /api/admin/namespaces/{id}/versions/{version}/classes/{class_id}  # Delete class<br>
<br>
# Release Management<br>
POST   /api/admin/namespaces/{id}/versions/{version}/release     # Release version<br>
GET    /api/admin/namespaces/{id}/versions/{version}/diff        # Compare versions<br>
```<br>
<br>
#### 3.1.2 Frontend Implementation<br>
<br>
**Admin Namespace Dashboard**:<br>
- List all reference ontologies with status indicators<br>
- Create new namespaces with proper IRI generation<br>
- Manage namespace metadata and ownership<br>
- Version management interface<br>
<br>
**Class Management Interface**:<br>
- Add/edit/delete classes with proper naming conventions<br>
- Real-time Fuseki synchronization<br>
- IRI preview and validation<br>
- Label management (updates both frontend and Fuseki)<br>
<br>
#### 3.1.3 Import System Overhaul<br>
- Remove local storage dependency for imports<br>
- Always fetch from Fuseki API<br>
- Consistent equivalence counting based on Fuseki data<br>
- Proper namespace resolution<br>
<br>
### Phase 2: Dependency Management and Validation<br>
**Timeline**: 2-3 weeks<br>
**Goal**: Enforce namespace hierarchy and prevent circular dependencies<br>
<br>
#### 3.2.1 Import Validation<br>
- Validate import hierarchy rules from namespace MVP spec<br>
- Block invalid import attempts (e.g., core importing from project)<br>
- Circular dependency detection<br>
- Version compatibility checking<br>
<br>
#### 3.2.2 Content Validation<br>
- SHACL validation pipeline<br>
- Naming convention enforcement (UpperCamelCase for classes)<br>
- RDF syntax validation<br>
- Import cycle detection<br>
<br>
#### 3.2.3 Quality Gates<br>
- Pre-release validation checks<br>
- Automated testing pipeline<br>
- Release approval workflow<br>
<br>
### Phase 3: Advanced Features and Governance<br>
**Timeline**: 3-4 weeks<br>
**Goal**: Production-ready namespace management with full governance<br>
<br>
#### 3.3.1 Access Control<br>
- Namespace ownership and permissions<br>
- Role-based access control (owner, contributor, viewer)<br>
- Cross-namespace change approval workflows<br>
<br>
#### 3.3.2 Publishing and Distribution<br>
- Automatic Fuseki graph creation on release<br>
- Static documentation generation<br>
- API endpoint for namespace discovery<br>
- Version-specific graph management<br>
<br>
#### 3.3.3 Monitoring and Analytics<br>
- Usage analytics and metrics<br>
- Health checks and monitoring<br>
- Dependency impact analysis<br>
- Change tracking and audit logs<br>
<br>
### Phase 4: Migration and Advanced Features<br>
**Timeline**: 2-3 weeks<br>
**Goal**: Migrate existing system and add advanced capabilities<br>
<br>
#### 3.4.1 Migration Strategy<br>
- Gradual migration from current system<br>
- Backward compatibility layer<br>
- Data migration tools<br>
- Existing ontology conversion<br>
<br>
#### 3.4.2 Advanced Features<br>
- IRI deprecation and migration tools<br>
- Emergency rollback procedures<br>
- Conflict resolution system<br>
- Multi-tenant namespace isolation<br>
<br>
## 4. Critical Gaps Addressed<br>
<br>
### 4.1 Import Dependency Management<br>
**Solution**: Import dependency graph validation with hierarchy enforcement<br>
**Implementation**: Database triggers and API validation<br>
**Timeline**: Phase 2<br>
<br>
### 4.2 Namespace Registry Validation<br>
**Solution**: Automated validation of namespace hierarchy rules<br>
**Implementation**: Validation service with rule engine<br>
**Timeline**: Phase 2<br>
<br>
### 4.3 IRI Stability and Migration<br>
**Solution**: IRI deprecation workflow with automatic redirects<br>
**Implementation**: IRI mapping service and migration tools<br>
**Timeline**: Phase 4<br>
<br>
### 4.4 Access Control and Permissions<br>
**Solution**: Granular namespace-level permissions<br>
**Implementation**: Role-based access control system<br>
**Timeline**: Phase 3<br>
<br>
### 4.5 Content Validation and Quality Gates<br>
**Solution**: Automated validation pipeline with SHACL<br>
**Implementation**: Validation service with CI/CD integration<br>
**Timeline**: Phase 2<br>
<br>
### 4.6 Publishing and Distribution<br>
**Solution**: Automatic publishing to Fuseki on release<br>
**Implementation**: Publishing service with graph management<br>
**Timeline**: Phase 3<br>
<br>
### 4.7 Conflict Resolution<br>
**Solution**: Global namespace prefix registry with conflict detection<br>
**Implementation**: Prefix registry service with validation<br>
**Timeline**: Phase 2<br>
<br>
### 4.8 Rollback and Recovery<br>
**Solution**: Point-in-time recovery with data integrity validation<br>
**Implementation**: Backup and recovery service<br>
**Timeline**: Phase 4<br>
<br>
### 4.9 Monitoring and Observability<br>
**Solution**: Comprehensive monitoring and analytics<br>
**Implementation**: Monitoring service with metrics collection<br>
**Timeline**: Phase 3<br>
<br>
### 4.10 Integration with Existing System<br>
**Solution**: Gradual migration with backward compatibility<br>
**Implementation**: Migration tools and compatibility layer<br>
**Timeline**: Phase 4<br>
<br>
## 5. Technical Specifications<br>
<br>
### 5.1 Versioning Strategy<br>
- **Date-based versioning**: `2025-09-01`, `2025-09-15`<br>
- **Stable IRIs**: Never change once released<br>
- **Deprecation**: Use `owl:deprecated "true"^^xsd:boolean`<br>
- **Version IRIs**: Dated URIs for specific versions<br>
<br>
### 5.2 Naming Conventions<br>
- **Classes**: `UpperCamelCase` (e.g., `AirVehicle`)<br>
- **Properties**: `lowerCamelCase` (e.g., `supportsMission`)<br>
- **Individuals**: `UPPER_SNAKE` or UUID suffixes<br>
- **No spaces or punctuation** in local names<br>
<br>
### 5.3 Import Hierarchy Rules<br>
- `project` may import `program`, `service`, `domain`, `core`<br>
- `program` may import `service`, `domain`, `core`<br>
- `service` may import `core`, `gov`<br>
- `domain` may import `core`<br>
- `vocab` should not import OWL modules<br>
- `shapes`/`align` import whatever they validate/map<br>
<br>
### 5.4 Data Flow<br>
1. **Create**: Admin creates namespace and version<br>
2. **Edit**: Admin adds/edits classes (draft version)<br>
3. **Validate**: Automated validation checks<br>
4. **Release**: Version becomes immutable<br>
5. **Publish**: Automatic Fuseki graph creation<br>
6. **Import**: Other ontologies import released versions<br>
<br>
## 6. Success Criteria<br>
<br>
### 6.1 Phase 1 Success<br>
- [ ] Fuseki is single source of truth<br>
- [ ] Admin can create and manage namespaces<br>
- [ ] Class labels sync between frontend and Fuseki<br>
- [ ] Import system works with Fuseki data only<br>
- [ ] Basic versioning is functional<br>
<br>
### 6.2 Phase 2 Success<br>
- [ ] Import hierarchy rules enforced<br>
- [ ] No circular dependencies possible<br>
- [ ] SHACL validation working<br>
- [ ] Naming conventions enforced<br>
- [ ] Quality gates prevent bad releases<br>
<br>
### 6.3 Phase 3 Success<br>
- [ ] Full access control implemented<br>
- [ ] Automatic publishing to Fuseki<br>
- [ ] Monitoring and analytics working<br>
- [ ] Documentation generation functional<br>
- [ ] Production-ready governance<br>
<br>
### 6.4 Phase 4 Success<br>
- [ ] Existing system migrated<br>
- [ ] Advanced features operational<br>
- [ ] Full backward compatibility<br>
- [ ] Emergency procedures tested<br>
- [ ] Multi-tenant support working<br>
<br>
## 7. Risk Mitigation<br>
<br>
### 7.1 Technical Risks<br>
- **Data Loss**: Comprehensive backup and recovery procedures<br>
- **Performance**: Fuseki optimization and caching strategies<br>
- **Compatibility**: Gradual migration with fallback options<br>
<br>
### 7.2 Operational Risks<br>
- **User Adoption**: Training and documentation<br>
- **Governance**: Clear policies and procedures<br>
- **Maintenance**: Automated monitoring and alerting<br>
<br>
## 8. Next Steps<br>
<br>
### 8.1 Immediate Actions<br>
1. **Approve implementation plan**<br>
2. **Set up development environment**<br>
3. **Create database schema**<br>
4. **Implement Phase 1 backend APIs**<br>
<br>
### 8.2 Phase 1 Deliverables<br>
1. **Namespace management APIs**<br>
2. **Admin frontend interface**<br>
3. **Import system overhaul**<br>
4. **Basic versioning system**<br>
<br>
### 8.3 Success Metrics<br>
- **Data Consistency**: 100% Fuseki-frontend sync<br>
- **Import Success**: 100% reference ontology imports working<br>
- **Admin Productivity**: Namespace creation < 5 minutes<br>
- **System Reliability**: 99.9% uptime<br>
<br>
## 9. Conclusion<br>
<br>
This implementation plan addresses the current namespace management gaps in ODRAS while establishing a robust, scalable foundation for defense and industry ontology management. The phased approach ensures minimal disruption while delivering immediate value through Fuseki as the single source of truth.<br>
<br>
The plan balances immediate needs (fixing import issues) with long-term goals (comprehensive namespace governance) while following established best practices from the namespace MVP specification.<br>
<br>

