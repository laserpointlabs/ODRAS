# [STANDARD NAME]: Extensible Architecture for Domain Tools

**Version:** 1.0  
**Date:** November 2025  
**Status:** Architectural Foundation

**Note:** ODRAS (Ontology-Driven Requirements Analysis System) is now **one use case** built on this standard, not the standard itself.

---

## The Core Insight

**[STANDARD NAME] is a standard/architecture. ODRAS is one implementation.**

People already understand this pattern:
- ✅ **Windows files** - They work with files every day
- ✅ **Extensions** - They install browser extensions, VS Code extensions
- ✅ **Tools** - They use tools that work with files
- ✅ **Workflows** - They connect tools together

**The Problem:** They don't realize they're already using this pattern.

**The Solution:** Make it obvious - give them access to:
- The entire file set
- All data
- External tools
- Workflows

---

## What [STANDARD NAME] Actually Is

### A Standard Architecture

**[STANDARD NAME] = [To Be Named] - Extensible Domain Architecture Standard**

A **standard architecture** for building domain-specific tools that:
1. Work with files (like Windows)
2. Use extensions (like browsers/VS Code)
3. Connect tools (like workflows)
4. Share data (like file formats)

### The Pattern Everyone Knows

```
Files → Tools → Extensions → Workflows
```

**Windows Example:**
- **Files**: `.docx`, `.xlsx`, `.pdf` in folders
- **Tools**: Word, Excel, Acrobat
- **Extensions**: Add-ins, macros, plugins
- **Workflows**: Print → Email → Archive

**[STANDARD NAME] Example (ODRAS use case):**
- **Files**: `.odras/projects/`, `.odras/requirements/`, `.odras/ndas/`
- **Tools**: Requirements Manager, Supplier Tracker, NDA Manager
- **Extensions**: Supply Chain Extension, Compliance Extension
- **Workflows**: Extract Requirements → Link to Supplier → Generate Report

**Same Pattern. Different Domain.**

**ODRAS is one implementation of this standard.**

---

## Architecture Principles

### 1. **File-Based (Like Windows)**

Everything is files in folders:
```
.odras/
├── projects/
│   ├── l0-core/
│   │   ├── project.json
│   │   ├── requirements/
│   │   │   ├── REQ-001.md
│   │   │   └── REQ-002.md
│   │   └── suppliers/
│   │       └── supplier-acme.json
│   └── l1-se-domain/
│       └── ...
├── ndas/
│   ├── nda-2024-001.json
│   └── nda-2024-002.json
└── compliance/
    ├── regulations/
    └── certifications/
```

**Why This Works:**
- ✅ Everyone understands folders
- ✅ Version control (Git) works automatically
- ✅ Searchable (Windows Search, Everything)
- ✅ Backed up (like any files)
- ✅ Shareable (copy folder, email, network drive)

### 2. **Extension-Based (Like VS Code/Browsers)**

Tools are extensions:
```
odras-supply-chain-extension/
odras-compliance-extension/
odras-nda-extension/
odras-training-extension/
```

**Why This Works:**
- ✅ Install only what you need
- ✅ Each role gets their own extension
- ✅ Extensions can be built by anyone
- ✅ Extensions work together

### 3. **Tool-Based (Like Command Line Tools)**

Each extension provides tools:
```
odras-supply-chain-extension/
├── add-supplier (tool)
├── link-deliverable (tool)
└── generate-report (tool)
```

**Why This Works:**
- ✅ Tools are simple, focused
- ✅ Tools can be called from anywhere
- ✅ Tools can be automated
- ✅ Tools can be chained together

### 4. **Workflow-Based (Like Automation)**

Tools connect via workflows:
```
Upload Document → Extract Requirements → Link to Supplier → Generate Report
```

**Why This Works:**
- ✅ Visual workflows (like Zapier, Power Automate)
- ✅ Automated processes
- ✅ Repeatable operations
- ✅ Error handling

---

## The Standard Structure

### File Organization Standard

```
.[standard-name]/
├── projects/          # Project hierarchy (L0, L1, L2)
├── requirements/      # Requirements (linked to projects)
├── suppliers/         # Suppliers (linked to projects)
├── ndas/              # NDAs (linked to projects/suppliers)
├── compliance/        # Regulations, certifications
├── training/          # Courses, certifications
└── workflows/         # BPMN workflow definitions
```

**Note:** In ODRAS use case, this is `.odras/`. Other use cases would use their own prefix.

### Extension Standard

```
[standard-name]-[domain]-extension/
├── package.json       # Extension manifest
├── src/
│   ├── tools/        # MCP tools
│   ├── ui/           # UI components
│   └── workflows/    # Workflow definitions
└── README.md          # Extension docs
```

### Tool Standard (MCP)

```json
{
  "name": "add_supplier",
  "description": "Add a new supplier",
  "inputSchema": {
    "type": "object",
    "properties": {
      "name": {"type": "string"},
      "contract_number": {"type": "string"}
    }
  }
}
```

### Workflow Standard (BPMN)

```xml
<bpmn:process id="supplier_onboarding">
  <bpmn:startEvent id="start"/>
  <bpmn:serviceTask id="add_supplier" name="Add Supplier"/>
  <bpmn:serviceTask id="link_requirements" name="Link Requirements"/>
  <bpmn:endEvent id="end"/>
</bpmn:process>
```

---

## How It Works (User Perspective)

### What Users See

