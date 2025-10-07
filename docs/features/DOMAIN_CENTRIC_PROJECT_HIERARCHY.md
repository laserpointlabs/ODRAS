# Domain-Centric Project Hierarchy Design

**Document Type:** Technical Architecture Design
**Created:** October 7, 2025
**Status:** Design Phase
**Related Documents:** ODRAS_Management_Presentation_Summary.md

---

## Executive Summary

This document outlines the design for a domain-centric project hierarchy system in ODRAS that supports vertical project paths within domains, cross-domain knowledge propagation, and intelligent impact analysis. The system enables top-down knowledge and requirements flow with DAS-driven cross-domain link detection and admin-controlled quality gates.

## Core Concept: Vertical Domain Paths

### Domain-Centric Organization

```mermaid
graph TD
    subgraph "Primary Core Domain (L0)"
        CORE[Core Organizational Knowledge]
    end

    subgraph "Domain A: Aerospace"
        A_L1[L1: System Architecture]
        A_L2A[L2: Navigation Design]
        A_L2B[L2: Safety Analysis]
        A_L3A[L3: GPS Implementation]
        A_L3B[L3: INS Implementation]
        A_L3C[L3: Safety Testing]
    end

    subgraph "Domain B: Maritime"
        B_L1[L1: Maritime Systems]
        B_L2A[L2: Navigation Systems]
        B_L2B[L2: Communication]
        B_L3A[L3: Radar Implementation]
        B_L3B[L3: Sonar Implementation]
    end

    CORE --> A_L1
    CORE --> B_L1

    A_L1 --> A_L2A
    A_L1 --> A_L2B
    A_L2A --> A_L3A
    A_L2A --> A_L3B
    A_L2B --> A_L3C

    B_L1 --> B_L2A
    B_L1 --> B_L2B
    B_L2A --> B_L3A
    B_L2A --> B_L3B

    classDef coreStyle fill:#ff6b6b,stroke:#d63031,stroke-width:3px,color:#fff
    classDef l1Style fill:#45b7d1,stroke:#0984e3,stroke-width:2px,color:#fff
    classDef l2Style fill:#96ceb4,stroke:#00b894,stroke-width:2px,color:#000
    classDef l3Style fill:#ddd6fe,stroke:#8b5cf6,stroke-width:2px,color:#000

    class CORE coreStyle
    class A_L1,B_L1 l1Style
    class A_L2A,A_L2B,B_L2A,B_L2B l2Style
    class A_L3A,A_L3B,A_L3C,B_L3A,B_L3B l3Style
```

### Project Hierarchy Levels

- **L0 (Core)**: Primary organizational domain with foundational knowledge
- **L1 (Strategic)**: Strategic & Architecture projects within specific domains
- **L2 (Tactical)**: Tactical & Design projects that inherit from L1
- **L3 (Implementation)**: Implementation & Testing projects that inherit from L2

## Knowledge Flow Architecture

### Top-Down Knowledge Propagation

```mermaid
graph TD
    subgraph "Knowledge Flow Pattern"
        L1_KNOWLEDGE[L1 Published Knowledge]
        L2_PROJECT[L2 Project]
        L2_DERIVED[L2 Derived Knowledge]
        L3_PROJECT[L3 Project]
        L3_DERIVED[L3 Implementation Knowledge]
    end

    subgraph "Approval Workflow"
        DRAFT[Draft State]
        REVIEW[Review State]
        APPROVED[Approved State]
        PUBLISHED[Published State]
    end

    subgraph "Cross-Domain Detection"
        DAS[DAS Analysis Engine]
        SIMILARITY[Similarity Detection]
        CROSS_DOMAIN[Cross-Domain Links]
        ADMIN_APPROVAL[Admin Approval]
    end

    L1_KNOWLEDGE -->|Import| L2_PROJECT
    L2_PROJECT -->|Analyze & Derive| L2_DERIVED
    L2_DERIVED --> DRAFT
    DRAFT --> REVIEW
    REVIEW --> APPROVED
    APPROVED --> PUBLISHED
    PUBLISHED -->|Import| L3_PROJECT
    L3_PROJECT -->|Implement| L3_DERIVED

    L2_DERIVED --> DAS
    DAS --> SIMILARITY
    SIMILARITY --> CROSS_DOMAIN
    CROSS_DOMAIN --> ADMIN_APPROVAL

    classDef knowledgeStyle fill:#4ecdc4,stroke:#00b894,stroke-width:2px,color:#fff
    classDef approvalStyle fill:#fdcb6e,stroke:#e17055,stroke-width:2px,color:#000
    classDef dasStyle fill:#a29bfe,stroke:#6c5ce7,stroke-width:2px,color:#fff

    class L1_KNOWLEDGE,L2_DERIVED,L3_DERIVED knowledgeStyle
    class DRAFT,REVIEW,APPROVED,PUBLISHED approvalStyle
    class DAS,SIMILARITY,CROSS_DOMAIN,ADMIN_APPROVAL dasStyle
```

