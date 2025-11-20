# Desktop Environment - Troubleshooting Guide

## Quick Diagnostics

### Problem: White Screen in Demo Window

**Check 1**: Is demo server running?
```bash
curl http://localhost:8082/intelligent_lattice_demo.html
```
- **If fails**: `cd scripts/demo && ./demo.sh start`
- **If works**: Check next step

**Check 2**: Is CSP allowing the iframe?
- Look for: `frame-src http://localhost:8082` in extension.ts:244
- **If missing**: Add to CSP header

**Check 3**: Does iframe have sandbox attributes?
- Look for: `sandbox="allow-same-origin allow-scripts..."` in extension.ts:405
- **If missing**: Add sandbox attributes

**Fix**: Reload Extension Development Host (Shift+F5, then F5)

### Problem: Save Button Does Nothing

**Check 1**: Is workspace folder open?
```bash
# In Extension Development Host, check bottom left corner
# Should show: /home/jdehart/working/ODRAS
```
- **If no folder**: Click status bar, select ODRAS folder

**Check 2**: Was lattice generated?
- Save button only appears after clicking "Generate Intelligent Lattice"
- Button says "💾 Save Results"
- **If button hidden**: Generate lattice first

**Check 3**: Is message being sent?
Add to `intelligent_lattice.js:2374`:
```javascript
console.log('Sending save message...', data);
window.parent.postMessage({...}, '*');
console.log('Message sent');
```

**Check 4**: Is message being received?
Add to extension.ts (desktop HTML):
```javascript
window.addEventListener('message', (event) => {
    console.log('Desktop received:', event.data);
    // ...
});
```

### Problem: Files Not Appearing in .odras/demo/

**Check 1**: Does folder exist?
```bash
ls -la .odras/demo/
```
- **If missing**: Extension should create it automatically

**Check 2**: Check file permissions
```bash
ls -ld .odras .odras/demo
```
- **If permission denied**: `chmod 755 .odras .odras/demo`

**Check 3**: Are files empty?
```bash
wc -l .odras/demo/*.json
```
- **If 0 bytes**: Data validation failed, check data.lattice is not null

**Check 4**: Check file timestamps
```bash
ls -lt .odras/demo/
```
- **If old**: Files not being updated, check extension code

### Problem: Extension Won't Start

**Error**: "Command 'desktop.openDesktop' not found"
- **Fix**: Extension not activated
- **Solution**: Reload window, check activationEvents in package.json

**Error**: "Cannot find module..."
- **Fix**: Dependencies not installed
- **Solution**: `cd desktop-environment-extension && npm install`

**Error**: TypeScript compilation errors
- **Fix**: Source code has syntax errors
- **Solution**: Check compilation output, fix errors

### Problem: Requirements Don't Auto-Load

**Symptom**: Textarea is empty when demo opens

**Root Cause**: Demo's `init()` calls `loadExampleRequirements()` automatically.

**If still empty**:
1. Check `intelligent_lattice.js:31` - should call `loadExampleRequirements()`
2. Check `intelligent_lattice.js:245` - should set `requirementsInput.value`
3. Check DOM element exists: `document.getElementById('requirementsInput')`

**Workaround**: Click "Load Example" button manually

### Problem: Generate Button Doesn't Work

**Symptom**: Clicking "Generate" does nothing

**Check 1**: Are requirements entered?
- Requirements textarea must have content
- **Fix**: Click "Load Example" first

**Check 2**: Is LLM service running?
```bash
curl http://localhost:8083/health
```
- **If fails**: Demo will use mock generation (this is OK)
- **If works**: Check for JavaScript errors

**Check 3**: Check network in browser
- Open demo standalone: `http://localhost:8082/intelligent_lattice_demo.html`
- Open browser dev tools, check Network tab
- Should see request to `http://localhost:8083/generate-lattice`

## Message Flow Debugging

### Enable Full Logging

**1. In Demo (intelligent_lattice.js)**:
```javascript
saveResults() {
    console.log('[DEMO] saveResults called');
    console.log('[DEMO] Current lattice:', this.currentLattice);
    
    const data = { ... };
    console.log('[DEMO] Prepared data:', Object.keys(data));
    
    window.parent.postMessage({...}, '*');
    console.log('[DEMO] Message sent to parent');
}
```

