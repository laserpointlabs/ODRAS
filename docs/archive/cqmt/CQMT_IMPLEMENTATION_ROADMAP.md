# CQMT Sync Feature Implementation Roadmap

## Strategic Context

This document outlines the implementation plan for completing our CQMT architecture with standard supporting infrastructure. **This is not adding bandaids—it's completing the implementation of a sound architecture.**

## Current State

### ✅ What We Have (Solid Architecture)
- Named graphs for ontology storage
- Separate microtheories for test data
- SPARQL-based competency questions
- Proper separation of concerns
- Standard RDF/triple-based approach

### ❌ What We're Missing (Standard Infrastructure)
- Dependency tracking system
- Change detection mechanism
- Version management tooling
- Migration support utilities

## Implementation Phases

### Phase 1: Foundation - Dependency Tracking ⚡ MVP

**Goal**: Track which MTs reference which ontology elements

**Effort**: Medium (2-3 weeks)

**Database Changes**:
```sql
CREATE TABLE mt_ontology_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mt_id UUID REFERENCES microtheories(id) ON DELETE CASCADE,
    ontology_graph_iri TEXT NOT NULL,
    referenced_element_iri TEXT NOT NULL,
    element_type VARCHAR(50), -- 'Class', 'ObjectProperty', 'DatatypeProperty'
    first_detected_at TIMESTAMPTZ DEFAULT NOW(),
    last_validated_at TIMESTAMPTZ,
    is_valid BOOLEAN DEFAULT TRUE,
    UNIQUE(mt_id, referenced_element_iri)
);

CREATE INDEX idx_mt_deps_element ON mt_ontology_dependencies(referenced_element_iri);
CREATE INDEX idx_mt_deps_valid ON mt_ontology_dependencies(is_valid);
CREATE INDEX idx_mt_deps_mt ON mt_ontology_dependencies(mt_id);
```

**Service Layer**:
```python
class CQMTDependencyTracker:
    """Track dependencies between MTs and ontology elements"""
    
    def extract_dependencies(mt_iri: str) -> List[Dependency]:
        """Parse MT triples and extract referenced IRIs"""
        
    def validate_dependencies(mt_id: str) -> ValidationResult:
        """Check if all dependencies still exist in ontology"""
        
    def get_affected_mts(ontology_graph_iri: str, changed_element_iri: str) -> List[str]:
        """Find MTs that reference a changed element"""
```

**API Endpoints**:
```python
GET /api/cqmt/microtheories/{mt_id}/dependencies
GET /api/cqmt/microtheories/{mt_id}/validation
GET /api/cqmt/ontologies/{graph_iri}/impact-analysis
```

**UI Updates**:
- Badge on MT list showing validation status
- Dependency panel in MT details view
- "Dependencies" tab showing all referenced elements

**Testing**:
- Unit tests for parsing logic
- Integration tests for dependency extraction
- E2E tests for validation workflow

### Phase 2: Change Detection ⚡ Recommended Next

**Goal**: Detect when ontology changes affect MTs

**Effort**: Medium (2-3 weeks)

**Hook Into Ontology Save**:
```python
@router.post("/api/ontology/save")
async def save_ontology(...):
    """Save ontology and detect changes"""
    
    # After saving ontology
    changes = detect_changes(old_ontology, new_ontology)
    
    if changes:
        affected_mts = get_affected_microtheories(changes)
        
        return {
            "success": True,
            "changes": changes,
            "affected_mts": affected_mts,
            "notification": f"{len(affected_mts)} microtheories affected"
        }
```

**Change Detection Service**:
```python
class OntologyChangeDetector:
    """Detect changes between ontology versions"""
    
    def detect_changes(old_ttl: str, new_ttl: str) -> List[Change]:
        """Compare two ontology versions"""
        
    def classify_change(change: Change) -> ChangeImpact:
        """Classify as breaking/compatible/enhancement"""
```

**User Experience**:
```
User saves ontology with renamed property
  ↓
System: "This change affects 2 microtheories"
  [Show Details] [Update Now] [Later]
  ↓
User clicks "Show Details"
  ↓
Dialog: "MT 'Baseline' references 'hasCapacity'"
```

**Testing**:
- Unit tests for change detection
- Integration tests for affected MT discovery
- E2E tests for notification flow

