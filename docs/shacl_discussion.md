Absolutely—here are two **Mermaid** diagrams you can paste straight into your builder to show (1) the ontology with a few **data properties** added, and (2) how the **SHACL shapes** hang together (including a reusable mass-quantity template).<br>
<br>
---<br>
<br>
## 1) Ontology + data properties<br>
<br>
```mermaid<br>
graph TD<br>
  %% ====== Classes ======<br>
  R[Requirement]<br>
  C[Component]<br>
  I[Interface]<br>
  P[Process]<br>
  F[Function]<br>
  K[Constraint]<br>
  QV[qudt:QuantityValue]<br>
<br>
  %% ====== Object properties ======<br>
  R -- has_constraint --> K<br>
  R -- specifies --> C<br>
  C -- presents --> I<br>
  C -- performs --> P<br>
  P -- realizes --> F<br>
  F -- specifically_depends_upon --> C<br>
  C -- hasMass --> QV<br>
<br>
  %% ====== Data properties on core classes ======<br>
  R -- hasID --> R_id["xsd:string"]<br>
  R -- hasText --> R_txt["xsd:string"]<br>
<br>
  C -- hasName --> C_name["xsd:string"]<br>
  C -- hasSerialNumber --> C_sn["xsd:string"]<br>
<br>
  K -- hasValue --> K_val["xsd:decimal"]<br>
  K -- hasUnit --> K_unit["xsd:string"]<br>
<br>
  %% ====== QUDT quantity value details ======<br>
  QV -- qudt:quantityKind --> QV_kind["qudt:Mass"]<br>
  QV -- qudt:numericValue --> QV_val["xsd:decimal"]<br>
  QV -- qudt:unit --> QV_unit["unit:KiloGM"]<br>
<br>
  %% Styling for "literal" leaves<br>
  classDef lit fill:#1f2b3a,stroke:#88a,stroke-width:1px,color:#cfe9ff,rx:6,ry:6;<br>
  class R_id,R_txt,C_name,C_sn,K_val,K_unit,QV_kind,QV_val,QV_unit lit;<br>
```<br>
<br>
**What’s shown:**<br>
<br>
* Your original object graph (Requirement → Constraint, etc.).<br>
* New **data properties**:<br>
<br>
  * `Requirement`: `hasID`, `hasText`<br>
  * `Component`: `hasName`, `hasSerialNumber`<br>
  * `Constraint`: `hasValue`, `hasUnit`<br>
  * `Component` → `hasMass` → `qudt:QuantityValue` with `qudt:numericValue` and `qudt:unit` (engineering-grade units)<br>
<br>
---<br>
<br>
## 2) SHACL shapes (class shape + nested quantity template)<br>
<br>
```mermaid<br>
flowchart LR<br>
  %% ====== NodeShapes ======<br>
  SComp[":ComponentShape\nsh:NodeShape\nsh:targetClass :Component"]<br>
  SMass[":MassQuantityShape\nsh:NodeShape\n(Reusable QUDT template)"]<br>
<br>
  %% ====== PropertyShapes attached to ComponentShape ======<br>
  SComp_Name["sh:property\npath :hasName\nxsd:string\nmin/max = 1"]<br>
  SComp_SN["sh:property\npath :hasSerialNumber\nxsd:string\npattern=^[A-Z0-9-]{6,}$"]<br>
  SComp_Mass["sh:property\npath :hasMass\nnode :MassQuantityShape\nmin/max = 1"]<br>
<br>
  %% ====== PropertyShapes inside MassQuantityShape ======<br>
  SMass_QK["sh:property\npath qudt:quantityKind\nhasValue qudt:Mass"]<br>
  SMass_NV["sh:property\npath qudt:numericValue\nxsd:decimal > 0"]<br>
  SMass_U["sh:property\npath qudt:unit\nin (unit:KiloGM)"]<br>
<br>
  %% ====== Wiring ======<br>
  SComp --> SComp_Name<br>
  SComp --> SComp_SN<br>
  SComp --> SComp_Mass<br>
  SComp_Mass --> SMass<br>
<br>
  SMass --> SMass_QK<br>
  SMass --> SMass_NV<br>
  SMass --> SMass_U<br>
<br>
  %% ====== Optional cross-field SPARQL checks (examples) ======<br>
  SP1["SPARQL: hasMass_SI == qudt:numericValue when unit=kg"]<br>
  SP2["SPARQL: numericValue within [lowerBound, upperBound] if provided"]<br>
<br>
  SComp --- SP1<br>
  SMass --- SP2<br>
```<br>
<br>
**What’s shown:**<br>
<br>
* `:ComponentShape` validates Components:<br>
<br>
  * `hasName` (string, exactly 1)<br>
  * `hasSerialNumber` (string with pattern)<br>
  * `hasMass` (exactly 1) and **delegates** to a reusable `:MassQuantityShape`<br>
