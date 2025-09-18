# ODRAS IRI System Overview<br>
<br>
## 🎯 Vision<br>
<br>
ODRAS implements a comprehensive **Installation-Specific IRI System** that enables:<br>
<br>
- **Global Resource Identification**: Every artifact has a unique, persistent IRI<br>
- **Cross-Installation Sharing**: Resources can be shared between ODRAS installations<br>
- **External System Integration**: Third-party tools can access and reference ODRAS artifacts<br>
- **Semantic Web Compliance**: IRIs are dereferenceable and follow W3C standards<br>
- **Military Domain Conventions**: Follows DoD naming and authority structures<br>
<br>
---<br>
<br>
## 🏗️ Architecture<br>
<br>
### Installation-Specific Domains<br>
```<br>
Navy XMA-ADT:     https://xma-adt.usn.mil/<br>
Air Force AFIT:   https://afit-research.usaf.mil/<br>
Army TRADOC:      https://tradoc-sim.usa.mil/<br>
Boeing Defense:   https://boeing-defense.boeing.com/<br>
```<br>
<br>
### Hierarchical Resource Structure<br>
```<br>
{installation_base}/program/{program}/project/{project}/{resource_type}/{resource_id}<br>
<br>
Examples:<br>
├── Files: https://xma-adt.usn.mil/program/abc/project/xyz/files/requirements.pdf<br>
├── Knowledge: https://xma-adt.usn.mil/program/abc/project/xyz/knowledge/mission-analysis<br><br>
├── Ontologies: https://xma-adt.usn.mil/program/abc/project/xyz/ontologies/requirements<br>
└── Core: https://xma-adt.usn.mil/core/ontologies/odras-base<br>
```<br>
<br>
---<br>
<br>
## 📚 Documentation Index<br>
<br>
### Setup and Configuration<br>
- **[Installation and IRI Setup](./INSTALLATION_AND_IRI_SETUP.md)** - Complete setup guide<br>
- **[Configuration Template](../config/installation-specific.env.template)** - Environment configuration<br>
<br>
### Development and Integration<br><br>
- **[Federated Access Quick Reference](./FEDERATED_ACCESS_QUICK_REFERENCE.md)** - Developer integration guide<br>
- **[API Documentation](./API_REFERENCE.md)** - Complete API reference (if exists)<br>
<br>
### System Documentation<br>
- **[Namespace Management](./namespace/namespace_mvp.md)** - Namespace system overview<br>
- **[URI Design](./namespace-organization-uri-design.md)** - URI design principles<br>
- **[Authentication System](./AUTHENTICATION_SYSTEM.md)** - User management and security<br>
<br>
---<br>
<br>
## 🔄 Workflow Examples<br>
<br>
### Scenario 1: Cross-Installation Knowledge Sharing<br>
<br>
**Norfolk Naval Base wants XMA-ADT's mission analysis:**<br>
<br>
```python<br>
# 1. Norfolk's system resolves XMA-ADT's IRI<br>
resolution = requests.get(<br>
    "https://xma-adt.usn.mil/api/iri/public/resolve",<br>
    params={"iri": "https://xma-adt.usn.mil/program/abc/project/xyz/knowledge/mission-analysis"}<br>
)<br>
<br>
# 2. Get the analysis content<br>
analysis = requests.get(resolution.json()["access_urls"]["content"])<br>
<br>
# 3. Use in Norfolk's analysis<br>
norfolk_analysis = integrate_external_knowledge(analysis.json())<br>
```<br>
<br>
### Scenario 2: Industry Partner Integration<br>
<br>
**Boeing references Navy specifications:**<br>
<br>
```python<br>
# 1. Discover XMA-ADT capabilities<br>
discovery = requests.get("https://xma-adt.usn.mil/api/federated/installations/discover")<br>
<br>
# 2. Access specific requirements<br>
requirements = requests.get(<br>
    "https://xma-adt.usn.mil/api/federated/files/{req-file-id}/download"<br>
)<br>
<br>
# 3. Integrate into Boeing's design process<br>
boeing_design = incorporate_navy_requirements(requirements.content)<br>
```<br>
<br>
### Scenario 3: Academic Research<br>
<br>
**AFIT researcher cites Navy analysis:**<br>
<br>
```python<br>
# 1. Access Navy knowledge asset<br>
knowledge_iri = "https://xma-adt.usn.mil/program/abc/project/xyz/knowledge/lessons-learned"<br>
knowledge_data = resolve_and_fetch_iri(knowledge_iri)<br>
<br>
# 2. Include in academic paper with proper citation<br>
citation = {<br>
    "source": "U.S. Navy XMA-ADT ODRAS",<br>
    "title": knowledge_data["title"],<br>
    "iri": knowledge_iri,<br>
    "accessed_at": datetime.now().isoformat(),<br>
    "authority": "admin@xma-adt.usn.mil"<br>
}<br>
```<br>
<br>
---<br>
<br>
## 🎯 Benefits<br>
<br>
### For Military Organizations<br>
- **Resource Sharing**: Share analysis and knowledge across installations<br>
- **Standardization**: Common IRI format across all ODRAS installations<br><br>
- **Authority Control**: Clear ownership and contact information<br>
- **Security**: Controlled access with public/private distinctions<br>
<br>
### For Industry Partners<br>
- **Integration**: Access Navy/DoD artifacts for design and analysis<br>
- **Compliance**: Reference authoritative requirements and specifications<br>
- **Collaboration**: Contribute knowledge back to military partners<br>
- **Traceability**: Clear provenance for all referenced artifacts<br>
<br>
### For Researchers<br>
- **Access**: Use military knowledge for academic research<br>
- **Citation**: Proper attribution with persistent IRIs<br>
- **Collaboration**: Share research results back to military<br>
- **Standards**: Follow semantic web best practices<br>
<br>
---<br>
<br>
## 🚀 Getting Started<br>
<br>
### For Installation Administrators<br>
1. **[Setup Guide](./INSTALLATION_AND_IRI_SETUP.md)** - Configure your installation<br>
2. **Test IRI generation** with new uploads<br>
3. **Configure public resources** for sharing<br>
4. **Set up monitoring** for federated access<br>
<br>
### For External Developers<br>
1. **[Quick Reference](./FEDERATED_ACCESS_QUICK_REFERENCE.md)** - Integration examples<br>
2. **Test with discovery endpoint** to understand capabilities<br>
3. **Implement IRI resolution** in your system<br>
4. **Add proper error handling** for private resources<br>
<br>
### For End Users<br>
1. **Upload files** and see automatic IRI generation<br>
2. **Use copy buttons** to share IRIs with collaborators<br>
3. **Make resources public** (admin only) for external sharing<br>
4. **View IRI details** to understand resource structure<br>
<br>
---<br>
<br>
## 📈 Future Enhancements<br>
<br>
- **RDF Export**: Export resources as RDF triples<br>
- **SPARQL Endpoints**: Query resources using SPARQL<br>
- **Federation Registry**: Central registry of ODRAS installations<br>
- **Cross-Installation Search**: Search across multiple installations<br>
- **Workflow Integration**: Use IRIs in Camunda workflows<br>
- **Ontology Alignment**: Map concepts across installations<br>
<br>
---<br>
<br>
The ODRAS IRI system transforms isolated installations into a **federated semantic web** where knowledge and artifacts can be shared, referenced, and integrated across the entire defense and industry ecosystem.<br>
<br>
<br>
<br>

