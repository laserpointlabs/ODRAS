# Namespace Management Guide
*Comprehensive IRI and URI Organization System*

## 🎯 Overview

The ODRAS Namespace Management System provides hierarchical URI organization, installation-specific IRI configuration, and comprehensive namespace governance. It enables organizations to maintain consistent, meaningful, and scalable identifier schemes across all ontologies and resources.

## 🏗️ Architecture

### Core Components

#### **1. Hierarchical Namespace Structure**
```
{installation_base_uri}/{organization}/{department}/{project}/{resource_type}/{resource_name}
```

#### **2. Namespace Registry**
- **Organization Management**: Top-level organizational units
- **Department Hierarchy**: Departmental namespace allocation
- **Project Scoping**: Project-specific namespace isolation
- **Resource Typing**: Typed resource identification

#### **3. IRI Resolution Service**
- **Dynamic URI Generation**: Context-aware IRI creation
- **Resolution Mapping**: IRI to resource resolution
- **Conflict Detection**: Namespace collision prevention
- **Migration Support**: Namespace evolution and migration

## 🚀 Features

### **Namespace Hierarchy**

#### **Organization Level**
- **Root Namespace**: Installation-wide base URI configuration
- **Organization Units**: Top-level organizational divisions
- **Policy Enforcement**: Organization-wide naming conventions
- **Access Control**: Organization-level permissions

#### **Department Level**
- **Department Namespaces**: Departmental URI allocation
- **Inheritance Rules**: Policy inheritance from organization
- **Resource Quotas**: Namespace usage limits
- **Collaboration Settings**: Cross-department resource sharing

#### **Project Level**
- **Project Isolation**: Project-specific namespace boundaries
- **Resource Organization**: Typed resource categorization
- **Version Management**: Namespace versioning support
- **Integration Points**: External system integration

### **IRI Management**

#### **Dynamic IRI Generation**
```python
# Example IRI patterns
{base_uri}/organizations/acme/engineering/project-alpha/ontologies/requirements-v1
{base_uri}/organizations/acme/research/ai-project/datasets/training-data
{base_uri}/organizations/acme/shared/vocabularies/common-terms
```

#### **Resource Types**
- **Ontologies**: `/ontologies/{ontology-name}`
- **Datasets**: `/datasets/{dataset-name}`
- **Vocabularies**: `/vocabularies/{vocab-name}`
- **Documents**: `/documents/{document-name}`
- **Models**: `/models/{model-name}`

#### **IRI Resolution**
- **Content Negotiation**: Format-specific resource delivery
- **Dereferenceable IRIs**: HTTP-accessible resource identifiers
- **Metadata Exposure**: RDF metadata for all resources
- **Version Resolution**: Version-specific IRI handling

### **Namespace Governance**

#### **Policy Management**
- **Naming Conventions**: Enforced identifier patterns
- **Reserved Terms**: Protected namespace segments
- **Validation Rules**: IRI format validation
- **Approval Workflows**: Namespace creation approval

#### **Access Control**
- **Role-Based Permissions**: Namespace operation permissions
- **Resource Visibility**: Public/private namespace designation
- **Delegation Rules**: Namespace administration delegation
- **Audit Logging**: Comprehensive namespace change tracking

## 🛠️ Implementation

### **Backend Services**

#### **Namespace Service**
```python
class NamespaceService:
    def create_organization(self, name, base_uri, admin_user)
    def create_department(self, org_id, name, parent_dept=None)
    def create_project_namespace(self, dept_id, project_id, config)
    def generate_resource_iri(self, project_id, resource_type, name)
    def resolve_iri(self, iri)
    def validate_namespace(self, namespace_config)
```

#### **IRI Resolution Service**
```python
class IRIResolutionService:
    def resolve_to_resource(self, iri)
    def get_resource_metadata(self, iri)
    def handle_content_negotiation(self, iri, accept_header)
    def redirect_to_current_version(self, iri)
```

### **API Endpoints**

#### **Organization Management**
```python
# Organization operations
POST   /api/namespaces/organizations        # Create organization
GET    /api/namespaces/organizations        # List organizations
GET    /api/namespaces/organizations/{id}   # Get organization
PUT    /api/namespaces/organizations/{id}   # Update organization
DELETE /api/namespaces/organizations/{id}   # Delete organization

# Department operations
POST   /api/namespaces/organizations/{id}/departments    # Create department
GET    /api/namespaces/organizations/{id}/departments    # List departments
PUT    /api/namespaces/departments/{id}                  # Update department
DELETE /api/namespaces/departments/{id}                  # Delete department
```

#### **Project Namespaces**
```python
# Project namespace operations
POST   /api/namespaces/projects/{id}/namespace    # Configure project namespace
GET    /api/namespaces/projects/{id}/namespace    # Get namespace config
PUT    /api/namespaces/projects/{id}/namespace    # Update namespace
GET    /api/namespaces/projects/{id}/iris         # List project IRIs

# IRI operations
POST   /api/iris/generate    # Generate new IRI
GET    /api/iris/resolve     # Resolve IRI to resource
GET    /api/iris/validate    # Validate IRI format
GET    /api/iris/metadata    # Get IRI metadata
```

