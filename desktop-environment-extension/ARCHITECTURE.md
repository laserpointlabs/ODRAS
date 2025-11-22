# Desktop Environment Extension - Architecture

## Overview

This extension creates a desktop-like environment within VS Code, allowing users to open applications (like the Lattice Demo) in draggable windows and save files directly to the workspace.

## How It Works

### Core Components

1. **Desktop Webview Panel** (`DesktopEnvironment.createDesktop()`)
   - Single VS Code webview panel that acts as the desktop
   - Shows icons for folders and applications
   - Manages all application windows within this single webview
   - Lives at: `vscode.ViewColumn.One`

2. **Application Windows** (inside Desktop Webview)
   - Created as `<div>` elements with class `.window`
   - Each window contains an `<iframe>` that loads the application
   - Windows are draggable via the titlebar
   - Z-index management for bring-to-front

3. **File System Access** (Extension Host)
   - Extension host has full Node.js file system access
   - Can read/write to `.odras/demo/` folder directly
   - No browser security restrictions

## Iframe Approach (The Key to Making This Work)

### Why Iframes?

We use iframes to load applications (like the Lattice Demo) because:

1. **Isolation**: Each application runs in its own sandboxed iframe
2. **Network Requests**: The app can make fetch requests to localhost:8083 (LLM service)
3. **External Scripts**: CDN scripts (like Cytoscape) load normally
4. **Simplicity**: The app works exactly as it does standalone

### Iframe Configuration

```html
<iframe 
    id="${windowId}-iframe" 
    src="http://localhost:8082/intelligent_lattice_demo.html"
    sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-modals"
    style="width: 100%; height: 100%; border: none;">
</iframe>
```

**Sandbox Attributes:**
- `allow-same-origin`: Allows postMessage communication
- `allow-scripts`: JavaScript can run
- `allow-forms`: Form inputs work
- `allow-popups`: Alerts and modals work
- `allow-modals`: Modal dialogs work

### CSP (Content Security Policy)

The desktop webview has CSP headers to allow iframe loading:

```html
<meta http-equiv="Content-Security-Policy" 
      content="default-src 'none'; 
               script-src 'unsafe-inline'; 
               style-src 'unsafe-inline'; 
               frame-src http://localhost:8082 http://localhost:8083;">
```

**Key parts:**
- `frame-src http://localhost:8082`: Allows loading demo in iframe
- `frame-src http://localhost:8083`: Allows LLM service iframes if needed
- `script-src 'unsafe-inline'`: Allows inline JavaScript in desktop
- `style-src 'unsafe-inline'`: Allows inline CSS

## Save to Disk - Message Chain

### The Complete Flow

```
1. User clicks "💾 Save Results" in Lattice Demo
   ↓
2. Demo calls: window.parent.postMessage({
       source: 'lattice-demo-iframe',
       command: 'saveLattice',
       data: { lattice, projects, registry, ... }
   }, '*')
   ↓
3. Desktop webview receives message (event listener on window)
   ↓
4. Desktop webview forwards to Extension Host:
   vscode.postMessage({
       command: 'saveLattice',
       data: data
   })
   ↓
5. Extension Host receives message via:
   desktopPanel.webview.onDidReceiveMessage()
   ↓
6. Extension calls: saveLatticeToFile(data)
   ↓
7. Extension uses Node.js fs module to write files:
   - .odras/demo/lattice.json
   - .odras/demo/projects.json
   - .odras/demo/registry.json
   - .odras/demo/workflow-history.json
   - .odras/demo/llm-audit-trail.json
   ↓
8. Success notification: vscode.window.showInformationMessage()
```

### Code Locations

**Demo JavaScript** (`scripts/demo/static/intelligent_lattice.js:2372-2376`):
```javascript
if (window.parent && window.parent !== window) {
    // We're in an iframe - send message to parent (desktop webview)
    window.parent.postMessage({
        source: 'lattice-demo-iframe',
        command: 'saveLattice',
        data: data
    }, '*');
    
    this.updateAnalysisStatus('💾 Saving to .odras/demo/...');
    return;
}
```

**Desktop Webview Listener** (`extension.ts:407-415`):
```javascript
window.addEventListener('message', (event) => {
    if (event.data && event.data.source === 'lattice-demo-iframe') {
        // Forward to extension host
        vscode.postMessage({
            command: event.data.command,
            data: event.data.data
        });
    }
});
```

**Extension Host Handler** (`extension.ts:67-70`):
```typescript
case 'saveLattice':
    await this.saveLatticeToFile(message.data);
    break;
```

**File System Writer** (`extension.ts:204-236`):
```typescript
private async saveLatticeToFile(data: any) {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    const workspaceRoot = workspaceFolders[0].uri.fsPath;
    const odrasDemoDir = path.join(workspaceRoot, '.odras', 'demo');
    
    // Create directory
    fs.mkdirSync(odrasDemoDir, { recursive: true });
    
    // Save each file
    const files = [
        { name: 'lattice.json', data: data.lattice },
        // ... more files
    ];
    
    for (const file of files) {
        fs.writeFileSync(filePath, JSON.stringify(file.data, null, 2));
    }
    
    vscode.window.showInformationMessage('✅ Saved!');
}
```

