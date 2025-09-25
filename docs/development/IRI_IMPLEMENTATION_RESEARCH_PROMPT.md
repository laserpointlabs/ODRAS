# IRI Implementation Research & Implementation Prompt

## 🎯 Research Objective

**Research and implement RFC 3987-compliant IRI system for ODRAS** that makes all resources properly dereferenceable while following military/defense domain conventions.

## 📋 Current State Analysis

### ✅ What EXISTS in ODRAS
1. **IRI Resolution API**: `backend/api/iri_resolution.py` - Basic framework exists
2. **Resource URI Service**: `backend/services/resource_uri_service.py` - Partial implementation
3. **Installation IRI Service**: `backend/services/installation_iri_service.py` - Configuration system
4. **Namespace URI Generator**: `backend/services/namespace_uri_generator.py` - Organizational patterns
5. **IRI Documentation**: `docs/IRI_SYSTEM_OVERVIEW.md` and related docs

### 🚫 What's BROKEN (From Documentation Analysis)
1. **Double "odras" Path Bug**:
   ```
   Generated: https://xma-adt.usnc.mil/odras/odras/core/d6392b43.../
   Should Be: https://xma-adt.usnc.mil/program/core/project/d6392b43.../
   ```

2. **Projects Not Dereferenceable**:
   ```bash
   curl "/iri/resolve?iri=https://xma-adt.usnc.mil/projects/UUID"
   # Returns: {"detail":"IRI not found"}
   ```

3. **Missing Database Integration**: IRIs are text-only, not stored persistently

4. **Wrong Path Structure**: Using `/odras/` instead of `/program/project/` pattern

## 🔍 RFC 3987 Compliance Research

### Core Requirements from RFC 3987
**Research Tasks:**
1. **Syntax Rules**: What characters are valid in IRIs vs URIs?
2. **Unicode Handling**: How should ODRAS handle international characters?
3. **Normalization**: What normalization rules apply to IRIs?
4. **URI Conversion**: How to properly convert IRIs to URIs for compatibility?
5. **Security Considerations**: What security implications exist for IRI processing?

### Web Research Questions
1. **W3C Best Practices**: What are current W3C recommendations for IRI generation in semantic web applications?
2. **Government Standards**: Do DoD or military systems have specific IRI/URI standards?
3. **Ontology IRIs**: What are best practices for ontology namespace IRIs?
4. **Dereferenceable IRIs**: How should IRIs resolve to meaningful content?
5. **Content Negotiation**: What formats should dereferenceable IRIs support?

## 🏗️ Technical Investigation Required

### Current ODRAS Implementation Audit
**Investigate these specific areas:**

1. **ResourceURIService Analysis** (`backend/services/resource_uri_service.py`):
   ```python
   # Current implementation issues to research:
   def generate_project_uri(self, project_id: str) -> str:
       # Problem: Adds "/odras" prefix incorrectly
       # Research: Should this follow installation patterns from docs?
       return f"{base_uri}/odras/{namespace_path}/{project_id}/"
   ```

2. **IRI Resolution Database Function** (PostgreSQL):
   ```sql
   -- Current issue: Projects not included in resolve_iri() function
   -- Research: How should project IRIs be resolved to metadata?
   SELECT * FROM resolve_iri('https://xma-adt.usnc.mil/project/UUID');
   ```

3. **Installation Configuration** (`.env` patterns):
   ```bash
   # Research: Are these the correct patterns from specification?
   INSTALLATION_BASE_URI=https://xma-adt.usnc.mil
   # Should generate: /program/{namespace}/project/{uuid}/
   ```

### RFC 3987 Compliance Gaps
**Research specific compliance issues:**

1. **Character Encoding**: Does ODRAS properly handle Unicode in IRIs?
2. **Normalization**: Are IRIs normalized according to RFC 3987?
3. **Validation**: Does current validation follow RFC 3987 syntax rules?
4. **Resolution**: Do resolved IRIs return proper HTTP responses per RFC 3987?

## 🎯 Implementation Plan Research

### Phase 1: Standards Compliance Research
**Web Research Tasks:**
1. **Read RFC 3987 specification** - Understand syntax, processing, and security rules
2. **Study W3C IRI Guidelines** - Best practices for semantic web IRIs
3. **Research Military URI Standards** - Check if DoD has specific requirements
4. **Review Python IRI Libraries** - Find RFC 3987-compliant libraries for validation

### Phase 2: ODRAS-Specific Investigation
**Codebase Research Tasks:**
1. **Audit all IRI generation** - Find every place URIs/IRIs are created
2. **Test current resolution** - Which IRIs work vs which return "not found"?
3. **Database schema analysis** - What IRI storage exists vs what's needed?
4. **Configuration validation** - Are installation settings following specification?