## Requirements Hierarchy System

### Requirements Flow and Derivation

```mermaid
graph TD
    subgraph "L1 Domain Requirements"
        L1_REQ1[REQ-L1-001: System Navigation]
        L1_REQ2[REQ-L1-002: Safety Standards]
        L1_REQ3[REQ-L1-003: Performance Metrics]
    end

    subgraph "L2 Mission Requirements"
        L2_REQ1[REQ-L2-001: GPS Navigation]
        L2_REQ2[REQ-L2-002: Backup INS]
        L2_REQ3[REQ-L2-003: Safety Protocols]
        L2_REQ4[REQ-L2-004: Performance Tests]
    end

    subgraph "L3 Implementation Requirements"
        L3_REQ1[REQ-L3-001: GPS Receiver Config]
        L3_REQ2[REQ-L3-002: INS Calibration]
        L3_REQ3[REQ-L3-003: Safety Test Cases]
        L3_REQ4[REQ-L3-004: Performance Benchmarks]
    end

    subgraph "Cross-Domain Links"
        MARITIME_REQ[Maritime Navigation REQ]
        AUTOMOTIVE_REQ[Automotive Safety REQ]
    end

    L1_REQ1 -->|Import & Derive| L2_REQ1
    L1_REQ1 -->|Import & Derive| L2_REQ2
    L1_REQ2 -->|Import & Derive| L2_REQ3
    L1_REQ3 -->|Import & Derive| L2_REQ4

    L2_REQ1 -->|Import & Derive| L3_REQ1
    L2_REQ2 -->|Import & Derive| L3_REQ2
    L2_REQ3 -->|Import & Derive| L3_REQ3
    L2_REQ4 -->|Import & Derive| L3_REQ4

    L2_REQ1 -.->|DAS Detected Link| MARITIME_REQ
    L2_REQ3 -.->|DAS Detected Link| AUTOMOTIVE_REQ

    classDef l1ReqStyle fill:#ff7675,stroke:#d63031,stroke-width:2px,color:#fff
    classDef l2ReqStyle fill:#74b9ff,stroke:#0984e3,stroke-width:2px,color:#fff
    classDef l3ReqStyle fill:#55a3ff,stroke:#2d3436,stroke-width:2px,color:#fff
    classDef crossDomainStyle fill:#fd79a8,stroke:#e84393,stroke-width:2px,color:#fff

    class L1_REQ1,L1_REQ2,L1_REQ3 l1ReqStyle
    class L2_REQ1,L2_REQ2,L2_REQ3,L2_REQ4 l2ReqStyle
    class L3_REQ1,L3_REQ2,L3_REQ3,L3_REQ4 l3ReqStyle
    class MARITIME_REQ,AUTOMOTIVE_REQ crossDomainStyle
```

## Cross-Domain Intelligence System

### DAS Cross-Domain Detection

