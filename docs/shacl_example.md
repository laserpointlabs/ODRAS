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
---<br>
<br>
```mermaid<br>
flowchart LR<br>
  %% ====== NodeShapes ======<br>
  SComp[":ComponentShape<br>sh:NodeShape<br>sh:targetClass :Component"]<br>
  SMass[":MassQuantityShape<br>sh:NodeShape<br>(Reusable QUDT template)"]<br>
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

