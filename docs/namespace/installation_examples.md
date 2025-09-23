# ODRAS Installation Configuration Examples<br>
<br>
This document provides examples of how to configure ODRAS for different organizational contexts using proper namespace URIs.<br>
<br>
## Navy ADT Installation<br>
<br>
### Environment Variables<br>
```bash<br>
# .env file for Navy ADT installation<br>
ODRAS_INSTALLATION_ORGANIZATION="US Navy ADT"<br>
ODRAS_INSTALLATION_BASE_URI="https://ontology.navy.mil/adt"<br>
ODRAS_INSTALLATION_PREFIX="adt"<br>
ODRAS_INSTALLATION_TYPE="navy-program"<br>
ODRAS_INSTALLATION_PROGRAM_OFFICE="ADT"<br>
```<br>
<br>
### Generated URIs<br>
- **Core Ontology**: `https://ontology.navy.mil/adt/core/bseo`<br>
- **SE Domain**: `https://ontology.navy.mil/adt/se/reliability`<br>
- **Mission Type**: `https://ontology.navy.mil/adt/mission/asw`<br>
- **Platform Type**: `https://ontology.navy.mil/adt/platform/ddg`<br>
<br>
## Air Force ACC Installation<br>
<br>
### Environment Variables<br>
```bash<br>
# .env file for Air Force ACC installation<br>
ODRAS_INSTALLATION_ORGANIZATION="USAF ACC"<br>
ODRAS_INSTALLATION_BASE_URI="https://ontology.af.mil/acc"<br>
ODRAS_INSTALLATION_PREFIX="acc"<br>
ODRAS_INSTALLATION_TYPE="airforce-program"<br>
ODRAS_INSTALLATION_PROGRAM_OFFICE="ACC"<br>
```<br>
<br>
### Generated URIs<br>
- **Core Ontology**: `https://ontology.af.mil/acc/core/aviation`<br>
- **Program Specific**: `https://ontology.af.mil/acc/f35/core/stealth`<br>
- **Project Specific**: `https://ontology.af.mil/acc/f35/block-4/upgrades`<br>
<br>
## Industry Partner Installation<br>
<br>
### Environment Variables<br>
```bash<br>
# .env file for Boeing Defense installation<br>
ODRAS_INSTALLATION_ORGANIZATION="Boeing Defense"<br>
ODRAS_INSTALLATION_BASE_URI="https://ontology.boeing.com/defense"<br>
ODRAS_INSTALLATION_PREFIX="boeing"<br>
ODRAS_INSTALLATION_TYPE="industry"<br>
ODRAS_INSTALLATION_PROGRAM_OFFICE="Defense Systems"<br>
```<br>
<br>
### Generated URIs<br>
- **Core Ontology**: `https://ontology.boeing.com/defense/core/aircraft`<br>
- **Platform Specific**: `https://ontology.boeing.com/defense/platform/f18/super-hornet`<br>
- **Program Specific**: `https://ontology.boeing.com/defense/program/kc46/tanker`<br>
<br>
## Research Institution Installation<br>
<br>
### Environment Variables<br>
```bash<br>
# .env file for MIT Lincoln Laboratory installation<br>
ODRAS_INSTALLATION_ORGANIZATION="MIT Lincoln Laboratory"<br>
ODRAS_INSTALLATION_BASE_URI="https://ontology.ll.mit.edu/research"<br>
ODRAS_INSTALLATION_PREFIX="ll"<br>
ODRAS_INSTALLATION_TYPE="research"<br>
ODRAS_INSTALLATION_PROGRAM_OFFICE="Advanced Concepts"<br>
```<br>
<br>
### Generated URIs<br>
- **Core Ontology**: `https://ontology.ll.mit.edu/research/core/ai-systems`<br>
- **Domain Specific**: `https://ontology.ll.mit.edu/research/domain/cybersecurity`<br>
- **Project Specific**: `https://ontology.ll.mit.edu/research/project/quantum/communications`<br>
<br>
## Cross-Service Alignment Example<br>
<br>
When multiple ODRAS installations need to align their ontologies:<br>
<br>
```turtle<br>
@prefix adt: <https://ontology.navy.mil/adt/core#> .<br>
@prefix acc: <https://ontology.af.mil/acc/core#> .<br>
@prefix dod: <https://w3id.org/defense/dod/core#> .<br>
<br>
# Both services align to DoD core<br>
adt:Aircraft rdfs:subClassOf dod:Aircraft .<br>
acc:Aircraft rdfs:subClassOf dod:Aircraft .<br>
<br>
# Service-specific extensions<br>
adt:CarrierAircraft rdfs:subClassOf adt:Aircraft .<br>
acc:StealthAircraft rdfs:subClassOf acc:Aircraft .<br>
<br>
# Cross-service alignment<br>
adt:CarrierAircraft owl:equivalentClass acc:CarrierCapableAircraft .<br>
```<br>
<br>
## External Ontology Integration<br>
<br>
All installations can import standard external ontologies:<br>
<br>
```turtle<br>
@prefix bfo: <http://purl.obolibrary.org/obo/bfo/> .<br>
@prefix dod: <https://w3id.org/defense/dod/core#> .<br>
@prefix adt: <https://ontology.navy.mil/adt/core#> .<br>
<br>
# Your classes extend BFO<br>
adt:System rdfs:subClassOf bfo:Object .<br>
adt:Process rdfs:subClassOf bfo:Process .<br>
adt:Function rdfs:subClassOf bfo:Disposition .<br>
<br>
# Import DoD core<br>
adt:Aircraft rdfs:subClassOf dod:Aircraft .<br>
```<br>
<br>
## Configuration Best Practices<br>
<br>
1. **Use HTTPS**: Always use HTTPS for production installations<br>
2. **Meaningful Domains**: Use your organization's actual domain<br>
3. **Consistent Structure**: Follow the hierarchical pattern consistently<br>
4. **Version Control**: Include version information in URIs when needed<br>
5. **Documentation**: Document your namespace structure for users<br>
<br>
## Migration from odras.local<br>
<br>
To migrate from the development `odras.local` setup:<br>
<br>
1. **Set Environment Variables**: Configure your installation-specific variables<br>
2. **Update Existing Ontologies**: Use the namespace management interface to update existing ontologies<br>
3. **Update Imports**: Update any hardcoded imports to use the new URIs<br>
4. **Test Thoroughly**: Ensure all functionality works with the new URIs<br>
<br>
## Example Deployment Script<br>
<br>
```bash<br>
#!/bin/bash<br>
# deploy-odras.sh<br>
<br>
# Set installation-specific configuration<br>
export ODRAS_INSTALLATION_ORGANIZATION="US Navy ADT"<br>
export ODRAS_INSTALLATION_BASE_URI="https://ontology.navy.mil/adt"<br>
export ODRAS_INSTALLATION_PREFIX="adt"<br>
export ODRAS_INSTALLATION_TYPE="navy-program"<br>
export ODRAS_INSTALLATION_PROGRAM_OFFICE="ADT"<br>
<br>
# Start ODRAS with proper configuration<br>
docker-compose up -d<br>
<br>
echo "ODRAS deployed for $ODRAS_INSTALLATION_ORGANIZATION"<br>
echo "Base URI: $ODRAS_INSTALLATION_BASE_URI"<br>
echo "Access at: http://localhost:3000"<br>
```<br>
<br>

