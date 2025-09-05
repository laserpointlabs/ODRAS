# ODRAS Namespace Management Implementation Plan

## Executive Summary

This document outlines the implementation plan for ODRAS namespace management system with versioning, addressing the current local storage vs Fuseki inconsistencies and establishing a robust, scalable namespace architecture for defense and industry ontologies.

## 1. Current State Analysis

### 1.1 Problems Identified
- **Data Inconsistency**: Local storage and Fuseki contain different class labels
- **No Namespace Management**: Ad-hoc IRI generation without proper governance
- **Import System Issues**: Reference ontology imports fail due to data source mismatches
- **No Versioning**: No version control for ontology evolution
- **Single Source of Truth Missing**: Fuseki should be authoritative but isn't consistently used

### 1.2 Root Causes
- Frontend properties panel updates only local storage, not Fuseki
- Import system uses mixed data sources (local storage + API)
- No centralized namespace registry
- No versioning strategy for ontology evolution

## 2. Target Architecture

### 2.1 Core Principles
1. **Fuseki as Single Source of Truth**: All ontology data originates from and is validated against Fuseki
2. **Admin-Controlled Namespaces**: Only admins can create and manage reference ontologies
3. **Versioned Evolution**: All changes tracked through proper versioning
4. **Hierarchical Governance**: Enforce namespace hierarchy rules from namespace MVP spec
5. **Quality Gates**: Automated validation before release

### 2.2 Namespace Structure
```
https://w3id.org/defense/{type}/{name}#          # Stable namespace URI
https://w3id.org/defense/{type}/{name}           # Stable module IRI
https://w3id.org/defense/{type}/{name}/{version} # Version IRI
```

**Types**: `core`, `domain`, `program`, `project`, `industry`, `vocab`, `shapes`, `align`

## 3. Implementation Phases

### Phase 1: Core Namespace Management (MVP)
**Timeline**: 2-3 weeks
**Goal**: Establish basic namespace management with Fuseki as source of truth

#### 3.1.1 Backend Implementation

**Database Schema**:
```sql
-- Namespace registry
CREATE TABLE namespace_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL, -- core, domain, program, project, industry
    path VARCHAR(500) NOT NULL, -- dod/core, usn/core, etc.
    prefix VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'draft', -- draft, released, deprecated
    owners TEXT[], -- email addresses
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(name, type)
);

-- Version management
CREATE TABLE namespace_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    namespace_id UUID REFERENCES namespace_registry(id),
    version VARCHAR(50) NOT NULL, -- 2025-09-01, v1.0.0
    version_iri VARCHAR(1000) NOT NULL,
    status VARCHAR(50) DEFAULT 'draft', -- draft, released, deprecated
    created_at TIMESTAMP DEFAULT NOW(),
    released_at TIMESTAMP NULL,
    UNIQUE(namespace_id, version)
);

-- Class definitions (versioned)
CREATE TABLE namespace_classes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id UUID REFERENCES namespace_versions(id),
    local_name VARCHAR(255) NOT NULL, -- Class1, AirVehicle
    label VARCHAR(500) NOT NULL, -- "Air Vehicle", "Mission"
    iri VARCHAR(1000) NOT NULL, -- Full IRI
    comment TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**API Endpoints**:
```python
# Namespace Management
POST   /api/admin/namespaces                    # Create namespace
GET    /api/admin/namespaces                    # List namespaces
GET    /api/admin/namespaces/{id}               # Get namespace details
PUT    /api/admin/namespaces/{id}               # Update namespace metadata
DELETE /api/admin/namespaces/{id}               # Delete namespace

# Version Management
POST   /api/admin/namespaces/{id}/versions      # Create new version
GET    /api/admin/namespaces/{id}/versions      # List versions
GET    /api/admin/namespaces/{id}/versions/{version}  # Get version details
PUT    /api/admin/namespaces/{id}/versions/{version}  # Update version
DELETE /api/admin/namespaces/{id}/versions/{version}  # Delete version (if draft)

