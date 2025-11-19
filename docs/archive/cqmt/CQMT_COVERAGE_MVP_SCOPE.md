# CQ/MT Coverage Analysis - MVP Scope

## Decision: ✅ Include Basic Coverage in MVP

**Rationale**: Coverage analysis is core to understanding MT effectiveness. Without it, users can't see if CQs work across different MTs.

## MVP Scope (Minimal Implementation)

### Must Have
1. **Coverage API** (~50 lines backend)
   - Endpoint: `GET /api/cqmt/projects/{project_id}/coverage`
   - Query existing `cq_runs` table
   - Return matrix of last run per CQ×MT combination
   - No new tables, no complex logic

2. **Coverage Grid UI** (~100 lines frontend)
   - Simple HTML table showing CQ rows × MT columns
   - Pass/Fail/No-Run indicators
   - Click cell to see details
   - Existing Coverage tab placeholder → populate with grid

### Defer to Post-MVP
- ❌ Batch execution ("Run All Tests" button)
- ❌ Auto-execution on MT changes
- ❌ Trend analysis / charts
- ❌ Gap analysis suggestions
- ❌ Export to CSV
- ❌ Advanced filters

## Implementation Estimate

**Backend**: 2-3 hours
- Add `get_coverage_matrix()` method to `CQMTService`
- Query `cq_runs` table with GROUP BY cq_id, mt_iri
- Return JSON matrix

**Frontend**: 2-3 hours
- Update Coverage tab HTML
- JavaScript to render grid from API response
- Basic CSS for table styling

**Total**: ~5-6 hours for MVP coverage

## User Experience

**Before**: "My CQ passed, but I don't know if it works in other MTs"

**After**: 
```
Coverage Tab:
┌────────────────────┬──────────────┬──────────────┐
│ CQ Name            │ baseline-mt  │ edge-cases-mt│
├────────────────────┼──────────────┼──────────────┤
│ List Fighter Jets  │ ✅ PASS (2)  │ ⚠️ NO RUN   │
│ Operational Aircraft│ ✅ PASS (10)│ ❌ FAIL (err)│
└────────────────────┴──────────────┴──────────────┘
```

User can see gaps, click failed cells to debug, manually run missing tests.

## Decision: ✅ Go Ahead

This is essential for CQ/MT to deliver on its promise of "test-driven ontology development". Without it, users can't systematically validate ontologies.

## Action Items

1. ✅ Document MVP scope (this document)
2. ⏳ Implement `get_coverage_matrix()` backend method
3. ⏳ Add API endpoint
4. ⏳ Build frontend grid
5. ⏳ Test with existing data
6. ⏳ Defer advanced features to roadmap

## Success Criteria

- User can see which CQs pass/fail in which MTs
- Gaps are visible (no-run cells)
- Total coverage percentage shown
- Clicking cells shows run details
- Works with existing data (no migration needed)
