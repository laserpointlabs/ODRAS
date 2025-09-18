Below is an MVP spec for namespace management tailored to **ODRAS**. It is implementation-ready, minimal, and enforceable in an air-gapped environment.<br>
<br>
# 1. Scope<br>
<br>
Provide a single source of truth for ontology modules and their namespaces across Government → DoD → Service → Program → Project → Industry. ODRAS must:<br>
<br>
* mint stable IRIs,<br>
* register modules,<br>
* validate imports/versions,<br>
* publish artifacts (TTL, JSON-LD, SHACL),<br>
* expose a small CLI/SDK for pipelines.<br>
<br>
# 2. Namespace & Versioning Policy<br>
<br>
* **Base** (configurable): `https://w3id.org/defense` (external) and `https://schema.local/defense` (internal mirror).<br>
* **Module IRI (stable, no hash):** e.g., `https://w3id.org/defense/dod/core`<br>
* **Namespace URI (with hash):** `https://w3id.org/defense/dod/core#`<br>
* **Version IRI (dated):** `https://w3id.org/defense/dod/core/2025-09-01`<br>
* **Never change a class/property IRI once released.** Deprecate with `owl:deprecated "true"^^xsd:boolean`.<br>
<br>
# 3. Module Types (ODRAS recognizes exactly these)<br>
<br>
* `core`: gov, dod, service (`usn`, `usa`, `usaf`, `usmc`, `ussf`)<br>
* `domain`: joint packages (mission, logistics, weapons, maintenance)<br>
* `program`: per-program core<br>
* `project`: per-project module<br>
* `industry`: prime/supplier/partner<br>
* `vocab`: SKOS vocabularies<br>
* `align`: crosswalks to external standards<br>
* `shapes`: SHACL profiles<br>
<br>
# 4. Registry (single YAML file; required)<br>
<br>
`/namespaces/registry.yaml`<br>
<br>
```yaml<br>
base_external: "https://w3id.org/defense"<br>
base_internal: "https://schema.local/defense"<br>
modules:<br>
  - id: gov-core<br>
    type: core<br>
    path: gov/core<br>
    prefix: gov<br>
    status: released<br>
    owners: ["ontology-board@domain.mil"]<br>
    version: "2025-09-01"<br>
    imports: []<br>
  - id: dod-core<br>
    type: core<br>
    path: dod/core<br>
    prefix: dod<br>
    status: released<br>
    owners: ["ontology-board@domain.mil"]<br>
    version: "2025-09-01"<br>
    imports: ["gov-core"]<br>
  - id: usn-core<br>
    type: core<br>
    path: usn/core<br>
    prefix: usn<br>
    status: released<br>
    owners: ["navy-ontology@domain.mil"]<br>
    version: "2025-09-01"<br>
    imports: ["gov-core","dod-core"]<br>
  - id: pg-avp<br>
    type: program<br>
    path: program/AVP/core<br>
    prefix: pg-avp<br>
    status: draft<br>
    owners: ["avp-pmo@domain.mil"]<br>
    version: "2025-09-01"<br>
    imports: ["usn-core","domain-mission"]<br>
  - id: prj-x1<br>
    type: project<br>
    path: program/AVP/project/X1<br>
    prefix: prj-x1<br>
    status: draft<br>
    owners: ["avp-pmo@domain.mil"]<br>
    version: "2025-09-01"<br>
    imports: ["pg-avp"]<br>
  - id: domain-mission<br>
    type: domain<br>
    path: dod/joint/mission<br>
    prefix: joint-mission<br>
    status: released<br>
    owners: ["ontology-board@domain.mil"]<br>
    version: "2025-09-01"<br>
    imports: ["dod-core"]<br>
  - id: voc-mission<br>
    type: vocab<br>
    path: vocab/mission<br>
    prefix: voc-mission<br>
    status: released<br>
    owners: ["ontology-board@domain.mil"]<br>
    version: "2025-09-01"<br>
    imports: []<br>
  - id: sh-avp<br>
    type: shapes<br>
    path: shapes/program/AVP<br>
    prefix: sh-avp<br>
    status: draft<br>
    owners: ["avp-pmo@domain.mil"]<br>
    version: "2025-09-01"<br>
    imports: ["pg-avp","domain-mission"]<br>
```<br>
<br>
# 5. File Layout (repo)<br>
<br>
```<br>
/namespaces/registry.yaml<br>
/ontologies/<br>
  gov/core/<br>
    gov-core.ttl<br>
  dod/core/<br>
    dod-core.ttl<br>
  usn/core/<br>
    usn-core.ttl<br>
  dod/joint/mission/<br>
    domain-mission.ttl<br>
  program/AVP/core/<br>
    pg-avp.ttl<br>
  program/AVP/project/X1/<br>
    prj-x1.ttl<br>
/vocab/<br>
  mission/<br>
    voc-mission.ttl<br>
/shapes/<br>
  program/AVP/<br>
    sh-avp.ttl<br>
/align/<br>
  jc3iedm/<br>
    align-jc3iedm.ttl<br>
```<br>
<br>
# 6. Minimal Content Templates (ODRAS must scaffold)<br>
<br>
## 6.1 Ontology Module Template (TTL)<br>
<br>
```turtle<br>
@prefix owl:  <http://www.w3.org/2002/07/owl#> .<br>
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .<br>
@prefix dct:  <http://purl.org/dc/terms/> .<br>
@prefix vann: <http://purl.org/vocab/vann/> .<br>
<br>
<#ont> a owl:Ontology ;<br>
  dct:title "{{TITLE}}" ;<br>
  owl:versionIRI <{{BASE}}/{{PATH}}/{{VERSION}}> ;<br>
  vann:preferredNamespacePrefix "{{PREFIX}}" ;<br>
  vann:preferredNamespaceUri "{{BASE}}/{{PATH}}#"<br>
  .<br>
<br>
# Example declarations (replace or extend)<br>
{{PREFIX}}:System a owl:Class ; rdfs:label "System" .<br>
{{PREFIX}}:supportsMission a owl:ObjectProperty ;<br>
  rdfs:domain {{PREFIX}}:System ; rdfs:range {{REF_PREFIX}}:Mission .<br>
```<br>
<br>
ODRAS replaces `{{BASE}}`, `{{PATH}}`, `{{VERSION}}`, `{{PREFIX}}`, `{{REF_PREFIX}}`, `{{TITLE}}`.<br>
<br>
## 6.2 SKOS Vocabulary Template<br>
<br>
```turtle<br>
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .<br>
@prefix voc:  <{{BASE}}/{{PATH}}#> .<br>
<br>
voc:Scheme a skos:ConceptScheme ;<br>
  skos:prefLabel "{{TITLE}}" .<br>
<br>
voc:Mission a skos:Concept ; skos:prefLabel "Mission" ; skos:inScheme voc:Scheme .<br>
voc:ISR a skos:Concept ; skos:prefLabel "Intelligence, Surveillance, and Reconnaissance" ;<br>
  skos:broader voc:Mission ; skos:inScheme voc:Scheme .<br>
voc:CAS a skos:Concept ; skos:prefLabel "Close Air Support" ;<br>
  skos:broader voc:Mission ; skos:inScheme voc:Scheme .<br>
```<br>
<br>
## 6.3 SHACL Shape Template<br>
<br>
```turtle<br>
@prefix sh:  <http://www.w3.org/ns/shacl#> .<br>
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .<br>
@prefix base: <{{BASE}}/{{TARGET_PATH}}#> .<br>
@prefix shx: <{{BASE}}/{{PATH}}#> .<br>
<br>
shx:AirVehicleShape a sh:NodeShape ;<br>
  sh:targetClass base:AirVehicle ;<br>
  sh:property [<br>
    sh:path base:hasEngineCount ;<br>
    sh:datatype xsd:integer ;<br>
    sh:minInclusive 1 ;<br>
    sh:message "AirVehicle must have engineCount >= 1." ;<br>
  ] ;<br>
  sh:property [<br>
    sh:path base:supportsMission ;<br>
    sh:class base:Mission ;<br>
    sh:minCount 1 ;<br>
    sh:message "AirVehicle must support at least one Mission." ;<br>
  ] .<br>
```<br>
<br>
## 6.4 Alignment Template<br>
<br>
```turtle<br>
@prefix owl: <http://www.w3.org/2002/07/owl#> .<br>
@prefix a1:  <{{BASE}}/{{LEFT_PATH}}#> .<br>
@prefix a2:  <{{RIGHT_BASE}}/{{RIGHT_PATH}}#> .<br>
<br>
a1:Mission owl:equivalentClass a2:MissionTask .<br>
a1:AirVehicle owl:equivalentClass a2:Aircraft .<br>
```<br>
<br>
# 7. CLI (minimal commands)<br>
<br>
Implement as Python CLI `odras-ns` with a local `registry.yaml`.<br>
<br>
```<br>
odras-ns init                  # create /namespaces/registry.yaml if missing<br>
odras-ns add-module --id usn-core --type core --path usn/core --prefix usn --imports gov-core dod-core --title "Navy Core Ontology"<br>
odras-ns scaffold --id usn-core   # generate usn-core.ttl from template<br>
odras-ns mint --id usn-core --kind class --name CarrierLaunch<br>
odras-ns validate --all            # validate: registry schema, import DAG, TTL parse, SHACL compile<br>
odras-ns release --id pg-avp --version 2025-09-01   # set versionIRI, freeze, tag<br>
odras-ns publish --target fuseki   # push named graphs to Fuseki endpoints<br>
odras-ns diff --from 2025-06-01 --to 2025-09-01 --id dod-core  # entity/axiom diff<br>
```<br>
<br>
### Behavior (concise)<br>
<br>
* **init:** creates registry + default templates for `gov-core` and `dod-core`.<br>
* **add-module:** adds a row; enforces unique `id`, valid `type`, unique `prefix`, path hygiene.<br>
* **scaffold:** creates module file(s) with correct ontology header + namespace metadata.<br>
* **mint:** appends a class/property/individual skeleton to the module file; enforces naming conventions.<br>
* **validate:** runs:<br>
<br>
  * YAML schema check for registry,<br>
  * Import graph acyclicity and top-down rule,<br>
  * RDF syntax check (riot/jena or RDFLib),<br>
  * Optional SHACL compilation.<br>
