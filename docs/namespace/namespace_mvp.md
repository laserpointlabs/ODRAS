Below is an MVP spec for namespace management tailored to **ODRAS**. It is implementation-ready, minimal, and enforceable in an air-gapped environment.

# 1. Scope

Provide a single source of truth for ontology modules and their namespaces across Government → DoD → Service → Program → Project → Industry. ODRAS must:

* mint stable IRIs,
* register modules,
* validate imports/versions,
* publish artifacts (TTL, JSON-LD, SHACL),
* expose a small CLI/SDK for pipelines.

# 2. Namespace & Versioning Policy

* **Base** (configurable): `https://w3id.org/defense` (external) and `https://schema.local/defense` (internal mirror).
* **Module IRI (stable, no hash):** e.g., `https://w3id.org/defense/dod/core`
* **Namespace URI (with hash):** `https://w3id.org/defense/dod/core#`
* **Version IRI (dated):** `https://w3id.org/defense/dod/core/2025-09-01`
* **Never change a class/property IRI once released.** Deprecate with `owl:deprecated "true"^^xsd:boolean`.

# 3. Module Types (ODRAS recognizes exactly these)

* `core`: gov, dod, service (`usn`, `usa`, `usaf`, `usmc`, `ussf`)
* `domain`: joint packages (mission, logistics, weapons, maintenance)
* `program`: per-program core
* `project`: per-project module
* `industry`: prime/supplier/partner
* `vocab`: SKOS vocabularies
* `align`: crosswalks to external standards
* `shapes`: SHACL profiles

# 4. Registry (single YAML file; required)

`/namespaces/registry.yaml`

```yaml
base_external: "https://w3id.org/defense"
base_internal: "https://schema.local/defense"
modules:
  - id: gov-core
    type: core
    path: gov/core
    prefix: gov
    status: released
    owners: ["ontology-board@domain.mil"]
    version: "2025-09-01"
    imports: []
  - id: dod-core
    type: core
    path: dod/core
    prefix: dod
    status: released
    owners: ["ontology-board@domain.mil"]
    version: "2025-09-01"
    imports: ["gov-core"]
  - id: usn-core
    type: core
    path: usn/core
    prefix: usn
    status: released
    owners: ["navy-ontology@domain.mil"]
    version: "2025-09-01"
    imports: ["gov-core","dod-core"]
  - id: pg-avp
    type: program
    path: program/AVP/core
    prefix: pg-avp
    status: draft
    owners: ["avp-pmo@domain.mil"]
    version: "2025-09-01"
    imports: ["usn-core","domain-mission"]
  - id: prj-x1
    type: project
    path: program/AVP/project/X1
    prefix: prj-x1
    status: draft
    owners: ["avp-pmo@domain.mil"]
    version: "2025-09-01"
    imports: ["pg-avp"]
  - id: domain-mission
    type: domain
    path: dod/joint/mission
    prefix: joint-mission
    status: released
    owners: ["ontology-board@domain.mil"]
    version: "2025-09-01"
    imports: ["dod-core"]
  - id: voc-mission
    type: vocab
    path: vocab/mission
    prefix: voc-mission
    status: released
    owners: ["ontology-board@domain.mil"]
    version: "2025-09-01"
    imports: []
  - id: sh-avp
    type: shapes
    path: shapes/program/AVP
    prefix: sh-avp
    status: draft
    owners: ["avp-pmo@domain.mil"]
    version: "2025-09-01"
    imports: ["pg-avp","domain-mission"]
```

# 5. File Layout (repo)

```
/namespaces/registry.yaml
/ontologies/
  gov/core/
    gov-core.ttl
  dod/core/
    dod-core.ttl
  usn/core/
    usn-core.ttl
  dod/joint/mission/
    domain-mission.ttl
  program/AVP/core/
    pg-avp.ttl
  program/AVP/project/X1/
    prj-x1.ttl
/vocab/
  mission/
    voc-mission.ttl
/shapes/
  program/AVP/
    sh-avp.ttl
/align/
  jc3iedm/
    align-jc3iedm.ttl
```

# 6. Minimal Content Templates (ODRAS must scaffold)

## 6.1 Ontology Module Template (TTL)

