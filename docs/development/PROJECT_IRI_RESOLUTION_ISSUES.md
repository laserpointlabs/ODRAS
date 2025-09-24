# Project IRI Resolution System - Issues & Implementation Plan

**Status:** Documented for Future Implementation
**Priority:** Medium - Functional but not properly dereferenceable
**Date:** September 24, 2025

## 🎯 Executive Summary

ODRAS has a **partial IRI resolution system** that exists but is not working properly for projects. While the core DAS functionality works perfectly with enhanced project context and sources, project IRIs are currently **text-based only** and not properly dereferenceable.

## 🔍 Investigation Findings

### ✅ What's Working
- **IRI Resolution Endpoint:** `/iri/resolve` exists and functions
- **IRI Validation Endpoint:** `/iri/validate` works
- **Installation Config:** Properly configured in `.env`
- **File & Knowledge Asset IRIs:** May work (not tested extensively)

### ❌ What's Broken

#### 1. **Double "odras" Path Bug**
```
Currently Generated: https://xma-adt.usnc.mil/odras/odras/core/d6392b43-11b5-47bd-8b37-522424aea097/
Should Be:          https://xma-adt.usnc.mil/program/core/project/d6392b43-11b5-47bd-8b37-522424aea097/
```

#### 2. **Wrong Path Structure**
- **Expected Format:** `{base_uri}/program/{namespace}/project/{uuid}/`
- **Generated Format:** `{base_uri}/odras/{namespace}/project/{uuid}/` (with double "odras")
- **Issue:** Resource URI service not following installation IRI patterns

#### 3. **Projects Not Dereferenceable**
```bash
curl "http://localhost:8000/iri/resolve?iri=https://xma-adt.usnc.mil/odras/projects/d6392b43-11b5-47bd-8b37-522424aea097/"
# Returns: {"detail":"IRI not found"}
```

#### 4. **Missing Database Integration**
- Projects not registered in `resolve_iri()` database function
- IRIs are **text-only generation**, not **persistent objects**
- No database storage of canonical project IRIs

## 🏗️ Current Architecture Analysis

### ResourceURIService Issues
**File:** `backend/services/resource_uri_service.py`

**Current Implementation:**
```python
def generate_project_uri(self, project_id: str) -> str:
    # Issues:
    # 1. Adds "/odras" prefix incorrectly
    # 2. Doesn't follow installation patterns
    # 3. Not stored in database
    return f"{base_uri}/odras/{namespace_path}/{project_id}/"
```

### Installation IRI Service
**File:** `backend/services/installation_iri_service.py`

**Expected Pattern:**
```python
# From .env examples:
# https://xma-adt.usnc.mil/program/abc/project/12345678-1234-1234-1234-123456789abc
```

### IRI Resolution Database
**Function:** `resolve_iri()` (PostgreSQL)
- **Status:** Exists but incomplete
- **Missing:** Project registration logic
- **Issue:** Projects not included in resolution logic

## 🎯 Implementation Plan

### Phase 1: Fix URI Generation
1. **Update ResourceURIService** to follow installation patterns
2. **Remove double "odras"** from path generation
3. **Use proper program/project structure** from `.env` examples

### Phase 2: Database Integration
1. **Add project IRI storage** to projects table
2. **Update project creation** to generate and store canonical IRI
3. **Implement project resolution** in `resolve_iri()` function

### Phase 3: Make IRIs Dereferenceable
1. **Register projects** in IRI resolution system
2. **Return project metadata** when IRI is resolved
3. **Test end-to-end resolution** workflow

### Phase 4: Content Negotiation (Future)
1. **RDF/Turtle formats** for project metadata
2. **JSON-LD** structured data
3. **HTML** human-readable project pages

## 📋 Technical Requirements

### Database Changes Needed
```sql
-- Add canonical IRI storage
ALTER TABLE public.projects ADD COLUMN canonical_iri TEXT;
CREATE UNIQUE INDEX idx_projects_canonical_iri ON public.projects(canonical_iri);

-- Update resolve_iri() function to handle projects
-- (Implementation details in separate migration)
```

### Code Changes Required

#### 1. ResourceURIService Fix
```python
def generate_project_uri(self, project_id: str) -> str:
    namespace_path, project_name = self._get_project_namespace_info(project_id)

    if namespace_path:
        # Follow installation pattern: program/{namespace}/project/{uuid}/
        return f"{self.installation_base_uri}/program/{namespace_path}/project/{project_id}/"
    else:
        # Fallback for projects without namespace
        return f"{self.installation_base_uri}/projects/{project_id}/"
```

#### 2. Project Creation Integration
```python
# When creating project, generate and store canonical IRI
canonical_iri = uri_service.generate_project_uri(project_id)
# Store in database for future resolution
```

#### 3. IRI Resolution Function
```sql
-- Add project case to resolve_iri() PostgreSQL function
WHEN resource_type = 'project' THEN
    -- Return project metadata for resolution
```

## 🧪 Testing Plan

### Test Cases Required
1. **IRI Generation:** Correct format without double "odras"
2. **IRI Resolution:** Projects return proper metadata
3. **IRI Validation:** Generated IRIs pass validation
4. **Access Control:** Proper permissions for project access
5. **Namespace Integration:** Projects with/without namespaces

### Test Commands
```bash
# 1. Test IRI generation
curl "http://localhost:8000/api/das2/chat" -d '{"message": "What is the project URI?"}'

# 2. Test IRI resolution
curl "http://localhost:8000/iri/resolve?iri=https://xma-adt.usnc.mil/program/core/project/PROJECT_ID"

# 3. Test IRI validation
curl "http://localhost:8000/iri/validate?iri=GENERATED_IRI"
```

## 🔄 Current Workaround

**Status:** DAS returns project URIs but they are **not dereferenceable**
- Users can see the URI in DAS responses
- URIs are formatted (mostly) correctly
- But URIs return "IRI not found" when accessed
- **Impact:** Low - core functionality works, just no true dereferenceable IRIs

## 🎯 Success Criteria

When properly implemented:
1. ✅ **Generated IRIs follow installation patterns**
2. ✅ **IRIs are dereferenceable** (return metadata when accessed)
3. ✅ **IRIs are stored persistently** in database
4. ✅ **IRIs validate correctly** against installation config
5. ✅ **Access control works** (users can only access their projects)
6. ✅ **Content negotiation** (JSON, RDF, HTML responses)

## 📚 Related Documentation

- **Installation IRI Service:** `backend/services/installation_iri_service.py`
- **Resource URI Service:** `backend/services/resource_uri_service.py`
- **IRI Resolution API:** `backend/api/iri_resolution.py`
- **Environment Configuration:** `.env` (IRI examples on lines 17-21)

## 🏷️ Labels
`enhancement` `iri` `resolution` `database` `uri-generation` `medium-priority`

---

**Note:** This issue was discovered during DAS project context enhancement work. The core DAS functionality with comprehensive project details, sources, and enhanced logging is **working perfectly**. This IRI issue is a separate concern that can be addressed in a future sprint.