* **release:** stamps `owl:versionIRI` and writes a `MANIFEST.json`.<br>
* **publish:** loads named graphs to internal Fuseki: graph IRI = stable module IRI, version graph IRI = versionIRI.<br>
* **diff:** structural diff (classes, properties, individuals, axioms) between versions.<br>
<br>
# 8. Naming & Conventions (enforced by `validate`)<br>
<br>
* Classes: `UpperCamelCase` (e.g., `AirVehicle`)<br>
* Object/Data properties: `lowerCamelCase` (`supportsMission`, `maximumTakeoffWeight`)<br>
* Individuals: `UPPER_SNAKE` or UUID suffixes where appropriate<br>
* No spaces or punctuation in local names<br>
* Prefix uniqueness across registry<br>
* Module import constraints:<br>
<br>
  * `project` may import `program`, `service`, `domain`, `core`<br>
  * `program` may import `service`, `domain`, `core`<br>
  * `service` may import `core`, `gov`<br>
  * `domain` may import `core`<br>
  * `vocab` should not import OWL modules (optional)<br>
  * `shapes`/`align` import whatever they validate/map; **no one imports shapes/align**<br>
<br>
# 9. Publishing (air-gapped)<br>
<br>
* **Internal endpoint:** Fuseki (e.g., `http://fuseki.local/datasets/ont`).<br>
* Named graphs:<br>
<br>
  * stable graph: `<https://w3id.org/defense/dod/core>`<br>
  * versioned graph: `<https://w3id.org/defense/dod/core/2025-09-01>`<br>
