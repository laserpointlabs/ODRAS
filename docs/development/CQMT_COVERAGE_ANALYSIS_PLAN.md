# CQ/MT Coverage Analysis - Implementation Plan

## Problem Statement

Currently, the CQ/MT Workbench:
- ✅ Allows running individual CQs against specific MTs
- ✅ Stores run history in `cq_runs` table
- ❌ Does NOT systematically validate all CQs against all MTs
- ❌ Does NOT show comprehensive coverage metrics
- ❌ Shows only last run status per CQ (not per MT)

## Use Case: Why Test Every CQ Against Every MT?

**Scenario**: You have 3 CQs and 2 MTs:

```
CQs:
1. "List All Fighter Jets"
2. "List Operational Aircraft"
3. "List High-Capacity Transport"

MTs:
1. baseline-mt: Contains basic aircraft data
2. edge-cases-mt: Contains edge cases (decommissioned aircraft, etc.)
```

**Questions to Answer**:
- Does CQ1 work in both MTs? ✅ baseline (2 results) ✅ edge-cases (0 results) 
- Does CQ2 work in both MTs? ✅ baseline (10 results) ❌ edge-cases (crashes!)
- Does CQ3 work in both MTs? ✅ baseline (3 results) ✅ edge-cases (1 result)

**Key Insight**: Different MTs represent different scenarios. A CQ that passes against baseline might fail against edge cases, revealing ontology robustness issues.

## Current vs. Required Behavior

### Current Behavior
- CQ has `mt_iri_default` → runs against that MT only
- UI shows "last run status" → only shows one MT's result
- No systematic cross-MT testing

### Required Behavior
- **Coverage Tab** should show a matrix/grid:
  ```
  CQ                  | baseline-mt | edge-cases-mt | regression-mt
  --------------------|------------|---------------|---------------
  List Fighter Jets   | ✅ PASS (2) | ✅ PASS (0)   | ❌ FAIL (0)
  Operational Aircraft| ✅ PASS (10)| ❌ FAIL (err) | ✅ PASS (8)
  High-Capacity Trans | ✅ PASS (3) | ✅ PASS (1)  | ⚠️ NO RUN
  ```

## Implementation Plan

### Phase 1: Backend Coverage API ✅ EASY

#### New Endpoint: `GET /api/cqmt/projects/{project_id}/coverage`

**Returns**: Complete coverage matrix

```json
{
  "cqs": [
    {
      "id": "cq-uuid-1",
      "name": "List Fighter Jets",
      "runs_by_mt": {
        "baseline-mt": {
          "status": "pass",
          "row_count": 2,
          "last_run": "2024-10-22T14:30:00Z"
        },
        "edge-cases-mt": {
          "status": "pass",
          "row_count": 0,
          "last_run": "2024-10-22T15:00:00Z"
        }
      }
    }
  ],
  "mts": [
    {"iri": "baseline-mt", "label": "Baseline Data"},
    {"iri": "edge-cases-mt", "label": "Edge Cases"}
  ],
  "summary": {
    "total_cqs": 3,
    "total_mts": 2,
    "total_possible_runs": 6,
    "runs_completed": 5,
    "pass_rate": 0.83,
    "coverage_percentage": 83.3
  }
}
```

**Implementation**:
```python
def get_coverage_matrix(project_id: str) -> Dict[str, Any]:
    # Get all CQs
    cqs = self.get_cqs(project_id)
    
    # Get all MTs
    mts = self.get_microtheories(project_id)
    
    # For each CQ, find last run for each MT
    coverage = []
    for cq in cqs:
        runs_by_mt = {}
        for mt in mts:
            # Get last run for this CQ+MT combination
            last_run = self.db.execute("""
                SELECT pass, row_count, created_at, reason
                FROM cq_runs
                WHERE cq_id = %s AND mt_iri = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (cq['id'], mt['iri']))
            
            if last_run:
                runs_by_mt[mt['iri']] = {
                    "status": "pass" if last_run[0] else "fail",
                    "row_count": last_run[1],
                    "last_run": last_run[2].isoformat(),
                    "reason": last_run[3]
                }
        
        coverage.append({
            "id": cq['id'],
            "name": cq['cq_name'],
            "runs_by_mt": runs_by_mt
        })
    
    return {
        "cqs": coverage,
        "mts": mts,
        "summary": calculate_summary(coverage, mts)
    }
```

