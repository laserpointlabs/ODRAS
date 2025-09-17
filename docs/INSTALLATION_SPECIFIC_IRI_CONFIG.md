# Installation-Specific IRI Configuration for ODRAS

## Overview

ODRAS should use installation-specific base URIs that properly identify the responsible authority and installation. This follows military/government domain conventions and enables proper resource attribution.

## Configuration Structure

### Installation-Specific Base URIs

**Format**: `https://{installation}.{service}.{tld}`

**Examples**:
- `https://xma-adt.usn.mil` (Navy XMA-ADT)
- `https://afit-research.usaf.mil` (Air Force Institute of Technology)
- `https://tradoc-sim.usa.mil` (Army TRADOC)
- `https://boeing-defense.boeing.com` (Industry partner)

### Environment Variables

```bash
# XMA-ADT (Navy) Installation
INSTALLATION_NAME=XMA-ADT
INSTALLATION_TYPE=usn
TOP_LEVEL_DOMAIN=mil
INSTALLATION_BASE_URI=https://xma-adt.usn.mil
INSTALLATION_ORGANIZATION=U.S. Navy XMA-ADT
INSTALLATION_PROGRAM_OFFICE=Naval Air Systems Command
AUTHORITY_CONTACT=admin@xma-adt.usn.mil
```

## IRI Structure

### Hierarchical Resource IRIs

```
Base: https://xma-adt.usn.mil/

Core Resources:
├── /core/ontologies/{name}                    # Installation core ontologies
├── /core/vocabularies/{name}                  # Installation vocabularies
└── /admin/{resource_type}/{name}              # Administrative resources

Program/Project Resources:
├── /program/{program}/project/{project}/files/{file-id}
├── /program/{program}/project/{project}/knowledge/{asset-id}
├── /program/{program}/project/{project}/ontologies/{name}
├── /program/{program}/project/{project}/workflows/{workflow-id}
└── /program/{program}/project/{project}/users/{username}

Examples:
├── https://xma-adt.usn.mil/program/abc/project/caee53ce-4b7a/files/requirements.pdf
├── https://xma-adt.usn.mil/program/abc/project/caee53ce-4b7a/knowledge/mission-analysis
├── https://xma-adt.usn.mil/program/abc/project/caee53ce-4b7a/ontologies/requirements
└── https://xma-adt.usn.mil/core/ontologies/odras-base
```

### Service Branch Codes

| Branch | Code | Domain Pattern |
|--------|------|----------------|
| Navy | `usn` | `*.usn.mil` |
| Air Force | `usaf` | `*.usaf.mil` |
| Army | `usa` | `*.usa.mil` |
| Marines | `usmc` | `*.usmc.mil` |
| Space Force | `ussf` | `*.ussf.mil` |
| Coast Guard | `uscg` | `*.uscg.mil` |
| Industry | `industry` | `*.{company}.com` |
| Research | `research` | `*.edu` or `*.gov` |

### Top-Level Domains

| Domain | Usage | Authority |
|--------|-------|-----------|
| `.mil` | Military installations | DoD |
| `.gov` | Government agencies | GSA |
| `.com` | Industry partners | Commercial |
| `.edu` | Research institutions | Educational |
| `.org` | Non-profit organizations | Public |

## Benefits

### 1. **Clear Authority**
- Each IRI clearly identifies the responsible installation
- Authority contact is embedded in the domain structure
- Proper chain of responsibility for resource management

### 2. **Scalability**
- Multiple installations can coexist without conflicts
- Each installation maintains its own namespace authority
- Resources can reference across installations safely

### 3. **Compliance**
- Follows DoD domain naming conventions
- Supports multi-tenant deployment scenarios
- Enables proper security and access controls

### 4. **Interoperability**
- Resources can be shared between installations
- IRIs are globally unique and dereferenceable
- Supports federation and collaboration scenarios

## Implementation Plan

### Phase 1: Configuration Enhancement
1. **Update Settings class** with installation-specific fields
2. **Create InstallationIRIService** for proper IRI generation
3. **Add IRI columns** to all resource tables
4. **Implement automatic IRI minting** on resource creation

### Phase 2: IRI Resolution
1. **Create IRI resolution endpoints** to make IRIs dereferenceable
2. **Add IRI display** in frontend with copy functionality
3. **Implement IRI validation** and conflict detection
4. **Add IRI migration tools** for existing resources

### Phase 3: Cross-Installation Features
1. **Federation support** for multi-installation scenarios
2. **Resource sharing protocols** between installations
3. **Authority verification** for external IRI references
4. **Backup and recovery** for IRI persistence

## Example Configuration Files

See the installation-specific configuration examples in the ODRAS documentation for complete setup instructions for different installation types.