### **Data Models**

#### **Organization Model**
```python
class Organization:
    id: str
    name: str
    base_uri: str
    description: str
    admin_users: List[str]
    policies: NamespacePolicy
    created_at: datetime
    updated_at: datetime
```

#### **Department Model**
```python
class Department:
    id: str
    organization_id: str
    name: str
    parent_department_id: Optional[str]
    namespace_segment: str
    resource_quotas: dict
    permissions: DepartmentPermissions
    created_at: datetime
```

#### **Project Namespace Model**
```python
class ProjectNamespace:
    project_id: str
    department_id: str
    namespace_path: str
    base_iri: str
    resource_types: List[str]
    policies: NamespacePolicy
    status: NamespaceStatus
    created_at: datetime
```

## 📋 Configuration Examples

### **Installation Configuration**
```yaml
# Installation-specific IRI configuration
installation:
  base_uri: "https://data.example.org"
  organization: "acme-corp"
  default_policies:
    naming_convention: "kebab-case"
    reserved_terms: ["admin", "api", "www", "data"]
    max_segment_length: 50
    allowed_characters: "a-z0-9-"
```

### **Organization Setup**
```python
# Organization namespace configuration
organization_config = {
    "name": "ACME Corporation",
    "base_uri": "https://data.acme.com",
    "departments": [
        {
            "name": "Engineering",
            "namespace": "engineering",
            "quotas": {"projects": 100, "ontologies": 500}
        },
        {
            "name": "Research",
            "namespace": "research", 
            "quotas": {"projects": 50, "ontologies": 200}
        }
    ]
}
```

### **Project Namespace Examples**
```python
# Project namespace patterns
project_namespaces = {
    "requirements-analysis": {
        "base_iri": "https://data.acme.com/engineering/requirements-analysis",
        "resource_types": ["ontologies", "documents", "models"],
        "policies": {
            "versioning": "semantic",
            "visibility": "department",
            "approval_required": False
        }
    },
    "ai-research": {
        "base_iri": "https://data.acme.com/research/ai-research", 
        "resource_types": ["datasets", "models", "vocabularies"],
        "policies": {
            "versioning": "timestamp",
            "visibility": "organization",
            "approval_required": True
        }
    }
}
```

## 🔧 Management Workflows

### **Organization Setup**
1. **Install Base Configuration**: Set installation-wide base URI
2. **Create Organization**: Define organizational namespace
3. **Configure Departments**: Set up departmental hierarchy
4. **Define Policies**: Establish naming and access policies
5. **Assign Administrators**: Delegate namespace management

### **Project Namespace Creation**
1. **Project Registration**: Register project with department
2. **Namespace Allocation**: Generate project namespace path
3. **Resource Type Configuration**: Define allowed resource types
4. **Policy Application**: Apply organization/department policies
5. **IRI Generation**: Create initial resource IRIs

### **Namespace Maintenance**
1. **Policy Updates**: Modify naming conventions and rules
2. **Migration Support**: Handle namespace reorganization
3. **Cleanup Operations**: Remove unused namespaces
4. **Audit Reviews**: Regular namespace usage audits
5. **Performance Optimization**: IRI resolution performance tuning

## 🧪 Testing

### **Namespace Operations**
```python
def test_organization_creation()
def test_department_hierarchy()
def test_project_namespace_allocation()
def test_namespace_policy_enforcement()
def test_namespace_migration()
```

### **IRI Resolution**
```python
def test_iri_generation()
def test_iri_resolution()
def test_content_negotiation()
def test_version_resolution()
def test_metadata_exposure()
```

### **Integration Testing**
```python
def test_end_to_end_namespace_workflow()
def test_multi_organization_isolation()
def test_cross_department_collaboration()
def test_namespace_performance()
```

## 📊 Monitoring and Analytics

### **Namespace Metrics**
- **Namespace Utilization**: Usage across organizations/departments
- **IRI Resolution Performance**: Response times and success rates
- **Resource Distribution**: Resource types per namespace
- **Growth Patterns**: Namespace creation and expansion trends

### **Governance Metrics**
- **Policy Compliance**: Adherence to naming conventions
- **Access Patterns**: Namespace access and permission usage
- **Migration Activity**: Namespace changes and migrations
- **Audit Trail**: Comprehensive change tracking

## 🚀 Future Enhancements

### **Advanced Features**
- **Federated Namespaces**: Cross-installation namespace federation
- **Semantic Namespaces**: Ontology-driven namespace organization
- **Dynamic Policies**: Context-aware policy application
- **Automated Migration**: Intelligent namespace reorganization

### **Integration Enhancements**
- **External Registries**: Integration with external IRI registries
- **Blockchain Integration**: Immutable namespace registration
- **API Gateway Integration**: Namespace-aware API routing
- **Search Integration**: Namespace-aware resource discovery

### **User Experience**
- **Visual Namespace Browser**: Graphical namespace exploration
- **Namespace Designer**: Visual namespace hierarchy design
- **Policy Wizard**: Guided policy configuration
- **Migration Tools**: Automated namespace migration utilities

---

*This guide consolidates all namespace management documentation and serves as the comprehensive reference for IRI and URI organization in ODRAS.*