```mermaid
graph TD
    subgraph "Domain A: Aerospace"
        A_PROJ[Aerospace Navigation Project]
        A_REQ[Navigation Requirements]
        A_KNOWLEDGE[Navigation Knowledge]
    end

    subgraph "Domain B: Maritime"
        B_PROJ[Maritime Navigation Project]
        B_REQ[Navigation Requirements]
        B_KNOWLEDGE[Navigation Knowledge]
    end

    subgraph "Domain C: Automotive"
        C_PROJ[Automotive Safety Project]
        C_REQ[Safety Requirements]
        C_KNOWLEDGE[Safety Knowledge]
    end

    subgraph "DAS Analysis Engine"
        SEMANTIC[Semantic Analysis]
        SIMILARITY[Similarity Detection]
        CLASSIFIER[Link Classifier]
        CONFIDENCE[Confidence Scoring]
    end

    subgraph "Cross-Domain Links"
        NAV_LINK[Navigation Link A↔B]
        SAFETY_LINK[Safety Link A↔C]
        MULTI_LINK[Multi-Domain Link]
    end

    subgraph "Admin Approval"
        SUGGESTIONS[Link Suggestions]
        SME_REVIEW[SME Review]
        APPROVED_LINKS[Approved Links]
    end

    A_REQ --> SEMANTIC
    A_KNOWLEDGE --> SEMANTIC
    B_REQ --> SEMANTIC
    B_KNOWLEDGE --> SEMANTIC
    C_REQ --> SEMANTIC
    C_KNOWLEDGE --> SEMANTIC

    SEMANTIC --> SIMILARITY
    SIMILARITY --> CLASSIFIER
    CLASSIFIER --> CONFIDENCE

    CONFIDENCE --> NAV_LINK
    CONFIDENCE --> SAFETY_LINK
    CONFIDENCE --> MULTI_LINK

    NAV_LINK --> SUGGESTIONS
    SAFETY_LINK --> SUGGESTIONS
    MULTI_LINK --> SUGGESTIONS

    SUGGESTIONS --> SME_REVIEW
    SME_REVIEW --> APPROVED_LINKS

    classDef domainStyle fill:#74b9ff,stroke:#0984e3,stroke-width:2px,color:#fff
    classDef dasStyle fill:#a29bfe,stroke:#6c5ce7,stroke-width:2px,color:#fff
    classDef linkStyle fill:#fd79a8,stroke:#e84393,stroke-width:2px,color:#fff
    classDef approvalStyle fill:#00b894,stroke:#00a085,stroke-width:2px,color:#fff

    class A_PROJ,A_REQ,A_KNOWLEDGE,B_PROJ,B_REQ,B_KNOWLEDGE,C_PROJ,C_REQ,C_KNOWLEDGE domainStyle
    class SEMANTIC,SIMILARITY,CLASSIFIER,CONFIDENCE dasStyle
    class NAV_LINK,SAFETY_LINK,MULTI_LINK linkStyle
    class SUGGESTIONS,SME_REVIEW,APPROVED_LINKS approvalStyle
```

## Impact Analysis System

### Requirement Change Impact Graph

```mermaid
graph TD
    subgraph "Impact Source"
        SOURCE_REQ[Modified Requirement]
    end

    subgraph "Direct Impacts"
        DIRECT1[Child Requirement 1]
        DIRECT2[Child Requirement 2]
        DIRECT3[Derived Requirement 3]
    end

    subgraph "Cascade Impacts"
        CASCADE1[Grandchild Req 1]
        CASCADE2[Grandchild Req 2]
        CASCADE3[Implementation Req 1]
        CASCADE4[Implementation Req 2]
    end

    subgraph "Cross-Domain Impacts"
        CROSS1[Maritime Domain Req]
        CROSS2[Automotive Domain Req]
        CROSS3[Defense Domain Req]
    end

    subgraph "Impact Severity"
        LOW[Low Impact]
        MEDIUM[Medium Impact]
        HIGH[High Impact]
        CRITICAL[Critical Impact]
    end

    SOURCE_REQ -->|Direct| DIRECT1
    SOURCE_REQ -->|Direct| DIRECT2
    SOURCE_REQ -->|Direct| DIRECT3

    DIRECT1 -->|Cascade| CASCADE1
    DIRECT1 -->|Cascade| CASCADE2
    DIRECT2 -->|Cascade| CASCADE3
    DIRECT3 -->|Cascade| CASCADE4

    SOURCE_REQ -.->|Cross-Domain| CROSS1
    DIRECT2 -.->|Cross-Domain| CROSS2
    CASCADE1 -.->|Cross-Domain| CROSS3

    DIRECT1 --> MEDIUM
    DIRECT2 --> HIGH
    DIRECT3 --> LOW
    CASCADE1 --> MEDIUM
    CASCADE2 --> LOW
    CASCADE3 --> HIGH
    CASCADE4 --> MEDIUM
    CROSS1 --> CRITICAL
    CROSS2 --> HIGH
    CROSS3 --> MEDIUM

    classDef sourceStyle fill:#e17055,stroke:#d63031,stroke-width:3px,color:#fff
    classDef directStyle fill:#fdcb6e,stroke:#f39c12,stroke-width:2px,color:#000
    classDef cascadeStyle fill:#81ecec,stroke:#00cec9,stroke-width:2px,color:#000
    classDef crossStyle fill:#fd79a8,stroke:#e84393,stroke-width:2px,color:#fff
    classDef lowStyle fill:#00b894,stroke:#00a085,stroke-width:1px,color:#fff
    classDef mediumStyle fill:#fdcb6e,stroke:#f39c12,stroke-width:1px,color:#000
    classDef highStyle fill:#e17055,stroke:#d63031,stroke-width:1px,color:#fff
    classDef criticalStyle fill:#d63031,stroke:#74b9ff,stroke-width:2px,color:#fff

    class SOURCE_REQ sourceStyle
    class DIRECT1,DIRECT2,DIRECT3 directStyle
    class CASCADE1,CASCADE2,CASCADE3,CASCADE4 cascadeStyle
    class CROSS1,CROSS2,CROSS3 crossStyle
    class LOW lowStyle
    class MEDIUM mediumStyle
    class HIGH highStyle
    class CRITICAL criticalStyle
```

