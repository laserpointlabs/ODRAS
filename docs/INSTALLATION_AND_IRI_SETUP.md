# ODRAS Installation Setup and IRI System

## Overview

This document describes how to set up an ODRAS installation with proper installation-specific IRIs and federated access capabilities. This enables cross-installation artifact sharing and external system integration.

## Table of Contents

1. [Installation Configuration](#installation-configuration)
2. [IRI System Setup](#iri-system-setup) 
3. [Federated Access](#federated-access)
4. [External System Integration](#external-system-integration)
5. [Security and Access Control](#security-and-access-control)
6. [Troubleshooting](#troubleshooting)

---

## Installation Configuration

### 1. Environment Setup

Copy the configuration template and customize for your installation:

```bash
cd /path/to/odras
cp config/installation-specific.env.template .env
```

### 2. Installation-Specific Configuration

Edit your `.env` file with installation-specific values:

```bash
# =============================================================================
# INSTALLATION-SPECIFIC IRI CONFIGURATION
# =============================================================================

# XMA-ADT (Navy) Installation Example
INSTALLATION_NAME=XMA-ADT
INSTALLATION_TYPE=usn
TOP_LEVEL_DOMAIN=mil
INSTALLATION_BASE_URI=https://xma-adt.usn.mil
INSTALLATION_ORGANIZATION=U.S. Navy XMA-ADT
INSTALLATION_PROGRAM_OFFICE=Naval Air Systems Command
AUTHORITY_CONTACT=admin@xma-adt.usn.mil
```

### 3. Service Branch Configurations

#### Navy Installation
```bash
INSTALLATION_NAME=XMA-ADT
INSTALLATION_TYPE=usn
TOP_LEVEL_DOMAIN=mil
INSTALLATION_BASE_URI=https://xma-adt.usn.mil
```

#### Air Force Installation  
```bash
INSTALLATION_NAME=AFIT-RESEARCH
INSTALLATION_TYPE=usaf
TOP_LEVEL_DOMAIN=mil
INSTALLATION_BASE_URI=https://afit-research.usaf.mil
```

#### Army Installation
```bash
INSTALLATION_NAME=TRADOC-SIM
INSTALLATION_TYPE=usa
TOP_LEVEL_DOMAIN=mil
INSTALLATION_BASE_URI=https://tradoc-sim.usa.mil
```

#### Industry Partner
```bash
INSTALLATION_NAME=BOEING-DEFENSE
INSTALLATION_TYPE=industry
TOP_LEVEL_DOMAIN=com
INSTALLATION_BASE_URI=https://boeing-defense.boeing.com
```

### 4. Database Migration

Run the IRI system migration:

```bash
cd /path/to/odras
python -c "
import psycopg2
from backend.services.config import Settings

settings = Settings()
conn = psycopg2.connect(
    host=settings.postgres_host,
    database=settings.postgres_database,
    user=settings.postgres_user,
    password=settings.postgres_password,
    port=settings.postgres_port
)

with open('backend/migrations/015_installation_specific_iris.sql', 'r') as f:
    migration_sql = f.read()

with conn.cursor() as cur:
    cur.execute(migration_sql)
    conn.commit()

print('✅ IRI system migration completed')
conn.close()
"
```

---

## IRI System Setup

### 1. IRI Structure

ODRAS uses hierarchical, installation-specific IRIs:

```
Base Pattern:
https://{installation}.{service}.{tld}/program/{program}/project/{project}/{resource_type}/{resource_id}

Examples:
├── Files: https://xma-adt.usn.mil/program/abc/project/xyz/files/requirements.pdf
├── Knowledge: https://xma-adt.usn.mil/program/abc/project/xyz/knowledge/mission-analysis
├── Ontologies: https://xma-adt.usn.mil/program/abc/project/xyz/ontologies/requirements
└── Core: https://xma-adt.usn.mil/core/ontologies/odras-base
```

### 2. Automatic IRI Generation

IRIs are automatically generated when resources are created:

- **Files**: Get IRIs on upload
- **Knowledge Assets**: Get IRIs during processing
- **Projects**: Get IRIs on creation
- **Users**: Get IRIs on account creation

### 3. IRI Components

Each IRI contains:
- **Installation Identity**: `xma-adt.usn.mil`
- **Hierarchical Path**: `program/abc/project/xyz`
- **Resource Type**: `files`, `knowledge`, `ontologies`
- **Unique Identifier**: UUID or sanitized name

### 4. Validation

Check your IRI configuration:

```bash
curl -X GET "http://localhost:8000/api/iri/installation-config"
```

---

## Federated Access

### 1. Public IRI Resolution

External systems can resolve any IRI from your installation:

```bash
# Resolve IRI to get access information
curl -X GET "https://xma-adt.usn.mil/api/iri/public/resolve?iri={IRI}" \
  -H "Accept: application/json"
```

**Response:**
```json
{
  "iri": "https://xma-adt.usn.mil/program/abc/project/xyz/knowledge/mission-analysis",
  "resource_type": "knowledge_asset",
  "status": "public",
  "access_urls": {
    "content": "https://xma-adt.usn.mil/api/federated/knowledge/{id}/content",
    "metadata": "https://xma-adt.usn.mil/api/federated/knowledge/{id}/metadata"
  },
  "authority": {
    "organization": "U.S. Navy XMA-ADT",
    "contact": "admin@xma-adt.usn.mil",
    "installation": "XMA-ADT"
  }
}
```

### 2. Direct Artifact Access

Once you have the access URLs, get the actual artifacts:

```bash
# Download file content
curl -X GET "https://xma-adt.usn.mil/api/federated/files/{file-id}/download" \
  -o downloaded-file.pdf

# Get knowledge asset content and analysis results
curl -X GET "https://xma-adt.usn.mil/api/federated/knowledge/{asset-id}/content" \
  -H "Accept: application/json"
```

### 3. Installation Discovery

Discover an installation's capabilities:

```bash
curl -X GET "https://xma-adt.usn.mil/api/federated/installations/discover"
```

**Response:**
```json
{
  "installation": {
    "name": "XMA-ADT",
    "type": "usn",
    "organization": "U.S. Navy XMA-ADT",
    "base_uri": "https://xma-adt.usn.mil",
    "contact": "admin@xma-adt.usn.mil"
  },
  "capabilities": {
    "supported_resource_types": ["files", "knowledge", "ontologies", "projects"],
    "supported_formats": ["json", "rdf", "turtle"],
    "federated_access": true,
    "public_resolution": true
  },
  "endpoints": {
    "iri_resolution": "https://xma-adt.usn.mil/api/iri/public/resolve",
    "file_download": "https://xma-adt.usn.mil/api/federated/files/{file_id}/download",
    "knowledge_content": "https://xma-adt.usn.mil/api/federated/knowledge/{asset_id}/content"
  }
}
```

---

## External System Integration

### 1. Python Integration Example

```python
import requests

class ODRASFederatedClient:
    def __init__(self, installation_base_uri):
        self.base_uri = installation_base_uri.rstrip('/')
    
    def resolve_iri(self, iri):
        """Resolve an ODRAS IRI to get access information."""
        response = requests.get(
            f"{self.base_uri}/api/iri/public/resolve",
            params={"iri": iri, "include_content_url": True}
        )
        response.raise_for_status()
        return response.json()
    
    def get_file_content(self, iri):
        """Download file content using IRI."""
        resolution = self.resolve_iri(iri)
        if resolution["resource_type"] != "file":
            raise ValueError("IRI does not point to a file")
        
        download_url = resolution["access_urls"]["download"]
        response = requests.get(download_url)
        response.raise_for_status()
        return response.content
    
    def get_knowledge_content(self, iri):
        """Get knowledge asset content and analysis results."""
        resolution = self.resolve_iri(iri)
        if resolution["resource_type"] != "knowledge_asset":
            raise ValueError("IRI does not point to a knowledge asset")
        
        content_url = resolution["access_urls"]["content"]
        response = requests.get(content_url)
        response.raise_for_status()
        return response.json()

# Usage Example
client = ODRASFederatedClient("https://xma-adt.usn.mil")

# Get mission analysis from XMA-ADT
analysis_iri = "https://xma-adt.usn.mil/program/abc/project/xyz/knowledge/mission-analysis"
analysis_data = client.get_knowledge_content(analysis_iri)

# Get requirements document
requirements_iri = "https://xma-adt.usn.mil/program/abc/project/xyz/files/requirements.pdf"
requirements_pdf = client.get_file_content(requirements_iri)
```

### 2. Curl Script Example

```bash
#!/bin/bash
# Federated ODRAS Access Script

INSTALLATION_BASE="https://xma-adt.usn.mil"
IRI="$1"

if [ -z "$IRI" ]; then
    echo "Usage: $0 <IRI>"
    echo "Example: $0 https://xma-adt.usn.mil/program/abc/project/xyz/knowledge/mission-analysis"
    exit 1
fi

echo "🔍 Resolving IRI: $IRI"

# Step 1: Resolve IRI
RESOLUTION=$(curl -s "$INSTALLATION_BASE/api/iri/public/resolve?iri=$IRI")
echo "📋 Resolution response:"
echo "$RESOLUTION" | jq .

# Step 2: Extract content URL and fetch content
CONTENT_URL=$(echo "$RESOLUTION" | jq -r '.access_urls.content // .access_urls.download')

if [ "$CONTENT_URL" != "null" ]; then
    echo "📄 Fetching content from: $CONTENT_URL"
    curl -s "$CONTENT_URL" | jq . || curl -s "$CONTENT_URL"
else
    echo "❌ No content URL available"
fi
```

### 3. JavaScript/Node.js Integration

```javascript
class ODRASFederatedClient {
    constructor(installationBaseUri) {
        this.baseUri = installationBaseUri.replace(/\/$/, '');
    }
    
    async resolveIRI(iri) {
        const response = await fetch(
            `${this.baseUri}/api/iri/public/resolve?iri=${encodeURIComponent(iri)}&include_content_url=true`
        );
        
        if (!response.ok) {
            throw new Error(`IRI resolution failed: ${response.status}`);
        }
        
        return await response.json();
    }
    
    async getKnowledgeContent(iri) {
        const resolution = await this.resolveIRI(iri);
        
        if (resolution.resource_type !== 'knowledge_asset') {
            throw new Error('IRI does not point to a knowledge asset');
        }
        
        const contentResponse = await fetch(resolution.access_urls.content);
        if (!contentResponse.ok) {
            throw new Error(`Content access failed: ${contentResponse.status}`);
        }
        
        return await contentResponse.json();
    }
}

// Usage
const client = new ODRASFederatedClient('https://xma-adt.usn.mil');
const analysisData = await client.getKnowledgeContent(
    'https://xma-adt.usn.mil/program/abc/project/xyz/knowledge/mission-analysis'
);
```

---

## Security and Access Control

### 1. Public vs Private Resources

**Public Resources:**
- ✅ Accessible via federated endpoints
- ✅ No authentication required
- ✅ Full content and metadata available

**Private Resources:**
- ❌ Not accessible via federated endpoints
- ❌ Returns contact information for access requests
- ❌ Metadata only (no content)

### 2. Making Resources Public

**For Files:**
```bash
# Admin can make files public via API
curl -X PUT "http://localhost:8000/api/files/{file-id}/visibility" \
  -H "Authorization: Bearer {admin-token}" \
  -H "Content-Type: application/json" \
  -d '{"visibility": "public"}'
```

**For Knowledge Assets:**
```bash
# Admin can make knowledge assets public
curl -X PUT "http://localhost:8000/api/knowledge/assets/{asset-id}/public" \
  -H "Authorization: Bearer {admin-token}" \
  -H "Content-Type: application/json" \
  -d '{"is_public": true}'
```

### 3. Access Logging

All federated access is logged with:
- Source IP address
- Requested IRI
- Access timestamp
- Resource type accessed
- Success/failure status

---

## External System Integration

### 1. Integration Patterns

**Pattern 1: Direct IRI Resolution**
```python
# External system has an IRI and wants the artifact
iri = "https://xma-adt.usn.mil/program/abc/project/xyz/knowledge/mission-analysis"
content = resolve_and_fetch_content(iri)
```

**Pattern 2: Resource Discovery**
```python
# External system discovers available resources
discovery = discover_installation("https://xma-adt.usn.mil")
available_endpoints = discovery["endpoints"]
```

**Pattern 3: Artifact Citation**
```python
# External system cites ODRAS artifacts in reports
citation = {
    "source": "U.S. Navy XMA-ADT ODRAS",
    "iri": "https://xma-adt.usn.mil/program/abc/project/xyz/knowledge/mission-analysis",
    "title": "Mission Analysis Results",
    "accessed_at": "2025-09-16T15:30:00Z",
    "authority": "admin@xma-adt.usn.mil"
}
```

### 2. Use Cases

**Cross-Installation Collaboration:**
- Norfolk Naval Base references XMA-ADT's mission analysis
- AFIT Research uses Navy requirements for academic study
- Boeing Defense integrates Navy specifications into design

**External Tool Integration:**
- Analysis tools pull ODRAS artifacts for processing
- Reporting systems cite ODRAS knowledge assets
- Simulation tools use ODRAS ontologies and data

**Knowledge Sharing:**
- Share analysis results between installations
- Reference requirements across programs
- Distribute best practices and lessons learned

### 3. Authentication for Internal Access

For authenticated access (internal users), use standard API endpoints:

```bash
# Internal access with authentication
curl -X GET "http://localhost:8000/api/knowledge/assets/{asset-id}/content" \
  -H "Authorization: Bearer {user-token}"
```

---

## API Endpoints Reference

### 1. IRI Resolution Endpoints

| Endpoint | Purpose | Authentication |
|----------|---------|----------------|
| `GET /api/iri/resolve` | Resolve IRI (internal) | Required |
| `GET /api/iri/public/resolve` | Resolve IRI (federated) | None |
| `GET /api/iri/validate` | Validate IRI format | Required |
| `GET /api/iri/installation-config` | Get installation config | Required |

### 2. Federated Access Endpoints

| Endpoint | Purpose | Authentication |
|----------|---------|----------------|
| `GET /api/federated/files/{id}/download` | Download public file | None |
| `GET /api/federated/files/{id}/metadata` | Get file metadata | None |
| `GET /api/federated/knowledge/{id}/content` | Get knowledge content | None |
| `GET /api/federated/knowledge/{id}/metadata` | Get knowledge metadata | None |
| `GET /api/federated/installations/discover` | Installation discovery | None |

### 3. Example API Calls

**Resolve IRI:**
```bash
curl "https://xma-adt.usn.mil/api/iri/public/resolve?iri=https://xma-adt.usn.mil/program/abc/project/xyz/files/analysis.pdf"
```

**Download File:**
```bash
curl "https://xma-adt.usn.mil/api/federated/files/12345678-1234-1234-1234-123456789abc/download" -o analysis.pdf
```

**Get Knowledge Content:**
```bash
curl "https://xma-adt.usn.mil/api/federated/knowledge/87654321-4321-4321-4321-210987654321/content"
```

---

## Frontend IRI Features

### 1. IRI Display

**Files Page:**
- **IRI Column**: Compact buttons instead of long text
- **🔗 Copy Button**: Instantly copy IRI to clipboard
- **ℹ️ Details Button**: View full IRI breakdown

**Knowledge Management Page:**
- **IRI Display**: Clickable IRI under asset title
- **Component Breakdown**: Shows installation, program, project, resource type

### 2. IRI Details Modal

Click the ℹ️ button to see:
- **Full IRI**: Complete installation-specific IRI
- **Component Breakdown**: Domain, program, project, resource type
- **Installation Info**: Authority and contact information
- **Copy Functionality**: Easy IRI copying

---

## Security and Access Control

### 1. Access Levels

**Public Access (Federated):**
- ✅ No authentication required
- ✅ Public resources only
- ✅ Full content and metadata
- ✅ Cross-installation sharing

**Private Access (Internal):**
- 🔐 Authentication required
- 🔐 All resources (public and private)
- 🔐 Full ODRAS functionality
- 🔐 Project-based permissions

### 2. Making Resources Public

**Admin Controls:**
- Files can be made public via admin interface
- Knowledge assets can be made public via admin interface
- Public resources are accessible via federated endpoints

**Security Considerations:**
- Only admins can make resources public
- Public resources are accessible to anyone
- Private resources return contact info for access requests

---

## Troubleshooting

### 1. Common Issues

**"No IRI" in Frontend:**
```bash
# Check if backend includes IRI in response
curl "http://localhost:8000/api/files?project_id={project-id}" | jq '.[0].iri'

# If null, check database:
psql -d odras -c "SELECT filename, iri FROM files WHERE iri IS NOT NULL LIMIT 5;"
```

**IRI Resolution Fails:**
```bash
# Validate IRI format
curl "http://localhost:8000/api/iri/validate?iri={your-iri}"

# Check installation config
curl "http://localhost:8000/api/iri/installation-config"
```

**Federated Access Denied:**
- Ensure resource is marked as public
- Check if installation base URI is correct
- Verify network connectivity between installations

### 2. Validation Commands

**Check Installation Configuration:**
```bash
python -c "
from backend.services.config import Settings
from backend.services.installation_iri_service import get_installation_iri_service

settings = Settings()
iri_service = get_installation_iri_service(settings)

print('Installation Config:')
print(f'  Base URI: {iri_service.installation_base_uri}')
print(f'  Type: {settings.installation_type}')
print(f'  Organization: {settings.installation_organization}')

issues = iri_service.validate_installation_config()
if issues:
    print('⚠️  Configuration Issues:')
    for issue in issues:
        print(f'  - {issue}')
else:
    print('✅ Configuration is valid')
"
```

**Test IRI Generation:**
```bash
python -c "
from backend.services.installation_iri_service import get_installation_iri_service

iri_service = get_installation_iri_service()
test_iri = iri_service.generate_file_iri(
    'caee53ce-4b7a-4da0-937b-8f4664eb3462',
    'test.pdf', 
    '12345678-1234-1234-1234-123456789abc'
)
print(f'Generated IRI: {test_iri}')
"
```

### 3. Migration Issues

**If migration fails:**
```bash
# Check migration status
psql -d odras -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'files' AND column_name = 'iri';"

# Re-run migration if needed
python -c "exec(open('backend/migrations/015_installation_specific_iris.sql').read())"
```

---

## Best Practices

### 1. IRI Design
- ✅ Use installation-specific domains
- ✅ Follow hierarchical structure
- ✅ Include authority information
- ✅ Make IRIs dereferenceable

### 2. Federated Sharing
- ✅ Only make necessary resources public
- ✅ Include proper attribution and contact info
- ✅ Log all federated access
- ✅ Provide clear access policies

### 3. Cross-Installation Collaboration
- ✅ Use IRIs for all resource references
- ✅ Include installation discovery in integration
- ✅ Respect access controls and permissions
- ✅ Maintain audit trails for shared resources

---

## Conclusion

The ODRAS installation-specific IRI system enables powerful federated capabilities while maintaining proper security and authority controls. External systems can discover, reference, and access public artifacts using standard semantic web protocols, enabling true cross-installation collaboration and knowledge sharing.

For questions or support, contact your installation authority listed in the IRI resolution responses.