### Phase 2: Frontend Coverage Grid ✅ MODERATE

**UI Component**: Coverage grid/table

```html
<div id="coverage-grid">
  <h3>CQ Coverage Matrix</h3>
  <p>Shows latest run results for each CQ against each MT</p>
  
  <table class="coverage-table">
    <thead>
      <tr>
        <th>CQ Name</th>
        <th>baseline-mt</th>
        <th>edge-cases-mt</th>
        <th>regression-mt</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>List Fighter Jets</td>
        <td class="pass">✅ PASS (2 rows)</td>
        <td class="pass">✅ PASS (0 rows)</td>
        <td class="fail">❌ FAIL - missing_columns</td>
      </tr>
      <tr>
        <td>Operational Aircraft</td>
        <td class="pass">✅ PASS (10 rows)</td>
        <td class="fail">❌ FAIL - query error</td>
        <td class="no-run">⚠️ No run</td>
      </tr>
    </tbody>
  </table>
</div>
```

**Features**:
- Click any cell to see full run details
- "Run All CQs Against All MTs" button for batch execution
- Sortable/filterable table
- Export to CSV

### Phase 3: Batch Execution ✅ ADVANCED

**New Endpoint**: `POST /api/cqmt/projects/{project_id}/run-all`

**Purpose**: Run all CQs against all MTs systematically

**Request**:
```json
{
  "cq_ids": ["cq-uuid-1", "cq-uuid-2"],  // Optional: specific CQs
  "mt_iris": ["mt-uuid-1", "mt-uuid-2"], // Optional: specific MTs
  "force_rerun": false  // Re-run even if recent run exists
}
```

**Response**: Job ID for async execution

**Implementation**:
- Create background job (Celery/simple worker)
- For each CQ+MT combo, run CQ execution
- Store results in `cq_runs` table
- Publish progress events
- Update coverage matrix incrementally

### Phase 4: UI Enhancements ✅ FUTURE

1. **Visual Coverage Indicators**:
   - Green/yellow/red cells based on pass/fail/no-run
   - Row-wise pass rate percentage
   - Column-wise (MT) pass rate percentage

2. **Trend Analysis**:
   - Show how coverage changes over time
   - Chart: pass rate over time per MT

3. **Gap Analysis**:
   - Highlight CQs with no runs against certain MTs
   - Suggest "Run missing tests" action

4. **Filters**:
   - Filter by MT
   - Filter by CQ status
   - Filter by last run date

## Testing Strategy

### Test Case 1: Empty Coverage Matrix
- No CQs created yet
- API returns empty matrix with 0% coverage

### Test Case 2: Partial Coverage
- 3 CQs, 2 MTs
- Only some combinations have runs
- Shows missing runs as "⚠️ No run"

### Test Case 3: Full Coverage
- All CQs run against all MTs
- Shows 100% coverage
- All cells have status

### Test Case 4: Failure Detection
- CQ passes in MT1, fails in MT2
- Grid shows both statuses
- User can see failure reason

## Success Criteria

1. ✅ Coverage API returns complete matrix
2. ✅ UI displays grid with all CQ×MT combinations
3. ✅ Batch execution runs all tests systematically
4. ✅ Failed runs show detailed error messages
5. ✅ Missing runs clearly indicated
6. ✅ Coverage percentage calculated correctly

## Questions to Resolve

1. **Performance**: What if 100 CQs × 20 MTs = 2000 runs?
   - Answer: Batch execution is async, API returns cached results quickly

2. **Staleness**: When is data considered stale?
   - Answer: Show "last run" timestamp, let user decide

3. **Auto-run**: Should CQs auto-run when MT data changes?
   - Answer: Feature request, not MVP

4. **Cloning**: If I clone an MT, should I re-run all CQs?
   - Answer: Not automatic, but button available

## Next Steps

1. ✅ Document the problem (this document)
2. ⏳ Implement Phase 1: Coverage API
3. ⏳ Implement Phase 2: Coverage Grid UI
4. ⏳ Test with existing CQ/MT data
5. ⏳ Implement Phase 3: Batch Execution
6. ⏳ Add visual indicators and filters

## Related Documents

- [CQMT Workbench Specification](../features/CQMT_WORKBENCH_SPECIFICATION.md)
- [CQMT TODO List](cqmt_workbench_todo.md)
- [SPARQL Query Builder Plan](CQMT_SPARQL_QUERY_BUILDER_PLAN.md)
