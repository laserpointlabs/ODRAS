# CQMT Synchronization Implementation - TODO List

> **Context**: This implements standard industry infrastructure for our sound CQMT architecture. See `CQMT_ARCHITECTURAL_ASSESSMENT.md` for architectural validation.

## Phase 1: Dependency Tracking ⚡ MVP (RECOMMENDED FIRST)

### Database Layer
- [ ] **DB-001**: Create `mt_ontology_dependencies` table
  - Fields: id, mt_id, ontology_graph_iri, referenced_element_iri, element_type, timestamps, is_valid
  - Constraint: UNIQUE(mt_id, referenced_element_iri)
  - Acceptance: Table exists, constraints enforced

- [ ] **DB-002**: Create indexes on `mt_ontology_dependencies`
  - Index: referenced_element_iri (for impact analysis)
  - Index: is_valid (for validation queries)
  - Index: mt_id (for MT dependency lookups)
  - Acceptance: Queries perform well (<100ms)

- [ ] **DB-003**: Create migration script for existing MTs
  - Extract dependencies from all existing MTs
  - Populate dependency table
  - Acceptance: All existing MTs have dependency records

### Service Layer

- [ ] **SRV-001**: Create `CQMTDependencyTracker` service class
  - File: `backend/services/cqmt_dependency_tracker.py`
  - Methods: extract_dependencies(), validate_dependencies(), get_affected_mts()
  - Acceptance: Class exists, methods defined

- [ ] **SRV-002**: Implement dependency extraction logic
  - Parse MT triples from Fuseki
  - Extract IRIs (classes, properties, individuals)
  - Classify by element type
  - Acceptance: Unit tests pass with 95%+ accuracy

- [ ] **SRV-003**: Implement dependency validation logic
  - Query Fuseki for element existence
  - Mark dependencies as valid/invalid
  - Batch validation for performance
  - Acceptance: Correctly identifies valid/invalid references

- [ ] **SRV-004**: Implement affected MT discovery
  - Query dependency table for changed elements
  - Return list of affected MTs
  - Acceptance: Returns correct MTs for given element changes

- [ ] **SRV-005**: Hook into MT create/update workflow
  - Extract dependencies when MT created
  - Re-extract dependencies when MT updated
  - Update dependency table
  - Acceptance: Dependency table stays current

### API Layer

- [ ] **API-001**: Create `GET /api/cqmt/microtheories/{mt_id}/dependencies` endpoint
  - Returns: List of ontology elements MT depends on
  - Includes: element_type, referenced_element_iri, is_valid
  - Acceptance: Returns dependency list, handles missing MT

- [ ] **API-002**: Create `GET /api/cqmt/microtheories/{mt_id}/validation` endpoint
  - Returns: Validation status of all dependencies
  - Includes: invalid_count, broken_references list
  - Acceptance: Correctly reports validation status

- [ ] **API-003**: Create `GET /api/cqmt/ontologies/{graph_iri}/impact-analysis` endpoint
  - Input: element IRI (or list of changed elements)
  - Returns: List of affected MTs
  - Acceptance: Correctly identifies affected MTs

- [ ] **API-004**: Add dependency tracking to existing MT endpoints
  - POST /api/cqmt/projects/{project_id}/microtheories
  - PUT /api/cqmt/microtheories/{mt_id}
  - Acceptance: New/updated MTs automatically tracked

### Frontend Layer

- [ ] **UI-001**: Add validation badge to MT list view
  - Show ✅ green for valid, ⚠️ yellow for invalid, ❌ red for errors
  - Tooltip shows invalid count
  - Acceptance: Badge displays correctly, updates on validation

- [ ] **UI-002**: Create dependencies panel in MT details view
  - Display list of referenced elements
  - Show validation status for each
  - Link to ontology element if exists
  - Acceptance: Panel shows correct dependencies

- [ ] **UI-003**: Add "Validate" button to MT details
  - Triggers validation API call
  - Shows validation results
  - Updates UI with results
  - Acceptance: Button works, shows accurate results

- [ ] **UI-004**: Show validation warnings on CQ list
  - Indicate if CQ references invalid MT elements
  - Acceptance: Warnings appear when appropriate

### Testing

- [ ] **TEST-001**: Unit tests for dependency extraction
  - Test parsing various triple patterns
  - Test IRI extraction accuracy
  - Test element type classification
  - Acceptance: 90%+ code coverage

- [ ] **TEST-002**: Unit tests for validation logic
  - Test valid element detection
  - Test invalid element detection
  - Test batch validation
  - Acceptance: 90%+ code coverage

- [ ] **TEST-003**: Integration tests for API endpoints
  - Test dependency endpoint
  - Test validation endpoint
  - Test impact analysis endpoint
  - Acceptance: All tests pass

- [ ] **TEST-004**: E2E tests for full workflow
  - Create MT with dependencies
  - Validate dependencies
  - Change ontology element
  - Verify impact detection
  - Acceptance: Full workflow works

