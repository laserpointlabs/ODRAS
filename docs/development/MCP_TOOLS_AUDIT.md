# MCP Tools Audit Guide

*How to review and manage MCP (Model Context Protocol) tools in Cursor IDE*

## Overview

MCP tools extend Cursor's capabilities by providing access to external services and resources. However, having too many active tools can consume memory and credits unnecessarily.

## Current State

### Active MCP Tools
Based on the `list_mcp_resources` API call, **no MCP resources are currently active** in this session.

### MCP Infrastructure in Codebase
ODRAS has MCP infrastructure for DAS (Domain Analysis System):
- **Database**: `das_mcp_servers` table stores registered MCP servers
- **Client**: `backend/services/das_mcp_client.py` implements MCP client interface
- **Interface**: `backend/services/mcp_client_interface.py` defines MCP abstractions

### Configuration Files Found
- `.playwright-mcp/ontology.json` - Playwright MCP configuration
- `.playwright-mcp/test-ontology.json` - Test ontology configuration

## How to Audit MCP Tools

### 1. Check Cursor IDE Settings
MCP tools are configured in Cursor IDE settings, not in the codebase:
1. Open Cursor Settings (Cmd/Ctrl + ,)
2. Search for "MCP" or "Model Context Protocol"
3. Review active MCP servers/tools
4. Disable unused tools

### 2. Check via API (If Available)
```python
from mcp import list_mcp_resources
resources = list_mcp_resources()
# Review active resources
```

### 3. Review Database (For DAS MCP Servers)
```sql
SELECT name, server_type, status, is_active, last_health_check_at
FROM das_mcp_servers
WHERE is_active = TRUE
ORDER BY name;
```

## Best Practices

### ✅ **Keep Only Active Tools**
- Disable tools you're not actively using
- Enable tools only when needed for specific tasks
- Review quarterly during cleanup

### ✅ **Monitor Resource Usage**
- Track memory usage with multiple tools active
- Monitor credit consumption
- Disable tools that consume excessive resources

### ✅ **Document Active Tools**
- Maintain a list of active MCP tools and their purposes
- Document when tools are enabled/disabled
- Note any performance impacts

## Recommended Actions

1. **Review Cursor Settings**: Check IDE settings for active MCP tools
2. **Disable Unused Tools**: Turn off tools not currently needed
3. **Document Active Tools**: Maintain a list in this file
4. **Quarterly Review**: Include MCP tool audit in quarterly cleanup

## Active Tools Log

*Update this section as you enable/disable tools*

| Tool Name | Purpose | Status | Last Used | Notes |
|-----------|---------|--------|-----------|-------|
| - | - | - | - | No active tools currently |

---

*Last Updated: November 2024*

