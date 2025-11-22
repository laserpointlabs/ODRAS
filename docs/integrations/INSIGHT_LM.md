# InsightLM Integration

## Overview

**InsightLM** is a Continue.dev fork that adds workbook management capabilities for document organization and AI-powered analysis.

- **Repository**: https://github.com/laserpointlabs/insightLM
- **Type**: VS Code extension
- **Relationship to ODRAS**: Separate project, no code dependencies

## What is InsightLM?

InsightLM extends Continue.dev (an open-source AI code assistant) with:

- **Workbooks**: NotebookLM-style document organization
- **Document Management**: Upload and organize files for AI analysis
- **Continue.dev AI**: Full AI agent capabilities for code and document analysis
- **Integration**: AI can read and create files in workbooks

## Use Cases

### For ODRAS Users

InsightLM can complement ODRAS workflows:

1. **Requirements Analysis**: Organize RFP documents in workbooks, use Continue AI to extract requirements
2. **Knowledge Management**: Store reference documents, specifications, and standards
3. **Documentation Review**: Analyze large documents with AI assistance
4. **Project Planning**: Organize project documents and chat with AI about them

### Standalone Use

InsightLM can also be used independently:
- General document organization and AI analysis
- Code project documentation management
- Research document organization
- Any NotebookLM-style workflow

## Installation

### Prerequisites

- VS Code (not Cursor)
- Node.js >=20.19.0

### Running InsightLM

1. **Clone the repository:**
   ```bash
   cd /home/jdehart/working
   git clone https://github.com/laserpointlabs/insightLM.git
   ```

2. **Install dependencies:**
   ```bash
   cd insightLM/extensions/vscode
   npm install
   cd ../../gui && npm install
   cd ../../core && npm install
   ```

3. **Launch:**
   ```bash
   cd /home/jdehart/working/insightLM/extensions/vscode
   ./RUN_WORKBOOK_DEMO.sh
   ```

4. **Wait 15 seconds** for Extension Development Host to load

## Using InsightLM

### Creating Workbooks

In Extension Development Host window:
- Press `Ctrl+Shift+P`
- Type: `Insight: Create New Workbook`
- Enter workbook name
- Workbook appears in Continue sidebar

### Adding Documents

- Press `Ctrl+Shift+P`
- Type: `Insight: Add Document to Workbook`
- Select workbook
- Select file (.md, .txt, .pdf, .docx)

### Analyzing Documents with AI

1. Open Continue chat (click C icon in sidebar)
2. Add workbook files to context:
   - Type: `@Folder`
   - Select: `.insight/workbooks`
3. Ask Continue questions about your documents
4. Continue can create new files in the workbook

### Workbook Storage

Files are stored in `.insight/workbooks/{uuid}/`:
- `workbook.json` - Metadata
- `documents/` - Your uploaded and AI-generated files

## Integration with ODRAS

### No Code Dependencies

InsightLM and ODRAS are **completely separate** projects:
- No shared code
- No submodules
- No version dependencies
- Independent development cycles

### Data Sharing (Manual)

To use ODRAS data in InsightLM:

1. Export data from ODRAS (requirements, documents, etc.)
2. Save as files in filesystem
3. Add to InsightLM workbook
4. Analyze with Continue AI

### Workflow Example

```
ODRAS                          InsightLM
-----                          ----------
1. Create project
2. Extract requirements   →    3. Copy requirements.md to workbook
                               4. Use Continue AI to analyze
                          ←    5. AI generates analysis
6. Import analysis
```

## Development

### Separate Repositories

- **ODRAS**: https://github.com/laserpointlabs/ODRAS
- **InsightLM**: https://github.com/laserpointlabs/insightLM

Developed independently, no cross-dependencies.

### Development Workflow

See InsightLM's `DEVELOPMENT.md` for:
- Setting up development environment
- Cross-IDE workflow (edit in Cursor, test in VS Code)
- Build and test procedures

## Architecture

### InsightLM Components

```
insightLM/
├── extensions/vscode/      # VS Code extension with workbooks
│   └── src/workbooks/      # Workbook system code
├── core/                   # Continue.dev core (mostly unchanged)
├── gui/                    # Continue.dev React UI (mostly unchanged)
└── docs/                   # Documentation
```

### Workbook System

- **WorkbookManager**: CRUD operations for workbooks
- **WorkbookTreeProvider**: VS Code tree view integration
- **activateWorkbooks**: Extension activation and command registration

### Continue.dev Integration

- Workbooks appear in Continue sidebar
- AI can access workbook files via @mentions
- AI can create files in workbook documents folder
- Full Continue.dev agent functionality intact

## Differences from Continue.dev

InsightLM is a **static fork** of Continue.dev with additions:

**Additions:**
- Workbook management system
- Enhanced file organization
- Improved development scripts

**No Upstream Syncing:**
- Forked at Continue.dev v1.3.26
- No plans to merge upstream changes
- Maintained independently

## Support

### InsightLM Issues

Report at: https://github.com/laserpointlabs/insightLM/issues

### ODRAS Integration Questions

For questions about using InsightLM with ODRAS:
- Check this document first
- Open ODRAS issue if ODRAS-specific
- Open InsightLM issue if extension-specific

## Future Enhancements

Potential InsightLM features:

1. **ODRAS-specific connectors**: Direct ODRAS API integration
2. **Requirements extraction**: Specialized tools for requirements documents
3. **Project templates**: Pre-configured workbooks for ODRAS projects
4. **Export to ODRAS**: Direct export to ODRAS knowledge base

These would be InsightLM features, not ODRAS features.

## License

InsightLM inherits Continue.dev's Apache 2.0 license.

## Quick Reference

| Task | Command |
|------|---------|
| Launch InsightLM | `cd insightLM/extensions/vscode && ./RUN_WORKBOOK_DEMO.sh` |
| Stop InsightLM | `./STOP_DEMO.sh` |
| Rebuild after changes | `./quick-rebuild.sh` |
| Create workbook | Ctrl+Shift+P → "Insight: Create New Workbook" |
| Add document | Ctrl+Shift+P → "Insight: Add Document to Workbook" |
| Use Continue AI | Click C icon, type @Folder to add workbooks |

## Links

- InsightLM Repository: https://github.com/laserpointlabs/insightLM
- InsightLM Documentation: See repository README
- Continue.dev Docs: https://docs.continue.dev
- ODRAS Repository: https://github.com/laserpointlabs/ODRAS