- [ ] **TEST-005**: Performance tests
  - Test dependency extraction on large MTs (1000+ triples)
  - Test validation on multiple MTs
  - Test impact analysis query speed
  - Acceptance: All operations < 1 second

### Documentation

- [ ] **DOC-001**: Update CQMT API documentation
  - Document new endpoints
  - Add examples
  - Include error codes
  - Acceptance: Docs complete and accurate

- [ ] **DOC-002**: Create user guide for dependency tracking
  - Explain what dependencies are
  - Show how to use validation
  - Include troubleshooting
  - Acceptance: Guide helps users understand feature

## Phase 2: Change Detection ⚡ Recommended Next

### Service Layer

- [ ] **SRV-101**: Create `OntologyChangeDetector` service class
  - File: `backend/services/ontology_change_detector.py`
  - Methods: detect_changes(), classify_change(), get_changed_elements()
  - Acceptance: Class exists, methods defined

- [ ] **SRV-102**: Implement ontology diff logic
  - Compare old/new ontology versions
  - Detect additions, deletions, modifications
  - Track IRIs that changed
  - Acceptance: Correctly identifies all changes

- [ ] **SRV-103**: Implement change classification
  - Classify as breaking/compatible/enhancement
  - Detect renaming vs deletion
  - Track domain/range changes
  - Acceptance: Classifies changes correctly

- [ ] **SRV-104**: Hook into ontology save workflow
  - Call change detector before save
  - Store change metadata
  - Trigger notifications
  - Acceptance: Changes detected on every save

### API Layer

- [ ] **API-101**: Update `POST /api/ontology/save` endpoint
  - Detect changes before saving
  - Query affected MTs
  - Return change notification
  - Acceptance: Returns accurate change info

- [ ] **API-102**: Create `GET /api/ontology/{graph_iri}/changes` endpoint
  - Returns recent changes to ontology
  - Includes change metadata
  - Acceptance: Returns accurate change history

### Frontend Layer

- [ ] **UI-101**: Create change notification dialog
  - Shows: "This change affects X microtheories"
  - Lists affected MTs
  - Options: [Show Details] [Update Now] [Later]
  - Acceptance: Dialog displays correctly

- [ ] **UI-102**: Create change details view
  - Shows what changed
  - Lists affected MTs
  - Shows before/after for renames
  - Acceptance: Details view accurate

- [ ] **UI-103**: Add "Show Impact" button to ontology editor
  - Shows what would be affected before saving
  - Acceptance: Button works, shows accurate info

### Testing

- [ ] **TEST-101**: Unit tests for change detection
  - Test various change types
  - Test classification logic
  - Acceptance: 90%+ code coverage

- [ ] **TEST-102**: Integration tests for change workflow
  - Test change detection on save
  - Test notification flow
  - Acceptance: All tests pass

- [ ] **TEST-103**: E2E tests for change notification
  - Change ontology element
  - Verify notification appears
  - Verify affected MTs listed
  - Acceptance: Full workflow works

### Documentation

- [ ] **DOC-101**: Document change detection feature
  - Explain how it works
  - Show examples
  - Acceptance: Docs complete

## Phase 3: Smart Updates ⚡ Optional Enhancement

### Service Layer

- [ ] **SRV-201**: Create `MTReferenceUpdater` service class
  - File: `backend/services/mt_reference_updater.py`
  - Methods: update_references(), validate_update(), rollback()
  - Acceptance: Class exists, methods defined

- [ ] **SRV-202**: Implement IRI replacement logic
  - Parse MT triples
  - Replace old IRIs with new IRIs
  - Preserve triple structure
  - Acceptance: Correctly replaces IRIs

- [ ] **SRV-203**: Implement update validation
  - Validate against new ontology
  - Check for broken references
  - Acceptance: Correctly validates updates

- [ ] **SRV-204**: Implement rollback mechanism
  - Store original triples before update
  - Restore on failure
  - Acceptance: Rollback works correctly

### API Layer

- [ ] **API-201**: Create `POST /api/cqmt/microtheories/{mt_id}/update-references` endpoint
  - Input: change_mapping (old_iri → new_iri)
  - Updates MT triples
  - Returns update result
  - Acceptance: Endpoint works correctly

- [ ] **API-202**: Create batch update endpoint
  - Update multiple MTs at once
  - Track progress
  - Acceptance: Batch updates work

### Frontend Layer

- [ ] **UI-201**: Create update confirmation dialog
  - Shows what will be updated
  - Shows preview of changes
  - Acceptance: Dialog shows accurate preview

- [ ] **UI-202**: Create update progress indicator
  - Shows update progress
  - Handles errors gracefully
  - Acceptance: Progress indicator works

- [ ] **UI-203**: Add rollback UI
  - Allow user to undo failed updates
  - Acceptance: Rollback UI works

### Testing

