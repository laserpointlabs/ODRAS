# How to Test the New Features

## What We've Built

We've added two major features to ODRAS:

### 1. **User Tasks Tab** (from previous commit, already in main)
- A new tab in the main UI showing pending user tasks
- Red notification badge when tasks are pending
- Auto-refreshes every 30 seconds

### 2. **Requirements Review Interface** (just added)
- A beautiful review page for approving/rejecting extracted requirements
- Only appears when you navigate with specific parameters

## How to Test Each Feature

### Test 1: Check the User Tasks Tab
1. Go to: **http://localhost:8000/**
2. You should see 5 tabs:
   - Upload & Process
   - Personas
   - Prompts
   - Active Runs
   - **User Tasks** ← NEW TAB (with potential red badge)

### Test 2: Access the Requirements Review Interface

The review interface is **ONLY** visible when you provide a taskId or process_instance_id parameter. Try these URLs:

#### Option A: Direct Test URL
```bash
# Open this in your browser:
http://localhost:8000/user-review?taskId=test123
```

#### Option B: Via curl to see the HTML
```bash
curl -s "http://localhost:8000/user-review?taskId=test123" | grep -o "Requirements Review" | head -1
```

#### Option C: Check what you see WITHOUT parameters (should be the normal interface)
```bash
# This shows the NORMAL interface (not the review interface)
http://localhost:8000/user-review
```

### Test 3: See the Actual Review Interface

Open your browser and go to:
```
http://localhost:8000/user-review?taskId=demo123
```

You should see:
- **Gradient purple/blue background** (not the normal white page)
- **"📋 Requirements Review"** header
- **Task ID: demo123** in the top right
- **Loading spinner** (since there's no real data)
- **Three action buttons** at the bottom:
  - ✅ Approve & Continue (green)
  - 🔄 Rerun Extraction (orange)
  - ✏️ Edit Requirements (blue, disabled)

### Test 4: Test the Rerun Modal

1. Go to: `http://localhost:8000/user-review?taskId=test`
2. Wait for it to load (you'll see an error since there's no real task)
3. Click the **"🔄 Rerun Extraction"** button
4. A modal should pop up with:
   - Extraction method dropdown
   - Confidence threshold slider
   - Custom patterns textarea
   - Reason for rerun field

### Test 5: Check the API Endpoints

```bash
# Check user tasks endpoint
curl http://localhost:8000/api/user-tasks

# Check requirements endpoint (will error without valid process ID, but endpoint exists)
curl http://localhost:8000/api/user-tasks/test-process/requirements

# Check complete endpoint (will error without valid process ID, but endpoint exists)
curl -X POST http://localhost:8000/api/user-tasks/test-process/complete \
  -H "Content-Type: application/json" \
  -d '{"decision": "approve"}'
```

## Visual Comparison

### Main Interface (http://localhost:8000/user-review)
- White background
- Shows "ODRAS - Ontology-Driven Requirements Analysis System"
- Has form fields for uploading documents

### Review Interface (http://localhost:8000/user-review?taskId=anything)
- Purple gradient background
- Shows "📋 Requirements Review"
- Has requirement cards and action buttons
- Completely different UI

## Key Files Changed

1. **backend/main.py**
   - Added User Tasks tab
   - Modified `/user-review` endpoint to check for parameters

2. **backend/review_interface.py** (NEW)
   - Complete review interface HTML/CSS/JS
   - 900+ lines of beautiful UI code

3. **bpmn/odras_requirements_analysis.bpmn**
   - Fixed workflow to loop back after rerun/edit

## Quick Verification Commands

```bash
# See the difference between the two interfaces:
echo "=== Normal Interface (first 5 lines) ==="
curl -s "http://localhost:8000/user-review" | head -5

echo -e "\n=== Review Interface (first 5 lines) ==="
curl -s "http://localhost:8000/user-review?taskId=test" | head -5

# Count occurrences of unique elements
echo -e "\n=== Checking for review-specific elements ==="
curl -s "http://localhost:8000/user-review?taskId=test" | grep -c "review-container"
curl -s "http://localhost:8000/user-review?taskId=test" | grep -c "approveRequirements"
curl -s "http://localhost:8000/user-review?taskId=test" | grep -c "rerunModal"
```

## If You Don't See Changes

1. **Make sure the server is running**:
   ```bash
   # The server should be running on port 8000
   curl http://localhost:8000/
   ```

2. **Try a hard refresh** in your browser (Ctrl+F5 or Cmd+Shift+R)

3. **Check the git diff** to see the actual code changes:
   ```bash
   git diff HEAD~1 backend/main.py
   git diff HEAD~1 backend/review_interface.py
   ```

The main thing to remember: **The review interface only appears when you add `?taskId=something` to the URL!**