## Database Schema Design

### Core Tables Structure

```mermaid
erDiagram
    PROJECTS {
        uuid project_id PK
        varchar name
        text description
        varchar domain_path
        integer project_level
        uuid parent_project_id FK
        boolean is_primary_domain
        varchar knowledge_approval_status
        jsonb cross_domain_links
        timestamptz created_at
    }

    REQUIREMENTS {
        uuid requirement_id PK
        uuid project_id FK
        text requirement_text
        varchar requirement_type
        varchar priority
        varchar state
        varchar domain_path
        integer requirement_level
        uuid parent_requirement_id FK
        uuid derived_from FK
        uuid created_by FK
        boolean is_published
        timestamptz created_at
    }

    REQUIREMENT_IMPORTS {
        uuid import_id PK
        uuid source_project_id FK
        uuid target_project_id FK
        uuid requirement_id FK
        varchar import_type
        varchar import_status
        timestamptz created_at
    }

    CROSS_DOMAIN_REQUIREMENTS {
        uuid link_id PK
        uuid source_requirement_id FK
        uuid target_requirement_id FK
        varchar link_type
        float confidence_score
        varchar suggested_by
        varchar status
        timestamptz created_at
    }

    REQUIREMENT_IMPACTS {
        uuid impact_id PK
        uuid requirement_id FK
        uuid affected_requirement_id FK
        varchar impact_type
        varchar impact_severity
        text impact_description
        timestamptz created_at
    }

    PROJECTS ||--o{ REQUIREMENTS : "contains"
    PROJECTS ||--o{ PROJECTS : "parent_child"
    REQUIREMENTS ||--o{ REQUIREMENTS : "parent_child"
    REQUIREMENTS ||--o{ REQUIREMENT_IMPORTS : "imported_to"
    REQUIREMENTS ||--o{ CROSS_DOMAIN_REQUIREMENTS : "linked_with"
    REQUIREMENTS ||--o{ REQUIREMENT_IMPACTS : "impacts"
```

## Implementation Phases

### Phase Timeline

```mermaid
gantt
    title Implementation Timeline
    dateFormat  YYYY-MM-DD
    section Phase 1
    Add project hierarchy fields    :p1-1, 2025-10-08, 2d
    Update project creation API     :p1-2, after p1-1, 1d
    Basic hierarchy queries         :p1-3, after p1-2, 2d

    section Phase 2
    Requirements table creation     :p2-1, after p1-3, 2d
    Import/export functionality     :p2-2, after p2-1, 2d
    Basic approval workflow         :p2-3, after p2-2, 1d

    section Phase 3
    Cross-domain links table        :p3-1, after p2-3, 1d
    DAS similarity analysis         :p3-2, after p3-1, 2d
    Admin approval interface        :p3-3, after p3-2, 2d

    section Phase 4
    Impact analysis queries         :p4-1, after p3-3, 1d
    Graph traversal implementation  :p4-2, after p4-1, 2d
    Admin monitoring dashboard      :p4-3, after p4-2, 2d
```

## Admin Monitoring Dashboard

### Dashboard Overview