### Phase 3: Smart Updates ⚡ Optional Enhancement

**Goal**: Automatically update MT references when ontology changes

**Effort**: High (3-4 weeks)

**Implementation**:
```python
class MTReferenceUpdater:
    """Update MT references when ontology changes"""
    
    def update_references(mt_id: str, change_mapping: Dict[str, str]) -> UpdateResult:
        """Replace old IRIs with new IRIs in MT triples"""
        
    def validate_update(mt_id: str) -> ValidationResult:
        """Validate updated MT against new ontology"""
```

**Update Flow**:
1. Parse change mapping (old_iri → new_iri)
2. For each affected MT:
   - Load all triples
   - Replace old IRIs with new IRIs
   - Validate against new ontology
   - Commit updates to Fuseki
3. Report results to user

**Edge Cases**:
- Deleted element → Mark MT as "needs review"
- Property type changed → Warn user
- Domain/range changed → Validate existing data
- Multiple references → Batch updates

**Testing**:
- Unit tests for IRI replacement
- Integration tests for update workflow
- E2E tests for complex change scenarios
- Rollback tests

### Phase 4: Version Management ⚡ Future Enhancement

**Goal**: Full versioning support per versioning strategy doc

**Effort**: Very High (4-6 weeks)

**Implementation**:
- Semantic versioning per ontology
- Version snapshots in Fuseki
- MT-to-version binding
- Rollback capabilities
- Change history tracking

**Note**: This phase aligns with `docs/ODRAS_Comprehensive_Versioning_Strategy.md`

## Recommended Timeline

### Quarter 1: Phase 1 (Dependency Tracking)
- Weeks 1-2: Database schema + service layer
- Weeks 2-3: API endpoints + UI updates
- Week 3: Testing + documentation

### Quarter 2: Phase 2 (Change Detection)
- Weeks 1-2: Change detection service
- Weeks 2-3: Integration + notifications
- Week 3: Testing + user feedback

### Quarter 3+: Phases 3-4 (Optional)
- Evaluate user feedback
- Prioritize based on needs
- Implement as needed

## Success Metrics

### Phase 1 Success Criteria
- ✅ All MTs have dependency records
- ✅ Validation API works correctly
- ✅ UI shows broken references
- ✅ Zero false positives in detection

### Phase 2 Success Criteria
- ✅ All ontology saves detect changes
- ✅ Users are notified of affected MTs
- ✅ Users can see what's affected
- ✅ No performance degradation

### Phase 3 Success Criteria
- ✅ Updates succeed >95% of the time
- ✅ No data loss during updates
- ✅ Users can rollback failed updates
- ✅ Edge cases handled gracefully

## Risk Assessment

### Phase 1: Low Risk ✅
- Read-only operations
- No data modifications
- Easy to rollback
- Well-tested patterns

### Phase 2: Low-Medium Risk ⚠️
- Change detection complexity
- Performance concerns
- False positive risk
- Mitigated by testing

### Phase 3: Medium-High Risk ⚠️⚠️
- Data modification risks
- Potential data loss
- Complex edge cases
- Requires extensive testing

### Phase 4: High Risk ⚠️⚠️⚠️
- Major architectural changes
- Complex versioning logic
- Performance implications
- Requires careful planning

## Decision Framework

**Should we implement Phase X?**

- **Phase 1**: Yes, if CQMT is actively used
- **Phase 2**: Yes, if Phase 1 shows high impact
- **Phase 3**: Only if users request it
- **Phase 4**: Only if versioning strategy is adopted org-wide

## Alternative: Defer Implementation

If not urgent:
1. Document best practices (complete)
2. Add warning messages in UI
3. Create manual validation tool
4. Monitor issue frequency
5. Re-evaluate in 3-6 months

## References

- Architectural Assessment: `docs/development/CQMT_ARCHITECTURAL_ASSESSMENT.md`
- Sync Issue Analysis: `docs/development/CQMT_ONTOLOGY_SYNC_ISSUE.md`
- Quick Reference: `docs/development/CQMT_SYNC_QUICK_REFERENCE.md`
- Versioning Strategy: `docs/ODRAS_Comprehensive_Versioning_Strategy.md`
- CQMT Spec: `docs/features/CQMT_WORKBENCH_SPECIFICATION.md`