```turtle
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix dct:  <http://purl.org/dc/terms/> .
@prefix vann: <http://purl.org/vocab/vann/> .

<#ont> a owl:Ontology ;
  dct:title "{{TITLE}}" ;
  owl:versionIRI <{{BASE}}/{{PATH}}/{{VERSION}}> ;
  vann:preferredNamespacePrefix "{{PREFIX}}" ;
  vann:preferredNamespaceUri "{{BASE}}/{{PATH}}#"
  .

# Example declarations (replace or extend)
{{PREFIX}}:System a owl:Class ; rdfs:label "System" .
{{PREFIX}}:supportsMission a owl:ObjectProperty ;
  rdfs:domain {{PREFIX}}:System ; rdfs:range {{REF_PREFIX}}:Mission .
```

ODRAS replaces `{{BASE}}`, `{{PATH}}`, `{{VERSION}}`, `{{PREFIX}}`, `{{REF_PREFIX}}`, `{{TITLE}}`.

## 6.2 SKOS Vocabulary Template

```turtle
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix voc:  <{{BASE}}/{{PATH}}#> .

voc:Scheme a skos:ConceptScheme ;
  skos:prefLabel "{{TITLE}}" .

voc:Mission a skos:Concept ; skos:prefLabel "Mission" ; skos:inScheme voc:Scheme .
voc:ISR a skos:Concept ; skos:prefLabel "Intelligence, Surveillance, and Reconnaissance" ;
  skos:broader voc:Mission ; skos:inScheme voc:Scheme .
voc:CAS a skos:Concept ; skos:prefLabel "Close Air Support" ;
  skos:broader voc:Mission ; skos:inScheme voc:Scheme .
```

## 6.3 SHACL Shape Template

```turtle
@prefix sh:  <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix base: <{{BASE}}/{{TARGET_PATH}}#> .
@prefix shx: <{{BASE}}/{{PATH}}#> .

shx:AirVehicleShape a sh:NodeShape ;
  sh:targetClass base:AirVehicle ;
  sh:property [
    sh:path base:hasEngineCount ;
    sh:datatype xsd:integer ;
    sh:minInclusive 1 ;
    sh:message "AirVehicle must have engineCount >= 1." ;
  ] ;
  sh:property [
    sh:path base:supportsMission ;
    sh:class base:Mission ;
    sh:minCount 1 ;
    sh:message "AirVehicle must support at least one Mission." ;
  ] .
```

## 6.4 Alignment Template

```turtle
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix a1:  <{{BASE}}/{{LEFT_PATH}}#> .
@prefix a2:  <{{RIGHT_BASE}}/{{RIGHT_PATH}}#> .

a1:Mission owl:equivalentClass a2:MissionTask .
a1:AirVehicle owl:equivalentClass a2:Aircraft .
```

# 7. CLI (minimal commands)

Implement as Python CLI `odras-ns` with a local `registry.yaml`.

```
odras-ns init                  # create /namespaces/registry.yaml if missing
odras-ns add-module --id usn-core --type core --path usn/core --prefix usn --imports gov-core dod-core --title "Navy Core Ontology"
odras-ns scaffold --id usn-core   # generate usn-core.ttl from template
odras-ns mint --id usn-core --kind class --name CarrierLaunch
odras-ns validate --all            # validate: registry schema, import DAG, TTL parse, SHACL compile
odras-ns release --id pg-avp --version 2025-09-01   # set versionIRI, freeze, tag
odras-ns publish --target fuseki   # push named graphs to Fuseki endpoints
odras-ns diff --from 2025-06-01 --to 2025-09-01 --id dod-core  # entity/axiom diff
```

### Behavior (concise)

* **init:** creates registry + default templates for `gov-core` and `dod-core`.
* **add-module:** adds a row; enforces unique `id`, valid `type`, unique `prefix`, path hygiene.
* **scaffold:** creates module file(s) with correct ontology header + namespace metadata.
* **mint:** appends a class/property/individual skeleton to the module file; enforces naming conventions.
* **validate:** runs:

  * YAML schema check for registry,
  * Import graph acyclicity and top-down rule,
  * RDF syntax check (riot/jena or RDFLib),
  * Optional SHACL compilation.
* **release:** stamps `owl:versionIRI` and writes a `MANIFEST.json`.
* **publish:** loads named graphs to internal Fuseki: graph IRI = stable module IRI, version graph IRI = versionIRI.
* **diff:** structural diff (classes, properties, individuals, axioms) between versions.

# 8. Naming & Conventions (enforced by `validate`)

