# CQMT Ontology Sync Issue - Quick Reference

## The Problem

```
┌─────────────────┐  SAVE ONTOLOGY     ┌─────────────────┐
│   Ontology      │ ───────────────→   │   Ontology      │
│   hasCapacity   │                     │   hasCapacity1  │
└─────────────────┘                     └─────────────────┘
                                                   
                                                   
┌─────────────────┐                     ┌─────────────────┐
│   Microtheory   │                     │   Microtheory   │
│   :hasCapacity  │ ──── STALE ────→   │   :hasCapacity  │ ❌
└─────────────────┘                     └─────────────────┘
     (references)                              (still old!)
```

**What Happens**: Test data in Microtheories doesn't update when ontology changes.

## Why It Happens

1. **Decoupled Storage**: Ontology and MTs stored separately
2. **String References**: MTs use IRIs as literal strings
3. **No Tracking**: System doesn't know what MTs depend on what ontology elements

## Impact

✅ **Real Problem**:
- CQ tests fail silently after ontology changes
- Test-Driven Development workflow breaks
- User confusion about "why did my test stop working?"

❌ **Not a Problem**:
- Static ontologies that never change
- Manual recreation of MTs after changes

## Solution Approach

### Phase 1: Track Dependencies (RECOMMENDED FIRST STEP)

**What**: Know which MTs reference which ontology elements

**How**:
1. Parse MT triples → extract IRIs
2. Store in `mt_ontology_dependencies` table
3. Validate periodically
4. Show warnings in UI

**Database Schema**:
```sql
CREATE TABLE mt_ontology_dependencies (
    mt_id UUID,
    referenced_element_iri TEXT,
    element_type VARCHAR(50),
    is_valid BOOLEAN
);
```

**Example**:
```python
# MT has these triples:
:C130 :hasCapacity "92 passengers" .

# System extracts:
{
    "mt_id": "uuid-123",
    "referenced_element_iri": "http://example.org/ontology#hasCapacity",
    "element_type": "DatatypeProperty",
    "is_valid": True
}
```

### Phase 2: Detect Changes

**What**: Notify user when ontology changes affect MTs

**How**:
1. On ontology save, detect changes
2. Query dependency table
3. Return: "3 MTs affected by this change"
4. Offer update option

**User Flow**:
```
Save Ontology → "2 MTs need updating" → [Update Now] [Later]
```

### Phase 3: Smart Update (Optional)

**What**: Automatically update MT references

**How**:
1. Map old IRI → new IRI
2. Replace in MT triples
3. Validate results
4. Commit updates

**Edge Cases**:
- Deleted element → "Review required"
- Renamed element → Auto-update
- Type changed → Warn user

## Implementation Checklist

### Database
- [ ] Create `mt_ontology_dependencies` table
- [ ] Add indexes
- [ ] Migration for existing MTs

### Services
- [ ] Dependency extraction from MT triples
- [ ] Validation against Fuseki
- [ ] Change detection on ontology save

### API
- [ ] `GET /microtheories/{id}/dependencies`
- [ ] `GET /microtheories/{id}/validation`
- [ ] `POST /microtheories/{id}/update-references`

### UI
- [ ] Warning badges on MT list
- [ ] Dependency panel in MT details
- [ ] Update confirmation dialog

### Testing
- [ ] Unit tests for parsing
- [ ] Integration tests for detection
- [ ] E2E tests for update flow

## Quick Decision Guide

**Should we implement this?**

- ✅ **YES** if: Users frequently rename ontology elements
- ✅ **YES** if: CQMT is heavily used for validation
- ✅ **YES** if: Silent test failures are confusing users
- ❌ **NO** if: Ontologies are static/rarely change
- ❌ **NO** if: Users manually manage MT updates

**Which phase?**

- **Phase 1** (recommended first): Add tracking and warnings
- **Phase 2**: Add change detection if Phase 1 shows high impact
- **Phase 3**: Add auto-update only if users request it

## Alternative: Defer

If not urgent:
1. Document best practices for MT management
2. Add warning messages in UI
3. Create manual validation tool
4. Monitor issue frequency

## References

- Full analysis: `docs/development/CQMT_ONTOLOGY_SYNC_ISSUE.md`
- CQMT spec: `docs/features/CQMT_WORKBENCH_SPECIFICATION.md`
- CQMT service: `backend/services/cqmt_service.py`