```mermaid
graph TD
    subgraph "Admin Dashboard"
        OVERVIEW[System Overview]
        DOMAINS[Domain Health]
        APPROVALS[Pending Approvals]
        IMPACTS[Impact Analysis]
        CROSS_DOMAIN[Cross-Domain Links]
    end

    subgraph "System Metrics"
        PROJ_COUNT[Total Projects: 45]
        REQ_COUNT[Total Requirements: 1,247]
        PENDING_COUNT[Pending Approvals: 12]
        CROSS_COUNT[Cross-Domain Suggestions: 8]
        IMPACT_COUNT[High Impact Changes: 3]
    end

    subgraph "Domain Statistics"
        AEROSPACE[Aerospace: 15 projects]
        MARITIME[Maritime: 12 projects]
        AUTOMOTIVE[Automotive: 8 projects]
        DEFENSE[Defense: 10 projects]
    end

    subgraph "Quality Metrics"
        COVERAGE[Requirement Coverage: 87%]
        LINKS[Cross-Domain Links: 23]
        QUALITY[Quality Score: 92%]
    end

    OVERVIEW --> PROJ_COUNT
    OVERVIEW --> REQ_COUNT
    OVERVIEW --> PENDING_COUNT

    DOMAINS --> AEROSPACE
    DOMAINS --> MARITIME
    DOMAINS --> AUTOMOTIVE
    DOMAINS --> DEFENSE

    CROSS_DOMAIN --> COVERAGE
    CROSS_DOMAIN --> LINKS
    CROSS_DOMAIN --> QUALITY

    classDef dashboardStyle fill:#74b9ff,stroke:#0984e3,stroke-width:2px,color:#fff
    classDef metricsStyle fill:#00b894,stroke:#00a085,stroke-width:2px,color:#fff
    classDef domainStyle fill:#fdcb6e,stroke:#f39c12,stroke-width:2px,color:#000
    classDef qualityStyle fill:#a29bfe,stroke:#6c5ce7,stroke-width:2px,color:#fff

    class OVERVIEW,DOMAINS,APPROVALS,IMPACTS,CROSS_DOMAIN dashboardStyle
    class PROJ_COUNT,REQ_COUNT,PENDING_COUNT,CROSS_COUNT,IMPACT_COUNT metricsStyle
    class AEROSPACE,MARITIME,AUTOMOTIVE,DEFENSE domainStyle
    class COVERAGE,LINKS,QUALITY qualityStyle
```

## DAS Intelligence Integration

### DAS Analysis Capabilities

```mermaid
graph TD
    subgraph "DAS Intelligence Engine"
        PATTERN_ANALYSIS[Pattern Analysis]
        SIMILARITY_ENGINE[Similarity Engine]
        IMPACT_PREDICTOR[Impact Predictor]
        QUALITY_ANALYZER[Quality Analyzer]
        OPTIMIZATION_ENGINE[Optimization Engine]
    end

    subgraph "Analysis Inputs"
        PROJECT_DATA[Project Data]
        REQUIREMENT_DATA[Requirements Data]
        KNOWLEDGE_DATA[Knowledge Data]
        HISTORICAL_DATA[Historical Data]
        USER_BEHAVIOR[User Behavior]
    end

    subgraph "Intelligence Outputs"
        CROSS_DOMAIN_OPP[Cross-Domain Opportunities]
        REQUIREMENT_GAPS[Requirement Gaps]
        IMPACT_WARNINGS[Impact Warnings]
        QUALITY_ISSUES[Quality Issues]
        OPTIMIZATION_SUGGESTIONS[Optimization Suggestions]
    end

    subgraph "Admin Actions"
        APPROVE_LINKS[Approve Cross-Domain Links]
        QUALITY_REVIEW[Quality Review]
        IMPACT_MITIGATION[Impact Mitigation]
        PROCESS_OPTIMIZATION[Process Optimization]
    end

    PROJECT_DATA --> PATTERN_ANALYSIS
    REQUIREMENT_DATA --> SIMILARITY_ENGINE
    KNOWLEDGE_DATA --> QUALITY_ANALYZER
    HISTORICAL_DATA --> IMPACT_PREDICTOR
    USER_BEHAVIOR --> OPTIMIZATION_ENGINE

    PATTERN_ANALYSIS --> CROSS_DOMAIN_OPP
    SIMILARITY_ENGINE --> REQUIREMENT_GAPS
    IMPACT_PREDICTOR --> IMPACT_WARNINGS
    QUALITY_ANALYZER --> QUALITY_ISSUES
    OPTIMIZATION_ENGINE --> OPTIMIZATION_SUGGESTIONS

    CROSS_DOMAIN_OPP --> APPROVE_LINKS
    QUALITY_ISSUES --> QUALITY_REVIEW
    IMPACT_WARNINGS --> IMPACT_MITIGATION
    OPTIMIZATION_SUGGESTIONS --> PROCESS_OPTIMIZATION

    classDef dasStyle fill:#a29bfe,stroke:#6c5ce7,stroke-width:2px,color:#fff
    classDef inputStyle fill:#81ecec,stroke:#00cec9,stroke-width:2px,color:#000
    classDef outputStyle fill:#fdcb6e,stroke:#f39c12,stroke-width:2px,color:#000
    classDef actionStyle fill:#00b894,stroke:#00a085,stroke-width:2px,color:#fff

    class PATTERN_ANALYSIS,SIMILARITY_ENGINE,IMPACT_PREDICTOR,QUALITY_ANALYZER,OPTIMIZATION_ENGINE dasStyle
    class PROJECT_DATA,REQUIREMENT_DATA,KNOWLEDGE_DATA,HISTORICAL_DATA,USER_BEHAVIOR inputStyle
    class CROSS_DOMAIN_OPP,REQUIREMENT_GAPS,IMPACT_WARNINGS,QUALITY_ISSUES,OPTIMIZATION_SUGGESTIONS outputStyle
    class APPROVE_LINKS,QUALITY_REVIEW,IMPACT_MITIGATION,PROCESS_OPTIMIZATION actionStyle
```