* Optional static docs generation (RDFa/HTML) into `/site/<path>/index.html`.<br>
* If w3id is unavailable, use `base_internal` IRIs in content; maintain a mapping file for future external mirror.<br>
<br>
# 10. Integration with ODRAS Pipelines<br>
<br>
* **Extraction stage:** when ODRAS proposes new entities, call `odras-ns mint` into a *scratch project module*; do **not** touch cores directly.<br>
* **Review stage:** human review of scratch module; upon approval, move to program/service as needed, then `release`.<br>
* **Validation gate:** SHACL validation runs automatically in CI before data loads; failing shapes block ingestion.<br>
* **Alignment gate:** any mapping to external standards must live in an `align/*` module; cores remain clean.<br>
<br>
# 11. Minimal Examples<br>
<br>
## 11.1 Program → Project import<br>
<br>
`pg-avp.ttl` (fragment)<br>
<br>
```turtle<br>
@prefix owl: <http://www.w3.org/2002/07/owl#> .<br>
@prefix dct: <http://purl.org/dc/terms/> .<br>
@prefix pg:  <https://w3id.org/defense/program/AVP/core#> .<br>
<br>
<https://w3id.org/defense/program/AVP/core> a owl:Ontology ;<br>
  dct:title "AVP Program Core" ;<br>
  owl:versionIRI <https://w3id.org/defense/program/AVP/core/2025-09-01> ;<br>
  owl:imports <https://w3id.org/defense/usn/core> ,<br>
              <https://w3id.org/defense/dod/joint/mission> .<br>
<br>
pg:MissionProfile a owl:Class .<br>
```<br>
<br>
`prj-x1.ttl` (fragment)<br>
<br>
```turtle<br>
@prefix owl: <http://www.w3.org/2002/07/owl#> .<br>
@prefix prj: <https://w3id.org/defense/program/AVP/project/X1#> .<br>
@prefix pg:  <https://w3id.org/defense/program/AVP/core#> .<br>
<br>
<https://w3id.org/defense/program/AVP/project/X1> a owl:Ontology ;<br>
  owl:versionIRI <https://w3id.org/defense/program/AVP/project/X1/2025-09-01> ;<br>
  owl:imports <https://w3id.org/defense/program/AVP/core> .<br>
<br>
prj:AVP_001 a pg:MissionProfile .<br>
```<br>
<br>
## 11.2 SHACL validation (program profile)<br>
<br>
`sh-avp.ttl` (fragment)<br>
<br>
```turtle<br>
@prefix sh:  <http://www.w3.org/ns/shacl#> .<br>
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .<br>
@prefix pg:  <https://w3id.org/defense/program/AVP/core#> .<br>
<br>
pg:MissionProfileShape a sh:NodeShape ;<br>
  sh:targetClass pg:MissionProfile ;<br>
  sh:property [<br>
    sh:path pg:hasRequiredMoE ;<br>
    sh:datatype xsd:string ;<br>
    sh:minCount 1 ;<br>
  ] .<br>
```<br>
<br>
If `AVP_001` lacks `pg:hasRequiredMoE`, CI fails.<br>
<br>
## 11.3 Alignment (JC3IEDM)<br>
<br>
```turtle<br>
@prefix owl: <http://www.w3.org/2002/07/owl#> .<br>
@prefix dod: <https://w3id.org/defense/dod/core#> .<br>
@prefix jc3: <http://example.mil/jc3iedm#> .<br>
<br>
dod:Mission owl:equivalentClass jc3:MissionTask .<br>
```<br>
<br>
# 12. CI Gates (fast and strict)<br>
<br>
* **registry-schema:** JSON Schema or Pydantic model for `registry.yaml`<br>
* **imports-dag:** no cycles; only allowed directions<br>
* **iri-consistency:** `vann:preferredNamespaceUri` matches registry path<br>
* **ttl-parse:** riot or rdflib parse<br>
* **shape-compile:** SHACL syntax loads<br>
* **release-lock:** released module content immutable except new version<br>
<br>
# 13. Roadmap (MVP → v0.2)<br>
<br>
* **MVP (2–3 days dev):**<br>
<br>
  * `registry.yaml` loader + schema validation<br>
  * `add-module`, `scaffold`, `validate`, `release`<br>
  * TTL/SHACL parsing and basic import DAG checks<br>
* **v0.2 (1–2 weeks):**<br>
<br>
  * `mint` command with naming checks<br>
  * `publish` to Fuseki (named graphs)<br>
  * `diff` between versions<br>
  * Static doc generation (HTML+RDFa) per module<br>
<br>
# 14. Success Criteria<br>
<br>
* One `registry.yaml` governs all modules.<br>
* Every module has a stable IRI, namespace URI, and version IRI.<br>
* Import graph is acyclic and top-down.<br>
* SHACL validation runs in CI and blocks bad data.<br>
* ODRAS pipelines only create/edit **project** modules; promotion to higher layers is explicit via `release`.<br>
<br>

