# Save to Disk - Complete Technical Flow

## Overview

This document explains exactly how the Lattice Demo saves files to `.odras/demo/` when running in the Desktop Environment extension.

## The Three Layers

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Iframe (Lattice Demo)                             │
│ - Runs at: http://localhost:8082/intelligent_lattice_demo.html │
│ - Has: Generated lattice data in memory                    │
│ - Can: Send messages to parent via window.parent.postMessage() │
│ - Cannot: Access file system directly                      │
└─────────────────────────────────────────────────────────────┘
                            ↓ postMessage
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Desktop Webview (VS Code Webview Panel)           │
│ - Runs at: vscode.ViewColumn.One                           │
│ - Has: window.addEventListener('message') to receive       │
│ - Can: Forward messages to extension via vscode.postMessage() │
│ - Cannot: Access file system directly                      │
└─────────────────────────────────────────────────────────────┘
                            ↓ vscode.postMessage
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Extension Host (Node.js/TypeScript)               │
│ - Runs at: VS Code Extension Host process                  │
│ - Has: webview.onDidReceiveMessage() handler               │
│ - Can: Use Node.js fs module to write files                │
│ - Has: Full file system access                             │
└─────────────────────────────────────────────────────────────┘
                            ↓ fs.writeFileSync
┌─────────────────────────────────────────────────────────────┐
│ File System: .odras/demo/*.json                             │
└─────────────────────────────────────────────────────────────┘
```

## Step-by-Step Code Execution

### Step 1: User Clicks Save Button

**File**: `scripts/demo/static/intelligent_lattice_demo.html:819`
```html
<button class="btn" id="saveResultsBtn" style="display: none;">💾 Save Results</button>
```

**Event Handler**: `scripts/demo/static/intelligent_lattice.js:187-189`
```javascript
document.getElementById('saveResultsBtn')?.addEventListener('click', () => {
    this.saveResults();
});
```

### Step 2: Demo Prepares Data

**File**: `scripts/demo/static/intelligent_lattice.js:2345-2357`
```javascript
saveResults() {
    if (!this.currentLattice) {
        alert('No lattice generated yet. Please generate a lattice first.');
        return;
    }
    
    const data = {
        lattice: this.currentLattice,
        projects: this.createdProjects || [],
        registry: this.projectRegistry || {},
        workflowHistory: this.workflowHistory || [],
        llmAuditTrail: this.llmAuditTrail || []
    };
    // ... continues below
}
```

### Step 3: Demo Sends Message to Parent Webview

**File**: `scripts/demo/static/intelligent_lattice.js:2372-2376`
```javascript
// Check if vscode API is available (when embedded directly in VS Code webview)
if (typeof vscode !== 'undefined' && vscode) {
    // This path is NOT used in desktop environment (no vscode API in iframe)
}

// Fallback: Try iframe communication (THIS PATH IS USED)
if (window.parent && window.parent !== window) {
    // We're in an iframe - send message to parent (desktop webview)
    window.parent.postMessage({
        source: 'lattice-demo-iframe',  // ← CRITICAL: Identifies sender
        command: 'saveLattice',         // ← CRITICAL: Tells extension what to do
        data: data                      // ← CRITICAL: The actual lattice data
    }, '*');  // ← '*' = any origin (required for cross-origin postMessage)
    
    this.updateAnalysisStatus('💾 Saving to .odras/demo/...');
    return;
}
```

**Why `'*'` origin?**
- Iframe is at `http://localhost:8082`
- Parent webview is at `vscode-webview://...`
- Different origins, so we use `'*'` to allow the message

### Step 4: Desktop Webview Receives Message

**File**: `desktop-environment-extension/src/extension.ts:407-415` (in getDesktopHTML)
```javascript
// Listen for messages from iframe
window.addEventListener('message', (event) => {
    if (event.data && event.data.source === 'lattice-demo-iframe') {
        // Forward to extension host
        vscode.postMessage({
            command: event.data.command,  // 'saveLattice'
            data: event.data.data         // The lattice data
        });
    }
});
```

**Key Point**: The desktop webview acts as a **message forwarder**. It doesn't process the data, just passes it along.

### Step 5: Extension Host Receives Message

**File**: `desktop-environment-extension/src/extension.ts:49-76`
```typescript
this.desktopPanel.webview.onDidReceiveMessage(
    async (message) => {
        switch (message.command) {
            case 'getDesktopIcons':
                // ... other cases ...
                break;
            case 'saveLattice':
                await this.saveLatticeToFile(message.data);
                break;
            case 'folderWindowMessage':
                // ... other cases ...
                break;
        }
    },
    undefined,
    this.context.subscriptions
);
```

### Step 6: Extension Writes Files to Disk

**File**: `desktop-environment-extension/src/extension.ts:204-236`
```typescript
private async saveLatticeToFile(data: any) {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders || workspaceFolders.length === 0) {
        vscode.window.showErrorMessage('No workspace folder open');
        return;
    }

    const workspaceRoot = workspaceFolders[0].uri.fsPath;
    const odrasDemoDir = path.join(workspaceRoot, '.odras', 'demo');
    
    // Create directory if it doesn't exist
    if (!fs.existsSync(odrasDemoDir)) {
        fs.mkdirSync(odrasDemoDir, { recursive: true });
    }

    // Save files
    const files = [
        { name: 'lattice.json', data: data.lattice },
        { name: 'projects.json', data: data.projects },
        { name: 'registry.json', data: data.registry },
        { name: 'workflow-history.json', data: data.workflowHistory },
        { name: 'llm-audit-trail.json', data: data.llmAuditTrail }
    ];

    for (const file of files) {
        if (file.data !== undefined && file.data !== null) {
            const filePath = path.join(odrasDemoDir, file.name);
            fs.writeFileSync(filePath, JSON.stringify(file.data, null, 2), 'utf8');
        }
    }

    vscode.window.showInformationMessage('✅ Saved lattice data to .odras/demo/');
}
```

### Step 7: User Sees Confirmation

**VS Code Notification**: "✅ Saved lattice data to .odras/demo/"

**Files Created**:
```
.odras/demo/
├── lattice.json           (Project structure, data flows, analysis)
├── projects.json          (Created projects with IDs)
├── registry.json          (Project name → ID mapping)
├── workflow-history.json  (Complete workflow steps)
└── llm-audit-trail.json   (LLM interactions for debugging)
```

## Why Each Layer is Necessary

### Why Not: Direct File Access from Iframe?
**Browser security prevents file system access.**
- Iframes are sandboxed
- No direct access to Node.js APIs
- `fs.writeFileSync()` not available

### Why Not: Skip Desktop Webview (Iframe → Extension Direct)?
**Iframes can't directly communicate with extension host.**
- No `vscode.postMessage()` API available in iframe
- Only available in the webview that owns the iframe
- Must go through parent webview

### Why Not: Embed Demo HTML Directly (No Iframe)?
**External scripts won't load reliably.**
- VS Code webview CSP is very restrictive
- External scripts (Cytoscape) get blocked
- Network requests to localhost:8083 get blocked
- Script execution order becomes unpredictable

## Message Data Structure

### From Demo to Desktop Webview

```javascript
{
    source: 'lattice-demo-iframe',  // String identifier
    command: 'saveLattice',         // String command name
    data: {                         // Object with all data
        lattice: {                  // Main lattice structure
            analysis_summary: string,
            confidence: number,
            data_flows: array,
            projects: array,
            relationships: array
        },
        projects: array,            // Created ODRAS projects
        registry: object,           // Name → ID mapping
        workflowHistory: array,     // Workflow steps
        llmAuditTrail: array        // LLM interactions
    }
}
```

### From Desktop Webview to Extension Host

```javascript
{
    command: 'saveLattice',  // String command name
    data: {                  // Same object as above
        lattice: { ... },
        projects: [ ... ],
        registry: { ... },
        workflowHistory: [ ... ],
        llmAuditTrail: [ ... ]
    }
}
```

**Note**: The `source` field is stripped by the desktop webview before forwarding. The extension host only sees `command` and `data`.

## Security Considerations

### 1. Origin Validation

**Current**: Uses `source: 'lattice-demo-iframe'` to identify messages.

**Risk**: Any iframe could send messages with this source.

**Mitigation**:
- Extension only loads trusted iframes (localhost)
- Desktop environment is single-user (not multi-tenant)
- For production: validate iframe origin (`event.origin`)

### 2. Data Validation

**Current**: Writes data directly to files without validation.

**Risk**: Malicious data could corrupt files or fill disk.

**Mitigation**:
- Add data structure validation before saving
- Limit file sizes (e.g., max 10MB per file)
- Validate JSON structure matches expected schema
- Add error handling for write failures

### 3. Path Traversal

**Current**: Uses fixed path `.odras/demo/` + known filenames.

**Risk**: Low (no user input in paths).

**If accepting user paths in future**:
- Use `path.normalize()` and `path.resolve()`
- Check that resolved path is within workspace
- Reject paths with `..` or absolute paths

## Performance Considerations

### Message Size

**Current**: Entire lattice data (can be 100KB+) in single message.

**Works for**: Lattices with <100 projects.

**May fail for**: Very large lattices (1000+ projects).

**Solution if needed**:
- Chunk data into smaller messages
- Save files individually via separate messages
- Stream data instead of bulk transfer

### Memory Usage

**Current**: All data held in memory during transfer.

**Acceptable for**: Normal use (MB of data).

**Solution if needed**:
- Use IndexedDB in iframe to stage data
- Transfer in smaller chunks
- Compress data before transfer

## Debugging Tips

### Enable Message Logging

Add to demo JavaScript:
```javascript
window.parent.postMessage({
    source: 'lattice-demo-iframe',
    command: 'saveLattice',
    data: data
}, '*');
console.log('Sent save message with', Object.keys(data).length, 'keys');
```

Add to desktop webview:
```javascript
window.addEventListener('message', (event) => {
    console.log('Received message:', event.data);
    if (event.data && event.data.source === 'lattice-demo-iframe') {
        vscode.postMessage({
            command: event.data.command,
            data: event.data.data
        });
        console.log('Forwarded to extension host');
    }
});
```

Add to extension host:
```typescript
case 'saveLattice':
    console.log('Extension received save request');
    await this.saveLatticeToFile(message.data);
    console.log('Files saved successfully');
    break;
```

### Check File Creation

```bash
# Watch for file changes
watch -n 1 ls -lah .odras/demo/

# Check file contents
cat .odras/demo/lattice.json | jq '.projects | length'

# Verify all files exist
ls -1 .odras/demo/
```

## Known Working Configuration

- **VS Code**: 1.80.0+
- **Node.js**: 18.x+
- **TypeScript**: 5.0.0+
- **Demo Server**: Python 3 SimpleHTTPServer on port 8082
- **LLM Server**: Port 8083 (for lattice generation)
- **ODRAS API**: Port 8000 (for project creation)

## Testing the Save Flow

```bash
# 1. Start demo server
cd scripts/demo
./demo.sh start

# 2. Press F5 in Cursor to launch extension

# 3. In Extension Development Host window:
#    - Double-click "Lattice Demo" icon
#    - Click "Load Example" (or generate with custom requirements)
#    - Click "🧠 Generate Intelligent Lattice"
#    - Wait for generation to complete
#    - Click "💾 Save Results"

# 4. Check files were created:
ls -lah .odras/demo/

# 5. Verify content:
cat .odras/demo/lattice.json | jq '.analysis_summary'
```

## What Could Go Wrong

1. **Workspace not open**: Extension shows error, can't save
2. **Demo server not running**: White screen, can't load demo
3. **Message not forwarded**: Desktop webview listener not set up
4. **Permission denied**: `.odras/demo/` folder can't be created
5. **Data is null**: Empty files created (check file.data validation)
6. **Message lost**: Timing issue (listener not ready when message sent)

## Recovery Steps

If save isn't working:

1. **Check workspace**: Ensure ODRAS folder is open in VS Code
2. **Check demo server**: `curl http://localhost:8082/intelligent_lattice_demo.html`
3. **Check extension logs**: Look for errors in Extension Development Host
4. **Check message flow**: Add console.log at each layer
5. **Check file permissions**: Ensure `.odras/demo/` is writable
6. **Restart extension**: Reload Extension Development Host window
7. **Clear state**: Delete `.odras/demo/` and try again

## Success Indicators

✅ User clicks "💾 Save Results"
✅ Status changes to "💾 Saving to .odras/demo/..."
✅ VS Code notification appears: "✅ Saved lattice data to .odras/demo/"
✅ Files exist in `.odras/demo/` folder
✅ Files contain JSON data (not empty)
✅ All 5 files created (lattice, projects, registry, workflow-history, llm-audit-trail)
✅ File sizes are reasonable (>100 bytes each)

## Conclusion

The iframe + postMessage + extension host pattern is **the right approach** for desktop-like applications in VS Code that need file system access. It's:

- **Simple**: Clear separation of concerns
- **Secure**: Proper sandboxing at each layer
- **Reliable**: Uses standard web APIs
- **Maintainable**: Easy to understand and debug
- **Extensible**: Can add more applications easily

Don't try to embed HTML directly or bypass iframes. The three-layer message passing is necessary and works reliably.