## Database Schema Implementation

### SQL Schema Changes

```sql
-- Add hierarchy fields to existing projects table
ALTER TABLE public.projects
ADD COLUMN IF NOT EXISTS project_level INTEGER DEFAULT 1 CHECK (project_level IN (1, 2, 3)),
ADD COLUMN IF NOT EXISTS parent_project_id UUID REFERENCES public.projects(project_id) ON DELETE CASCADE,
ADD COLUMN IF NOT EXISTS domain_path TEXT,
ADD COLUMN IF NOT EXISTS is_primary_domain BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS knowledge_approval_status TEXT DEFAULT 'draft' CHECK (knowledge_approval_status IN ('draft', 'review', 'approved', 'published')),
ADD COLUMN IF NOT EXISTS cross_domain_links JSONB DEFAULT '[]';

-- Requirements hierarchy tables
CREATE TABLE IF NOT EXISTS public.requirements (
    requirement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES public.projects(project_id) ON DELETE CASCADE,
    requirement_text TEXT NOT NULL,
    requirement_type TEXT NOT NULL CHECK (requirement_type IN ('functional', 'non_functional', 'performance', 'safety', 'security', 'interface')),
    priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    state TEXT DEFAULT 'draft' CHECK (state IN ('draft', 'review', 'approved', 'published', 'deprecated')),
    domain_path TEXT NOT NULL,
    requirement_level INTEGER DEFAULT 1 CHECK (requirement_level IN (1, 2, 3)),
    parent_requirement_id UUID REFERENCES public.requirements(requirement_id) ON DELETE CASCADE,
    derived_from UUID REFERENCES public.requirements(requirement_id),
    created_by UUID REFERENCES public.users(user_id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    version INTEGER DEFAULT 1,
    is_published BOOLEAN DEFAULT FALSE
);

-- Requirements import/export relationships
CREATE TABLE IF NOT EXISTS public.requirement_imports (
    import_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_project_id UUID REFERENCES public.projects(project_id) ON DELETE CASCADE,
    target_project_id UUID REFERENCES public.projects(project_id) ON DELETE CASCADE,
    requirement_id UUID REFERENCES public.requirements(requirement_id) ON DELETE CASCADE,
    import_type TEXT DEFAULT 'inherited' CHECK (import_type IN ('inherited', 'referenced', 'derived')),
    import_status TEXT DEFAULT 'active' CHECK (import_status IN ('active', 'superseded', 'deprecated')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(target_project_id, requirement_id)
);

-- Cross-domain requirement links
CREATE TABLE IF NOT EXISTS public.cross_domain_requirements (
    link_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_requirement_id UUID REFERENCES public.requirements(requirement_id) ON DELETE CASCADE,
    target_requirement_id UUID REFERENCES public.requirements(requirement_id) ON DELETE CASCADE,
    link_type TEXT NOT NULL CHECK (link_type IN ('similar', 'conflicting', 'complementary', 'dependent')),
    confidence_score FLOAT DEFAULT 0.0 CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    suggested_by TEXT DEFAULT 'das' CHECK (suggested_by IN ('das', 'admin', 'sme')),
    status TEXT DEFAULT 'suggested' CHECK (status IN ('suggested', 'approved', 'rejected')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Requirements impact analysis
CREATE TABLE IF NOT EXISTS public.requirement_impacts (
    impact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requirement_id UUID REFERENCES public.requirements(requirement_id) ON DELETE CASCADE,
    affected_requirement_id UUID REFERENCES public.requirements(requirement_id) ON DELETE CASCADE,
    impact_type TEXT NOT NULL CHECK (impact_type IN ('direct', 'indirect', 'cascade')),
    impact_severity TEXT DEFAULT 'medium' CHECK (impact_severity IN ('low', 'medium', 'high', 'critical')),
    impact_description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_projects_level ON public.projects(project_level);
CREATE INDEX IF NOT EXISTS idx_projects_parent ON public.projects(parent_project_id);
CREATE INDEX IF NOT EXISTS idx_projects_domain ON public.projects(domain_path);
CREATE INDEX IF NOT EXISTS idx_requirements_project ON public.requirements(project_id);
CREATE INDEX IF NOT EXISTS idx_requirements_domain ON public.requirements(domain_path);
CREATE INDEX IF NOT EXISTS idx_requirements_level ON public.requirements(requirement_level);
CREATE INDEX IF NOT EXISTS idx_requirements_parent ON public.requirements(parent_requirement_id);
CREATE INDEX IF NOT EXISTS idx_requirements_published ON public.requirements(is_published) WHERE is_published = TRUE;
CREATE INDEX IF NOT EXISTS idx_requirement_imports_target ON public.requirement_imports(target_project_id);
CREATE INDEX IF NOT EXISTS idx_cross_domain_requirements_source ON public.cross_domain_requirements(source_requirement_id);

-- Comments for documentation
COMMENT ON COLUMN public.projects.project_level IS 'Project hierarchy level: 1=Strategic, 2=Tactical, 3=Implementation';
COMMENT ON COLUMN public.projects.parent_project_id IS 'Parent project ID for L2/L3 projects';
COMMENT ON COLUMN public.projects.domain_path IS 'Domain path e.g., "aerospace/navigation/autonomous"';
COMMENT ON COLUMN public.projects.is_primary_domain IS 'Whether this is the primary project for a domain';
COMMENT ON COLUMN public.projects.knowledge_approval_status IS 'Approval status for knowledge publishing';
COMMENT ON COLUMN public.projects.cross_domain_links IS 'JSON array of approved cross-domain links';
```

