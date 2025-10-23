# CI Smoke Test Fix Proposal

## Problem Analysis

The fast DAS validator requires **released namespaces** to create a test project, but CI might not have any.

### Current Code Flow
```python
# In fast_das_validator.py create_test_project()
namespaces_response = requests.get(
    f"{self.base_url}/api/namespaces/released",
    ...
)
self.fast_fail_check(
    len(namespaces) > 0,
    "No released namespaces available"  # FAILS HERE
)
```

### Root Cause
Schema initializes namespaces at lines 637-640, but:
- Might not run in CI (on conflict do nothing)
- Namespaces might not have 'released' status
- Versions might not be created

## Fix Options

### Option 1: Make Test Resilient ✅ Recommended
**Change**: Handle missing namespaces gracefully
**Effort**: 15 minutes
**Impact**: Test always works

```python
def create_test_project(self):
    """Create a test project dynamically"""
    self.log("Creating test project...")
    
    try:
        # Get available namespaces
        namespaces_response = requests.get(
            f"{self.base_url}/api/namespaces/released",
            headers={"Authorization": f"Bearer {self.auth_token}"},
            timeout=5
        )
        
        namespaces = []
        if namespaces_response.status_code == 200:
            namespaces = namespaces_response.json()
        
        # If no namespaces, create one
        if len(namespaces) == 0:
            self.log("No released namespaces found, creating test namespace...")
            namespace_id = self.create_test_namespace()
        else:
            namespace_id = namespaces[0]["id"]
        
        # Rest of project creation...
```

### Option 2: Ensure Namespaces in CI ✅ Quick
**Change**: Force namespace creation in init-db
**Effort**: 5 minutes
**Impact**: CI always has namespaces

```sql
-- In odras_schema.sql
INSERT INTO namespace_registry (...) VALUES (...)
ON CONFLICT (name, type) DO UPDATE SET status = 'released';
```

### Option 3: Skip Namespace Requirement ✅ Quick
**Change**: Make namespace optional for test projects
**Effort**: 10 minutes
**Impact**: Test works without namespaces

## Recommendation

**Implement Option 1 + Option 2**

1. **Fix the test** to handle missing namespaces (5 lines)
2. **Fix the schema** to ensure namespaces are released (1 line)

This ensures:
- Test works in all environments
- CI has proper data
- No regressions

## Implementation

Want me to implement this fix?
