# Simple Workbook Workflow (What Actually Works)

## 1. Create Workbook
- Ctrl+Shift+P → `Insight: Create New Workbook`
- Enter name
- Workbook appears in Continue sidebar

## 2. Add Existing Files to Workbook
- Ctrl+Shift+P → `Insight: Add Document to Workbook`
- Select workbook
- Select file

## 3. Ask Continue About Workbook Files
- Open Continue chat (C icon)
- Type: `@Folder .insight/workbooks`
- Ask: "Summarize the smart home architecture document"
- Continue reads the files

## 4. Save Continue's Output to Workbook

**When Continue generates content (like a table):**

**Method 1: Copy/Paste (Simplest)**
1. Continue generates the table in chat
2. Copy the table
3. In VS Code: File → New Text File
4. Paste the table
5. Save as: `.insight/workbooks/87ee3dc9.../documents/table.md`

**Method 2: Use Command**
1. Copy Continue's output
2. Ctrl+Shift+P → `Insight: Add Document to Workbook`
3. Select a file you created with the content
4. Done

## What Works
✅ Create/delete workbooks
✅ Add files to workbooks
✅ Continue can READ workbook files (with @Folder)
✅ Manual save of Continue's output

## What Doesn't Work Yet
❌ Continue automatically writing to workbooks (causes crashes)
❌ Continue in Agent mode (file tools available but unreliable)

## Recommendation
Keep it simple - use Continue for analysis, manually save important outputs to workbooks.
