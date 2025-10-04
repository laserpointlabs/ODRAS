# ODRAS Development TODO

## 🚨 Critical Issues

### 1. IRI/URI Standardization (Major Refactor)
**Status**: 🔴 Not Started
**Priority**: High
**Branch**: `feature/iri-standardization` (needs dedicated branch)

**Description**: Standardize terminology and implementation to use IRI consistently throughout the codebase.

**Tasks**:
- [ ] Create dedicated branch for IRI standardization
- [ ] Rename `ResourceURIService` → `ResourceIRIService`
- [ ] Update all API responses to use "iri" instead of "uri"
- [ ] Standardize frontend variable names and UI labels
- [ ] Update database column names where appropriate
- [ ] Update documentation and comments
- [ ] Comprehensive testing of IRI generation
- [ ] Migration plan for existing data

**Impact**: Major refactor affecting multiple services, APIs, and frontend components.

---

## 🐛 Bug Fixes

### 2. Project URI Display Fix
**Status**: ✅ Completed
**Priority**: High
**Date**: 2024-12-19

**Description**: Fixed project information page to show complete URI with installation base URI.

**Changes Made**:
- Updated `frontend/app.html` to use `INSTALLATION_CONFIG.baseUri` in project URI construction
- Now displays: `https://xma-adt.usnc.mil/odras/core/{project-id}/`
- Instead of: `http://odras/core/{project-id}/`

### 3. Duplicate "odras" in IRI Generation
**Status**: ✅ Completed
**Priority**: High
**Date**: 2024-12-19

**Description**: Fixed hardcoded duplicate "odras" in ResourceURIService URI generation.

**Changes Made**:
- Removed hardcoded `/odras/` from `ResourceURIService` methods
- Updated database records to remove duplicate "odras"
- Fixed IRI display to show "No element selected" when ontology is deleted

---

## 🔧 Technical Debt

### 4. Frontend IRI Display Cleanup
**Status**: ✅ Completed
**Priority**: Medium
**Date**: 2024-12-19

**Description**: Fixed IRI display to properly clear when ontology is deleted.

**Changes Made**:
- Updated `updateElementIriDisplay()` to check for active ontology
- Shows "No element selected" when no ontology is active
- Hides copy button when no element is selected

### 5. Database Migration Cleanup
**Status**: 🔴 Not Started
**Priority**: Low

**Description**: Clean up temporary database fix script and ensure all migrations are properly documented.

**Tasks**:
- [ ] Remove temporary `fix_duplicate_odras_iris.py` script (already deleted)
- [ ] Document the database fix in migration history
- [ ] Ensure all URI generation uses centralized service

### 6. Connection Pool Management
**Status**: 🔴 Not Started
**Priority**: High

**Description**: Improve connection pool management to prevent pool exhaustion, particularly during Playwright testing sessions.

**Tasks**:
- [ ] Investigate current connection pool configuration
- [ ] Implement proper connection cleanup in test teardown
- [ ] Add connection pool monitoring and alerts
- [ ] Optimize connection pool size for testing workloads
- [ ] Add connection pool health checks
- [ ] Implement connection timeout handling
- [ ] Add connection pool metrics and logging

---

## 🚀 Feature Improvements

### 7. Project Access Permissions
**Status**: 🔴 Not Started
**Priority**: Medium

**Description**: Fix project access issues where users can't see projects they should have access to.

**Tasks**:
- [ ] Investigate project membership validation
- [ ] Fix project dropdown population
- [ ] Ensure proper project selection workflow
- [ ] Test with different user roles

### 7. Installation Configuration Management
**Status**: 🔴 Not Started
**Priority**: Low

**Description**: Improve installation configuration loading and validation.

**Tasks**:
- [ ] Add configuration validation on startup
- [ ] Improve error handling for missing configuration
- [ ] Add configuration health checks
- [ ] Document configuration requirements

---

## 📋 Code Quality

### 8. Frontend Code Organization
**Status**: 🔴 Not Started
**Priority**: Low

**Description**: Improve frontend code organization and reduce duplication.

**Tasks**:
- [ ] Extract common IRI handling functions
- [ ] Consolidate duplicate code patterns
- [ ] Improve error handling consistency
- [ ] Add JSDoc comments for complex functions

### 9. Backend Service Consistency
**Status**: 🔴 Not Started
**Priority**: Low

**Description**: Ensure consistent patterns across backend services.

**Tasks**:
- [ ] Standardize error handling across services
- [ ] Improve logging consistency
- [ ] Add service health checks
- [ ] Document service interfaces

---

## 🧪 Testing

### 10. IRI Generation Testing
**Status**: 🔴 Not Started
**Priority**: High

**Description**: Comprehensive testing of IRI generation across all services.

**Tasks**:
- [ ] Unit tests for ResourceURIService
- [ ] Integration tests for IRI generation
- [ ] Frontend tests for IRI display
- [ ] End-to-end tests for complete IRI workflow

---

## 📚 Documentation

### 11. IRI Standards Documentation
**Status**: 🔴 Not Started
**Priority**: Medium

**Description**: Document IRI standards and usage patterns for the project.

**Tasks**:
- [ ] Create IRI standards guide
- [ ] Document URI vs IRI usage decisions
- [ ] Add examples of proper IRI construction
- [ ] Update API documentation

---

## 🎯 Next Actions

1. **Immediate**: Test the completed fixes (project URI display, IRI cleanup)
2. **Short-term**: Create branch for IRI standardization planning
3. **Medium-term**: Address project access permissions
4. **Long-term**: Implement comprehensive IRI standardization

---

## 📝 Notes

- All completed items are marked with ✅ and include completion date
- High priority items should be addressed first
- IRI standardization is a major refactor that needs careful planning
- Consider breaking large tasks into smaller, manageable chunks
- Always test changes thoroughly before marking as complete

---

*Last Updated: 2024-12-19*