**2. In Desktop Webview (extension.ts getDesktopHTML)**:
```javascript
window.addEventListener('message', (event) => {
    console.log('[DESKTOP] Received message:', event.data);
    
    if (event.data && event.data.source === 'lattice-demo-iframe') {
        console.log('[DESKTOP] Forwarding to extension...');
        vscode.postMessage({
            command: event.data.command,
            data: event.data.data
        });
        console.log('[DESKTOP] Forwarded');
    }
});
```

**3. In Extension Host (extension.ts)**:
```typescript
case 'saveLattice':
    console.log('[EXTENSION] Received save request');
    console.log('[EXTENSION] Data keys:', Object.keys(message.data));
    await this.saveLatticeToFile(message.data);
    console.log('[EXTENSION] Save complete');
    break;
```

### Expected Log Sequence

```
[DEMO] saveResults called
[DEMO] Current lattice: {...}
[DEMO] Prepared data: ['lattice', 'projects', 'registry', 'workflowHistory', 'llmAuditTrail']
[DEMO] Message sent to parent
[DESKTOP] Received message: {source: 'lattice-demo-iframe', command: 'saveLattice', data: {...}}
[DESKTOP] Forwarding to extension...
[DESKTOP] Forwarded
[EXTENSION] Received save request
[EXTENSION] Data keys: ['lattice', 'projects', 'registry', 'workflowHistory', 'llmAuditTrail']
[EXTENSION] Save complete
```

**If logs stop at any point, that's where the issue is.**

## Common Fixes

### Fix 1: Reload Everything
```bash
# Reload Extension Development Host
Shift+F5 (stop debug)
F5 (start debug)

# Reload Demo (in desktop window)
Close demo window, double-click icon again
```

### Fix 2: Restart Services
```bash
cd scripts/demo
./demo.sh stop
./demo.sh start
```

### Fix 3: Clean State
```bash
# Remove saved data
rm -rf .odras/demo/*

# Restart extension
Shift+F5, then F5
```

### Fix 4: Reinstall Dependencies
```bash
cd desktop-environment-extension
rm -rf node_modules package-lock.json
npm install
npm run compile
```

## When to Use iframe vs Direct Embedding

### Use Iframe When:
✅ App needs external scripts (CDN libraries)
✅ App makes network requests to other servers
✅ App is complex (1000+ lines of JavaScript)
✅ App has its own server/URL
✅ You want app to work standalone AND in extension

### Use Direct Embedding When:
✅ App is simple (few hundred lines)
✅ No external dependencies
✅ No network requests
✅ Full control over HTML/JS/CSS
✅ Need tighter integration with VS Code

**For Lattice Demo**: Iframe is the right choice.

## Critical Code Locations

| What | Where | Line |
|------|-------|------|
| Save button click | `intelligent_lattice.js` | 187-189 |
| Save function | `intelligent_lattice.js` | 2345-2426 |
| PostMessage to parent | `intelligent_lattice.js` | 2372-2376 |
| Desktop message listener | `extension.ts` (in HTML) | 407-415 |
| Extension message handler | `extension.ts` | 67-70 |
| File system writer | `extension.ts` | 204-236 |
| Iframe creation | `extension.ts` (in HTML) | 397-420 |
| CSP configuration | `extension.ts` | 244 |

## Questions to Ask When Debugging

1. **Is the workspace open?** Check VS Code status bar
2. **Is the demo server running?** `curl localhost:8082`
3. **Is the demo loaded?** Check for white screen
4. **Did generation complete?** Check for save button
5. **Did click work?** Check for status change
6. **Did message send?** Check console logs
7. **Did files save?** Check `.odras/demo/` folder
8. **Are files correct?** Check JSON content

## Contact Points for Issues

- **Iframe not loading**: Check CSP and demo server
- **Save not working**: Check message chain and file permissions
- **Demo not initializing**: Check external scripts loading
- **Files empty**: Check data validation and null checks
- **Extension crashes**: Check TypeScript compilation errors

## This Approach is SOLID

After many failed attempts, the iframe + postMessage + file system approach is:
- ✅ Working reliably
- ✅ Simple to understand
- ✅ Easy to debug
- ✅ Maintainable code
- ✅ Extensible for new apps

**Don't try to "fix" it with direct HTML embedding or complex script injection. It works as-is.**