# Class Management (versioned)
POST   /api/admin/namespaces/{id}/versions/{version}/classes     # Add class
GET    /api/admin/namespaces/{id}/versions/{version}/classes     # List classes
PUT    /api/admin/namespaces/{id}/versions/{version}/classes/{class_id}  # Update class
DELETE /api/admin/namespaces/{id}/versions/{version}/classes/{class_id}  # Delete class

# Release Management
POST   /api/admin/namespaces/{id}/versions/{version}/release     # Release version
GET    /api/admin/namespaces/{id}/versions/{version}/diff        # Compare versions
```

#### 3.1.2 Frontend Implementation

**Admin Namespace Dashboard**:
- List all reference ontologies with status indicators
- Create new namespaces with proper IRI generation
- Manage namespace metadata and ownership
- Version management interface

**Class Management Interface**:
- Add/edit/delete classes with proper naming conventions
- Real-time Fuseki synchronization
- IRI preview and validation
- Label management (updates both frontend and Fuseki)

#### 3.1.3 Import System Overhaul
- Remove local storage dependency for imports
- Always fetch from Fuseki API
- Consistent equivalence counting based on Fuseki data
- Proper namespace resolution

### Phase 2: Dependency Management and Validation
**Timeline**: 2-3 weeks
**Goal**: Enforce namespace hierarchy and prevent circular dependencies

#### 3.2.1 Import Validation
- Validate import hierarchy rules from namespace MVP spec
- Block invalid import attempts (e.g., core importing from project)
- Circular dependency detection
- Version compatibility checking

#### 3.2.2 Content Validation
- SHACL validation pipeline
- Naming convention enforcement (UpperCamelCase for classes)
- RDF syntax validation
- Import cycle detection

#### 3.2.3 Quality Gates
- Pre-release validation checks
- Automated testing pipeline
- Release approval workflow

### Phase 3: Advanced Features and Governance
**Timeline**: 3-4 weeks
**Goal**: Production-ready namespace management with full governance

#### 3.3.1 Access Control
- Namespace ownership and permissions
- Role-based access control (owner, contributor, viewer)
- Cross-namespace change approval workflows

#### 3.3.2 Publishing and Distribution
- Automatic Fuseki graph creation on release
- Static documentation generation
- API endpoint for namespace discovery
- Version-specific graph management

#### 3.3.3 Monitoring and Analytics
- Usage analytics and metrics
- Health checks and monitoring
- Dependency impact analysis
- Change tracking and audit logs

### Phase 4: Migration and Advanced Features
**Timeline**: 2-3 weeks
**Goal**: Migrate existing system and add advanced capabilities

#### 3.4.1 Migration Strategy
- Gradual migration from current system
- Backward compatibility layer
- Data migration tools
- Existing ontology conversion

#### 3.4.2 Advanced Features
- IRI deprecation and migration tools
- Emergency rollback procedures
- Conflict resolution system
- Multi-tenant namespace isolation

## 4. Critical Gaps Addressed

### 4.1 Import Dependency Management
**Solution**: Import dependency graph validation with hierarchy enforcement
**Implementation**: Database triggers and API validation
**Timeline**: Phase 2

### 4.2 Namespace Registry Validation
**Solution**: Automated validation of namespace hierarchy rules
**Implementation**: Validation service with rule engine
**Timeline**: Phase 2

### 4.3 IRI Stability and Migration
**Solution**: IRI deprecation workflow with automatic redirects
**Implementation**: IRI mapping service and migration tools
**Timeline**: Phase 4

### 4.4 Access Control and Permissions
**Solution**: Granular namespace-level permissions
**Implementation**: Role-based access control system
**Timeline**: Phase 3

### 4.5 Content Validation and Quality Gates
**Solution**: Automated validation pipeline with SHACL
**Implementation**: Validation service with CI/CD integration
**Timeline**: Phase 2

### 4.6 Publishing and Distribution
**Solution**: Automatic publishing to Fuseki on release
**Implementation**: Publishing service with graph management
**Timeline**: Phase 3

### 4.7 Conflict Resolution
**Solution**: Global namespace prefix registry with conflict detection
**Implementation**: Prefix registry service with validation
**Timeline**: Phase 2

### 4.8 Rollback and Recovery
**Solution**: Point-in-time recovery with data integrity validation
**Implementation**: Backup and recovery service
**Timeline**: Phase 4

### 4.9 Monitoring and Observability
**Solution**: Comprehensive monitoring and analytics
**Implementation**: Monitoring service with metrics collection
**Timeline**: Phase 3

### 4.10 Integration with Existing System
**Solution**: Gradual migration with backward compatibility
**Implementation**: Migration tools and compatibility layer
**Timeline**: Phase 4

## 5. Technical Specifications

### 5.1 Versioning Strategy
- **Date-based versioning**: `2025-09-01`, `2025-09-15`
- **Stable IRIs**: Never change once released
- **Deprecation**: Use `owl:deprecated "true"^^xsd:boolean`
- **Version IRIs**: Dated URIs for specific versions

### 5.2 Naming Conventions
- **Classes**: `UpperCamelCase` (e.g., `AirVehicle`)
- **Properties**: `lowerCamelCase` (e.g., `supportsMission`)
- **Individuals**: `UPPER_SNAKE` or UUID suffixes
- **No spaces or punctuation** in local names

### 5.3 Import Hierarchy Rules
- `project` may import `program`, `service`, `domain`, `core`
- `program` may import `service`, `domain`, `core`
- `service` may import `core`, `gov`
- `domain` may import `core`
- `vocab` should not import OWL modules
- `shapes`/`align` import whatever they validate/map

### 5.4 Data Flow
1. **Create**: Admin creates namespace and version
2. **Edit**: Admin adds/edits classes (draft version)
3. **Validate**: Automated validation checks
4. **Release**: Version becomes immutable
5. **Publish**: Automatic Fuseki graph creation
6. **Import**: Other ontologies import released versions

## 6. Success Criteria

### 6.1 Phase 1 Success
- [ ] Fuseki is single source of truth
- [ ] Admin can create and manage namespaces
- [ ] Class labels sync between frontend and Fuseki
- [ ] Import system works with Fuseki data only
- [ ] Basic versioning is functional

### 6.2 Phase 2 Success
- [ ] Import hierarchy rules enforced
- [ ] No circular dependencies possible
- [ ] SHACL validation working
- [ ] Naming conventions enforced
- [ ] Quality gates prevent bad releases

### 6.3 Phase 3 Success
- [ ] Full access control implemented
- [ ] Automatic publishing to Fuseki
- [ ] Monitoring and analytics working
- [ ] Documentation generation functional
- [ ] Production-ready governance

### 6.4 Phase 4 Success
- [ ] Existing system migrated
- [ ] Advanced features operational
- [ ] Full backward compatibility
- [ ] Emergency procedures tested
- [ ] Multi-tenant support working

## 7. Risk Mitigation

### 7.1 Technical Risks
- **Data Loss**: Comprehensive backup and recovery procedures
- **Performance**: Fuseki optimization and caching strategies
- **Compatibility**: Gradual migration with fallback options

### 7.2 Operational Risks
- **User Adoption**: Training and documentation
- **Governance**: Clear policies and procedures
- **Maintenance**: Automated monitoring and alerting

## 8. Next Steps

### 8.1 Immediate Actions
1. **Approve implementation plan**
2. **Set up development environment**
3. **Create database schema**
4. **Implement Phase 1 backend APIs**

### 8.2 Phase 1 Deliverables
1. **Namespace management APIs**
2. **Admin frontend interface**
3. **Import system overhaul**
4. **Basic versioning system**

### 8.3 Success Metrics
- **Data Consistency**: 100% Fuseki-frontend sync
- **Import Success**: 100% reference ontology imports working
- **Admin Productivity**: Namespace creation < 5 minutes
- **System Reliability**: 99.9% uptime

## 9. Conclusion

This implementation plan addresses the current namespace management gaps in ODRAS while establishing a robust, scalable foundation for defense and industry ontology management. The phased approach ensures minimal disruption while delivering immediate value through Fuseki as the single source of truth.

The plan balances immediate needs (fixing import issues) with long-term goals (comprehensive namespace governance) while following established best practices from the namespace MVP specification.