### Phase 3: Gap Analysis
**Compare ODRAS vs RFC 3987:**
1. **Syntax compliance** - Are generated IRIs valid per RFC 3987?
2. **Resolution compliance** - Do resolved IRIs follow HTTP standards?
3. **Unicode support** - Can ODRAS handle international characters properly?
4. **Security compliance** - Are RFC 3987 security considerations addressed?

## 🧪 Testing Framework Required

### RFC 3987 Compliance Tests
**Create test cases for:**
1. **IRI Syntax Validation**: Test against RFC 3987 ABNF grammar
2. **Unicode Character Handling**: Test international characters in resource names
3. **Resolution Testing**: Verify all generated IRIs are dereferenceable
4. **Content Negotiation**: Test different format responses (JSON, RDF, HTML)

### Current Bug Reproduction
**Test cases to reproduce known issues:**
```bash
# Test 1: Double "odras" path bug
curl "http://localhost:8000/api/das2/chat" -d '{"message": "What is my project URI?"}'
# Expected: NO double "odras" in path

# Test 2: Project IRI resolution
PROJECT_IRI="https://xma-adt.usnc.mil/program/core/project/PROJECT_ID"
curl "http://localhost:8000/iri/resolve?iri=$PROJECT_IRI"
# Expected: Project metadata, not "IRI not found"

# Test 3: IRI validation
curl "http://localhost:8000/iri/validate?iri=$PROJECT_IRI"
# Expected: Valid per RFC 3987
```

## 📚 Documentation Research

### Required Reading
1. **RFC 3987 Full Text**: Official IRI specification
2. **W3C Architecture of the World Wide Web**: Best practices context
3. **W3C Cool URIs for the Semantic Web**: Practical guidelines
4. **ODRAS IRI Documentation**: `docs/IRI_SYSTEM_OVERVIEW.md` and related files

### Specification References to Add
**Update these files with proper RFC 3987 references:**
1. `backend/services/resource_uri_service.py` ✅ (Done)
2. `backend/api/iri_resolution.py` ✅ (Done)
3. `backend/services/installation_iri_service.py` (Needs RFC reference)
4. `backend/services/namespace_uri_generator.py` (Needs RFC reference)

## 🔧 Implementation Priorities

### Priority 1: Fix Path Generation (Critical)
- **Issue**: Double "odras" path bug
- **Impact**: IRIs are malformed and non-dereferenceable
- **Research**: Understand intended path structure from specification

### Priority 2: Database Integration (High)
- **Issue**: IRIs are text-only, not persistent objects
- **Impact**: IRIs can't be resolved to actual resources
- **Research**: How to store and resolve IRIs per RFC 3987

### Priority 3: RFC 3987 Compliance (Medium)
- **Issue**: No formal RFC 3987 validation
- **Impact**: IRIs may not be syntactically correct
- **Research**: RFC 3987 syntax rules and validation requirements

### Priority 4: Content Negotiation (Low)
- **Issue**: Only JSON responses for IRI resolution
- **Impact**: Not following semantic web best practices
- **Research**: RFC 3987 + HTTP content negotiation standards

## 🎯 Success Criteria

### RFC 3987 Compliance
- ✅ **Valid IRI Syntax**: All generated IRIs pass RFC 3987 validation
- ✅ **Unicode Support**: Proper handling of international characters
- ✅ **Normalization**: IRIs properly normalized per specification
- ✅ **URI Mapping**: Correct IRI-to-URI conversion when needed

### ODRAS Functionality
- ✅ **Dereferenceable IRIs**: All project/ontology/file IRIs resolve to metadata
- ✅ **Correct Path Structure**: Follow installation specification patterns
- ✅ **Database Persistence**: IRIs stored and retrievable from database
- ✅ **Access Control**: Proper permissions for IRI resolution

### Documentation
- ✅ **RFC 3987 References**: All IRI code references RFC 3987 compliance
- ✅ **Specification Alignment**: Code comments explain RFC 3987 conformance
- ✅ **Testing Documentation**: RFC 3987 compliance test procedures

---

## 🚀 Next Steps

1. **Research RFC 3987 thoroughly** - Understand all syntax and processing requirements
2. **Audit current ODRAS IRI implementation** against RFC 3987 requirements
3. **Fix critical path generation bugs** identified in documentation
4. **Implement RFC 3987-compliant validation** for all generated IRIs
5. **Add comprehensive testing** for standards compliance
6. **Update all IRI-related code** with proper RFC 3987 references

**Goal: Make ODRAS IRI system fully RFC 3987-compliant and properly dereferenceable for semantic web interoperability.** 🎯
