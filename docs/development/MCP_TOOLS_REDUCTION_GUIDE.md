# MCP Tools Reduction Guide

*How to resolve "exceeding total tools limit" warning in Cursor IDE*

## Problem

Cursor IDE has a **limit of 40 MCP tools** total across all MCP servers. When you exceed this limit, you'll see a warning:
- "Exceeding total tools limit"
- Performance degradation
- Slower AI responses
- Potential tool selection confusion

## Solution: Audit and Disable Unused MCP Servers

### Step 1: Access Cursor MCP Settings

1. **Open Cursor Settings**:
   - Press `Cmd + ,` (Mac) or `Ctrl + ,` (Windows/Linux)
   - Or: `Cursor` → `Settings` → `Preferences`

2. **Find MCP Configuration**:
   - Search for "MCP" or "Model Context Protocol"
   - Look for "MCP Servers" or "MCP Configuration"
   - May be in: `Settings` → `Features` → `MCP` or `Settings` → `Extensions` → `MCP`

3. **Alternative Location** (if not in settings):
   - Check `~/.cursor/mcp.json` or `~/.config/cursor/mcp.json`
   - Or look for MCP configuration in workspace settings

### Step 2: List All Active MCP Servers

Once you find the MCP configuration, you'll see a list like:

```json
{
  "mcpServers": {
    "server1": { ... },
    "server2": { ... },
    "server3": { ... },
    ...
  }
}
```

**Count the total number of tools**:
- Each MCP server can expose multiple tools
- Sum all tools across all servers
- If > 40, you need to disable some servers

### Step 3: Categorize MCP Servers

Create a list of your MCP servers and categorize them:

| Server Name | Purpose | Tools Count | Priority | Status |
|-------------|---------|-------------|----------|--------|
| GitHub | GitHub integration | 15 | High | Keep |
| Browser | Web browsing | 8 | Medium | Keep |
| Context7 | Documentation | 12 | Medium | Keep |
| Chrome DevTools | Browser debugging | 10 | Low | Disable |
| Playwright | Testing | 5 | Low | Disable |
| ... | ... | ... | ... | ... |

### Step 4: Disable Low-Priority Servers

**Disable servers you don't actively use**:

1. **In Cursor Settings**:
   - Find the MCP server configuration
   - Toggle off or remove unused servers
   - Save settings

2. **In Configuration File** (if editing directly):
   ```json
   {
     "mcpServers": {
       "github": { "enabled": true },
       "browser": { "enabled": true },
       "context7": { "enabled": true },
       "chrome-devtools": { "enabled": false },  // Disabled
       "playwright": { "enabled": false }        // Disabled
     }
   }
   ```

### Step 5: Verify Tool Count

After disabling servers:
1. Restart Cursor IDE
2. Check if warning is gone
3. Verify tool count is ≤ 40
4. Test that essential tools still work

## Recommended MCP Server Priority

### ✅ **Keep Active** (Essential)
- **GitHub** - Code repository management
- **Browser** - Web browsing and research
- **Context7** - Documentation lookup (if used)

### ⚠️ **Evaluate** (Use Case Dependent)
- **Chrome DevTools** - Only if actively debugging browsers
- **Playwright** - Only if actively testing web apps
- **File System** - Only if needed for file operations
- **Database** - Only if actively querying databases

### ❌ **Disable** (Rarely Used)
- Servers you haven't used in the last month
- Servers for features you don't actively develop
- Duplicate functionality servers
- Experimental or test servers

## Quick Reduction Strategy

### Option 1: Disable by Category
- **Development**: Keep GitHub, disable others
- **Testing**: Disable Playwright, Chrome DevTools if not testing
- **Documentation**: Keep Context7 if used, disable others
- **Experimental**: Disable all experimental servers

### Option 2: Disable by Frequency
- **Daily use**: Keep
- **Weekly use**: Keep if essential
- **Monthly use**: Disable
- **Never used**: Disable immediately

### Option 3: Disable by Tool Count
- Disable servers with many tools first
- Keep servers with few essential tools
- Aim for ≤ 30 tools total (safety margin)

## Example: Reducing from 50+ to <40 Tools

**Before**:
- GitHub: 15 tools
- Browser: 8 tools
- Context7: 12 tools
- Chrome DevTools: 10 tools
- Playwright: 5 tools
- File System: 8 tools
- **Total: 58 tools** ❌

**After** (disable Chrome DevTools, Playwright, File System):
- GitHub: 15 tools
- Browser: 8 tools
- Context7: 12 tools
- **Total: 35 tools** ✅

## Maintenance

### Quarterly Review
1. Run `python scripts/quarterly_cleanup.py`
2. Review MCP server usage
3. Disable unused servers
4. Document changes in `MCP_TOOLS_AUDIT.md`

### When to Re-enable
- Starting a new feature that needs specific tools
- Temporarily enable, use, then disable
- Don't leave servers enabled "just in case"

## Troubleshooting

### Can't Find MCP Settings?
1. Check Cursor version (MCP support in recent versions)
2. Look in workspace settings (`.cursor/` folder)
3. Check Cursor documentation for your version
4. Try searching settings for "protocol" or "context"

### Tools Still Showing After Disabling?
1. Restart Cursor IDE completely
2. Clear Cursor cache if available
3. Check for multiple configuration files
4. Verify settings were saved

### Need Specific Server?
1. Enable only when needed
2. Disable immediately after use
3. Document which servers you need for which tasks
4. Create a "server activation checklist" for common tasks

## Best Practices

### ✅ **Minimal Active Set**
- Keep only 2-3 essential servers active
- Enable others only when needed
- Disable immediately after use

### ✅ **Document Your Setup**
- Maintain a list of active servers
- Note which servers are for which tasks
- Update quarterly

### ✅ **Monitor Performance**
- Watch for "exceeding limit" warnings
- Track response times
- Adjust server count based on performance

## Current ODRAS MCP Servers

*Update this section as you audit your setup*

| Server | Tools | Status | Purpose | Last Used |
|--------|-------|--------|---------|-----------|
| - | - | - | - | - |

---

**Action Items**:
1. ✅ Access Cursor MCP settings
2. ⏳ List all active servers and tool counts
3. ⏳ Categorize by priority
4. ⏳ Disable low-priority servers
5. ⏳ Verify tool count ≤ 40
6. ⏳ Document active servers above

*Last Updated: November 2024*