## Issues We May Encounter

### 1. **Cross-Origin Communication Complexity**

**Issue**: Three-layer message passing (iframe → webview → extension) adds complexity.

**Symptoms**:
- Messages not reaching extension host
- Data getting lost in transit
- Timing issues (messages sent before listeners ready)

**Solutions**:
- Add `source` identifier to all messages (`source: 'lattice-demo-iframe'`)
- Use wildcard origin (`'*'`) for `postMessage` in iframe
- Add message logging for debugging
- Ensure event listeners are set up before content loads

### 2. **CSP (Content Security Policy) Restrictions**

**Issue**: VS Code webviews have strict CSP by default, blocking iframes and external resources.

**Symptoms**:
- White screen when opening demo
- "Refused to frame..." errors in console
- External scripts (Cytoscape) not loading

**Solutions**:
- Add `frame-src http://localhost:*` to allow local iframes
- Use sandbox attributes on iframe
- Allow unsafe-inline scripts/styles
- Keep CSP as permissive as needed for localhost

### 3. **External Script Loading in Iframes**

**Issue**: External CDN scripts (like Cytoscape from unpkg.com) may be blocked.

**Current Status**: Works because iframe loads from HTTP server (localhost:8082), not embedded HTML.

**If we switch back to embedded HTML**:
- Cytoscape won't load (CSP blocks external scripts)
- Must bundle Cytoscape locally or use different approach

**Solution**: Keep using HTTP server URL (`src="http://localhost:8082/..."`) in iframe.

### 4. **Workspace Folder Requirement**

**Issue**: Extension requires an open workspace folder to save files.

**Symptoms**:
- "No workspace folder open" error
- Files not saving

**Solutions**:
- Auto-open ODRAS workspace on extension activation (already implemented)
- Show helpful error messages with "Select Folder" button
- Check for workspace before saving

### 5. **Demo Server Must Be Running**

**Issue**: Demo loads from `http://localhost:8082`, which requires the HTTP server to be running.

**Symptoms**:
- 404 errors when opening demo
- Blank iframe
- Warning message about server not running

**Solutions**:
- Add server check before creating window (already implemented)
- Show clear error message: "Start with: cd scripts/demo && ./demo.sh start"
- Consider auto-starting server in future

### 6. **Message Data Size Limits**

**Issue**: `postMessage` has size limits (usually ~1MB depending on browser/VS Code).

**Symptoms**:
- Large lattices fail to save
- No error message (silent failure)
- Only some files get saved

**Solutions**:
- Split large data into chunks
- Save files individually (current approach already does this)
- Add error handling for postMessage failures
- Consider streaming approach for very large data

### 7. **Iframe Sandbox Restrictions**

**Issue**: Sandbox attributes restrict what the iframe can do.

**Current Sandbox**: `allow-same-origin allow-scripts allow-forms allow-popups allow-modals`

**Not Allowed**:
- `window.top` access (security feature)
- Direct file system access (must use postMessage)
- Opening new browser windows
- Downloading files directly

**If We Need More Permissions**:
- `allow-downloads`: Allow file downloads
- `allow-pointer-lock`: For games/interactive apps
- Be careful: more permissions = less security

### 8. **Duplicate Event Listeners**

**Issue**: When creating multiple demo windows, event listeners accumulate.

**Symptoms**:
- Messages handled multiple times
- Files saved multiple times
- Memory leaks

**Solutions**:
- Use unique window IDs
- Check message windowId before handling
- Remove listeners when windows close
- Consider using AbortController for cleanup

### 9. **Window vs Iframe Focus**

**Issue**: Clicking in iframe doesn't bring parent window to front.

**Symptoms**:
- Window appears "stuck behind" other windows
- User thinks window is broken

**Solutions**:
- Add click handler to bring window to front
- Update z-index on iframe clicks
- May need to monitor iframe focus events

### 10. **Network Request Origins**

**Issue**: Demo makes requests to `localhost:8083` (LLM service) from within iframe.

**Current Status**: Works because iframe loads from `localhost:8082` (same origin).

**If We Switch to Embedded HTML**:
- Requests would be blocked (different origin)
- CORS errors
- Must keep using HTTP server URL in iframe

## Best Practices Going Forward

### 1. **Keep Using Iframes for Web Apps**
- Don't try to embed HTML directly
- Iframes are the reliable, tested approach
- External scripts work
- Network requests work

### 2. **Use HTTP Server for Demo**
- Keep demo on `http://localhost:8082`
- Don't try to bundle demo into extension
- Simpler and more flexible

### 3. **Message Protocol**
Always include:
```javascript
{
    source: 'lattice-demo-iframe',  // Identify sender
    command: 'saveLattice',          // Action to perform
    data: { ... }                    // Payload
}
```

### 4. **Error Handling**
- Check for workspace before file operations
- Check for server before loading iframe
- Show clear error messages with solutions
- Log errors for debugging

