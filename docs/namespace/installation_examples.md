# ODRAS Installation Configuration Examples

This document provides examples of how to configure ODRAS for different organizational contexts using proper namespace URIs.

## Navy ADT Installation

### Environment Variables
```bash
# .env file for Navy ADT installation
ODRAS_INSTALLATION_ORGANIZATION="US Navy ADT"
ODRAS_INSTALLATION_BASE_URI="https://ontology.navy.mil/adt"
ODRAS_INSTALLATION_PREFIX="adt"
ODRAS_INSTALLATION_TYPE="navy-program"
ODRAS_INSTALLATION_PROGRAM_OFFICE="ADT"
```

### Generated URIs
- **Core Ontology**: `https://ontology.navy.mil/adt/core/bseo`
- **SE Domain**: `https://ontology.navy.mil/adt/se/reliability`
- **Mission Type**: `https://ontology.navy.mil/adt/mission/asw`
- **Platform Type**: `https://ontology.navy.mil/adt/platform/ddg`

## Air Force ACC Installation

### Environment Variables
```bash
# .env file for Air Force ACC installation
ODRAS_INSTALLATION_ORGANIZATION="USAF ACC"
ODRAS_INSTALLATION_BASE_URI="https://ontology.af.mil/acc"
ODRAS_INSTALLATION_PREFIX="acc"
ODRAS_INSTALLATION_TYPE="airforce-program"
ODRAS_INSTALLATION_PROGRAM_OFFICE="ACC"
```

### Generated URIs
- **Core Ontology**: `https://ontology.af.mil/acc/core/aviation`
- **Program Specific**: `https://ontology.af.mil/acc/f35/core/stealth`
- **Project Specific**: `https://ontology.af.mil/acc/f35/block-4/upgrades`

## Industry Partner Installation

### Environment Variables
```bash
# .env file for Boeing Defense installation
ODRAS_INSTALLATION_ORGANIZATION="Boeing Defense"
ODRAS_INSTALLATION_BASE_URI="https://ontology.boeing.com/defense"
ODRAS_INSTALLATION_PREFIX="boeing"
ODRAS_INSTALLATION_TYPE="industry"
ODRAS_INSTALLATION_PROGRAM_OFFICE="Defense Systems"
```

### Generated URIs
- **Core Ontology**: `https://ontology.boeing.com/defense/core/aircraft`
- **Platform Specific**: `https://ontology.boeing.com/defense/platform/f18/super-hornet`
- **Program Specific**: `https://ontology.boeing.com/defense/program/kc46/tanker`

## Research Institution Installation

### Environment Variables
```bash
# .env file for MIT Lincoln Laboratory installation
ODRAS_INSTALLATION_ORGANIZATION="MIT Lincoln Laboratory"
ODRAS_INSTALLATION_BASE_URI="https://ontology.ll.mit.edu/research"
ODRAS_INSTALLATION_PREFIX="ll"
ODRAS_INSTALLATION_TYPE="research"
ODRAS_INSTALLATION_PROGRAM_OFFICE="Advanced Concepts"
```

### Generated URIs
- **Core Ontology**: `https://ontology.ll.mit.edu/research/core/ai-systems`
- **Domain Specific**: `https://ontology.ll.mit.edu/research/domain/cybersecurity`
- **Project Specific**: `https://ontology.ll.mit.edu/research/project/quantum/communications`

## Cross-Service Alignment Example

When multiple ODRAS installations need to align their ontologies:

```turtle
@prefix adt: <https://ontology.navy.mil/adt/core#> .
@prefix acc: <https://ontology.af.mil/acc/core#> .
@prefix dod: <https://w3id.org/defense/dod/core#> .

# Both services align to DoD core
adt:Aircraft rdfs:subClassOf dod:Aircraft .
acc:Aircraft rdfs:subClassOf dod:Aircraft .

# Service-specific extensions
adt:CarrierAircraft rdfs:subClassOf adt:Aircraft .
acc:StealthAircraft rdfs:subClassOf acc:Aircraft .

# Cross-service alignment
adt:CarrierAircraft owl:equivalentClass acc:CarrierCapableAircraft .
```

## External Ontology Integration

All installations can import standard external ontologies:

```turtle
@prefix bfo: <http://purl.obolibrary.org/obo/bfo/> .
@prefix dod: <https://w3id.org/defense/dod/core#> .
@prefix adt: <https://ontology.navy.mil/adt/core#> .

# Your classes extend BFO
adt:System rdfs:subClassOf bfo:Object .
adt:Process rdfs:subClassOf bfo:Process .
adt:Function rdfs:subClassOf bfo:Disposition .

# Import DoD core
adt:Aircraft rdfs:subClassOf dod:Aircraft .
```

## Configuration Best Practices

1. **Use HTTPS**: Always use HTTPS for production installations
2. **Meaningful Domains**: Use your organization's actual domain
3. **Consistent Structure**: Follow the hierarchical pattern consistently
4. **Version Control**: Include version information in URIs when needed
5. **Documentation**: Document your namespace structure for users

## Migration from odras.local

To migrate from the development `odras.local` setup:

1. **Set Environment Variables**: Configure your installation-specific variables
2. **Update Existing Ontologies**: Use the namespace management interface to update existing ontologies
3. **Update Imports**: Update any hardcoded imports to use the new URIs
4. **Test Thoroughly**: Ensure all functionality works with the new URIs

## Example Deployment Script

```bash
#!/bin/bash
# deploy-odras.sh

# Set installation-specific configuration
export ODRAS_INSTALLATION_ORGANIZATION="US Navy ADT"
export ODRAS_INSTALLATION_BASE_URI="https://ontology.navy.mil/adt"
export ODRAS_INSTALLATION_PREFIX="adt"
export ODRAS_INSTALLATION_TYPE="navy-program"
export ODRAS_INSTALLATION_PROGRAM_OFFICE="ADT"

# Start ODRAS with proper configuration
docker-compose up -d

echo "ODRAS deployed for $ODRAS_INSTALLATION_ORGANIZATION"
echo "Base URI: $ODRAS_INSTALLATION_BASE_URI"
echo "Access at: http://localhost:3000"
```

