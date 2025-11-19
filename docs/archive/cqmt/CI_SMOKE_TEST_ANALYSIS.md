# CI Smoke Test Analysis

## Current Status

### Local Status ✅
- Fast DAS validator **PASSES** locally (13.6s)
- All tests passing:
  - ✅ ODRAS connectivity
  - ✅ Authentication
  - ✅ DAS basic response
  - ✅ Ontology context
  - ✅ Rich attributes

### CI Status ⚠️
- Fast DAS validator **FAILING** in CI
- Need to investigate CI-specific issues

## Common CI Failure Causes

### 1. Namespace Availability 🔥 Likely Issue
**Problem**: Script requires released namespaces
```python
namespaces_response = requests.get(
    f"{self.base_url}/api/namespaces/released",
    ...
)
self.fast_fail_check(
    len(namespaces) > 0,
    "No released namespaces available"
)
```

**CI Issue**: Fresh database might not have namespaces
**Fix**: Make namespace creation part of `init-db` or handle missing namespaces gracefully

### 2. Timing Issues
**Problem**: 30s timeout for DAS responses
**CI Issue**: CI might be slower than local
**Fix**: Increase timeout or add retry logic

### 3. Service Startup Timing
**Problem**: Tests run immediately after services start
**CI Issue**: Services might not be fully ready
**Fix**: Add wait/health check before tests

### 4. Authentication Issues
**Problem**: Credentials not available
**CI Issue**: User creation might fail
**Fix**: Verify `init-db` creates users correctly

## Recommended Fixes

### Fix 1: Handle Missing Namespaces ✅ Quick
```python
# In create_test_project()
if len(namespaces) == 0:
    # Create a namespace if none exist
    self.log("No namespaces found, creating one...")
    # Create namespace logic here
```

### Fix 2: Add Retry Logic ✅ Quick
```python
def test_with_retry(self, test_func, max_retries=3):
    for i in range(max_retries):
        try:
            return test_func()
        except Exception as e:
            if i == max_retries - 1:
                raise
            self.log(f"Retry {i+1}/{max_retries}...")
            time.sleep(2)
```

### Fix 3: Increase Timeouts ⚠️ Quick
```python
# Change 30s to 60s for CI
timeout=60 if os.getenv("CI") else 30
```

## Investigation Needed

To fix the CI issue, we need to see the actual error. Can you share:
1. The CI failure logs
2. Which test fails
3. The error message

Once we have that, I can provide a targeted fix.

## Immediate Action

**Option 1**: Make smoke test more resilient (recommended)
- Handle missing namespaces
- Add retries
- Increase timeouts

**Option 2**: Skip smoke test temporarily
- Disable Step 1 in CI
- Focus on other tests
- Fix smoke test separately

**Option 3**: Make smoke test optional
- Only fail CI if critical issue
- Continue with other tests
- Log smoke test failure as warning

Which approach do you prefer?