## API Implementation Examples

### Project Creation with Hierarchy

```python
# Backend API endpoint update
@app.post("/api/projects")
async def create_project(body: Dict, user=Depends(get_user)):
    name = (body.get("name") or "").strip()
    namespace_id = body.get("namespace_id")
    domain = body.get("domain")
    project_level = body.get("project_level", 1)  # Default to L1
    parent_project_id = body.get("parent_project_id")  # Optional for L2/L3
    domain_path = body.get("domain_path", domain)  # Use domain as default path

    # Validation logic for hierarchy
    if project_level > 1 and not parent_project_id:
        raise HTTPException(status_code=400, detail="L2/L3 projects require parent_project_id")

    if project_level == 1 and parent_project_id:
        raise HTTPException(status_code=400, detail="L1 projects cannot have parent")

    # Validate parent project exists and is at correct level
    if parent_project_id:
        parent_project = db.get_project(parent_project_id)
        if not parent_project:
            raise HTTPException(status_code=400, detail="Parent project not found")
        if parent_project['project_level'] >= project_level:
            raise HTTPException(status_code=400, detail="Parent project must be at higher level")

    # Create project with hierarchy
    proj = db.create_project_with_hierarchy(
        name=name,
        owner_user_id=user["user_id"],
        description=body.get("description"),
        namespace_id=namespace_id,
        domain=domain,
        project_level=project_level,
        parent_project_id=parent_project_id,
        domain_path=domain_path
    )

    return {"project": proj}
```

### Requirements Import API

```python
@app.post("/api/projects/{project_id}/requirements/import")
async def import_requirements(
    project_id: str,
    body: Dict,
    user=Depends(get_user)
):
    source_project_id = body.get("source_project_id")
    requirement_ids = body.get("requirement_ids", [])

    if not source_project_id or not requirement_ids:
        raise HTTPException(status_code=400, detail="source_project_id and requirement_ids required")

    # Validate user has access to both projects
    if not db.user_has_project_access(user["user_id"], project_id):
        raise HTTPException(status_code=403, detail="Access denied to target project")
    if not db.user_has_project_access(user["user_id"], source_project_id):
        raise HTTPException(status_code=403, detail="Access denied to source project")

    # Import requirements
    result = requirements_service.import_requirements_to_project(
        target_project_id=project_id,
        source_project_id=source_project_id,
        requirement_ids=requirement_ids
    )

    return result

@app.post("/api/projects/{project_id}/requirements/{requirement_id}/derive")
async def derive_requirements(
    project_id: str,
    requirement_id: str,
    body: Dict,
    user=Depends(get_user)
):
    derived_requirements = body.get("derived_requirements", [])

    if not derived_requirements:
        raise HTTPException(status_code=400, detail="derived_requirements required")

    # Validate user access
    if not db.user_has_project_access(user["user_id"], project_id):
        raise HTTPException(status_code=403, detail="Access denied")

    # Create derived requirements
    result = requirements_service.derive_requirements(
        project_id=project_id,
        parent_requirement_id=requirement_id,
        derived_requirements=derived_requirements
    )

    return result
```

