# ODRAS IRI System Overview

## 🎯 Vision

ODRAS implements a comprehensive **Installation-Specific IRI System** that enables:

- **Global Resource Identification**: Every artifact has a unique, persistent IRI
- **Cross-Installation Sharing**: Resources can be shared between ODRAS installations
- **External System Integration**: Third-party tools can access and reference ODRAS artifacts
- **Semantic Web Compliance**: IRIs are dereferenceable and follow W3C standards
- **Military Domain Conventions**: Follows DoD naming and authority structures

---

## 🏗️ Architecture

### Installation-Specific Domains
```
Navy XMA-ADT:     https://xma-adt.usn.mil/
Air Force AFIT:   https://afit-research.usaf.mil/
Army TRADOC:      https://tradoc-sim.usa.mil/
Boeing Defense:   https://boeing-defense.boeing.com/
```

### Hierarchical Resource Structure
```
{installation_base}/program/{program}/project/{project}/{resource_type}/{resource_id}

Examples:
├── Files: https://xma-adt.usn.mil/program/abc/project/xyz/files/requirements.pdf
├── Knowledge: https://xma-adt.usn.mil/program/abc/project/xyz/knowledge/mission-analysis  
├── Ontologies: https://xma-adt.usn.mil/program/abc/project/xyz/ontologies/requirements
└── Core: https://xma-adt.usn.mil/core/ontologies/odras-base
```

---

## 📚 Documentation Index

### Setup and Configuration
- **[Installation and IRI Setup](./INSTALLATION_AND_IRI_SETUP.md)** - Complete setup guide
- **[Configuration Template](../config/installation-specific.env.template)** - Environment configuration

### Development and Integration  
- **[Federated Access Quick Reference](./FEDERATED_ACCESS_QUICK_REFERENCE.md)** - Developer integration guide
- **[API Documentation](./API_REFERENCE.md)** - Complete API reference (if exists)

### System Documentation
- **[Namespace Management](./namespace/namespace_mvp.md)** - Namespace system overview
- **[URI Design](./namespace-organization-uri-design.md)** - URI design principles
- **[Authentication System](./AUTHENTICATION_SYSTEM.md)** - User management and security

---

## 🔄 Workflow Examples

### Scenario 1: Cross-Installation Knowledge Sharing

**Norfolk Naval Base wants XMA-ADT's mission analysis:**

```python
# 1. Norfolk's system resolves XMA-ADT's IRI
resolution = requests.get(
    "https://xma-adt.usn.mil/api/iri/public/resolve",
    params={"iri": "https://xma-adt.usn.mil/program/abc/project/xyz/knowledge/mission-analysis"}
)

# 2. Get the analysis content
analysis = requests.get(resolution.json()["access_urls"]["content"])

# 3. Use in Norfolk's analysis
norfolk_analysis = integrate_external_knowledge(analysis.json())
```

### Scenario 2: Industry Partner Integration

**Boeing references Navy specifications:**

```python
# 1. Discover XMA-ADT capabilities
discovery = requests.get("https://xma-adt.usn.mil/api/federated/installations/discover")

# 2. Access specific requirements
requirements = requests.get(
    "https://xma-adt.usn.mil/api/federated/files/{req-file-id}/download"
)

# 3. Integrate into Boeing's design process
boeing_design = incorporate_navy_requirements(requirements.content)
```

### Scenario 3: Academic Research

**AFIT researcher cites Navy analysis:**

```python
# 1. Access Navy knowledge asset
knowledge_iri = "https://xma-adt.usn.mil/program/abc/project/xyz/knowledge/lessons-learned"
knowledge_data = resolve_and_fetch_iri(knowledge_iri)

# 2. Include in academic paper with proper citation
citation = {
    "source": "U.S. Navy XMA-ADT ODRAS",
    "title": knowledge_data["title"],
    "iri": knowledge_iri,
    "accessed_at": datetime.now().isoformat(),
    "authority": "admin@xma-adt.usn.mil"
}
```

---

## 🎯 Benefits

### For Military Organizations
- **Resource Sharing**: Share analysis and knowledge across installations
- **Standardization**: Common IRI format across all ODRAS installations  
- **Authority Control**: Clear ownership and contact information
- **Security**: Controlled access with public/private distinctions

### For Industry Partners
- **Integration**: Access Navy/DoD artifacts for design and analysis
- **Compliance**: Reference authoritative requirements and specifications
- **Collaboration**: Contribute knowledge back to military partners
- **Traceability**: Clear provenance for all referenced artifacts

### For Researchers
- **Access**: Use military knowledge for academic research
- **Citation**: Proper attribution with persistent IRIs
- **Collaboration**: Share research results back to military
- **Standards**: Follow semantic web best practices

---

## 🚀 Getting Started

### For Installation Administrators
1. **[Setup Guide](./INSTALLATION_AND_IRI_SETUP.md)** - Configure your installation
2. **Test IRI generation** with new uploads
3. **Configure public resources** for sharing
4. **Set up monitoring** for federated access

### For External Developers
1. **[Quick Reference](./FEDERATED_ACCESS_QUICK_REFERENCE.md)** - Integration examples
2. **Test with discovery endpoint** to understand capabilities
3. **Implement IRI resolution** in your system
4. **Add proper error handling** for private resources

### For End Users
1. **Upload files** and see automatic IRI generation
2. **Use copy buttons** to share IRIs with collaborators
3. **Make resources public** (admin only) for external sharing
4. **View IRI details** to understand resource structure

---

## 📈 Future Enhancements

- **RDF Export**: Export resources as RDF triples
- **SPARQL Endpoints**: Query resources using SPARQL
- **Federation Registry**: Central registry of ODRAS installations
- **Cross-Installation Search**: Search across multiple installations
- **Workflow Integration**: Use IRIs in Camunda workflows
- **Ontology Alignment**: Map concepts across installations

---

The ODRAS IRI system transforms isolated installations into a **federated semantic web** where knowledge and artifacts can be shared, referenced, and integrated across the entire defense and industry ecosystem.
