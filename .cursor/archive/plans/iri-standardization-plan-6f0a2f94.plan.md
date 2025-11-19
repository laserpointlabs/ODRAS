<!-- 6f0a2f94-0589-4055-be5c-ee9e41cf1adf 75c68717-72ac-4b7c-892d-c52fb0aeac36 -->
# IRI Standardization Plan

## Overview

ODRAS currently uses a mix of URI and IRI terminology and implementation. This plan standardizes the entire system to use IRI (Internationalized Resource Identifier) consistently, following RFC 3987 and aligning with the existing IRI system architecture.

## Current State Analysis

### Services

- `ResourceURIService` - Uses "URI" terminology (needs rename to `ResourceIRIService`)
- `InstallationIRIService` - Already uses "IRI" correctly
- `NamespaceURIGenerator` - Uses "URI" terminology

### Database

- Some columns use `iri` (correct): `knowledge_assets.iri`, `files.iri`, `projects.iri`, `users.iri`
- Some columns use `uri`: `individual_instances.instance_uri`, `system_index.entity_uri`
- Comments mention "URI/IRI" inconsistently

### API Endpoints

- `/iri/resolve` - Already uses IRI correctly
- Various endpoints return `uri` fields that should be `iri`
- Service methods use `generate_*_uri()` naming

### Frontend

- Mixed usage of `uri` and `iri` variables
- UI labels may show "URI" instead of "IRI"

## Implementation Strategy

This plan integrates with Epic #71 (Incremental Refactoring Strategy) but treats IRI standardization as a focused cross-cutting concern that should be completed systematically.

### Phase 1: Backend Service Standardization

**Files**: `backend/services/resource_uri_service.py`, `backend/services/namespace_uri_generator.py`

1. Rename `ResourceURIService` → `ResourceIRIService`
2. Update all method names: `generate_*_uri()` → `generate_*_iri()`
3. Update all internal variable names and comments
4. Update `NamespaceURIGenerator` to use IRI terminology
5. Update all imports and usages across backend

### Phase 2: Database Schema Standardization

**File**: `backend/odras_schema.sql`

1. Rename columns: `instance_uri` → `instance_iri`, `entity_uri` → `entity_iri`
2. Update comments: Replace "URI/IRI" with "IRI"
3. Create migration script for existing data
4. Update all SQL queries that reference renamed columns

### Phase 3: API Standardization

**Files**: All files in `backend/api/`

1. Update API response schemas to use `iri` instead of `uri`
2. Update endpoint documentation
3. Update all service method calls to use new IRI method names
4. Ensure consistent IRI format in responses

### Phase 4: Frontend Standardization

**File**: `frontend/app.html`

1. Update JavaScript variable names: `uri` → `iri` where appropriate
2. Update UI labels: "URI" → "IRI"
3. Update API calls to expect `iri` fields
4. Update display functions to show "IRI" consistently

### Phase 5: Documentation and Comments

**Files**: All documentation files, code comments

1. Update all documentation to use IRI terminology
2. Update code comments
3. Update API documentation
4. Ensure consistency in user-facing documentation

### Phase 6: Testing and Validation

**Files**: All test files

1. Update test fixtures to use `iri` fields
2. Update test assertions
3. Add tests for IRI generation consistency
4. Validate IRI format compliance

## Key Files to Modify

### Backend Services

- `backend/services/resource_uri_service.py` → `resource_iri_service.py`
- `backend/services/namespace_uri_generator.py`
- `backend/services/installation_iri_service.py` (already correct, verify)

### Database

- `backend/odras_schema.sql`
- Migration script for column renames
- All SQL queries referencing `*_uri` columns

### API Endpoints

- `backend/api/ontology_registry.py`
- `backend/api/ontology.py`
- `backend/api/individuals.py`
- `backend/api/das.py`
- `backend/api/files.py`
- All other API files using URI services

### Frontend

- `frontend/app.html` (search for uri/URI usage)

### Documentation

- `docs/IRI_SYSTEM_OVERVIEW.md` (verify consistency)
- `docs/deployment/INSTALLATION_SPECIFIC_IRI_CONFIG.md`
- `TODO.md` (update task #1)

## Migration Considerations

1. **Database Migration**: Column renames require careful migration

- Create migration script with `ALTER TABLE` statements
- Update all references before dropping old columns
- Test migration on development database first

2. **Backward Compatibility**: Consider temporary aliases

- API endpoints could accept both `uri` and `iri` during transition
- Deprecate `uri` parameters after frontend is updated

3. **Data Migration**: Existing data may have `uri` values

- Verify all existing IRIs are valid
- No data transformation needed (IRIs are already valid)

## Integration with Current Refactoring

This plan aligns with Epic #71 (Incremental Refactoring):

- Can be done incrementally by component
- Each phase can be completed independently
- Fits the "refactor as you touch" strategy
- However, IRI standardization is foundational and should be completed systematically

**Recommended Approach**: Complete Phases 1-3 first (backend + database) as they're foundational, then do Phase 4 (frontend) incrementally as UI components are touched.

## Success Criteria

1. All services use IRI terminology consistently
2. All database columns use `iri` naming
3. All API responses use `iri` fields
4. Frontend displays "IRI" consistently
5. All documentation uses IRI terminology
6. No references to "URI" remain (except in comments explaining IRI vs URI relationship)
7. All tests pass with IRI naming

## Risk Mitigation

1. **Breaking Changes**: Update frontend and backend simultaneously or use API versioning
2. **Data Loss**: Test migrations thoroughly on development database
3. **Service Disruption**: Deploy backend changes first, then frontend
4. **Testing**: Comprehensive test suite before deployment

### To-dos

- [ ] Rename ResourceURIService to ResourceIRIService and update all method names (generate_*_uri → generate_*_iri)
- [ ] Update NamespaceURIGenerator to use IRI terminology consistently
- [ ] Update all imports and usages of ResourceURIService across backend codebase
- [ ] Create migration to rename database columns (instance_uri → instance_iri, entity_uri → entity_iri)
- [ ] Update all SQL queries to use renamed IRI columns
- [ ] Update API response schemas to use iri instead of uri fields
- [ ] Update all API endpoints to use new IRI service methods and return iri fields
- [ ] Update frontend JavaScript variables from uri to iri where appropriate
- [ ] Update frontend UI labels to display 'IRI' instead of 'URI'
- [ ] Update all documentation files to use IRI terminology consistently
- [ ] Update all tests to use IRI naming and validate IRI format compliance
- [ ] Comprehensive testing: verify IRI generation, API responses, database queries, and frontend display