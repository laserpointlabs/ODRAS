# Installation-Specific IRI Configuration for ODRAS<br>
<br>
## Overview<br>
<br>
ODRAS should use installation-specific base URIs that properly identify the responsible authority and installation. This follows military/government domain conventions and enables proper resource attribution.<br>
<br>
## Configuration Structure<br>
<br>
### Installation-Specific Base URIs<br>
<br>
**Format**: `https://{installation}.{service}.{tld}`<br>
<br>
**Examples**:<br>
- `https://xma-adt.usn.mil` (Navy XMA-ADT)<br>
- `https://afit-research.usaf.mil` (Air Force Institute of Technology)<br>
- `https://tradoc-sim.usa.mil` (Army TRADOC)<br>
- `https://boeing-defense.boeing.com` (Industry partner)<br>
<br>
### Environment Variables<br>
<br>
```bash<br>
# XMA-ADT (Navy) Installation<br>
INSTALLATION_NAME=XMA-ADT<br>
INSTALLATION_TYPE=usn<br>
TOP_LEVEL_DOMAIN=mil<br>
INSTALLATION_BASE_URI=https://xma-adt.usn.mil<br>
INSTALLATION_ORGANIZATION=U.S. Navy XMA-ADT<br>
INSTALLATION_PROGRAM_OFFICE=Naval Air Systems Command<br>
AUTHORITY_CONTACT=admin@xma-adt.usn.mil<br>
```<br>
<br>
## IRI Structure<br>
<br>
### Hierarchical Resource IRIs<br>
<br>
```<br>
Base: https://xma-adt.usn.mil/<br>
<br>
Core Resources:<br>
├── /core/ontologies/{name}                    # Installation core ontologies<br>
├── /core/vocabularies/{name}                  # Installation vocabularies<br>
└── /admin/{resource_type}/{name}              # Administrative resources<br>
<br>
Program/Project Resources:<br>
├── /program/{program}/project/{project}/files/{file-id}<br>
├── /program/{program}/project/{project}/knowledge/{asset-id}<br>
├── /program/{program}/project/{project}/ontologies/{name}<br>
├── /program/{program}/project/{project}/workflows/{workflow-id}<br>
└── /program/{program}/project/{project}/users/{username}<br>
<br>
Examples:<br>
├── https://xma-adt.usn.mil/program/abc/project/caee53ce-4b7a/files/requirements.pdf<br>
├── https://xma-adt.usn.mil/program/abc/project/caee53ce-4b7a/knowledge/mission-analysis<br>
├── https://xma-adt.usn.mil/program/abc/project/caee53ce-4b7a/ontologies/requirements<br>
└── https://xma-adt.usn.mil/core/ontologies/odras-base<br>
```<br>
<br>
### Service Branch Codes<br>
<br>
| Branch | Code | Domain Pattern |<br>
|--------|------|----------------|<br>
| Navy | `usn` | `*.usn.mil` |<br>
| Air Force | `usaf` | `*.usaf.mil` |<br>
| Army | `usa` | `*.usa.mil` |<br>
| Marines | `usmc` | `*.usmc.mil` |<br>
| Space Force | `ussf` | `*.ussf.mil` |<br>
| Coast Guard | `uscg` | `*.uscg.mil` |<br>
| Industry | `industry` | `*.{company}.com` |<br>
| Research | `research` | `*.edu` or `*.gov` |<br>
<br>
### Top-Level Domains<br>
<br>
| Domain | Usage | Authority |<br>
|--------|-------|-----------|<br>
| `.mil` | Military installations | DoD |<br>
| `.gov` | Government agencies | GSA |<br>
| `.com` | Industry partners | Commercial |<br>
| `.edu` | Research institutions | Educational |<br>
| `.org` | Non-profit organizations | Public |<br>
<br>
## Benefits<br>
<br>
### 1. **Clear Authority**<br>
- Each IRI clearly identifies the responsible installation<br>
- Authority contact is embedded in the domain structure<br>
- Proper chain of responsibility for resource management<br>
<br>
### 2. **Scalability**<br>
- Multiple installations can coexist without conflicts<br>
- Each installation maintains its own namespace authority<br>
- Resources can reference across installations safely<br>
<br>
### 3. **Compliance**<br>
- Follows DoD domain naming conventions<br>
- Supports multi-tenant deployment scenarios<br>
- Enables proper security and access controls<br>
<br>
### 4. **Interoperability**<br>
- Resources can be shared between installations<br>
- IRIs are globally unique and dereferenceable<br>
- Supports federation and collaboration scenarios<br>
<br>
## Implementation Plan<br>
<br>
### Phase 1: Configuration Enhancement<br>
1. **Update Settings class** with installation-specific fields<br>
2. **Create InstallationIRIService** for proper IRI generation<br>
3. **Add IRI columns** to all resource tables<br>
4. **Implement automatic IRI minting** on resource creation<br>
<br>
### Phase 2: IRI Resolution<br>
1. **Create IRI resolution endpoints** to make IRIs dereferenceable<br>
2. **Add IRI display** in frontend with copy functionality<br>
3. **Implement IRI validation** and conflict detection<br>
4. **Add IRI migration tools** for existing resources<br>
<br>
### Phase 3: Cross-Installation Features<br>
1. **Federation support** for multi-installation scenarios<br>
2. **Resource sharing protocols** between installations<br>
3. **Authority verification** for external IRI references<br>
4. **Backup and recovery** for IRI persistence<br>
<br>
## Example Configuration Files<br>
<br>
See the installation-specific configuration examples in the ODRAS documentation for complete setup instructions for different installation types.<br>
<br>
<br>
<br>
<br>
<br>
<br>
<br>
<br>
<br>
<br>
<br>
<br>
<br>
<br>
<br>
<br>


