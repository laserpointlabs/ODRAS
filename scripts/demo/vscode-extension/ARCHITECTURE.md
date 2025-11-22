# VS Code Extension Architecture

## Overview

This VS Code extension wraps the ODRAS Intelligent Lattice Demo as a webview panel. It demonstrates how ODRAS workbenches can be converted to VS Code extensions.

## Key Concepts

### Webviews

**Webviews are like iframes but with more capabilities:**

- **Isolated Context**: Webviews run in a separate JavaScript context from VS Code
- **Message Passing**: Communication via `vscode.postMessage()` and `window.addEventListener('message')`
- **File System Access**: Extension host can read/write files, webview cannot
- **Resource Loading**: Can load local files via `webview.asWebviewUri()`
- **Full HTML/CSS/JS**: Can use any web technologies (Cytoscape.js, React, etc.)

### Architecture Flow

```
VS Code Extension Host (TypeScript)
    ↓
Creates Webview Panel
    ↓
Loads HTML from intelligent_lattice_demo.html
    ↓
Injects VS Code API bridge
    ↓
Webview (HTML/JavaScript)
    ↓
Communicates via postMessage
    ↓
Extension saves to workspace files
```

## File Structure

```
vscode-extension/
├── src/
│   └── extension.ts          # Extension host code
├── package.json              # Extension manifest
├── tsconfig.json            # TypeScript config
└── README.md                # User documentation
```

## How It Works

### 1. Extension Activation

When user runs `ODRAS: Open Intelligent Lattice Demo`:
- Extension creates a webview panel
- Loads `intelligent_lattice_demo.html` from `../static/`
- Injects VS Code API bridge script
- Updates resource paths to use webview URIs

### 2. Webview Integration

The injected script:
- Adds "Save to Workspace" and "Load from Workspace" buttons
- Intercepts save operations to use VS Code API
- Handles workspace data loading

### 3. File Storage

Results saved to `.odras/demo/` in workspace:
- `lattice.json` - Project lattice structure
- `projects.json` - Created projects
- `registry.json` - Project name mappings
- `workflow-history.json` - Workflow execution history
- `llm-audit-trail.json` - LLM interaction log

### 4. Backend API

**The backend API remains unchanged:**
- Extension webview calls ODRAS API at `http://localhost:8000`
- Same authentication, same endpoints
- API is tool-agnostic - works with any client

## Benefits

1. **File-Based**: Everything saved as files for version control
2. **Indexable**: Files can be indexed by VS Code, Git, search tools
3. **No Custom UI**: Leverages VS Code's extension infrastructure
4. **API Remains**: Backend API stays independent and reusable

## Next Steps

This pattern can be applied to:
- Requirements Workbench
- Ontology Workbench  
- Knowledge Workbench
- Any other ODRAS workbench

Each becomes a VS Code extension that:
- Uses webviews for complex UI
- Saves results as files
- Communicates with ODRAS API
- Integrates with VS Code ecosystem