**They see:**
- Files in folders (like Windows)
- Tools they can use (like command line)
- Extensions they can install (like VS Code)
- Workflows they can run (like automation)

**They don't see:**
- Databases
- APIs
- Servers
- Complex architecture

### Example: Supply Chain Manager

```
1. Open folder: .odras/suppliers/
2. See files: supplier-acme.json, supplier-beta.json
3. Use tool: "Add Supplier" (from extension)
4. Tool creates: supplier-gamma.json
5. Link to project: Tool updates project.json
6. Generate report: Tool reads files, creates Excel
```

**It's just files and tools. That's it.**

---

## The Extension Ecosystem

### Built-In Extensions (ODRAS Use Case)

- `odras-core` - Basic project/requirement management
- `odras-supply-chain` - Supplier management
- `odras-compliance` - Regulatory compliance
- `odras-nda` - NDA/contract management
- `odras-training` - Training management

### Community Extensions

Anyone can build:
- `[standard-name]-custom-domain` - Your domain-specific extension
- `[standard-name]-integration-salesforce` - Salesforce integration
- `[standard-name]-reporting-custom` - Custom reporting

**Note:** Extensions follow the standard naming: `[standard-name]-[domain]-extension`

### Extension Marketplace

- Browse extensions
- Install with one click
- Rate and review
- Contribute back

---

## Integration with External Tools

### File-Based Integration

**Any tool that reads files works:**
- Excel → Read `.odras/projects/*.json`
- Python scripts → Process files
- PowerShell → Automate workflows
- Git → Version control

### Tool-Based Integration

**Any tool that calls commands works:**
- VS Code → Call MCP tools
- Continue.ai → Use tools via MCP
- PowerShell → Invoke tools
- Python → Call tools via MCP

### Workflow Integration

**Any workflow tool works:**
- Power Automate → Trigger workflows
- Zapier → Connect workflows
- GitHub Actions → Automate workflows
- Custom scripts → Run workflows

---

## The Standard Benefits

### For Users

- ✅ **Familiar**: Files and folders (like Windows)
- ✅ **Simple**: Tools do one thing well
- ✅ **Flexible**: Install only what you need
- ✅ **Extensible**: Add your own tools
- ✅ **Portable**: Copy folder, works anywhere

### For Developers

- ✅ **Standard**: Follow the pattern
- ✅ **Simple**: Files + Tools + Extensions
- ✅ **Composable**: Build on existing tools
- ✅ **Testable**: Test files and tools
- ✅ **Maintainable**: Clear structure

### For Organizations

- ✅ **Version Control**: Git works automatically
- ✅ **Backup**: Backup files (like any files)
- ✅ **Audit**: Track file changes
- ✅ **Compliance**: Files are auditable
- ✅ **Integration**: Works with existing tools

---

## Migration Path

### From "ODRAS System" to "ODRAS Standard"

**Phase 1: File-Based**
- Move data to files
- Use file structure standard
- Tools read/write files

**Phase 2: Tool-Based**
- Convert APIs to tools
- Tools use MCP standard
- Tools work with files

**Phase 3: Extension-Based**
- Package tools as extensions
- Extensions follow standard
- Extensions work together

**Phase 4: Workflow-Based**
- Define workflows
- Workflows use tools
- Workflows automate processes

---

## Example: Building a Custom Extension

### Step 1: Define Your Domain

```
I need to track equipment maintenance.
```

### Step 2: Create File Structure

```
.odras/equipment/
├── equipment-001.json
├── equipment-002.json
└── maintenance/
    ├── maintenance-2024-001.json
    └── maintenance-2024-002.json
```

### Step 3: Create Tools

```python
# tools/add_equipment.py
def add_equipment(name, serial_number):
    equipment = {
        "id": generate_id(),
        "name": name,
        "serial_number": serial_number,
        "created_at": datetime.now()
    }
    save_to_file(f".[standard-name]/equipment/{equipment['id']}.json", equipment)
    return equipment
```

### Step 4: Create Extension

```json
{
  "name": "[standard-name]-equipment",
  "tools": [
    "add_equipment",
    "schedule_maintenance",
    "track_maintenance"
  ]
}
```

### Step 5: Use It

```
1. Install extension
2. Use tools: "Add Equipment", "Schedule Maintenance"
3. Files created automatically
4. Tools work together
```

**That's it. Simple.**

---

## The Key Message

**[STANDARD NAME] is not a system you learn.**

**[STANDARD NAME] is a standard you already know:**

- ✅ Files → You use files every day
- ✅ Tools → You use tools every day  
- ✅ Extensions → You install extensions
- ✅ Workflows → You automate things

**The only difference:**
- Instead of `.docx` files → `.[standard-name]/projects/` files
- Instead of Word → Domain-specific tools
- Instead of Word add-ins → Domain extensions
- Instead of macros → Workflows

**Same pattern. Different domain.**

**ODRAS is one use case built on this standard.**

---

## Summary

**[STANDARD NAME] as a Standard:**
- File-based (like Windows)
- Tool-based (like command line)
- Extension-based (like VS Code)
- Workflow-based (like automation)

**Result:**
- Users understand it immediately (they already use this pattern)
- Developers can build extensions easily (follow the standard)
- Organizations can integrate it seamlessly (works with existing tools)
- Multiple use cases can be built (ODRAS is one example)

**[STANDARD NAME] = The standard architecture for building domain-specific tools.**

**ODRAS = One implementation of [STANDARD NAME] for requirements analysis.**