### 5. **File System Operations**
- Always use `fs.existsSync()` before reading
- Use `recursive: true` when creating directories
- Write files atomically (temp file + rename for large files)
- Validate data before writing

## Testing Checklist

- [ ] Desktop opens on activation
- [ ] Icons render correctly
- [ ] Double-click opens applications
- [ ] Demo loads in iframe (not white screen)
- [ ] Requirements auto-load
- [ ] Generate button works
- [ ] Save button appears after generation
- [ ] Click save → files appear in `.odras/demo/`
- [ ] All 5 JSON files are created
- [ ] Files have correct content
- [ ] Success notification appears

## Troubleshooting

### White Screen in Demo Window
1. Check demo server is running: `curl http://localhost:8082/intelligent_lattice_demo.html`
2. Check CSP allows `frame-src http://localhost:8082`
3. Check iframe sandbox attributes
4. Look for errors in Extension Development Host console

### Save Not Working
1. Check workspace folder is open
2. Check message is sent from demo: `window.parent.postMessage(...)`
3. Check desktop webview forwards message
4. Check extension host receives message
5. Check file system permissions for `.odras/demo/`
6. Look for errors in extension host console

### Demo Server Not Running
```bash
cd scripts/demo
./demo.sh start
# Or manually:
python3 -m http.server 8082 --directory static
```

## Future Improvements

1. **Auto-start demo server** when extension activates
2. **Resize windows** (add resize handles to window divs)
3. **Maximize/minimize** buttons (already have close button)
4. **Multiple desktops** or workspaces
5. **Window snapping** (snap to edges, quarter-screen, etc.)
6. **Taskbar** showing open windows
7. **File browser** improvements (copy/paste, drag-drop)
8. **Application launcher** (command palette for apps)
9. **Settings panel** (configure server ports, etc.)
10. **Error recovery** (auto-restart server if it crashes)

## Why This Approach Works

### Attempted Approaches That Failed

1. **Direct HTML Embedding** - External scripts (Cytoscape) wouldn't load
2. **Complex Script Injection** - Initialization order was unpredictable
3. **Hybrid srcdoc + fetch** - Network requests blocked by security
4. **Multiple webview panels** - Didn't give desktop feel

### Why Iframe URL Loading Works

1. **External scripts load**: Cytoscape loads from unpkg.com
2. **Network requests work**: Fetch to localhost:8083 works
3. **Initialization reliable**: Standard HTML load sequence
4. **PostMessage available**: `window.parent` accessible with `allow-same-origin`
5. **No CSP conflicts**: iframe has its own CSP from HTTP server

### The Critical Insight

**VS Code webviews can't directly access the file system**, but **the extension host can**.

The solution is a **message bridge**:
- Webview (iframe) → Webview (desktop) → Extension Host → File System

This three-layer approach is necessary because:
1. Iframe can't directly talk to extension host
2. Iframe CAN talk to parent webview via `postMessage`
3. Parent webview CAN talk to extension host via `vscode.postMessage()`
4. Extension host has full file system access

## Code Summary

- **Total lines**: 525 (simple and maintainable)
- **Core files**:
  - `src/extension.ts` - Main extension logic (525 lines)
  - `src/fileManager.ts` - File system utilities (44 lines)
  - `package.json` - Extension manifest (37 lines)

- **No complex dependencies**: Just VS Code API + Node.js built-ins
- **No bundling needed**: Iframe loads from HTTP server
- **No build configuration**: Standard TypeScript compiler

## Comparison to Failed Approaches

| Approach | Lines of Code | External Scripts | Network Requests | File Saving | Result |
|----------|---------------|------------------|------------------|-------------|---------|
| Direct HTML Embedding | 2400+ | ❌ Failed | ❌ Blocked | Attempted | Failed |
| Complex Script Injection | 2500+ | ❌ Failed | ❌ Blocked | Attempted | Failed |
| Iframe URL Loading | 525 | ✅ Works | ✅ Works | ✅ Works | **Success** |

## Lessons Learned

1. **Simplicity wins**: The simplest approach (iframe + URL) works best
2. **Don't fight the platform**: Use iframes as intended, don't try to hack around them
3. **Security is strict**: CSP and sandbox attributes must be configured correctly
4. **Message passing works**: It's reliable when set up properly
5. **HTTP server is OK**: Don't need to bundle everything into the extension

## Next Steps for Future Development

1. **Add more applications**: Supply Chain, Compliance, etc.
2. **Improve window management**: Resize, maximize, minimize
3. **Add taskbar**: Show open windows, quick switching
4. **Better file browser**: Context menus, drag-drop
5. **Settings panel**: Configure ports, theme, etc.
6. **Error recovery**: Auto-restart services if they fail
7. **State persistence**: Remember open windows across sessions
8. **Keyboard shortcuts**: Alt+Tab, etc.

## Critical Files to Not Break

1. **Message source identifier**: `source: 'lattice-demo-iframe'` - must match in demo and desktop
2. **CSP frame-src**: Must include `http://localhost:8082` or iframe won't load
3. **Iframe sandbox**: Must include `allow-same-origin` or postMessage won't work
4. **File paths**: `.odras/demo/` structure must match what other tools expect