* `:MassQuantityShape` validates the QUDT quantity:<br>
<br>
  * `qudt:quantityKind = qudt:Mass`<br>
  * `qudt:numericValue` is a positive decimal<br>
  * `qudt:unit ∈ { unit:KiloGM }` (enforce SI kg)<br>
* Two optional **SPARQL** constraints (handy for engineering):<br>
<br>
  * Literal shortcut `hasMass_SI` equals the QUDT numeric value (when unit=kg)<br>
  * numericValue within tolerance bounds if you store `lowerBound`/`upperBound`<br>
<br>
---<br>
<br>
### (Optional) Matching SHACL (copy-paste TTl if you want to generate from your builder)<br>
<br>
```turtle<br>
@prefix :      <https://example.org/onto#> .<br>
@prefix sh:    <http://www.w3.org/ns/shacl#> .<br>
@prefix qudt:  <http://qudt.org/schema/qudt/> .<br>
@prefix unit:  <http://qudt.org/vocab/unit/> .<br>
@prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .<br>
<br>
:ComponentShape a sh:NodeShape ;<br>
  sh:targetClass :Component ;<br>
  sh:property [<br>
    sh:path :hasName ;<br>
    sh:datatype xsd:string ;<br>
    sh:minCount 1 ; sh:maxCount 1 ;<br>
    sh:message "Component must have exactly one hasName (xsd:string)."<br>
  ] ;<br>
  sh:property [<br>
    sh:path :hasSerialNumber ;<br>
    sh:datatype xsd:string ;<br>
    sh:pattern "^[A-Z0-9\\-]{6,}$" ;<br>
    sh:message "Serial number must be 6+ chars (A-Z,0-9,-)."<br>
  ] ;<br>
  sh:property [<br>
    sh:path :hasMass ;<br>
    sh:minCount 1 ; sh:maxCount 1 ;<br>
    sh:node :MassQuantityShape ;<br>
    sh:message "Component must have exactly one hasMass (QUDT QuantityValue)."<br>
  ] .<br>
<br>
:MassQuantityShape a sh:NodeShape ;<br>
  sh:property [<br>
    sh:path qudt:quantityKind ;<br>
    sh:hasValue qudt:Mass ;<br>
    sh:message "QuantityValue must have qudt:quantityKind qudt:Mass."<br>
  ] ;<br>
  sh:property [<br>
    sh:path qudt:numericValue ;<br>
    sh:datatype xsd:decimal ;<br>
    sh:minExclusive 0 ;<br>
    sh:message "Mass numericValue must be > 0 (xsd:decimal)."<br>
  ] ;<br>
  sh:property [<br>
    sh:path qudt:unit ;<br>
    sh:in ( unit:KiloGM ) ;<br>
    sh:minCount 1 ;<br>
    sh:message "Mass unit must be unit:KiloGM (SI kg)."<br>
  ] .<br>
<br>
# Optional SPARQL checks<br>
:MassSICheck a sh:NodeShape ;<br>
  sh:targetClass :Component ;<br>
  sh:sparql [<br>
    sh:message "hasMass_SI must equal qudt:numericValue when unit=kg." ;<br>
    sh:select """<br>
      PREFIX qudt: <http://qudt.org/schema/qudt/><br>
      PREFIX unit: <http://qudt.org/vocab/unit/><br>
      SELECT ?this WHERE {<br>
        ?this :hasMass_SI ?si ;<br>
              :hasMass ?qv .<br>
        ?qv   qudt:numericValue ?v ;<br>
              qudt:unit unit:KiloGM .<br>
        FILTER(?si != ?v)<br>
      }<br>
    """<br>
  ] .<br>
<br>
:MassWithinBounds a sh:NodeShape ;<br>
  sh:targetObjectsOf :hasMass ;<br>
  sh:sparql [<br>
    sh:message "numericValue must be within [lowerBound, upperBound] if provided." ;<br>
    sh:select """<br>
      PREFIX qudt: <http://qudt.org/schema/qudt/><br>
      SELECT $this WHERE {<br>
        $this qudt:numericValue ?v .<br>
        OPTIONAL { $this :lowerBound ?lo . }<br>
        OPTIONAL { $this :upperBound ?hi . }<br>
        FILTER( (BOUND(?lo) && ?v < ?lo) || (BOUND(?hi) && ?v > ?hi) )<br>
      }<br>
    """<br>
  ] .<br>
```<br>
<br>

