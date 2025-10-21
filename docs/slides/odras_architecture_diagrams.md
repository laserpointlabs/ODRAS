# ODRAS Architecture Diagrams for Slides

## 1. Overall Architecture

```mermaid
%%{init: {'theme':'base', 'themeVariables': { 'fontSize':'16px'}}}%%
flowchart LR
    subgraph UI["User Interface"]
    direction TB
        WEB["Web Portal"]
        DAS["DAS Chat"]
        API["REST APIs"]
    end
    
    subgraph CORE["ODRAS Core"]
    direction TB
        ONT["Ontology<br/>Engine"]
        KNOW["Knowledge<br/>RAG"]
        REQ["Requirements<br/>Processor"]
        CONC["Conceptualizer<br/>AI"]
    end
    
    subgraph DATA["Data Layer"]
    direction TB
        PG["PostgreSQL"]
        NEO["Neo4j"]
        QD["Qdrant<br/>Vectors"]
        FUSE["Fuseki<br/>RDF"]
    end
    
    UI --> CORE
    CORE --> DATA
    
    style UI fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style CORE fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style DATA fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
```

## 2. Project Cell Architecture

```mermaid
%%{init: {'theme':'base', 'themeVariables': { 'fontSize':'14px'}}}%%
flowchart LR
    subgraph CELL["Project Cell"]
        direction TB
        NS["Namespace<br/>URI"]
        ONT2["Ontology"]
        DOC["Documents"]
        REQ2["Requirements"]
        KNOW2["Knowledge<br/>Base"]
        
        NS --> ONT2
        DOC --> KNOW2
        DOC --> REQ2
        ONT2 --> REQ2
    end
    
    subgraph ISO["Isolation"]
        SEC["Security<br/>Boundary"]
        PERM["Access<br/>Control"]
    end
    
    CELL --> ISO
    
    style CELL fill:#fff3e0,stroke:#f57c00,stroke-width:3px
    style ISO fill:#ffebee,stroke:#d32f2f,stroke-width:2px
```

## 3. Knowledge Processing Pipeline

```mermaid
%%{init: {'theme':'base', 'themeVariables': { 'fontSize':'14px'}}}%%
flowchart LR
    DOC2["📄 Document"] --> EXT["Extract<br/>Text"]
    EXT --> CHUNK["Chunk<br/>Content"]
    CHUNK --> EMB["Generate<br/>Embeddings"]
    EMB --> QDRANT["Store in<br/>Qdrant"]
    
    QDRANT --> RAG["RAG<br/>Search"]
    QUERY["User<br/>Query"] --> RAG
    RAG --> AI["LLM<br/>Response"]
    
    style DOC2 fill:#e8eaf6,stroke:#3f51b5,stroke-width:2px
    style QDRANT fill:#e0f2f1,stroke:#00897b,stroke-width:2px
    style AI fill:#fce4ec,stroke:#c2185b,stroke-width:2px
```

## 4. Ontology Management

```mermaid
%%{init: {'theme':'base', 'themeVariables': { 'fontSize':'14px'}}}%%
flowchart TD
    subgraph ONT3["Ontology Layers"]
        FOUND["Foundation<br/>Core SE"]
        DOM["Domain<br/>Aerospace"]
        PROJ["Project<br/>Specific"]
        
        FOUND --> DOM
        DOM --> PROJ
    end
    
    subgraph OPS["Operations"]
        IMP["Import"]
        VAL["Validate"]
        PUB["Publish"]
        VER["Version"]
    end
    
    ONT3 --> OPS
    OPS --> FUSE2["Fuseki<br/>RDF Store"]
    
    style FOUND fill:#ffecb3,stroke:#ff6f00,stroke-width:2px
    style FUSE2 fill:#c8e6c9,stroke:#388e3c,stroke-width:2px
```

## 5. Conceptualization Process

```mermaid
%%{init: {'theme':'base', 'themeVariables': { 'fontSize':'14px'}}}%%
flowchart LR
    REQ3["Requirements"] --> DAS2["DAS<br/>Analysis"]
    ONT4["Ontology<br/>Classes"] --> DAS2
    
    DAS2 --> GEN{{"Generate<br/>Concepts"}}
    
    GEN --> COMP["Components"]
    GEN --> FUNC["Functions"]
    GEN --> INTF["Interfaces"]
    GEN --> CONS["Constraints"]
    
    COMP --> CAM["Export to<br/>Cameo"]
    FUNC --> CAM
    INTF --> CAM
    CONS --> CAM
    
    style REQ3 fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
    style DAS2 fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style CAM fill:#e8f5e9,stroke:#388e3c,stroke-width:2px
```