* Classes: `UpperCamelCase` (e.g., `AirVehicle`)
* Object/Data properties: `lowerCamelCase` (`supportsMission`, `maximumTakeoffWeight`)
* Individuals: `UPPER_SNAKE` or UUID suffixes where appropriate
* No spaces or punctuation in local names
* Prefix uniqueness across registry
* Module import constraints:

  * `project` may import `program`, `service`, `domain`, `core`
  * `program` may import `service`, `domain`, `core`
  * `service` may import `core`, `gov`
  * `domain` may import `core`
  * `vocab` should not import OWL modules (optional)
  * `shapes`/`align` import whatever they validate/map; **no one imports shapes/align**

# 9. Publishing (air-gapped)

* **Internal endpoint:** Fuseki (e.g., `http://fuseki.local/datasets/ont`).
* Named graphs:

  * stable graph: `<https://w3id.org/defense/dod/core>`
  * versioned graph: `<https://w3id.org/defense/dod/core/2025-09-01>`
* Optional static docs generation (RDFa/HTML) into `/site/<path>/index.html`.
* If w3id is unavailable, use `base_internal` IRIs in content; maintain a mapping file for future external mirror.

# 10. Integration with ODRAS Pipelines

* **Extraction stage:** when ODRAS proposes new entities, call `odras-ns mint` into a *scratch project module*; do **not** touch cores directly.
* **Review stage:** human review of scratch module; upon approval, move to program/service as needed, then `release`.
* **Validation gate:** SHACL validation runs automatically in CI before data loads; failing shapes block ingestion.
* **Alignment gate:** any mapping to external standards must live in an `align/*` module; cores remain clean.

# 11. Minimal Examples

## 11.1 Program → Project import

`pg-avp.ttl` (fragment)

```turtle
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix pg:  <https://w3id.org/defense/program/AVP/core#> .

<https://w3id.org/defense/program/AVP/core> a owl:Ontology ;
  dct:title "AVP Program Core" ;
  owl:versionIRI <https://w3id.org/defense/program/AVP/core/2025-09-01> ;
  owl:imports <https://w3id.org/defense/usn/core> ,
              <https://w3id.org/defense/dod/joint/mission> .

pg:MissionProfile a owl:Class .
```

`prj-x1.ttl` (fragment)

```turtle
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix prj: <https://w3id.org/defense/program/AVP/project/X1#> .
@prefix pg:  <https://w3id.org/defense/program/AVP/core#> .

<https://w3id.org/defense/program/AVP/project/X1> a owl:Ontology ;
  owl:versionIRI <https://w3id.org/defense/program/AVP/project/X1/2025-09-01> ;
  owl:imports <https://w3id.org/defense/program/AVP/core> .

prj:AVP_001 a pg:MissionProfile .
```

## 11.2 SHACL validation (program profile)

`sh-avp.ttl` (fragment)

```turtle
@prefix sh:  <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix pg:  <https://w3id.org/defense/program/AVP/core#> .

pg:MissionProfileShape a sh:NodeShape ;
  sh:targetClass pg:MissionProfile ;
  sh:property [
    sh:path pg:hasRequiredMoE ;
    sh:datatype xsd:string ;
    sh:minCount 1 ;
  ] .
```

If `AVP_001` lacks `pg:hasRequiredMoE`, CI fails.

## 11.3 Alignment (JC3IEDM)

```turtle
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix dod: <https://w3id.org/defense/dod/core#> .
@prefix jc3: <http://example.mil/jc3iedm#> .

dod:Mission owl:equivalentClass jc3:MissionTask .
```

# 12. CI Gates (fast and strict)

* **registry-schema:** JSON Schema or Pydantic model for `registry.yaml`
* **imports-dag:** no cycles; only allowed directions
* **iri-consistency:** `vann:preferredNamespaceUri` matches registry path
* **ttl-parse:** riot or rdflib parse
* **shape-compile:** SHACL syntax loads
* **release-lock:** released module content immutable except new version

# 13. Roadmap (MVP → v0.2)

* **MVP (2–3 days dev):**

  * `registry.yaml` loader + schema validation
  * `add-module`, `scaffold`, `validate`, `release`
  * TTL/SHACL parsing and basic import DAG checks
* **v0.2 (1–2 weeks):**

  * `mint` command with naming checks
  * `publish` to Fuseki (named graphs)
  * `diff` between versions
  * Static doc generation (HTML+RDFa) per module

# 14. Success Criteria

* One `registry.yaml` governs all modules.
* Every module has a stable IRI, namespace URI, and version IRI.
* Import graph is acyclic and top-down.
* SHACL validation runs in CI and blocks bad data.
* ODRAS pipelines only create/edit **project** modules; promotion to higher layers is explicit via `release`.

