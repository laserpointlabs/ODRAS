# ODRAS Intelligent Lattice Demo - VS Code Extension

This VS Code extension provides the ODRAS Intelligent Lattice Demo as a webview panel within VS Code. All results are saved as files in the workspace for indexing, version control, and integration with other tools.

## Features

- **Webview Panel**: Opens the demo in a VS Code webview panel
- **File-Based Storage**: All results saved to `.odras/demo/` directory
- **Workspace Integration**: Load and save lattice data from workspace
- **Full Demo Functionality**: All features from the standalone HTML demo

## Installation

### Development

1. Install dependencies:
   ```bash
   cd scripts/demo/vscode-extension
   npm install
   ```

2. Compile TypeScript:
   ```bash
   npm run compile
   ```

3. Press F5 in VS Code to launch extension development host

### Production

1. Package the extension:
   ```bash
   vsce package
   ```

2. Install the `.vsix` file in VS Code

## Usage

1. Open Command Palette (Ctrl+Shift+P / Cmd+Shift+P)
2. Run command: `ODRAS: Open Intelligent Lattice Demo`
3. The demo opens in a webview panel
4. Use "Save to Workspace" to save results as files
5. Use "Load from Workspace" to restore saved data

## File Structure

Results are saved to `.odras/demo/` in your workspace:

- `lattice.json` - Project lattice structure
- `projects.json` - Created projects data
- `registry.json` - Project name to ID mapping
- `workflow-history.json` - Complete workflow history
- `llm-audit-trail.json` - LLM interaction audit trail

## Requirements

- ODRAS API running on `http://localhost:8000`
- OpenAI API key set in environment (`OPENAI_API_KEY`)
- VS Code 1.80.0 or higher

## Architecture

- **Extension Host**: TypeScript extension code (`src/extension.ts`)
- **Webview**: HTML/JavaScript webview panel
- **Backend API**: Communicates with ODRAS API at `http://localhost:8000`
- **File Storage**: Saves results as JSON files in workspace

## Development

- `src/extension.ts` - Main extension code
- `package.json` - Extension manifest
- `tsconfig.json` - TypeScript configuration

The webview uses the existing demo files from `../static/`:
- `intelligent_lattice.js` - Demo logic
- `lattice_demo.css` - Styles