## Benefits and Value Proposition

### System Benefits

1. **Domain-Centric Organization**: Clear vertical paths within domains
2. **Knowledge Propagation**: Top-down knowledge flow with approval gates
3. **Cross-Domain Intelligence**: DAS-driven discovery of connections
4. **Quality Control**: Multi-stage approval process
5. **Impact Analysis**: Real-time impact assessment for changes
6. **Scalable Architecture**: Supports multiple domains and hierarchies
7. **Expert System Behavior**: Knowledge flows from experts to implementers

### Implementation Advantages

1. **Builds on Existing Infrastructure**: Leverages current ODRAS capabilities
2. **Incremental Delivery**: Value delivered at each implementation phase
3. **Simple Database Changes**: Standard foreign keys and queries
4. **DAS Integration**: Reuses existing AI capabilities
5. **Admin Control**: Comprehensive monitoring and approval workflows

### Development Effort Estimation

- **Phase 1 (Basic Hierarchy)**: 1-2 days
- **Phase 2 (Requirements Flow)**: 2-3 days
- **Phase 3 (Cross-Domain Detection)**: 2-3 days
- **Phase 4 (Impact Analysis)**: 1-2 days
- **Total Estimated Effort**: 6-10 days

## Usage Examples

### Creating Domain Hierarchy

```python
# Create primary aerospace domain (L1)
aerospace_l1 = create_project({
    "name": "Aerospace Systems Architecture",
    "domain": "aerospace",
    "domain_path": "aerospace",
    "project_level": 1,
    "is_primary_domain": True
})

# Create navigation subsystem (L2)
navigation_l2 = create_project({
    "name": "Navigation Systems Design",
    "domain": "aerospace",
    "domain_path": "aerospace/navigation",
    "project_level": 2,
    "parent_project_id": aerospace_l1["project_id"]
})

# Create GPS implementation (L3)
gps_l3 = create_project({
    "name": "GPS Navigation Implementation",
    "domain": "aerospace",
    "domain_path": "aerospace/navigation/gps",
    "project_level": 3,
    "parent_project_id": navigation_l2["project_id"]
})
```

### Requirements Flow Example

```python
# Create L1 requirement
l1_req = create_requirement({
    "project_id": aerospace_l1["project_id"],
    "requirement_text": "The system shall provide autonomous navigation capabilities",
    "requirement_type": "functional",
    "priority": "high",
    "requirement_level": 1
})

# Publish L1 requirement
publish_requirements(aerospace_l1["project_id"], [l1_req["requirement_id"]])

# Import to L2 project
import_requirements(
    target_project_id=navigation_l2["project_id"],
    source_project_id=aerospace_l1["project_id"],
    requirement_ids=[l1_req["requirement_id"]]
)

# Derive L2 requirements
derive_requirements(
    project_id=navigation_l2["project_id"],
    parent_requirement_id=l1_req["requirement_id"],
    derived_requirements=[
        {
            "requirement_text": "The navigation system shall provide GPS-based positioning",
            "requirement_type": "functional",
            "priority": "high"
        },
        {
            "requirement_text": "The navigation system shall provide backup inertial navigation",
            "requirement_type": "functional",
            "priority": "medium"
        }
    ]
)
```

## Conclusion

The domain-centric project hierarchy design provides a natural evolution of ODRAS that supports:

- **Vertical knowledge flow** within domains
- **Cross-domain intelligence** through DAS
- **Impact analysis** for change management
- **Quality control** through approval workflows
- **Administrative oversight** through comprehensive dashboards

This design is achievable within 6-10 days of development effort and builds upon existing ODRAS infrastructure, making it a practical and valuable enhancement to the platform.

The system enables organizations to:
1. Organize projects by domain expertise
2. Ensure knowledge flows from strategic to implementation levels
3. Discover cross-domain opportunities automatically
4. Maintain quality through controlled approval processes
5. Understand the impact of changes before they are made

---

*Document Created: October 7, 2025*
*Author: ODRAS Development Team*
*Status: Design Phase - Ready for Implementation*
