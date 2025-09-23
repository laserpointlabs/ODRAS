# How to Test the New Features<br>
<br>
## What We've Built<br>
<br>
We've added two major features to ODRAS:<br>
<br>
### 1. **User Tasks Tab** (from previous commit, already in main)<br>
- A new tab in the main UI showing pending user tasks<br>
- Red notification badge when tasks are pending<br>
- Auto-refreshes every 30 seconds<br>
<br>
### 2. **Requirements Review Interface** (just added)<br>
- A beautiful review page for approving/rejecting extracted requirements<br>
- Only appears when you navigate with specific parameters<br>
<br>
## How to Test Each Feature<br>
<br>
### Test 1: Check the User Tasks Tab<br>
1. Go to: **http://localhost:8000/**<br>
2. You should see 5 tabs:<br>
   - Upload & Process<br>
   - Personas<br>
   - Prompts<br>
   - Active Runs<br>
   - **User Tasks** ← NEW TAB (with potential red badge)<br>
<br>
### Test 2: Access the Requirements Review Interface<br>
<br>
The review interface is **ONLY** visible when you provide a taskId or process_instance_id parameter. Try these URLs:<br>
<br>
#### Option A: Direct Test URL<br>
```bash<br>
# Open this in your browser:<br>
http://localhost:8000/user-review?taskId=test123<br>
```<br>
<br>
#### Option B: Via curl to see the HTML<br>
```bash<br>
curl -s "http://localhost:8000/user-review?taskId=test123" | grep -o "Requirements Review" | head -1<br>
```<br>
<br>
#### Option C: Check what you see WITHOUT parameters (should be the normal interface)<br>
```bash<br>
# This shows the NORMAL interface (not the review interface)<br>
http://localhost:8000/user-review<br>
```<br>
<br>
### Test 3: See the Actual Review Interface<br>
<br>
Open your browser and go to:<br>
```<br>
http://localhost:8000/user-review?taskId=demo123<br>
```<br>
<br>
You should see:<br>
- **Gradient purple/blue background** (not the normal white page)<br>
- **"📋 Requirements Review"** header<br>
- **Task ID: demo123** in the top right<br>
- **Loading spinner** (since there's no real data)<br>
- **Three action buttons** at the bottom:<br>
  - ✅ Approve & Continue (green)<br>
  - 🔄 Rerun Extraction (orange)<br>
  - ✏️ Edit Requirements (blue, disabled)<br>
<br>
### Test 4: Test the Rerun Modal<br>
<br>
1. Go to: `http://localhost:8000/user-review?taskId=test`<br>
2. Wait for it to load (you'll see an error since there's no real task)<br>
3. Click the **"🔄 Rerun Extraction"** button<br>
4. A modal should pop up with:<br>
   - Extraction method dropdown<br>
   - Confidence threshold slider<br>
   - Custom patterns textarea<br>
   - Reason for rerun field<br>
<br>
### Test 5: Check the API Endpoints<br>
<br>
```bash<br>
# Check user tasks endpoint<br>
curl http://localhost:8000/api/user-tasks<br>
<br>
# Check requirements endpoint (will error without valid process ID, but endpoint exists)<br>
curl http://localhost:8000/api/user-tasks/test-process/requirements<br>
<br>
# Check complete endpoint (will error without valid process ID, but endpoint exists)<br>
curl -X POST http://localhost:8000/api/user-tasks/test-process/complete \<br>
  -H "Content-Type: application/json" \<br>
  -d '{"decision": "approve"}'<br>
```<br>
<br>
## Visual Comparison<br>
<br>
### Main Interface (http://localhost:8000/user-review)<br>
- White background<br>
- Shows "ODRAS - Ontology-Driven Requirements Analysis System"<br>
- Has form fields for uploading documents<br>
<br>
### Review Interface (http://localhost:8000/user-review?taskId=anything)<br>
- Purple gradient background<br>
- Shows "📋 Requirements Review"<br>
- Has requirement cards and action buttons<br>
- Completely different UI<br>
<br>
## Key Files Changed<br>
<br>
1. **backend/main.py**<br>
   - Added User Tasks tab<br>
   - Modified `/user-review` endpoint to check for parameters<br>
<br>
2. **backend/review_interface.py** (NEW)<br>
   - Complete review interface HTML/CSS/JS<br>
   - 900+ lines of beautiful UI code<br>
<br>
3. **bpmn/odras_requirements_analysis.bpmn**<br>
   - Fixed workflow to loop back after rerun/edit<br>
<br>
## Quick Verification Commands<br>
<br>
```bash<br>
# See the difference between the two interfaces:<br>
echo "=== Normal Interface (first 5 lines) ==="<br>
curl -s "http://localhost:8000/user-review" | head -5<br>
<br>
echo -e "\n=== Review Interface (first 5 lines) ==="<br>
curl -s "http://localhost:8000/user-review?taskId=test" | head -5<br>
<br>
# Count occurrences of unique elements<br>
echo -e "\n=== Checking for review-specific elements ==="<br>
curl -s "http://localhost:8000/user-review?taskId=test" | grep -c "review-container"<br>
curl -s "http://localhost:8000/user-review?taskId=test" | grep -c "approveRequirements"<br>
curl -s "http://localhost:8000/user-review?taskId=test" | grep -c "rerunModal"<br>
```<br>
<br>
## If You Don't See Changes<br>
<br>
1. **Make sure the server is running**:<br>
   ```bash<br>
   # The server should be running on port 8000<br>
   curl http://localhost:8000/<br>
   ```<br>
<br>
2. **Try a hard refresh** in your browser (Ctrl+F5 or Cmd+Shift+R)<br>
<br>
3. **Check the git diff** to see the actual code changes:<br>
   ```bash<br>
   git diff HEAD~1 backend/main.py<br>
   git diff HEAD~1 backend/review_interface.py<br>
   ```<br>
<br>
The main thing to remember: **The review interface only appears when you add `?taskId=something` to the URL!**<br>

