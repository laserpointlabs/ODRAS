Absolutely—here are two **Mermaid** diagrams you can paste straight into your builder to show (1) the ontology with a few **data properties** added, and (2) how the **SHACL shapes** hang together (including a reusable mass-quantity template).

---

## 1) Ontology + data properties

```mermaid
graph TD
  %% ====== Classes ======
  R[Requirement]
  C[Component]
  I[Interface]
  P[Process]
  F[Function]
  K[Constraint]
  QV[qudt:QuantityValue]

  %% ====== Object properties ======
  R -- has_constraint --> K
  R -- specifies --> C
  C -- presents --> I
  C -- performs --> P
  P -- realizes --> F
  F -- specifically_depends_upon --> C
  C -- hasMass --> QV

  %% ====== Data properties on core classes ======
  R -- hasID --> R_id["xsd:string"]
  R -- hasText --> R_txt["xsd:string"]

  C -- hasName --> C_name["xsd:string"]
  C -- hasSerialNumber --> C_sn["xsd:string"]

  K -- hasValue --> K_val["xsd:decimal"]
  K -- hasUnit --> K_unit["xsd:string"]

  %% ====== QUDT quantity value details ======
  QV -- qudt:quantityKind --> QV_kind["qudt:Mass"]
  QV -- qudt:numericValue --> QV_val["xsd:decimal"]
  QV -- qudt:unit --> QV_unit["unit:KiloGM"]

  %% Styling for "literal" leaves
  classDef lit fill:#1f2b3a,stroke:#88a,stroke-width:1px,color:#cfe9ff,rx:6,ry:6;
  class R_id,R_txt,C_name,C_sn,K_val,K_unit,QV_kind,QV_val,QV_unit lit;
```

**What’s shown:**

* Your original object graph (Requirement → Constraint, etc.).
* New **data properties**:

  * `Requirement`: `hasID`, `hasText`
  * `Component`: `hasName`, `hasSerialNumber`
  * `Constraint`: `hasValue`, `hasUnit`
  * `Component` → `hasMass` → `qudt:QuantityValue` with `qudt:numericValue` and `qudt:unit` (engineering-grade units)

---

## 2) SHACL shapes (class shape + nested quantity template)

```mermaid
flowchart LR
  %% ====== NodeShapes ======
  SComp[":ComponentShape\nsh:NodeShape\nsh:targetClass :Component"]
  SMass[":MassQuantityShape\nsh:NodeShape\n(Reusable QUDT template)"]

  %% ====== PropertyShapes attached to ComponentShape ======
  SComp_Name["sh:property\npath :hasName\nxsd:string\nmin/max = 1"]
  SComp_SN["sh:property\npath :hasSerialNumber\nxsd:string\npattern=^[A-Z0-9-]{6,}$"]
  SComp_Mass["sh:property\npath :hasMass\nnode :MassQuantityShape\nmin/max = 1"]

  %% ====== PropertyShapes inside MassQuantityShape ======
  SMass_QK["sh:property\npath qudt:quantityKind\nhasValue qudt:Mass"]
  SMass_NV["sh:property\npath qudt:numericValue\nxsd:decimal > 0"]
  SMass_U["sh:property\npath qudt:unit\nin (unit:KiloGM)"]

  %% ====== Wiring ======
  SComp --> SComp_Name
  SComp --> SComp_SN
  SComp --> SComp_Mass
  SComp_Mass --> SMass

  SMass --> SMass_QK
  SMass --> SMass_NV
  SMass --> SMass_U

  %% ====== Optional cross-field SPARQL checks (examples) ======
  SP1["SPARQL: hasMass_SI == qudt:numericValue when unit=kg"]
  SP2["SPARQL: numericValue within [lowerBound, upperBound] if provided"]

  SComp --- SP1
  SMass --- SP2
```

**What’s shown:**