- [ ] **TEST-201**: Unit tests for IRI replacement
  - Test various replacement scenarios
  - Test edge cases
  - Acceptance: 90%+ code coverage

- [ ] **TEST-202**: Integration tests for update workflow
  - Test successful updates
  - Test failed updates
  - Test rollback
  - Acceptance: All tests pass

- [ ] **TEST-203**: E2E tests for smart updates
  - Change ontology
  - Trigger update
  - Verify results
  - Acceptance: Full workflow works

### Documentation

- [ ] **DOC-201**: Document smart update feature
  - Explain how it works
  - Show examples
  - Acceptance: Docs complete

## Phase 4: Version Management ⚡ Future Enhancement

### Database Layer

- [ ] **DB-301**: Create ontology_version table
  - Track ontology versions
  - Store version metadata
  - Acceptance: Table exists

- [ ] **DB-302**: Create mt_version_binding table
  - Bind MTs to ontology versions
  - Acceptance: Table exists

### Service Layer

- [ ] **SRV-301**: Implement semantic versioning
  - Track major/minor/patch versions
  - Acceptance: Versioning works

- [ ] **SRV-302**: Implement version snapshots
  - Store ontology snapshots
  - Acceptance: Snapshots work

- [ ] **SRV-303**: Implement rollback to version
  - Restore previous ontology version
  - Acceptance: Rollback works

### API Layer

- [ ] **API-301**: Version management endpoints
  - GET /api/ontology/{graph_iri}/versions
  - POST /api/ontology/{graph_iri}/rollback
  - Acceptance: Endpoints work

### Testing

- [ ] **TEST-301**: Version management tests
  - Test versioning
  - Test rollback
  - Acceptance: Tests pass

## General Tasks (All Phases)

### Infrastructure

- [ ] **INFRA-001**: Set up monitoring for dependency tracking
  - Track dependency extraction performance
  - Monitor validation performance
  - Acceptance: Monitoring works

- [ ] **INFRA-002**: Set up error handling
  - Graceful degradation
  - Error logging
  - Acceptance: Errors handled gracefully

- [ ] **INFRA-003**: Performance optimization
  - Batch operations
  - Caching where appropriate
  - Acceptance: Performance acceptable

### Documentation

- [ ] **DOC-GEN-001**: Update CQMT feature guide
  - Add dependency tracking section
  - Add change detection section
  - Acceptance: Guide updated

- [ ] **DOC-GEN-002**: Create developer guide
  - Explain how it works internally
  - Include examples
  - Acceptance: Guide helps developers

- [ ] **DOC-GEN-003**: Create migration guide
  - Guide for updating existing MTs
  - Acceptance: Guide helps users

## Definition of Done

### For Each Task:
- [ ] Code written and reviewed
- [ ] Unit tests written and passing
- [ ] Integration tests written and passing
- [ ] Documentation updated
- [ ] No linter errors
- [ ] No security issues
- [ ] Performance acceptable

### For Each Phase:
- [ ] All tasks completed
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Demo recorded
- [ ] User feedback collected

## Estimated Effort

### Phase 1: Dependency Tracking
- **Effort**: 2-3 weeks
- **Team**: 1-2 developers
- **Risk**: Low

### Phase 2: Change Detection
- **Effort**: 2-3 weeks
- **Team**: 1-2 developers
- **Risk**: Low-Medium

### Phase 3: Smart Updates
- **Effort**: 3-4 weeks
- **Team**: 2 developers
- **Risk**: Medium-High

### Phase 4: Version Management
- **Effort**: 4-6 weeks
- **Team**: 2-3 developers
- **Risk**: High

## Priority Recommendation

1. **Phase 1** (Do first): Low risk, high value, foundation for everything else
2. **Phase 2** (Do second): Low-medium risk, high value, completes MVP
3. **Phase 3** (Defer): Higher risk, medium value, only if users request
4. **Phase 4** (Defer): High risk/complexity, align with org versioning strategy

## Success Criteria

### Phase 1 Success:
- All MTs have dependency records
- Validation API works correctly
- UI shows broken references
- Zero false positives

### Phase 2 Success:
- All ontology saves detect changes
- Users notified of affected MTs
- No performance degradation

### Phase 3 Success:
- Updates succeed >95% of the time
- No data loss
- Rollback works

### Phase 4 Success:
- Versioning works correctly
- Rollback successful
- No data corruption

## References

- Architectural Assessment: `docs/development/CQMT_ARCHITECTURAL_ASSESSMENT.md`
- Technical Analysis: `docs/development/CQMT_ONTOLOGY_SYNC_ISSUE.md`
- Quick Reference: `docs/development/CQMT_SYNC_QUICK_REFERENCE.md`
- Implementation Roadmap: `docs/development/CQMT_IMPLEMENTATION_ROADMAP.md`
- Master Summary: `docs/development/CQMT_SYNC_MASTER_SUMMARY.md`

---

**Remember**: This is completing standard industry infrastructure for a sound architecture. Not bandaids—professional practice.