* `:ComponentShape` validates Components:

  * `hasName` (string, exactly 1)
  * `hasSerialNumber` (string with pattern)
  * `hasMass` (exactly 1) and **delegates** to a reusable `:MassQuantityShape`
* `:MassQuantityShape` validates the QUDT quantity:

  * `qudt:quantityKind = qudt:Mass`
  * `qudt:numericValue` is a positive decimal
  * `qudt:unit ∈ { unit:KiloGM }` (enforce SI kg)
* Two optional **SPARQL** constraints (handy for engineering):

  * Literal shortcut `hasMass_SI` equals the QUDT numeric value (when unit=kg)
  * numericValue within tolerance bounds if you store `lowerBound`/`upperBound`

---

### (Optional) Matching SHACL (copy-paste TTl if you want to generate from your builder)

```turtle
@prefix :      <https://example.org/onto#> .
@prefix sh:    <http://www.w3.org/ns/shacl#> .
@prefix qudt:  <http://qudt.org/schema/qudt/> .
@prefix unit:  <http://qudt.org/vocab/unit/> .
@prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .

:ComponentShape a sh:NodeShape ;
  sh:targetClass :Component ;
  sh:property [
    sh:path :hasName ;
    sh:datatype xsd:string ;
    sh:minCount 1 ; sh:maxCount 1 ;
    sh:message "Component must have exactly one hasName (xsd:string)."
  ] ;
  sh:property [
    sh:path :hasSerialNumber ;
    sh:datatype xsd:string ;
    sh:pattern "^[A-Z0-9\\-]{6,}$" ;
    sh:message "Serial number must be 6+ chars (A-Z,0-9,-)."
  ] ;
  sh:property [
    sh:path :hasMass ;
    sh:minCount 1 ; sh:maxCount 1 ;
    sh:node :MassQuantityShape ;
    sh:message "Component must have exactly one hasMass (QUDT QuantityValue)."
  ] .

:MassQuantityShape a sh:NodeShape ;
  sh:property [
    sh:path qudt:quantityKind ;
    sh:hasValue qudt:Mass ;
    sh:message "QuantityValue must have qudt:quantityKind qudt:Mass."
  ] ;
  sh:property [
    sh:path qudt:numericValue ;
    sh:datatype xsd:decimal ;
    sh:minExclusive 0 ;
    sh:message "Mass numericValue must be > 0 (xsd:decimal)."
  ] ;
  sh:property [
    sh:path qudt:unit ;
    sh:in ( unit:KiloGM ) ;
    sh:minCount 1 ;
    sh:message "Mass unit must be unit:KiloGM (SI kg)."
  ] .

# Optional SPARQL checks
:MassSICheck a sh:NodeShape ;
  sh:targetClass :Component ;
  sh:sparql [
    sh:message "hasMass_SI must equal qudt:numericValue when unit=kg." ;
    sh:select """
      PREFIX qudt: <http://qudt.org/schema/qudt/>
      PREFIX unit: <http://qudt.org/vocab/unit/>
      SELECT ?this WHERE {
        ?this :hasMass_SI ?si ;
              :hasMass ?qv .
        ?qv   qudt:numericValue ?v ;
              qudt:unit unit:KiloGM .
        FILTER(?si != ?v)
      }
    """
  ] .

:MassWithinBounds a sh:NodeShape ;
  sh:targetObjectsOf :hasMass ;
  sh:sparql [
    sh:message "numericValue must be within [lowerBound, upperBound] if provided." ;
    sh:select """
      PREFIX qudt: <http://qudt.org/schema/qudt/>
      SELECT $this WHERE {
        $this qudt:numericValue ?v .
        OPTIONAL { $this :lowerBound ?lo . }
        OPTIONAL { $this :upperBound ?hi . }
        FILTER( (BOUND(?lo) && ?v < ?lo) || (BOUND(?hi) && ?v > ?hi) )
      }
    """
  ] .
```

